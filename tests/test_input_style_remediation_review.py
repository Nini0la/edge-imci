from __future__ import annotations

import json
from collections import Counter

from edge_imci.generation.input_style_remediation_review import (
    CANONICAL_RECORDS_PATH,
    MANIFEST_PATH,
    build_reviewed_remediation_canary,
)
from edge_imci.generation.holistic_style_remediation import RUN_DIR


def test_remediation_review_rebuilds_five_approved_records_exactly() -> None:
    language, canonical, chats, audit = build_reviewed_remediation_canary()
    frozen = [
        json.loads(line)
        for line in CANONICAL_RECORDS_PATH.read_text(encoding="utf-8").splitlines()
    ]
    assert canonical == frozen
    assert len(language) == len(canonical) == len(chats) == 5
    assert len(audit) == 6
    assert Counter(row["language_provenance"]["variant_style"] for row in canonical) == {
        "NIGERIAN_ENGLISH": 2,
        "NOISY_TYPED_ENGLISH": 3,
    }


def test_fever_context_shift_is_rejected_and_not_exported() -> None:
    _, canonical, _, audit = build_reviewed_remediation_canary()
    rejected = [item for item in audit if item["review_decision"] == "REJECTED"]
    assert len(rejected) == 1
    assert rejected[0]["semantic_case_id"] == "hpg-041-fever-high-positive"
    assert rejected[0]["variant_style"] == "NIGERIAN_ENGLISH"
    assert "MALARIA_RISK_CONTEXT_SHIFT" in rejected[0]["reason_codes"]
    assert not any(
        row["source_case_id"] == "hpg-041-fever-high-positive"
        and row["language_provenance"]["variant_style"] == "NIGERIAN_ENGLISH"
        for row in canonical
    )


def test_remediation_evidence_has_six_unique_zero_retry_attempts() -> None:
    attempts = [
        json.loads(path.read_text())
        for path in sorted((RUN_DIR / "attempts").glob("*/terminal.json"))
    ]
    assert len(attempts) == 6
    assert len({item["request_id"] for item in attempts}) == 6
    assert all(item["usage"]["retry_count"] == 0 for item in attempts)


def test_manifest_authorizes_no_more_calls_or_scale() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["approved_record_count"] == 5
    assert manifest["authorization"] == {
        "additional_remote_calls_authorized": False,
        "bulk_generation_authorized": False,
        "production_clinical_use_authorized": False,
        "training_authorized": False,
    }
