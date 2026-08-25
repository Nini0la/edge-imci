"""Inference-only matched evaluation for an existing Modal training checkpoint."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal

from edge_imci.experiments.provenance import atomic_write_json
from edge_imci.training.modal_finetune import (
    OUTPUT_ROOT,
    REMOTE_ROOT,
    ROOT,
    _generate_validation_predictions,
    artifact_volume,
    training_image,
)

APP_NAME = "edge-imci-qwen3-0-6b-checkpoint-evaluation"
app = modal.App(APP_NAME)


def _safe_identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", value):
        raise ValueError(f"invalid {label}")
    return value


@app.function(
    image=training_image,
    gpu="A10G",
    timeout=30 * 60,
    volumes={str(OUTPUT_ROOT): artifact_volume},
)
def evaluate_existing_checkpoint(
    training_run_id: str, cell_id: str
) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from edge_imci.evaluation.checkpoint import (
        evaluate_checkpoint_predictions,
        load_checkpoint_evaluation_policy,
    )
    from edge_imci.model_io import encounter as encounter_io
    from edge_imci.training.finetune import load_json_object, preflight_training

    started = time.monotonic()
    training_run_id = _safe_identifier(training_run_id, "training_run_id")
    cell_id = _safe_identifier(cell_id, "cell_id")
    source_dir = OUTPUT_ROOT / training_run_id
    model_dir = source_dir / "merged"
    config_path = source_dir / "config.json"
    manifest_path = source_dir / "remote_run_manifest.json"
    if not model_dir.is_dir() or not config_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError(f"existing checkpoint evidence is incomplete: {source_dir}")
    manifest = load_json_object(manifest_path)
    if manifest.get("run_id") != training_run_id or manifest.get("status") != "SUCCEEDED":
        raise ValueError("source training run is not a successful immutable checkpoint")

    policy_path = (
        REMOTE_ROOT
        / "configs/evaluation/structured_extraction_checkpoint_policy_v1.json"
    )
    load_checkpoint_evaluation_policy(policy_path, repo_root=REMOTE_ROOT)
    model_schema_path = (
        REMOTE_ROOT / "configs/model_io/model_facing_encounter_v1.schema.json"
    )
    if not model_schema_path.is_file():
        raise FileNotFoundError(f"model-facing schema is missing: {model_schema_path}")
    encounter_io.MODEL_FACING_ENCOUNTER_SCHEMA_PATH = model_schema_path

    config = load_json_object(config_path)
    _, rows = preflight_training(config_path, repo_root=REMOTE_ROOT)
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        local_files_only=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    ).to("cuda")
    model.eval()

    predictions, inference = _generate_validation_predictions(
        model,
        tokenizer,
        rows["VALIDATION"],
        config["validation_generation"],
    )
    output_dir = OUTPUT_ROOT / "matrix-evaluations" / cell_id
    output_dir.mkdir(parents=True, exist_ok=False)
    predictions_path = output_dir / "validation_predictions.jsonl"
    predictions_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in predictions
        ),
        encoding="utf-8",
    )
    report = evaluate_checkpoint_predictions(
        predictions_path,
        candidate_id=cell_id,
        policy_path=policy_path,
        repo_root=REMOTE_ROOT,
    )
    (output_dir / "validation_evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = {
        "cell_id": cell_id,
        "source_training_run_id": training_run_id,
        "status": "SUCCEEDED",
        "test_partition_used": False,
        "duration_seconds": time.monotonic() - started,
        "gpu_name": torch.cuda.get_device_name(0),
        "validation_inference": inference,
        "aggregate": report["aggregate"],
        "promotion": report["promotion"],
        "report_sha256": report["report_sha256"],
        "remote_artifact_path": str(output_dir),
    }
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact_volume.commit()
    return receipt


@app.local_entrypoint()
def main(training_run_id: str, cell_id: str, output: str) -> None:
    result = evaluate_existing_checkpoint.remote(training_run_id, cell_id)
    receipt = {
        "receipt_id": f"{cell_id}-matched-validation-v1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "operating_mode": "AUTOMATIC_EVIDENCE",
        "routine_example_review": False,
        "result": result,
    }
    destination = Path(output)
    if not destination.is_absolute():
        destination = ROOT / destination
    atomic_write_json(destination, receipt)
    print(
        json.dumps(
            {
                "cell_id": result["cell_id"],
                "status": result["status"],
                "duration_seconds": result["duration_seconds"],
                "promotion_eligible": result["promotion"]["eligible"],
                "aggregate": result["aggregate"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"receipt={destination}")
