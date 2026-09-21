"""Offline full-report capture contract; injected evidence is not model accuracy."""

from copy import deepcopy
from dataclasses import replace
from http.client import HTTPConnection
import json
from threading import Thread
from unittest.mock import Mock

import pytest

from app.api import make_server
from app.assessment import (
    ASSESSMENTS, AssessmentError, _SUPPORTED_FIELDS, _get, _in_scope,
    accept_assessment, assessment_schema, evaluate_assessment, extract_assessment,
    prepare_assessment_review,
)
from app.language_understanding import CanonicalEvidenceCandidate
from tests.test_assessment_workflow import QueueExtractor, empty_encounter, known_complete, review_body
from tests.test_frontier_assessment import offline_only, provider_for


def candidate(values, report, *, uncertainties=()):
    evidence = empty_encounter()
    for field, value in values.items():
        node = evidence
        parts = field.split(".")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
    return CanonicalEvidenceCandidate(
        canonical_evidence=evidence, english_rendering=report, uncertainties=uncertainties,
        evidence_spans=tuple({"field": field, "source_text": report} for field in values if values[field] is not None),
        provider="azure-openai", model="offline-fixture", prompt_version="offline-test",
    )


def test_full_report_cross_path_proposals_are_sparse_in_scope_and_not_autoaccepted():
    accepted = known_complete()
    before = deepcopy(accepted)
    report = "Age 18 months. No convulsions. Cough today. No sunken eyes, fever or ear pain."
    values = {
        "patient_facts.age_months": 18,
        "danger_signs.convulsing_now": False,
        "respiratory.cough_duration_days": 0,
        "diarrhoea.dehydration.sunken_eyes": False,
        "patient_facts.has_fever": False,
        "ear.ear_pain": False,
    }
    evidence = candidate(values, report)
    evidence_before = deepcopy(evidence)
    provider = provider_for(evidence)
    preview = extract_assessment({
        "assessment": "full-note", "encounter": accepted, "findings": "  " + report + "\n",
    }, provider)
    provider.understand.assert_called_once_with(
        report, {"assessment": "Full assessment report", "id": "full-note"}, None, accepted,
    )
    assert provider.understand.call_args.args[3] is not accepted
    assert preview["assessment"] == "full-note" and preview["input_text"] == report
    assert preview["english_rendering"] == report
    assert preview["evidence_spans"] == list(evidence.evidence_spans)
    assert preview["understanding"]["provider"] == evidence.provider
    assert preview["extraction_mode"] == provider.mode_label
    assert {row["field"]: row["value"] for row in preview["changes"]} == values
    assert all(not row["outside_assessment"] for row in preview["changes"])
    assert any(row["previous"] is False and row["value"] is False for row in preview["changes"])
    assert not {"encounter", "analysis", "question"} & preview.keys()
    assert not any("outside the selected assessment" in warning for warning in preview["warnings"])
    assert preview["candidate_encounter"]["respiratory"]["respiratory_rate"] is None
    assert accepted == before and evidence == evidence_before

    body = review_body(accepted, preview["changes"], assessment="full-note")
    reviewed = prepare_assessment_review(body)
    assert reviewed["changed_fields"] == []
    assert all(not row["outside_assessment"] for row in reviewed["changes"])
    for confirmed in (None, False, 1, "true"):
        with pytest.raises(AssessmentError, match="confirmation"):
            accept_assessment({**body, "confirmed": confirmed})
    resolutions = {row["field"]: "replace" for row in reviewed["changes"] if row["conflict"]}
    result = accept_assessment({**body, "changes": reviewed["changes"], "resolutions": resolutions})
    expected = candidate({**{
        field: _get(before, field) for field in _SUPPORTED_FIELDS
    }, **values}, report).canonical_evidence
    assert result["encounter"] == expected
    assert result["encounter"]["respiratory"]["respiratory_rate"] == 42
    assert set(result["assessments"]) == set(ASSESSMENTS)
    assert accepted == before and evidence == evidence_before


