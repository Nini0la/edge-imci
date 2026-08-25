from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from edge_imci.review.calibration import (
    historical_calibration_cases,
    prepare_historical_calibration,
    score_historical_calibration,
)


def test_historical_calibration_selection_has_both_labels_and_all_styles() -> None:
    attempts, labels = historical_calibration_cases(maximum_cases=48)
    assert len(attempts) == len(labels) == 48
    assert set(item["human_label"] for item in labels) == {"PASS", "FAIL"}
    assert set(item["variant_style"] for item in labels) == {
        "NIGERIAN_ENGLISH",
        "NIGERIAN_PIDGIN",
        "NOISY_TYPED_ENGLISH",
        "TELEGRAPHIC_PHC_NOTE",
    }
    assert all(count >= 4 for count in Counter(item["human_label"] for item in labels).values())


def test_calibration_prepare_is_zero_call(tmp_path: Path) -> None:
    manifest = prepare_historical_calibration(
        output_dir=tmp_path / "calibration",
        model="primary-calibration-test",
        maximum_cases=48,
    )
    assert manifest["status"] == "CALIBRATION_BATCH_PREPARED_ZERO_CALL"
    assert manifest["case_count"] == 48
    assert manifest["remote_call_performed"] is False


def test_calibration_scores_agreement_and_error_rates(tmp_path: Path) -> None:
    calibration = tmp_path / "calibration"
    prepare_historical_calibration(output_dir=calibration, maximum_cases=48)
    pipeline = calibration / "review_pipeline"
    subjects = {
        item["subject_id"]: item
        for item in (
            json.loads(line)
            for line in (pipeline / "subjects.jsonl").read_text().splitlines()
        )
    }
    labels = {
        item["subject_id"]: item["human_label"]
        for item in (
            json.loads(line)
            for line in (calibration / "human_labels.jsonl").read_text().splitlines()
        )
    }
    index = json.loads((pipeline / "primary_index.json").read_text())
    outputs = []
    for custom_id, index_item in index.items():
        subject = subjects[index_item["subject_id"]]
        human_label = labels[subject["subject_id"]]
        assessments = []
        for fact_index, fact in enumerate(subject["known_facts"]):
            failed = human_label == "FAIL" and fact_index == 0
            assessments.append(
                {
                    "fact_id": fact["fact_id"],
                    "status": "MISSING" if failed else "MATCHED",
                    "evidence_text": None if failed else subject["candidate_text"],
                    "issue_code": "FACT_MISSING" if failed else None,
                }
            )
        review = {
            "review_schema_id": "edge-imci-synthetic-language-review-output-v1",
            "subject_id": subject["subject_id"],
            "verdict": human_label,
            "error_codes": ["FACT_MISSING"] if human_label == "FAIL" else [],
            "fact_assessments": assessments,
            "unknown_violations": [],
            "unsupported_claims": [],
            "style_assessment": "PASS",
            "risk_level": "HIGH" if subject["high_risk"] else "LOW",
            "summary": "Frozen calibration fixture prediction.",
        }
        outputs.append(
            {
                "custom_id": custom_id,
                "response": {
                    "status_code": 200,
                    "body": {
                        "output_text": json.dumps(review),
                        "usage": {"input_tokens": 100, "output_tokens": 100},
                    },
                },
                "error": None,
            }
        )
    output_path = tmp_path / "primary_output.jsonl"
    output_path.write_text("".join(json.dumps(item) + "\n" for item in outputs))
    report = score_historical_calibration(
        calibration_dir=calibration,
        primary_output_path=output_path,
    )
    assert report["status"] == "CALIBRATION_PASSED"
    assert report["agreement_rate"] == 1.0
    assert report["false_acceptance_rate"] == 0.0
    assert report["false_rejection_rate"] == 0.0
