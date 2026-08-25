from __future__ import annotations

import copy
import json

from edge_imci.evaluation.ood_regression_canary import (
    CANARY_PATH,
    CANARY_SHA256,
    SPARSE_COUGH_CANARY_PATH,
    SPARSE_COUGH_CANARY_SHA256,
    load_frozen_canary,
    score_ood_canary_prediction,
)


EXACT_INPUT = (
    "This child is 18 months old. They've been coughing for 2 weeks. "
    "They have ear pus that just started yesterday."
)
SPARSE_COUGH_INPUT = "The child is 22 months and is coughing."


def test_frozen_canary_has_expected_semantics_and_isolation() -> None:
    canary = load_frozen_canary()
    target = canary["expected_target"]

    assert canary["input"] == {"role": "user", "content": EXACT_INPUT}
    assert canary["provenance"]["failure_label"] == "user-reported OOD failure"
    assert canary["isolation"] == {
        "partition": "OOD_REGRESSION_CANARY",
        "campaign_data_eligible": False,
        "training_eligible": False,
        "validation_eligible": False,
        "test_eligible": False,
        "model_selection_eligible": False,
    }
    assert target["patient_facts"] == {
        "age_months": 18,
        "has_cough_or_difficult_breathing": True,
        "has_diarrhoea": None,
        "has_fever": None,
        "has_ear_problem": True,
    }
    assert target["respiratory"]["cough_duration_days"] == 14
    assert target["ear"] == {
        "ear_pain": None,
        "ear_discharge_reported": True,
        "ear_discharge_duration_days": 1,
        "pus_draining_from_ear": None,
        "tender_swelling_behind_ear": None,
    }
    assert all(value is None for value in target["danger_signs"].values())
    assert target["diarrhoea"] is None
    assert target["fever"] is None
    assert all(
        value is None
        for key, value in target["respiratory"].items()
        if key != "cough_duration_days"
    )


def test_canary_is_not_campaign_or_model_selection_data() -> None:
    canary = load_frozen_canary()
    campaign_dir = CANARY_PATH.parents[2] / "data/training_sources/structured_extraction_campaign_v1"
    for filename in ("canonical_records.jsonl", "chat_messages.jsonl", "language_variants.jsonl"):
        campaign_text = (campaign_dir / filename).read_text(encoding="utf-8")
        assert EXACT_INPUT not in campaign_text
        assert SPARSE_COUGH_INPUT not in campaign_text
    assert canary["isolation"]["partition"] not in {"TRAIN", "VALIDATION", "TEST"}
    assert canary["isolation"]["model_selection_eligible"] is False


def test_sparse_cough_failure_is_frozen_as_a_separate_ood_canary() -> None:
    canary = load_frozen_canary(
        SPARSE_COUGH_CANARY_PATH,
        expected_sha256=SPARSE_COUGH_CANARY_SHA256,
    )
    target = canary["expected_target"]

    assert canary["input"]["content"] == SPARSE_COUGH_INPUT
    assert canary["provenance"]["observed_training_run_id"] == (
        "251039a3-4adc-4e74-8c30-069eb8aca6de"
    )
    assert target["patient_facts"] == {
        "age_months": 22,
        "has_cough_or_difficult_breathing": True,
        "has_diarrhoea": None,
        "has_fever": None,
        "has_ear_problem": None,
    }
    assert all(value is None for value in target["danger_signs"].values())
    assert all(value is None for value in target["respiratory"].values())
    assert target["diarrhoea"] is None
    assert target["fever"] is None
    assert target["ear"] is None

    report = score_ood_canary_prediction(
        target,
        candidate_id="perfect-sparse-cough-candidate",
        canary_path=SPARSE_COUGH_CANARY_PATH,
        expected_sha256=SPARSE_COUGH_CANARY_SHA256,
    )
    assert report["passed"] is True
    assert report["model_selection_eligible"] is False


def test_perfect_prediction_passes_all_canary_scores() -> None:
    target = load_frozen_canary()["expected_target"]
    report = score_ood_canary_prediction(
        json.dumps(target), candidate_id="perfect-candidate"
    )

    assert report["passed"] is True
    assert report["parse"] == {"valid": True, "error": None}
    assert report["schema"]["valid"] is True
    assert report["unsupported_keys"] == {"count": 0, "paths": []}
    assert report["unsupported_inferences"]["count"] == 0
    assert report["semantics"]["accuracy"] == 1.0
    assert report["model_selection_eligible"] is False
    assert report["informational_only"] is True


def test_parse_schema_unsupported_key_and_inference_failures_are_separate() -> None:
    parse_report = score_ood_canary_prediction("not-json", candidate_id="parse-failure")
    assert parse_report["parse"]["valid"] is False
    assert parse_report["schema"]["valid"] is False

    target = copy.deepcopy(load_frozen_canary()["expected_target"])
    target["diagnosis"] = "ACUTE_EAR_INFECTION"
    key_report = score_ood_canary_prediction(target, candidate_id="unsupported-key")
    assert key_report["parse"]["valid"] is True
    assert key_report["schema"]["valid"] is False
    assert key_report["unsupported_keys"] == {"count": 1, "paths": ["diagnosis"]}

    target = copy.deepcopy(load_frozen_canary()["expected_target"])
    target["danger_signs"]["vomits_everything"] = False
    inference_report = score_ood_canary_prediction(target, candidate_id="inference")
    assert inference_report["schema"]["valid"] is True
    assert inference_report["unsupported_inferences"]["count"] == 1
    assert inference_report["unsupported_inferences"]["mismatches"][0]["path"] == (
        "danger_signs.vomits_everything"
    )
    assert inference_report["semantics"]["mismatch_count"] == 1

    target = copy.deepcopy(load_frozen_canary()["expected_target"])
    target["diarrhoea"] = {
        "duration_days": 2,
        "blood_in_stool": None,
        "dehydration": {
            "restless_or_irritable": None,
            "sunken_eyes": None,
            "drinking_status": None,
            "skin_pinch": None,
        },
        "cholera_in_area": None,
        "rehydration_stage": None,
        "post_rehydration": None,
    }
    pathway_report = score_ood_canary_prediction(target, candidate_id="pathway-inference")
    assert pathway_report["schema"]["valid"] is True
    assert pathway_report["unsupported_keys"]["count"] == 0
    assert pathway_report["unsupported_inferences"]["mismatches"][0]["path"] == (
        "diarrhoea"
    )


def test_canary_pin_rejects_modified_bytes(tmp_path) -> None:
    changed = tmp_path / "changed.json"
    changed.write_bytes(CANARY_PATH.read_bytes() + b"\n")
    try:
        load_frozen_canary(changed, expected_sha256=CANARY_SHA256)
    except ValueError as error:
        assert str(error) == "OOD regression canary SHA-256 mismatch"
    else:
        raise AssertionError("modified canary unexpectedly passed its hash pin")
