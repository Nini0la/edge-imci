"""Deterministic compilation of registry-bound experiment sweeps."""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping
from copy import deepcopy
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any

from edge_imci.experiments.provenance import (
    atomic_write_json,
    hash_canonical,
    resolve_repo_path,
)
from edge_imci.experiments.registry import (
    REPO_ROOT,
    SCHEMA_DIR,
    ExperimentRegistry,
    load_json_object,
    validate_against_schema,
)

DEFAULT_SWEEP_SCHEMA_PATH = SCHEMA_DIR / "experiment_sweep.schema.json"


class MatrixCompilationError(ValueError):
    """Raised when a sweep cannot be compiled into safe, reproducible cells."""


def _set_existing_path(config: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    if not parts or any(not part or part.startswith("_") for part in parts):
        raise MatrixCompilationError(f"invalid override path: {dotted_path}")
    current: Any = config
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            raise MatrixCompilationError(f"override path does not exist: {dotted_path}")
        current = current[part]
    final = parts[-1]
    if not isinstance(current, dict) or final not in current:
        raise MatrixCompilationError(f"override path does not exist: {dotted_path}")
    current[final] = deepcopy(value)


def _decimal(value: float | str) -> Decimal:
    return Decimal(str(value))


def _seconds(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN))


def _estimate_gpu_seconds(
    resolved_config: Mapping[str, Any], estimation: Mapping[str, Any]
) -> float:
    baseline_total = _decimal(estimation["baseline_gpu_seconds"])
    baseline_train = _decimal(estimation["baseline_train_seconds"])
    baseline_epochs = _decimal(estimation["baseline_epochs"])
    contingency = _decimal(estimation["contingency_multiplier"])
    if baseline_train > baseline_total:
        raise MatrixCompilationError(
            "baseline_train_seconds cannot exceed baseline_gpu_seconds"
        )
    epochs = _decimal(resolved_config["optimization"]["epochs"])
    if epochs <= 0 or baseline_epochs <= 0:
        raise MatrixCompilationError("epoch estimates require positive epoch counts")
    fixed = baseline_total - baseline_train
    return _seconds((fixed + baseline_train * epochs / baseline_epochs) * contingency)


def _blocked_reasons(spec: Mapping[str, Any]) -> list[str]:
    reasons = [
        f"gate:{gate['gate_id']}"
        for gate in spec["controls"]["gates"]
        if not gate["satisfied"]
    ]
    if not spec["controls"]["launch_authorized"]:
        reasons.append("launch_authorization")
    return reasons


