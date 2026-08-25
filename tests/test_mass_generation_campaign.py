from __future__ import annotations

from collections import Counter

from edge_imci.generation.mass_campaign import (
    build_mass_campaign,
    prepare_regular_english_canary,
)


def test_mass_campaign_is_balanced_six_style_and_blocked() -> None:
    requests, schedule, preflight = build_mass_campaign()
    assert len(requests) == 10_000
    assert len(schedule["units"]) == 10_000
    assert schedule["authorization"]["remote_calls_authorized"] is False
    assert preflight["status"] == "BLOCKED_NOT_AUTHORIZED"
    assert preflight["remote_call_performed"] is False
    assert Counter(item["variant_style"] for item in requests) == {
        "NATURAL_CONVERSATIONAL_ENGLISH": 2000,
        "CLINICAL_STANDARD_ENGLISH": 2000,
        "NIGERIAN_ENGLISH": 1500,
        "NIGERIAN_PIDGIN": 1500,
        "NOISY_TYPED_ENGLISH": 1500,
        "TELEGRAPHIC_PHC_NOTE": 1500,
    }
    assert len({item["request_sha256"] for item in requests}) == 10_000
    assert preflight["estimated_generation_cost_usd"] == 55.0


def test_first_schedule_round_covers_all_styles() -> None:
    requests, schedule, _ = build_mass_campaign()
    request_by_hash = {item["request_sha256"]: item for item in requests}
    first_styles = {
        request_by_hash[item["source_request_sha256"]]["variant_style"]
        for item in schedule["units"][:6]
    }
    assert len(first_styles) == 6


def test_regular_english_canary_is_prepared_but_not_authorized(tmp_path) -> None:
    report = prepare_regular_english_canary(output_dir=tmp_path / "canary")
    assert report["request_count"] == 14
    assert report["status"] == "CANARY_PREPARED_BLOCKED_NOT_AUTHORIZED"
    assert report["remote_call_performed"] is False
