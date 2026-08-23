from __future__ import annotations

import json

import yaml
from jsonschema import Draft202012Validator

from edge_imci.generation.holistic_canary import (
    CANARY_SELECTION_PATH,
    CANARY_SELECTION_SCHEMA_PATH,
    CANARY_SELECTION_YAML_PATH,
    build_canary_source_requests,
    derive_canary_case_ids,
    load_canary_selection,
)


EXPECTED_CASE_IDS = [
    "hpg-001-all-negative",
    "hpg-020-resp-post-bronchodilator-improved",
    "hpg-068-cross-four-pathways",
    "hpg-076-complete-danger-plus-all-pathways",
    "hpg-072-incomplete-multiple-groups",
    "hpg-073-incomplete-known-urgent",
]


def test_canary_selection_schema_pins_and_yaml_mirror_are_valid() -> None:
    schema = json.loads(CANARY_SELECTION_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    selection = load_canary_selection()

    assert selection["status"] == "SELECTED_NOT_AUTHORIZED_FOR_REMOTE_CALLS"
    assert selection["remote_calls_authorized"] is False
    assert [item["selected_case_id"] for item in selection["strata"]] == EXPECTED_CASE_IDS
    assert yaml.safe_load(CANARY_SELECTION_YAML_PATH.read_text(encoding="utf-8")) == json.loads(
        CANARY_SELECTION_PATH.read_text(encoding="utf-8")
    )


def test_canary_selection_is_derived_from_frozen_case_properties() -> None:
    assert derive_canary_case_ids() == EXPECTED_CASE_IDS


def test_canary_builds_two_blind_unauthorized_requests_per_case() -> None:
    requests = build_canary_source_requests()

    assert len(requests) == 12
    assert [item["semantic_case_id"] for item in requests[::2]] == EXPECTED_CASE_IDS
    assert all(item["generation_authorized"] is False for item in requests)
    assert all(item["teacher_model"] is None for item in requests)
    for offset in range(0, len(requests), 2):
        pair = requests[offset : offset + 2]
        assert {item["strategy_id"] for item in pair} == {
            "phc-concise-complete-v1",
            "phc-natural-complete-v1",
        }
        assert len({item["request_sha256"] for item in pair}) == 2
