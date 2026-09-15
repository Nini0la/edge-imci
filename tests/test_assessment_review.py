from __future__ import annotations

from copy import deepcopy

import pytest

from app.assessment import (
    AssessmentError, _SUPPORTED_FIELDS, accept_assessment, extract_assessment,
    prepare_assessment_review,
)
from tests.test_assessment_api import api
from tests.test_assessment_workflow import QueueExtractor, empty_encounter, known_complete, review_body


def test_disjoint_captures_reviewed_against_latest_preserve_both_accepts():
    initial = empty_encounter()
    a, b = empty_encounter(), empty_encounter()
    a["respiratory"]["cough_duration_days"] = 3
    b["ear"]["ear_pain"] = True
    provider = QueueExtractor(a, b)
    first = extract_assessment({
        "assessment": "respiratory", "encounter": initial, "findings": "Cough for three days.",
    }, provider)
    second = extract_assessment({
        "assessment": "ear", "encounter": initial, "findings": "Ear pain.",
    }, provider)
    latest = accept_assessment(review_body(initial, first["changes"]))["encounter"]
    body = {"assessment": "ear", "encounter": latest, "changes": second["changes"]}
    before = deepcopy(body)
    reviewed = prepare_assessment_review(body)
    assert body == before
    assert reviewed["changed_fields"] == []
    assert all(not row["review_changed"] and not row["conflict"] for row in reviewed["changes"])
    result = accept_assessment({**body, "changes": reviewed["changes"], "confirmed": True})
    assert result["encounter"]["respiratory"]["cough_duration_days"] == 3
    assert result["encounter"]["ear"]["ear_pain"] is True
    assert len(provider.prompts) == 2
    assert initial == empty_encounter() and body == before


@pytest.mark.parametrize("latest_value", [False, None, True])
@pytest.mark.parametrize("choice", ["keep", "replace", "unknown"])
def test_overlap_requires_choice_even_after_retraction_or_matching_proposal(latest_value, choice):
    field = "respiratory.chest_indrawing"
    initial = empty_encounter()
    initial["respiratory"]["chest_indrawing"] = not latest_value if latest_value is not None else True
    original = {"field": field, "previous": initial["respiratory"]["chest_indrawing"], "value": True}
    latest = accept_assessment(review_body(initial, [
        {**original, "value": latest_value},
    ], resolutions={field: "replace"}))["encounter"]
    review = prepare_assessment_review(review_body(latest, [original]))
    row, = review["changes"]
    assert review["changed_fields"] == [field]
    assert row["review_changed"] is True and row["previous"] is latest_value
    assert row["conflict"] is (latest_value is False)
    body = review_body(latest, review["changes"])
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        accept_assessment(body)
    result = accept_assessment({**body, "resolutions": {field: choice}})
    expected = latest_value if choice == "keep" else True if choice == "replace" else None
    assert result["encounter"]["respiratory"]["chest_indrawing"] is expected


def test_same_value_reconfirmations_and_metadata_retained_without_aliasing():
    latest = known_complete()
    changes = [
        {"field": f"respiratory.{name}", "previous": value, "value": value,
         "conflict": True, "outside_assessment": True, "review_changed": True,
         "source": {"text": "Original report"}, "label": name}
        for name, value in (("respiratory_rate", 42), ("child_calm", True), ("breaths_counted_one_minute", True))
    ]
    body = review_body(latest, changes)
    before = deepcopy(body)
    review = prepare_assessment_review(body)
    assert body == before and review["changed_fields"] == []
    assert len(review["changes"]) == 3
    for original, row in zip(changes, review["changes"]):
        assert not row["conflict"] and not row["outside_assessment"] and not row["review_changed"]
        assert row["label"] == original["label"] and row["source"] == original["source"]
    assert accept_assessment({**body, "changes": review["changes"]})["encounter"] == latest
    review["changes"][0]["source"]["text"] = "Not the original"
    assert body == before


def test_typed_numeric_comparisons_and_repeated_review_use_original_rows():
    latest = empty_encounter()
    latest["respiratory"]["oxygen_saturation_percent"] = 95.0
    field = "respiratory.oxygen_saturation_percent"
    body = review_body(latest, [{"field": field, "previous": 95, "value": 95}])
    review = prepare_assessment_review(body)
    assert review["changed_fields"] == [field]
    assert review["changes"][0]["conflict"] is True
    assert type(review["changes"][0]["previous"]) is float
    assert type(body["changes"][0]["previous"]) is int
    assert prepare_assessment_review(body) == review
    with pytest.raises(AssessmentError, match="evidence has changed"):
        accept_assessment(body)
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        accept_assessment({**body, "changes": review["changes"]})


