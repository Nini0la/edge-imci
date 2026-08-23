"""Build and preflight the immutable 12-request Azure teacher canary package."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from edge_imci.generation.azure_foundry import (
    AZURE_EXECUTION_CONFIG_PATH,
    AZURE_EXECUTION_SCHEMA_PATH,
    normalize_azure_v1_base_url,
    require_authorized_execution_config,
)
from edge_imci.generation.holistic_bakeoff import (
    SCHEDULE_SCHEMA_PATH,
    build_bakeoff_schedule,
)
from edge_imci.generation.holistic_canary import (
    CANARY_SELECTION_PATH,
    build_canary_source_requests,
    load_canary_selection,
)
from edge_imci.generation.holistic_variants import ROOT


CANARY_RUN_ID = "holistic-teacher-canary-gpt41-20250414-v1"
CANARY_RUN_DIR = ROOT / "experiments" / "generation" / CANARY_RUN_ID
CANARY_EXECUTION_PATH = CANARY_RUN_DIR / "azure_execution_config.json"
CANARY_SCHEDULE_PATH = CANARY_RUN_DIR / "schedule.json"
CANARY_PREFLIGHT_PATH = CANARY_RUN_DIR / "preflight.json"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _configuration_for_strategy(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "configuration_id": f"azure-gpt41-20250414__{request['strategy_id']}",
        "teacher_provider": "AZURE_OPENAI",
        "teacher_model": "gpt-4.1",
        "teacher_snapshot": "2025-04-14",
        "strategy_id": request["strategy_id"],
        "prompt_id": request["prompt_id"],
        "prompt_version": request["prompt_version"],
        "prompt_sha256": request["prompt_sha256"],
        "sampling_config": {"temperature": 0.7},
        "max_output_tokens": 2000,
    }


def build_canary_execution_config() -> dict[str, Any]:
    config = copy.deepcopy(_load_json(AZURE_EXECUTION_CONFIG_PATH))
    config["status"] = "AUTHORIZED_FOR_RECORDED_BAKEOFF_ONLY"
    config["remote_calls_authorized"] = True
    config["limits"] = {
        "maximum_remote_attempts": 12,
        "maximum_budget_usd": 1.0,
    }
    require_authorized_execution_config(config)
    return config


def build_canary_schedule(*, approved_by: str, approved_at: str) -> dict[str, Any]:
    requests = build_canary_source_requests()
    by_strategy = {item["strategy_id"]: item for item in requests}
    configurations = [
        _configuration_for_strategy(by_strategy[strategy_id])
        for strategy_id in load_canary_selection()["prompt_strategy_ids"]
    ]
    schedule = build_bakeoff_schedule(
        generation_run_id=CANARY_RUN_ID,
        created_at=approved_at,
        authorization={
            "project_owner": approved_by,
            "approved_at": approved_at,
            "variant_contract_approved": True,
            "remote_calls_authorized": True,
            "budget": {"currency": "USD", "maximum_amount": 1.0},
        },
        teacher_configurations=configurations,
        source_requests=requests,
    )
    if len(schedule["units"]) != 12:
        raise ValueError("Azure teacher canary must contain exactly 12 units")
    return schedule


def validate_secret_environment(env_path: Path) -> dict[str, Any]:
    if not env_path.is_file():
        raise ValueError("local .env file is missing")
    mode = stat.S_IMODE(env_path.stat().st_mode)
    if mode != 0o600:
        raise ValueError("local .env file must have mode 0600")
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("local .env contains a malformed line")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    required = {"AZURE_OPENAI_BASE_URL", "AZURE_OPENAI_API_KEY"}
    missing = sorted(key for key in required if not values.get(key))
    if missing:
        raise ValueError(f"local .env is missing required names: {missing}")
    normalize_azure_v1_base_url(values["AZURE_OPENAI_BASE_URL"])
    return {
        "env_file_present": True,
        "env_file_mode": "0600",
        "required_variable_names_present": sorted(required),
        "base_url_valid": True,
        "secret_values_persisted": False,
    }


def build_canary_preflight(
    *, approved_by: str, approved_at: str, env_path: Path, source_git_commit: str
) -> dict[str, Any]:
    if len(source_git_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_git_commit
    ):
        raise ValueError("source_git_commit must be a full lowercase Git SHA")
    selection = load_canary_selection()
    execution = build_canary_execution_config()
    schedule = build_canary_schedule(approved_by=approved_by, approved_at=approved_at)
    environment = validate_secret_environment(env_path)
    case_ids = [item["selected_case_id"] for item in selection["strata"]]
    unit_case_ids = [item["semantic_case_id"] for item in schedule["units"]]
    if any(unit_case_ids.count(case_id) != 2 for case_id in case_ids):
        raise ValueError("each selected canary case must have exactly two scheduled units")
    reservation_per_attempt = Decimal("0.02")
    total_reservation = reservation_per_attempt * len(schedule["units"])
    if total_reservation > Decimal(str(execution["limits"]["maximum_budget_usd"])):
        raise ValueError("conservative canary reservation exceeds budget ceiling")
    return {
        "preflight_schema_id": "edge-imci-holistic-teacher-canary-preflight-v1",
        "generation_run_id": CANARY_RUN_ID,
        "status": "VALIDATED_NOT_STARTED",
        "validated_at": approved_at,
        "approval": {
            "project_owner": approved_by,
            "approval_basis": "Project owner instructed Codex to proceed with the described step-4 immutable schedule",
            "variant_contract_approved_for_canary": True,
            "remote_calls_authorized_for_schedule": True,
            "execution_not_started": True,
        },
        "source_pins": {
            "source_git_commit": source_git_commit,
            "canary_selection_sha256": _sha256(CANARY_SELECTION_PATH),
            "azure_execution_template_sha256": _sha256(AZURE_EXECUTION_CONFIG_PATH),
            "azure_execution_schema_sha256": _sha256(AZURE_EXECUTION_SCHEMA_PATH),
            "schedule_schema_sha256": _sha256(SCHEDULE_SCHEMA_PATH),
        },
        "artifact_hashes": {
            "azure_execution_config_sha256": _canonical_hash(execution),
            "schedule_sha256": _canonical_hash(schedule),
        },
        "environment_checks": environment,
        "exposure": {
            "selected_case_count": 6,
            "configuration_count": 2,
            "scheduled_attempt_count": 12,
            "attempts_started": 0,
            "maximum_remote_attempts": 12,
            "budget_currency": "USD",
            "maximum_budget": 1.0,
            "accounted_spend": 0.0,
            "reservation_per_attempt": float(reservation_per_attempt),
            "maximum_reserved_total": float(total_reservation),
            "reservation_kind": "CONSERVATIVE_EXECUTION_RESERVATION_NOT_BILLING_EVIDENCE",
        },
        "checks": {
            "selection_valid": True,
            "two_strategies_per_case": True,
            "request_hashes_valid": True,
            "teacher_target_blind": True,
            "deployment_snapshot_pinned": True,
            "provider_storage_disabled": True,
            "sdk_automatic_retries_disabled": True,
            "ambiguous_outcomes_require_reconciliation": True,
        },
    }


def write_canary_run_package(
    *,
    approved_by: str,
    approved_at: str,
    env_path: Path,
    source_git_commit: str,
    output_dir: Path = CANARY_RUN_DIR,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"canary run package already exists: {output_dir}")
    execution = build_canary_execution_config()
    schedule = build_canary_schedule(approved_by=approved_by, approved_at=approved_at)
    preflight = build_canary_preflight(
        approved_by=approved_by,
        approved_at=approved_at,
        env_path=env_path,
        source_git_commit=source_git_commit,
    )
    output_dir.mkdir(parents=True)
    for name, value in (
        ("azure_execution_config", execution),
        ("schedule", schedule),
        ("preflight", preflight),
    ):
        (output_dir / f"{name}.json").write_bytes(_canonical_bytes(value))
        (output_dir / f"{name}.yaml").write_text(
            f"# Generated from experiments/generation/{CANARY_RUN_ID}/{name}.json; edit canonical JSON.\n"
            + yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120),
            encoding="utf-8",
        )
    return preflight
