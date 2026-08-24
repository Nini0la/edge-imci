from __future__ import annotations

import json

import pytest

from edge_imci.generation import input_style_pathway_qualification as qualification
from edge_imci.generation.input_style_pathway_qualification_review import build_review


def test_qualification_authorization_is_staged_and_bounded() -> None:
    authorization = qualification.load_authorization()
    assert authorization["first_gate_attempts"] == 7
    assert authorization["maximum_remote_attempts"] == 96
    assert authorization["maximum_budget_usd"] == 4.0
    assert authorization["semantic_retries"] is False
    assert authorization["bulk_generation_authorized"] is False


def test_requests_put_v13_gate_first_then_cover_four_by_24() -> None:
    requests = qualification.build_source_requests()
    assert len(requests) == 96
    assert [item["semantic_case_id"] for item in requests[:7]] == list(
        qualification.TARGETED_CASES
    )
    assert {
        item["qualification_phase"] for item in requests[:7]
    } == {"V13_TARGETED_GATE"}
    assert all(item["prompt_version"] == "1.3.0" for item in requests[:24])
    style_counts: dict[str, int] = {}
    for item in requests:
        style_counts[item["variant_style"]] = style_counts.get(item["variant_style"], 0) + 1
    assert style_counts == {
        "NIGERIAN_ENGLISH": 24,
        "NIGERIAN_PIDGIN": 24,
        "NOISY_TYPED_ENGLISH": 24,
        "TELEGRAPHIC_PHC_NOTE": 24,
    }


def test_prepare_writes_96_unit_zero_call_package(tmp_path, monkeypatch) -> None:
    output = tmp_path / qualification.RUN_ID
    monkeypatch.setattr(qualification, "RUN_DIR", output)
    qualification.prepare(
        approved_by="Test Owner",
        approved_at="2026-08-23T12:00:00Z",
    )
    schedule = json.loads((output / "schedule.json").read_text())
    preflight = json.loads((output / "preflight.json").read_text())
    execution = json.loads((output / "azure_execution_config.json").read_text())
    assert len(schedule["units"]) == 96
    assert preflight["first_gate_attempts"] == 7
    assert preflight["maximum_reserved_total_usd"] == pytest.approx(2.88)
    assert execution["limits"] == {
        "maximum_remote_attempts": 96,
        "maximum_budget_usd": 4.0,
    }
    assert qualification.derive_resume_state(schedule, [])["unit_count"] == 96
    assert not (output / "attempts").exists()


def test_v2_delegated_review_releases_only_nigerian_english() -> None:
    review = build_review()
    decisions = {
        item["variant_style"]: item for item in review["style_decisions"]
    }
    assert decisions["NIGERIAN_ENGLISH"]["release_decision"] == "QUALIFIED"
    assert decisions["NIGERIAN_ENGLISH"]["semantic_approved"] == 24
    assert decisions["NIGERIAN_PIDGIN"]["release_decision"] == "REMEDIATE_AND_REQUALIFY"
    assert decisions["NOISY_TYPED_ENGLISH"]["release_decision"] == "REMEDIATE_AND_REQUALIFY"
    assert decisions["TELEGRAPHIC_PHC_NOTE"]["release_decision"] == "REMEDIATE_AND_REQUALIFY"
    assert sum(item["semantic_rejected"] for item in decisions.values()) == 10
