from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from http.client import HTTPConnection
import json
import sys
from threading import Thread

import pytest

from app.api import make_server
from app.extractor.base import ExtractionError
from app.speech import ASRResult, AudioInput, SpeechError
from tests.test_assessment_workflow import QueueExtractor, empty_encounter, known_complete


class FakeSpeech:
    def __init__(self):
        self.calls = []
        self.result = ASRResult("Cough for three days, rate 42.", "local-fake", "test-model", 2.5)

    def transcribe(self, audio):
        self.calls.append(audio)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def api(monkeypatch, request):
    def forbidden_provider(*args, **kwargs):
        pytest.fail("Tests must not construct a paid/default provider")

    monkeypatch.setattr("app.api.create_default_service", forbidden_provider)
    monkeypatch.setattr("app.api.IntronSpeechProvider", forbidden_provider)
    monkeypatch.setenv("EDGEIMCI_ALLOWED_ORIGINS", getattr(request, "param", ""))
    extractor, speech = QueueExtractor(), FakeSpeech()
    server = make_server(port=0, extractor=extractor, speech_provider=speech)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def post(path, body, content_type="application/json", *, headers=None, raw_json=False):
        data = body if raw_json or not content_type.lower().startswith("application/json") else json.dumps(body).encode()
        request_headers = {"Host": f"127.0.0.1:{server.server_port}", "Content-Type": content_type}
        request_headers.update(headers or {})
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            connection.putrequest("POST", f"/api/{path}", skip_host=True)
            for name, values in request_headers.items():
                if values is not None:
                    for value in values if isinstance(values, list) else [values]:
                        connection.putheader(name, value)
            connection.putheader("Content-Length", str(len(data)))
            connection.endheaders(data)
            with connection.getresponse() as response:
                return response.status, json.load(response)
        finally:
            connection.close()

    post.port = server.server_port
    post.handler = server.RequestHandlerClass

    try:
        yield post, extractor, speech
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_transcribe_scoped_review_repeat_accept_completes_respiratory(api):
    post, extractor, speech = api
    audio = b"synthetic audio passed unchanged to the injected provider"
    status, transcript = post("transcribe", audio, "audio/webm;codecs=opus", headers={"X-EdgeIMCI-ASR-Language": "pcm"})
    assert status == 200 and transcript == asdict(speech.result)
    assert speech.calls == [AudioInput(audio, "audio/webm;codecs=opus", "pcm")]
    assert extractor.prompts == []

    accepted = empty_encounter()
    accepted["patient_facts"]["age_months"] = 18
    accepted["danger_signs"] = known_complete()["danger_signs"]
    first, second = empty_encounter(), empty_encounter()
    first["patient_facts"]["has_cough_or_difficult_breathing"] = True
    first["respiratory"].update(cough_duration_days=3, respiratory_rate=42)
    second["respiratory"] = known_complete()["respiratory"]
    extractor.encounters.extend([first, second])
    for index in range(2):
        before = deepcopy(accepted)
        status, current = post("assessment/evaluate", {"encounter": accepted})
        assert status == 200
        question = current["assessments"]["respiratory"]["question"]
        status, preview = post("assessment/extract", {
            "assessment": "respiratory", "encounter": accepted,
            "findings": transcript["transcript"] if index == 0 else "Calm, counted a full minute; no indrawing, stridor or wheeze. No oximeter.",
            "question_field": question["field"],
        })
        assert status == 200 and preview["changes"]
        assert preview["assessment"] == "respiratory"
        assert preview["extraction_mode"] == extractor.mode_label
        assert "analysis" not in preview and "encounter" not in preview
        assert all(not change["conflict"] and not change["outside_assessment"] for change in preview["changes"])
        assert accepted == before
        status, unchanged = post("assessment/evaluate", {"encounter": accepted})
        assert status == 200 and unchanged == current
        body = {"assessment": "respiratory", "encounter": accepted, "changes": preview["changes"]}
        status, error = post("assessment/accept", {**body, "confirmed": False})
        assert status == 422 and "confirmation" in error["error"]
        status, result = post("assessment/accept", {**body, "confirmed": True})
        assert status == 200
        accepted = result["encounter"]
        assert result["assessments"]["respiratory"]["status"] == ("INCOMPLETE" if index == 0 else "COMPLETE")
    assert accepted["respiratory"] == known_complete()["respiratory"]
    assert accepted["patient_facts"]["has_fever"] is None
    assert result["analysis"]["state"] == "INCOMPLETE"  # Unrelated entries still unknown.
    assert result["assessments"]["respiratory"]["question"] is None
    assert len(extractor.prompts) == 2 and not extractor.encounters