@pytest.mark.parametrize("question_field", [None, "patient_facts.age_months", "", False, {}])
def test_full_note_rejects_any_question_field_before_provider_call(question_field):
    provider = provider_for()
    with pytest.raises(AssessmentError, match="follow-up question"):
        extract_assessment({
            "assessment": "full-note", "findings": "18 months.", "question_field": question_field,
        }, provider)
    provider.understand.assert_not_called()


def test_empty_report_evidence_leaves_unknowns_and_assessments_unstarted():
    provider = provider_for(candidate({}, "Not assessed."))
    preview = extract_assessment({"assessment": "full-note", "findings": "Not assessed."}, provider)
    assert preview["changes"] == []
    result = accept_assessment(review_body(empty_encounter(), [], assessment="full-note"))
    assert result["encounter"] == empty_encounter()
    assert result["analysis"]["state"] == "INCOMPLETE"
    assert all(item["status"] == "NOT_STARTED" for item in result["assessments"].values())


@pytest.mark.parametrize("field", _SUPPORTED_FIELDS)
def test_full_note_attempts_only_applied_field_owner_not_shared_scope(field):
    # Retraction to unknown exposes bookkeeping independently of known evidence.
    body = review_body(empty_encounter(), [
        {"field": field, "previous": None, "value": None, "uncertain": True},
    ], assessment="full-note", resolutions={field: "unknown"})
    result = accept_assessment(body)
    for name, (_, prefix, entry) in ASSESSMENTS.items():
        owns = field.startswith(prefix + ".") or field == entry
        assert result["assessments"][name]["status"] == ("INCOMPLETE" if owns else "NOT_STARTED")
    kept = accept_assessment({**body, "resolutions": {field: "keep"}})
    assert all(item["status"] == "NOT_STARTED" for item in kept["assessments"].values())


def test_age_alone_preserves_prior_attempts_without_starting_other_assessments():
    result = accept_assessment(review_body(empty_encounter(), [
        {"field": "patient_facts.age_months", "previous": None, "value": 18},
    ], assessment="full-note", attempted=["ear"]))
    assert result["assessments"]["ear"]["status"] == "INCOMPLETE"
    assert all(item["status"] == "NOT_STARTED" for name, item in result["assessments"].items() if name != "ear")
    assert result["analysis"]["state"] == "INCOMPLETE"
    assert result["encounter"]["patient_facts"]["has_fever"] is None


def test_full_note_is_not_a_clinical_assessment_or_control_membership():
    assert set(ASSESSMENTS) == {"danger", "respiratory", "diarrhoea", "fever", "ear"}
    assert all("full-note" not in control["assessments"] for control in assessment_schema()["fields"].values())
    assert all(_in_scope(field, "full-note") for field in _SUPPORTED_FIELDS)
    assert not _in_scope("respiratory.diagnosis", "full-note")
    assert not _in_scope("diarrhoea.rehydration_stage", "full-note")
    body = review_body(empty_encounter(), [
        {"field": "ear.ear_pain", "previous": None, "value": True},
    ], assessment="full-note", attempted=["full-note"])
    before = deepcopy(body)
    for operation in (evaluate_assessment, accept_assessment):
        with pytest.raises(AssessmentError, match="existing IMCI assessments"):
            operation(body)
    assert body == before


@pytest.mark.parametrize("latest_value", [None, False, True])
@pytest.mark.parametrize("choice", ["keep", "replace", "unknown"])
def test_full_note_conflict_stale_and_changed_review_guards(latest_value, choice):
    field = "ear.ear_pain"
    original = {"field": field, "previous": False if latest_value is None else None, "value": True,
                "conflict": False, "outside_assessment": True}
    latest = empty_encounter()
    latest["ear"]["ear_pain"] = latest_value
    body = review_body(latest, [original], assessment="full-note")
    before = deepcopy(body)
    with pytest.raises(AssessmentError, match="evidence has changed"):
        accept_assessment({**body, "resolutions": {field: choice}})
    reviewed = prepare_assessment_review(body)
    row, = reviewed["changes"]
    assert reviewed["changed_fields"] == [field] and row["review_changed"] is True
    assert row["conflict"] is (latest_value is False) and not row["outside_assessment"]
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        accept_assessment({**body, "changes": reviewed["changes"]})
    result = accept_assessment({**body, "changes": reviewed["changes"], "resolutions": {field: choice}})
    assert result["encounter"]["ear"]["ear_pain"] is (latest_value if choice == "keep" else True if choice == "replace" else None)
    assert body == before


