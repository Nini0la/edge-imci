"""Offline schema and worker-entered observation contracts."""

from copy import deepcopy
import hashlib
from http.client import HTTPConnection
import json
import sys

import pytest

from app.assessment import (
    ASSESSMENTS, AssessmentError, _SUPPORTED_FIELDS, _in_scope, accept_assessment,
    assessment_schema, evaluate_assessment, prepare_assessment_review,
)
from app.service.render import humanize_missing_element
from edge_imci.model_io.encounter import MODEL_FACING_ENCOUNTER_SCHEMA_PATH
from tests.test_assessment_api import api
from tests.test_assessment_workflow import empty_encounter, known_complete, review_body


def test_schema_is_filtered_actual_contract_not_clinical_requirements():
    raw = MODEL_FACING_ENCOUNTER_SCHEMA_PATH.read_bytes()
    canonical = json.loads(raw)
    result = assessment_schema()
    assert set(result) == {"schema_id", "schema_sha256", "fields"}
    assert result["schema_id"] == canonical["$id"]
    assert result["schema_sha256"] == hashlib.sha256(raw).hexdigest()
    fields = result["fields"]
    assert set(fields) == set(_SUPPORTED_FIELDS)
    assert not any("rehydration" in path for path in fields)
    for path, control in fields.items():
        node = canonical
        for part in path.split("."):
            if "$ref" in node:
                node = canonical["$defs"][node["$ref"].split("/")[-1]]
            if "oneOf" in node:
                node = canonical["$defs"][node["oneOf"][0]["$ref"].split("/")[-1]]
            node = node["properties"][part]
        if "$ref" in node:
            node = canonical["$defs"][node["$ref"].split("/")[-1]]
        assert control["path"] == path
        assert control["label"] == humanize_missing_element(path)
        assert control["nullable"] is ("null" in node["type"])
        assert control["assessments"] == [scope for scope in ASSESSMENTS if _in_scope(path, scope)]
        assert set(control) <= {"path", "label", "kind", "nullable", "options", "minimum", "maximum", "unit", "assessments"}
        assert control["kind"] in {"boolean", "integer", "number", "enum"}
        if control["kind"] == "enum":
            assert [option["value"] for option in control["options"]] == [value for value in node["enum"] if value is not None]
            assert all(type(option["value"]) is str and option["label"] for option in control["options"])
        else:
            assert control["kind"] in node["type"]
            assert "options" not in control
        for bound in ("minimum", "maximum"):
            assert (bound in control) is (bound in node)
            if bound in node:
                assert control[bound] == node[bound]
    assert fields["patient_facts.age_months"]["minimum"] == 0
    assert "maximum" not in fields["patient_facts.age_months"]
    assert "minimum" not in fields["fever.temperature_c"]
    assert "maximum" not in fields["fever.temperature_c"]
    assert {path: control["unit"] for path, control in fields.items() if "unit" in control} == {
        "patient_facts.age_months": "months",
        "respiratory.cough_duration_days": "days",
        "diarrhoea.duration_days": "days",
        "fever.fever_duration_days": "days",
        "ear.ear_discharge_duration_days": "days",
        "respiratory.respiratory_rate": "breaths per minute",
        "respiratory.post_bronchodilator_respiratory_rate": "breaths per minute",
        "respiratory.oxygen_saturation_percent": "%",
        "fever.temperature_c": "deg C",
    }
    assert fields["danger_signs.lethargic_or_unconscious"]["assessments"] == ["danger", "diarrhoea"]
    # Required JSON keys are not requirements for known clinical observations.
    complete = evaluate_assessment({"encounter": known_complete()})
    assert complete["analysis"]["state"] == "COMPLETE"
    assert complete["encounter"]["respiratory"]["post_bronchodilator_respiratory_rate"] is None


def test_schema_get_is_read_only_without_providers_or_evaluation(api, monkeypatch):
    post, extractor, speech = api

    def forbidden(*args, **kwargs):
        pytest.fail("Schema GET must not interpret, accept, or evaluate")

    for name in ("extract_assessment", "accept_assessment", "evaluate_assessment", "prepare_assessment_review"):
        monkeypatch.setattr("app.api." + name, forbidden)
    monkeypatch.setattr("app.assessment.evaluate_holistic_encounter", forbidden)
    expected = assessment_schema()
    connection = HTTPConnection("127.0.0.1", post.port, timeout=5)
    try:
        connection.request("GET", "/api/assessment/schema")
        with connection.getresponse() as response:
            assert response.status == 200
            assert response.getheader("Cache-Control") == "no-store"
            assert json.load(response) == expected
    finally:
        connection.close()
    assert extractor.prompts == [] and speech.calls == []


@pytest.mark.parametrize("age", [0, 1, 2, 59, 60])
def test_declared_age_minimum_does_not_change_adapter_scope(age):
    body = review_body(empty_encounter(), [{"field": "patient_facts.age_months", "previous": None, "value": age}])
    for operation in (prepare_assessment_review, accept_assessment):
        if 2 <= age <= 59:
            operation(body)
        else:
            with pytest.raises(AssessmentError, match="supported"):
                operation(body)


@pytest.mark.parametrize("value", [True, False, None])
def test_direct_manual_review_accept_needs_no_provider_credentials_or_consent(api, monkeypatch, value):
    post, extractor, speech = api
    for name in ("INTRON_API_KEY", "EDGEIMCI_FRONTIER_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    for name in ("openai", "azure.identity", "modal"):
        monkeypatch.setitem(sys.modules, name, None)
    field = "danger_signs.vomits_everything"
    metadata = {"worker_entered": True, "actor": {"id": "offline-worker"}, "custom_metadata": {"source": "manual"}}
    row = {"field": field, "previous": None, "value": value, **metadata}
    body = review_body(empty_encounter(), [row], assessment="danger", consent=False, **metadata)
    before = deepcopy(body)
    status, review = post("assessment/review", body)
    assert status == 200
    assert all(review["changes"][0][key] == item for key, item in metadata.items())
    status, error = post("assessment/accept", {**body, "changes": review["changes"], "confirmed": False})
    assert status == 422 and "confirmation" in error["error"]
    status, result = post("assessment/accept", {
        **body, "changes": review["changes"], "resolutions": {field: "replace"},
    })
    assert status == 200
    assert result["encounter"]["danger_signs"]["vomits_everything"] is value
    reference = evaluate_assessment({"encounter": result["encounter"]})["analysis"]
    assert result["analysis"] == json.loads(json.dumps(reference))
    assert all(result["encounter"]["danger_signs"][key] is None for key in result["encounter"]["danger_signs"] if key != "vomits_everything")
    assert body == before
    assert extractor.prompts == [] and speech.calls == []


@pytest.mark.parametrize("extra", ["respiratory.wheezing", "danger_signs.diagnosis", "worker_entered"])
@pytest.mark.parametrize("changes", [[], [{"field": "ear.ear_pain", "previous": None, "value": True}]])
def test_resolutions_only_name_submitted_fields(extra, changes):
    body = review_body(empty_encounter(), changes, assessment="ear", resolutions={extra: "keep"})
    before = deepcopy(body)
    with pytest.raises(AssessmentError, match="only submitted"):
        accept_assessment(body)
    assert body == before
