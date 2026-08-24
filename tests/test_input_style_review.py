from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from edge_imci.generation.input_style_review import (
    CANONICAL_RECORDS_PATH,
    MANIFEST_PATH,
    build_reviewed_style_canary,
)
from edge_imci.generation.holistic_style_canary import RUN_DIR


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_reviewed_style_canary_rebuilds_exactly() -> None:
    language, canonical, chats, audit = build_reviewed_style_canary()
    assert canonical == _jsonl(CANONICAL_RECORDS_PATH)
    assert len(language) == len(canonical) == len(chats) == 9
    assert len(audit) == 12
    assert sum(item["review_decision"] == "REJECTED" for item in audit) == 3


def test_approved_style_counts_and_unknown_preservation() -> None:
    _, canonical, _, _ = build_reviewed_style_canary()
    assert Counter(row["language_provenance"]["variant_style"] for row in canonical) == {
        "NIGERIAN_ENGLISH": 2,
        "NIGERIAN_PIDGIN": 3,
        "NOISY_TYPED_ENGLISH": 1,
        "TELEGRAPHIC_PHC_NOTE": 3,
    }
    incomplete = [
        row
        for row in canonical
        if row["source_case_id"] == "hpg-071-incomplete-entry-unknown"
    ]
    assert len(incomplete) == 3
    assert all(row["target"]["patient_facts"]["has_diarrhoea"] is None for row in incomplete)
    assert all("diarr" not in row["input"]["content"].casefold() for row in incomplete)


def test_style_manifest_does_not_authorize_scale_or_training() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["approved_record_count"] == 9
    assert manifest["authorization"] == {
        "bulk_generation_authorized": False,
        "production_clinical_use_authorized": False,
        "training_authorized": False,
    }


def test_remote_evidence_contains_twelve_unique_first_attempts_and_no_retries() -> None:
    terminal_paths = sorted((RUN_DIR / "attempts").glob("*/terminal.json"))
    attempts = [json.loads(path.read_text()) for path in terminal_paths]
    assert len(attempts) == 12
    assert len({item["request_id"] for item in attempts}) == 12
    assert all(item["usage"]["retry_count"] == 0 for item in attempts)
    assert all(item["attempt_id"].endswith("__attempt-1") for item in attempts)
