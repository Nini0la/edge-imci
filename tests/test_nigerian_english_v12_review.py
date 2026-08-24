from __future__ import annotations

import json

from edge_imci.generation.nigerian_english_v12_review import (
    CANONICAL_RECORDS_PATH,
    MANIFEST_PATH,
    build_reviewed_canary,
)
from edge_imci.generation.nigerian_english_v12_canary import RUN_DIR


def test_review_rebuilds_three_approved_records_exactly() -> None:
    language, canonical, chats, audit = build_reviewed_canary()
    frozen = [
        json.loads(line)
        for line in CANONICAL_RECORDS_PATH.read_text(encoding="utf-8").splitlines()
    ]
    assert canonical == frozen
    assert len(language) == len(canonical) == len(chats) == len(audit) == 3
    assert all(
        row["language_provenance"]["variant_style"] == "NIGERIAN_ENGLISH"
        for row in canonical
    )


def test_annotation_only_rejection_is_remediated_without_mutating_attempt() -> None:
    _, _, _, audit = build_reviewed_canary()
    remediated = [item for item in audit if item["evidence_annotation_remediated"]]
    assert len(remediated) == 1
    assert remediated[0]["semantic_case_id"] == (
        "hpg-020-resp-post-bronchodilator-improved"
    )
    assert remediated[0]["immutable_attempt_status"] == "DETERMINISTIC_REJECTED"
    assert remediated[0]["corrected_revalidation"]["deterministic_pass"] is True


def test_fever_variant_preserves_area_level_malaria_risk() -> None:
    language, _, _, _ = build_reviewed_canary()
    fever = next(
        item
        for item in language
        if item["semantic_case_id"] == "hpg-041-fever-high-positive"
    )
    submission = fever["conversation"][0]["content"]
    assert "Malaria risk in the area is high" in submission
    assert "child is at high risk" not in submission


def test_run_has_three_unique_zero_retry_terminal_attempts() -> None:
    attempts = [
        json.loads(path.read_text())
        for path in sorted((RUN_DIR / "attempts").glob("*/terminal.json"))
    ]
    assert len(attempts) == 3
    assert len({item["request_id"] for item in attempts}) == 3
    assert all(item["usage"]["retry_count"] == 0 for item in attempts)


def test_manifest_authorizes_no_more_calls_or_scale() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["approved_record_count"] == 3
    assert manifest["recipe_decision"] == (
        "APPROVED_FOR_FURTHER_CONTROLLED_GENERATION"
    )
    assert manifest["authorization"] == {
        "additional_remote_calls_authorized": False,
        "bulk_generation_authorized": False,
        "production_clinical_use_authorized": False,
        "training_authorized": False,
    }
