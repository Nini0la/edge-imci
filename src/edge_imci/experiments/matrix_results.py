"""Deterministic aggregate leaderboard construction for a completed matrix."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edge_imci.experiments.provenance import hash_canonical, resolve_repo_path
from edge_imci.experiments.registry import (
    DEFAULT_RUN_INDEX_PATH,
    REPO_ROOT,
    load_json_object,
)
from edge_imci.experiments.tracking import validate_run_sidecar


class MatrixResultsError(ValueError):
    """Raised when matrix result evidence is incomplete or inconsistent."""


def _verified_plan(path: Path) -> dict[str, Any]:
    plan = load_json_object(path)
    claimed = plan.get("plan_sha256")
    unsigned = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if not isinstance(claimed, str) or hash_canonical(unsigned) != claimed:
        raise MatrixResultsError("compiled plan SHA-256 mismatch")
    return plan


def build_matrix_leaderboard(
    plan_path: str | Path,
    state_path: str | Path,
    reused_evaluation_path: str | Path,
    policy_path: str | Path,
    *,
    repo_root: str | Path = REPO_ROOT,
    run_index_path: str | Path = DEFAULT_RUN_INDEX_PATH,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()

    def local(value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else resolve_repo_path(root, path)

    plan = _verified_plan(local(plan_path))
    state = load_json_object(local(state_path))
    if state.get("status") != "SUCCEEDED" or state.get("plan_sha256") != plan["plan_sha256"]:
        raise MatrixResultsError("matrix execution state is not a matching success")
    policy = load_json_object(local(policy_path))
    ranking_order = policy["promotion"]["ranking_order"]
    by_cell = {cell["cell_id"]: cell for cell in plan["cells"]}
    results = {item["cell_id"]: dict(item) for item in state["results"]}

    reused = [cell for cell in plan["cells"] if cell["state"] == "REUSED"]
    if len(reused) != 1:
        raise MatrixResultsError("leaderboard expects exactly one reused baseline cell")
    reused_cell = reused[0]
    receipt = load_json_object(local(reused_evaluation_path))["result"]
    if (
        receipt.get("status") != "SUCCEEDED"
        or receipt.get("cell_id") != reused_cell["cell_id"]
        or receipt.get("test_partition_used") is not False
    ):
        raise MatrixResultsError("reused checkpoint evaluation is incomplete")
    run_index = load_json_object(local(run_index_path))
    indexed = {item["run_id"]: item for item in run_index["runs"]}
    source_run_id = reused_cell["reused_run_id"]
    if source_run_id not in indexed:
        raise MatrixResultsError("reused source run is absent from the run index")
    sidecar = validate_run_sidecar(root / indexed[source_run_id]["sidecar_path"])
    results[reused_cell["cell_id"]] = {
        "cell_id": reused_cell["cell_id"],
        "status": "SUCCEEDED",
        "run_id": source_run_id,
        "reused_training_run": True,
        "promotion_eligible": receipt["promotion"]["eligible"],
        "aggregate": receipt["aggregate"],
        "gpu_seconds": (
            float(sidecar["telemetry"]["gpu_seconds"])
            + float(receipt["duration_seconds"])
        ),
        "training_gpu_seconds": sidecar["telemetry"]["gpu_seconds"],
        "evaluation_gpu_seconds": receipt["duration_seconds"],
    }

    if set(results) != set(by_cell):
        missing = sorted(set(by_cell) - set(results))
        extra = sorted(set(results) - set(by_cell))
        raise MatrixResultsError(
            f"leaderboard evidence mismatch; missing={missing}, extra={extra}"
        )
    rows: list[dict[str, Any]] = []
    for cell_id, result in results.items():
        if result.get("status") != "SUCCEEDED":
            raise MatrixResultsError(f"non-successful result in leaderboard: {cell_id}")
        aggregate = result["aggregate"]
        row = {
            "cell_id": cell_id,
            "axis_values": by_cell[cell_id]["axis_values"],
            "run_id": result["run_id"],
            "reused_training_run": bool(result.get("reused_training_run", False)),
            "promotion_eligible": result["promotion_eligible"],
            "gpu_seconds": result["gpu_seconds"],
            "metrics": {metric: aggregate[metric] for metric in ranking_order},
            "p95_latency_seconds": aggregate["p95_latency_seconds"],
        }
        rows.append(row)

    def rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            0 if row["promotion_eligible"] else 1,
            *(-float(row["metrics"][metric]) for metric in ranking_order),
            float(row["gpu_seconds"]),
            row["cell_id"],
        )

    rows.sort(key=rank_key)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    winner = rows[0] if rows and rows[0]["promotion_eligible"] else None
    leaderboard: dict[str, Any] = {
        "schema_version": "1.0.0",
        "matrix_id": plan["matrix_id"],
        "plan_sha256": plan["plan_sha256"],
        "operating_mode": "AUTOMATIC_EVIDENCE",
        "test_partition_used": False,
        "ranking_order": ranking_order,
        "tie_breakers": ["gpu_seconds_ascending", "cell_id_ascending"],
        "cell_count": len(rows),
        "eligible_count": sum(row["promotion_eligible"] for row in rows),
        "recorded_matrix_gpu_seconds": state["actual_gpu_seconds"],
        "winner_cell_id": winner["cell_id"] if winner else None,
        "rows": rows,
    }
    leaderboard["leaderboard_sha256"] = hash_canonical(leaderboard)
    return leaderboard
