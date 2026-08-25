from __future__ import annotations

import json
from pathlib import Path

import pytest

from edge_imci.evaluation.checkpoint import (
    CheckpointEvaluationError,
    evaluate_checkpoint_predictions,
    load_checkpoint_evaluation_policy,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = (
    ROOT / "data/training_sources/structured_extraction_campaign_v1/chat_messages.jsonl"
)
POLICY = ROOT / "configs/evaluation/structured_extraction_checkpoint_policy_v1.json"


def _validation_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["partition"] == "VALIDATION"
    ]


def _write_predictions(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "predictions.jsonl"
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _perfect_predictions() -> list[dict]:
    return [
        {
            "example_id": row["example_id"],
            "prediction": row["messages"][-1]["content"],
            "latency_seconds": 0.25,
        }
        for row in _validation_rows()
    ]


def test_policy_is_pinned_and_valid() -> None:
    path, policy = load_checkpoint_evaluation_policy(POLICY)
    assert path == POLICY
    assert policy["dataset"]["partition"] == "VALIDATION"
    assert policy["controls"]["test_partition_prohibited"] is True


def test_perfect_checkpoint_is_promotion_eligible_and_sliced(tmp_path: Path) -> None:
    report = evaluate_checkpoint_predictions(
        _write_predictions(tmp_path, _perfect_predictions()),
        candidate_id="perfect-fixture",
        policy_path=POLICY,
    )

    assert report["partition"] == "VALIDATION"
    assert report["test_partition_used"] is False
    assert report["aggregate"]["example_count"] == 115
    assert report["aggregate"]["coverage_rate"] == 1.0
    assert report["aggregate"]["schema_valid_rate"] == 1.0
    assert report["aggregate"]["field_accuracy"] == 1.0
    assert report["aggregate"]["decision_equivalence_rate"] == 1.0
    assert report["aggregate"]["p95_latency_seconds"] == 0.25
    assert report["promotion"]["eligible"] is True
    assert {style: metrics["example_count"] for style, metrics in report["slices"].items()} == {
        "phc-nigerian-english-v1": 30,
        "phc-nigerian-pidgin-v1": 25,
        "phc-noisy-typed-english-v1": 28,
        "phc-telegraphic-note-v1": 32,
    }


def test_missing_and_invalid_predictions_score_as_failures(tmp_path: Path) -> None:
    predictions = _perfect_predictions()
    predictions.pop()
    predictions[0]["prediction"] = "not-json"
    report = evaluate_checkpoint_predictions(
        _write_predictions(tmp_path, predictions),
        candidate_id="broken-fixture",
        policy_path=POLICY,
    )

    assert report["aggregate"]["coverage_rate"] == 114 / 115
    assert report["aggregate"]["json_parse_rate"] == 113 / 115
    assert report["aggregate"]["schema_valid_rate"] == 113 / 115
    assert report["promotion"]["eligible"] is False
    assert {failure["metric"] for failure in report["promotion"]["failures"]} >= {
        "coverage_rate",
        "json_parse_rate",
        "schema_valid_rate",
    }


def test_prediction_ids_must_be_unique_and_known(tmp_path: Path) -> None:
    predictions = _perfect_predictions()
    predictions.append(predictions[0])
    with pytest.raises(CheckpointEvaluationError, match="duplicate prediction"):
        evaluate_checkpoint_predictions(
            _write_predictions(tmp_path, predictions),
            candidate_id="duplicate-fixture",
            policy_path=POLICY,
        )

    predictions = _perfect_predictions()
    predictions[0]["example_id"] = "unknown-example"
    with pytest.raises(CheckpointEvaluationError, match="unknown prediction"):
        evaluate_checkpoint_predictions(
            _write_predictions(tmp_path, predictions),
            candidate_id="unknown-fixture",
            policy_path=POLICY,
        )
