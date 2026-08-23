from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_variants import (
    CANDIDATE_SCHEMA_ID,
    CANDIDATE_SCHEMA_PATH,
    PILOT_CONFIG_PATH,
    ROOT,
    VARIANT_RECORD_SCHEMA_PATH,
    build_pilot_requests,
    build_source_package,
    build_variant_record,
    load_pilot_config,
    load_variant_contract,
    source_fact_specs,
    summarize_attempts,
    validate_attempt_record,
    validate_candidate,
)


ATTEMPT_SCHEMA_PATH = (
    ROOT / "configs" / "generation" / "holistic_teacher_attempt_v1.schema.json"
)


@pytest.fixture(scope="module")
def semantics() -> list[dict]:
    return load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)


@pytest.fixture(scope="module")
def parents() -> list[dict]:
    return load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)


def _candidate(semantic: dict, parent: dict, strategy_id: str) -> dict:
    # This deliberately simple text exists only in memory to exercise mechanics.
    # It is not a mock-teacher output and is never written to the repository.
    submission = parent["conversation"][0]["content"] + " Assessment recorded in full."
    return {
        "candidate_schema_id": CANDIDATE_SCHEMA_ID,
        "semantic_case_id": semantic["golden_case_id"],
        "strategy_id": strategy_id,
        "user_submission": submission,
        "fact_evidence": [
            {"fact_id": fact["fact_id"], "evidence_text": submission}
            for fact in source_fact_specs(semantic)
        ],
    }


def test_contract_and_pilot_are_explicitly_non_generating() -> None:
    contract = load_variant_contract()
    config = load_pilot_config()

    assert contract["semantic_unit"] == "WHOLE_ENCOUNTER"
    assert contract["generation_boundary"]["teacher_generates"] == [
        "PHC_WORKER_USER_SUBMISSION",
        "FACT_EVIDENCE_SPANS",
    ]
    assert contract["no_waste_policy"]["mock_teacher_allowed"] is False
    assert contract["no_waste_policy"]["persist_test_mutations"] is False
    assert config["mock_teacher"] is False
    assert config["actual_generation_authorized"] is False
    assert config["teacher_models"] == []


def test_generation_yaml_files_are_exact_json_mirrors() -> None:
    for json_path in (
        ROOT / "configs" / "generation" / "holistic_language_variant_contract_v1.json",
        PILOT_CONFIG_PATH,
    ):
        yaml_path = json_path.with_suffix(".yaml")
        assert yaml.safe_load(yaml_path.read_text(encoding="utf-8")) == json.loads(
            json_path.read_text(encoding="utf-8")
        )


def test_all_generation_schemas_are_valid_draft_2020_12() -> None:
    for path in (
        CANDIDATE_SCHEMA_PATH,
        VARIANT_RECORD_SCHEMA_PATH,
        ATTEMPT_SCHEMA_PATH,
    ):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_request_builder_is_model_independent_and_covers_same_78_cases_twice(
    semantics: list[dict], parents: list[dict]
) -> None:
    requests = build_pilot_requests()
    case_ids = {item["golden_case_id"] for item in semantics}

    assert len(semantics) == len(parents) == 78
    assert len(requests) == 156
    assert {item["semantic_case_id"] for item in requests} == case_ids
    assert {item["strategy_id"] for item in requests} == {
        "phc-concise-complete-v1",
        "phc-natural-complete-v1",
    }
    assert all(item["teacher_model"] is None for item in requests)
    assert all(item["generation_authorized"] is False for item in requests)
    parents_by_id = {item["golden_case_id"]: item for item in parents}
    for request in requests:
        rendered = request["rendered_prompt"]
        parent = parents_by_id[request["semantic_case_id"]]
        assert parent["conversation"][1]["content"] not in rendered
        assert "source_value_sha256" not in rendered
        assert "classifications_covered" not in rendered
        assert "actions_covered" not in rendered
        assert "urgent_action_required" not in rendered
        assert "IMCI-MSC-" not in rendered
    for case_id in case_ids:
        assert sum(item["semantic_case_id"] == case_id for item in requests) == 2


def test_teacher_payload_excludes_encounter_provenance_and_assistant_target(
    semantics: list[dict], parents: list[dict]
) -> None:
    package = build_source_package(semantics[0], "phc-concise-complete-v1")

    assert "encounter_id" not in package["structured_encounter"]
    assert "schema_version" not in package["structured_encounter"]
    assert all(
        fact not in {"encounter_id", "schema_version"}
        for fact in package["required_fact_ids"]
    )
    assert "canonical_assistant_response" not in package
    assert parents[0]["conversation"][1]["content"] not in json.dumps(package)
    serialized = json.dumps(package)
    assert "source_value_sha256" not in serialized
    assert "classifications_covered" not in serialized
    assert "actions_covered" not in serialized
    assert "urgent_action_required" not in serialized
    assert "IMCI-MSC-" not in serialized


def test_source_fact_contract_preserves_unknown_as_unknown(semantics: list[dict]) -> None:
    record = next(item for item in semantics if item["golden_case_id"].startswith("hpg-071-"))
    package = build_source_package(record, "phc-concise-complete-v1")
    flattened_ids = set(package["required_fact_ids"])

    assert package["unknown_values_are_not_negative"] is True
    assert package["structured_encounter"]["patient_facts"]["has_diarrhoea"] is None
    assert "patient_facts.has_diarrhoea" not in flattened_ids


