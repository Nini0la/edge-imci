from __future__ import annotations

import json

import pytest

from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.model_io.encounter import (
    model_target_to_holistic_encounter,
    project_model_facing_encounter,
)
from edge_imci.training.dataset_policy import parent_semantic_partition
from edge_imci.training.out_of_scope_parents import (
    MANIFEST_PATH,
    PARENTS_PATH,
    build_out_of_scope_training_parents,
)


def test_out_of_scope_training_parents_rebuild_exactly_and_are_train_only() -> None:
    records = build_out_of_scope_training_parents()
    frozen = [json.loads(line) for line in PARENTS_PATH.read_text().splitlines()]
    assert records == frozen
    assert len(records) == 2
    assert {row["partition"] for row in records} == {"TRAIN"}
    assert all(parent_semantic_partition(row["parent_case_id"]) == "TRAIN" for row in records)


def test_training_parents_are_distinct_from_evaluation_cases_and_scope_rejected() -> None:
    records = build_out_of_scope_training_parents()
    evaluation_ids = {
        "hpg-077-out-of-scope-age-1",
        "hpg-078-out-of-scope-age-60",
    }
    assert not ({row["parent_case_id"] for row in records} & evaluation_ids)
    suite = {row["golden_case_id"]: row for row in load_holistic_golden_suite()}
    evaluation_targets = {
        json.dumps(project_model_facing_encounter(suite[case_id]), sort_keys=True)
        for case_id in evaluation_ids
    }
    for row in records:
        assert json.dumps(row["model_facing_target"], sort_keys=True) not in evaluation_targets
        with pytest.raises(ValueError, match="age_months"):
            model_target_to_holistic_encounter(
                row["model_facing_target"], encounter_id=row["parent_case_id"]
            )


def test_parent_targets_contain_observations_but_no_clinical_outputs() -> None:
    forbidden = {"classification", "classifications", "actions", "management", "urgency"}
    for row in build_out_of_scope_training_parents():
        assert forbidden.isdisjoint(row["model_facing_target"])
        assert row["expected_adapter_outcome"]["owner"] == "DETERMINISTIC_SCOPE_CHECKER"
        assert row["language_generation_status"] == "NOT_STARTED_REVIEWED_VARIANT_REQUIRED"


def test_parent_manifest_keeps_generation_and_training_blocked() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["training_and_evaluation_parents_disjoint"] is True
    assert manifest["authorization"] == {
        "bulk_generation_authorized": False,
        "training_authorized": False,
    }