@pytest.mark.parametrize("previous", [None, False, True])
def test_full_note_uncertainty_is_an_explicit_reviewable_null(previous):
    field = "danger_signs.vomits_everything"
    accepted = empty_encounter()
    accepted["danger_signs"]["vomits_everything"] = previous
    uncertainty = ({"field": field, "source_text": "Vomiting.", "reason": "Everything not specified."},)
    preview = extract_assessment({
        "assessment": "full-note", "encounter": accepted, "findings": "Vomiting.",
    }, provider_for(candidate({}, "Vomiting.", uncertainties=uncertainty)))
    row, = preview["changes"]
    assert row["value"] is None and row["uncertain"] and not row["outside_assessment"]
    assert row["previous"] is previous and row["conflict"] is (previous is not None)
    body = review_body(accepted, preview["changes"], assessment="full-note")
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        accept_assessment(body)
    assert accept_assessment({**body, "resolutions": {field: "keep"}})["encounter"] == accepted
    result = accept_assessment({**body, "resolutions": {field: "unknown"}})
    assert result["encounter"]["danger_signs"]["vomits_everything"] is None
    assert result["analysis"]["state"] == "INCOMPLETE"
    assert accepted["danger_signs"]["vomits_everything"] is previous


@pytest.mark.parametrize("scope", [None, "", "full-report", "FULL-NOTE", [], {}, 5])
def test_invalid_capture_scope_rejected_by_all_operations(scope):
    provider = provider_for()
    body = review_body(empty_encounter(), [], assessment=scope, findings="Report.")
    for operation in (prepare_assessment_review, accept_assessment):
        with pytest.raises(AssessmentError):
            operation(body)
    with pytest.raises(AssessmentError):
        extract_assessment(body, provider)
    provider.understand.assert_not_called()


@pytest.mark.parametrize("findings", [None, "", " \n", "x" * 8001, [], {}, 42])
def test_malformed_full_report_rejected_before_provider(findings):
    provider = provider_for()
    with pytest.raises(AssessmentError, match="report"):
        extract_assessment({"assessment": "full-note", "findings": findings}, provider)
    provider.understand.assert_not_called()


@pytest.mark.parametrize("evidence", [None, [], {}, {"diagnosis": "PNEUMONIA"}])
def test_invalid_provider_evidence_cannot_replace_accepted_encounter(evidence):
    accepted = known_complete()
    before = deepcopy(accepted)
    provider = provider_for(replace(candidate({}, "Report."), canonical_evidence=evidence))
    with pytest.raises(AssessmentError):
        extract_assessment({"assessment": "full-note", "encounter": accepted, "findings": "Report."}, provider)
    assert accepted == before


@pytest.mark.parametrize("field,value", [
    ("respiratory.diagnosis", "PNEUMONIA"),
    ("diarrhoea.rehydration_stage", "IN_PROGRESS"),
    ("diarrhoea.post_rehydration", {}),
    ("ear.ear_pain", "false"),
    ("patient_facts.age_months", 60),
])
def test_unsupported_fields_and_invalid_values_fail_atomically_at_every_stage(field, value):
    evidence = candidate({}, "Report.")
    section, name = field.split(".")
    evidence.canonical_evidence[section][name] = value
    body = review_body(empty_encounter(), [
        {"field": "respiratory.cough_duration_days", "previous": None, "value": 3},
        {"field": field, "previous": None, "value": value},
    ], assessment="full-note", findings="Report.", resolutions={field: "replace"})
    before = deepcopy(body)
    with pytest.raises(AssessmentError):
        extract_assessment(body, provider_for(evidence))
    for operation in (prepare_assessment_review, accept_assessment):
        with pytest.raises(AssessmentError):
            operation(body)
    assert body == before


