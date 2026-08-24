"""Targeted v2.1 regression for the four middle-gate failure modes."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
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
from edge_imci.generation.holistic_middle_gate import (
    RESERVATION_USD,
    STRATEGY_ID,
    _canonical_hash,
    _hash_bytes,
    _load_json,
    validate_middle_candidate,
)
from edge_imci.generation.holistic_variants import ROOT, build_source_package


RUN_ID = "holistic-teacher-middle-regression-gpt41-20250414-v1"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
PROMPT_PATH = (
    ROOT
    / "prompts"
    / "holistic_language_variants"
    / "phc_natural_complete_v2_1.txt"
)
PROMPT_VERSION = "2.1.0"
CASES = (
    "hpg-011-resp-age-12-rate-40",
    "hpg-041-fever-high-positive",
    "hpg-014-resp-chest-hiv-positive",
    "hpg-062-ear-acute-pain",
)


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
    results = []
    for case_id in CASES:
        package = build_source_package(semantics[case_id], STRATEGY_ID)
        rendered = template.replace(
            "{{SOURCE_PACKAGE_JSON}}",
            json.dumps(package, ensure_ascii=False, sort_keys=True),
        )
        identity = {
            "experiment_id": "holistic-teacher-middle-regression-v1",
            "semantic_case_id": case_id,
            "strategy_id": STRATEGY_ID,
            "prompt_id": "edge-imci-phc-natural-complete",
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": prompt_sha,
            "source_package_sha256": _canonical_hash(package),
        }
        results.append(
            {
                "request_id": f"{case_id}__natural-v2-1-regression",
                **identity,
                "request_sha256": _canonical_hash(
                    {**identity, "rendered_prompt": rendered}
                ),
                "source_package": package,
                "rendered_prompt": rendered,
            }
        )
    return results


def prepare(*, approved_by: str, approved_at: str) -> None:
    if RUN_DIR.exists():
        raise FileExistsError(f"regression package already exists: {RUN_DIR}")
    RUN_DIR.mkdir(parents=True)
    requests = _requests()
    configuration = {
        "configuration_id": "azure-gpt41-20250414__natural-complete-prompt-v2-1",
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
            "budget": {"currency": "USD", "maximum_amount": 0.25},
        },
        teacher_configurations=[configuration],
        source_requests=requests,
    )
    schedule["source_pins"]["validator_sha256"] = _hash_bytes(
        Path(validate_middle_candidate.__code__.co_filename).read_bytes()
    )
    execution = copy.deepcopy(_load_json(CANARY_EXECUTION_PATH))
    execution["limits"] = {"maximum_remote_attempts": 4, "maximum_budget_usd": 0.25}
    require_authorized_execution_config(execution)
    preflight = {
        "preflight_schema_id": "edge-imci-holistic-teacher-middle-regression-preflight-v1",
        "generation_run_id": RUN_ID,
        "status": "AUTHORIZED_NOT_STARTED",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "authorization_basis": (
            "Targeted remediation is within the project owner's delegated middle-gate review scope."
        ),
        "case_ids": list(CASES),
        "prompt_version": PROMPT_VERSION,
        "scheduled_attempts": 4,
        "maximum_budget_usd": 0.25,
        "maximum_reserved_total_usd": 0.08,
        "teacher_target_blind": True,
        "semantic_retries": False,
    }
    _write("azure_execution_config", execution)
    _write("schedule", schedule)
    _write("source_requests", requests)
    _write("preflight", preflight)
    (RUN_DIR / "README.md").write_text(
        "# Natural-v2.1 targeted middle regression\n\n"
        "Four attempts recheck logical connectors, epistemic qualifiers, and coordinated-list evidence spans. Large-scale generation remains unauthorized.\n",
        encoding="utf-8",
    )


def _state(schedule: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_state_schema_id": "edge-imci-holistic-teacher-middle-regression-state-v1",
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
                f"targeted-regression provider call stopped ({type(exc).__name__})"
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
