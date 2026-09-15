from copy import deepcopy

import pytest

from app.assessment import evaluate_assessment


@pytest.mark.parametrize("entry,attempted,status", [
    (None, [], "NOT_STARTED"),
    (None, ["respiratory", "diarrhoea", "fever", "ear"], "INCOMPLETE"),
    (False, [], "COMPLETE"),
])
def test_general_danger_interrupts_every_question_without_urgent_inactive_paths(entry, attempted, status):
    encounter = evaluate_assessment({})["encounter"]
    encounter["patient_facts"].update(
        age_months=18, has_cough_or_difficult_breathing=entry,
        has_diarrhoea=entry, has_fever=entry, has_ear_problem=entry,
    )
    encounter["danger_signs"] = {field: False for field in encounter["danger_signs"]}
    encounter["danger_signs"]["convulsing_now"] = True
    before = deepcopy(encounter)

    result = evaluate_assessment({"encounter": encounter, "attempted": attempted})

    assert encounter == before
    assert result["analysis"]["is_urgent"] is True
    assert result["analysis"]["is_complete"] is (entry is False)
    assert result["analysis"]["urgent_actions"]
    assert result["assessments"]["danger"]["status"] == "URGENT"
    for assessment in ("respiratory", "diarrhoea", "fever", "ear"):
        progress = result["assessments"][assessment]
        assert progress["status"] == status
        assert bool(progress["missing_fields"]) is (entry is None)
        assert progress["blockers"] == []
    assert all(
        progress["decision"] == "URGENT" and progress["question"] is None
        for progress in result["assessments"].values()
    )
    assert "Mastoiditis" not in result["analysis"]["classifications"]


@pytest.mark.parametrize("ear_pain,ear_classification", [
    (False, "No ear infection"),
    (True, "Acute ear infection"),
])
def test_active_respiratory_and_fever_are_genuinely_urgent_but_uncomplicated_ear_is_not(ear_pain, ear_classification):
    encounter = evaluate_assessment({})["encounter"]
    encounter["patient_facts"].update(
        age_months=18, has_cough_or_difficult_breathing=True,
        has_diarrhoea=False, has_fever=True, has_ear_problem=True,
    )
    encounter["danger_signs"] = {field: False for field in encounter["danger_signs"]}
    encounter["danger_signs"]["convulsing_now"] = True
    encounter["respiratory"].update(
        cough_duration_days=3, respiratory_rate=35, chest_indrawing=False,
        stridor_when_calm=False, wheezing=False, recurrent_wheeze=False,
        child_calm=True, breaths_counted_one_minute=True, pulse_oximeter_available=False,
    )
    encounter["fever"].update(
        temperature_c=38.0, malaria_risk="HIGH", fever_duration_days=2,
        stiff_neck=False, runny_nose=False, obvious_cause_of_fever_present=False,
        identified_bacterial_cause_present=False, malaria_test_available=True,
        malaria_test_result="NEGATIVE", measles_within_last_3_months=False,
        generalized_rash=False, measles_cough=False, red_eyes=False,
    )
    encounter["ear"].update(
        ear_pain=ear_pain, ear_discharge_reported=False,
        pus_draining_from_ear=False, tender_swelling_behind_ear=False,
    )
    before = deepcopy(encounter)

    result = evaluate_assessment({"encounter": encounter})

    assert encounter == before
    assert result["analysis"]["state"] == "URGENT_COMPLETE"
    assert result["analysis"]["urgent_actions"]
    assert {name: progress["status"] for name, progress in result["assessments"].items()} == {
        "danger": "URGENT", "respiratory": "URGENT", "diarrhoea": "COMPLETE",
        "fever": "URGENT", "ear": "COMPLETE",
    }
    assert all(
        progress["decision"] == "URGENT" and progress["question"] is None
        and progress["missing_fields"] == [] and progress["blockers"] == []
        for progress in result["assessments"].values()
    )
    assert set(result["analysis"]["classifications"]) == {
        "Very severe disease", "Severe pneumonia or very severe disease",
        "Very severe febrile disease", ear_classification,
    }
    assert "Mastoiditis" not in result["analysis"]["classifications"]
