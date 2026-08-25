"""Matched corpus evaluation for structured-extraction checkpoints."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from edge_imci.evaluation.structured_extraction import (
    compare_decision_equivalence,
    parse_model_target_json,
    score_structured_extraction,
)
from edge_imci.experiments.provenance import (
    hash_canonical,
    hash_file,
    resolve_repo_path,
)
from edge_imci.experiments.registry import (
    SCHEMA_DIR,
    load_json_object,
    validate_against_schema,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = (
    ROOT / "configs/evaluation/structured_extraction_checkpoint_policy_v1.json"
)
POLICY_SCHEMA_PATH = SCHEMA_DIR / "checkpoint_evaluation_policy.schema.json"
_STYLE = re.compile(r"__(phc-[a-z0-9-]+)__v[0-9]+$")
class CheckpointEvaluationError(ValueError):
    """Raised when prediction evidence violates the matched evaluation contract."""


def load_checkpoint_evaluation_policy(
    policy_path: str | Path = DEFAULT_POLICY_PATH,
    *,
    repo_root: str | Path = ROOT,
) -> tuple[Path, dict[str, Any]]:
    """Load and validate the pinned policy against the selected repository root."""

    root = Path(repo_root).resolve()
    policy_file = Path(policy_path)
    if not policy_file.is_absolute():
        policy_file = resolve_repo_path(root, policy_file)
    policy = load_json_object(policy_file)
    schema_path = (
        root
        / "experiments/registry/schemas/checkpoint_evaluation_policy.schema.json"
    )
    validate_against_schema(policy, schema_path)
    return policy_file, policy


def _iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise CheckpointEvaluationError(f"blank JSONL row at {path}:{line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise CheckpointEvaluationError(
                    f"invalid JSON at {path}:{line_number}: {error.msg}"
                ) from error
            if not isinstance(row, dict):
                raise CheckpointEvaluationError(
                    f"JSONL row at {path}:{line_number} must be an object"
                )
            yield line_number, row


def _style_id(row: Mapping[str, Any]) -> str:
    match = _STYLE.search(str(row.get("variant_id", "")))
    return match.group(1) if match else "unknown-style"


def _load_gold(policy: Mapping[str, Any], root: Path) -> list[dict[str, Any]]:
    dataset_path = resolve_repo_path(root, policy["dataset"]["path"])
    actual_sha256, _ = hash_file(dataset_path)
    if actual_sha256 != policy["dataset"]["sha256"]:
        raise CheckpointEvaluationError("evaluation dataset SHA-256 mismatch")
    partition = policy["dataset"]["partition"]
    if partition != "VALIDATION" or not policy["controls"]["test_partition_prohibited"]:
        raise CheckpointEvaluationError("checkpoint selection must use VALIDATION only")
    rows = [row for _, row in _iter_jsonl(dataset_path) if row.get("partition") == partition]
    expected = policy["dataset"]["expected_record_count"]
    if len(rows) != expected:
        raise CheckpointEvaluationError(
            f"evaluation set contains {len(rows)} rows, expected {expected}"
        )
    ids = [row.get("example_id") for row in rows]
    if any(not isinstance(example_id, str) or not example_id for example_id in ids):
        raise CheckpointEvaluationError("evaluation row lacks example_id")
    if len(ids) != len(set(ids)):
        raise CheckpointEvaluationError("evaluation example_id values must be unique")
    return rows


def _load_predictions(path: Path, expected_ids: set[str]) -> dict[str, dict[str, Any]]:
    predictions: dict[str, dict[str, Any]] = {}
    for line_number, row in _iter_jsonl(path):
        example_id = row.get("example_id")
        if not isinstance(example_id, str) or not example_id:
            raise CheckpointEvaluationError(
                f"prediction row {line_number} lacks example_id"
            )
        if example_id not in expected_ids:
            raise CheckpointEvaluationError(f"unknown prediction example_id: {example_id}")
        if example_id in predictions:
            raise CheckpointEvaluationError(f"duplicate prediction: {example_id}")
        if "prediction" not in row:
            raise CheckpointEvaluationError(
                f"prediction row {line_number} lacks prediction"
            )
        latency = row.get("latency_seconds")
        if latency is not None and (
            not isinstance(latency, (int, float)) or isinstance(latency, bool) or latency < 0
        ):
            raise CheckpointEvaluationError(
                f"prediction row {line_number} has invalid latency_seconds"
            )
        predictions[example_id] = row
    return predictions


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def _aggregate(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(receipts)
    latencies = [row["latency_seconds"] for row in receipts if row["latency_seconds"] is not None]
    metrics: dict[str, Any] = {
        "example_count": count,
        "coverage_rate": _mean([float(row["prediction_present"]) for row in receipts]),
        "json_parse_rate": _mean([float(row["json_parsed"]) for row in receipts]),
        "schema_valid_rate": _mean([float(row["extraction"]["schema_valid"]) for row in receipts]),
        "exact_match_rate": _mean(
            [float(row["extraction"]["whole_record_exact_match"]) for row in receipts]
        ),
        "decision_equivalence_rate": _mean(
            [float(row["decision"]["decision_equivalent"]) for row in receipts]
        ),
        "urgency_equivalence_rate": _mean(
            [float(row["decision"]["urgency_equivalent"]) for row in receipts]
        ),
        "urgent_action_equivalence_rate": _mean(
            [float(row["decision"]["urgent_action_equivalent"]) for row in receipts]
        ),
        "referral_behavior_equivalence_rate": _mean(
            [float(row["decision"]["referral_behavior_equivalent"]) for row in receipts]
        ),
        "management_equivalence_rate": _mean(
            [float(row["decision"]["management_equivalent"]) for row in receipts]
        ),
        "latency_observation_count": len(latencies),
        "p50_latency_seconds": _percentile(latencies, 0.50),
        "p95_latency_seconds": _percentile(latencies, 0.95),
    }
    for name in (
        "field_accuracy",
        "known_positive_precision",
        "known_positive_recall",
        "known_negative_accuracy",
        "unknown_preservation_accuracy",
        "measurement_accuracy",
        "duration_accuracy",
        "qualifier_accuracy",
        "pre_post_intervention_accuracy",
    ):
        values = [row["extraction"][name] for row in receipts]
        applicable = [float(value) for value in values if value is not None]
        metrics[name] = _mean(applicable) if applicable else None
    return metrics


def _threshold_failures(
    metrics: Mapping[str, Any], thresholds: Mapping[str, float], prefix: str
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for metric, minimum in thresholds.items():
        actual = metrics.get(metric)
        if actual is None or actual < minimum:
            failures.append(
                {
                    "scope": prefix,
                    "metric": metric,
                    "minimum": minimum,
                    "actual": actual,
                }
            )
    return failures


def score_candidate_predictions(
    gold_rows: list[dict[str, Any]],
    predictions: Mapping[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Score matched predictions while preserving one receipt per gold row."""

    receipts: list[dict[str, Any]] = []
    for gold_row in gold_rows:
        example_id = gold_row["example_id"]
        gold = parse_model_target_json(gold_row["messages"][-1]["content"])
        source = predictions.get(example_id)
        parsed: dict[str, Any] = {}
        parse_error = None
        if source is not None:
            try:
                raw = source["prediction"]
                if isinstance(raw, str):
                    parsed = parse_model_target_json(raw)
                elif isinstance(raw, dict):
                    parsed = raw
                else:
                    raise TypeError("prediction must be a JSON object or encoded object")
            except (json.JSONDecodeError, TypeError, ValueError) as error:
                parse_error = str(error)
        extraction = score_structured_extraction(gold, parsed).to_dict()
        decision = compare_decision_equivalence(gold, parsed).to_dict()
        receipts.append(
            {
                "example_id": example_id,
                "source_case_id": gold_row["source_case_id"],
                "style_id": _style_id(gold_row),
                "prediction_present": source is not None,
                "json_parsed": source is not None and parse_error is None,
                "parse_error": parse_error,
                "latency_seconds": source.get("latency_seconds") if source else None,
                "extraction": extraction,
                "decision": decision,
            }
        )
    return receipts


