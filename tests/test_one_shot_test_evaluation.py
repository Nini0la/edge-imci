from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from edge_imci.evaluation.one_shot_test import (
    OneShotTestError,
    evaluate_one_shot_test_predictions,
    load_one_shot_test_finalization_recovery,
    load_one_shot_test_policy,
    load_one_shot_test_recovery,
)

ROOT = Path(__file__).resolve().parents[1]
REAL_POLICY = ROOT / "configs/evaluation/qwen3_0_6b_one_shot_test_v1.json"
REAL_RECOVERY = (
    ROOT / "configs/evaluation/qwen3_0_6b_one_shot_test_recovery_v1.json"
)
REAL_FINALIZATION_RECOVERY = (
    ROOT
    / "configs/evaluation/qwen3_0_6b_one_shot_test_finalization_recovery_v1.json"
)
REAL_FINALIZATION_RECOVERY_V2 = (
    ROOT
    / "configs/evaluation/qwen3_0_6b_one_shot_test_finalization_recovery_v2.json"
)


def _target(age_months: int = 18) -> dict:
    return {
        "patient_facts": {
            "age_months": age_months,
            "has_cough_or_difficult_breathing": False,
            "has_diarrhoea": False,
            "has_fever": False,
            "has_ear_problem": False,
        },
        "danger_signs": {
            "unable_to_drink_or_breastfeed": False,
            "vomits_everything": False,
            "had_convulsions": False,
            "lethargic_or_unconscious": False,
            "convulsing_now": False,
        },
        "respiratory": None,
        "diarrhoea": None,
        "fever": None,
        "ear": None,
    }


def _canonical(value: dict) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    schema_source = ROOT / "experiments/registry/schemas/one_shot_test_policy.schema.json"
    schema_path = tmp_path / "experiments/registry/schemas/one_shot_test_policy.schema.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_bytes(schema_source.read_bytes())

    styles = [
        "phc-nigerian-english-v1",
        "phc-nigerian-pidgin-v1",
        "phc-noisy-typed-english-v1",
        "phc-telegraphic-note-v1",
    ]
    rows: list[dict] = []
    for index, style in enumerate(styles, start=1):
        target = _target(17 + index)
        rows.append(
            {
                "example_id": f"test-{index}",
                "source_case_id": f"case-{index}",
                "variant_id": f"case-{index}__{style}__v0001",
                "partition": "TEST",
                "messages": [
                    {"role": "system", "content": "extract"},
                    {"role": "user", "content": f"synthetic input {index}"},
                    {"role": "assistant", "content": _canonical(target)},
                ],
            }
        )
    dataset = tmp_path / "data/test.jsonl"
    _write_jsonl(dataset, rows)
    dataset_sha256 = hashlib.sha256(dataset.read_bytes()).hexdigest()

    candidate_ids = ["base", "selected", "seed-control"]
    candidates = []
    for candidate_id, role in zip(
        candidate_ids,
        ["BASE_CONTROL", "SELECTED_FINE_TUNE", "SEED_CONTROL"],
        strict=True,
    ):
        candidates.append(
            {
                "candidate_id": candidate_id,
                "role": role,
                "kind": "HF_BASE",
                "required_for_execution": True,
                "model_id": "Qwen/Qwen3-0.6B",
                "revision": "a" * 40,
                "tokenizer_revision": "a" * 40,
                "model_weights_sha256": "b" * 64,
                "artifact": None,
            }
        )
    metrics = [
        "coverage_rate",
        "json_parse_rate",
        "schema_valid_rate",
        "exact_match_rate",
        "field_accuracy",
        "decision_equivalence_rate",
        "urgent_action_equivalence_rate",
        "referral_behavior_equivalence_rate",
    ]
    policy = {
        "schema_version": "1.0.0",
        "evaluation_id": "synthetic-one-shot",
        "authorization_id": "synthetic-one-shot-v1",
        "status": "AUTHORIZED_FOR_ONE_SHOT_TEST",
        "authority": "PROJECT_OWNER",
        "authorized_at": "2026-08-24T00:00:00Z",
        "dataset": {
            "path": "data/test.jsonl",
            "sha256": dataset_sha256,
            "partition": "TEST",
            "expected_record_count": 143,
            "split_policy_id": "edge-imci-parent-semantic-split-v1",
        },
        "candidates": candidates,
        "generation": {
            "chat_template": "PINNED_QWEN3_TOKENIZER_TEMPLATE",
            "enable_thinking": False,
            "max_new_tokens": 1200,
            "do_sample": False,
            "batch_size": 8,
            "identical_for_all_candidates": True,
        },
        "scoring": {
            "reported_metrics": metrics,
            "paired_metrics": [
                "exact_match_rate",
                "field_accuracy",
                "decision_equivalence_rate",
                "urgent_action_equivalence_rate",
                "referral_behavior_equivalence_rate",
            ],
            "results_by_language_style": True,
            "confidence_intervals": {
                "method": "DETERMINISTIC_PAIRED_PERCENTILE_BOOTSTRAP",
                "confidence": 0.95,
                "bootstrap_samples": 1000,
                "seed": 7,
            },
        },
        "comparison": {
            "selected_candidate_id": "selected",
            "base_candidate_id": "base",
            "optional_seed_control_id": "seed-control",
        },
        "thresholds": {
            "selected_global_minimums": {metric: 1.0 for metric in metrics},
            "selected_per_style_minimums": {
                "schema_valid_rate": 1.0,
                "urgent_action_equivalence_rate": 1.0,
                "referral_behavior_equivalence_rate": 1.0,
            },
            "paired_improvement": [
                {
                    "metric": metric,
                    "minimum_point_difference": 0.0,
                    "minimum_ci_lower_bound": 0.0,
                    "strict": metric
                    in {"exact_match_rate", "field_accuracy", "decision_equivalence_rate"},
                }
                for metric in [
                    "exact_match_rate",
                    "field_accuracy",
                    "decision_equivalence_rate",
                    "urgent_action_equivalence_rate",
                    "referral_behavior_equivalence_rate",
                ]
            ],
        },
        "controls": {
            "one_shot_execution": True,
            "close_after_attempt": True,
            "aggregate_only_release": True,
            "routine_record_review_prohibited": True,
            "prompt_repair_prohibited": True,
            "checkpoint_selection_prohibited": True,
            "result_driven_rerun_prohibited": True,
            "missing_predictions_score_as_failures": True,
        },
        "execution": {
            "environment_kind": "MODAL",
            "gpu_type": "A10G",
            "private_evidence_volume": "private",
            "a10g_gpu_rate_per_second": 0.000306,
            "currency": "USD",
        },
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    prediction_paths: dict[str, Path] = {}
    for candidate_id in candidate_ids:
        predictions = []
        for row in rows:
            prediction = (
                row["messages"][-1]["content"] if candidate_id != "base" else "{}"
            )
            predictions.append(
                {
                    "example_id": row["example_id"],
                    "prediction": prediction,
                    "latency_seconds": 0.1,
                }
            )
        path = tmp_path / f"{candidate_id}.jsonl"
        _write_jsonl(path, predictions)
        prediction_paths[candidate_id] = path
    return policy_path, prediction_paths


def test_real_policy_is_authorized_without_loading_test_rows() -> None:
    _, policy = load_one_shot_test_policy(REAL_POLICY)
    assert policy["dataset"]["partition"] == "TEST"
    assert policy["dataset"]["expected_record_count"] == 143
    assert len(policy["candidates"]) == 3
    assert policy["controls"]["one_shot_execution"] is True


def test_aggregate_report_contains_no_row_level_evidence(tmp_path: Path) -> None:
    policy_path, predictions = _fixture(tmp_path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["dataset"]["expected_record_count"] = 4
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    report = evaluate_one_shot_test_predictions(
        predictions, policy_path=policy_path, repo_root=tmp_path
    )
    assert report["aggregate_only"] is True
    assert report["routine_record_review_performed"] is False
    assert report["test_record_count"] == 4
    assert report["pass_fail"]["passed"] is True
    assert "receipts" not in report
    serialized = json.dumps(report)
    assert "synthetic input" not in serialized
    assert "test-1" not in serialized
    assert report["paired_comparison"]["metrics"]["exact_match_rate"]["difference"] == 1.0
    assert set(report["candidate_results"]["selected"]["by_language_style"]) == {
        "phc-nigerian-english-v1",
        "phc-nigerian-pidgin-v1",
        "phc-noisy-typed-english-v1",
        "phc-telegraphic-note-v1",
    }


def test_candidate_set_cannot_change_after_preregistration(tmp_path: Path) -> None:
    policy_path, predictions = _fixture(tmp_path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["dataset"]["expected_record_count"] = 4
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    predictions.pop("seed-control")
    with pytest.raises(OneShotTestError, match="differ from preregistration"):
        evaluate_one_shot_test_predictions(
            predictions, policy_path=policy_path, repo_root=tmp_path
        )


def test_disabled_one_shot_control_is_rejected(tmp_path: Path) -> None:
    policy_path, _ = _fixture(tmp_path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["controls"]["one_shot_execution"] = False
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(Exception, match="one_shot_execution"):
        load_one_shot_test_policy(policy_path, repo_root=tmp_path)


def test_real_recovery_authorizes_only_missing_frozen_candidates() -> None:
    _, recovery = load_one_shot_test_recovery(REAL_RECOVERY)
    assert recovery["status"] == "AUTHORIZED_INFRASTRUCTURE_ONLY_CONTINUATION"
    assert recovery["controls"]["raw_result_review_performed"] is False
    assert recovery["controls"]["rerun_completed_candidates_prohibited"] is True
    assert [item["candidate_id"] for item in recovery["preserved_candidates"]] == [
        "qwen3-0.6b-base-control"
    ]
    assert recovery["remaining_candidate_ids"] == [
        "qwen3-0.6b-sft-selected-seed-20260824",
        "qwen3-0.6b-sft-seed-control-3407",
    ]


def test_recovery_with_result_review_is_rejected(tmp_path: Path) -> None:
    schema_source = (
        ROOT / "experiments/registry/schemas/one_shot_test_recovery.schema.json"
    )
    schema_destination = (
        tmp_path / "experiments/registry/schemas/one_shot_test_recovery.schema.json"
    )
    schema_destination.parent.mkdir(parents=True)
    schema_destination.write_bytes(schema_source.read_bytes())
    recovery = json.loads(REAL_RECOVERY.read_text(encoding="utf-8"))
    recovery["controls"]["raw_result_review_performed"] = True
    recovery_path = tmp_path / "recovery.json"
    recovery_path.write_text(json.dumps(recovery), encoding="utf-8")
    with pytest.raises(Exception, match="raw_result_review_performed"):
        load_one_shot_test_recovery(recovery_path, repo_root=tmp_path)


def test_real_finalization_recovery_prohibits_candidate_inference() -> None:
    _, recovery = load_one_shot_test_finalization_recovery(
        REAL_FINALIZATION_RECOVERY
    )
    assert recovery["status"] == "AUTHORIZED_AGGREGATE_ONLY_COMPLETION"
    assert recovery["controls"]["candidate_inference_prohibited"] is True
    assert recovery["controls"]["raw_result_review_performed"] is False
    assert len(recovery["completed_candidates"]) == 3


def test_second_finalization_recovery_is_aggregate_only() -> None:
    _, recovery = load_one_shot_test_finalization_recovery(
        REAL_FINALIZATION_RECOVERY_V2
    )
    assert recovery["finalization_recovery_sequence"] == 2
    assert recovery["controls"]["candidate_inference_prohibited"] is True
    assert recovery["controls"]["aggregate_once"] is True
