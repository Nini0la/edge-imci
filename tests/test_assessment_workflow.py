from __future__ import annotations

from copy import deepcopy

import pytest

from app.api import result_payload
from app.assessment import (
    AssessmentError, accept_assessment, evaluate_assessment, extract_assessment,
)
from app.extractor.base import ExtractionError, ExtractionResult
from app.extractor.stub import StubEncounterExtractor
from app.language_understanding import ExistingExtractorLanguageUnderstandingProvider
from app.service import ExtractionPreview, evaluate_extracted_findings


class QueueExtractor:
    mode_label = "injected-test-extractor"

    def __init__(self, *encounters):
        self.encounters = list(encounters)
        self.prompts = []

    def extract(self, prompt):
        self.prompts.append(prompt)
        assert self.encounters, "Unexpected extraction call"
        encounter = self.encounters.pop(0)
        if isinstance(encounter, Exception):
            raise encounter
        # Do not copy here: callers must not mutate provider-owned evidence.
        return ExtractionResult(encounter, self.mode_label)

    def understand(self, transcript, assessment_context, question_context, current_encounter_state):
        return ExistingExtractorLanguageUnderstandingProvider(self).understand(
            transcript, assessment_context, question_context, current_encounter_state,
        )


def known_complete():
    extractor = StubEncounterExtractor()
    return deepcopy(extractor.extract(
        extractor.fixture_text("hpg-068-cross-four-pathways")
    ).encounter)


def empty_encounter():
    def unknown(value):
        return {key: unknown(item) for key, item in value.items()} if isinstance(value, dict) else None

    return unknown(known_complete())


def review_body(encounter, changes, **kwargs):
    return {
        "assessment": "respiratory", "encounter": encounter,
        "changes": changes, "confirmed": True, **kwargs,
    }


def test_new_assessment_does_not_treat_selection_or_attempt_as_evidence():
    result = evaluate_assessment({"attempted": ["respiratory"]})
    assert result["encounter"] == empty_encounter()
    assert result["analysis"]["state"] == "INCOMPLETE"
    assert result["assessments"]["respiratory"]["status"] == "INCOMPLETE"
    assert result["assessments"]["danger"]["status"] == "NOT_STARTED"
    assert result["assessments"]["respiratory"]["question"]["field"] == "patient_facts.age_months"


def test_null_omissions_preserve_accepted_values_and_unknowns_without_aliasing():
    accepted = empty_encounter()
    accepted["patient_facts"].update(age_months=18, has_cough_or_difficult_breathing=True)
    accepted["respiratory"].update(respiratory_rate=42, chest_indrawing=False)
    proposed = empty_encounter()
    proposed["respiratory"]["cough_duration_days"] = 3
    before, provider_before = deepcopy(accepted), deepcopy(proposed)
    extractor = QueueExtractor(proposed, empty_encounter())
    preview = extract_assessment({
        "assessment": "respiratory", "encounter": accepted, "findings": "Cough for three days.",
    }, extractor)
    assert [change["field"] for change in preview["changes"]] == ["respiratory.cough_duration_days"]
    assert accepted == before and proposed == provider_before
    body = review_body(accepted, preview["changes"])
    with pytest.raises(AssessmentError, match="confirmation"):
        accept_assessment({**body, "confirmed": False})
    result = accept_assessment(body)
    expected = deepcopy(before)
    expected["respiratory"]["cough_duration_days"] = 3
    assert result["encounter"] == expected
    assert result["encounter"]["respiratory"]["wheezing"] is None
    omitted = extract_assessment({
        "assessment": "respiratory", "encounter": result["encounter"], "findings": "Not sure.",
    }, extractor)
    assert omitted["changes"] == []
    assert accept_assessment(review_body(result["encounter"], []))["encounter"] == expected
    result["encounter"]["respiratory"]["respiratory_rate"] = 99
    assert accepted == before and proposed == provider_before


