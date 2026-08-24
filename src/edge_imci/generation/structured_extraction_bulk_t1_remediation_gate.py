"""Run the 15-case remediation gate required before continuing bulk generation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

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
from edge_imci.generation.holistic_middle_gate import validate_middle_candidate
from edge_imci.generation.holistic_variants import ROOT, build_source_package
from edge_imci.generation.language_semantic_guards import validate_language_semantics


RUN_ID = "structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v1"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
AUTHORIZATION_PATH = (
    ROOT
    / "configs"
    / "generation"
    / "structured_extraction_bulk_t1_remediation_gate_v1.json"
)
EXPECTED_ATTEMPTS = 15
STYLE_CONFIGURATIONS = (
    {
        "variant_style": "NIGERIAN_ENGLISH",
        "strategy_id": "phc-nigerian-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_nigerian_english_v1_3_2.txt",
        "prompt_id": "edge-imci-phc-nigerian-english",
        "prompt_version": "1.3.2",
        "case_ids": (
            "hpg-049-fever-duration-7",
            "hpg-068-cross-four-pathways",
            "hpg-016-resp-oximeter-89-9",
        ),
        "noise_profile": [],
    },
    {
        "variant_style": "NIGERIAN_PIDGIN",
        "strategy_id": "phc-nigerian-pidgin-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_2_2.txt",
        "prompt_id": "edge-imci-phc-nigerian-pidgin",
        "prompt_version": "1.2.2",
        "case_ids": (
            "hpg-054-fever-measles-eye",
            "hpg-060-fever-test-result-unknown",
            "hpg-071-incomplete-entry-unknown",
            "hpg-020-resp-post-bronchodilator-improved",
        ),
        "noise_profile": [],
    },
    {
        "variant_style": "NOISY_TYPED_ENGLISH",
        "strategy_id": "phc-noisy-typed-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_2.txt",
        "prompt_id": "edge-imci-phc-noisy-typed-english",
        "prompt_version": "1.2.2",
        "case_ids": (
            "hpg-060-fever-test-result-unknown",
            "hpg-068-cross-four-pathways",
            "hpg-072-incomplete-multiple-groups",
            "hpg-075-contradiction-drinking",
        ),
        "noise_profile": (
            "ARTICLE_OMISSION",
            "PUNCTUATION_LOSS",
            "CASING_VARIATION",
            "SENTENCE_FRAGMENTS",
            "SPELLING_NOISE",
        ),
    },
    {
        "variant_style": "TELEGRAPHIC_PHC_NOTE",
        "strategy_id": "phc-telegraphic-note-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_telegraphic_note_v1_1_1.txt",
        "prompt_id": "edge-imci-phc-telegraphic-note",
        "prompt_version": "1.1.1",
        "case_ids": (
            "hpg-011-resp-age-12-rate-40",
            "hpg-015-resp-stridor",
            "hpg-070-cross-multiple-urgent",
            "hpg-037-diarrhoea-positive-drinking-reuse",
        ),
        "noise_profile": (
            "ABBREVIATION_DENSITY_MEDIUM",
            "SENTENCE_FRAGMENTS",
            "TELEGRAPHIC_COMPRESSION",
        ),
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_authorization() -> dict[str, Any]:
    value = _load_json(AUTHORIZATION_PATH)
    expected = {
        "authorization_id": "edge-imci-structured-extraction-bulk-t1-remediation-gate-v1",
        "status": "AUTHORIZED_FOR_TARGETED_EXECUTION",
        "authority": "PROJECT_OWNER_DELEGATION",
        "generation_run_id": RUN_ID,
        "maximum_remote_attempts": EXPECTED_ATTEMPTS,
        "semantic_retries": False,
        "teacher_target_blind": True,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"incorrect remediation authorization {key}")
    return value


def _semantics() -> dict[str, dict[str, Any]]:
    return {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }


def _parents() -> dict[str, dict[str, Any]]:
    return {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }


def build_source_requests() -> list[dict[str, Any]]:
    semantics = _semantics()
    requests: list[dict[str, Any]] = []
    for style in STYLE_CONFIGURATIONS:
        prompt_path = ROOT / style["prompt_path"]
        template = prompt_path.read_text(encoding="utf-8")
        if template.count("{{SOURCE_PACKAGE_JSON}}") != 1:
            raise ValueError(f"invalid source placeholder: {prompt_path}")
        prompt_sha = _sha256(prompt_path)
        for case_id in style["case_ids"]:
            package = build_source_package(semantics[case_id], style["strategy_id"])
            rendered = template.replace(
                "{{SOURCE_PACKAGE_JSON}}",
                json.dumps(package, ensure_ascii=False, sort_keys=True),
            )
            identity = {
                "experiment_id": "structured-extraction-bulk-t1-remediation-gate-v1",
                "semantic_case_id": case_id,
                "strategy_id": style["strategy_id"],
                "variant_style": style["variant_style"],
                "noise_profile": list(style["noise_profile"]),
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
    if len(requests) != EXPECTED_ATTEMPTS:
        raise ValueError("remediation gate must contain 15 attempts")
    return requests


def _candidate_validator(
    candidate: dict[str, Any],
    semantic_record: dict[str, Any],
    parent_language: dict[str, Any],
    strategy_id: str,
):
    baseline = validate_middle_candidate(
        candidate, semantic_record, parent_language, strategy_id
    )
    style = next(
        item for item in STYLE_CONFIGURATIONS if item["strategy_id"] == strategy_id
    )
    semantic = validate_language_semantics(
        candidate, semantic_record, variant_style=style["variant_style"]
    )
    errors = tuple(dict.fromkeys((*baseline.error_codes, *semantic.error_codes)))
    return type(baseline)(not errors, errors, True)


def _write_json(name: str, value: Any) -> None:
    path = RUN_DIR / f"{name}.json"
    if isinstance(value, dict):
        _atomic_write(path, value)
        return
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def prepare(*, approved_by: str, approved_at: str) -> dict[str, Any]:
    if RUN_DIR.exists():
        raise FileExistsError(f"remediation gate already exists: {RUN_DIR}")
    auth = load_authorization()
    requests = build_source_requests()
    RUN_DIR.mkdir(parents=True)
    configs = []
    for style in STYLE_CONFIGURATIONS:
        configs.append(
            {
                "configuration_id": (
                    "azure-gpt41-20250414__"
                    f"{style['strategy_id']}__prompt-v{style['prompt_version'].replace('.', '-')}"
                ),
                "teacher_provider": "AZURE_OPENAI",
                "teacher_model": "gpt-4.1",
                "teacher_snapshot": "2025-04-14",
                "strategy_id": style["strategy_id"],
                "prompt_id": style["prompt_id"],
                "prompt_version": style["prompt_version"],
                "prompt_sha256": _sha256(ROOT / style["prompt_path"]),
                "sampling_config": {"temperature": style.get("temperature", 0.7)},
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
            "budget": {"currency": "USD", "maximum_amount": auth["maximum_budget_usd"]},
        },
        teacher_configurations=configs,
        source_requests=requests,
    )
    schedule["source_pins"]["validator_sha256"] = _sha256(Path(__file__))
    execution = copy.deepcopy(_load_json(CANARY_EXECUTION_PATH))
    execution["limits"] = {
        "maximum_remote_attempts": EXPECTED_ATTEMPTS,
        "maximum_budget_usd": auth["maximum_budget_usd"],
    }
    require_authorized_execution_config(execution)
    preflight = {
        "preflight_schema_id": "edge-imci-structured-extraction-bulk-t1-remediation-preflight-v1",
        "generation_run_id": RUN_ID,
        "status": "AUTHORIZED_NOT_STARTED",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "authorization_id": auth["authorization_id"],
        "authorization_sha256": _sha256(AUTHORIZATION_PATH),
        "scheduled_attempts": EXPECTED_ATTEMPTS,
        "maximum_budget_usd": auth["maximum_budget_usd"],
        "maximum_reserved_total_usd": auth["reservation_per_started_attempt_usd"] * EXPECTED_ATTEMPTS,
        "teacher_target_blind": True,
        "training_authorized": False,
    }
    _write_json("azure_execution_config", execution)
    _write_json("schedule", schedule)
    _write_json("source_requests", requests)
    _write_json("preflight", preflight)
    (RUN_DIR / "README.md").write_text(
        "# Structured-extraction bulk T1 remediation gate\n\n"
        "> **Authority:** PROJECT_OWNER_DELEGATED_EXECUTION · **Lifecycle:** PREPARED\n\n"
        "Fifteen target-blind attempts recheck every semantic failure class found in T1. "
        "Passing this gate may release a separately versioned continuation; training remains unauthorized.\n",
        encoding="utf-8",
    )
    return preflight


def _state(schedule: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_state_schema_id": "edge-imci-structured-extraction-bulk-t1-remediation-state-v1",
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
        "transport_failures": sum(item["status"] == "TRANSPORT_FAILED" for item in attempts),
        "usage": {
            "input_tokens": sum(item["usage"]["input_tokens"] or 0 for item in attempts),
            "output_tokens": sum(item["usage"]["output_tokens"] or 0 for item in attempts),
            "cached_input_tokens": sum(item["usage"]["cached_input_tokens"] or 0 for item in attempts),
        },
        "resume": derive_resume_state(schedule, attempts),
    }


def execute(*, env_path: Path) -> dict[str, Any]:
    auth = load_authorization()
    execution = _load_json(RUN_DIR / "azure_execution_config.json")
    schedule = _load_json(RUN_DIR / "schedule.json")
    preflight = _load_json(RUN_DIR / "preflight.json")
    if preflight["status"] != "AUTHORIZED_NOT_STARTED":
        raise ValueError("remediation gate lacks authorized preflight")
    require_authorized_execution_config(execution)
    load_secure_env(env_path)
    requests = {
        item["request_sha256"]: item for item in json.loads((RUN_DIR / "source_requests.json").read_text())
    }
    store = AppendOnlyAttemptStore(RUN_DIR / "attempts")
    attempts = store.latest_attempts()
    resume = derive_resume_state(schedule, attempts)
    if any(item["resume_state"] == "RECONCILIATION_REQUIRED" for item in resume["units"]):
        raise CanaryExecutionStopped("an earlier request requires reconciliation")
    completed = {item["request_id"] for item in attempts if item["status"] != "REQUESTED"}
    pending = [item for item in schedule["units"] if item["request_id"] not in completed]
    semantics = _semantics()
    parents = _parents()
    transport = OpenAIAzureResponsesTransport(execution)
    reservation = Decimal(str(auth["reservation_per_started_attempt_usd"]))
    started_before = len(attempts)

    def run_one(unit: dict[str, Any], ordinal: int) -> Exception | None:
        request = requests[unit["source_request_sha256"]]
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
                remote_attempts_already_started=started_before + ordinal,
                accounted_cost_usd=reservation * (started_before + ordinal),
                maximum_next_attempt_cost_usd=reservation,
                candidate_validator=_candidate_validator,
            )
        except Exception as exc:
            unresolved = [
                item for item in store.latest_attempts()
                if item["request_id"] == unit["request_id"] and item["status"] == "REQUESTED"
            ]
            if len(unresolved) == 1:
                store.persist(
                    complete_attempt_from_transport_failure(
                        receipt=unresolved[0], completed_at=_utc_now(), latency_ms=0,
                        error_code="PROVIDER_CALL_FAILED_OUTCOME_UNCERTAIN",
                    )
                )
            return exc
        return None

    concurrency = auth["maximum_concurrency"]
    for batch_start in range(0, len(pending), concurrency):
        batch = pending[batch_start : batch_start + concurrency]
        failures = []
        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = [pool.submit(run_one, unit, batch_start + index) for index, unit in enumerate(batch)]
            for future in as_completed(futures):
                if (failure := future.result()) is not None:
                    failures.append(failure)
        _write_json("run_state", _state(schedule, store.latest_attempts()))
        if failures:
            raise CanaryExecutionStopped(
                f"remediation provider microbatch stopped after {type(failures[0]).__name__}"
            )
    result = _state(schedule, store.latest_attempts())
    _write_json("run_state", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute"))
    parser.add_argument("--approved-by", default="Niniola Adegboyega")
    parser.add_argument("--approved-at")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args()
    if args.command == "prepare":
        approved_at = args.approved_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        result = prepare(approved_by=args.approved_by, approved_at=approved_at)
        print(json.dumps({"status": "PREPARED", "attempts": result["scheduled_attempts"]}))
        return 0
    try:
        result = execute(env_path=args.env_file)
    except CanaryExecutionStopped as exc:
        print(json.dumps({"status": "STOPPED", "reason": str(exc)}))
        return 2
    print(json.dumps({"status": "OK", "attempts": result["remote_attempts_started"], "passes": result["deterministic_passes"], "rejections": result["deterministic_rejections"], "usage": result["usage"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
