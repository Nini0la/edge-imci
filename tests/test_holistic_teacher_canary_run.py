from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from edge_imci.generation.holistic_canary_run import (
    CANARY_RUN_ID,
    build_canary_execution_config,
    build_canary_preflight,
    build_canary_schedule,
    validate_secret_environment,
    write_canary_run_package,
)


APPROVED_AT = "2026-08-23T06:07:16Z"


def _env(path: Path) -> Path:
    path.write_text(
        "AZURE_OPENAI_BASE_URL=https://fixture.openai.azure.com/openai/v1/\n"
        "AZURE_OPENAI_API_KEY=fixture-secret-never-persisted\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def test_run_specific_execution_and_schedule_are_exactly_bounded() -> None:
    execution = build_canary_execution_config()
    schedule = build_canary_schedule(approved_by="Test Owner", approved_at=APPROVED_AT)

    assert execution["status"] == "AUTHORIZED_FOR_RECORDED_BAKEOFF_ONLY"
    assert execution["limits"] == {
        "maximum_remote_attempts": 12,
        "maximum_budget_usd": 1.0,
    }
    assert schedule["generation_run_id"] == CANARY_RUN_ID
    assert len(schedule["units"]) == 12
    assert len({item["request_id"] for item in schedule["units"]}) == 12
    assert len({item["review_item_id"] for item in schedule["units"]}) == 12
    assert {item["teacher_snapshot"] for item in schedule["configurations"]} == {
        "2025-04-14"
    }
    assert all(
        item["sampling_config"] == {"temperature": 0.7}
        and item["max_output_tokens"] == 2000
        for item in schedule["configurations"]
    )


def test_environment_preflight_never_returns_secret_values(tmp_path: Path) -> None:
    result = validate_secret_environment(_env(tmp_path / ".env"))
    serialized = json.dumps(result)

    assert result["env_file_mode"] == "0600"
    assert result["base_url_valid"] is True
    assert "fixture-secret" not in serialized
    assert "fixture.openai.azure.com" not in serialized

    bad = _env(tmp_path / "bad.env")
    bad.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        validate_secret_environment(bad)


def test_preflight_reports_zero_calls_and_conservative_exposure(tmp_path: Path) -> None:
    preflight = build_canary_preflight(
        approved_by="Test Owner",
        approved_at=APPROVED_AT,
        env_path=_env(tmp_path / ".env"),
        source_git_commit="a" * 40,
    )

    assert preflight["status"] == "VALIDATED_NOT_STARTED"
    assert preflight["exposure"]["scheduled_attempt_count"] == 12
    assert preflight["exposure"]["attempts_started"] == 0
    assert preflight["exposure"]["accounted_spend"] == 0.0
    assert preflight["exposure"]["maximum_reserved_total"] == 0.24
    assert all(preflight["checks"].values())


def test_writer_creates_json_yaml_mirrors_once(tmp_path: Path) -> None:
    destination = tmp_path / CANARY_RUN_ID
    write_canary_run_package(
        approved_by="Test Owner",
        approved_at=APPROVED_AT,
        env_path=_env(tmp_path / ".env"),
        source_git_commit="a" * 40,
        output_dir=destination,
    )
    for name in ("azure_execution_config", "schedule", "preflight"):
        canonical = json.loads((destination / f"{name}.json").read_text(encoding="utf-8"))
        mirror = yaml.safe_load((destination / f"{name}.yaml").read_text(encoding="utf-8"))
        assert mirror == canonical
    with pytest.raises(FileExistsError):
        write_canary_run_package(
            approved_by="Test Owner",
            approved_at=APPROVED_AT,
            env_path=_env(tmp_path / "another.env"),
            source_git_commit="a" * 40,
            output_dir=destination,
        )
