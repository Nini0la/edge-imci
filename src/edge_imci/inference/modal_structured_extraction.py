"""Run interactive inference against the completed Modal checkpoint."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal

from edge_imci.evaluation.holistic import evaluate_holistic_encounter
from edge_imci.evaluation.structured_extraction import parse_model_target_json
from edge_imci.experiments.provenance import atomic_write_json
from edge_imci.model_io import encounter as encounter_io
from edge_imci.training.modal_finetune import (
    OUTPUT_ROOT,
    ROOT,
    artifact_volume,
    training_image,
)
from edge_imci.training.structured_extraction import (
    STRUCTURED_EXTRACTION_SYSTEM_INSTRUCTION,
)


APP_NAME = "edge-imci-qwen3-0-6b-inference"
TRAINING_RUN_ID = "251039a3-4adc-4e74-8c30-069eb8aca6de"
MODEL_WEIGHTS_SHA256 = "86bb2507e5e7d04ad35c6c933923b902d21652bd04c401055a97a0d4485fd76a"
MODEL_DIR = OUTPUT_ROOT / TRAINING_RUN_ID / "merged"
RUN_MANIFEST = OUTPUT_ROOT / TRAINING_RUN_ID / "remote_run_manifest.json"
REMOTE_MODEL_SCHEMA_PATH = Path(
    "/workspace/configs/model_io/model_facing_encounter_v1.schema.json"
)
DEFAULT_DEMO_TEXT = (
    "The child is 18 months old and has had cough or difficult breathing for 3 "
    "days. The child was calm and I counted 52 breaths in one full minute. There "
    "is no chest indrawing, no stridor when calm, no wheezing, and no history of "
    "recurrent wheeze. A pulse oximeter is available and the oxygen saturation is "
    "96 percent. The child is not HIV exposed or infected. No bronchodilator trial "
    "was done. The child is able to drink or breastfeed, does not vomit everything, "
    "has had no convulsions, is not convulsing now, and is not lethargic or "
    "unconscious. The child does not have diarrhoea, fever, or an ear problem."
)
DEFAULT_OUTPUT_PATH = (
    ROOT
    / "experiments/inference/qwen3-0.6b-structured-extraction-sft-v1"
    / "first-novel-demo.json"
)
app = modal.App(APP_NAME)


def inference_messages(text: str) -> list[dict[str, str]]:
    if not text.strip():
        raise ValueError("inference text must not be blank")
    return [
        {"role": "system", "content": STRUCTURED_EXTRACTION_SYSTEM_INSTRUCTION},
        {"role": "user", "content": text.strip()},
    ]


@app.function(
    image=training_image,
    gpu="A10G",
    timeout=15 * 60,
    volumes={str(OUTPUT_ROOT): artifact_volume},
)
def infer(text: str, max_new_tokens: int = 1200) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not MODEL_DIR.is_dir() or not RUN_MANIFEST.is_file():
        raise FileNotFoundError(f"completed checkpoint is unavailable: {MODEL_DIR}")
    manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("run_id") != TRAINING_RUN_ID or manifest.get("status") != "SUCCEEDED":
        raise ValueError("training run manifest is not the expected successful run")
    recorded_weights = manifest.get("artifacts", {}).get("merged/model.safetensors", {})
    if recorded_weights.get("sha256") != MODEL_WEIGHTS_SHA256:
        raise ValueError("product checkpoint weights differ from the provisional designation")

    load_started = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR),
        local_files_only=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    ).to("cuda")
    model.eval()
    load_seconds = time.monotonic() - load_started

    messages = inference_messages(text)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to("cuda")
    generation_started = time.monotonic()
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    generation_seconds = time.monotonic() - generation_started
    generated_ids = output[0, inputs["input_ids"].shape[1] :]
    raw_response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

    parsed = None
    parse_error = None
    schema_error = None
    adapter_error = None
    schema_valid = False
    downstream = None
    try:
        parsed = parse_model_target_json(raw_response)
    except Exception as error:
        parse_error = f"{type(error).__name__}: {error}"
    if parsed is not None:
        # Modal's package mount can change __file__ depth. Pin the same schema
        # copied into the training image instead of relying on repository-root
        # discovery inside the remote container.
        encounter_io.MODEL_FACING_ENCOUNTER_SCHEMA_PATH = REMOTE_MODEL_SCHEMA_PATH
        try:
            encounter_io.validate_model_facing_encounter(parsed)
            schema_valid = True
        except Exception as error:
            schema_error = f"{type(error).__name__}: {error}"
    if schema_valid:
        try:
            encounter = encounter_io.model_target_to_holistic_encounter(
                parsed, encounter_id="interactive-modal-demo"
            )
            downstream = evaluate_holistic_encounter(encounter).to_dict()
        except Exception as error:
            adapter_error = f"{type(error).__name__}: {error}"

    return {
        "training_run_id": TRAINING_RUN_ID,
        "model_weights_sha256": MODEL_WEIGHTS_SHA256,
        "model_path": str(MODEL_DIR),
        "input_text": text,
        "raw_response": raw_response,
        "parsed_target": parsed,
        "schema_valid": schema_valid,
        "parse_error": parse_error,
        "schema_error": schema_error,
        "adapter_error": adapter_error,
        "downstream_evaluation": downstream,
        "runtime": {
            "gpu_name": torch.cuda.get_device_name(0),
            "load_seconds": load_seconds,
            "generation_seconds": generation_seconds,
            "input_tokens": inputs["input_ids"].shape[1],
            "output_tokens": generated_ids.shape[0],
            "output_tokens_per_second": generated_ids.shape[0] / generation_seconds,
        },
    }


@app.local_entrypoint()
def main(
    text: str = DEFAULT_DEMO_TEXT,
    output: str = str(DEFAULT_OUTPUT_PATH),
    max_new_tokens: int = 1200,
) -> None:
    result = infer.remote(text, max_new_tokens)
    receipt = {
        "receipt_id": "edge-imci-qwen3-0.6b-first-interactive-demo-v1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "test_partition_used": False,
        "production_clinical_use_authorized": False,
        "result": result,
    }
    destination = Path(output)
    if not destination.is_absolute():
        destination = ROOT / destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(destination, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"receipt={destination}")
