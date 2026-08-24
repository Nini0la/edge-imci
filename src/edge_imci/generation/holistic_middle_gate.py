"""Prepare and execute the eight-case natural-v2 middle-coverage gate."""

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
from edge_imci.generation.holistic_bakeoff import build_bakeoff_schedule, derive_resume_state
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


RUN_ID = "holistic-teacher-middle-gate-gpt41-20250414-v1"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
PROMPT_PATH = (
    ROOT
    / "prompts"
    / "holistic_language_variants"
    / "phc_natural_complete_v2.txt"
)
STRATEGY_ID = "phc-natural-complete-v1"
PROMPT_VERSION = "2.0.0"
CASE_SELECTION = (
    ("ordinary_nonurgent_respiratory", "hpg-011-resp-age-12-rate-40"),
    ("diarrhoea_some_dehydration", "hpg-028-diarrhoea-some-dehydration"),
    ("fever_malaria_positive", "hpg-041-fever-high-positive"),
    ("acute_ear_infection", "hpg-062-ear-acute-pain"),
    ("incomplete_entry_acquisition", "hpg-071-incomplete-entry-unknown"),
    ("bronchodilator_reassessment", "hpg-020-resp-post-bronchodilator-improved"),
    ("nonurgent_referral", "hpg-014-resp-chest-hiv-positive"),
    ("urgent_incomplete", "hpg-073-incomplete-known-urgent"),
)
RESERVATION_USD = Decimal("0.02")
_FIELD_PATH = re.compile(
    r"\b(?:patient_facts|danger_signs|respiratory|diarrhoea|fever|ear)\."
    r"[a-z][a-z0-9_]*\b",
    re.IGNORECASE,
)
_LITERAL_INTERNAL_MARKERS = (
    "IMCI-MSC-",
    "edge-imci-",
    "source_value_sha256",
    "fact_evidence",
    "candidate_schema_id",
)


