"""Provider-neutral speech input and Intron's asynchronous file API.

Sahara 2.5 is intended, but the public API exposes no model pin selector or
verifiable server version. Intron results therefore always have model=None.
Container checks are lightweight validation, not full audio decoding.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
import re
import ssl
import time
from typing import Callable, Protocol
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from uuid import uuid4

import certifi


MAX_AUDIO_BYTES = 5_000_000
INTRON_LANGUAGES = frozenset({"en", "pcm", "yo", "ig", "ha"})
_MAX_RESPONSE_BYTES = 1_000_000
_BASE_URL = "https://infer.voice.intron.io/file/v1"


@dataclass(frozen=True)
class AudioInput:
    data: bytes
    content_type: str
    language: str | None = None


@dataclass(frozen=True)
class ASRResult:
    transcript: str
    provider: str
    model: str | None = None
    duration_seconds: float | None = None


class SpeechError(Exception):
    """Safe to display to callers; never include provider bodies or credentials."""


class SpeechProvider(Protocol):
    def transcribe(self, audio: AudioInput) -> ASRResult: ...


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _audio_format(audio: AudioInput) -> tuple[str, str]:
    if not isinstance(audio.data, bytes) or not 0 < len(audio.data) <= MAX_AUDIO_BYTES:
        raise SpeechError("Audio must contain between 1 and 5,000,000 bytes.")
    if not isinstance(audio.content_type, str):
        raise SpeechError("Unsupported audio content type.")
    content_type = audio.content_type.split(";", 1)[0].strip().lower()
    extensions = {
        "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
        "audio/mp4": "mp4", "audio/ogg": "ogg", "audio/webm": "webm",
        "audio/flac": "flac",
    }
    if content_type not in extensions:
        raise SpeechError("Unsupported audio content type.")
    data = audio.data
    extension = extensions[content_type]
    valid = False
    if extension == "wav":
        valid = len(data) >= 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    elif extension == "mp3":
        offset = 0
        if data[:3] == b"ID3" and len(data) >= 10:
            if data[3] not in (2, 3, 4) or any(byte & 128 for byte in data[6:10]):
                raise SpeechError("Audio content does not match its declared format.")
            offset = 10 + sum(byte << shift for byte, shift in zip(data[6:10], (21, 14, 7, 0)))
            if data[3] == 4 and data[5] & 16:
                offset += 10  # ID3v2.4 optional footer.
        frame = data[offset:offset + 4]
        valid = (
            len(frame) == 4 and frame[0] == 255 and frame[1] & 224 == 224
            and frame[1] & 24 != 8 and frame[1] & 6 != 0
            and frame[2] >> 4 not in (0, 15) and frame[2] & 12 != 12
        )
    elif extension == "mp4":
        box_size = int.from_bytes(data[:4], "big")
        brands = {
            b"isom", b"iso2", b"iso3", b"iso4", b"iso5", b"iso6", b"iso7",
            b"iso8", b"iso9", b"mp41", b"mp42", b"M4A ", b"M4B ", b"M4V ",
            b"avc1", b"dash",
        }
        valid = (
            len(data) >= 16 and data[4:8] == b"ftyp"
            and 16 <= box_size <= len(data) and data[8:12] in brands
        )
    elif extension == "ogg":
        valid = len(data) >= 28 and data[:5] == b"OggS\x00" and data[26] > 0
    elif extension == "webm":
        valid = data[:4] == b"\x1a\x45\xdf\xa3" and b"\x42\x82\x84webm" in data[4:4096]
    elif extension == "flac":
        valid = (
            len(data) >= 42 and data[:4] == b"fLaC"
            and data[4] & 127 == 0 and data[5:8] == b"\x00\x00\x22"
        )
    if not valid:
        raise SpeechError("Audio content does not match its declared format.")
    return content_type, extension


class IntronSpeechProvider:
    """No I/O on construction. Inject urlopen(request, timeout=...), clock and
    sleep for tests; the transport must not follow redirects. Missing credentials
    fail only when transcribe is called, leaving text-only callers unaffected.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        urlopen: Callable | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = os.getenv("INTRON_API_KEY", "") if api_key is None else api_key
        self._urlopen = urlopen
        self._clock = clock
        self._sleep = sleep

    def transcribe(self, audio: AudioInput) -> ASRResult:
        deadline = self._clock() + 90.0

        def remaining() -> float:
            seconds = deadline - self._clock()
            if seconds <= 0:
                raise SpeechError("Speech transcription timed out. You can enter text instead.")
            return seconds

        def wait(retry_after: str | None) -> None:
            delay = 1.0
            if retry_after and re.fullmatch(r"[0-9]+", retry_after.strip()):
                digits = retry_after.strip().lstrip("0") or "0"
                delay = 90.0 if len(digits) > 2 else max(delay, float(digits))
            self._sleep(min(delay, remaining()))
            remaining()

        def request(req: Request) -> tuple[dict | None, str | None]:
            timeout = min(15.0, remaining())
            request_deadline = self._clock() + timeout
            try:
                response = open_url(req, timeout=timeout)
            except HTTPError as error:
                response = error
            with response:
                remaining()
                retry_after = response.headers.get("Retry-After")
                if response.status in (429, 503) and req.get_method() == "GET":
                    return None, retry_after
                if not 200 <= response.status < 300:
                    raise SpeechError("Speech service is unavailable. You can enter text instead.")
                body = bytearray()
                # read1 avoids an unbounded read waiting for a slowly streamed body.
                while True:
                    remaining()
                    if self._clock() >= request_deadline:
                        raise SpeechError("Speech transcription timed out. You can enter text instead.")
                    chunk = response.read1(min(65536, _MAX_RESPONSE_BYTES + 1 - len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body) > _MAX_RESPONSE_BYTES:
                        raise SpeechError("Speech service returned an invalid response.")
            remaining()
            payload = json.loads(body.decode("utf-8"))
            if (
                not isinstance(payload, dict) or payload.get("status") != "Ok"
                or not isinstance(payload.get("data"), dict)
            ):
                raise SpeechError("Speech service returned an invalid response.")
            return payload["data"], retry_after

        try:
            if not self._api_key or not self._api_key.strip():
                raise SpeechError("Speech transcription is not configured. You can enter text instead.")
            if (
                not re.fullmatch(r"[\x21-\x7e]+", self._api_key)
            ):
                raise SpeechError("Speech transcription configuration is invalid.")
            if audio.language not in INTRON_LANGUAGES:
                raise SpeechError("Select a supported transcription language for this recording.")
            content_type, extension = _audio_format(audio)
            boundary = uuid4().hex
            filename = f"audio.{extension}"
            fields = {
                "audio_file_name": filename,
                "use_language_asr_input": audio.language,
                "use_disable_llm_corrections": "TRUE",
                "use_diarization": "FALSE",
                "use_category": "file_category_general",
            }
            body = b"".join(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("ascii")
                for name, value in fields.items()
            )
            body += (
                f'--{boundary}\r\nContent-Disposition: form-data; name="audio_file_blob"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("ascii") + audio.data + f"\r\n--{boundary}--\r\n".encode("ascii")
            open_url = self._urlopen
            if open_url is None:
                context = ssl.create_default_context(cafile=certifi.where())
                open_url = build_opener(HTTPSHandler(context=context), _NoRedirects()).open
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
                "User-Agent": "EdgeIMCI/0.1",
            }
            uploaded, retry_after = request(Request(
                f"{_BASE_URL}/upload", data=body, method="POST",
                headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
            ))
            file_id = uploaded.get("file_id")
            if not isinstance(file_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", file_id):
                raise SpeechError("Speech service returned an invalid response.")
            status_request = Request(f"{_BASE_URL}/status/{file_id}", headers=headers, method="GET")
            while True:
                wait(retry_after)
                data, retry_after = request(status_request)
                if data is None:
                    continue
                status = data.get("processing_status")
                if status == "FILE_TRANSCRIBED":
                    transcript = data.get("audio_transcript")
                    duration = data.get("processed_audio_duration_in_seconds")
                    if not isinstance(transcript, str) or not transcript.strip():
                        raise SpeechError("Speech service returned an invalid response.")
                    if duration is not None and (
                        type(duration) not in (int, float)
                        or not math.isfinite(duration) or duration < 0
                    ):
                        raise SpeechError("Speech service returned an invalid response.")
                    return ASRResult(
                        transcript, "intron",
                        duration_seconds=float(duration) if duration is not None else None,
                    )
                if status == "FILE_PROCESSING_FAILED":
                    raise SpeechError("Speech transcription failed. You can enter text instead.")
                if status not in ("FILE_QUEUED", "FILE_PENDING", "FILE_PROCESSING"):
                    raise SpeechError("Speech service returned an invalid response.")
        except SpeechError:
            raise
        except Exception:
            # Never surface transport errors, provider bodies, credentials or PHI.
            raise SpeechError("Speech service is unavailable. You can enter text instead.") from None