def test_all_supported_fields_including_nested_nulls_can_be_reviewed():
    body = review_body(empty_encounter(), [
        {"field": field, "previous": None, "value": None, "uncertain": True}
        for field in _SUPPORTED_FIELDS
    ])
    review = prepare_assessment_review(body)
    assert [row["field"] for row in review["changes"]] == list(_SUPPORTED_FIELDS)
    assert review["changed_fields"] == []
    assert all(row["uncertain"] and row["value"] is None for row in review["changes"])


@pytest.mark.parametrize("latest_value", [None, False, True])
def test_uncertainty_nulls_retained_and_always_require_choice(latest_value):
    latest = empty_encounter()
    latest["respiratory"]["wheezing"] = latest_value
    field = "respiratory.wheezing"
    body = review_body(latest, [{"field": field, "previous": None, "value": None, "uncertain": True}])
    review = prepare_assessment_review(body)
    row, = review["changes"]
    assert row["value"] is None and row["uncertain"] is True
    assert row["previous"] is latest_value
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        accept_assessment({**body, "changes": review["changes"]})
    result = accept_assessment({**body, "changes": review["changes"], "resolutions": {field: "keep"}})
    assert result["encounter"] == latest


def test_fake_flags_recomputed_and_shared_scope_preserved():
    latest = empty_encounter()
    latest["danger_signs"]["convulsing_now"] = False
    review = prepare_assessment_review(review_body(latest, [
        {"field": "danger_signs.convulsing_now", "previous": None, "value": True,
         "conflict": False, "outside_assessment": False, "review_changed": False},
        {"field": "patient_facts.age_months", "previous": None, "value": 18, "outside_assessment": True},
    ]))
    danger, age = review["changes"]
    assert danger["conflict"] and danger["outside_assessment"] and danger["review_changed"]
    assert not age["outside_assessment"] and not age["review_changed"]
    shared = prepare_assessment_review({
        "assessment": "diarrhoea", "encounter": latest,
        "changes": [{"field": "danger_signs.lethargic_or_unconscious", "previous": None, "value": True}],
    })
    assert shared["changes"][0]["outside_assessment"] is False


@pytest.mark.parametrize("field,value", [
    ("respiratory.wheezing", "false"), ("respiratory.wheezing", 0),
    ("respiratory.respiratory_rate", True), ("respiratory.respiratory_rate", 42.5),
    ("respiratory.oxygen_saturation_percent", 101),
    ("respiratory.oxygen_saturation_percent", float("nan")),
    ("patient_facts.age_months", 1), ("patient_facts.age_months", 60),
    ("diarrhoea.dehydration.drinking_status", "INVALID"),
    ("ear.ear_pain", {}), ("ear.ear_pain", []),
])
@pytest.mark.parametrize("key", ["value", "previous"])
@pytest.mark.parametrize("choice", ["keep", "unknown", "replace"])
def test_candidate_and_original_previous_validate_against_canonical_shape(field, value, key, choice):
    body = review_body(empty_encounter(), [{"field": field, "previous": None, "value": None, key: value}])
    with pytest.raises(AssessmentError):
        prepare_assessment_review(body)
    with pytest.raises(AssessmentError):
        accept_assessment({**body, "resolutions": {field: choice}})


@pytest.mark.parametrize("changes", [
    None, {}, "rows", [None], [{"field": []}],
    [{"field": "respiratory.diagnosis", "previous": None, "value": "PNEUMONIA"}],
    [{"field": "diarrhoea.rehydration_stage", "previous": None, "value": None}],
    [{"field": "diarrhoea.post_rehydration", "previous": None, "value": None}],
    [{"field": "ear.ear_pain", "value": True}],
    [{"field": "ear.ear_pain", "previous": None}],
    [{"field": "ear.ear_pain", "previous": None, "value": True}] * 2,
    [{"field": "ear.ear_pain", "previous": None, "value": True}] * (len(_SUPPORTED_FIELDS) + 1),
    [{"field": "ear.ear_pain", "previous": None, "value": True, "uncertain": True}],
    [{"field": "ear.ear_pain", "previous": None, "value": None, "uncertain": "true"}],
])
def test_invalid_review_rows_rejected_without_mutation(changes):
    body = review_body(empty_encounter(), changes)
    before = deepcopy(body)
    with pytest.raises(AssessmentError):
        prepare_assessment_review(body)
    with pytest.raises(AssessmentError):
        accept_assessment(body)
    assert body == before


