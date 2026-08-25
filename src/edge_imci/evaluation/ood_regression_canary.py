"""Informational-only evaluation for the frozen user-reported OOD canary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from edge_imci.evaluation.structured_extraction import parse_model_target_json
from edge_imci.model_io.encounter import validate_model_facing_encounter


ROOT = Path(__file__).resolve().parents[3]
CANARY_PATH = (
    ROOT / "configs/evaluation/user_reported_ood_regression_canary_v1.json"
)
CANARY_SHA256 = "4cfb6e9183a0c84731e069618feb85a9e2ed96c844c78ca502acef095481c9f7"
SPARSE_COUGH_CANARY_PATH = (
    ROOT
    / "configs/evaluation/user_reported_sparse_cough_ood_regression_canary_v1.json"
)
SPARSE_COUGH_CANARY_SHA256 = (
    "b6880718f6836f72d7724a7ef8e6d60df7275baed15e44bc9f63cf7e7c3d4158"
)
_MISSING = object()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    result: dict[str, Any] = {}
    for key in sorted(value):
        child = f"{prefix}.{key}" if prefix else key
        result.update(_flatten(value[key], child))
    return result


def _json_path(parts: list[Any]) -> str:
    return ".".join(str(part) for part in parts) or "$"


def _unsupported_key_paths(
    candidate: Any, expected_shape: Any, prefix: str = ""
) -> list[str]:
    if not isinstance(candidate, dict) or not isinstance(expected_shape, dict):
        return []
    paths: list[str] = []
    for key, value in candidate.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in expected_shape:
            paths.append(path)
        else:
            paths.extend(_unsupported_key_paths(value, expected_shape[key], path))
    return paths


def _unsupported_inferences(
    candidate: Any, expected: Any, prefix: str = ""
) -> list[dict[str, Any]]:
    if expected is None:
        if candidate is not _MISSING and candidate is not None:
            return [{"path": prefix, "expected": None, "actual": candidate}]
        return []
    if not isinstance(expected, dict):
        return []
    actual = candidate if isinstance(candidate, dict) else {}
    rows: list[dict[str, Any]] = []
    for key, expected_value in expected.items():
        path = f"{prefix}.{key}" if prefix else key
        rows.extend(
            _unsupported_inferences(actual.get(key, _MISSING), expected_value, path)
        )
    return rows


def load_frozen_canary(
    path: str | Path = CANARY_PATH,
    *,
    expected_sha256: str = CANARY_SHA256,
) -> dict[str, Any]:
    """Load the byte-pinned canary and validate its isolation and target contract."""

    canary_path = Path(path)
    if _sha256(canary_path) != expected_sha256:
        raise ValueError("OOD regression canary SHA-256 mismatch")
    canary = json.loads(canary_path.read_text(encoding="utf-8"))
    if not isinstance(canary, dict):
        raise ValueError("OOD regression canary must be one JSON object")
    expected_isolation = {
        "partition": "OOD_REGRESSION_CANARY",
        "campaign_data_eligible": False,
        "training_eligible": False,
        "validation_eligible": False,
        "test_eligible": False,
        "model_selection_eligible": False,
    }
    if canary.get("status") != "FROZEN":
        raise ValueError("OOD regression canary is not frozen")
    if canary.get("provenance", {}).get("failure_label") != "user-reported OOD failure":
        raise ValueError("OOD regression canary provenance label differs")
    if canary.get("isolation") != expected_isolation:
        raise ValueError("OOD regression canary isolation controls differ")
    schema_path = ROOT / canary["target_contract"]["schema_path"]
    if _sha256(schema_path) != canary["target_contract"]["schema_sha256"]:
        raise ValueError("model-facing schema SHA-256 mismatch")
    validate_model_facing_encounter(canary["expected_target"])
    return canary


def score_ood_canary_prediction(
    prediction: str | dict[str, Any],
    *,
    candidate_id: str,
    canary_path: str | Path = CANARY_PATH,
    expected_sha256: str = CANARY_SHA256,
) -> dict[str, Any]:
    """Score one candidate without producing model-selection evidence."""

    if not candidate_id:
        raise ValueError("candidate_id is required")
    canary = load_frozen_canary(canary_path, expected_sha256=expected_sha256)
    parse_error: str | None = None
    try:
        if isinstance(prediction, str):
            parsed = parse_model_target_json(prediction)
        elif isinstance(prediction, dict):
            parsed = prediction
        else:
            raise TypeError("prediction must be a JSON object or encoded object")
        parse_valid = True
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        parsed = {}
        parse_valid = False
        parse_error = str(error)

    schema = json.loads(
        (ROOT / canary["target_contract"]["schema_path"]).read_text(encoding="utf-8")
    )
    schema_errors = sorted(
        Draft202012Validator(schema).iter_errors(parsed),
        key=lambda error: list(error.absolute_path),
    )
    unsupported_keys = sorted(
        set(_unsupported_key_paths(parsed, canary["expected_target"]))
    )

    expected = _flatten(canary["expected_target"])
    actual = _flatten(parsed)
    mismatches = []
    for path in sorted(set(expected) | set(actual)):
        expected_value = expected.get(path, _MISSING)
        actual_value = actual.get(path, _MISSING)
        if expected_value != actual_value:
            mismatches.append(
                {
                    "path": path,
                    "expected": "<unsupported>" if expected_value is _MISSING else expected_value,
                    "actual": "<missing>" if actual_value is _MISSING else actual_value,
                }
            )
    unsupported_inferences = _unsupported_inferences(
        parsed, canary["expected_target"]
    )
    matched = len(expected) - sum(
        expected.get(row["path"], _MISSING) != actual.get(row["path"], _MISSING)
        for row in mismatches
        if row["path"] in expected
    )
    schema_valid = parse_valid and not schema_errors
    passed = schema_valid and not unsupported_keys and not mismatches
    return {
        "schema_version": "1.0.0",
        "evaluation_id": "edge-imci-user-reported-ood-regression-evaluation-v1",
        "candidate_id": candidate_id,
        "canary_id": canary["canary_id"],
        "canary_sha256": expected_sha256,
        "partition": "OOD_REGRESSION_CANARY",
        "provenance": canary["provenance"],
        "model_selection_eligible": False,
        "informational_only": True,
        "passed": passed,
        "parse": {"valid": parse_valid, "error": parse_error},
        "schema": {
            "valid": schema_valid,
            "errors": [
                {"path": _json_path(list(error.absolute_path)), "message": error.message}
                for error in schema_errors
            ],
        },
        "unsupported_keys": {"count": len(unsupported_keys), "paths": unsupported_keys},
        "unsupported_inferences": {
            "count": len(unsupported_inferences),
            "mismatches": unsupported_inferences,
        },
        "semantics": {
            "expected_field_count": len(expected),
            "matched_field_count": matched,
            "accuracy": matched / len(expected),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--prediction-file", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = score_ood_canary_prediction(
        args.prediction_file.read_text(encoding="utf-8"),
        candidate_id=args.candidate_id,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
