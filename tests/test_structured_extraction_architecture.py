from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from edge_imci.evaluation.holistic import evaluate_holistic_encounter
from edge_imci.evaluation.structured_extraction import (
    compare_decision_equivalence,
    parse_model_target_json,
    score_structured_extraction,
)
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.model_io import (
    canonical_model_target_json,
    model_target_to_holistic_encounter,
    project_model_facing_encounter,
    validate_model_facing_encounter,
)
from edge_imci.training.structured_extraction import (
    build_structured_extraction_record,
    format_structured_extraction_messages,
)
from edge_imci.training.dataset_policy import (
    DATASET_POLICY_PATH,
    DATASET_POLICY_YAML_PATH,
    assert_target_corpus_eligible,
    load_structured_extraction_dataset_policy,
    parent_semantic_partition,
)


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return load_holistic_golden_suite()


def _by_id(records: list[dict]) -> dict[str, dict]:
    return {record["golden_case_id"]: record for record in records}


def _approved_variant(record: dict) -> dict:
    case_id = record["golden_case_id"]
    return {
        "variant_id": f"{case_id}__teacher-natural__v1",
        "semantic_case_id": case_id,
        "status": "APPROVED_CORPUS_CANDIDATE",
        "parent_source": {"semantic_cases_sha256": "a" * 64},
        "conversation": [
            {"role": "user", "content": "The child is 18 months old; the recorded findings follow."},
            {"role": "assistant", "content": "THIS FROZEN PRESENTATION MUST NOT BECOME THE TARGET"},
        ],
        "generation_provenance": {
            "generation_run_id": "teacher-canary-v1",
            "teacher_provider": "azure-openai",
            "teacher_model": "gpt-4.1",
            "teacher_snapshot": "2025-04-14",
            "prompt_id": "phc-natural-complete",
            "prompt_version": "v2.1",
            "prompt_sha256": "b" * 64,
        },
        "review": {
            "semantic_faithfulness": "APPROVED",
            "naturalness": "APPROVED",
            "phc_suitability": "APPROVED_FOR_HACKATHON",
            "reviewer": "project-owner",
        },
        "eligibility": {"corpus_candidate": True, "training": False},
    }


def test_all_frozen_cases_project_to_the_model_contract(records: list[dict]) -> None:
    forbidden = {
        "encounter_id",
        "schema_version",
        "expected",
        "classifications",
        "actions",
        "rule_ids",
        "provenance",
    }
    for record in records:
        target = project_model_facing_encounter(record)
        validate_model_facing_encounter(target)
        assert set(target) == {
            "patient_facts",
            "danger_signs",
            "respiratory",
            "diarrhoea",
            "fever",
            "ear",
        }
        assert forbidden.isdisjoint(target)


def test_projection_reproduces_all_76_existing_in_scope_oracle_results(
    records: list[dict],
) -> None:
    for record in records[:76]:
        target = project_model_facing_encounter(record)
        encounter = model_target_to_holistic_encounter(
            target, encounter_id=f"projection-{record['golden_case_id']}"
        )
        assert evaluate_holistic_encounter(encounter).to_dict() == record["expected"][
            "evaluation"
        ]


def test_scope_boundary_ages_remain_truthful_and_are_rejected_by_adapter(
    records: list[dict],
) -> None:
    by_id = _by_id(records)
    for case_id, age in (
        ("hpg-077-out-of-scope-age-1", 1),
        ("hpg-078-out-of-scope-age-60", 60),
    ):
        target = project_model_facing_encounter(by_id[case_id])
        assert target["patient_facts"]["age_months"] == age
        with pytest.raises(ValueError, match="age_months"):
            model_target_to_holistic_encounter(target, encounter_id=case_id)


def test_unknown_is_not_interchangeable_with_negative(records: list[dict]) -> None:
    target = project_model_facing_encounter(_by_id(records)["hpg-071-incomplete-entry-unknown"])
    predicted = copy.deepcopy(target)
    predicted["patient_facts"]["has_diarrhoea"] = False
    metrics = score_structured_extraction(target, predicted)
    assert metrics.schema_valid is True
    assert metrics.whole_record_exact_match is False
    assert metrics.unknown_preservation_accuracy is not None
    assert metrics.unknown_preservation_accuracy < 1.0