def evaluate_checkpoint_predictions(
    predictions_path: str | Path,
    *,
    candidate_id: str,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Evaluate one checkpoint's complete VALIDATION predictions."""

    root = Path(repo_root).resolve()
    policy_file, policy = load_checkpoint_evaluation_policy(
        policy_path, repo_root=root
    )
    gold_rows = _load_gold(policy, root)
    expected_ids = {row["example_id"] for row in gold_rows}
    prediction_file = Path(predictions_path)
    if not prediction_file.is_absolute():
        prediction_file = resolve_repo_path(root, prediction_file)
    predictions = _load_predictions(prediction_file, expected_ids)

    receipts = score_candidate_predictions(gold_rows, predictions)

    aggregate = _aggregate(receipts)
    by_style: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for receipt in receipts:
        by_style[receipt["style_id"]].append(receipt)
    slices = {style: _aggregate(rows) for style, rows in sorted(by_style.items())}
    failures = _threshold_failures(
        aggregate, policy["promotion"]["global_minimums"], "global"
    )
    for style, metrics in slices.items():
        failures.extend(
            _threshold_failures(
                metrics, policy["promotion"]["per_style_minimums"], f"style:{style}"
            )
        )
    ranking_vector = [
        {"metric": metric, "value": aggregate[metric]}
        for metric in policy["promotion"]["ranking_order"]
    ]
    try:
        prediction_reference = prediction_file.relative_to(root).as_posix()
    except ValueError:
        prediction_reference = str(prediction_file)
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "evaluation_id": policy["evaluation_id"],
        "candidate_id": candidate_id,
        "partition": "VALIDATION",
        "test_partition_used": False,
        "policy_path": policy_file.relative_to(root).as_posix(),
        "policy_sha256": hash_canonical(policy),
        "dataset_path": policy["dataset"]["path"],
        "dataset_sha256": policy["dataset"]["sha256"],
        "prediction_path": prediction_reference,
        "prediction_sha256": hash_file(prediction_file)[0],
        "aggregate": aggregate,
        "slices": slices,
        "promotion": {
            "eligible": not failures,
            "failure_count": len(failures),
            "failures": failures,
            "ranking_vector": ranking_vector,
        },
        "receipts": receipts,
    }
    result["report_sha256"] = hash_canonical(result)
    return result
