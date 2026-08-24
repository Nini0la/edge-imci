from __future__ import annotations

import json

from edge_imci.training.structured_extraction_campaign import (
    CANONICAL_PATH,
    CHAT_PATH,
    EXCLUSIONS_PATH,
    LANGUAGE_PATH,
    MANIFEST_PATH,
    build_campaign_corpus,
    load_campaign_terminals,
)


def _jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_campaign_reconciles_exact_allocation_and_transport_receipts() -> None:
    rows = load_campaign_terminals()
    assert len(rows) == 2150
    assert sum(row["status"] != "TRANSPORT_FAILED" for row in rows) == 2142
    assert sum(row["status"] == "TRANSPORT_FAILED" for row in rows) == 8


def test_campaign_export_rebuilds_exactly_and_covers_all_parents() -> None:
    language, canonical, chats, exclusions, sample = build_campaign_corpus()
    assert language == _jsonl(LANGUAGE_PATH)
    assert canonical == _jsonl(CANONICAL_PATH)
    assert chats == _jsonl(CHAT_PATH)
    assert exclusions == _jsonl(EXCLUSIONS_PATH)
    assert len(canonical) == 1497
    assert len(exclusions) == 653
    assert len(sample) == 145
    assert len({row["source_case_id"] for row in canonical}) == 78


def test_campaign_targets_are_json_only_and_do_not_leak_clinical_outputs() -> None:
    forbidden = {"classification", "classifications", "actions", "management", "urgency"}
    canonical = _jsonl(CANONICAL_PATH)
    chats = _jsonl(CHAT_PATH)
    by_id = {row["example_id"]: row for row in canonical}
    for chat in chats:
        target = json.loads(chat["messages"][-1]["content"])
        assert target == by_id[chat["example_id"]]["target"]
        assert forbidden.isdisjoint(target)


def test_campaign_preserves_unknowns_and_distinct_out_of_scope_age_parents() -> None:
    records = _jsonl(CANONICAL_PATH)
    duration_unknown = [
        row for row in records if row["source_case_id"] == "hpg-039-diarrhoea-duration-unknown"
    ]
    assert duration_unknown
    assert all(row["target"]["diarrhoea"]["duration_days"] is None for row in duration_unknown)
    ages = {
        row["source_case_id"]: row["target"]["patient_facts"]["age_months"]
        for row in records
        if row["source_case_id"].startswith("oos-extract-")
    }
    assert ages == {
        "oos-extract-young-respiratory-001": 1,
        "oos-extract-older-fever-001": 60,
    }


def test_manifest_keeps_training_blocked_and_pins_counts() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["record_count"] == 1497
    assert manifest["excluded_receipt_count"] == 653
    assert manifest["parent_case_count"] == 78
    assert manifest["authorization"] == {
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }
