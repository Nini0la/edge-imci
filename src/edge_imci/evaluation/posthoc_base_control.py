"""Aggregate-only evaluation for an authorized post-hoc base-prompt correction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edge_imci.evaluation.base_control_prompt import (
    load_schema_informed_base_system_prompt,
)
from edge_imci.evaluation.checkpoint import _load_predictions, score_candidate_predictions
from edge_imci.evaluation.one_shot_test import (
    _candidate_summary,
    _paired_summary,
    load_authorized_test_rows,
    load_one_shot_test_policy,
)
from edge_imci.experiments.provenance import hash_canonical, hash_file, resolve_repo_path
from edge_imci.experiments.registry import load_json_object, validate_against_schema

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUTHORIZATION_PATH = (
    ROOT
    / "configs/evaluation/qwen3_0_6b_posthoc_schema_informed_base_control_v1.json"
)


class PosthocBaseControlError(ValueError):
    """Raised when the post-hoc authorization or evidence differs from its pins."""


def load_posthoc_base_control_authorization(
    authorization_path: str | Path = DEFAULT_AUTHORIZATION_PATH,
    *,
    repo_root: str | Path = ROOT,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Validate the explicit one-use authorization without loading TEST rows."""

    root = Path(repo_root).resolve()
    authorization_file = Path(authorization_path)
    if not authorization_file.is_absolute():
        authorization_file = resolve_repo_path(root, authorization_file)
    authorization = load_json_object(authorization_file)
    validate_against_schema(
        authorization,
        root
        / "experiments/registry/schemas/posthoc_base_control_authorization.schema.json",
    )

    original = authorization["original_evidence"]
    policy_file, policy = load_one_shot_test_policy(
        original["policy_path"], repo_root=root
    )
    if hash_file(policy_file)[0] != original["policy_sha256"]:
        raise PosthocBaseControlError("original TEST policy SHA-256 mismatch")
    if policy["authorization_id"] != original["authorization_id"]:
        raise PosthocBaseControlError("original TEST authorization identity mismatch")

    report_path = resolve_repo_path(root, original["aggregate_report_path"])
    if hash_file(report_path)[0] != original["aggregate_report_file_sha256"]:
        raise PosthocBaseControlError("original aggregate report file SHA-256 mismatch")
    report = load_json_object(report_path)
    if report.get("report_sha256") != original["aggregate_report_sha256"]:
        raise PosthocBaseControlError("original aggregate report identity mismatch")
    if report.get("test_status") != "CLOSED":
        raise PosthocBaseControlError("original TEST evidence is not closed")

    comparison = authorization["comparison"]
    candidates = {candidate["candidate_id"]: candidate for candidate in policy["candidates"]}
    base = candidates.get(comparison["source_base_candidate_id"])
    selected = candidates.get(comparison["historical_selected_candidate_id"])
    if base is None or base["role"] != "BASE_CONTROL" or base["kind"] != "HF_BASE":
        raise PosthocBaseControlError("authorized source base candidate is invalid")
    if selected is None or selected["role"] != "SELECTED_FINE_TUNE":
        raise PosthocBaseControlError("authorized historical selected candidate is invalid")

    treatment = authorization["prompt_treatment"]
    _, hashes = load_schema_informed_base_system_prompt(
        resolve_repo_path(root, treatment["schema_path"]),
        resolve_repo_path(root, treatment["example_output_path"]),
    )
    for name in ("schema_sha256", "example_output_sha256", "prompt_sha256"):
        if hashes[name] != treatment[name]:
            raise PosthocBaseControlError(f"authorized {name} mismatch")
    if authorization["generation"] != {
        key: policy["generation"][key]
        for key in ("chat_template", "enable_thinking", "max_new_tokens", "do_sample", "batch_size")
    }:
        raise PosthocBaseControlError("generation settings differ from the original TEST")
    return authorization_file, authorization, policy


def evaluate_posthoc_base_control_predictions(
    corrected_base_predictions_path: str | Path,
    historical_selected_predictions_path: str | Path,
    *,
    authorization_path: str | Path = DEFAULT_AUTHORIZATION_PATH,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Compare new base predictions with preserved selected predictions privately."""

    root = Path(repo_root).resolve()
    authorization_file, authorization, policy = (
        load_posthoc_base_control_authorization(
            authorization_path, repo_root=root
        )
    )
    gold_rows = load_authorized_test_rows(policy, repo_root=root)
    expected_ids = {row["example_id"] for row in gold_rows}
    base_path = Path(corrected_base_predictions_path)
    selected_path = Path(historical_selected_predictions_path)
    base_predictions = _load_predictions(base_path, expected_ids)
    selected_predictions = _load_predictions(selected_path, expected_ids)
    comparison = authorization["comparison"]
    if hash_file(selected_path)[0] != comparison["historical_selected_prediction_sha256"]:
        raise PosthocBaseControlError("historical selected prediction SHA-256 mismatch")

    base_receipts = score_candidate_predictions(gold_rows, base_predictions)
    selected_receipts = score_candidate_predictions(gold_rows, selected_predictions)
    base_id = comparison["corrected_base_candidate_id"]
    selected_id = comparison["historical_selected_candidate_id"]
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "diagnostic_id": authorization["diagnostic_id"],
        "status": "POST_HOC_DIAGNOSTIC",
        "partition": "TEST",
        "post_hoc": True,
        "untouched_test_claim": False,
        "new_pass_fail_claim": False,
        "aggregate_only": True,
        "routine_record_review_performed": False,
        "authorization_path": authorization_file.relative_to(root).as_posix(),
        "authorization_sha256": hash_file(authorization_file)[0],
        "original_evidence": authorization["original_evidence"],
        "test_record_count": len(gold_rows),
        "candidate_results": {
            base_id: _candidate_summary(
                base_receipts, candidate_id=base_id, policy=policy
            ),
            selected_id: _candidate_summary(
                selected_receipts, candidate_id=selected_id, policy=policy
            ),
        },
        "paired_comparison": _paired_summary(
            selected_receipts,
            base_receipts,
            selected_id=selected_id,
            base_id=base_id,
            policy=policy,
        ),
        "private_prediction_evidence": {
            base_id: {
                "prediction_sha256": hash_file(base_path)[0],
                "prediction_record_count": len(base_predictions),
            },
            selected_id: {
                "prediction_sha256": hash_file(selected_path)[0],
                "prediction_record_count": len(selected_predictions),
                "historical_reuse": True,
            },
        },
    }
    report["report_sha256"] = hash_canonical(report)
    return report
