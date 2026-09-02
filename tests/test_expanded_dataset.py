from __future__ import annotations

import json

from edge_imci.training.expanded_dataset import (
    CANONICAL_PATH,
    CHAT_PATH,
    DUPLICATE_REPORT_PATH,
    MANIFEST_PATH,
    build_expanded_dataset,
)


def _jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_auto_promotion_rebuilds_frozen_dataset() -> None:
    canonical, chats, duplicates = build_expanded_dataset()
    assert canonical == _jsonl(CANONICAL_PATH)
    assert chats == _jsonl(CHAT_PATH)
    assert duplicates == json.loads(DUPLICATE_REPORT_PATH.read_text(encoding="utf-8"))
    assert len(canonical) == len(chats) == 7163


def test_auto_promotion_adds_exactly_5666_train_records() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["promoted_record_count"] == 5666
    assert manifest["partition_counts"] == {
        "TEST": 143,
        "TRAIN": 6905,
        "VALIDATION": 115,
    }
    assert manifest["authorization"]["experimental_finetuning_authorized"] is True
    assert manifest["authorization"]["training_authorized"] is False
    assert manifest["authorization"]["test_unsealing_authorized"] is False


def test_expanded_dataset_contains_all_seven_styles() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert set(manifest["style_counts"]) == {
        "NIGERIAN_ENGLISH",
        "NIGERIAN_PIDGIN",
        "NOISY_TYPED_ENGLISH",
        "TELEGRAPHIC_PHC_NOTE",
        "NATURAL_CONVERSATIONAL_ENGLISH",
        "CLINICAL_STANDARD_ENGLISH",
        "SUBJECTLESS_UNPUNCTUATED_SHORTHAND",
    }


def test_chat_targets_match_canonical_targets() -> None:
    canonical = {row["example_id"]: row for row in _jsonl(CANONICAL_PATH)}
    for chat in _jsonl(CHAT_PATH):
        assert json.loads(chat["messages"][-1]["content"]) == canonical[chat["example_id"]][
            "target"
        ]
