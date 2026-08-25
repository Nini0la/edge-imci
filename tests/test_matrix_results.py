from __future__ import annotations

from pathlib import Path

from edge_imci.experiments.matrix_results import build_matrix_leaderboard

ROOT = Path(__file__).resolve().parents[1]
MATRIX_DIR = ROOT / "experiments/training/matrices/qwen3-0.6b-sft-calibration-v1"


def test_completed_matrix_has_a_deterministic_safety_first_winner() -> None:
    leaderboard = build_matrix_leaderboard(
        MATRIX_DIR.parent / "qwen3-0.6b-sft-calibration-v1.plan.json",
        MATRIX_DIR / "execution/state.json",
        MATRIX_DIR / "execution/reused-baseline-evaluation.json",
        ROOT / "configs/evaluation/structured_extraction_checkpoint_policy_v1.json",
    )
    assert leaderboard["cell_count"] == 24
    assert leaderboard["eligible_count"] == 8
    assert leaderboard["winner_cell_id"] == "qwen3-0.6b-sft-calibration-v1--016--dde3f482d8"
    winner = leaderboard["rows"][0]
    assert winner["promotion_eligible"] is True
    assert set(winner["metrics"].values()) == {1.0}
    assert winner["axis_values"] == {
        "optimization.epochs": 3.0,
        "optimization.learning_rate": 0.0002,
        "optimization.seed": 20260824,
    }
