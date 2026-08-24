"""Prepare and execute the bounded EdgeIMCI input-language style canary."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.azure_foundry import (
    OpenAIAzureResponsesTransport,
    complete_attempt_from_transport_failure,
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
from edge_imci.generation.holistic_middle_gate import validate_middle_candidate
from edge_imci.generation.holistic_variants import (
    ROOT,
    CandidateValidation,
    build_source_package,
)
from edge_imci.generation.language_semantic_guards import (
    load_style_contract,
    validate_language_semantics,
)


RUN_ID = "holistic-input-style-canary-gpt41-20250414-v1"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
RESERVATION_USD = Decimal("0.03")
CASE_SELECTION = (
    ("post_intervention_and_measurement", "hpg-020-resp-post-bronchodilator-improved"),
    ("connector_and_epistemic_qualifier", "hpg-041-fever-high-positive"),
    ("unknown_preservation", "hpg-071-incomplete-entry-unknown"),
)
STYLE_CONFIGURATIONS = (
    {
        "variant_style": "NIGERIAN_ENGLISH",
        "strategy_id": "phc-nigerian-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_nigerian_english_v1.txt",
        "prompt_id": "edge-imci-phc-nigerian-english",
        "prompt_version": "1.0.0",
        "noise_profile": [],
    },
    {
        "variant_style": "NIGERIAN_PIDGIN",
        "strategy_id": "phc-nigerian-pidgin-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1.txt",
        "prompt_id": "edge-imci-phc-nigerian-pidgin",
        "prompt_version": "1.0.0",
        "noise_profile": [],
    },
    {
        "variant_style": "NOISY_TYPED_ENGLISH",
        "strategy_id": "phc-noisy-typed-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1.txt",
        "prompt_id": "edge-imci-phc-noisy-typed-english",
        "prompt_version": "1.0.0",
        "noise_profile": [
            "ARTICLE_OMISSION",
            "PUNCTUATION_LOSS",
            "CASING_VARIATION",
            "SENTENCE_FRAGMENTS",
            "SPELLING_NOISE",
        ],
    },
    {
        "variant_style": "TELEGRAPHIC_PHC_NOTE",
        "strategy_id": "phc-telegraphic-note-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_telegraphic_note_v1.txt",
        "prompt_id": "edge-imci-phc-telegraphic-note",
        "prompt_version": "1.0.0",
        "noise_profile": [
            "ABBREVIATION_DENSITY_MEDIUM",
            "SENTENCE_FRAGMENTS",
            "TELEGRAPHIC_COMPRESSION",
        ],
    },
)


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


def _styles_by_strategy() -> dict[str, dict[str, Any]]:
    return {item["strategy_id"]: item for item in STYLE_CONFIGURATIONS}


def validate_style_candidate(
    candidate: dict[str, Any],
    semantic_record: dict[str, Any],
    parent_language: dict[str, Any],
    strategy_id: str,
) -> CandidateValidation:
    baseline = validate_middle_candidate(
        candidate, semantic_record, parent_language, strategy_id
    )
    style = _styles_by_strategy()[strategy_id]
    semantic = validate_language_semantics(
        candidate,
        semantic_record,
        variant_style=style["variant_style"],
    )
    errors = tuple(dict.fromkeys((*baseline.error_codes, *semantic.error_codes)))
    return CandidateValidation(not errors, errors, True)


def _requests() -> list[dict[str, Any]]:
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    requests: list[dict[str, Any]] = []
    for style in STYLE_CONFIGURATIONS:
        prompt_path = ROOT / style["prompt_path"]
        template = prompt_path.read_text(encoding="utf-8")
        if template.count("{{SOURCE_PACKAGE_JSON}}") != 1:
            raise ValueError("style prompt must contain exactly one source-package placeholder")
        prompt_sha = _hash_bytes(prompt_path.read_bytes())
        for stratum, case_id in CASE_SELECTION:
            package = build_source_package(semantics[case_id], style["strategy_id"])
            rendered = template.replace(
                "{{SOURCE_PACKAGE_JSON}}",
                json.dumps(package, ensure_ascii=False, sort_keys=True),
            )
            identity = {
                "experiment_id": "holistic-input-language-style-canary-v1",
                "semantic_case_id": case_id,
                "strategy_id": style["strategy_id"],
                "variant_style": style["variant_style"],
                "noise_profile": style["noise_profile"],
                "stratum": stratum,
                "prompt_id": style["prompt_id"],
                "prompt_version": style["prompt_version"],
                "prompt_sha256": prompt_sha,
                "source_package_sha256": _canonical_hash(package),
            }
            requests.append(
                {
                    "request_id": f"{case_id}__{style['strategy_id']}",
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
        raise FileExistsError(f"style-canary package already exists: {RUN_DIR}")
    contract = load_style_contract()
    authorization = contract["authorization"]
    if authorization["maximum_remote_attempts"] != len(CASE_SELECTION) * len(
        STYLE_CONFIGURATIONS
    ):
        raise ValueError("style contract attempt cap differs from canary design")
    RUN_DIR.mkdir(parents=True)
    requests = _requests()
    teacher_configurations = []
    for style in STYLE_CONFIGURATIONS:
        prompt_path = ROOT / style["prompt_path"]
        teacher_configurations.append(
            {
                "configuration_id": f"azure-gpt41-20250414__{style['strategy_id']}",
                "teacher_provider": "AZURE_OPENAI",
                "teacher_model": "gpt-4.1",
                "teacher_snapshot": "2025-04-14",
                "strategy_id": style["strategy_id"],
                "prompt_id": style["prompt_id"],
                "prompt_version": style["prompt_version"],
                "prompt_sha256": _hash_bytes(prompt_path.read_bytes()),
                "sampling_config": {"temperature": 0.7},
                "max_output_tokens": 2200,
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
            "budget": {
                "currency": "USD",
                "maximum_amount": authorization["maximum_budget_usd"],
            },
        },
        teacher_configurations=teacher_configurations,
        source_requests=requests,
    )
    schedule["source_pins"]["validator_sha256"] = _hash_bytes(Path(__file__).read_bytes())
    execution = copy.deepcopy(_load_json(CANARY_EXECUTION_PATH))
    execution["limits"] = {
        "maximum_remote_attempts": authorization["maximum_remote_attempts"],
        "maximum_budget_usd": authorization["maximum_budget_usd"],
    }
    require_authorized_execution_config(execution)
    preflight = {
        "preflight_schema_id": "edge-imci-input-language-style-canary-preflight-v1",
        "generation_run_id": RUN_ID,
        "status": "AUTHORIZED_NOT_STARTED",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "authorization_basis": "Project owner authorized the four bounded input-language canaries and hackathon-scoped Pidgin review.",
        "style_contract_id": contract["contract_id"],
        "canary_source_pins": {
            "style_contract_sha256": _hash_bytes(
                (
                    ROOT
                    / "configs/generation/input_language_style_contract_v1.json"
                ).read_bytes()
            ),
            "style_canary_runner_sha256": _hash_bytes(Path(__file__).read_bytes()),
        },
        "case_selection": [
            {"stratum": stratum, "semantic_case_id": case_id}
            for stratum, case_id in CASE_SELECTION
        ],
        "styles": [
            {
                "variant_style": style["variant_style"],
                "strategy_id": style["strategy_id"],
                "noise_profile": style["noise_profile"],
            }
            for style in STYLE_CONFIGURATIONS
        ],
        "scheduled_attempts": len(requests),
        "maximum_budget_usd": authorization["maximum_budget_usd"],
        "maximum_reserved_total_usd": float(RESERVATION_USD * len(requests)),
        "teacher_target_blind": True,
        "semantic_retries": False,
        "bulk_generation_authorized": False,
        "training_authorized": False,
    }
    _write("azure_execution_config", execution)
    _write("schedule", schedule)
    _write("source_requests", requests)
    _write("preflight", preflight)
    (RUN_DIR / "README.md").write_text(
        "# EdgeIMCI input-language style canary\n\n"
        "> **Authority:** `PROJECT_OWNER_AUTHORIZED_CANARY` · **Lifecycle:** `PREPARED`\n\n"
        "Twelve bounded, target-blind GPT-4.1 attempts compare Nigerian English, Nigerian Pidgin, noisy typed English and telegraphic PHC notes over the same three parent encounters. Bulk generation and training remain unauthorized.\n",
        encoding="utf-8",
    )


def _state(schedule: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_state_schema_id": "edge-imci-input-language-style-canary-state-v1",
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
    preflight = _load_json(RUN_DIR / "preflight.json")
    if preflight.get("status") != "AUTHORIZED_NOT_STARTED":
        raise ValueError("style canary lacks authorized preflight")
    require_authorized_execution_config(execution)
    load_secure_env(env_path)
    requests = {
        (item["semantic_case_id"], item["strategy_id"]): item
        for item in json.loads(
            (RUN_DIR / "source_requests.json").read_text(encoding="utf-8")
        )
    }
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
                candidate_validator=validate_style_candidate,
            )
        except Exception as exc:
            latest = store.latest_attempts()
            unresolved = [
                item
                for item in latest
                if item["request_id"] == unit["request_id"]
                and item["status"] == "REQUESTED"
            ]
            if len(unresolved) == 1:
                failure = complete_attempt_from_transport_failure(
                    receipt=unresolved[0],
                    completed_at=_utc_now(),
                    latency_ms=0,
                    error_code="PROVIDER_CALL_FAILED_OUTCOME_UNCERTAIN",
                )
                store.persist(failure)
            _atomic_write(RUN_DIR / "run_state.json", _state(schedule, store.latest_attempts()))
            raise CanaryExecutionStopped(
                f"style-canary provider call stopped ({type(exc).__name__})"
            ) from None
        _atomic_write(RUN_DIR / "run_state.json", _state(schedule, store.latest_attempts()))
    result = _state(schedule, store.latest_attempts())
    _atomic_write(RUN_DIR / "run_state.json", result)
    return result


def reconcile_uncertain_requested() -> dict[str, Any]:
    """Close one historical dangling receipt without retrying its request."""

    store = AppendOnlyAttemptStore(RUN_DIR / "attempts")
    unresolved = [item for item in store.latest_attempts() if item["status"] == "REQUESTED"]
    if len(unresolved) != 1:
        raise ValueError("reconciliation requires exactly one dangling REQUESTED receipt")
    failure = complete_attempt_from_transport_failure(
        receipt=unresolved[0],
        completed_at=_utc_now(),
        latency_ms=0,
        error_code="PROVIDER_CALL_FAILED_OUTCOME_UNCERTAIN",
    )
    store.persist(failure)
    schedule = _load_json(RUN_DIR / "schedule.json")
    state = _state(schedule, store.latest_attempts())
    _atomic_write(RUN_DIR / "run_state.json", state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute", "reconcile-uncertain"))
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
    if args.command == "reconcile-uncertain":
        result = reconcile_uncertain_requested()
        print(
            json.dumps(
                {
                    "status": "RECONCILED_WITHOUT_RETRY",
                    "attempts": result["remote_attempts_started"],
                }
            )
        )
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


if __name__ == "__main__":
    raise SystemExit(main())
