"""Blind review, immutable scheduling, and resume logic for the teacher bake-off.

This module does not call a model or write generated records. A real execution
layer may persist an authorized schedule and immutable attempt records later.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from edge_imci.generation.holistic_variants import (
    ATTEMPT_SCHEMA_PATH,
    FROZEN_LANGUAGE_SHA256,
    ROOT,
    SEMANTIC_CASES_SHA256,
    build_pilot_requests,
    validate_attempt_record,
)


REVIEW_SCHEMA_ID = "edge-imci-holistic-language-variant-review-v1"
SCHEDULE_SCHEMA_ID = "edge-imci-holistic-teacher-bakeoff-schedule-v1"
SELECTION_POLICY_ID = "edge-imci-holistic-teacher-bakeoff-selection-policy-v1"

REVIEW_SCHEMA_PATH = (
    ROOT / "configs" / "generation" / "holistic_language_variant_review_v1.schema.json"
)
SCHEDULE_SCHEMA_PATH = (
    ROOT / "configs" / "generation" / "holistic_teacher_bakeoff_schedule_v1.schema.json"
)
SELECTION_POLICY_PATH = (
    ROOT / "configs" / "generation" / "holistic_teacher_bakeoff_selection_policy_v1.json"
)
SELECTION_POLICY_YAML_PATH = SELECTION_POLICY_PATH.with_suffix(".yaml")
VARIANT_CONTRACT_PATH = (
    ROOT / "configs" / "generation" / "holistic_language_variant_contract_v1.json"
)
VARIANT_VALIDATOR_PATH = ROOT / "src" / "edge_imci" / "generation" / "holistic_variants.py"

TERMINAL_GENERATION_STATUSES = frozenset(
    {
        "PARSE_FAILED",
        "DETERMINISTIC_REJECTED",
        "PENDING_HUMAN_REVIEW",
    }
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema_validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(
        _load_json(path),
        format_checker=FormatChecker(),
    )


def load_selection_policy() -> dict[str, Any]:
    policy = _load_json(SELECTION_POLICY_PATH)
    if policy.get("selection_policy_id") != SELECTION_POLICY_ID:
        raise ValueError("incorrect teacher bake-off selection policy ID")
    if policy.get("status") != "PROPOSED_FOR_PROJECT_OWNER_REVIEW":
        raise ValueError("selection policy must remain proposed until separately approved")
    if policy.get("automatic_winner_selection") is not False:
        raise ValueError("v1 must not select a teacher automatically")
    if policy.get("systematic_corruption_threshold") != "NOT_AUTOMATICALLY_INFERRED_IN_V1":
        raise ValueError("v1 must leave systematic-corruption disposition to review")
    return policy


def validate_review_record(review: Mapping[str, Any]) -> None:
    record = dict(review)
    _schema_validator(REVIEW_SCHEMA_PATH).validate(record)
    assessments = record["assessments"]
    hard_failure = any(
        (
            assessments["semantic_faithfulness"] == "FAIL",
            assessments["fact_completeness"] == "FAIL",
            assessments["unknown_preservation"] == "FAIL",
            assessments["target_leakage"] == "PRESENT",
            assessments["answer_shaped_language"] == "PRESENT",
            assessments["naturalness_score"] < 3,
            assessments["phc_suitability_score"] < 3,
            bool(record["error_codes"]),
        )
    )
    uncertain = any(
        (
            assessments["semantic_faithfulness"] == "UNSURE",
            assessments["fact_completeness"] == "UNSURE",
            assessments["unknown_preservation"] == "UNSURE",
            assessments["target_leakage"] == "SUSPECTED",
            assessments["answer_shaped_language"] == "SUSPECTED",
        )
    )
    expected = "REJECT" if hard_failure else "ESCALATE" if uncertain else "APPROVE"
    if record["overall_disposition"] != expected:
        raise ValueError(
            f"review disposition must be {expected} for the recorded assessments"
        )


def build_blind_review_item(
    *,
    review_item_id: str,
    semantic_record: Mapping[str, Any],
    variant_record: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the reviewer surface without model, strategy, or target-side data."""

    if semantic_record["golden_case_id"] != variant_record["semantic_case_id"]:
        raise ValueError("semantic and variant records refer to different cases")
    encounter = semantic_record["input"]["encounter"]
    clinical_encounter = {
        key: value
        for key, value in encounter.items()
        if key not in {"encounter_id", "schema_version"}
    }
    item = {
        "review_schema_id": REVIEW_SCHEMA_ID,
        "review_item_id": review_item_id,
        "structured_encounter": clinical_encounter,
        "user_submission": variant_record["conversation"][0]["content"],
    }
    serialized = json.dumps(item, ensure_ascii=False)
    if variant_record["conversation"][1]["content"] in serialized:
        raise ValueError("blind review item leaked target-side content")
    if any(
        key in item
        for key in (
            "configuration_id",
            "teacher_model",
            "strategy_id",
            "assistant_response",
            "alignment",
        )
    ):
        raise ValueError("blind review item leaked configuration metadata")
    return item