@pytest.mark.parametrize("field", ["patient_facts.has_fever", "danger_signs.convulsing_now"])
def test_out_of_scope_evidence_including_true_danger_needs_explicit_resolution(field):
    accepted, proposed = empty_encounter(), empty_encounter()
    section, name = field.split(".")
    proposed[section][name] = True
    preview = extract_assessment({
        "assessment": "respiratory", "encounter": accepted, "findings": "Additional positive finding.",
    }, QueueExtractor(proposed))
    change, = preview["changes"]
    assert change["field"] == field and change["outside_assessment"] is True
    assert change["value"] is True
    # Flags are display metadata, not authority to bypass worker review.
    body = review_body(accepted, [{**change, "outside_assessment": False, "conflict": False}])
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        accept_assessment(body)
    assert accepted == empty_encounter()
    for choice in ("keep", "unknown", "replace"):
        result = accept_assessment({**body, "resolutions": {field: choice}})
        assert result["encounter"][section][name] is (True if choice == "replace" else None)
        if field == "danger_signs.convulsing_now" and choice == "replace":
            assert result["analysis"]["state"] == "URGENT_INCOMPLETE"


@pytest.mark.parametrize("choice,expected", [("keep", 42), ("replace", 35), ("unknown", None)])
def test_conflict_is_computed_server_side_and_choice_controls_accepted_value(choice, expected):
    accepted, proposed = empty_encounter(), empty_encounter()
    accepted["respiratory"]["respiratory_rate"] = 42
    proposed["respiratory"]["respiratory_rate"] = 35
    preview = extract_assessment({
        "assessment": "respiratory", "encounter": accepted, "findings": "Repeat rate is 35.",
    }, QueueExtractor(proposed))
    change, = preview["changes"]
    assert change["previous"] == 42 and change["conflict"] is True
    body = review_body(accepted, [{**change, "conflict": False, "outside_assessment": False}])
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        accept_assessment(body)
    result = accept_assessment({**body, "resolutions": {change["field"]: choice}})
    assert result["encounter"]["respiratory"]["respiratory_rate"] == expected
    assert accepted["respiratory"]["respiratory_rate"] == 42


def test_explicit_null_retraction_requires_choice_and_reopens_required_question():
    accepted = known_complete()
    field = "respiratory.respiratory_rate"
    body = review_body(accepted, [{"field": field, "previous": 42, "value": None}])
    with pytest.raises(AssessmentError, match="Explicitly resolve"):
        accept_assessment(body)
    result = accept_assessment({**body, "resolutions": {field: "unknown"}})
    assert result["encounter"]["respiratory"]["respiratory_rate"] is None
    assert result["assessments"]["respiratory"]["status"] == "INCOMPLETE"
    assert result["assessments"]["respiratory"]["question"]["field"] == field
    assert accepted == known_complete()


@pytest.mark.parametrize("previous", [True, 0])
def test_stale_previous_value_or_equal_but_different_type_rejects_whole_patch(previous):
    accepted = empty_encounter()
    accepted["respiratory"]["chest_indrawing"] = False
    before = deepcopy(accepted)
    body = review_body(accepted, [
        {"field": "patient_facts.age_months", "previous": None, "value": 18},
        {"field": "respiratory.chest_indrawing", "previous": previous, "value": True},
    ], resolutions={"respiratory.chest_indrawing": "replace"})
    with pytest.raises(AssessmentError, match="evidence has changed"):
        accept_assessment(body)
    assert accepted == before


@pytest.mark.parametrize("bad_change", [
    {"field": "patient_facts.age_months", "previous": None, "value": 18},  # duplicate
    {"field": "respiratory.diagnosis", "previous": None, "value": "PNEUMONIA"},
    {"field": "diarrhoea.rehydration_stage", "previous": None, "value": "IN_PROGRESS"},
    {"field": "diarrhoea.post_rehydration", "previous": None, "value": {}},
    {"field": "respiratory.chest_indrawing", "previous": None, "value": "false"},
    {"field": "respiratory.oxygen_saturation_percent", "previous": None, "value": 101},
])
def test_invalid_fields_duplicates_treatment_and_values_reject_atomically(bad_change):
    accepted = empty_encounter()
    body = review_body(accepted, [
        {"field": "patient_facts.age_months", "previous": None, "value": 18}, bad_change,
    ], resolutions={bad_change["field"]: "replace"})
    before = deepcopy(body)
    with pytest.raises(AssessmentError):
        accept_assessment(body)
    assert body == before


