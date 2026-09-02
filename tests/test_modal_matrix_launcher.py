from __future__ import annotations

import json
from pathlib import Path

import pytest

from edge_imci.experiments.modal_matrix import (
    ModalMatrixError,
    command_for_cell,
    load_authorized_schedule,
)

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "experiments/training/matrices/qwen3-0.6b-sft-calibration-v1.plan.json"
MANIFEST = (
    ROOT
    / "experiments/training/matrices/qwen3-0.6b-sft-calibration-v1/configs/manifest.json"
)
QWEN_1_7B_PLAN = (
    ROOT / "experiments/training/matrices/qwen3-1.7b-sft-initial-matrix-v1.plan.json"
)
QWEN_1_7B_MANIFEST = (
    ROOT
    / "experiments/training/matrices/qwen3-1.7b-sft-initial-matrix-v1/configs/manifest.json"
)
QWEN_1_7B_V2_PLAN = (
    ROOT / "experiments/training/matrices/qwen3-1.7b-seven-style-sft-matrix-v2.plan.json"
)
QWEN_1_7B_V2_MANIFEST = (
    ROOT
    / "experiments/training/matrices/qwen3-1.7b-seven-style-sft-matrix-v2/configs/manifest.json"
)


def test_authorized_schedule_binds_every_ready_config() -> None:
    plan, cells = load_authorized_schedule(PLAN, MANIFEST)
    assert plan["controls"]["launch_authorized"] is True
    assert len(cells) == 23
    assert all(cell["state"] == "READY" for cell in cells)
    command = command_for_cell(cells[0])
    assert command[:4] == [
        "modal",
        "run",
        "-m",
        "edge_imci.training.modal_finetune",
    ]
    assert command[command.index("--run-name") + 1] == cells[0]["cell_id"]
    assert command[command.index("--config-path") + 1].endswith(".json")


def test_schedule_rejects_tampered_manifest(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["plan_sha256"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ModalMatrixError, match="manifest and plan"):
        load_authorized_schedule(PLAN, path)


def test_qwen3_1_7b_schedule_binds_all_eight_cells_to_its_experiment() -> None:
    plan, cells = load_authorized_schedule(QWEN_1_7B_PLAN, QWEN_1_7B_MANIFEST)

    assert plan["registry"]["experiment_id"] == (
        "qwen3-1.7b-structured-extraction-sft-v1-modal"
    )
    assert len(cells) == 8
    assert plan["execution"]["max_parallel_runs"] == 4
    assert all(cell["state"] == "READY" for cell in cells)
    assert all(command_for_cell(cell)[0:4] == [
        "modal",
        "run",
        "-m",
        "edge_imci.training.modal_finetune",
    ] for cell in cells)


def test_qwen3_1_7b_seven_style_matrix_binds_all_authorized_cells() -> None:
    plan = json.loads(QWEN_1_7B_V2_PLAN.read_text(encoding="utf-8"))
    manifest = json.loads(QWEN_1_7B_V2_MANIFEST.read_text(encoding="utf-8"))
    verified_plan, cells = load_authorized_schedule(
        QWEN_1_7B_V2_PLAN, QWEN_1_7B_V2_MANIFEST
    )

    assert plan["summary"]["cell_count"] == 24
    assert plan["summary"]["ready_run_count"] == 24
    assert plan["controls"]["launch_authorized"] is True
    assert manifest["config_count"] == 24
    assert verified_plan["matrix_id"] == plan["matrix_id"]
    assert len(cells) == 24
