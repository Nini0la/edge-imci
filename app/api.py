"""Small HTTP boundary for the EdgeIMCI prototype application."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

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
                self._send_json({"status": "ok", "mode": extractor.mode_label})
                return
            if path == "/api/examples":
                self._send_json({"examples": examples})
                return
            if path.startswith("/api/"):
                self._send_json({"error": "API route not found."}, HTTPStatus.NOT_FOUND)
                return
            self._serve_static(path)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path not in {"/api/extract", "/api/evaluate", "/api/analyze"}:
                self._send_json({"error": "API route not found."}, HTTPStatus.NOT_FOUND)
                return

            body = self._read_json_body()
            if body is None:
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

        def _read_json_body(self) -> dict[str, Any] | None:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(
                    {"error": "Invalid Content-Length."}, HTTPStatus.BAD_REQUEST
                )
                return None
            if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
                self._send_json(
                    {"error": "Request body must be between 1 byte and 1 MB."},
                    HTTPStatus.BAD_REQUEST,
                )
                return None

            try:
                body = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
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
) -> ThreadingHTTPServer:
    if extractor is None:
        extractor, configured_examples = create_default_service(extractor_mode)
        if examples is None:
            examples = configured_examples
    elif examples is None:
        examples = []
    handler = _handler_class(extractor, examples, static_root)
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve the EdgeIMCI prototype application."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument(
        "--extractor",
        choices=("stub", "modal"),
        default=os.environ.get("EDGEIMCI_EXTRACTOR", "modal"),
        help="Extraction backend; defaults to EDGEIMCI_EXTRACTOR or modal.",
    )
    args = parser.parse_args()

    server = make_server(args.host, args.port, extractor_mode=args.extractor)
    print(f"EdgeIMCI available at http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