@pytest.mark.parametrize("prefix", ["", "post_bronchodilator_"])
def test_full_note_measurement_episodes_cannot_reuse_old_qualifiers(prefix):
    rate, calm, minute = [f"respiratory.{prefix}{name}" for name in (
        "respiratory_rate", "child_calm", "breaths_counted_one_minute",
    )]
    accepted = candidate({rate: 42, calm: True, minute: True}, "Old count.").canonical_evidence
    preview = extract_assessment({"assessment": "full-note", "encounter": accepted, "findings": "Repeat count 35."},
                                 provider_for(candidate({rate: 35}, "Repeat count 35.")))
    body = review_body(accepted, preview["changes"], assessment="full-note", resolutions={rate: "replace"})
    before = deepcopy(body)
    with pytest.raises(AssessmentError, match="inherit old validity"):
        accept_assessment(body)
    assert body == before
    preview = extract_assessment({"assessment": "full-note", "encounter": accepted,
                                  "findings": "35, calm, counted for a full minute."},
                                 provider_for(candidate({rate: 35, calm: True, minute: True}, "35, calm, counted for a full minute.")))
    assert len(preview["changes"]) == 3
    result = accept_assessment({**body, "changes": preview["changes"]})
    assert _get(result["encounter"], rate) == 35
    assert body == before


@pytest.mark.parametrize("prefix", ["", "post_bronchodilator_"])
@pytest.mark.parametrize("invalid", ["child_calm", "breaths_counted_one_minute"])
def test_full_note_validity_repair_requires_repeated_rate_and_both_qualifiers(prefix, invalid):
    values = {f"respiratory.{prefix}{name}": value for name, value in (
        ("respiratory_rate", 42), ("child_calm", True), ("breaths_counted_one_minute", True),
    )}
    field = f"respiratory.{prefix}{invalid}"
    accepted = candidate({**values, field: False}, "Old invalid count.").canonical_evidence
    body = review_body(accepted, [{"field": field, "previous": False, "value": True}],
                       assessment="full-note", resolutions={field: "replace"})
    before = deepcopy(body)
    with pytest.raises(AssessmentError, match="must be repeated"):
        accept_assessment(body)
    assert body == before
    rows = [{"field": path, "previous": _get(accepted, path), "value": value} for path, value in values.items()]
    result = accept_assessment({**body, "changes": rows})
    assert all(_get(result["encounter"], path) == value for path, value in values.items())


def test_http_full_note_uses_configured_understanding_not_native_or_speech():
    report = "Cough for three days. No ear pain."
    provider = provider_for(candidate({"respiratory.cough_duration_days": 3, "ear.ear_pain": False}, report))
    native, speech = QueueExtractor(), Mock()
    server = make_server(port=0, extractor=native, language_provider=provider,
                         speech_provider=speech, language_understanding_mode="frontier")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def post(route, body):
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            connection.request("POST", "/api/assessment/" + route, json.dumps(body),
                               {"Content-Type": "application/json"})
            with connection.getresponse() as response:
                return response.status, json.load(response)
        finally:
            connection.close()

    try:
        accepted = empty_encounter()
        body = {"assessment": "full-note", "encounter": accepted, "findings": report}
        status, preview = post("extract", body)
        assert status == 200 and preview["extraction_mode"] == provider.mode_label
        status, unchanged = post("evaluate", {"encounter": accepted})
        assert status == 200 and unchanged["encounter"] == accepted
        body = {**body, "changes": preview["changes"]}
        status, reviewed = post("review", body)
        assert status == 200 and reviewed["changed_fields"] == []
        body["changes"] = reviewed["changes"]
        assert post("accept", body)[0] == 422
        status, result = post("accept", {**body, "confirmed": True})
        assert status == 200 and set(result["assessments"]) == set(ASSESSMENTS)
        assert result["encounter"]["respiratory"]["cough_duration_days"] == 3
        assert result["encounter"]["ear"]["ear_pain"] is False
        assert result["analysis"]["state"] == "INCOMPLETE"
        assert post("evaluate", {"attempted": ["full-note"]})[0] == 422
        assert post("extract", {**body, "question_field": None})[0] == 422
        provider.understand.assert_called_once_with(
            report, {"assessment": "Full assessment report", "id": "full-note"}, None, accepted,
        )
        assert native.prompts == []
        speech.transcribe.assert_not_called()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
