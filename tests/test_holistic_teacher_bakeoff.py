from __future__ import annotations

import copy
import json

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_bakeoff import (
    REVIEW_SCHEMA_ID,
    REVIEW_SCHEMA_PATH,
    SCHEDULE_SCHEMA_PATH,
    SELECTION_POLICY_PATH,
    SELECTION_POLICY_YAML_PATH,
    build_bakeoff_schedule,
    build_blind_review_item,
    derive_resume_state,
    load_selection_policy,
    summarize_bakeoff_evidence,
    validate_review_record,
)
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_variants import (
    CANDIDATE_SCHEMA_ID,
    build_pilot_requests,
    build_variant_record,
    source_fact_specs,
)


def _authorization() -> dict:
    return {
        "project_owner": "test-project-owner",
        "approved_at": "2026-08-23T00:00:00Z",
        "variant_contract_approved": True,
        "remote_calls_authorized": True,
        "budget": {"currency": "USD", "maximum_amount": 10.0},
    }


def _configuration(request: dict) -> dict:
    return {
        "configuration_id": "teacher-a__phc-concise-complete-v1",
        "teacher_provider": "test-provider",
        "teacher_model": "test-model",
        "teacher_snapshot": "test-model-2026-08-23",
        "strategy_id": request["strategy_id"],
        "prompt_id": request["prompt_id"],
        "prompt_version": request["prompt_version"],
        "prompt_sha256": request["prompt_sha256"],
        "sampling_config": {"temperature": 0.2},
        "max_output_tokens": 2000,
    }


def _schedule(*, one_unit: bool = False) -> dict:
    requests = [
        item
        for item in build_pilot_requests()
        if item["strategy_id"] == "phc-concise-complete-v1"
    ]
    schedule = build_bakeoff_schedule(
        generation_run_id="in-memory-bakeoff-run",
        created_at="2026-08-23T00:00:00Z",
        authorization=_authorization(),
        teacher_configurations=[_configuration(requests[0])],
        source_requests=requests,
    )
    if one_unit:
        schedule = copy.deepcopy(schedule)
        schedule["units"] = schedule["units"][:1]
    return schedule


def _candidate(case_id: str, strategy_id: str) -> dict:
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    parents = {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }
    submission = parents[case_id]["conversation"][0]["content"] + " Fully recorded."
    return {
        "candidate_schema_id": CANDIDATE_SCHEMA_ID,
        "semantic_case_id": case_id,
        "strategy_id": strategy_id,
        "user_submission": submission,
        "fact_evidence": [
            {"fact_id": item["fact_id"], "evidence_text": submission}
            for item in source_fact_specs(semantics[case_id])
        ],
    }


def _attempt(
    schedule: dict,
    *,
    status: str,
    attempt_number: int = 0,
    provider_request_id: str | None = None,
) -> dict:
    unit = schedule["units"][0]
    configuration = schedule["configurations"][0]
    candidate = (
        _candidate(unit["semantic_case_id"], unit["strategy_id"])
        if status in {"PENDING_HUMAN_REVIEW", "DETERMINISTIC_REJECTED"}
        else None
    )
    raw_response = (
        json.dumps(candidate)
        if candidate
        else "not-json"
        if status == "PARSE_FAILED"
        else None
    )
    return {
        "attempt_schema_id": "edge-imci-holistic-teacher-attempt-v1",
        "generation_run_id": schedule["generation_run_id"],
        "attempt_id": f"attempt-{attempt_number}",
        "request_id": unit["request_id"],
        "configuration_id": unit["configuration_id"],
        "semantic_case_id": unit["semantic_case_id"],
        "status": status,
        "teacher": {
            "provider": configuration["teacher_provider"],
            "model": configuration["teacher_model"],
            "snapshot": configuration["teacher_snapshot"],
        },
        "prompt": {
            "strategy_id": configuration["strategy_id"],
            "prompt_id": configuration["prompt_id"],
            "prompt_version": configuration["prompt_version"],
            "prompt_sha256": configuration["prompt_sha256"],
        },
        "generation_parameters": {
            "sampling_config": configuration["sampling_config"],
            "max_output_tokens": configuration["max_output_tokens"],
        },
        "request_sha256": unit["source_request_sha256"],
        "requested_at": f"2026-08-23T00:00:0{attempt_number}Z",
        "completed_at": (
            None
            if status == "REQUESTED"
            else f"2026-08-23T00:00:0{attempt_number + 1}Z"
        ),
        "raw_response": raw_response,
        "candidate": candidate,
        "validation": {
            "deterministic_pass": status
            in {"PENDING_HUMAN_REVIEW", "APPROVED_CORPUS_CANDIDATE"},
            "error_codes": [] if candidate else [status],
            "requires_human_semantic_review": True,
        },
        "usage": {
            "input_tokens": 100 if candidate else None,
            "output_tokens": 100 if candidate else None,
            "cached_input_tokens": 0 if candidate else None,
            "latency_ms": 1000 if candidate else None,
            "retry_count": attempt_number,
            "provider_request_id": provider_request_id,
            "raw_usage": {"test": True} if candidate else None,
        },
    }


