from __future__ import annotations

import json

import pytest

from edge_imci.generation import nigerian_english_v12_canary as canary


def test_authorization_is_exactly_three_calls_and_no_scale() -> None:
    authorization = canary.load_authorization()
    assert authorization["maximum_remote_attempts"] == 3
    assert authorization["maximum_budget_usd"] == 0.25
    assert authorization["semantic_retries"] is False
    assert authorization["bulk_generation_authorized"] is False
    assert authorization["training_authorized"] is False
    assert authorization["production_clinical_use_authorized"] is False


def test_requests_cover_only_nigerian_english_v12_over_matched_cases() -> None:
    requests = canary.build_source_requests()
    assert len(requests) == 3
    assert {item["prompt_version"] for item in requests} == {"1.2.0"}
    assert {item["variant_style"] for item in requests} == {"NIGERIAN_ENGLISH"}
    assert {item["semantic_case_id"] for item in requests} == {
        case_id for _, case_id in canary.CASE_SELECTION
    }
    assert all("{{SOURCE_PACKAGE_JSON}}" not in item["rendered_prompt"] for item in requests)


def test_v12_prompt_protects_area_level_malaria_context() -> None:
    prompt = canary.PROMPT_PATH.read_text(encoding="utf-8")
    assert "malaria-risk category describes the area" in prompt
    assert "Never recast it as the child's individual risk" in prompt
    assert "Malaria-risk wording refers to the area/setting" in prompt


def test_prepare_writes_three_unit_zero_call_package(tmp_path, monkeypatch) -> None:
    output = tmp_path / canary.RUN_ID
    monkeypatch.setattr(canary, "RUN_DIR", output)
    canary.prepare(approved_by="Test Owner", approved_at="2026-08-23T12:00:00Z")
    schedule = json.loads((output / "schedule.json").read_text())
    preflight = json.loads((output / "preflight.json").read_text())
    execution = json.loads((output / "azure_execution_config.json").read_text())
    assert len(schedule["units"]) == 3
    assert preflight["scheduled_attempts"] == 3
    assert preflight["maximum_reserved_total_usd"] == pytest.approx(0.09)
    assert execution["limits"] == {
        "maximum_remote_attempts": 3,
        "maximum_budget_usd": 0.25,
    }
    assert not (output / "attempts").exists()
