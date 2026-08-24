from __future__ import annotations

import json

import pytest

from edge_imci.generation import holistic_style_remediation as remediation


def test_remediation_authorization_is_exactly_six_calls_and_no_scale() -> None:
    authorization = remediation.load_authorization()
    assert authorization["maximum_remote_attempts"] == 6
    assert authorization["maximum_budget_usd"] == 0.5
    assert authorization["semantic_retries"] is False
    assert authorization["bulk_generation_authorized"] is False
    assert authorization["training_authorized"] is False


def test_v11_requests_cover_two_styles_over_same_three_cases() -> None:
    requests = remediation.build_source_requests()
    assert len(requests) == 6
    assert {item["prompt_version"] for item in requests} == {"1.1.0"}
    assert {item["variant_style"] for item in requests} == {
        "NIGERIAN_ENGLISH",
        "NOISY_TYPED_ENGLISH",
    }
    assert len({item["semantic_case_id"] for item in requests}) == 3
    assert all(item["rendered_prompt"].count("SOURCE_PACKAGE_JSON") == 1 for item in requests)


@pytest.mark.parametrize(
    "relative_path",
    [
        "prompts/holistic_language_variants/phc_nigerian_english_v1_1.txt",
        "prompts/holistic_language_variants/phc_noisy_typed_english_v1_1.txt",
    ],
)
def test_v11_prompt_protects_known_negatives_and_has_no_patch_marker(
    relative_path: str,
) -> None:
    text = (remediation.ROOT / relative_path).read_text(encoding="utf-8")
    assert "never use a double negative" in text
    assert "never weaken a supplied known negative" in text
    assert "No known negative is phrased as absence of a report" in text
    assert "\n+Clinical truth" not in text


def test_prepare_writes_a_six_unit_zero_call_package(tmp_path, monkeypatch) -> None:
    output = tmp_path / remediation.RUN_ID
    monkeypatch.setattr(remediation, "RUN_DIR", output)
    remediation.prepare(approved_by="Test Owner", approved_at="2026-08-23T12:00:00Z")
    schedule = json.loads((output / "schedule.json").read_text())
    preflight = json.loads((output / "preflight.json").read_text())
    execution = json.loads((output / "azure_execution_config.json").read_text())
    assert len(schedule["units"]) == 6
    assert preflight["scheduled_attempts"] == 6
    assert preflight["maximum_reserved_total_usd"] == pytest.approx(0.18)
    assert execution["limits"] == {
        "maximum_remote_attempts": 6,
        "maximum_budget_usd": 0.5,
    }
    assert not (output / "attempts").exists()


def test_nigerian_english_v12_protects_area_level_malaria_context() -> None:
    prompt = (
        remediation.ROOT
        / "prompts/holistic_language_variants/phc_nigerian_english_v1_2.txt"
    ).read_text(encoding="utf-8")
    assert "malaria-risk category describes the area" in prompt
    assert "Never recast it as the child's individual risk" in prompt
    assert "Malaria-risk wording refers to the area/setting" in prompt
