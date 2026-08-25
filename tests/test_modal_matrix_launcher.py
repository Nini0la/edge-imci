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