@pytest.mark.parametrize("language", ["en", "pcm", "yo", "ig", "ha"])
def test_http_transcribe_propagates_language(api, language):
    post, extractor, speech = api
    status, transcript = post("transcribe", b"audio", "audio/wav",
                              headers={"X-EdgeIMCI-ASR-Language": language})
    assert status == 200 and transcript == asdict(speech.result)
    assert speech.calls == [AudioInput(b"audio", "audio/wav", language)]
    assert extractor.prompts == []


@pytest.mark.parametrize("language", [None, "", "sw", "EN", "en,pcm", "42"])
def test_http_transcribe_requires_language_before_body_or_providers(api, monkeypatch, language):
    post, extractor, speech = api
    body_reads = []

    def forbidden_body_read(self, limit):
        body_reads.append(limit)
        self._send_json({"error": "Unexpected body read."}, 500)
        return None

    monkeypatch.setenv("INTRON_LANGUAGE", "en")
    monkeypatch.setattr(post.handler, "_read_body", forbidden_body_read)
    status, error = post("transcribe", b"audio", "audio/wav",
                         headers={"X-EdgeIMCI-ASR-Language": language})
    assert status == 400 and "before transcription" in error["error"]
    assert body_reads == [] and speech.calls == [] and extractor.prompts == []


def test_http_errors_are_safe_and_do_not_change_accepted_encounter(api):
    post, extractor, speech = api
    accepted = known_complete()
    before = deepcopy(accepted)
    status, _ = post("assessment/evaluate", [])
    assert status == 400
    for invalid in ({"diagnosis": "PNEUMONIA"}, [], "not an encounter"):
        status, error = post("assessment/evaluate", {"encounter": invalid})
        assert status == 422 and error["error"]
    extractor.encounters.extend([
        {"diagnosis": "PNEUMONIA"}, ExtractionError("private provider details"),
        RuntimeError("private provider details"),
    ])
    body = {"assessment": "respiratory", "encounter": accepted, "findings": "Repeat assessment."}
    status, error = post("assessment/extract", body)
    assert status == 503 and "diagnosis" not in error["error"]
    for _ in range(2):
        status, error = post("assessment/extract", body)
        assert status == 503 and "private provider details" not in error["error"]
    for failure in (SpeechError("Speech unavailable. Enter text instead."), RuntimeError("private speech details")):
        speech.result = failure
        status, error = post("transcribe", b"audio", "audio/wav", headers={"X-EdgeIMCI-ASR-Language": "en"})
        assert status == 503 and "private speech details" not in error["error"]
        assert "text" in error["error"]
    assert speech.calls == [AudioInput(b"audio", "audio/wav", "en")] * 2
    status, result = post("assessment/evaluate", {"encounter": accepted})
    assert status == 200 and result["encounter"] == before
    assert result["analysis"]["state"] == "COMPLETE"
    assert accepted == before


JSON_ROUTES = (
    "extract", "analyze", "evaluate", "assessment/extract",
    "assessment/evaluate", "assessment/accept",
)


@pytest.mark.parametrize("headers", [
    {"Origin": "https://attacker.example"},
    {"Origin": "null"},
    {"Origin": ""},
    {"Origin": "http://localhost:5173.attacker.example"},
    {"Origin": "http://localhost:5173/"},
    {"Origin": ["http://localhost:5173", "https://attacker.example"]},
    {"Sec-Fetch-Site": "cross-site"},
    {"Origin": "http://localhost:5173", "Sec-Fetch-Site": "cross-site"},
    {"Host": None},
    {"Host": ""},
    {"Host": ["localhost:5173", "localhost:5173"]},
    {"Host": "attacker.example", "Origin": "http://attacker.example"},
    {"Host": "localhost:5173.attacker.example"},
    {"Host": "localhost:1"},
    {"Host": "localhost:5173, attacker.example"},
])
def test_untrusted_posts_are_rejected_before_body_or_providers(api, monkeypatch, headers):
    post, extractor, speech = api
    # Reading even a single byte would produce 400, rather than the boundary's 403.
    monkeypatch.setattr("app.api.MAX_REQUEST_BYTES", 0)
    monkeypatch.setattr("app.api.MAX_AUDIO_BYTES", 0)
    for path in (*JSON_ROUTES, "transcribe", "unknown"):
        status, error = post(path, b"{}", headers={"X-EdgeIMCI-ASR-Language": "en", **headers}, raw_json=True)
        assert status == 403 and error["error"]
    assert extractor.prompts == [] and speech.calls == []


@pytest.mark.parametrize("content_type", [
    None, "text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=test",
    "application/jsonp", ["application/json", "text/plain"],
])
def test_json_routes_require_json_content_type_before_body(api, monkeypatch, content_type):
    post, extractor, speech = api
    monkeypatch.setattr("app.api.MAX_REQUEST_BYTES", 0)
    for path in JSON_ROUTES:
        status, error = post(path, b'{"findings":"Repeat assessment."}',
                             headers={"Content-Type": content_type}, raw_json=True)
        assert status == 415 and error["error"]
    assert extractor.prompts == [] and speech.calls == []


