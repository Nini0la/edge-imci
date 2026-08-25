"""Aggregate-only, one-shot evaluation for the reserved TEST partition."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from edge_imci.evaluation.checkpoint import (
    _aggregate,
    _load_predictions,
    _threshold_failures,
    score_candidate_predictions,
)
from edge_imci.experiments.provenance import hash_canonical, hash_file, resolve_repo_path
from edge_imci.experiments.registry import load_json_object, validate_against_schema

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = ROOT / "configs/evaluation/qwen3_0_6b_one_shot_test_v1.json"
POLICY_SCHEMA_PATH = ROOT / "experiments/registry/schemas/one_shot_test_policy.schema.json"
DEFAULT_RECOVERY_PATH = (
    ROOT / "configs/evaluation/qwen3_0_6b_one_shot_test_recovery_v1.json"
)
RECOVERY_SCHEMA_PATH = (
    ROOT / "experiments/registry/schemas/one_shot_test_recovery.schema.json"
)
DEFAULT_FINALIZATION_RECOVERY_PATH = (
    ROOT
    / "configs/evaluation/qwen3_0_6b_one_shot_test_finalization_recovery_v1.json"
)
FINALIZATION_RECOVERY_SCHEMA_PATH = (
    ROOT
    / "experiments/registry/schemas/one_shot_test_finalization_recovery.schema.json"
)


class OneShotTestError(ValueError):
    """Raised when reserved-TEST evidence violates its preregistration."""


def candidate_prompt_treatment(candidate: Mapping[str, Any]) -> str:
    """Return the preregistered prompt treatment, including the historical default."""

    treatment = candidate.get("prompt_treatment")
    if treatment is None:
        return "DATASET_SYSTEM_INSTRUCTION"
    return str(treatment["kind"])


def validate_candidate_prompt_treatments(policy: Mapping[str, Any]) -> None:
    """Reject accidental or unbalanced candidate-specific prompt changes."""

    candidates = policy["candidates"]
    treatments = [candidate_prompt_treatment(candidate) for candidate in candidates]
    identical = policy["generation"]["identical_for_all_candidates"]
    if identical and len(set(treatments)) != 1:
        raise OneShotTestError(
            "candidate prompt treatments differ despite identical_for_all_candidates"
        )
    if not identical:
        schema_informed = [
            candidate
            for candidate in candidates
            if candidate_prompt_treatment(candidate)
            == "SCHEMA_INFORMED_BASE_CONTROL_V1"
        ]
        if len(schema_informed) != 1 or schema_informed[0]["role"] != "BASE_CONTROL":
            raise OneShotTestError(
                "exactly the BASE_CONTROL must receive the schema-informed treatment"
            )
        if any(
            candidate["role"] != "BASE_CONTROL"
            and candidate_prompt_treatment(candidate) != "DATASET_SYSTEM_INSTRUCTION"
            for candidate in candidates
        ):
            raise OneShotTestError(
                "fine-tuned candidates must retain the dataset system instruction"
            )


def _iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise OneShotTestError(f"blank JSONL row at {path}:{line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise OneShotTestError(
                    f"invalid JSON at {path}:{line_number}: {error.msg}"
                ) from error
            if not isinstance(row, dict):
                raise OneShotTestError(
                    f"JSONL row at {path}:{line_number} must be an object"
                )
            yield line_number, row


def load_one_shot_test_policy(
    policy_path: str | Path = DEFAULT_POLICY_PATH,
    *,
    repo_root: str | Path = ROOT,
) -> tuple[Path, dict[str, Any]]:
    """Load the immutable preregistration without reading reserved TEST rows."""

    root = Path(repo_root).resolve()
    policy_file = Path(policy_path)
    if not policy_file.is_absolute():
        policy_file = resolve_repo_path(root, policy_file)
    policy = load_json_object(policy_file)
    schema_path = root / "experiments/registry/schemas/one_shot_test_policy.schema.json"
    validate_against_schema(policy, schema_path)
    controls = policy["controls"]
    required_controls = {
        "one_shot_execution": True,
        "close_after_attempt": True,
        "aggregate_only_release": True,
        "routine_record_review_prohibited": True,
        "prompt_repair_prohibited": True,
        "checkpoint_selection_prohibited": True,
        "result_driven_rerun_prohibited": True,
        "missing_predictions_score_as_failures": True,
    }
    for name, expected in required_controls.items():
        if controls.get(name) is not expected:
            raise OneShotTestError(f"required TEST control is disabled: {name}")
    if policy["status"] != "AUTHORIZED_FOR_ONE_SHOT_TEST":
        raise OneShotTestError("TEST policy is not authorized for one-shot execution")
    validate_candidate_prompt_treatments(policy)
    return policy_file, policy


def load_one_shot_test_recovery(
    recovery_path: str | Path = DEFAULT_RECOVERY_PATH,
    *,
    repo_root: str | Path = ROOT,
) -> tuple[Path, dict[str, Any]]:
    """Load an explicit infrastructure-only continuation authorization."""

    root = Path(repo_root).resolve()
    recovery_file = Path(recovery_path)
    if not recovery_file.is_absolute():
        recovery_file = resolve_repo_path(root, recovery_file)
    recovery = load_json_object(recovery_file)
    schema_path = (
        root / "experiments/registry/schemas/one_shot_test_recovery.schema.json"
    )
    validate_against_schema(recovery, schema_path)
    if recovery["status"] != "AUTHORIZED_INFRASTRUCTURE_ONLY_CONTINUATION":
        raise OneShotTestError("TEST recovery is not authorized")
    required_controls = {
        "continuation_count_limit": 1,
        "preserve_completed_predictions": True,
        "rerun_completed_candidates_prohibited": True,
        "candidate_changes_prohibited": True,
        "generation_changes_prohibited": True,
        "threshold_changes_prohibited": True,
        "raw_result_review_performed": False,
        "close_after_continuation": True,
    }
    for name, expected in required_controls.items():
        if recovery["controls"].get(name) != expected:
            raise OneShotTestError(f"required TEST recovery control differs: {name}")
    return recovery_file, recovery


def load_one_shot_test_finalization_recovery(
    recovery_path: str | Path = DEFAULT_FINALIZATION_RECOVERY_PATH,
    *,
    repo_root: str | Path = ROOT,
) -> tuple[Path, dict[str, Any]]:
    """Load an aggregate-only completion authorization after frozen inference."""

    root = Path(repo_root).resolve()
    recovery_file = Path(recovery_path)
    if not recovery_file.is_absolute():
        recovery_file = resolve_repo_path(root, recovery_file)
    recovery = load_json_object(recovery_file)
    schema_path = (
        root
        / "experiments/registry/schemas/one_shot_test_finalization_recovery.schema.json"
    )
    validate_against_schema(recovery, schema_path)
    if recovery["status"] != "AUTHORIZED_AGGREGATE_ONLY_COMPLETION":
        raise OneShotTestError("TEST finalization recovery is not authorized")
    required_controls = {
        "candidate_inference_prohibited": True,
        "preserve_completed_predictions": True,
        "candidate_changes_prohibited": True,
        "generation_changes_prohibited": True,
        "threshold_changes_prohibited": True,
        "raw_result_review_performed": False,
        "aggregate_once": True,
        "close_after_finalization": True,
    }
    for name, expected in required_controls.items():
        if recovery["controls"].get(name) != expected:
            raise OneShotTestError(
                f"required TEST finalization control differs: {name}"
            )
    return recovery_file, recovery


def load_authorized_test_rows(
    policy: Mapping[str, Any], *, repo_root: str | Path = ROOT
) -> list[dict[str, Any]]:
    """Load exactly the hash-pinned TEST partition for authorized remote execution."""

    root = Path(repo_root).resolve()
    dataset = policy["dataset"]
    if dataset["partition"] != "TEST":
        raise OneShotTestError("one-shot evaluator requires the TEST partition")
    dataset_path = resolve_repo_path(root, dataset["path"])
    actual_sha256, _ = hash_file(dataset_path)
    if actual_sha256 != dataset["sha256"]:
        raise OneShotTestError("TEST dataset SHA-256 mismatch")
    rows = [
        row
        for _, row in _iter_jsonl(dataset_path)
        if row.get("partition") == "TEST"
    ]
    if len(rows) != dataset["expected_record_count"]:
        raise OneShotTestError(
            f"TEST contains {len(rows)} rows, expected {dataset['expected_record_count']}"
        )
    ids = [row.get("example_id") for row in rows]
    if any(not isinstance(example_id, str) or not example_id for example_id in ids):
        raise OneShotTestError("TEST row lacks example_id")
    if len(ids) != len(set(ids)):
        raise OneShotTestError("TEST example_id values must be unique")
    return rows


def _metric_value(receipt: Mapping[str, Any], metric: str) -> float | None:
    direct = {
        "coverage_rate": receipt["prediction_present"],
        "json_parse_rate": receipt["json_parsed"],
    }
    if metric in direct:
        return float(direct[metric])
    extraction = {
        "schema_valid_rate": "schema_valid",
        "exact_match_rate": "whole_record_exact_match",
        "field_accuracy": "field_accuracy",
    }
    if metric in extraction:
        value = receipt["extraction"][extraction[metric]]
        return None if value is None else float(value)
    decision = {
        "decision_equivalence_rate": "decision_equivalent",
        "urgent_action_equivalence_rate": "urgent_action_equivalent",
        "referral_behavior_equivalence_rate": "referral_behavior_equivalent",
    }
    if metric in decision:
        return float(receipt["decision"][decision[metric]])
    raise OneShotTestError(f"unsupported preregistered metric: {metric}")


def _seed(base_seed: int, *parts: str) -> int:
    material = ":".join((str(base_seed), *parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(probability * len(ordered)) - 1))
    return ordered[index]


def _bootstrap_mean_ci(
    values: list[float], *, samples: int, confidence: float, seed: int
) -> dict[str, float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    count = len(values)
    estimates = [
        sum(values[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(samples)
    ]
    tail = (1.0 - confidence) / 2.0
    return {
        "confidence": confidence,
        "lower": _percentile(estimates, tail),
        "upper": _percentile(estimates, 1.0 - tail),
    }


def _candidate_summary(
    receipts: list[dict[str, Any]],
    *,
    candidate_id: str,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    aggregate = _aggregate(receipts)
    by_style: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        by_style[receipt["style_id"]].append(receipt)
    slices = {style: _aggregate(rows) for style, rows in sorted(by_style.items())}
    bootstrap = policy["scoring"]["confidence_intervals"]
    intervals: dict[str, Any] = {}
    for metric in policy["scoring"]["reported_metrics"]:
        values = [
            value
            for receipt in receipts
            if (value := _metric_value(receipt, metric)) is not None
        ]
        intervals[metric] = _bootstrap_mean_ci(
            values,
            samples=bootstrap["bootstrap_samples"],
            confidence=bootstrap["confidence"],
            seed=_seed(bootstrap["seed"], candidate_id, metric),
        )
    return {"aggregate": aggregate, "by_language_style": slices, "confidence_intervals": intervals}


def _paired_summary(
    selected: list[dict[str, Any]],
    base: list[dict[str, Any]],
    *,
    selected_id: str,
    base_id: str,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    selected_by_id = {receipt["example_id"]: receipt for receipt in selected}
    base_by_id = {receipt["example_id"]: receipt for receipt in base}
    if selected_by_id.keys() != base_by_id.keys():
        raise OneShotTestError("paired candidates do not cover identical TEST examples")
    bootstrap = policy["scoring"]["confidence_intervals"]
    metrics: dict[str, Any] = {}
    for metric in policy["scoring"]["paired_metrics"]:
        differences: list[float] = []
        for example_id in sorted(selected_by_id):
            selected_value = _metric_value(selected_by_id[example_id], metric)
            base_value = _metric_value(base_by_id[example_id], metric)
            if selected_value is not None and base_value is not None:
                differences.append(selected_value - base_value)
        point = sum(differences) / len(differences) if differences else None
        interval = _bootstrap_mean_ci(
            differences,
            samples=bootstrap["bootstrap_samples"],
            confidence=bootstrap["confidence"],
            seed=_seed(bootstrap["seed"], selected_id, base_id, metric),
        )
        metrics[metric] = {
            "paired_example_count": len(differences),
            "difference": point,
            "confidence_interval": interval,
        }
    return {"selected_candidate_id": selected_id, "base_candidate_id": base_id, "metrics": metrics}


def _paired_threshold_failures(
    paired: Mapping[str, Any], policy: Mapping[str, Any]
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for rule in policy["thresholds"]["paired_improvement"]:
        result = paired["metrics"][rule["metric"]]
        point = result["difference"]
        interval = result["confidence_interval"]
        point_ok = point is not None and (
            point > rule["minimum_point_difference"]
            if rule["strict"]
            else point >= rule["minimum_point_difference"]
        )
        lower = None if interval is None else interval["lower"]
        lower_ok = lower is not None and (
            lower > rule["minimum_ci_lower_bound"]
            if rule["strict"]
            else lower >= rule["minimum_ci_lower_bound"]
        )
        if not point_ok or not lower_ok:
            failures.append(
                {
                    "scope": "paired:selected-vs-base",
                    "metric": rule["metric"],
                    "minimum_point_difference": rule["minimum_point_difference"],
                    "minimum_ci_lower_bound": rule["minimum_ci_lower_bound"],
                    "strict": rule["strict"],
                    "actual_point_difference": point,
                    "actual_ci_lower_bound": lower,
                }
            )
    return failures


def evaluate_one_shot_test_predictions(
    prediction_paths: Mapping[str, str | Path],
    *,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Score TEST privately and return aggregate-only, hash-pinned evidence."""

    root = Path(repo_root).resolve()
    policy_file, policy = load_one_shot_test_policy(policy_path, repo_root=root)
    gold_rows = load_authorized_test_rows(policy, repo_root=root)
    expected_ids = {row["example_id"] for row in gold_rows}
    registered = {candidate["candidate_id"] for candidate in policy["candidates"]}
    if set(prediction_paths) != registered:
        raise OneShotTestError("prediction candidates differ from preregistration")

    receipts_by_candidate: dict[str, list[dict[str, Any]]] = {}
    summaries: dict[str, Any] = {}
    private_evidence: dict[str, Any] = {}
    for candidate in policy["candidates"]:
        candidate_id = candidate["candidate_id"]
        path = Path(prediction_paths[candidate_id])
        predictions = _load_predictions(path, expected_ids)
        receipts = score_candidate_predictions(gold_rows, predictions)
        receipts_by_candidate[candidate_id] = receipts
        summaries[candidate_id] = _candidate_summary(
            receipts, candidate_id=candidate_id, policy=policy
        )
        private_evidence[candidate_id] = {
            "prediction_sha256": hash_file(path)[0],
            "prediction_record_count": len(predictions),
        }

    comparison = policy["comparison"]
    paired = _paired_summary(
        receipts_by_candidate[comparison["selected_candidate_id"]],
        receipts_by_candidate[comparison["base_candidate_id"]],
        selected_id=comparison["selected_candidate_id"],
        base_id=comparison["base_candidate_id"],
        policy=policy,
    )
    selected_summary = summaries[comparison["selected_candidate_id"]]
    failures = _threshold_failures(
        selected_summary["aggregate"],
        policy["thresholds"]["selected_global_minimums"],
        "selected:global",
    )
    for style, metrics in selected_summary["by_language_style"].items():
        failures.extend(
            _threshold_failures(
                metrics,
                policy["thresholds"]["selected_per_style_minimums"],
                f"selected:style:{style}",
            )
        )
    failures.extend(_paired_threshold_failures(paired, policy))

    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "evaluation_id": policy["evaluation_id"],
        "authorization_id": policy["authorization_id"],
        "partition": "TEST",
        "one_shot": True,
        "aggregate_only": True,
        "routine_record_review_performed": False,
        "policy_path": policy_file.relative_to(root).as_posix(),
        "policy_sha256": hash_file(policy_file)[0],
        "dataset_sha256": policy["dataset"]["sha256"],
        "test_record_count": len(gold_rows),
        "candidate_results": summaries,
        "paired_comparison": paired,
        "private_prediction_evidence": private_evidence,
        "pass_fail": {
            "passed": not failures,
            "failure_count": len(failures),
            "failures": failures,
        },
    }
    report["report_sha256"] = hash_canonical(report)
    return report
