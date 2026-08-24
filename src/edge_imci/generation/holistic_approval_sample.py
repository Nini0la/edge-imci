"""Prepare and execute the owner-authorized v2 teacher approval sample."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.azure_foundry import (
    OpenAIAzureResponsesTransport,
    execute_authorized_unit,
    require_authorized_execution_config,
)
from edge_imci.generation.holistic_bakeoff import (
    build_bakeoff_schedule,
    derive_resume_state,
)
from edge_imci.generation.holistic_canary_execute import (
    AppendOnlyAttemptStore,
    CanaryExecutionStopped,
    _atomic_write,
    _utc_now,
    load_secure_env,
)
from edge_imci.generation.holistic_canary_run import CANARY_EXECUTION_PATH
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_variants import (
    ROOT,
    CandidateValidation,
    build_source_package,
    validate_candidate,
)


RUN_ID = "holistic-teacher-approval-sample-gpt41-20250414-v2"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
CASES = (
    "hpg-001-all-negative",
    "hpg-076-complete-danger-plus-all-pathways",
)
PROMPTS = (
    {
        "strategy_id": "phc-concise-complete-v2",
        "prompt_id": "edge-imci-phc-concise-complete",
        "prompt_version": "2.0.0",
        "path": ROOT
        / "prompts"
        / "holistic_language_variants"
        / "phc_concise_complete_v2.txt",
    },
    {
        "strategy_id": "phc-natural-complete-v2",
        "prompt_id": "edge-imci-phc-natural-complete",
        "prompt_version": "2.0.0",
        "path": ROOT
        / "prompts"
        / "holistic_language_variants"
        / "phc_natural_complete_v2.txt",
    },
)
RESERVATION_USD = Decimal("0.02")
_V2_INTERNAL_FIELD_PATH = re.compile(
    r"\b(?:patient_facts|danger_signs|respiratory|diarrhoea|fever|ear)\."
    r"[a-z][a-z0-9_]*\b",
    re.IGNORECASE,
)
_V2_LITERAL_INTERNAL_MARKERS = (
    "IMCI-MSC-",
    "edge-imci-",
    "source_value_sha256",
    "fact_evidence",
    "candidate_schema_id",
)


def validate_candidate_v2(
    candidate: dict[str, Any],
    semantic_record: dict[str, Any],
    parent_language: dict[str, Any],
    strategy_id: str,
) -> CandidateValidation:
    """Use field-path-aware leakage matching while retaining all v1 checks."""

    baseline = validate_candidate(
        candidate, semantic_record, parent_language, strategy_id
    )
    errors = list(baseline.error_codes)
    if "INTERNAL_IDENTIFIER_LEAKAGE" in errors:
        submission = candidate.get("user_submission", "")
        genuine_leakage = any(
            marker.casefold() in submission.casefold()
            for marker in _V2_LITERAL_INTERNAL_MARKERS
        ) or _V2_INTERNAL_FIELD_PATH.search(submission) is not None
        if not genuine_leakage:
            errors.remove("INTERNAL_IDENTIFIER_LEAKAGE")
    return CandidateValidation(
        deterministic_pass=not errors,
        error_codes=tuple(errors),
        requires_human_semantic_review=True,
    )


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_artifact(name: str, value: Any) -> None:
    json_path = RUN_DIR / f"{name}.json"
    json_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (RUN_DIR / f"{name}.yaml").write_text(
        f"# Generated from experiments/generation/{RUN_ID}/{name}.json; edit canonical JSON.\n"
        + yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def _source_requests() -> list[dict[str, Any]]:
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    requests: list[dict[str, Any]] = []
    for prompt in PROMPTS:
        template = prompt["path"].read_text(encoding="utf-8")
        prompt_sha = _file_hash(prompt["path"])
        for case_id in CASES:
            package = build_source_package(semantics[case_id], prompt["strategy_id"])
            rendered = template.replace(
                "{{SOURCE_PACKAGE_JSON}}",
                json.dumps(package, ensure_ascii=False, sort_keys=True),
            )
            identity = {
                "experiment_id": "holistic-teacher-approval-sample-v2",
                "semantic_case_id": case_id,
                "strategy_id": prompt["strategy_id"],
                "prompt_id": prompt["prompt_id"],
                "prompt_version": prompt["prompt_version"],
                "prompt_sha256": prompt_sha,
                "source_package_sha256": _canonical_hash(package),
            }
            requests.append(
                {
                    "request_id": f"{case_id}__{prompt['strategy_id']}",
                    **identity,
                    "request_sha256": _canonical_hash(
                        {**identity, "rendered_prompt": rendered}
                    ),
                    "source_package": package,
                    "rendered_prompt": rendered,
                }
            )
    return requests


def prepare(*, approved_by: str, approved_at: str) -> None:
    if RUN_DIR.exists():
        raise FileExistsError(f"approval sample package already exists: {RUN_DIR}")
    RUN_DIR.mkdir(parents=True)
    requests = _source_requests()
    configurations = []
    for prompt in PROMPTS:
        configurations.append(
            {
                "configuration_id": f"azure-gpt41-20250414__{prompt['strategy_id']}",
                "teacher_provider": "AZURE_OPENAI",
                "teacher_model": "gpt-4.1",
                "teacher_snapshot": "2025-04-14",
                "strategy_id": prompt["strategy_id"],
                "prompt_id": prompt["prompt_id"],
                "prompt_version": prompt["prompt_version"],
                "prompt_sha256": _file_hash(prompt["path"]),
                "sampling_config": {"temperature": 0.7},
                "max_output_tokens": 2000,
            }
        )
    schedule = build_bakeoff_schedule(
        generation_run_id=RUN_ID,
        created_at=approved_at,
        authorization={
            "project_owner": approved_by,
            "approved_at": approved_at,
            "variant_contract_approved": True,
            "remote_calls_authorized": True,
            "budget": {"currency": "USD", "maximum_amount": 0.25},
        },
        teacher_configurations=configurations,
        source_requests=requests,
    )
    schedule["source_pins"]["validator_sha256"] = _file_hash(Path(__file__))
    execution = copy.deepcopy(_load_json(CANARY_EXECUTION_PATH))
    execution["limits"] = {"maximum_remote_attempts": 4, "maximum_budget_usd": 0.25}
    require_authorized_execution_config(execution)
    preflight = {
        "preflight_schema_id": "edge-imci-holistic-teacher-approval-sample-preflight-v2",
        "generation_run_id": RUN_ID,
        "status": "AUTHORIZED_NOT_STARTED",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "authorization_basis": (
            "Project owner delegated evaluation and generation through representative paired samples, "
            "stopping before large-scale generation."
        ),
        "case_ids": list(CASES),
        "prompt_versions": [item["prompt_version"] for item in PROMPTS],
        "scheduled_attempts": 4,
        "maximum_budget_usd": 0.25,
        "maximum_reserved_total_usd": 0.08,
        "teacher_target_blind": True,
        "provider_storage_disabled": True,
        "semantic_retries": False,
    }
    _write_artifact("azure_execution_config", execution)
    _write_artifact("schedule", schedule)
    _write_artifact("source_requests", requests)
    _write_artifact("preflight", preflight)
    (RUN_DIR / "README.md").write_text(
        "# Holistic teacher approval sample — v2\n\n"
        "This owner-authorized four-attempt sample tests the version-2 concise and natural prompts "
        "against one simple and one complete urgent four-pathway case. The teacher sees source "
        "observations only; frozen assistant responses are attached only after validation and review.\n",
        encoding="utf-8",
    )


def _state(schedule: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_state_schema_id": "edge-imci-holistic-teacher-approval-sample-state-v2",
        "generation_run_id": RUN_ID,
        "updated_at": _utc_now(),
        "remote_attempts_started": len(attempts),
        "deterministic_passes": sum(
            item["status"] == "PENDING_HUMAN_REVIEW" for item in attempts
        ),
        "deterministic_rejections": sum(
            item["status"] == "DETERMINISTIC_REJECTED" for item in attempts
        ),
        "reserved_total_usd": float(RESERVATION_USD * len(attempts)),
        "reservation_is_not_billing_evidence": True,
        "usage": {
            "input_tokens": sum(item["usage"]["input_tokens"] or 0 for item in attempts),
            "output_tokens": sum(item["usage"]["output_tokens"] or 0 for item in attempts),
            "cached_input_tokens": sum(
                item["usage"]["cached_input_tokens"] or 0 for item in attempts
            ),
        },
        "resume": derive_resume_state(schedule, attempts),
    }


def execute(*, env_path: Path, max_new_attempts: int | None = None) -> dict[str, Any]:
    execution = _load_json(RUN_DIR / "azure_execution_config.json")
    schedule = _load_json(RUN_DIR / "schedule.json")
    requests = {
        (item["semantic_case_id"], item["strategy_id"]): item
        for item in json.loads((RUN_DIR / "source_requests.json").read_text(encoding="utf-8"))
    }
    require_authorized_execution_config(execution)
    load_secure_env(env_path)
    store = AppendOnlyAttemptStore(RUN_DIR / "attempts")
    attempts = store.latest_attempts()
    resume = derive_resume_state(schedule, attempts)
    if any(
        item["resume_state"] == "RECONCILIATION_REQUIRED" for item in resume["units"]
    ):
        raise CanaryExecutionStopped("an earlier request requires reconciliation")
    completed = {item["request_id"] for item in attempts if item["status"] != "REQUESTED"}
    pending = [item for item in schedule["units"] if item["request_id"] not in completed]
    if max_new_attempts is not None:
        pending = pending[:max_new_attempts]
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    parents = {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }
    transport = OpenAIAzureResponsesTransport(execution)
    for unit in pending:
        current = store.latest_attempts()
        request = requests[(unit["semantic_case_id"], unit["strategy_id"])]
        try:
            execute_authorized_unit(
                execution_config=execution,
                schedule=schedule,
                unit=unit,
                source_request=request,
                semantic_record=semantics[unit["semantic_case_id"]],
                parent_language=parents[unit["semantic_case_id"]],
                transport=transport,
                persist_attempt=store.persist,
                requested_at=_utc_now(),
                completed_at=_utc_now,
                retry_count=0,
                remote_attempts_already_started=len(current),
                accounted_cost_usd=RESERVATION_USD * len(current),
                maximum_next_attempt_cost_usd=RESERVATION_USD,
                candidate_validator=validate_candidate_v2,
            )
        except Exception as exc:
            latest = store.latest_attempts()
            _atomic_write(RUN_DIR / "run_state.json", _state(schedule, latest))
            raise CanaryExecutionStopped(
                f"approval-sample provider call stopped ({type(exc).__name__})"
            ) from None
        _atomic_write(RUN_DIR / "run_state.json", _state(schedule, store.latest_attempts()))
    result = _state(schedule, store.latest_attempts())
    _atomic_write(RUN_DIR / "run_state.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute"))
    parser.add_argument("--approved-by", default="Niniola Adegboyega")
    parser.add_argument("--approved-at")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--max-new-attempts", type=int)
    args = parser.parse_args()
    if args.command == "prepare":
        approved_at = args.approved_at or datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        prepare(approved_by=args.approved_by, approved_at=approved_at)
        print(json.dumps({"status": "PREPARED", "generation_run_id": RUN_ID}))
        return 0
    try:
        state = execute(env_path=args.env_file, max_new_attempts=args.max_new_attempts)
    except CanaryExecutionStopped as exc:
        print(json.dumps({"status": "STOPPED", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": "OK",
                "remote_attempts_started": state["remote_attempts_started"],
                "deterministic_passes": state["deterministic_passes"],
                "deterministic_rejections": state["deterministic_rejections"],
                "usage": state["usage"],
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
