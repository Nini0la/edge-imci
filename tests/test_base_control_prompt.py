from __future__ import annotations

import json
from pathlib import Path

import pytest

from edge_imci.evaluation.base_control_prompt import (
    SCHEMA_INFORMED_BASE_PROMPT_ID,
    apply_schema_informed_base_prompt,
    load_schema_informed_base_system_prompt,
)
from edge_imci.evaluation.one_shot_test import (
    OneShotTestError,
    validate_candidate_prompt_treatments,
)
from edge_imci.evaluation.posthoc_base_control import (
    load_posthoc_base_control_authorization,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "configs/model_io/model_facing_encounter_v1.schema.json"
EXAMPLE = ROOT / "configs/evaluation/schema_informed_base_example_v1.json"
POSTHOC_AUTHORIZATION = (
    ROOT
    / "configs/evaluation/qwen3_0_6b_posthoc_schema_informed_base_control_v1.json"
)


def test_base_prompt_contains_complete_schema_and_valid_example() -> None:
    prompt, receipt = load_schema_informed_base_system_prompt(SCHEMA, EXAMPLE)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert json.dumps(schema, separators=(",", ":"), sort_keys=True) in prompt
    assert "Example of a schema-valid output" in prompt
    assert "do not copy its values" in prompt
    assert receipt["prompt_id"] == SCHEMA_INFORMED_BASE_PROMPT_ID
    assert all(receipt[name] for name in receipt if name.endswith("sha256"))


def test_base_prompt_replacement_does_not_mutate_frozen_rows() -> None:
    rows = [
        {
            "example_id": "example-1",
            "messages": [
                {"role": "system", "content": "historical instruction"},
                {"role": "user", "content": "findings"},
                {"role": "assistant", "content": "{}"},
            ],
        }
    ]

    prepared = apply_schema_informed_base_prompt(rows, "schema-informed")

    assert prepared[0]["messages"][0]["content"] == "schema-informed"
    assert rows[0]["messages"][0]["content"] == "historical instruction"
    assert prepared[0]["messages"][1:] == rows[0]["messages"][1:]


def test_only_base_control_may_receive_schema_informed_treatment() -> None:
    treatment = {
        "kind": "SCHEMA_INFORMED_BASE_CONTROL_V1",
        "schema_path": "configs/model_io/model_facing_encounter_v1.schema.json",
        "schema_sha256": "a" * 64,
        "example_output_path": "configs/evaluation/schema_informed_base_example_v1.json",
        "example_output_sha256": "b" * 64,
        "prompt_sha256": "c" * 64,
    }
    policy = {
        "generation": {"identical_for_all_candidates": False},
        "candidates": [
            {"role": "BASE_CONTROL", "prompt_treatment": treatment},
            {"role": "SELECTED_FINE_TUNE"},
        ],
    }
    validate_candidate_prompt_treatments(policy)

    policy["candidates"][0].pop("prompt_treatment")
    policy["candidates"][1]["prompt_treatment"] = treatment
    with pytest.raises(OneShotTestError, match="exactly the BASE_CONTROL"):
        validate_candidate_prompt_treatments(policy)


def test_posthoc_test_use_is_explicitly_scoped_and_hash_pinned() -> None:
    path, authorization, policy = load_posthoc_base_control_authorization(
        POSTHOC_AUTHORIZATION
    )

    assert path == POSTHOC_AUTHORIZATION
    assert authorization["authority"] == "PROJECT_OWNER"
    assert authorization["status"] == (
        "AUTHORIZED_POST_HOC_SCHEMA_INFORMED_BASE_CONTROL"
    )
    assert authorization["controls"]["test_partition_use_count_limit"] == 1
    assert authorization["controls"]["fine_tuned_candidate_inference_prohibited"]
    assert authorization["controls"]["untouched_test_claim_prohibited"]
    assert policy["authorization_id"] == authorization["original_evidence"][
        "authorization_id"
    ]
