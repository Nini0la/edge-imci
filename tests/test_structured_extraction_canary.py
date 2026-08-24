from __future__ import annotations

import hashlib
import json

from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.model_io import project_model_facing_encounter
from edge_imci.training.dataset_policy import parent_semantic_partition
from edge_imci.training.extraction_canary import (
    CANONICAL_RECORDS_PATH,
    CHAT_MESSAGES_PATH,
    LANGUAGE_VARIANTS_PATH,
    MANIFEST_PATH,
    ROOT,
    build_extraction_canary,
    load_canary_approval,
)


def _jsonl(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_approval_promotes_exactly_three_recorded_reviewed_attempts() -> None:
    approval = load_canary_approval()
    assert len(approval["approved_attempts"]) == 3
    assert approval["bulk_generation_authorized"] is False
    assert approval["training_authorized"] is False
    assert all(
        item["review"]
        == {
            "semantic_faithfulness": "APPROVED",
            "naturalness": "APPROVED",
            "phc_suitability": "APPROVED_FOR_HACKATHON",
        }
        for item in approval["approved_attempts"]
    )


def test_canary_records_are_rebuilt_exactly_from_frozen_sources() -> None:
    variants, canonical, chats = build_extraction_canary()
    assert variants == _jsonl(LANGUAGE_VARIANTS_PATH)
    assert canonical == _jsonl(CANONICAL_RECORDS_PATH)
    assert chats == _jsonl(CHAT_MESSAGES_PATH)
    assert len(variants) == len(canonical) == len(chats) == 3


def test_promoted_language_is_approved_but_not_training_authorized() -> None:
    variants, _, _ = build_extraction_canary()
    for variant in variants:
        assert variant["status"] == "APPROVED_CORPUS_CANDIDATE"
        assert variant["review"] == {
            "semantic_faithfulness": "APPROVED",
            "naturalness": "APPROVED",
            "phc_suitability": "APPROVED_FOR_HACKATHON",
            "reviewer": "Niniola Adegboyega",
        }
        assert variant["eligibility"] == {
            "teacher_bakeoff": True,
            "corpus_candidate": True,
            "training": False,
        }


def test_canonical_pairing_uses_only_user_language_and_deterministic_target() -> None:
    variants, canonical, chats = build_extraction_canary()
    variant_by_id = {row["variant_id"]: row for row in variants}
    for record, chat in zip(canonical, chats, strict=True):
        variant = variant_by_id[record["variant_id"]]
        assert record["input"] == variant["conversation"][0]
        assert variant["conversation"][1]["content"] not in json.dumps(record)
        assert record["partition"] == parent_semantic_partition(record["source_case_id"])
        assert chat["partition"] == record["partition"]
        assert json.loads(chat["messages"][-1]["content"]) == record["target"]
        assert set(record["target"]) == {
            "patient_facts",
            "danger_signs",
            "respiratory",
            "diarrhoea",
            "fever",
            "ear",
        }


def test_canary_targets_match_frozen_semantic_projection() -> None:
    semantics = {
        row["golden_case_id"]: row for row in load_holistic_golden_suite()
    }
    _, canonical, _ = build_extraction_canary()
    for record in canonical:
        assert record["target"] == project_model_facing_encounter(
            semantics[record["source_case_id"]]
        )


def test_canary_manifest_pins_assets_and_keeps_execution_unauthorized() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["record_count"] == 3
    assert manifest["parent_case_count"] == 3
    assert manifest["partition_counts"] == {
        "TRAIN": 3,
        "VALIDATION": 0,
        "TEST": 0,
    }
    assert manifest["authorization"] == {
        "bulk_generation_authorized": False,
        "training_authorized": False,
    }
    for relative, evidence in manifest["assets"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == evidence[
            "sha256"
        ]