@pytest.mark.parametrize("uncertain,value", [
    (None, None), (0, None), (1, None), ("false", None), ([], None), ({}, None),
    (True, False), (True, True),
])
@pytest.mark.parametrize("choice", ["keep", "unknown", "replace"])
def test_accept_validates_uncertainty_even_for_discarded_rows(uncertain, value, choice):
    field = "respiratory.wheezing"
    body = review_body(empty_encounter(), [
        {"field": field, "previous": None, "value": value, "uncertain": uncertain},
    ], resolutions={field: choice})
    with pytest.raises(AssessmentError, match="uncertainty"):
        accept_assessment(body)


@pytest.mark.parametrize("overrides", [
    {"assessment": "unknown"}, {"assessment": []}, {"encounter": {}}, {"encounter": []},
])
def test_invalid_assessment_or_latest_encounter_rejected(overrides):
    with pytest.raises(AssessmentError):
        prepare_assessment_review({**review_body(empty_encounter(), []), **overrides})


def test_rebase_does_not_weaken_stale_previous_or_final_validation():
    latest = empty_encounter()
    field = "respiratory.chest_indrawing"
    review = prepare_assessment_review(review_body(latest, [{"field": field, "previous": None, "value": True}]))
    latest["respiratory"]["chest_indrawing"] = False
    with pytest.raises(AssessmentError, match="evidence has changed"):
        accept_assessment(review_body(latest, review["changes"], resolutions={field: "replace"}))
    review = prepare_assessment_review(review_body(latest, review["changes"]))
    review["changes"][0]["value"] = "true"
    with pytest.raises(AssessmentError, match="invalid or outside"):
        accept_assessment(review_body(latest, review["changes"], resolutions={field: "replace"}))


@pytest.mark.parametrize("flag", [None, 0, 1, "false", [], {}])
def test_accept_rejects_non_boolean_review_changed(flag):
    with pytest.raises(AssessmentError, match="Invalid evidence review"):
        accept_assessment(review_body(empty_encounter(), [
            {"field": "respiratory.wheezing", "previous": None, "value": True, "review_changed": flag},
        ]))


def test_disjoint_rebase_does_not_infer_measurement_independence():
    latest = empty_encounter()
    original = [{"field": "respiratory.respiratory_rate", "previous": None, "value": 35}]
    latest = accept_assessment(review_body(latest, [
        {"field": f"respiratory.{name}", "previous": None, "value": True}
        for name in ("child_calm", "breaths_counted_one_minute")
    ]))["encounter"]
    review = prepare_assessment_review(review_body(latest, original))
    assert review["changed_fields"] == []
    with pytest.raises(AssessmentError, match="inherit old validity"):
        accept_assessment(review_body(latest, review["changes"]))


def test_http_review_is_pure_and_does_not_call_providers_or_evaluator(api, monkeypatch):
    post, extractor, speech = api

    def forbidden(*args, **kwargs):
        pytest.fail("Review must not extract, accept, or evaluate")

    monkeypatch.setattr("app.assessment.evaluate_assessment", forbidden)
    monkeypatch.setattr("app.assessment.evaluate_holistic_encounter", forbidden)
    monkeypatch.setattr("app.api.accept_assessment", forbidden)
    monkeypatch.setattr("app.api.extract_assessment", forbidden)
    body = review_body(empty_encounter(), [
        {"field": "ear.ear_pain", "previous": True, "value": True},
    ], assessment="ear")
    status, review = post("assessment/review", body)
    assert status == 200 and review == prepare_assessment_review(body)
    assert set(review) == {"changes", "changed_fields"}
    assert review["changed_fields"] == ["ear.ear_pain"]
    status, error = post("assessment/review", {**body, "changes": [{"field": "unknown"}]})
    assert status == 422 and error["error"]
    status, unchanged = post("assessment/review", {**body, "changes": []})
    assert status == 200 and unchanged == {"changes": [], "changed_fields": []}
    assert extractor.prompts == [] and speech.calls == []


@pytest.mark.parametrize("headers,raw,status", [
    ({"Origin": "https://attacker.example"}, b"{}", 403),
    ({"Content-Type": "text/plain"}, b"{}", 415),
    ({}, b'{"changes":[],"changes":[]}', 400),
    ({}, b'{"value":NaN}', 400),
    ({}, b"[]", 400),
])
def test_http_review_preserves_request_boundary(api, headers, raw, status):
    post, extractor, speech = api
    actual, error = post("assessment/review", raw, headers=headers, raw_json=True)
    assert actual == status and error["error"]
    assert extractor.prompts == [] and speech.calls == []
