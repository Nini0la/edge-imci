from __future__ import annotations

from email.parser import BytesParser
from email.policy import default
from io import BytesIO
import json
import traceback
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from app.speech import (
    ASRResult, AudioInput, IntronSpeechProvider, MAX_AUDIO_BYTES, SpeechError,
    SpeechProvider, _NoRedirects,
)


WAV = (
    b"RIFF\x26\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    b"\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00"
    b"\x02\x00\x10\x00data\x02\x00\x00\x00\x01\x02"
)
MP3 = b"\xff\xfb\x90\x00" + bytes(100)
FORMATS = [
    ("audio/wav", WAV),
    ("audio/x-wav", WAV),
    ("audio/mpeg", MP3),
    ("audio/mpeg", b"ID3\x04\x00\x00\x00\x00\x00\x00" + MP3),
    ("audio/mp4", b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00M4A isom"),
    ("audio/mp4", b"\x00\x00\x00\x18ftypiso6\x00\x00\x00\x00iso6mp41"),
    ("audio/ogg", b"OggS\x00" + bytes(21) + b"\x01\x08OpusHead"),
    ("audio/webm;codecs=opus", b"\x1a\x45\xdf\xa3\x87\x42\x82\x84webm" + bytes(20)),
    ("audio/flac", b"fLaC\x80\x00\x00\x22" + bytes(34)),
]
SECRET = "fake-key-not-a-secret"
PHI = "synthetic-private-transcript"


class Response(BytesIO):
    def __init__(self, data=None, *, raw=None, status=200, headers=None):
        super().__init__(json.dumps({"status": "Ok", "data": data}).encode() if raw is None else raw)
        self.status = status
        self.headers = headers or {}
        self.bytes_read = 0

    def read1(self, size=-1):
        chunk = super().read1(size)
        self.bytes_read += len(chunk)
        return chunk


class Transport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.now = 0.0
        self.sleeps = []

    def __call__(self, request, *, timeout):
        self.calls.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def provider(self, **kwargs):
        return IntronSpeechProvider(
            api_key=SECRET, urlopen=self, clock=self.clock, sleep=self.sleep, **kwargs,
        )


def uploaded(**kwargs):
    return Response({"file_id": "test-file-123"}, **kwargs)


def completed(**kwargs):
    return Response({"processing_status": "FILE_TRANSCRIBED", "audio_transcript": PHI, **kwargs})


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.delenv("INTRON_API_KEY", raising=False)
    monkeypatch.delenv("INTRON_LANGUAGE", raising=False)
    def unexpected_network(*args, **kwargs):
        pytest.fail("Real network transport must not be constructed in these tests")
    monkeypatch.setattr("app.speech.build_opener", unexpected_network)


@pytest.mark.parametrize("language", ["en", "pcm", "yo", "ig", "ha"])
def test_contract_and_multipart(language):
    transport = Transport(uploaded(), completed(processed_audio_duration_in_seconds=2.5, model="unverified"))
    provider: SpeechProvider = transport.provider()
    result = provider.transcribe(AudioInput(WAV, " Audio/X-Wav ;codecs=pcm", language))
    assert result == ASRResult(PHI, "intron", model=None, duration_seconds=2.5)
    assert ASRResult("text", "other").duration_seconds is None
    post, timeout = transport.calls[0]
    assert timeout == 15
    assert post.full_url == "https://infer.voice.intron.io/file/v1/upload"
    assert post.get_method() == "POST"
    assert all(req.get_header("Authorization") == f"Bearer {SECRET}" for req, _ in transport.calls)
    assert all(req.get_header("User-agent") == "EdgeIMCI/0.1" for req, _ in transport.calls)
    message = BytesParser(policy=default).parsebytes(
        f'Content-Type: {post.get_header("Content-type")}\r\nMIME-Version: 1.0\r\n\r\n'.encode() + post.data
    )
    parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
    assert set(parts) == {
        "audio_file_name", "audio_file_blob", "use_language_asr_input",
        "use_disable_llm_corrections", "use_diarization", "use_category",
    }
    for name, expected in {
        "audio_file_name": b"audio.wav", "use_language_asr_input": language.encode(),
        "use_disable_llm_corrections": b"TRUE", "use_diarization": b"FALSE",
        "use_category": b"file_category_general",
    }.items():
        assert parts[name].get_payload(decode=True) == expected
    assert parts["audio_file_blob"].get_payload(decode=True) == WAV
    assert parts["audio_file_blob"].get_filename() == "audio.wav"
    assert parts["audio_file_blob"].get_content_type() == "audio/x-wav"
    assert SECRET.encode() not in post.data
    get, _ = transport.calls[1]
    assert get.get_method() == "GET"
    assert get.full_url == "https://infer.voice.intron.io/file/v1/status/test-file-123"
    assert get.data is None


def test_missing_credentials_are_lazy():
    transport = Transport()
    provider = IntronSpeechProvider(urlopen=transport)
    IntronSpeechProvider()
    with pytest.raises(SpeechError, match="not configured"):
        provider.transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert not transport.calls


@pytest.mark.parametrize("environment_language", ["en", "sw"])
def test_language_is_explicit_per_request_and_environment_is_ignored(monkeypatch, environment_language):
    monkeypatch.setenv("INTRON_API_KEY", SECRET)
    monkeypatch.setenv("INTRON_LANGUAGE", environment_language)
    transport = Transport(uploaded(), completed(), uploaded(), completed())
    provider = IntronSpeechProvider(urlopen=transport, clock=transport.clock, sleep=transport.sleep)
    assert not transport.calls
    with pytest.raises(SpeechError, match="language"):
        provider.transcribe(AudioInput(WAV, "audio/wav"))
    assert not transport.calls
    assert provider.transcribe(AudioInput(WAV, "audio/wav", "yo")).model is None
    assert b'name="use_language_asr_input"\r\n\r\nyo\r\n' in transport.calls[0][0].data
    assert provider.transcribe(AudioInput(WAV, "audio/wav", "en")).model is None
    assert b'name="use_language_asr_input"\r\n\r\nen\r\n' in transport.calls[2][0].data
    assert len(transport.calls) == 4


@pytest.mark.parametrize("language", [None, "", "sw", "EN", " en ", "en\r\nInjected", 42, True, b"en", [], {}])
def test_missing_or_unsupported_language_never_uploaded(language):
    transport = Transport()
    with pytest.raises(SpeechError):
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", language))
    assert not transport.calls


@pytest.mark.parametrize("content_type,data", FORMATS)
def test_supported_containers(content_type, data):
    transport = Transport(uploaded(), completed())
    assert transport.provider().transcribe(AudioInput(data, content_type, "en")).transcript == PHI


@pytest.mark.parametrize("audio", [
    AudioInput(b"", "audio/wav", "en"),
    AudioInput(WAV + bytes(MAX_AUDIO_BYTES), "audio/wav", "en"),
    AudioInput(b"not audio", "audio/wav", "en"),
    AudioInput(WAV, "audio/mpeg", "en"),
    AudioInput(WAV, "text/plain", "en"),
    AudioInput(WAV, "audio/wav\r\nInjected: value", "en"),
    AudioInput(b"ID3" + bytes(20), "audio/mpeg", "en"),
    AudioInput(b"\xff\xf1\x50\x80", "audio/mpeg", "en"),  # AAC, not MPEG audio.
    AudioInput(b"\x00\x00\xff\xffftypM4A " + bytes(12), "audio/mp4", "en"),
    AudioInput(b"\x00\x00\x00\x18ftypavif" + bytes(12), "audio/mp4", "en"),
    AudioInput(b"\x1a\x45\xdf\xa3matroska" + bytes(20), "audio/webm", "en"),
    AudioInput(b"OggS\x01" + bytes(30), "audio/ogg", "en"),
    AudioInput(b"fLaC" + bytes(40), "audio/flac", "en"),
    AudioInput("not bytes", "audio/wav", "en"),
    AudioInput(WAV, None, "en"),
])
def test_invalid_input_never_uploaded(audio):
    transport = Transport()
    with pytest.raises(SpeechError, match="Audio|audio"):
        transport.provider().transcribe(audio)
    assert not transport.calls


def test_exact_size_limit_allowed():
    transport = Transport(uploaded(), completed())
    audio = AudioInput(WAV + bytes(MAX_AUDIO_BYTES - len(WAV)), "audio/wav", "en")
    assert transport.provider().transcribe(audio).provider == "intron"


def test_polling_documented_states_and_retry_after():
    transport = Transport(
        uploaded(headers={"Retry-After": "2"}),
        *(Response({"processing_status": status}) for status in ("FILE_QUEUED", "FILE_PENDING", "FILE_PROCESSING")),
        HTTPError("https://infer.voice.intron.io", 429, SECRET, {"Retry-After": "3"}, BytesIO(PHI.encode())),
        Response(status=503, headers={"Retry-After": "4"}),
        completed(),
    )
    assert transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en")).model is None
    assert transport.sleeps == [2, 1, 1, 1, 3, 4]
    assert [req.get_method() for req, _ in transport.calls] == ["POST"] + ["GET"] * 6


@pytest.mark.parametrize("retry_after", ["0", "-1", "NaN", "1.5", "Wed, 21 Oct 2015 07:28:00 GMT"])
def test_invalid_or_zero_retry_after_uses_moderate_interval(retry_after):
    transport = Transport(uploaded(headers={"Retry-After": retry_after}), completed())
    transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert transport.sleeps == [1]


@pytest.mark.parametrize("retry_after", ["9999999999", "9" * 100])
def test_retry_after_is_bounded_by_total_timeout(retry_after):
    transport = Transport(uploaded(headers={"Retry-After": retry_after}))
    with pytest.raises(SpeechError, match="timed out"):
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert transport.now == 90
    assert len(transport.calls) == 1


def test_pending_timeout_and_per_request_remaining_budget():
    transport = Transport(uploaded(), *(Response({"processing_status": "FILE_PENDING"}) for _ in range(100)))
    with pytest.raises(SpeechError, match="timed out"):
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert transport.now == 90
    assert transport.calls[-1][1] == 1
    assert all(0 < timeout <= 15 for _, timeout in transport.calls)
    assert sum(req.get_method() == "POST" for req, _ in transport.calls) == 1


@pytest.mark.parametrize("status", [301, 302, 307, 308, 400, 401, 403, 429, 500, 503])
def test_upload_errors_never_resubmit_or_leak(status):
    response = Response(raw=f"{SECRET} {PHI}".encode(), status=status, headers={"Retry-After": "1", "Location": "https://other.example"})
    transport = Transport(response)
    with pytest.raises(SpeechError) as caught:
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert SECRET not in str(caught.value) and PHI not in str(caught.value)
    assert response.bytes_read == 0 and response.closed
    assert len(transport.calls) == 1


@pytest.mark.parametrize("error", [URLError(f"{SECRET} {PHI}"), TimeoutError(PHI), ValueError(SECRET)])
def test_transport_exception_chain_is_suppressed(error, caplog, capsys):
    transport = Transport(error)
    with pytest.raises(SpeechError) as caught:
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert len(transport.calls) == 1
    rendered = "".join(traceback.format_exception(caught.value))
    assert SECRET not in rendered and PHI not in rendered
    assert not caplog.records
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("raw", [b"", b"not json", b"\xff", b"[]", b"null", b'{"status":"Error","data":{}}', b'{"status":"Ok","data":[]}'])
def test_malformed_envelopes_fail_closed(raw):
    transport = Transport(Response(raw=raw))
    with pytest.raises(SpeechError):
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert len(transport.calls) == 1


@pytest.mark.parametrize("file_id", [None, "", 42, "../../other", "https://other.example", "id?secret=key", "x" * 201])
def test_invalid_file_ids_not_followed(file_id):
    transport = Transport(Response({"file_id": file_id}))
    with pytest.raises(SpeechError):
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert len(transport.calls) == 1


@pytest.mark.parametrize("data", [
    {}, {"processing_status": "UNKNOWN"}, {"processing_status": "FILE_PROCESSING_FAILED", "message": PHI},
    {"processing_status": "FILE_TRANSCRIBED"},
    *({"processing_status": "FILE_TRANSCRIBED", "audio_transcript": text} for text in (None, "", "  ", 123, [])),
    *({"processing_status": "FILE_TRANSCRIBED", "audio_transcript": PHI, "processed_audio_duration_in_seconds": duration} for duration in (-1, True, "20", float("inf"), float("nan"))),
])
def test_invalid_status_results_fail_closed(data):
    transport = Transport(uploaded(), Response(data))
    with pytest.raises(SpeechError) as caught:
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert PHI not in str(caught.value)
    assert len(transport.calls) == 2


def test_response_size_limit_and_cleanup():
    response = Response(raw=b" " * 1_000_002)
    transport = Transport(response)
    with pytest.raises(SpeechError, match="invalid response"):
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert response.bytes_read == 1_000_001
    assert response.closed


@pytest.mark.parametrize("phase", ["upload", "status"])
def test_late_response_rejected(phase):
    transport = Transport()

    class LateResponse(Response):
        def read1(self, size=-1):
            transport.now += 90
            return super().read1(size)

    response = LateResponse({"file_id": "test-file-123"} if phase == "upload" else {
        "processing_status": "FILE_TRANSCRIBED", "audio_transcript": PHI,
    })
    transport.responses = [response] if phase == "upload" else [uploaded(), response]
    with pytest.raises(SpeechError, match="timed out"):
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert response.closed


def test_status_auth_error_is_not_retried():
    error_body = BytesIO(f"{SECRET} {PHI}".encode())
    transport = Transport(uploaded(), HTTPError(
        "https://infer.voice.intron.io", 401, SECRET, {}, error_body,
    ))
    with pytest.raises(SpeechError) as caught:
        transport.provider().transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert SECRET not in str(caught.value) and PHI not in str(caught.value)
    assert len(transport.calls) == 2
    assert error_body.closed


def test_invalid_configuration_is_safe():
    transport = Transport()
    provider = IntronSpeechProvider(api_key=SECRET + "\r\nX: value", urlopen=transport)
    with pytest.raises(SpeechError, match="configuration is invalid") as caught:
        provider.transcribe(AudioInput(WAV, "audio/wav", "en"))
    assert SECRET not in str(caught.value)
    assert not transport.calls


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_redirect_handler_never_forwards_credentials(code):
    request = Request("https://infer.voice.intron.io/file/v1/upload", headers={"Authorization": f"Bearer {SECRET}"})
    assert _NoRedirects().redirect_request(request, None, code, "redirect", {}, "https://other.example") is None
