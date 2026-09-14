"""Small HTTP boundary for the EdgeIMCI prototype application."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
import os
import shlex
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from app.assessment import AssessmentError, accept_assessment, evaluate_assessment, extract_assessment
from app.extractor.base import ExtractionError
from app.language_understanding import (
    ExistingExtractorLanguageUnderstandingProvider,
    FrontierApiLanguageUnderstandingProvider,
    LanguageUnderstandingProvider,
)
from app.speech import AudioInput, INTRON_LANGUAGES, IntronSpeechProvider, MAX_AUDIO_BYTES, SpeechError, SpeechProvider
from app.service import (
    AnalysisResult,
    ExtractionPreview,
    PipelineStep,
    analyze_freeform_findings,
    create_default_service,
    evaluate_extracted_findings,
    extract_freeform_findings,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATIC_ROOT = ROOT / "web" / "dist"
MAX_REQUEST_BYTES = 1_000_000


def result_payload(result: AnalysisResult | ExtractionPreview) -> dict[str, Any]:
    """Serialize the application result without exposing clinical internals."""

    payload = asdict(result)
    payload["state"] = result.state
    return payload


def _handler_class(
    extractor: Any,
    examples: list[dict[str, str]],
    static_root: Path,
    speech_provider: SpeechProvider,
    configured_origins: set[str],
    language_provider: LanguageUnderstandingProvider,
) -> type[BaseHTTPRequestHandler]:
    class EdgeIMCIRequestHandler(BaseHTTPRequestHandler):
        server_version = "EdgeIMCI/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Allow", "GET, POST, OPTIONS")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/health":
                self._send_json({"status": "ok", "mode": extractor.mode_label,
                                 "language_understanding": {"mode": language_provider.mode_label}})
                return
            if path == "/api/examples":
                self._send_json({"examples": examples})
                return
            if path.startswith("/api/"):
                self._send_json({"error": "API route not found."}, HTTPStatus.NOT_FOUND)
                return
            self._serve_static(path)

        def do_POST(self) -> None:  # noqa: N802
            if not self._trusted_request():
                return
            path = urlparse(self.path).path
            if path == "/api/transcribe":
                language = self.headers.get("X-EdgeIMCI-ASR-Language", "")
                if language not in INTRON_LANGUAGES:
                    self._send_json(
                        {"error": "Select English, Nigerian Pidgin-English, Yoruba-English, Igbo-English, or Hausa-English before transcription."},
                        HTTPStatus.BAD_REQUEST,
                    )
                    return
                audio = self._read_body(MAX_AUDIO_BYTES)
                if audio is None:
                    return
                try:
                    transcript = speech_provider.transcribe(AudioInput(
                        audio, self.headers.get("Content-Type", ""), language,
                    ))
                    self._send_json(asdict(transcript))
                except SpeechError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
                except Exception:
                    self._send_json({"error": "Speech transcription failed. You can enter text instead."}, HTTPStatus.SERVICE_UNAVAILABLE)
                return
            if path not in {
                "/api/extract", "/api/evaluate", "/api/analyze",
                "/api/assessment/extract", "/api/assessment/evaluate", "/api/assessment/accept",
            }:
                self._send_json({"error": "API route not found."}, HTTPStatus.NOT_FOUND)
                return

            body = self._read_json_body()
            if body is None:
                return

            if path.startswith("/api/assessment/"):
                try:
                    if path.endswith("/extract"):
                        payload = extract_assessment(body, language_provider)
                    elif path.endswith("/accept"):
                        payload = accept_assessment(body)
                    else:
                        payload = evaluate_assessment(body)
                    self._send_json(payload)
                except AssessmentError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.UNPROCESSABLE_ENTITY)
                except ExtractionError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
                except Exception:
                    self._send_json({"error": "The assessment could not be processed. Accepted findings are unchanged."}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path == "/api/evaluate":
                try:
                    preview = ExtractionPreview(
                        input_text=body["input_text"],
                        extraction_mode=body["extraction_mode"],
                        matched_case_id=body.get("matched_case_id"),
                        structured_encounter=body["structured_encounter"],
                        schema_valid=bool(body.get("schema_valid")),
                        structured_view=[
                            tuple(row) for row in body.get("structured_view", [])
                        ],
                        extraction_warnings=list(body.get("extraction_warnings", [])),
                        pipeline_trace=[
                            PipelineStep(**step)
                            for step in body.get("pipeline_trace", [])
                        ],
                        error=body.get("error"),
                        outside_supported_scope=bool(
                            body.get("outside_supported_scope")
                        ),
                    )
                except (KeyError, TypeError, ValueError):
                    self._send_json(
                        {
                            "error": "Request body does not contain a valid extraction preview."
                        },
                        HTTPStatus.BAD_REQUEST,
                    )
                    return
                self._send_json(result_payload(evaluate_extracted_findings(preview)))
                return

            if not isinstance(body.get("findings"), str):
                self._send_json(
                    {
                        "error": "Request body must contain a string field named 'findings'."
                    },
                    HTTPStatus.BAD_REQUEST,
                )
                return

            if path == "/api/extract":
                preview = extract_freeform_findings(
                    body["findings"], extractor=extractor
                )
                self._send_json(result_payload(preview))
                return

            result = analyze_freeform_findings(body["findings"], extractor=extractor)
            self._send_json(result_payload(result))

        def _trusted_request(self) -> bool:
            # Use the bound port, never the untrusted Host, to establish local origins.
            port = self.server.server_port
            origins = configured_origins | {
                f"http://127.0.0.1:{port}", f"http://localhost:{port}",
                "http://localhost:5173", "http://127.0.0.1:5173",
            }
            hosts = {urlparse(origin).netloc for origin in origins}
            request_hosts = self.headers.get_all("Host", [])
            request_origins = self.headers.get_all("Origin", [])
            if (
                len(request_hosts) != 1 or request_hosts[0] not in hosts
                or (request_origins and (len(request_origins) != 1 or request_origins[0] not in origins))
                or any(value.strip().lower() == "cross-site" for value in self.headers.get_all("Sec-Fetch-Site", []))
            ):
                self._send_json({"error": "Request origin or host is not trusted."}, HTTPStatus.FORBIDDEN)
                return False
            return True

        def _read_body(self, maximum: int) -> bytes | None:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(
                    {"error": "Invalid Content-Length."}, HTTPStatus.BAD_REQUEST
                )
                return None
            if self.headers.get("Transfer-Encoding") or content_length <= 0 or content_length > maximum:
                self._send_json(
                    {"error": f"Request body must have a Content-Length between 1 and {maximum} bytes."},
                    HTTPStatus.BAD_REQUEST,
                )
                return None
            self.connection.settimeout(15)
            try:
                content = self.rfile.read(content_length)
            except OSError:
                self._send_json({"error": "Request upload timed out."}, HTTPStatus.REQUEST_TIMEOUT)
                return None
            if len(content) != content_length:
                self._send_json({"error": "Incomplete request upload."}, HTTPStatus.BAD_REQUEST)
                return None
            return content

        def _read_json_body(self) -> dict[str, Any] | None:
            content_types = self.headers.get_all("Content-Type", [])
            if len(content_types) != 1 or content_types[0].split(";", 1)[0].strip().lower() != "application/json":
                self._send_json({"error": "Content-Type must be application/json."}, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
                return None
            content = self._read_body(MAX_REQUEST_BYTES)
            if content is None:
                return None

            def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate JSON key")
                    result[key] = value
                return result

            def finite_float(value: str) -> float:
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError("Non-finite JSON number")
                return number

            try:
                body = json.loads(content, object_pairs_hook=unique_object,
                                  parse_constant=finite_float, parse_float=finite_float)
            except (ValueError, UnicodeDecodeError, RecursionError):
                self._send_json(
                    {"error": "Request body must be valid JSON."},
                    HTTPStatus.BAD_REQUEST,
                )
                return None
            if not isinstance(body, dict):
                self._send_json(
                    {"error": "Request body must be a JSON object."},
                    HTTPStatus.BAD_REQUEST,
                )
                return None
            return body

        def _serve_static(self, request_path: str) -> None:
            if not static_root.is_dir():
                self._send_json(
                    {
                        "error": "Frontend build not found.",
                        "detail": "Run 'npm run build' in web/ or use the Vite development server.",
                    },
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return

            relative = unquote(request_path).lstrip("/") or "index.html"
            candidate = (static_root / relative).resolve()
            if not candidate.is_relative_to(static_root.resolve()):
                self._send_json({"error": "Invalid path."}, HTTPStatus.BAD_REQUEST)
                return
            if not candidate.is_file():
                candidate = static_root / "index.html"

            content_type, _ = mimetypes.guess_type(candidate.name)
            content = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Cache-Control",
                "no-cache"
                if candidate.name == "index.html"
                else "public, max-age=31536000, immutable",
            )
            self.end_headers()
            self.wfile.write(content)

        def _send_json(
            self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK
        ) -> None:
            content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, message: str, *args: Any) -> None:
            print(f"{self.address_string()} - {message % args}")

    return EdgeIMCIRequestHandler


def make_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    static_root: Path = DEFAULT_STATIC_ROOT,
    extractor: Any | None = None,
    examples: list[dict[str, str]] | None = None,
    extractor_mode: str | None = None,
    speech_provider: SpeechProvider | None = None,
    language_provider: LanguageUnderstandingProvider | None = None,
    language_understanding_mode: str = "native",
) -> ThreadingHTTPServer:
    configured_origins = set()
    origin_config = os.environ.get("EDGEIMCI_ALLOWED_ORIGINS", "")
    if origin_config:
        for entry in origin_config.split(","):
            origin = entry.strip()
            try:
                parsed = urlparse(origin)
                if (
                    parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None
                    or origin != f"{parsed.scheme}://{parsed.netloc}"
                    or any(char.isspace() or ord(char) < 32 for char in origin)
                    or any(char in origin for char in "*\\")
                    or parsed.netloc.endswith(":")
                ):
                    raise ValueError("Invalid origin")
                parsed.port  # Validate the optional port as well as the hostname.
            except ValueError:
                raise ValueError("EDGEIMCI_ALLOWED_ORIGINS must contain only explicit http/https origins without paths or credentials.") from None
            configured_origins.add(origin)
    if extractor is None:
        extractor, configured_examples = create_default_service(extractor_mode)
        if examples is None:
            examples = configured_examples
    elif examples is None:
        examples = []
    if language_provider is None:
        if language_understanding_mode == "frontier":
            language_provider = FrontierApiLanguageUnderstandingProvider()
        elif language_understanding_mode == "native":
            language_provider = ExistingExtractorLanguageUnderstandingProvider(extractor)
        else:
            raise ValueError("Unsupported language-understanding mode.")
    handler = _handler_class(extractor, examples, static_root, speech_provider or IntronSpeechProvider(), configured_origins, language_provider)
    return ThreadingHTTPServer((host, port), handler)


def load_environment(path: Path) -> None:
    """Read explicitly supported dotenv settings without shell execution or logs."""
    try:
        if path.stat().st_mode & 0o077:
            raise ValueError("Restrict the environment file to its owner with chmod 600 before starting.")
        allowed = {"INTRON_API_KEY", "EDGEIMCI_FRONTIER_API_KEY", "EDGEIMCI_FRONTIER_ENDPOINT", "EDGEIMCI_FRONTIER_MODEL"}
        values = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.strip().removeprefix("export ").partition("=")
            name = name.strip()
            if separator and name in allowed:
                parsed = shlex.split(value, comments=True)
                if name in values or len(parsed) != 1 or not parsed[0]:
                    raise ValueError("The environment file contains an empty or repeated supported setting.")
                values[name] = parsed[0]
        if "INTRON_API_KEY" not in values:
            raise ValueError("The environment file must contain one nonempty INTRON_API_KEY entry.")
        os.environ.update(values)
    except (OSError, UnicodeError):
        raise ValueError("The environment file could not be read.") from None
    except ValueError as exc:
        # shlex errors never include input, but use a fixed message for malformed quotes.
        if str(exc) in {"No closing quotation", "No escaped character"}:
            raise ValueError("The environment file contains an invalid quoted value.") from None
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve the EdgeIMCI prototype application."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--env-file", type=Path, help="Load speech/frontier settings from an owner-only dotenv file.")
    parser.add_argument("--language-understanding", choices=("frontier", "native"),
                        default="frontier", help="Scoped understanding provider; frontier is the demo bypass.")
    parser.add_argument(
        "--extractor",
        choices=("stub", "modal"),
        default=os.environ.get("EDGEIMCI_EXTRACTOR", "modal"),
        help="Extraction backend; defaults to EDGEIMCI_EXTRACTOR or modal.",
    )
    args = parser.parse_args()
    if args.env_file:
        try:
            load_environment(args.env_file)
        except ValueError as exc:
            parser.error(str(exc))

    server = make_server(args.host, args.port, extractor_mode=args.extractor,
                         language_understanding_mode=args.language_understanding)
    print(f"EdgeIMCI available at http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