def _approved_review(review_item_id: str) -> dict:
    return {
        "review_schema_id": REVIEW_SCHEMA_ID,
        "review_id": "review-result-1",
        "review_item_id": review_item_id,
        "reviewer": {
            "identity": "test-reviewer",
            "role": "PROJECT_OWNER",
            "reviewed_at": "2026-08-23T01:00:00Z",
            "blind_to_configuration": True,
        },
        "assessments": {
            "semantic_faithfulness": "PASS",
            "fact_completeness": "PASS",
            "unknown_preservation": "PASS",
            "target_leakage": "NONE",
            "answer_shaped_language": "NONE",
            "naturalness_score": 4,
            "phc_suitability_score": 4,
        },
        "error_codes": [],
        "overall_disposition": "APPROVE",
        "notes": "",
    }


def test_review_and_schedule_schemas_and_selection_policy_are_valid() -> None:
    for path in (REVIEW_SCHEMA_PATH, SCHEDULE_SCHEMA_PATH):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    policy = load_selection_policy()
    assert policy["automatic_winner_selection"] is False
    assert policy["systematic_corruption_threshold"] == "NOT_AUTOMATICALLY_INFERRED_IN_V1"
    assert yaml.safe_load(SELECTION_POLICY_YAML_PATH.read_text(encoding="utf-8")) == json.loads(
        SELECTION_POLICY_PATH.read_text(encoding="utf-8")
    )


def test_schedule_requires_explicit_authorization_and_covers_all_78_cases() -> None:
    schedule = _schedule()
    assert len(schedule["units"]) == 78
    assert len({item["request_id"] for item in schedule["units"]}) == 78
    assert len({item["review_item_id"] for item in schedule["units"]}) == 78
    assert schedule["retry_policy"] == {
        "transport_retry_limit": 1,
        "semantic_retry": False,
        "uncertain_request_policy": "RECONCILE_BEFORE_RETRY",
    }

    requests = [
        item
        for item in build_pilot_requests()
        if item["strategy_id"] == "phc-concise-complete-v1"
    ]
    authorization = _authorization()
    authorization["remote_calls_authorized"] = False
    with pytest.raises(ValidationError):
        build_bakeoff_schedule(
            generation_run_id="unauthorized",
            created_at="2026-08-23T00:00:00Z",
            authorization=authorization,
            teacher_configurations=[_configuration(requests[0])],
            source_requests=requests,
        )