def compile_experiment_matrix(
    spec_path: str | Path,
    *,
    registry: ExperimentRegistry | None = None,
    repo_root: str | Path = REPO_ROOT,
    schema_path: str | Path = DEFAULT_SWEEP_SCHEMA_PATH,
) -> dict[str, Any]:
    """Expand a reviewed sweep into immutable, budget-checked run cells.

    Compilation is deliberately side-effect free: it never launches compute or
    mutates the experiment registry.
    """

    root = Path(repo_root).resolve()
    spec_file = Path(spec_path)
    if not spec_file.is_absolute():
        spec_file = resolve_repo_path(root, spec_file)
    spec = load_json_object(spec_file)
    validate_against_schema(spec, schema_path)

    active_registry = registry or ExperimentRegistry(repo_root=root)
    active_registry.validate()
    try:
        experiment = active_registry.get(spec["experiment_id"])
    except KeyError as error:
        raise MatrixCompilationError(str(error)) from error
    if experiment["experiment_type"] != "TRAINING":
        raise MatrixCompilationError("experiment matrices currently require TRAINING")
    if experiment["status"] in {"SUPERSEDED", "FAILED"}:
        raise MatrixCompilationError(
            f"cannot compile cells for {experiment['status']} experiment"
        )

    base_path = resolve_repo_path(root, spec["base_config_path"])
    base_config = load_json_object(base_path)
    if base_config.get("base_model", {}).get("revision") in {None, "", "main"}:
        raise MatrixCompilationError("base model must use an immutable revision")
    if not spec["controls"]["test_partition_prohibited"]:
        raise MatrixCompilationError("training matrices must prohibit TEST use")

    for gate in spec["controls"]["gates"]:
        if gate["satisfied"] and not gate.get("evidence_ref"):
            raise MatrixCompilationError(
                f"satisfied gate lacks evidence_ref: {gate['gate_id']}"
            )
        if gate.get("evidence_ref"):
            resolve_repo_path(root, gate["evidence_ref"])

    axis_names = sorted(spec["axes"])
    axis_values = [spec["axes"][name] for name in axis_names]
    combinations = list(itertools.product(*axis_values))
    if len(combinations) > spec["budget"]["max_runs"]:
        raise MatrixCompilationError(
            f"matrix expands to {len(combinations)} runs, above max_runs={spec['budget']['max_runs']}"
        )

    registered_run_ids = set(experiment["run_ids"])
    reuse_by_digest: dict[str, dict[str, Any]] = {}
    for reused in spec.get("reused_cells", []):
        if set(reused["axis_values"]) != set(axis_names):
            raise MatrixCompilationError(
                f"reused cell {reused['run_id']} must specify every matrix axis"
            )
        if reused["run_id"] not in registered_run_ids:
            raise MatrixCompilationError(
                f"reused run is not linked from registry experiment: {reused['run_id']}"
            )
        digest = hash_canonical(reused["axis_values"])
        if digest in reuse_by_digest:
            raise MatrixCompilationError("reused_cells contain duplicate axis values")
        reuse_by_digest[digest] = reused

    reasons = _blocked_reasons(spec)
    definition_sha256 = hash_canonical(
        {
            key: value
            for key, value in experiment.items()
            if key not in {"status", "run_ids", "evidence"}
        }
    )
    cells: list[dict[str, Any]] = []
    matched_reuse: set[str] = set()
    for index, combination in enumerate(combinations, start=1):
        axis = dict(zip(axis_names, combination, strict=True))
        resolved = deepcopy(base_config)
        for dotted_path, value in sorted(spec.get("fixed_overrides", {}).items()):
            _set_existing_path(resolved, dotted_path, value)
        for dotted_path, value in axis.items():
            _set_existing_path(resolved, dotted_path, value)
        axis_digest = hash_canonical(axis)
        reused = reuse_by_digest.get(axis_digest)
        if reused:
            matched_reuse.add(axis_digest)
        config_digest = hash_canonical(resolved)
        cell_id = f"{spec['matrix_id']}--{index:03d}--{config_digest[:10]}"
        estimate = 0.0 if reused else _estimate_gpu_seconds(resolved, spec["estimation"])
        state = "REUSED" if reused else ("BLOCKED" if reasons else "READY")
        cells.append(
            {
                "cell_id": cell_id,
                "state": state,
                "axis_values": axis,
                "resolved_config_sha256": config_digest,
                "resolved_config": resolved,
                "estimated_gpu_seconds": estimate,
                "reused_run_id": reused["run_id"] if reused else None,
                "blocked_reasons": [] if reused else reasons,
            }
        )
    unmatched = set(reuse_by_digest) - matched_reuse
    if unmatched:
        raise MatrixCompilationError("a reused cell does not occur in the matrix axes")

    estimated_gpu_seconds = _seconds(
        sum((_decimal(cell["estimated_gpu_seconds"]) for cell in cells), Decimal(0))
    )
    maximum = _decimal(spec["budget"]["max_estimated_gpu_seconds"])
    if _decimal(estimated_gpu_seconds) > maximum:
        raise MatrixCompilationError(
            f"estimated GPU seconds {estimated_gpu_seconds} exceed budget {maximum}"
        )
    new_cells = [cell for cell in cells if cell["state"] != "REUSED"]
    summary = {
        "cell_count": len(cells),
        "new_run_count": len(new_cells),
        "reused_run_count": len(cells) - len(new_cells),
        "ready_run_count": sum(cell["state"] == "READY" for cell in cells),
        "blocked_run_count": sum(cell["state"] == "BLOCKED" for cell in cells),
        "estimated_gpu_seconds": estimated_gpu_seconds,
        "estimated_gpu_hours": float(
            (_decimal(estimated_gpu_seconds) / Decimal(3600)).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_EVEN
            )
        ),
        "max_parallel_runs": spec["execution"]["max_parallel_runs"],
        "minimum_execution_waves": math.ceil(
            len(new_cells) / spec["execution"]["max_parallel_runs"]
        )
        if new_cells
        else 0,
    }
    plan: dict[str, Any] = {
        "schema_version": "1.0.0",
        "matrix_id": spec["matrix_id"],
        "source_spec": spec_file.relative_to(root).as_posix(),
        "source_spec_sha256": hash_canonical(spec),
        "registry": {
            "registry_id": active_registry.matrix["registry_id"],
            "experiment_id": experiment["experiment_id"],
            "experiment_status_at_compile": experiment["status"],
            "experiment_definition_sha256": definition_sha256,
        },
        "base_config_path": base_path.relative_to(root).as_posix(),
        "base_config_sha256": hash_canonical(base_config),
        "execution": deepcopy(spec["execution"]),
        "budget": deepcopy(spec["budget"]),
        "controls": deepcopy(spec["controls"]),
        "summary": summary,
        "cells": cells,
    }
    plan["plan_sha256"] = hash_canonical(plan)
    return plan


def materialize_matrix_configs(
    plan_path: str | Path,
    output_dir: str | Path,
    *,
    repo_root: str | Path = REPO_ROOT,
) -> dict[str, Any]:
    """Write prospective resolved configs after verifying the compiled plan hash."""

    root = Path(repo_root).resolve()
    source = Path(plan_path)
    if not source.is_absolute():
        source = resolve_repo_path(root, source)
    plan = load_json_object(source)
    claimed_digest = plan.get("plan_sha256")
    unsigned = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if not isinstance(claimed_digest, str) or hash_canonical(unsigned) != claimed_digest:
        raise MatrixCompilationError("compiled plan SHA-256 mismatch")

    destination = Path(output_dir)
    if not destination.is_absolute():
        destination = (root / destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for cell in plan["cells"]:
        if cell["state"] == "REUSED":
            continue
        config = cell["resolved_config"]
        if hash_canonical(config) != cell["resolved_config_sha256"]:
            raise MatrixCompilationError(
                f"resolved config hash mismatch: {cell['cell_id']}"
            )
        path = destination / f"{cell['cell_id']}.json"
        if path.exists() and load_json_object(path) != config:
            raise MatrixCompilationError(f"refusing to overwrite changed config: {path}")
        atomic_write_json(path, config)
        files.append(
            {
                "cell_id": cell["cell_id"],
                "path": str(path.relative_to(root))
                if path.is_relative_to(root)
                else str(path),
                "config_sha256": cell["resolved_config_sha256"],
                "estimated_gpu_seconds": cell["estimated_gpu_seconds"],
                "state": cell["state"],
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "matrix_id": plan["matrix_id"],
        "plan_sha256": claimed_digest,
        "config_count": len(files),
        "configs": files,
    }
    manifest["manifest_sha256"] = hash_canonical(manifest)
    atomic_write_json(destination / "manifest.json", manifest)
    return manifest