def test_plan_reassessment_state_is_representable_but_not_silently_evaluated(
    records: list[dict],
) -> None:
    target = project_model_facing_encounter(_by_id(records)["hpg-028-diarrhoea-some-dehydration"])
    target["diarrhoea"]["rehydration_stage"] = "IN_PROGRESS"
    validate_model_facing_encounter(target)
    with pytest.raises(ValueError, match="corpus-ineligible"):
        assert_target_corpus_eligible(target)
    with pytest.raises(ValueError, match="treatment-stage"):
        model_target_to_holistic_encounter(target, encounter_id="plan-b-in-progress")


def test_canonical_json_is_stable_and_duplicate_keys_are_rejected(records: list[dict]) -> None:
    target = project_model_facing_encounter(records[0])
    encoded = canonical_model_target_json(target)
    assert canonical_model_target_json(json.loads(encoded)) == encoded
    assert parse_model_target_json(encoded) == target
    with pytest.raises(ValueError, match="duplicate JSON key"):
        parse_model_target_json('{"patient_facts":null,"patient_facts":null}')
    with pytest.raises(ValueError, match="non-finite JSON number"):
        parse_model_target_json('{"temperature_c":NaN}')


def test_sft_record_uses_approved_user_language_and_deterministic_target_only(
    records: list[dict],
) -> None:
    source = records[0]
    variant = _approved_variant(source)
    sft = build_structured_extraction_record(
        semantic_record=source,
        variant_record=variant,
        variant_style="NATURAL_CONVERSATIONAL_ENGLISH",
    )
    assert sft["input"] == variant["conversation"][0]
    assert sft["target"] == project_model_facing_encounter(source)
    assert sft["partition"] == parent_semantic_partition(source["golden_case_id"])
    assert sft["eligibility"] == {"corpus_candidate": True, "training": False}
    assert "THIS FROZEN PRESENTATION" not in json.dumps(sft)

    messages = format_structured_extraction_messages(sft)
    assert [message["role"] for message in messages] == ["system", "user", "assistant"]
    assert json.loads(messages[-1]["content"]) == sft["target"]
    assert "Classifications" not in messages[-1]["content"]


def test_dataset_policy_is_versioned_and_yaml_is_an_exact_mirror() -> None:
    policy = load_structured_extraction_dataset_policy()
    assert yaml.safe_load(DATASET_POLICY_YAML_PATH.read_text(encoding="utf-8")) == policy
    assert policy["generic_acquisition_mode_policy"]["add_new_model_target_label"] is False
    assert policy["contradiction_policy"]["model_outputs_derived_contradiction_label"] is False
    assert policy["longitudinal_reassessment_policy"][
        "non_null_unsupported_fields_are_corpus_eligible"
    ] is False
    assert policy["out_of_scope_age_policy"][
        "current_distinct_training_parent_cases_available"
    ] is True
    assert Path(DATASET_POLICY_PATH).is_file()


def test_parent_split_is_inherited_and_scope_boundary_cases_are_reserved_for_test(
    records: list[dict],
) -> None:
    source = records[0]
    first = build_structured_extraction_record(
        semantic_record=source,
        variant_record=_approved_variant(source),
        variant_style="NATURAL_CONVERSATIONAL_ENGLISH",
    )
    second_variant = _approved_variant(source)
    second_variant["variant_id"] += "__second-language-realization"
    second = build_structured_extraction_record(
        semantic_record=source,
        variant_record=second_variant,
        variant_style="NATURAL_CONVERSATIONAL_ENGLISH",
    )
    assert first["partition"] == second["partition"]
    assert parent_semantic_partition("hpg-077-out-of-scope-age-1") == "TEST"
    assert parent_semantic_partition("hpg-078-out-of-scope-age-60") == "TEST"
    assert parent_semantic_partition("oos-extract-young-respiratory-001") == "TRAIN"
    assert parent_semantic_partition("oos-extract-older-fever-001") == "TRAIN"


def test_contradiction_case_exports_observations_not_a_derived_label(
    records: list[dict],
) -> None:
    target = project_model_facing_encounter(
        _by_id(records)["hpg-075-contradiction-drinking"]
    )
    assert "contradiction" not in json.dumps(target).lower()
    assert target["danger_signs"]["unable_to_drink_or_breastfeed"] is False
    assert target["diarrhoea"]["dehydration"]["drinking_status"] == "UNABLE"