@pytest.mark.parametrize("age", [1, 60])
def test_out_of_range_age_rejected_at_extraction_and_acceptance(age):
    accepted, proposed = empty_encounter(), empty_encounter()
    proposed["patient_facts"]["age_months"] = age
    with pytest.raises(AssessmentError, match="supported"):
        extract_assessment({
            "assessment": "respiratory", "encounter": accepted, "findings": f"Age {age} months.",
        }, QueueExtractor(proposed))
    with pytest.raises(AssessmentError, match="supported"):
        accept_assessment(review_body(accepted, [
            {"field": "patient_facts.age_months", "previous": None, "value": age},
        ]))
    assert accepted == empty_encounter()


@pytest.mark.parametrize("invalid", [{"diagnosis": "PNEUMONIA"}, [], "not an encounter", None])
def test_invalid_extractor_schema_or_object_does_not_mutate_accepted_evidence(invalid):
    accepted = known_complete()
    before, invalid_before = deepcopy(accepted), deepcopy(invalid)
    with pytest.raises((AssessmentError, ExtractionError)):
        extract_assessment({
            "assessment": "respiratory", "encounter": accepted, "findings": "Repeat assessment.",
        }, QueueExtractor(invalid))
    assert accepted == before and invalid == invalid_before


def test_question_is_bound_to_current_deterministic_question_before_extractor_call():
    accepted, proposed = empty_encounter(), empty_encounter()
    proposed["patient_facts"]["age_months"] = 18
    extractor = QueueExtractor(proposed)
    body = {"assessment": "respiratory", "encounter": accepted, "findings": "18 months."}
    question = evaluate_assessment(body)["assessments"]["respiratory"]["question"]
    assert question["field"] == "patient_facts.age_months"
    for field in ("respiratory.respiratory_rate", "danger_signs.convulsing_now", {"field": question["field"]}):
        with pytest.raises(AssessmentError, match="question is stale"):
            extract_assessment({**body, "question_field": field}, extractor)
    assert extractor.prompts == []
    preview = extract_assessment({**body, "question_field": question["field"]}, extractor)
    assert question["text"] in extractor.prompts[0]
    assert "18 months." in extractor.prompts[0]
    assert [change["field"] for change in preview["changes"]] == [question["field"]]
    result = accept_assessment(review_body(accepted, preview["changes"]))
    assert result["encounter"]["patient_facts"]["has_cough_or_difficult_breathing"] is None
    with pytest.raises(AssessmentError, match="question is stale"):
        extract_assessment({**body, "encounter": result["encounter"], "question_field": question["field"]}, extractor)
    assert len(extractor.prompts) == 1


@pytest.mark.parametrize("qualifier", ["child_calm", "breaths_counted_one_minute"])
def test_missing_required_observation_and_measurement_validity_keep_assessment_incomplete(qualifier):
    accepted = known_complete()
    accepted["respiratory"].update(cough_duration_days=None, **{qualifier: None})
    result = evaluate_assessment({"encounter": accepted})
    progress = result["assessments"]["respiratory"]
    assert progress["status"] == "INCOMPLETE"
    assert {"respiratory.cough_duration_days", f"respiratory.{qualifier}"} <= set(progress["missing_fields"])
    # Supplying the missing history alone cannot validate the respiratory rate.
    result = accept_assessment(review_body(accepted, [
        {"field": "respiratory.cough_duration_days", "previous": None, "value": 3},
    ]))
    assert result["analysis"]["state"] == "INCOMPLETE"
    assert result["assessments"]["respiratory"]["status"] == "INCOMPLETE"
    assert result["assessments"]["respiratory"]["question"]["field"] == f"respiratory.{qualifier}"
    result["encounter"]["respiratory"][qualifier] = False
    invalid_measurement = evaluate_assessment({"encounter": result["encounter"]})
    assert invalid_measurement["analysis"]["state"] == "INCOMPLETE"
    assert invalid_measurement["assessments"]["respiratory"]["status"] == "INCOMPLETE"
    assert "Pneumonia" not in invalid_measurement["analysis"]["classifications"]


