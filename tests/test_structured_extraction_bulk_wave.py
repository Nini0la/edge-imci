from __future__ import annotations

import json

from edge_imci.generation import structured_extraction_bulk_wave as bulk


def test_bulk_contract_is_bounded_and_does_not_authorize_training() -> None:
    contract = bulk.load_contract()
    assert contract["wave"]["maximum_remote_attempts"] == 2142
    assert contract["wave"]["maximum_budget_usd"] == 50.0
    assert [item["new_attempts"] for item in contract["wave"]["tranches"]] == [
        250,
        250,
        1642,
    ]
    assert contract["authorization"] == {
        "bulk_generation_authorized": True,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }


def test_bulk_allocation_is_balanced_and_excludes_oos_evaluation_parents() -> None:
    requests, order, manifest = bulk.build_requests_and_order()
    assert len(requests) == len(order) == 2142
    assert len(manifest["campaign_parent_ids"]) == 78
    assert "hpg-077-out-of-scope-age-1" not in manifest["campaign_parent_ids"]
    assert "hpg-078-out-of-scope-age-60" not in manifest["campaign_parent_ids"]
    assert "oos-extract-young-respiratory-001" in manifest["campaign_parent_ids"]
    assert "oos-extract-older-fever-001" in manifest["campaign_parent_ids"]
    assert sorted(manifest["parent_attempt_counts"].values()).count(28) == 36
    assert sorted(manifest["parent_attempt_counts"].values()).count(27) == 42
    assert manifest["style_attempt_counts"] == {
        "NIGERIAN_ENGLISH": 536,
        "NIGERIAN_PIDGIN": 536,
        "NOISY_TYPED_ENGLISH": 535,
        "TELEGRAPHIC_PHC_NOTE": 535,
    }
    assert manifest["first_78_unique_parent_count"] == 78


def test_bulk_prepare_is_zero_call_and_pins_all_units(tmp_path, monkeypatch) -> None:
    output = tmp_path / bulk.RUN_ID
    monkeypatch.setattr(bulk, "RUN_DIR", output)
    preflight = bulk.prepare(
        approved_by="Test Owner",
        approved_at="2026-08-23T12:00:00Z",
    )
    schedule = json.loads((output / "schedule.json").read_text(encoding="utf-8"))
    requests = json.loads((output / "source_requests.json").read_text(encoding="utf-8"))
    assert preflight["scheduled_attempts"] == 2142
    assert preflight["maximum_reserved_total_usd"] == 42.84
    assert len(schedule["units"]) == len(requests) == 2142
    assert len({item["request_id"] for item in schedule["units"]}) == 2142
    assert bulk.derive_resume_state(schedule, [])["unit_count"] == 2142
    assert not (output / "attempts").exists()


def test_v3_continuation_excludes_exact_completed_requests(tmp_path, monkeypatch) -> None:
    output = tmp_path / "structured-extraction-language-bulk-gpt41-20250414-v3"
    monkeypatch.setattr(
        bulk,
        "CONTRACT_PATH",
        bulk.ROOT / "configs/generation/structured_extraction_bulk_wave_v3.json",
    )
    monkeypatch.setattr(bulk, "CONTRACT_ID", "edge-imci-structured-extraction-bulk-wave-v3")
    monkeypatch.setattr(bulk, "RUN_ID", "structured-extraction-language-bulk-gpt41-20250414-v3")
    monkeypatch.setattr(bulk, "RUN_DIR", output)
    monkeypatch.setattr(bulk, "SKIP_PREFIX_ATTEMPTS", 0)
    monkeypatch.setattr(
        bulk,
        "SKIP_COMPLETED_RUN_ID",
        "structured-extraction-language-bulk-gpt41-20250414-v1",
    )
    preflight = bulk.prepare(
        approved_by="Test Owner",
        approved_at="2026-08-23T12:30:00Z",
    )
    schedule = json.loads((output / "schedule.json").read_text(encoding="utf-8"))
    prior_attempts = bulk.AppendOnlyAttemptStore(
        bulk.ROOT
        / "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v1/attempts"
    ).latest_attempts()
    prior_hashes = {item["request_sha256"] for item in prior_attempts}
    continuation_hashes = {item["source_request_sha256"] for item in schedule["units"]}
    assert preflight["scheduled_attempts"] == 2111
    assert preflight["allocation_manifest"]["continuation_skip_mode"] == "EXACT_COMPLETED_REQUEST_HASHES"
    assert len(prior_hashes) == 31
    assert prior_hashes.isdisjoint(continuation_hashes)
    assert len(prior_hashes | continuation_hashes) == 2142


def test_completed_slot_can_be_recovered_without_large_source_manifest() -> None:
    terminal = {
        "request_id": "run__configuration__hpg-001-all-negative__variant-0007",
        "request_sha256": "unused-when-compacted",
        "semantic_case_id": "hpg-001-all-negative",
        "prompt": {"strategy_id": "phc-telegraphic-note-v1"},
    }
    assert bulk._completed_slot_from_terminal(terminal) == (
        "hpg-001-all-negative",
        "phc-telegraphic-note-v1",
        7,
    )


def test_completed_slot_prefers_source_manifest_when_available() -> None:
    terminal = {
        "request_id": "not-required",
        "request_sha256": "request-sha",
        "semantic_case_id": "case-from-terminal",
    }
    requests = {
        "request-sha": {
            "semantic_case_id": "case-from-manifest",
            "strategy_id": "style-from-manifest",
            "variant_index": 3,
        }
    }
    assert bulk._completed_slot_from_terminal(terminal, requests) == (
        "case-from-manifest",
        "style-from-manifest",
        3,
    )


def test_transport_failure_is_not_a_completed_language_candidate() -> None:
    terminal = {
        "status": "TRANSPORT_FAILED",
        "candidate": None,
    }
    assert not bulk._terminal_completes_language_slot(terminal)
    assert bulk._terminal_completes_language_slot({"status": "PARSE_FAILED"})
    assert bulk._terminal_completes_language_slot({"status": "DETERMINISTIC_REJECTED"})
    assert bulk._terminal_completes_language_slot({"status": "PENDING_HUMAN_REVIEW"})