def test_sft_pairing_rejects_unapproved_language(records: list[dict]) -> None:
    variant = _approved_variant(records[0])
    variant["status"] = "PENDING_HUMAN_REVIEW"
    with pytest.raises(ValueError, match="approved corpus-candidate"):
        build_structured_extraction_record(
            semantic_record=records[0],
            variant_record=variant,
            variant_style="NATURAL_CONVERSATIONAL_ENGLISH",
        )


def test_exact_extraction_scores_perfectly(records: list[dict]) -> None:
    target = project_model_facing_encounter(_by_id(records)["hpg-076-complete-danger-plus-all-pathways"])
    metrics = score_structured_extraction(target, copy.deepcopy(target))
    assert metrics.schema_valid is True
    assert metrics.whole_record_exact_match is True
    assert metrics.field_accuracy == 1.0
    assert metrics.known_positive_precision == 1.0
    assert metrics.known_positive_recall == 1.0
    assert metrics.known_negative_accuracy == 1.0
    assert metrics.unknown_preservation_accuracy == 1.0
    assert metrics.measurement_accuracy == 1.0
    assert metrics.duration_accuracy == 1.0
    assert metrics.qualifier_accuracy == 1.0
    assert metrics.acquisition_mode_accuracy is None
    assert metrics.pre_post_intervention_accuracy == 1.0


def test_schema_invalid_prediction_is_visible_in_both_metric_layers(records: list[dict]) -> None:
    gold = project_model_facing_encounter(records[0])
    predicted = copy.deepcopy(gold)
    del predicted["danger_signs"]
    assert score_structured_extraction(gold, predicted).schema_valid is False
    downstream = compare_decision_equivalence(gold, predicted)
    assert downstream.predicted_pipeline_state == "SCHEMA_INVALID"
    assert downstream.decision_equivalent is False


def test_non_exact_structure_can_still_be_decision_equivalent(records: list[dict]) -> None:
    gold = project_model_facing_encounter(records[0])
    predicted = copy.deepcopy(gold)
    predicted["respiratory"] = {
        "cough_duration_days": None,
        "respiratory_rate": None,
        "chest_indrawing": None,
        "stridor_when_calm": None,
        "wheezing": None,
        "recurrent_wheeze": None,
        "child_calm": None,
        "breaths_counted_one_minute": None,
        "pulse_oximeter_available": None,
        "oxygen_saturation_percent": None,
        "hiv_exposed_or_infected": None,
        "bronchodilator_trial_completed": None,
        "post_bronchodilator_respiratory_rate": None,
        "post_bronchodilator_chest_indrawing": None,
        "post_bronchodilator_child_calm": None,
        "post_bronchodilator_breaths_counted_one_minute": None,
    }
    assert score_structured_extraction(gold, predicted).whole_record_exact_match is False
    assert compare_decision_equivalence(gold, predicted).decision_equivalent is True


def test_urgent_action_equivalence_is_separately_visible(records: list[dict]) -> None:
    gold = project_model_facing_encounter(
        _by_id(records)["hpg-002-danger-unable-to-drink-or-breastfeed"]
    )
    predicted = copy.deepcopy(gold)
    predicted["danger_signs"]["unable_to_drink_or_breastfeed"] = False
    downstream = compare_decision_equivalence(gold, predicted)
    assert downstream.urgency_equivalent is False
    assert downstream.urgent_action_equivalent is False
    assert downstream.decision_equivalent is False


def test_equivalent_scope_rejections_compare_as_decision_equivalent(
    records: list[dict],
) -> None:
    target = project_model_facing_encounter(
        _by_id(records)["hpg-077-out-of-scope-age-1"]
    )
    downstream = compare_decision_equivalence(target, copy.deepcopy(target))
    assert downstream.gold_pipeline_state == "OUT_OF_SCOPE_AGE"
    assert downstream.predicted_pipeline_state == "OUT_OF_SCOPE_AGE"
    assert downstream.prediction_accepted_by_adapter is False
    assert downstream.decision_equivalent is True
