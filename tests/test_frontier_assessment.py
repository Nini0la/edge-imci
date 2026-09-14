"""Offline transcript-only integration; injected evidence is not model accuracy."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from http.client import HTTPConnection
import json
import sys
from threading import Thread
from unittest.mock import Mock

import pytest

from app.api import make_server, result_payload
from app.assessment import AssessmentError, accept_assessment, evaluate_assessment, extract_assessment
from app.language_understanding import CanonicalEvidenceCandidate, FRONTIER_PROMPT_VERSION, LanguageUnderstandingProvider
from app.service import ExtractionPreview, evaluate_extracted_findings
from scripts import check_frontier_demo as demo
from tests.test_assessment_workflow import QueueExtractor, empty_encounter


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline tests must not construct a live provider")

    for name in ("create_default_service", "FrontierApiLanguageUnderstandingProvider", "IntronSpeechProvider"):
        monkeypatch.setattr("app.api." + name, forbidden)
    monkeypatch.setitem(sys.modules, "openai", None)
    monkeypatch.setitem(sys.modules, "azure.identity", None)
    monkeypatch.setenv("EDGEIMCI_ALLOWED_ORIGINS", "")


def candidate(values, transcript, *, english=None, uncertainties=()):
    return CanonicalEvidenceCandidate(
        canonical_evidence=demo.with_values(empty_encounter(), values),
        english_rendering=transcript if english is None else english,
        warnings=("Review these synthetic observations.",),
        uncertainties=uncertainties,
        evidence_spans=tuple({"field": field, "source_text": transcript} for field in values),
        provider="azure-openai", model="offline-fixture", request_id="req-offline-123",
        prompt_version=FRONTIER_PROMPT_VERSION,
        usage={"input_tokens": 100, "output_tokens": 80, "total_tokens": 180},
    )


def provider_for(*candidates):
    provider = Mock(spec=LanguageUnderstandingProvider)
    provider.mode_label = "azure-openai/offline-fixture"
    provider.understand.side_effect = candidates
    return provider


def review(encounter, preview, *, assessment="respiratory", resolutions=None):
    return accept_assessment({
        "assessment": assessment, "encounter": encounter, "confirmed": True,
        "changes": preview["changes"], "resolutions": resolutions or {},
    })


def test_prerequisites_need_explicit_outside_choices_and_do_not_invent_respiratory():
    accepted = empty_encounter()
    evidence = candidate(demo.PREREQUISITES, demo.PREREQUISITES_REPORT)
    provider = provider_for(evidence)
    preview = extract_assessment({"assessment": "danger", "encounter": accepted,
                                  "findings": demo.PREREQUISITES_REPORT}, provider)
    demo.check_synthetic_proposal(preview, demo.PREREQUISITES)
    outside = {row["field"] for row in preview["changes"] if row["outside_assessment"]}
    assert outside == {"patient_facts.has_diarrhoea", "patient_facts.has_fever", "patient_facts.has_ear_problem"}
    tampered = {**preview, "changes": [{**row, "outside_assessment": False} for row in preview["changes"]]}
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        review(accepted, tampered, assessment="danger")
    result = review(accepted, preview, assessment="danger", resolutions={field: "replace" for field in outside})
    assert result["encounter"] == demo.with_values(accepted, demo.PREREQUISITES)
    assert result["encounter"]["patient_facts"]["has_cough_or_difficult_breathing"] is None
    assert all(value is None for value in result["encounter"]["respiratory"].values())
    assert result["assessments"]["danger"]["status"] == "COMPLETE"
    assert result["analysis"]["state"] == "INCOMPLETE"
    assert accepted == empty_encounter()


@pytest.mark.parametrize("report,answer", [
    (demo.ENGLISH_REPORT, "No"),
    (demo.YORUBA_REPORT, "R\u00e1r\u00e1, k\u00f2 s\u00ed."),
], ids=["english", "yoruba-english"])
def test_report_review_context_only_stridor_followup_and_unchanged_engine(report, answer):
    baseline = demo.with_values(empty_encounter(), demo.PREREQUISITES)
    evidence = candidate(demo.RESPIRATORY, report, english=demo.ENGLISH_REPORT)
    followup = candidate({demo.STRIDOR: False}, answer, english="No.")
    evidence_before, baseline_before = asdict(evidence), deepcopy(baseline)
    provider = provider_for(evidence, followup)
    body = {"assessment": "respiratory", "encounter": baseline, "findings": "  " + report + "\n"}
    preview = extract_assessment(body, provider)
    provider.understand.assert_called_once_with(
        report, {"assessment": "respiratory", "id": "respiratory"}, None, baseline,
    )
    assert provider.understand.call_args.args[3] is not baseline
    demo.check_synthetic_proposal(preview, demo.RESPIRATORY)
    assert preview["candidate_encounter"] == evidence.canonical_evidence
    assert preview["candidate_encounter"] is not evidence.canonical_evidence
    assert preview["input_text"] == report
    assert preview["english_rendering"] == demo.ENGLISH_REPORT
    assert preview["evidence_spans"] == list(evidence.evidence_spans)
    assert all(span["source_text"] in report for span in preview["evidence_spans"])
    assert preview["uncertainties"] == []
    assert preview["warnings"][-1] == evidence.warnings[0]
    assert preview["understanding"] == {
        key: evidence_before[key] for key in ("provider", "model", "request_id", "prompt_version", "usage")
    }
    assert "analysis" not in preview and "encounter" not in preview
    assert evaluate_assessment({"encounter": baseline})["analysis"]["state"] == "INCOMPLETE"
    with pytest.raises(AssessmentError, match="confirmation"):
        accept_assessment({**body, "changes": preview["changes"], "confirmed": False})
    partial = review(baseline, preview)
    progress = partial["assessments"]["respiratory"]
    assert progress["status"] == "INCOMPLETE" and progress["decision"] == "ASK"
    assert progress["missing_fields"] == [demo.STRIDOR]
    assert progress["question"] == {"field": demo.STRIDOR, "text": "Is there stridor when the child is calm?"}
    assert partial["analysis"]["state"] == "INCOMPLETE"
    followup_body = {"assessment": "respiratory", "encounter": partial["encounter"],
                     "findings": answer, "question_field": demo.STRIDOR}
    with pytest.raises(AssessmentError, match="question is stale"):
        extract_assessment({**followup_body, "question_field": "respiratory.wheezing"}, provider)
    assert provider.understand.call_count == 1
    answered = extract_assessment(followup_body, provider)
    provider.understand.assert_called_with(
        answer, {"assessment": "respiratory", "id": "respiratory"}, progress["question"], partial["encounter"],
    )
    demo.check_synthetic_proposal(answered, {demo.STRIDOR: False})
    assert answered["candidate_encounter"]["patient_facts"]["age_months"] is None
    assert answered["candidate_encounter"]["danger_signs"]["vomits_everything"] is None
    assert answered["candidate_encounter"]["respiratory"]["respiratory_rate"] is None
    assert answered["candidate_encounter"]["respiratory"]["child_calm"] is None
    assert answered["candidate_encounter"]["respiratory"]["breaths_counted_one_minute"] is None
    final = review(partial["encounter"], answered)
    expected = demo.with_values(baseline, {**demo.RESPIRATORY, demo.STRIDOR: False})
    reference = evaluate_extracted_findings(ExtractionPreview(
        input_text="Worker-reviewed assessment evidence", extraction_mode="reviewed-assessment-evidence",
        matched_case_id=None, structured_encounter=expected, schema_valid=True,
    ))
    assert final["encounter"] == expected
    assert final["analysis"] == result_payload(reference)
    assert final["analysis"]["classifications"] == ["Pneumonia"]
    assert final["analysis"]["state"] == "COMPLETE" and not final["analysis"]["is_urgent"]
    assert all(item["status"] == "COMPLETE" and item["question"] is None for item in final["assessments"].values())
    assert baseline == baseline_before and asdict(evidence) == evidence_before
    with pytest.raises(AssessmentError, match="question is stale"):
        extract_assessment({**followup_body, "encounter": final["encounter"]}, provider)
    assert provider.understand.call_count == 2
    preview["candidate_encounter"]["respiratory"]["respiratory_rate"] = 99
    final["encounter"]["respiratory"]["respiratory_rate"] = 99
    assert asdict(evidence) == evidence_before and baseline == baseline_before


def test_provider_receives_isolated_current_encounter_even_if_it_mutates_context():
    accepted = demo.with_values(empty_encounter(), demo.PREREQUISITES)
    before = deepcopy(accepted)
    evidence = candidate({}, "Not sure.")
    provider = provider_for()

    def understand(transcript, assessment, question, current):
        assert current == before and current is not accepted
        current["patient_facts"]["age_months"] = 59
        return evidence

    provider.understand.side_effect = understand
    preview = extract_assessment({"assessment": "respiratory", "encounter": accepted,
                                  "findings": "Not sure."}, provider)
    assert preview["changes"] == [] and accepted == before
    assert preview["candidate_encounter"] == empty_encounter()


@pytest.mark.parametrize("old_value", [None, False, True])
def test_uncertainty_null_requires_explicit_choice_never_silent_keep(old_value):
    field = demo.STRIDOR
    accepted = demo.with_values(empty_encounter(), {**demo.PREREQUISITES, **demo.RESPIRATORY, field: old_value})
    before = deepcopy(accepted)
    uncertainty = ({"field": field, "source_text": "Not sure about stridor.", "reason": "Not assessed reliably."},)
    evidence = candidate({}, "Not sure about stridor.", uncertainties=uncertainty)
    preview = extract_assessment({"assessment": "respiratory", "encounter": accepted,
                                  "findings": "Not sure about stridor."}, provider_for(evidence))
    row, = preview["changes"]
    assert row["field"] == field and row["value"] is None and row["uncertain"] is True
    assert row["previous"] is old_value and row["conflict"] is (old_value is not None)
    assert preview["uncertainties"] == list(uncertainty)
    assert preview["candidate_encounter"]["respiratory"]["stridor_when_calm"] is None
    tampered = {**preview, "changes": [{**row, "uncertain": False, "conflict": False, "outside_assessment": False}]}
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        review(accepted, tampered)
    kept = review(accepted, preview, resolutions={field: "keep"})
    assert kept["encounter"] == before
    for choice in ("unknown", "replace"):
        result = review(accepted, preview, resolutions={field: choice})
        assert result["encounter"]["respiratory"]["stridor_when_calm"] is None
        assert result["assessments"]["respiratory"]["status"] == "INCOMPLETE"
        assert result["assessments"]["respiratory"]["question"]["field"] == field
        assert result["analysis"]["state"] == "INCOMPLETE"
    assert accepted == before


@pytest.mark.parametrize("report,assessment,uncertainties", [
    (demo.VOMITING_REPORT, "danger", (
        {"field": "danger_signs.vomits_everything", "source_text": "vomiting", "reason": "Not stated to vomit everything."},
        {"field": None, "source_text": "since yesterday", "reason": "No canonical vomiting duration; do not normalize relative time."},
    )),
    ("The child has a cough since yesterday.", "respiratory", (
        {"field": "respiratory.cough_duration_days", "source_text": "since yesterday", "reason": "Relative time is not a numeric duration."},
    )),
], ids=["vomiting-is-not-everything", "relative-time-is-not-one-day"])
def test_ambiguity_preserved_as_reviewable_null_without_numeric_duration(report, assessment, uncertainties):
    accepted = demo.with_values(empty_encounter(), demo.PREREQUISITES)
    accepted["danger_signs"]["vomits_everything"] = None
    values = {"patient_facts.has_cough_or_difficult_breathing": True} if assessment == "respiratory" else {}
    evidence = candidate(values, report, uncertainties=uncertainties)
    preview = extract_assessment({"assessment": assessment, "encounter": accepted, "findings": report}, provider_for(evidence))
    assert preview["input_text"] == preview["english_rendering"] == report
    assert preview["uncertainties"] == list(uncertainties)
    assert preview["candidate_encounter"]["danger_signs"]["vomits_everything"] is None
    durations = {field: value for field, value in demo.leaves(preview["candidate_encounter"]).items() if "duration" in field}
    assert durations and all(value is None for value in durations.values())
    uncertain_fields = {item["field"] for item in uncertainties if item["field"] is not None}
    assert {row["field"] for row in preview["changes"] if row["uncertain"]} == uncertain_fields
    assert all(row["value"] is None for row in preview["changes"] if row["uncertain"])
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        review(accepted, preview, assessment=assessment)
    result = review(accepted, preview, assessment=assessment, resolutions={field: "unknown" for field in uncertain_fields})
    assert result["assessments"][assessment]["question"]["field"] in uncertain_fields
    assert result["analysis"]["state"] == "INCOMPLETE" and not result["analysis"]["is_urgent"]


def test_known_urgency_interrupts_missing_questions_after_frontier_review():
    accepted = empty_encounter()
    accepted["danger_signs"]["convulsing_now"] = True
    provider = provider_for(candidate(demo.RESPIRATORY, demo.ENGLISH_REPORT))
    preview = extract_assessment({"assessment": "respiratory", "encounter": accepted,
                                  "findings": demo.ENGLISH_REPORT}, provider)
    assert preview["candidate_encounter"]["danger_signs"]["convulsing_now"] is None
    result = review(accepted, preview)
    assert result["encounter"]["danger_signs"]["convulsing_now"] is True
    assert result["analysis"]["state"] == "URGENT_INCOMPLETE"
    assert result["analysis"]["urgent_actions"] and result["analysis"]["missing_elements"]
    assert result["analysis"]["rendered_response"].startswith("URGENT:")
    assert all(item["decision"] == "URGENT" and item["question"] is None for item in result["assessments"].values())
    with pytest.raises(AssessmentError, match="question is stale"):
        extract_assessment({"assessment": "respiratory", "encounter": result["encounter"],
                            "findings": "No", "question_field": demo.STRIDOR}, provider)
    assert provider.understand.call_count == 1


def test_http_injected_frontier_bypasses_native_extractor_and_health_reports_both_modes():
    evidence = candidate(demo.RESPIRATORY, demo.YORUBA_REPORT, english=demo.ENGLISH_REPORT)
    provider, native = provider_for(evidence), QueueExtractor()
    speech = Mock()
    speech.transcribe.side_effect = AssertionError("Transcript-only test must not call ASR")
    server = make_server(port=0, extractor=native, language_provider=provider,
                         speech_provider=speech, language_understanding_mode="frontier")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, body=None):
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
            connection.request("GET" if body is None else "POST", "/api/" + path,
                               body=data, headers={"Content-Type": "application/json"})
            with connection.getresponse() as response:
                return response.status, json.load(response)
        finally:
            connection.close()

    try:
        status, health = request("health")
        assert status == 200
        assert health == {"status": "ok", "mode": native.mode_label,
                          "language_understanding": {"mode": provider.mode_label}}
        accepted = demo.with_values(empty_encounter(), demo.PREREQUISITES)
        status, preview = request("assessment/extract", {"assessment": "respiratory",
                                  "encounter": accepted, "findings": demo.YORUBA_REPORT})
        assert status == 200 and native.prompts == []
        assert preview["input_text"] == demo.YORUBA_REPORT
        assert preview["english_rendering"] == demo.ENGLISH_REPORT
        assert preview["evidence_spans"] == list(evidence.evidence_spans)
        assert preview["candidate_encounter"] == evidence.canonical_evidence
        assert preview["understanding"]["request_id"] == evidence.request_id
        status, unchanged = request("assessment/evaluate", {"encounter": accepted})
        assert status == 200 and unchanged["encounter"] == accepted
        body = {"assessment": "respiratory", "encounter": accepted, "changes": preview["changes"]}
        status, _ = request("assessment/accept", body)
        assert status == 422
        status, partial = request("assessment/accept", {**body, "confirmed": True})
        assert status == 200 and partial["assessments"]["respiratory"]["question"]["field"] == demo.STRIDOR
        for route in ("extract", "analyze"):
            native.encounters.append(empty_encounter())
            status, result = request(route, {"findings": "Native endpoint report."})
            assert status == 200 and result["extraction_mode"] == native.mode_label
        assert native.prompts == ["Native endpoint report."] * 2
        assert provider.understand.call_count == 1
        speech.transcribe.assert_not_called()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_smoke_requires_live_without_network(monkeypatch, capsys):
    network = Mock(side_effect=AssertionError("No network without --live"))
    monkeypatch.setattr(demo, "HTTPConnection", network)
    with pytest.raises(SystemExit) as error:
        demo.main([])
    assert error.value.code == 2
    assert "--live is required" in capsys.readouterr().err
    network.assert_not_called()


@pytest.mark.parametrize("unexpected_field", [False, True], ids=["six-call-success", "fail-before-review"])
def test_smoke_contract_against_local_server_with_only_injected_candidates(unexpected_field, capsys):
    respiratory = {**demo.RESPIRATORY, **({demo.STRIDOR: False} if unexpected_field else {})}
    provider = provider_for(
        candidate(demo.PREREQUISITES, demo.PREREQUISITES_REPORT),
        candidate(respiratory, demo.ENGLISH_REPORT),
        candidate({demo.STRIDOR: False}, "No"),
        candidate(demo.RESPIRATORY, demo.YORUBA_REPORT, english=demo.ENGLISH_REPORT),
        candidate({demo.STRIDOR: False}, "R\u00e1r\u00e1, k\u00f2 s\u00ed.", english="No."),
        candidate({}, demo.VOMITING_REPORT, uncertainties=(
            {"field": "danger_signs.vomits_everything", "source_text": "vomiting", "reason": "Not stated to vomit everything."},
            {"field": None, "source_text": "since yesterday", "reason": "Relative duration is not normalized."},
        )),
    )
    native, speech = QueueExtractor(), Mock()
    server = make_server(port=0, extractor=native, language_provider=provider, speech_provider=speech)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # --live exercises CLI consent, but this server has only offline candidates.
        code = demo.main(["--live", "--base-url", f"http://127.0.0.1:{server.server_port}"])
        summary = json.loads(capsys.readouterr().out.splitlines()[-1])
        assert code == (1 if unexpected_field else 0)
        assert summary["status"] == ("failed" if unexpected_field else "passed")
        assert summary["stage"] == ("english-respiratory" if unexpected_field else "ambiguity")
        assert summary["scoped_provider_calls"] == provider.understand.call_count == (2 if unexpected_field else 6)
        assert summary["http_calls"] == (6 if unexpected_field else 14)
        assert summary["provider"] == provider.mode_label and summary["transcript_only"] is True
        assert summary["latency_seconds"] >= 0
        assert set(summary) == {"status", "stage", "transcript_only", "provider", "http_calls",
                                "scoped_provider_calls", "latency_seconds"}
        assert native.prompts == []
        speech.transcribe.assert_not_called()
        calls = provider.understand.call_args_list
        assert calls[0].args[1] == {"assessment": "general_danger_signs", "id": "danger"}
        if not unexpected_field:
            assert calls[1].args[3] == calls[3].args[3]  # Both languages start from the same baseline.
            assert calls[2].args[0] == "No"
            assert calls[2].args[2] == calls[4].args[2] == {
                "field": demo.STRIDOR, "text": "Is there stridor when the child is calm?",
            }
            assert calls[5].args[3] == empty_encounter()  # Ambiguity is independent.
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("url", [
    "https://127.0.0.1:8000", "http://example.com:8000", "http://127.0.0.1.evil:8000",
    "http://user:secret@127.0.0.1:8000", "http://127.0.0.1:8000/path",
    "http://127.0.0.1:8000?token=secret", "http://127.0.0.1:8000#fragment",
    "http://127.0.0.1:0", "http://127.0.0.1:65536", "http://127.0.0.1",
])
def test_smoke_rejects_nonlocal_or_unsafe_urls_before_network(url, monkeypatch, capsys):
    network = Mock()
    monkeypatch.setattr(demo, "HTTPConnection", network)
    with pytest.raises(SystemExit) as error:
        demo.main(["--live", "--base-url", url])
    assert error.value.code == 2
    capsys.readouterr()
    network.assert_not_called()


@pytest.mark.parametrize("fault", ["unexpected-field", "wrong-value", "bool-is-not-int", "canonical-only", "uncertainty", "duplicate"])
def test_smoke_synthetic_review_rejects_every_unexpected_proposal(fault):
    preview = extract_assessment({"assessment": "respiratory", "findings": demo.ENGLISH_REPORT},
                                 provider_for(candidate(demo.RESPIRATORY, demo.ENGLISH_REPORT)))
    if fault == "unexpected-field":
        preview["changes"][0]["field"] = "danger_signs.vomits_everything"
    elif fault == "wrong-value":
        preview["changes"][0]["value"] = False
    elif fault == "bool-is-not-int":
        preview["changes"][0]["value"] = 1
    elif fault == "canonical-only":
        preview["candidate_encounter"]["respiratory"]["stridor_when_calm"] = False
    elif fault == "uncertainty":
        preview["uncertainties"] = [{"field": demo.STRIDOR}]
    else:
        preview["changes"].append(deepcopy(preview["changes"][0]))
    with pytest.raises(AssertionError):
        demo.check_synthetic_proposal(preview, demo.RESPIRATORY)
