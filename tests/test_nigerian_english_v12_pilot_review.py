from __future__ import annotations

import json

from edge_imci.generation.nigerian_english_v12_pilot import RUN_DIR
from edge_imci.generation.nigerian_english_v12_pilot_review import (
    CANONICAL_RECORDS_PATH,
    MANIFEST_PATH,
    build_reviewed_pilot,
)


def test_review_rebuilds_19_approved_records_exactly() -> None:
    language, canonical, chats, audit = build_reviewed_pilot()
    frozen = [
        json.loads(line)
        for line in CANONICAL_RECORDS_PATH.read_text(encoding="utf-8").splitlines()
    ]
    assert canonical == frozen
    assert len(language) == len(canonical) == len(chats) == 19
    assert len(audit) == 24


def test_review_records_five_semantic_rejections_and_one_annotation_fix() -> None:
    _, _, _, audit = build_reviewed_pilot()
    rejected = [item for item in audit if item["review_decision"] == "REJECTED"]
    remediated = [item for item in audit if item["evidence_annotation_remediated"]]
    assert len(rejected) == 5
    assert len(remediated) == 1
    assert remediated[0]["semantic_case_id"] == "hpg-042-fever-high-negative"
    assert {
        code for item in rejected for code in item["reason_codes"]
    } == {
        "DIARRHOEA_DRINKING_STATUS_DISTINCTION_LOST",
        "KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT",
    }


def test_pilot_attempts_are_24_unique_and_zero_retry() -> None:
    attempts = [
        json.loads(path.read_text())
        for path in sorted((RUN_DIR / "attempts").glob("*/terminal.json"))
    ]
    assert len(attempts) == 24
    assert len({item["request_id"] for item in attempts}) == 24
    assert all(item["usage"]["retry_count"] == 0 for item in attempts)


def test_manifest_blocks_more_calls_and_scale() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["approved_record_count"] == 19
    assert manifest["rejected_record_count"] == 5
    assert manifest["recipe_decision"] == "REVISE_BEFORE_SCALE"
    assert manifest["next_prompt_version"] == "1.3.0"
    assert manifest["authorization"] == {
        "additional_remote_calls_authorized": False,
        "bulk_generation_authorized": False,
        "production_clinical_use_authorized": False,
        "training_authorized": False,
    }