def test_resume_state_never_retries_uncertain_or_semantic_outcomes() -> None:
    schedule = _schedule(one_unit=True)
    assert derive_resume_state(schedule, [])["state_counts"] == {"PENDING": 1}

    requested = _attempt(schedule, status="REQUESTED")
    assert derive_resume_state(schedule, [requested])["state_counts"] == {
        "RECONCILIATION_REQUIRED": 1
    }

    transport = _attempt(schedule, status="TRANSPORT_FAILED")
    assert derive_resume_state(schedule, [transport])["state_counts"] == {
        "RETRYABLE_TRANSPORT": 1
    }

    identified_transport = _attempt(
        schedule, status="TRANSPORT_FAILED", provider_request_id="provider-request-1"
    )
    assert derive_resume_state(schedule, [identified_transport])["state_counts"] == {
        "RECONCILIATION_REQUIRED": 1
    }

    parse_failed = _attempt(schedule, status="PARSE_FAILED")
    assert derive_resume_state(schedule, [parse_failed])["state_counts"] == {
        "TERMINAL": 1
    }
    with pytest.raises(ValueError, match="only a known transport failure"):
        derive_resume_state(
            schedule,
            [parse_failed, _attempt(schedule, status="PARSE_FAILED", attempt_number=1)],
        )


def test_one_known_transport_retry_is_allowed_and_then_terminal() -> None:
    schedule = _schedule(one_unit=True)
    first = _attempt(schedule, status="TRANSPORT_FAILED")
    second = _attempt(schedule, status="TRANSPORT_FAILED", attempt_number=1)
    state = derive_resume_state(schedule, [first, second])
    assert state["state_counts"] == {"TERMINAL_TRANSPORT_FAILURE": 1}
    assert state["execution_complete"] is True


def test_blind_review_surface_hides_target_and_configuration() -> None:
    schedule = _schedule(one_unit=True)
    unit = schedule["units"][0]
    requests = {
        (item["semantic_case_id"], item["strategy_id"]): item
        for item in build_pilot_requests()
    }
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    parents = {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }
    semantic = semantics[unit["semantic_case_id"]]
    parent = parents[unit["semantic_case_id"]]
    request = requests[(unit["semantic_case_id"], unit["strategy_id"])]
    candidate = _candidate(unit["semantic_case_id"], unit["strategy_id"])
    variant = build_variant_record(
        candidate=candidate,
        semantic_record=semantic,
        parent_language=parent,
        request=request,
        generation_run_id=schedule["generation_run_id"],
        attempt_id="attempt-0",
        teacher_provider="test-provider",
        teacher_model="test-model",
        teacher_snapshot="test-model-2026-08-23",
        renderer_git_commit="0" * 40,
        generated_at="2026-08-23T00:00:01Z",
    )
    item = build_blind_review_item(
        review_item_id=unit["review_item_id"],
        semantic_record=semantic,
        variant_record=variant,
    )
    serialized = json.dumps(item)
    assert parent["conversation"][1]["content"] not in serialized
    for hidden in (
        "configuration_id",
        "teacher_model",
        "strategy_id",
        "alignment",
        "fact_evidence",
    ):
        assert hidden not in item


def test_review_disposition_is_coherent_and_selection_remains_human() -> None:
    schedule = _schedule(one_unit=True)
    attempt = _attempt(schedule, status="PENDING_HUMAN_REVIEW")
    review = _approved_review(schedule["units"][0]["review_item_id"])
    validate_review_record(review)

    incoherent = copy.deepcopy(review)
    incoherent["assessments"]["target_leakage"] = "SUSPECTED"
    with pytest.raises(ValueError, match="must be ESCALATE"):
        validate_review_record(incoherent)

    summary = summarize_bakeoff_evidence(
        schedule=schedule,
        attempts=[attempt],
        reviews=[review],
        systematic_corruption_by_configuration={
            schedule["configurations"][0]["configuration_id"]: "NONE"
        },
        acceptance_sufficiency_by_configuration={
            schedule["configurations"][0]["configuration_id"]: "SUFFICIENT"
        },
        accounting_by_configuration={
            schedule["configurations"][0]["configuration_id"]: {
                "currency": "USD",
                "total_cost": 1.0,
            }
        },
    )
    configuration = summary["configurations"][0]
    assert configuration["eligible_for_project_owner_selection"] is True
    assert configuration["cost_per_human_approved_item"] == 1.0
    assert summary["automatic_winner_selection"] is False
    assert summary["winner_selected"] is False
    assert summary["bulk_generation_authorized"] is False
    assert summary["training_authorized"] is False
