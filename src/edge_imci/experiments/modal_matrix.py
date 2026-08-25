"""Guarded Modal execution for an authorized, compiled training matrix."""

from __future__ import annotations

import json
import subprocess
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from edge_imci.experiments.provenance import atomic_write_json, hash_canonical
from edge_imci.experiments.registry import REPO_ROOT, load_json_object
from edge_imci.experiments.tracking import validate_run_sidecar
from edge_imci.training.finetune import training_tracking

MODULE = "edge_imci.training.modal_finetune"


class ModalMatrixError(RuntimeError):
    """Raised when an authorized matrix cannot safely continue."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _verified_plan(path: Path) -> dict[str, Any]:
    plan = load_json_object(path)
    claimed = plan.get("plan_sha256")
    unsigned = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if not isinstance(claimed, str) or hash_canonical(unsigned) != claimed:
        raise ModalMatrixError("compiled plan SHA-256 mismatch")
    if not plan["controls"]["launch_authorized"]:
        raise ModalMatrixError("matrix launch is not authorized")
    unsatisfied = [
        gate["gate_id"] for gate in plan["controls"]["gates"] if not gate["satisfied"]
    ]
    if unsatisfied:
        raise ModalMatrixError(f"matrix gates are unsatisfied: {unsatisfied}")
    if plan["summary"]["estimated_gpu_seconds"] > plan["budget"][
        "max_estimated_gpu_seconds"
    ]:
        raise ModalMatrixError("compiled plan exceeds its GPU budget")
    return plan


def load_authorized_schedule(
    plan_path: str | Path,
    manifest_path: str | Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    plan = _verified_plan(Path(plan_path))
    manifest = load_json_object(manifest_path)
    if manifest.get("plan_sha256") != plan["plan_sha256"]:
        raise ModalMatrixError("config manifest and plan SHA-256 disagree")
    by_cell = {item["cell_id"]: item for item in manifest["configs"]}
    ready = [cell for cell in plan["cells"] if cell["state"] == "READY"]
    if set(by_cell) != {cell["cell_id"] for cell in ready}:
        raise ModalMatrixError("config manifest does not contain every READY cell")
    for cell in ready:
        item = by_cell[cell["cell_id"]]
        if item["config_sha256"] != cell["resolved_config_sha256"]:
            raise ModalMatrixError(f"config digest mismatch: {cell['cell_id']}")
        config = load_json_object(item["path"])
        if hash_canonical(config) != item["config_sha256"]:
            raise ModalMatrixError(f"materialized config changed: {cell['cell_id']}")
        if training_tracking(config)["experiment_id"] != plan["registry"][
            "experiment_id"
        ]:
            raise ModalMatrixError(
                f"config experiment differs from plan: {cell['cell_id']}"
            )
        cell["materialized_config_path"] = item["path"]
    return plan, ready


def command_for_cell(
    cell: dict[str, Any], *, run_name: str | None = None
) -> list[str]:
    return [
        "modal",
        "run",
        "-m",
        MODULE,
        "--run-name",
        run_name or cell["cell_id"],
        "--config-path",
        cell["materialized_config_path"],
    ]


def _existing_success(
    root: Path, experiment_id: str, cell: dict[str, Any]
) -> dict[str, Any] | None:
    experiment_dir = root / "experiments/training" / experiment_id
    candidates = [experiment_dir / cell["cell_id"] / "edgeimci_run.json"]
    candidates.extend(
        sorted(
            experiment_dir.glob(
                f"{cell['cell_id']}--attempt-*/edgeimci_run.json"
            )
        )
    )
    for sidecar in candidates:
        if not sidecar.is_file():
            continue
        record = validate_run_sidecar(sidecar)
        if record["status"] == "SUCCEEDED":
            return _result_from_sidecar(cell, sidecar, record, skipped=True)
    return None


def _next_run_name(root: Path, experiment_id: str, cell_id: str) -> str:
    experiment_dir = root / "experiments/training" / experiment_id
    if not (experiment_dir / cell_id).exists():
        return cell_id
    attempt = 2
    while (experiment_dir / f"{cell_id}--attempt-{attempt}").exists():
        attempt += 1
    return f"{cell_id}--attempt-{attempt}"


def _result_from_sidecar(
    cell: dict[str, Any],
    sidecar: Path,
    record: dict[str, Any],
    *,
    skipped: bool,
) -> dict[str, Any]:
    evaluation = record["scientific_results"].get("checkpoint_evaluation")
    if not isinstance(evaluation, dict):
        raise ModalMatrixError(f"missing checkpoint evaluation: {cell['cell_id']}")
    aggregate = evaluation.get("aggregate", {})
    if aggregate.get("coverage_rate") != 1.0 or aggregate.get(
        "latency_observation_count"
    ) != 115:
        raise ModalMatrixError(f"incomplete validation evidence: {cell['cell_id']}")
    return {
        "cell_id": cell["cell_id"],
        "status": "SUCCEEDED",
        "skipped_existing": skipped,
        "run_id": record["run_id"],
        "sidecar_path": str(sidecar.relative_to(REPO_ROOT)),
        "gpu_seconds": record["telemetry"]["gpu_seconds"],
        "promotion_eligible": evaluation["promotion"]["eligible"],
        "aggregate": aggregate,
    }


def _run_cell(
    root: Path,
    experiment_id: str,
    cell: dict[str, Any],
    logs_dir: Path,
) -> dict[str, Any]:
    run_name = _next_run_name(root, experiment_id, cell["cell_id"])
    log_path = logs_dir / f"{run_name}.log"
    command = command_for_cell(cell, run_name=run_name)
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=root,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if completed.returncode != 0:
        return {
            "cell_id": cell["cell_id"],
            "run_name": run_name,
            "status": "FAILED",
            "returncode": completed.returncode,
            "log_path": str(log_path.relative_to(root)),
            "estimated_gpu_seconds": cell["estimated_gpu_seconds"],
        }
    sidecar = (
        root
        / "experiments/training"
        / experiment_id
        / run_name
        / "edgeimci_run.json"
    )
    try:
        record = validate_run_sidecar(sidecar)
        result = _result_from_sidecar(cell, sidecar, record, skipped=False)
    except (KeyError, ModalMatrixError, OSError, ValueError) as error:
        return {
            "cell_id": cell["cell_id"],
            "run_name": run_name,
            "status": "FAILED",
            "error": f"{type(error).__name__}: {error}",
            "log_path": str(log_path.relative_to(root)),
            "estimated_gpu_seconds": cell["estimated_gpu_seconds"],
        }
    result["log_path"] = str(log_path.relative_to(root))
    result["run_name"] = run_name
    return result


def run_modal_matrix(
    plan_path: str | Path,
    manifest_path: str | Path,
    *,
    repo_root: str | Path = REPO_ROOT,
    canary_only: bool = False,
) -> dict[str, Any]:
    """Execute READY cells, halting new scheduling after any systemic failure."""

    root = Path(repo_root).resolve()
    plan, cells = load_authorized_schedule(plan_path, manifest_path)
    experiment_id = plan["registry"]["experiment_id"]
    execution_dir = (
        root / "experiments/training/matrices" / plan["matrix_id"] / "execution"
    )
    logs_dir = execution_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    state_path = execution_dir / "state.json"
    lock = threading.Lock()
    results: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for cell in cells:
        existing = _existing_success(root, experiment_id, cell)
        if existing:
            results.append(existing)
        else:
            pending.append(cell)
    pending.sort(key=lambda cell: (cell["estimated_gpu_seconds"], cell["cell_id"]))
    if canary_only and pending:
        pending = pending[:1]

    state: dict[str, Any] = {
        "schema_version": "1.0.0",
        "matrix_id": plan["matrix_id"],
        "plan_sha256": plan["plan_sha256"],
        "operating_mode": "AUTOMATIC_EVIDENCE",
        "started_at": _now(),
        "finished_at": None,
        "status": "RUNNING",
        "canary_only": canary_only,
        "results": results,
    }
    atomic_write_json(state_path, state)

    max_workers = 1 if canary_only else plan["execution"]["max_parallel_runs"]
    iterator = iter(pending)
    failed = False
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        active: dict[Future, dict[str, Any]] = {}
        for _ in range(max_workers):
            cell = next(iterator, None)
            if cell is not None:
                active[executor.submit(_run_cell, root, experiment_id, cell, logs_dir)] = cell
        while active:
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                cell = active.pop(future)
                try:
                    result = future.result()
                except (OSError, RuntimeError, ValueError) as error:
                    result = {
                        "cell_id": cell["cell_id"],
                        "status": "FAILED",
                        "error": f"{type(error).__name__}: {error}",
                    }
                with lock:
                    results.append(result)
                    state["results"] = results
                    atomic_write_json(state_path, state)
                print(
                    json.dumps(
                        {
                            "cell_id": result["cell_id"],
                            "status": result["status"],
                            "gpu_seconds": result.get("gpu_seconds"),
                            "promotion_eligible": result.get("promotion_eligible"),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                if result["status"] != "SUCCEEDED":
                    failed = True
            if not failed:
                while len(active) < max_workers:
                    cell = next(iterator, None)
                    if cell is None:
                        break
                    active[executor.submit(_run_cell, root, experiment_id, cell, logs_dir)] = cell

    state["finished_at"] = _now()
    state["status"] = "FAILED" if failed else "SUCCEEDED"
    state["results"] = sorted(results, key=lambda item: item["cell_id"])
    state["actual_gpu_seconds"] = sum(
        float(item.get("gpu_seconds") or 0) for item in state["results"]
    )
    state["unmetered_failed_estimate_seconds"] = sum(
        float(item.get("estimated_gpu_seconds") or 0)
        for item in state["results"]
        if item["status"] != "SUCCEEDED"
    )
    state["successful_cell_count"] = sum(
        item["status"] == "SUCCEEDED" for item in state["results"]
    )
    state["failed_cell_count"] = sum(
        item["status"] != "SUCCEEDED" for item in state["results"]
    )
    atomic_write_json(state_path, state)
    if failed:
        raise ModalMatrixError(f"matrix halted; see {state_path}")
    return state