def build_bakeoff_schedule(
    *,
    generation_run_id: str,
    created_at: str,
    authorization: Mapping[str, Any],
    teacher_configurations: Sequence[Mapping[str, Any]],
    source_requests: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build, but do not persist or execute, one immutable authorized schedule."""

    requests = list(source_requests) if source_requests is not None else build_pilot_requests()
    configurations = [dict(item) for item in teacher_configurations]
    configuration_ids = [item["configuration_id"] for item in configurations]
    if len(configuration_ids) != len(set(configuration_ids)):
        raise ValueError("teacher configuration IDs must be unique")

    by_strategy: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for request in requests:
        by_strategy[request["strategy_id"]].append(request)

    units: list[dict[str, Any]] = []
    for configuration in configurations:
        strategy_requests = by_strategy.get(configuration["strategy_id"], [])
        if not strategy_requests:
            raise ValueError(
                f"configuration has no source requests: {configuration['configuration_id']}"
            )
        first = strategy_requests[0]
        for field in ("prompt_id", "prompt_version", "prompt_sha256"):
            if configuration[field] != first[field]:
                raise ValueError(
                    f"configuration prompt pin does not match source request: {field}"
                )
        for request in strategy_requests:
            request_suffix = request.get("request_id_suffix", "")
            if request_suffix and (
                not isinstance(request_suffix, str)
                or not request_suffix.startswith("__")
            ):
                raise ValueError("request_id_suffix must be empty or begin with '__'")
            request_id = (
                f"{generation_run_id}__{configuration['configuration_id']}__"
                f"{request['semantic_case_id']}{request_suffix}"
            )
            review_digest = hashlib.sha256(request_id.encode()).hexdigest()[:24]
            units.append(
                {
                    "request_id": request_id,
                    "configuration_id": configuration["configuration_id"],
                    "semantic_case_id": request["semantic_case_id"],
                    "strategy_id": request["strategy_id"],
                    "source_request_sha256": request["request_sha256"],
                    "review_item_id": f"review-{review_digest}",
                }
            )

    schedule = {
        "schedule_schema_id": SCHEDULE_SCHEMA_ID,
        "generation_run_id": generation_run_id,
        "experiment_id": "holistic-teacher-prompt-bakeoff-v1",
        "created_at": created_at,
        "authorization": dict(authorization),
        "source_pins": {
            "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
            "frozen_language_renderings_sha256": FROZEN_LANGUAGE_SHA256,
            "variant_contract_sha256": _sha256(VARIANT_CONTRACT_PATH),
            "validator_sha256": _sha256(VARIANT_VALIDATOR_PATH),
            "attempt_schema_sha256": _sha256(ATTEMPT_SCHEMA_PATH),
            "review_schema_sha256": _sha256(REVIEW_SCHEMA_PATH),
            "selection_policy_sha256": _sha256(SELECTION_POLICY_PATH),
            "schedule_schema_sha256": _sha256(SCHEDULE_SCHEMA_PATH),
        },
        "retry_policy": {
            "transport_retry_limit": 1,
            "semantic_retry": False,
            "uncertain_request_policy": "RECONCILE_BEFORE_RETRY",
        },
        "configurations": configurations,
        "units": units,
    }
    _schema_validator(SCHEDULE_SCHEMA_PATH).validate(schedule)
    request_ids = [item["request_id"] for item in units]
    review_ids = [item["review_item_id"] for item in units]
    if len(request_ids) != len(set(request_ids)):
        raise ValueError("schedule request IDs must be unique")
    if len(review_ids) != len(set(review_ids)):
        raise ValueError("schedule blind-review IDs must be unique")
    return schedule


def derive_resume_state(
    schedule: Mapping[str, Any], attempts: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    """Derive safe next work from an immutable schedule and immutable attempts."""

    schedule_record = dict(schedule)
    _schema_validator(SCHEDULE_SCHEMA_PATH).validate(schedule_record)
    units = {item["request_id"]: item for item in schedule_record["units"]}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_attempt_ids: set[str] = set()
    for raw_attempt in attempts:
        attempt = dict(raw_attempt)
        validate_attempt_record(attempt)
        if attempt["attempt_id"] in seen_attempt_ids:
            raise ValueError(f"duplicate attempt ID: {attempt['attempt_id']}")
        seen_attempt_ids.add(attempt["attempt_id"])
        if attempt["request_id"] not in units:
            raise ValueError(f"attempt is not part of schedule: {attempt['request_id']}")
        unit = units[attempt["request_id"]]
        for attempt_key, unit_key in (
            ("configuration_id", "configuration_id"),
            ("semantic_case_id", "semantic_case_id"),
        ):
            if attempt[attempt_key] != unit[unit_key]:
                raise ValueError(f"attempt does not match scheduled {attempt_key}")
        if attempt["request_sha256"] != unit["source_request_sha256"]:
            raise ValueError("attempt request hash does not match schedule")
        grouped[attempt["request_id"]].append(attempt)

    retry_limit = schedule_record["retry_policy"]["transport_retry_limit"]
    unit_states: list[dict[str, Any]] = []
    for request_id, unit in units.items():
        request_attempts = sorted(
            grouped.get(request_id, []), key=lambda item: item["requested_at"]
        )
        if len(request_attempts) > retry_limit + 1:
            raise ValueError(f"request exceeds transport retry limit: {request_id}")
        for index, attempt in enumerate(request_attempts):
            if attempt["usage"]["retry_count"] != index:
                raise ValueError(f"attempt retry_count is not sequential: {request_id}")
            if index:
                prior = request_attempts[index - 1]
                if prior["status"] != "TRANSPORT_FAILED":
                    raise ValueError("only a known transport failure may be retried")
                if prior["usage"]["provider_request_id"] is not None:
                    raise ValueError("provider-identified requests require reconciliation")

        latest = request_attempts[-1] if request_attempts else None
        if latest is None:
            state = "PENDING"
        elif latest["status"] in TERMINAL_GENERATION_STATUSES:
            state = "TERMINAL"
        elif latest["status"] == "REQUESTED":
            state = "RECONCILIATION_REQUIRED"
        elif latest["status"] == "TRANSPORT_FAILED":
            if latest["usage"]["provider_request_id"] is not None:
                state = "RECONCILIATION_REQUIRED"
            elif latest["usage"]["retry_count"] < retry_limit:
                state = "RETRYABLE_TRANSPORT"
            else:
                state = "TERMINAL_TRANSPORT_FAILURE"
        else:  # guarded by the attempt schema
            raise ValueError(f"unsupported attempt status: {latest['status']}")
        unit_states.append(
            {
                **unit,
                "resume_state": state,
                "attempt_count": len(request_attempts),
                "latest_attempt_id": latest["attempt_id"] if latest else None,
                "latest_status": latest["status"] if latest else None,
            }
        )

    counts = Counter(item["resume_state"] for item in unit_states)
    active_states = {"PENDING", "RETRYABLE_TRANSPORT", "RECONCILIATION_REQUIRED"}
    return {
        "generation_run_id": schedule_record["generation_run_id"],
        "unit_count": len(unit_states),
        "state_counts": {key: counts[key] for key in sorted(counts)},
        "units": unit_states,
        "execution_complete": not any(
            item["resume_state"] in active_states for item in unit_states
        ),
        "winner_selected": False,
        "bulk_generation_authorized": False,
        "training_authorized": False,
    }


def _p95(values: Sequence[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def summarize_bakeoff_evidence(
    *,
    schedule: Mapping[str, Any],
    attempts: Iterable[Mapping[str, Any]],
    reviews: Iterable[Mapping[str, Any]],
    systematic_corruption_by_configuration: Mapping[str, str] | None = None,
    acceptance_sufficiency_by_configuration: Mapping[str, str] | None = None,
    accounting_by_configuration: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Order selection evidence without automatically choosing a winner."""

    policy = load_selection_policy()
    attempt_rows = [dict(item) for item in attempts]
    resume = derive_resume_state(schedule, attempt_rows)
    units = {item["request_id"]: item for item in schedule["units"]}
    unit_by_review = {item["review_item_id"]: item for item in schedule["units"]}
    latest_by_request: dict[str, dict[str, Any]] = {}
    for attempt in sorted(attempt_rows, key=lambda item: item["requested_at"]):
        latest_by_request[attempt["request_id"]] = attempt

    review_rows = [dict(item) for item in reviews]
    reviews_by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    review_ids: set[str] = set()
    for review in review_rows:
        validate_review_record(review)
        if review["review_id"] in review_ids:
            raise ValueError(f"duplicate review ID: {review['review_id']}")
        review_ids.add(review["review_id"])
        if review["review_item_id"] not in unit_by_review:
            raise ValueError("review does not belong to the schedule")
        reviews_by_item[review["review_item_id"]].append(review)

    systematic = systematic_corruption_by_configuration or {}
    acceptance = acceptance_sufficiency_by_configuration or {}
    accounting = accounting_by_configuration or {}
    state_by_request = {item["request_id"]: item for item in resume["units"]}
    summaries: list[dict[str, Any]] = []
    minimum_reviews = policy["review_mode"]["minimum_reviews_per_candidate"]
    for configuration in schedule["configurations"]:
        configuration_id = configuration["configuration_id"]
        config_units = [
            item for item in units.values() if item["configuration_id"] == configuration_id
        ]
        latest_attempts = [
            latest_by_request[item["request_id"]]
            for item in config_units
            if item["request_id"] in latest_by_request
        ]
        reviewable_units = [
            item
            for item in config_units
            if latest_by_request.get(item["request_id"], {}).get("status")
            == "PENDING_HUMAN_REVIEW"
        ]
        config_reviews = [
            review
            for unit in config_units
            for review in reviews_by_item.get(unit["review_item_id"], [])
        ]
        dispositions = Counter(item["overall_disposition"] for item in config_reviews)
        naturalness = [
            item["assessments"]["naturalness_score"] for item in config_reviews
        ]
        suitability = [
            item["assessments"]["phc_suitability_score"] for item in config_reviews
        ]
        latency = [
            item["usage"]["latency_ms"]
            for item in latest_attempts
            if item["usage"]["latency_ms"] is not None
        ]
        execution_complete = all(
            state_by_request[item["request_id"]]["resume_state"]
            in {"TERMINAL", "TERMINAL_TRANSPORT_FAILURE"}
            for item in config_units
        )
        no_reconciliation = all(
            state_by_request[item["request_id"]]["resume_state"]
            != "RECONCILIATION_REQUIRED"
            for item in config_units
        )
        review_complete = all(
            len(reviews_by_item.get(item["review_item_id"], [])) >= minimum_reviews
            for item in reviewable_units
        )
        no_escalations = dispositions["ESCALATE"] == 0
        no_approved_leakage = all(
            review["overall_disposition"] != "APPROVE"
            or review["assessments"]["target_leakage"] == "NONE"
            for review in config_reviews
        )
        systematic_state = systematic.get(configuration_id, "UNRESOLVED")
        acceptance_state = acceptance.get(configuration_id, "UNRESOLVED")
        accounting_record = accounting.get(configuration_id)
        accounting_complete = bool(
            accounting_record
            and accounting_record.get("currency")
            and accounting_record.get("total_cost") is not None
        )
        gates = {
            "execution_complete": execution_complete,
            "no_reconciliation_outstanding": no_reconciliation,
            "review_complete": review_complete,
            "no_review_escalations_outstanding": no_escalations,
            "human_acceptance_reviewed_as_sufficient": acceptance_state
            == "SUFFICIENT",
            "systematic_corruption_reviewed_as_none": systematic_state == "NONE",
            "usage_and_cost_evidence_complete": accounting_complete,
            "no_approved_target_leakage": no_approved_leakage,
        }
        approved_count = dispositions["APPROVE"]
        total_cost = accounting_record.get("total_cost") if accounting_record else None
        summaries.append(
            {
                "configuration_id": configuration_id,
                "scheduled_unit_count": len(config_units),
                "attempted_unit_count": len(latest_attempts),
                "deterministic_pass_count": sum(
                    item["validation"]["deterministic_pass"] for item in latest_attempts
                ),
                "reviewable_unit_count": len(reviewable_units),
                "review_count": len(config_reviews),
                "human_approved_count": approved_count,
                "human_rejected_count": dispositions["REJECT"],
                "human_escalated_count": dispositions["ESCALATE"],
                "mean_naturalness_score": (
                    sum(naturalness) / len(naturalness) if naturalness else None
                ),
                "mean_phc_suitability_score": (
                    sum(suitability) / len(suitability) if suitability else None
                ),
                "p95_latency_ms": _p95(latency),
                "accounting": accounting_record,
                "cost_per_human_approved_item": (
                    total_cost / approved_count
                    if total_cost is not None and approved_count
                    else None
                ),
                "systematic_corruption_review": systematic_state,
                "human_acceptance_review": acceptance_state,
                "eligibility_gates": gates,
                "eligible_for_project_owner_selection": all(gates.values()),
            }
        )

    return {
        "selection_policy_id": SELECTION_POLICY_ID,
        "generation_run_id": schedule["generation_run_id"],
        "comparison_order": policy["comparison_order"],
        "configurations": summaries,
        "automatic_winner_selection": False,
        "winner_selected": False,
        "selected_configuration_id": None,
        "bulk_generation_authorized": False,
        "training_authorized": False,
    }


def write_selection_policy_yaml_mirror() -> None:
    import yaml

    value = _load_json(SELECTION_POLICY_PATH)
    SELECTION_POLICY_YAML_PATH.write_text(
        f"# Generated from {SELECTION_POLICY_PATH.relative_to(ROOT)}; edit canonical JSON.\n"
        + yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
