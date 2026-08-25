from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from edge_imci.experiments.matrix import (
    MatrixCompilationError,
    compile_experiment_matrix,
    materialize_matrix_configs,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "configs/training/qwen3_0_6b_sft_calibration_matrix_v1.json"
QWEN_1_7B_SPEC_PATH = (
    ROOT / "configs/training/qwen3_1_7b_sft_initial_matrix_v1.json"
)
PLAN_PATH = (
    ROOT
    / "experiments/training/matrices/qwen3-0.6b-sft-calibration-v1.plan.json"
)


def _write_spec(tmp_path: Path, mutate=None) -> Path:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if mutate:
        mutate(spec)
    path = tmp_path / "matrix.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def test_first_calibration_matrix_is_deterministic_and_budgeted() -> None:
    first = compile_experiment_matrix(SPEC_PATH)
    second = compile_experiment_matrix(SPEC_PATH)

    assert first == second
    assert first["summary"] == {
        "cell_count": 24,
        "new_run_count": 23,
        "reused_run_count": 1,
        "ready_run_count": 23,
        "blocked_run_count": 0,
        "estimated_gpu_seconds": 18509.305,
        "estimated_gpu_hours": 5.141,
        "max_parallel_runs": 4,
        "minimum_execution_waves": 6,
    }
    assert len({cell["cell_id"] for cell in first["cells"]}) == 24
    reused = [cell for cell in first["cells"] if cell["state"] == "REUSED"]
    assert reused[0]["reused_run_id"] == "4b9c196e-d3f7-4e45-a591-f8bf32932a9b"
    assert reused[0]["estimated_gpu_seconds"] == 0.0
    ready = [cell for cell in first["cells"] if cell["state"] == "READY"]
    assert len(ready) == 23
    assert all(not cell["blocked_reasons"] for cell in ready)


def test_matrix_rejects_unknown_override_path(tmp_path: Path) -> None:
    def mutate(spec):
        spec["axes"]["optimization.typo"] = spec["axes"].pop(
            "optimization.epochs"
        )
        spec["reused_cells"][0]["axis_values"]["optimization.typo"] = spec[
            "reused_cells"
        ][0]["axis_values"].pop("optimization.epochs")

    path = _write_spec(tmp_path, mutate)
    with pytest.raises(MatrixCompilationError, match="does not exist"):
        compile_experiment_matrix(path)


def test_matrix_fails_closed_above_budget(tmp_path: Path) -> None:
    path = _write_spec(
        tmp_path,
        lambda spec: spec["budget"].update({"max_estimated_gpu_seconds": 1}),
    )
    with pytest.raises(MatrixCompilationError, match="exceed budget"):
        compile_experiment_matrix(path)


def test_reused_run_must_be_linked_from_registry(tmp_path: Path) -> None:
    def mutate(spec):
        reused = deepcopy(spec["reused_cells"][0])
        reused["run_id"] = "unregistered-run"
        spec["reused_cells"] = [reused]

    path = _write_spec(tmp_path, mutate)
    with pytest.raises(MatrixCompilationError, match="not linked"):
        compile_experiment_matrix(path)


def test_materialization_verifies_plan_and_writes_only_new_cells(
    tmp_path: Path,
) -> None:
    manifest = materialize_matrix_configs(PLAN_PATH, tmp_path / "configs")
    assert manifest["config_count"] == 23
    assert len(manifest["configs"]) == 23
    for item in manifest["configs"]:
        path = Path(item["path"])
        assert path.is_file()
        assert item["config_sha256"]


def test_materialization_rejects_tampered_plan(tmp_path: Path) -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    plan["cells"][0]["estimated_gpu_seconds"] += 1
    path = tmp_path / "tampered-plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(MatrixCompilationError, match="plan SHA-256 mismatch"):
        materialize_matrix_configs(path, tmp_path / "configs")


def test_qwen3_1_7b_initial_matrix_has_exact_authorized_axes() -> None:
    plan = compile_experiment_matrix(QWEN_1_7B_SPEC_PATH)

    assert plan["summary"]["cell_count"] == 8
    assert plan["summary"]["ready_run_count"] == 8
    assert plan["summary"]["max_parallel_runs"] == 4
    assert plan["summary"]["minimum_execution_waves"] == 2
    assert plan["summary"]["estimated_gpu_seconds"] <= 24000
    assert {
        (
            cell["axis_values"]["optimization.epochs"],
            cell["axis_values"]["optimization.learning_rate"],
            cell["axis_values"]["optimization.seed"],
        )
        for cell in plan["cells"]
    } == {
        (epoch, learning_rate, 3407)
        for epoch in (1.0, 2.0, 3.0, 5.0)
        for learning_rate in (0.0001, 0.0002)
    }
    assert all(
        cell["resolved_config"]["dataset"]["test_partition"] == "TEST"
        and cell["resolved_config"]["tokenization"]["assistant_only_loss"] is True
        for cell in plan["cells"]
    )