def test_urgent_partial_interrupts_questions_before_age_or_unrelated_completeness():
    accepted = empty_encounter()
    accepted["danger_signs"]["convulsing_now"] = True
    result = evaluate_assessment({"encounter": accepted})
    analysis = result["analysis"]
    assert analysis["state"] == "URGENT_INCOMPLETE"
    assert analysis["is_urgent"] and not analysis["is_complete"]
    assert analysis["urgent_actions"] and analysis["missing_elements"]
    assert analysis["rendered_response"].startswith("URGENT:")
    assert all(item["decision"] == "URGENT" and item["question"] is None for item in result["assessments"].values())


def test_contradiction_only_urgent_incompleteness_renders_without_crashing():
    accepted = known_complete()
    accepted["danger_signs"]["convulsing_now"] = True
    accepted["diarrhoea"]["dehydration"]["drinking_status"] = "UNABLE"
    result = evaluate_assessment({"encounter": accepted})
    analysis = result["analysis"]
    assert analysis["contradictions"] and not analysis["missing_elements"]
    assert analysis["state"] == "URGENT_INCOMPLETE"
    assert analysis["rendered_response"].startswith("URGENT:")
    assert analysis["urgent_actions"]
    assert all(item["blockers"] for item in result["assessments"].values())


def test_complete_fixture_result_exactly_matches_existing_evaluation_service():
    accepted = known_complete()
    before = deepcopy(accepted)
    expected = evaluate_extracted_findings(ExtractionPreview(
        input_text="Worker-reviewed assessment evidence",
        extraction_mode="reviewed-assessment-evidence", matched_case_id=None,
        structured_encounter=accepted, schema_valid=True,
    ))
    assert expected.state == "COMPLETE"
    result = evaluate_assessment({"encounter": accepted})
    assert result["analysis"] == result_payload(expected)
    assert all(item["status"] == "COMPLETE" for item in result["assessments"].values())
    assert accepted == before


@pytest.mark.parametrize("prefix", ["", "post_bronchodilator_"])
def test_replacement_rate_cannot_inherit_old_measurement_validity(prefix):
    accepted = known_complete()
    rate, calm, minute = [f"respiratory.{prefix}{name}" for name in (
        "respiratory_rate", "child_calm", "breaths_counted_one_minute",
    )]
    for field, value in ((rate, 42), (calm, True), (minute, True)):
        accepted["respiratory"][field.split(".")[1]] = value
    before = deepcopy(accepted)
    body = review_body(accepted, [{"field": rate, "previous": 42, "value": 35}], resolutions={rate: "replace"})
    with pytest.raises(AssessmentError, match="inherit old validity"):
        accept_assessment(body)
    assert accepted == before
    proposed = empty_encounter()
    for field, value in ((rate, 35), (calm, True), (minute, True)):
        proposed["respiratory"][field.split(".")[1]] = value
    preview = extract_assessment({
        "assessment": "respiratory", "encounter": accepted,
        "findings": "Repeated rate 35, calm, counted one full minute.",
    }, QueueExtractor(proposed))
    assert {change["field"] for change in preview["changes"]} == {rate, calm, minute}
    result = accept_assessment({**body, "changes": preview["changes"]})
    assert result["encounter"]["respiratory"][rate.split(".")[1]] == 35


def test_repairing_invalid_qualifier_requires_repeated_count_not_just_calm_child():
    accepted = known_complete()
    accepted["respiratory"]["child_calm"] = False
    progress = evaluate_assessment({"encounter": accepted})["assessments"]["respiratory"]
    assert "Repeat" in progress["question"]["text"]
    field = "respiratory.child_calm"
    body = review_body(accepted, [{"field": field, "previous": False, "value": True}], resolutions={field: "replace"})
    with pytest.raises(AssessmentError, match="must be repeated"):
        accept_assessment(body)
    body["changes"] += [
        {"field": "respiratory.respiratory_rate", "previous": 42, "value": 42},
        {"field": "respiratory.breaths_counted_one_minute", "previous": True, "value": True},
    ]
    assert accept_assessment(body)["assessments"]["respiratory"]["status"] == "COMPLETE"