def test_local_origins_and_exact_hosts_allow_provider_calls(api):
    post, extractor, speech = api
    origins = (
        f"http://localhost:{post.port}", f"http://127.0.0.1:{post.port}",
        "http://localhost:5173", "http://127.0.0.1:5173",
    )
    for origin in origins:
        headers = {"Origin": origin, "Sec-Fetch-Site": "same-site", "X-EdgeIMCI-ASR-Language": "en"}
        status, transcript = post("transcribe", b"audio", "audio/wav", headers=headers)
        assert status == 200 and transcript == asdict(speech.result)
        headers["Host"] = origin.removeprefix("http://")
        extractor.encounters.append(empty_encounter())
        status, preview = post("assessment/extract", {
            "assessment": "respiratory", "encounter": empty_encounter(), "findings": "Repeat assessment.",
        }, "Application/JSON; charset=utf-8", headers=headers)
        assert status == 200 and preview["assessment"] == "respiratory"
    assert len(extractor.prompts) == len(speech.calls) == len(origins)


@pytest.mark.parametrize("api", [" https://clinic.example, http://clinic.example:8080 "], indirect=True)
def test_explicit_deployment_origins_and_hosts(api, monkeypatch):
    post, extractor, speech = api
    # The allowlist is captured at construction, not changed by requests or later env edits.
    monkeypatch.setenv("EDGEIMCI_ALLOWED_ORIGINS", "https://attacker.example")
    for origin, host in (("https://clinic.example", "clinic.example"), ("http://clinic.example:8080", "clinic.example:8080")):
        status, _ = post("transcribe", b"audio", "audio/wav", headers={"Origin": origin, "Host": host, "X-EdgeIMCI-ASR-Language": "en"})
        assert status == 200
    for headers in (
        {"Origin": "http://clinic.example", "Host": "clinic.example"},
        {"Origin": "https://attacker.example", "Host": "attacker.example"},
        {"Origin": "https://clinic.example", "Host": "clinic.example:443"},
    ):
        status, _ = post("transcribe", b"audio", "audio/wav", headers={"X-EdgeIMCI-ASR-Language": "en", **headers})
        assert status == 403
    assert len(speech.calls) == 2 and extractor.prompts == []


@pytest.mark.parametrize("origin", [
    "*", "https://*.example", "null", "clinic.example", "ftp://clinic.example",
    "https://", "https://clinic.example/", "https://clinic.example/path",
    "https://clinic.example?", "https://clinic.example#", "https://user:pass@clinic.example",
    "https://clinic.example:invalid", "https://clinic.example:65536", "https://clinic.example:",
    "https://clinic.example,", "https://clinic.example,,http://localhost:5173",
    "https://clinic.example\n.evil", "https://clinic.example\\evil", " ", "https://[invalid",
])
def test_invalid_origin_config_fails_before_provider_construction(monkeypatch, origin):
    def forbidden_provider(*args, **kwargs):
        pytest.fail("Invalid configuration must fail before constructing providers")

    monkeypatch.setenv("EDGEIMCI_ALLOWED_ORIGINS", origin)
    monkeypatch.setattr("app.api.create_default_service", forbidden_provider)
    monkeypatch.setattr("app.api.IntronSpeechProvider", forbidden_provider)
    with pytest.raises(ValueError, match="EDGEIMCI_ALLOWED_ORIGINS"):
        make_server(port=0)


@pytest.mark.parametrize("raw_json", [
    b'{"private":', b'{"private":"\xff"}',
    b'{"findings":"first","findings":"second"}',
    b'{"nested":{"private":1,"private":2}}',
    b'{"nested":[{"private":1,"private":2}]}',
    b'{"private":NaN}', b'{"private":Infinity}', b'{"private":-Infinity}',
    b'{"private":1e9999}', b'{"private":-1e9999}',
    b'{"private":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}',
    b'{"private":' + b'9' * max(10000, sys.get_int_max_str_digits() + 1) + b'}',
], ids=["syntax", "encoding", "duplicate", "nested-duplicate", "array-duplicate",
        "nan", "infinity", "negative-infinity", "overflow", "negative-overflow", "depth", "huge-int"])
def test_malformed_json_returns_safe_400_without_provider_calls(api, raw_json):
    post, extractor, speech = api
    for path in JSON_ROUTES:
        status, error = post(path, raw_json, raw_json=True)
        assert status == 400
        assert error == {"error": "Request body must be valid JSON."}
    assert extractor.prompts == [] and speech.calls == []