def test_candidate_mutations_are_rejected_in_memory(
    semantics: list[dict], parents: list[dict]
) -> None:
    semantic = semantics[0]
    parent = parents[0]
    strategy = "phc-concise-complete-v1"
    valid = _candidate(semantic, parent, strategy)
    assert validate_candidate(valid, semantic, parent, strategy).deterministic_pass

    missing = copy.deepcopy(valid)
    missing["fact_evidence"].pop()
    assert "FACT_SET_MISMATCH" in validate_candidate(
        missing, semantic, parent, strategy
    ).error_codes

    extra = copy.deepcopy(valid)
    extra["fact_evidence"].append(
        {
            "fact_id": "fever.temperature_c",
            "evidence_text": extra["user_submission"],
        }
    )
    assert "FACT_SET_MISMATCH" in validate_candidate(
        extra, semantic, parent, strategy
    ).error_codes

    leaked = copy.deepcopy(valid)
    leaked["user_submission"] += " IMCI-MSC-EXAMPLE"
    assert "INTERNAL_IDENTIFIER_LEAKAGE" in validate_candidate(
        leaked, semantic, parent, strategy
    ).error_codes

    duplicate = copy.deepcopy(valid)
    duplicate["user_submission"] = parent["conversation"][0]["content"]
    duplicate["fact_evidence"] = [
        {"fact_id": fact["fact_id"], "evidence_text": duplicate["user_submission"]}
        for fact in source_fact_specs(semantic)
    ]
    assert "DUPLICATE_CANONICAL_USER_SUBMISSION" in validate_candidate(
        duplicate, semantic, parent, strategy
    ).error_codes


def test_variant_record_attaches_frozen_target_and_remains_training_ineligible(
    semantics: list[dict], parents: list[dict]
) -> None:
    semantic = semantics[0]
    parent = parents[0]
    request = next(
        item
        for item in build_pilot_requests()
        if item["semantic_case_id"] == semantic["golden_case_id"]
        and item["strategy_id"] == "phc-concise-complete-v1"
    )
    record = build_variant_record(
        candidate=_candidate(semantic, parent, request["strategy_id"]),
        semantic_record=semantic,
        parent_language=parent,
        request=request,
        generation_run_id="in-memory-mechanics-test",
        attempt_id="in-memory-attempt-1",
        teacher_provider="test-placeholder",
        teacher_model="test-placeholder",
        teacher_snapshot="test-placeholder",
        renderer_git_commit="0" * 40,
        generated_at="2026-08-23T00:00:00Z",
    )

    assert record["conversation"][1] == parent["conversation"][1]
    assert record["alignment"] == parent["alignment"]
    assert all("source_value_sha256" in item for item in record["fact_evidence"])
    assert record["status"] == "PENDING_HUMAN_REVIEW"
    assert record["validation"]["requires_human_semantic_review"] is True
    assert record["eligibility"]["corpus_candidate"] is False
    assert record["eligibility"]["training"] is False


def test_attempt_summary_cannot_authorize_generation_or_training() -> None:
    attempts = [
        {
            "configuration_id": "teacher-a__prompt-a",
            "status": "PENDING_HUMAN_REVIEW",
            "validation": {"deterministic_pass": True, "error_codes": []},
        },
        {
            "configuration_id": "teacher-a__prompt-a",
            "status": "DETERMINISTIC_REJECTED",
            "validation": {
                "deterministic_pass": False,
                "error_codes": ["FACT_SET_MISMATCH"],
            },
        },
    ]
    summary = summarize_attempts(attempts)

    assert summary["configurations"][0]["deterministic_pass_rate"] == 0.5
    assert summary["winner_selected"] is False
    assert summary["bulk_generation_authorized"] is False
    assert summary["training_authorized"] is False


def test_production_shaped_attempt_schema_resolves_candidate_reference(
    semantics: list[dict], parents: list[dict]
) -> None:
    candidate = _candidate(
        semantics[0], parents[0], "phc-concise-complete-v1"
    )
    record = {
        "attempt_schema_id": "edge-imci-holistic-teacher-attempt-v1",
        "generation_run_id": "in-memory-mechanics-test",
        "attempt_id": "attempt-1",
        "request_id": "request-1",
        "configuration_id": "teacher-a__phc-concise-complete-v1",
        "semantic_case_id": semantics[0]["golden_case_id"],
        "status": "PENDING_HUMAN_REVIEW",
        "teacher": {
            "provider": "test-placeholder",
            "model": "test-placeholder",
            "snapshot": "test-placeholder",
        },
        "prompt": {
            "strategy_id": "phc-concise-complete-v1",
            "prompt_id": "edge-imci-phc-concise-complete",
            "prompt_version": "1.0.0",
            "prompt_sha256": "0" * 64,
        },
        "generation_parameters": {
            "sampling_config": {"temperature": 0.2},
            "max_output_tokens": 2000,
        },
        "request_sha256": "0" * 64,
        "requested_at": "2026-08-23T00:00:00Z",
        "completed_at": "2026-08-23T00:00:01Z",
        "raw_response": json.dumps(candidate),
        "candidate": candidate,
        "validation": {
            "deterministic_pass": True,
            "error_codes": [],
            "requires_human_semantic_review": True,
        },
        "usage": {
            "input_tokens": 100,
            "output_tokens": 100,
            "cached_input_tokens": 0,
            "latency_ms": 1000,
            "retry_count": 0,
            "provider_request_id": "test-placeholder",
            "raw_usage": {"test": True},
        },
    }

    validate_attempt_record(record)


def test_infrastructure_does_not_persist_generated_outputs() -> None:
    config = json.loads(PILOT_CONFIG_PATH.read_text(encoding="utf-8"))
    assert "output_path" not in config
    assert not (ROOT / "experiments" / "runs" / config["experiment_id"]).exists()
