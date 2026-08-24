from __future__ import annotations

import json

import pytest

from edge_imci.generation import nigerian_english_v12_pilot as pilot


def test_pilot_authorization_is_24_calls_one_dollar_and_no_scale() -> None:
    authorization = pilot.load_authorization()
    assert authorization["maximum_remote_attempts"] == 24
    assert authorization["maximum_budget_usd"] == 1.0
    assert authorization["semantic_retries"] is False
    assert authorization["controlled_pilot_authorized"] is True
    assert authorization["bulk_generation_authorized"] is False
    assert authorization["training_authorized"] is False


def test_selection_has_24_distinct_new_eligible_parents() -> None:
    selection = pilot.load_selection()
    case_ids = [item["semantic_case_id"] for item in selection["cases"]]
    assert len(case_ids) == len(set(case_ids)) == 24
    assert not set(case_ids) & pilot.PRIOR_VALIDATION_CASES
    assert {item["stratum"].split("_", 1)[0] for item in selection["cases"]} >= {
        "baseline",
        "danger",
        "respiratory",
        "diarrhoea",
        "fever",
        "ear",
        "integrated",
    }


def test_requests_are_target_blind_nigerian_english_v12() -> None:
    requests = pilot.build_source_requests()
    assert len(requests) == 24
    assert {item["variant_style"] for item in requests} == {"NIGERIAN_ENGLISH"}
    assert {item["prompt_version"] for item in requests} == {"1.2.0"}
    assert len({item["semantic_case_id"] for item in requests}) == 24
    assert all(
        "{{SOURCE_PACKAGE_JSON}}" not in item["rendered_prompt"] for item in requests
    )
    assert all(
        not any(
            term in json.dumps(item["source_package"]["structured_encounter"]).lower()
            for term in (
                "classification",
                "final_actions",
                "urgent_action_required",
                "rule_id",
            )
        )
        for item in requests
    )
    assert all(
        "EXPECTED_CLASSIFICATION_LABELS"
        in item["source_package"]["teacher_visibility"]["hidden"]
        for item in requests
    )


def test_prepare_writes_24_unit_zero_call_package(tmp_path, monkeypatch) -> None:
    output = tmp_path / pilot.RUN_ID
    monkeypatch.setattr(pilot, "RUN_DIR", output)
    pilot.prepare(approved_by="Test Owner", approved_at="2026-08-23T12:00:00Z")
    schedule = json.loads((output / "schedule.json").read_text())
    preflight = json.loads((output / "preflight.json").read_text())
    execution = json.loads((output / "azure_execution_config.json").read_text())
    assert len(schedule["units"]) == 24
    assert preflight["scheduled_attempts"] == 24
    assert preflight["distinct_parent_cases"] == 24
    assert preflight["maximum_reserved_total_usd"] == pytest.approx(0.72)
    assert execution["limits"] == {
        "maximum_remote_attempts": 24,
        "maximum_budget_usd": 1.0,
    }
    resume = pilot.derive_resume_state(schedule, [])
    assert resume["unit_count"] == 24
    assert not (output / "attempts").exists()


def test_v13_prompt_explicitly_protects_new_pilot_failure_boundaries() -> None:
    prompt = (
        pilot.ROOT
        / "prompts"
        / "holistic_language_variants"
        / "phc_nigerian_english_v1_3.txt"
    ).read_text(encoding="utf-8")
    assert "drinking_status" in prompt
    assert "Never use \"able to drink or breastfeed\" as evidence" in prompt
    assert "ear_discharge_reported = false" in prompt
    assert "Never render it as \"not reported\"" in prompt