def validate_middle_candidate(
    candidate: dict[str, Any],
    semantic_record: dict[str, Any],
    parent_language: dict[str, Any],
    strategy_id: str,
) -> CandidateValidation:
    baseline = validate_candidate(candidate, semantic_record, parent_language, strategy_id)
    errors = list(baseline.error_codes)
    if "INTERNAL_IDENTIFIER_LEAKAGE" in errors:
        submission = candidate.get("user_submission", "")
        genuine = any(
            marker.casefold() in submission.casefold()
            for marker in _LITERAL_INTERNAL_MARKERS
        ) or _FIELD_PATH.search(submission) is not None
        if not genuine:
            errors.remove("INTERNAL_IDENTIFIER_LEAKAGE")
    return CandidateValidation(not errors, tuple(errors), True)


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _hash_bytes(payload.encode("utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write(name: str, value: Any) -> None:
    (RUN_DIR / f"{name}.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (RUN_DIR / f"{name}.yaml").write_text(
        f"# Generated from experiments/generation/{RUN_ID}/{name}.json; edit canonical JSON.\n"
        + yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def _requests() -> list[dict[str, Any]]:
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt_sha = _hash_bytes(PROMPT_PATH.read_bytes())
    requests = []
    for _, case_id in CASE_SELECTION:
        package = build_source_package(semantics[case_id], STRATEGY_ID)
        rendered = template.replace(
            "{{SOURCE_PACKAGE_JSON}}",
            json.dumps(package, ensure_ascii=False, sort_keys=True),
        )
        identity = {
            "experiment_id": "holistic-teacher-middle-coverage-gate-v1",
            "semantic_case_id": case_id,
            "strategy_id": STRATEGY_ID,
            "prompt_id": "edge-imci-phc-natural-complete",
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": prompt_sha,
            "source_package_sha256": _canonical_hash(package),
        }
        requests.append(
            {
                "request_id": f"{case_id}__natural-v2-middle-gate",
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
        raise FileExistsError(f"middle-gate package already exists: {RUN_DIR}")
    RUN_DIR.mkdir(parents=True)
    requests = _requests()
    configuration = {
        "configuration_id": "azure-gpt41-20250414__natural-complete-prompt-v2",
        "teacher_provider": "AZURE_OPENAI",
        "teacher_model": "gpt-4.1",
        "teacher_snapshot": "2025-04-14",
        "strategy_id": STRATEGY_ID,
        "prompt_id": "edge-imci-phc-natural-complete",
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": _hash_bytes(PROMPT_PATH.read_bytes()),
        "sampling_config": {"temperature": 0.7},
        "max_output_tokens": 2000,
    }
    schedule = build_bakeoff_schedule(
        generation_run_id=RUN_ID,
        created_at=approved_at,
        authorization={
            "project_owner": approved_by,
            "approved_at": approved_at,
            "variant_contract_approved": True,
            "remote_calls_authorized": True,
            "budget": {"currency": "USD", "maximum_amount": 0.50},
        },
        teacher_configurations=[configuration],
        source_requests=requests,
    )
    schedule["source_pins"]["validator_sha256"] = _hash_bytes(Path(__file__).read_bytes())
    execution = copy.deepcopy(_load_json(CANARY_EXECUTION_PATH))
    execution["limits"] = {"maximum_remote_attempts": 8, "maximum_budget_usd": 0.50}
    require_authorized_execution_config(execution)
    preflight = {
        "preflight_schema_id": "edge-imci-holistic-teacher-middle-gate-preflight-v1",
        "generation_run_id": RUN_ID,
        "status": "AUTHORIZED_NOT_STARTED",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "authorization_basis": "Project owner approved the proposed eight-case middle-coverage gate.",
        "case_selection": [
            {"stratum": stratum, "semantic_case_id": case_id}
            for stratum, case_id in CASE_SELECTION
        ],
        "prompt_version": PROMPT_VERSION,
        "schema_compatible_strategy_id": STRATEGY_ID,
        "scheduled_attempts": 8,
        "maximum_budget_usd": 0.50,
        "maximum_reserved_total_usd": 0.16,
        "teacher_target_blind": True,
        "semantic_retries": False,
    }
    _write("azure_execution_config", execution)
    _write("schedule", schedule)
    _write("source_requests", requests)
    _write("preflight", preflight)
    (RUN_DIR / "README.md").write_text(
        "# Natural-v2 middle-coverage gate\n\n"
        "Eight owner-authorized GPT-4.1 attempts cover the clinically and interactionally important middle strata between the two approval extremes. Large-scale generation remains unauthorized.\n",
        encoding="utf-8",
    )


def _state(schedule: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_state_schema_id": "edge-imci-holistic-teacher-middle-gate-state-v1",
        "generation_run_id": RUN_ID,
        "updated_at": _utc_now(),
        "remote_attempts_started": len(attempts),
        "deterministic_passes": sum(
            item["status"] == "PENDING_HUMAN_REVIEW" for item in attempts
        ),
        "deterministic_rejections": sum(
            item["status"] in {"PARSE_FAILED", "DETERMINISTIC_REJECTED"}
            for item in attempts
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


def execute(*, env_path: Path) -> dict[str, Any]:
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
                candidate_validator=validate_middle_candidate,
            )
        except Exception as exc:
            _atomic_write(RUN_DIR / "run_state.json", _state(schedule, store.latest_attempts()))
            raise CanaryExecutionStopped(
                f"middle-gate provider call stopped ({type(exc).__name__})"
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
    args = parser.parse_args()
    if args.command == "prepare":
        approved_at = args.approved_at or datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        prepare(approved_by=args.approved_by, approved_at=approved_at)
        print(json.dumps({"status": "PREPARED", "generation_run_id": RUN_ID}))
        return 0
    try:
        result = execute(env_path=args.env_file)
    except CanaryExecutionStopped as exc:
        print(json.dumps({"status": "STOPPED", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": "OK",
                "attempts": result["remote_attempts_started"],
                "deterministic_passes": result["deterministic_passes"],
                "deterministic_rejections": result["deterministic_rejections"],
                "usage": result["usage"],
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
