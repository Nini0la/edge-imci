"""Run the bounded Nigerian-English/noisy-English prompt-remediation canary."""

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
from edge_imci.generation.holistic_style_canary import (
    CASE_SELECTION,
    validate_style_candidate,
)
from edge_imci.generation.holistic_variants import ROOT, build_source_package


RUN_ID = "holistic-input-style-remediation-gpt41-20250414-v1"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
AUTHORIZATION_PATH = (
    ROOT
    / "configs"
    / "generation"
    / "input_language_style_remediation_authorization_v1.json"
)
RESERVATION_USD = Decimal("0.03")
STYLE_CONFIGURATIONS = (
    {
        "variant_style": "NIGERIAN_ENGLISH",
        "strategy_id": "phc-nigerian-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_nigerian_english_v1_1.txt",
        "prompt_id": "edge-imci-phc-nigerian-english",
        "prompt_version": "1.1.0",
        "noise_profile": [],
    },
    {
        "variant_style": "NOISY_TYPED_ENGLISH",
        "strategy_id": "phc-noisy-typed-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_1.txt",
        "prompt_id": "edge-imci-phc-noisy-typed-english",
        "prompt_version": "1.1.0",
        "noise_profile": [
            "ARTICLE_OMISSION",
            "PUNCTUATION_LOSS",
            "CASING_VARIATION",
            "SENTENCE_FRAGMENTS",
            "SPELLING_NOISE",
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


def load_authorization() -> dict[str, Any]:
    authorization = _load_json(AUTHORIZATION_PATH)
    expected = {
        "authorization_id": "edge-imci-input-language-style-remediation-authorization-v1",
        "status": "AUTHORIZED_FOR_BOUNDED_REMEDIATION_CANARY",
        "authority": "PROJECT_OWNER_DECISION",
        "maximum_remote_attempts": 6,
        "maximum_budget_usd": 0.5,
        "semantic_retries": False,
        "bulk_generation_authorized": False,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }
    for key, value in expected.items():
        if authorization.get(key) != value:
            raise ValueError(f"incorrect remediation authorization {key}")
    if authorization["authorized_styles"] != [
        "NIGERIAN_ENGLISH",
        "NOISY_TYPED_ENGLISH",
    ]:
        raise ValueError("remediation authorization has incorrect style scope")
    return authorization


def build_source_requests() -> list[dict[str, Any]]:
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    requests: list[dict[str, Any]] = []
    for style in STYLE_CONFIGURATIONS:
        prompt_path = ROOT / style["prompt_path"]
        template = prompt_path.read_text(encoding="utf-8")
        if template.count("{{SOURCE_PACKAGE_JSON}}") != 1:
            raise ValueError("remediation prompt must have exactly one source placeholder")
        prompt_sha = _hash_bytes(prompt_path.read_bytes())
        for stratum, case_id in CASE_SELECTION:
            package = build_source_package(semantics[case_id], style["strategy_id"])
            rendered = template.replace(
                "{{SOURCE_PACKAGE_JSON}}",
                json.dumps(package, ensure_ascii=False, sort_keys=True),
            )
            identity = {
                "experiment_id": "holistic-input-language-style-remediation-v1",
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
        raise FileExistsError(f"remediation package already exists: {RUN_DIR}")
    authorization = load_authorization()
    requests = build_source_requests()
    if len(requests) != authorization["maximum_remote_attempts"]:
        raise ValueError("remediation schedule differs from authorized attempt cap")
    RUN_DIR.mkdir(parents=True)
    configurations = []
    for style in STYLE_CONFIGURATIONS:
        prompt_path = ROOT / style["prompt_path"]
        configurations.append(
            {
                "configuration_id": (
                    f"azure-gpt41-20250414__{style['strategy_id']}__prompt-v1-1"
                ),
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
        teacher_configurations=configurations,
        source_requests=requests,
    )
    schedule["source_pins"]["validator_sha256"] = _hash_bytes(
        Path(__file__).read_bytes()
    )
    execution = copy.deepcopy(_load_json(CANARY_EXECUTION_PATH))
    execution["limits"] = {
        "maximum_remote_attempts": authorization["maximum_remote_attempts"],
        "maximum_budget_usd": authorization["maximum_budget_usd"],
    }
    require_authorized_execution_config(execution)
    preflight = {
        "preflight_schema_id": "edge-imci-input-language-style-remediation-preflight-v1",
        "generation_run_id": RUN_ID,
        "status": "AUTHORIZED_NOT_STARTED",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "authorization_id": authorization["authorization_id"],
        "authorization_sha256": _hash_bytes(AUTHORIZATION_PATH.read_bytes()),
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
        "# EdgeIMCI input-language style remediation canary\n\n"
        "> **Authority:** `PROJECT_OWNER_AUTHORIZED_CANARY` · **Lifecycle:** `PREPARED`\n\n"
        "Six target-blind GPT-4.1 attempts retest Nigerian English and noisy typed English v1.1 over the same three matched encounters. No retries, bulk generation, or training are authorized.\n",
        encoding="utf-8",
    )


def _state(schedule: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_state_schema_id": "edge-imci-input-language-style-remediation-state-v1",
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
    if preflight["status"] != "AUTHORIZED_NOT_STARTED":
        raise ValueError("remediation canary lacks authorized preflight")
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
                store.persist(
                    complete_attempt_from_transport_failure(
                        receipt=unresolved[0],
                        completed_at=_utc_now(),
                        latency_ms=0,
                        error_code="PROVIDER_CALL_FAILED_OUTCOME_UNCERTAIN",
                    )
                )
            _atomic_write(
                RUN_DIR / "run_state.json", _state(schedule, store.latest_attempts())
            )
            raise CanaryExecutionStopped(
                f"remediation provider call stopped ({type(exc).__name__})"
            ) from None
        _atomic_write(
            RUN_DIR / "run_state.json", _state(schedule, store.latest_attempts())
        )
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


if __name__ == "__main__":
    raise SystemExit(main())
