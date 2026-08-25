"""Modal runner for pinned Qwen3 structured-extraction LoRA lanes.

Local preflight only (no cloud resources):
    uv run --extra modal-training modal run -m edge_imci.training.modal_finetune --dry-run

Launch one pinned config after explicit authorization:
    uv run --extra modal-training modal run -m edge_imci.training.modal_finetune \
      --config-path configs/training/qwen3_0_6b_structured_extraction_lora_v1.json
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal

from edge_imci.experiments.tracking import RunTracker
from edge_imci.training.finetune import (
    DEFAULT_CONFIG_PATH,
    ROOT,
    load_json_object,
    preflight_training,
    training_tracking,
)

APP_NAME = "edge-imci-qwen3-0-6b-sft"
REMOTE_ROOT = Path("/workspace")
MODEL_CACHE_PATH = Path("/model-cache")
OUTPUT_ROOT = Path("/outputs")

app = modal.App(APP_NAME)

training_image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install(
        "accelerate==1.9.0",
        "datasets==3.6.0",
        "huggingface-hub==0.34.2",
        "jsonschema==4.25.0",
        "peft==0.16.0",
        "safetensors==0.5.3",
        "torch==2.7.1",
        "transformers==4.54.0",
    )
    .env(
        {
            "HF_HOME": str(MODEL_CACHE_PATH),
            "EDGE_IMCI_REPO_ROOT": str(REMOTE_ROOT),
            "HF_XET_HIGH_PERFORMANCE": "1",
            "PYTHONPATH": "/workspace/src",
            "TOKENIZERS_PARALLELISM": "true",
        }
    )
    .add_local_dir(str(ROOT / "src"), remote_path="/workspace/src")
    .add_local_dir(str(ROOT / "configs"), remote_path="/workspace/configs")
    .add_local_dir(
        str(ROOT / "experiments/registry/schemas"),
        remote_path="/workspace/experiments/registry/schemas",
    )
    .add_local_dir(
        str(ROOT / "data/training_sources/structured_extraction_campaign_v1"),
        remote_path=(
            "/workspace/data/training_sources/structured_extraction_campaign_v1"
        ),
    )
)

model_cache_volume = modal.Volume.from_name(
    "edge-imci-hf-cache", create_if_missing=True
)
artifact_volume = modal.Volume.from_name(
    "edge-imci-finetune-artifacts", create_if_missing=True
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _hash_tree(path: Path) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest = hashlib.sha256()
        size = 0
        with item.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        result[str(item.relative_to(path))] = {
            "sha256": digest.hexdigest(),
            "bytes": size,
        }
    return result


def _tokenize_records(tokenizer, rows: list[dict[str, Any]], max_length: int):
    from datasets import Dataset

    encoded: list[dict[str, list[int]]] = []
    lengths: list[int] = []
    for row in rows:
        messages = row["messages"]
        prompt = tokenizer.apply_chat_template(
            messages[:-1],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        # Qwen3's non-thinking inference prompt includes the canonical empty
        # reasoning block. Training on this exact prefix aligns SFT and runtime.
        full_text = prompt + messages[-1]["content"] + tokenizer.eos_token + "\n"
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        full = tokenizer(full_text, add_special_tokens=False)
        input_ids = full["input_ids"]
        if input_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError(f"chat prefix mismatch for {row['example_id']}")
        if len(input_ids) > max_length:
            raise ValueError(
                f"{row['example_id']} has {len(input_ids)} tokens; truncation is forbidden"
            )
        labels = [-100] * len(prompt_ids) + input_ids[len(prompt_ids) :]
        if not any(label != -100 for label in labels):
            raise ValueError(f"{row['example_id']} has no assistant loss tokens")
        encoded.append(
            {
                "input_ids": input_ids,
                "attention_mask": full["attention_mask"],
                "labels": labels,
            }
        )
        lengths.append(len(input_ids))
    ordered = sorted(lengths)
    return Dataset.from_list(encoded), {
        "count": len(lengths),
        "min": min(lengths),
        "median": ordered[len(ordered) // 2],
        "p95": ordered[max(0, int(len(ordered) * 0.95) - 1)],
        "max": max(lengths),
    }


def _generation_smoke(model, tokenizer, rows, config):
    import torch
    from jsonschema import Draft202012Validator

    schema = load_json_object(
        REMOTE_ROOT / "configs/model_io/model_facing_encounter_v1.schema.json"
    )
    validator = Draft202012Validator(schema)
    selected = rows[: config["example_count"]]
    receipts = []
    parsed_count = 0
    schema_valid_count = 0
    exact_count = 0
    model.eval()
    for row in selected:
        prompt = tokenizer.apply_chat_template(
            row["messages"][:-1],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(
            model.device
        )
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=config["max_new_tokens"],
                do_sample=config["do_sample"],
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
            )
        prediction = tokenizer.decode(
            output[0, inputs["input_ids"].shape[1] :], skip_special_tokens=True
        ).strip()
        target = json.loads(row["messages"][-1]["content"])
        parsed = None
        parse_error = None
        try:
            parsed = json.loads(prediction)
            parsed_count += 1
        except json.JSONDecodeError as error:
            parse_error = error.msg
        schema_valid = parsed is not None and not list(validator.iter_errors(parsed))
        exact = parsed is not None and _canonical_json(parsed) == _canonical_json(target)
        schema_valid_count += int(schema_valid)
        exact_count += int(exact)
        receipts.append(
            {
                "example_id": row["example_id"],
                "source_case_id": row["source_case_id"],
                "prediction": prediction,
                "parsed": parsed is not None,
                "schema_valid": schema_valid,
                "exact_match": exact,
                "parse_error": parse_error,
            }
        )
    denominator = len(selected)
    return {
        "example_count": denominator,
        "json_parse_count": parsed_count,
        "json_parse_rate": parsed_count / denominator,
        "schema_valid_count": schema_valid_count,
        "schema_valid_rate": schema_valid_count / denominator,
        "exact_match_count": exact_count,
        "exact_match_rate": exact_count / denominator,
        "receipts": receipts,
    }


def _generate_validation_predictions(model, tokenizer, rows, config):
    """Generate a complete evaluation partition in GPU-efficient batches."""
    import torch

    batch_size = config.get("batch_size", 8)
    original_padding_side = tokenizer.padding_side
    tokenizer.padding_side = "left"
    predictions = []
    started = time.monotonic()
    try:
        for offset in range(0, len(rows), batch_size):
            batch = rows[offset : offset + batch_size]
            prompts = [
                tokenizer.apply_chat_template(
                    row["messages"][:-1],
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
                for row in batch
            ]
            inputs = tokenizer(
                prompts,
                return_tensors="pt",
                add_special_tokens=False,
                padding=True,
            ).to(model.device)
            batch_started = time.monotonic()
            with torch.inference_mode():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=config["max_new_tokens"],
                    do_sample=config["do_sample"],
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id,
                )
            batch_seconds = time.monotonic() - batch_started
            prompt_width = inputs["input_ids"].shape[1]
            for row, output in zip(batch, outputs, strict=True):
                prediction = tokenizer.decode(
                    output[prompt_width:], skip_special_tokens=True
                ).strip()
                predictions.append(
                    {
                        "example_id": row["example_id"],
                        "prediction": prediction,
                        "latency_seconds": batch_seconds / len(batch),
                    }
                )
    finally:
        tokenizer.padding_side = original_padding_side
    return predictions, {
        "example_count": len(predictions),
        "batch_size": batch_size,
        "duration_seconds": time.monotonic() - started,
    }


@app.function(
    image=training_image,
    gpu="A10G",
    timeout=4 * 60 * 60,
    volumes={
        str(MODEL_CACHE_PATH): model_cache_volume,
        str(OUTPUT_ROOT): artifact_volume,
    },
)
def train(
    run_id: str, code_provenance: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    import importlib.metadata

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    from edge_imci.evaluation.checkpoint import (
        evaluate_checkpoint_predictions,
        load_checkpoint_evaluation_policy,
    )
    from edge_imci.model_io import encounter as encounter_io

    started = time.monotonic()
    started_at = _utc_now()
    remote_evaluation_policy_path = (
        REMOTE_ROOT
        / "configs/evaluation/structured_extraction_checkpoint_policy_v1.json"
    )
    load_checkpoint_evaluation_policy(
        remote_evaluation_policy_path,
        repo_root=REMOTE_ROOT,
    )
    remote_model_schema_path = (
        REMOTE_ROOT / "configs/model_io/model_facing_encounter_v1.schema.json"
    )
    if not remote_model_schema_path.is_file():
        raise FileNotFoundError(
            f"remote model-facing schema is missing: {remote_model_schema_path}"
        )
    encounter_io.MODEL_FACING_ENCOUNTER_SCHEMA_PATH = remote_model_schema_path
    remote_config_path = Path("/tmp") / f"edgeimci-training-{run_id}.json"
    remote_config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    preflight, rows = preflight_training(
        remote_config_path, repo_root=REMOTE_ROOT
    )
    training_tracking(config)
    if config["modal"]["gpu_type"] != "A10G":
        raise ValueError("Modal GPU decorator and pinned config disagree")
    expected_modal = {
        "app_name": APP_NAME,
        "function_name": "train",
        "model_cache_volume": "edge-imci-hf-cache",
        "artifact_volume": "edge-imci-finetune-artifacts",
        "artifact_root": str(OUTPUT_ROOT),
    }
    for key, expected in expected_modal.items():
        if config["modal"].get(key) != expected:
            raise ValueError(f"Modal decorator/resource mismatch: {key}")
    distribution_names = {
        "torch": "torch",
        "transformers": "transformers",
        "datasets": "datasets",
        "accelerate": "accelerate",
        "peft": "peft",
        "huggingface_hub": "huggingface-hub",
    }
    for config_name, distribution_name in distribution_names.items():
        actual = importlib.metadata.version(distribution_name)
        expected = config["software"][config_name]
        if actual != expected:
            raise ValueError(
                f"pinned software mismatch for {distribution_name}: {actual} != {expected}"
            )
    set_seed(config["optimization"]["seed"])
    base = config["base_model"]
    tokenizer = AutoTokenizer.from_pretrained(
        base["model_id"], revision=base["tokenizer_revision"], use_fast=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    max_length = config["tokenization"]["max_sequence_length"]
    train_dataset, train_lengths = _tokenize_records(
        tokenizer, rows["TRAIN"], max_length
    )
    validation_dataset, validation_lengths = _tokenize_records(
        tokenizer, rows["VALIDATION"], max_length
    )
    if max(train_lengths["max"], validation_lengths["max"]) > max_length:
        raise ValueError("sequence length preflight failed")

    model = AutoModelForCausalLM.from_pretrained(
        base["model_id"],
        revision=base["revision"],
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    model.config.use_cache = False
    method = config["method"]
    model = get_peft_model(
        model,
        LoraConfig(
            r=method["rank"],
            lora_alpha=method["alpha"],
            lora_dropout=method["dropout"],
            bias=method["bias"],
            target_modules=method["target_modules"],
            task_type="CAUSAL_LM",
        ),
    )
    trainable, total = model.get_nb_trainable_parameters()
    output_dir = OUTPUT_ROOT / run_id
    checkpoint_dir = output_dir / "checkpoints"
    adapter_dir = output_dir / "adapter"
    merged_dir = output_dir / "merged"
    output_dir.mkdir(parents=True, exist_ok=False)
    optimization = config["optimization"]
    arguments = TrainingArguments(
        output_dir=str(checkpoint_dir),
        num_train_epochs=optimization["epochs"],
        learning_rate=optimization["learning_rate"],
        weight_decay=optimization["weight_decay"],
        warmup_ratio=optimization["warmup_ratio"],
        per_device_train_batch_size=optimization["per_device_train_batch_size"],
        per_device_eval_batch_size=optimization["per_device_eval_batch_size"],
        gradient_accumulation_steps=optimization["gradient_accumulation_steps"],
        gradient_checkpointing=optimization["gradient_checkpointing"],
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_grad_norm=optimization["max_grad_norm"],
        optim=optimization["optimizer"],
        lr_scheduler_type=optimization["lr_scheduler_type"],
        bf16=optimization["bf16"],
        tf32=optimization["tf32"],
        seed=optimization["seed"],
        data_seed=optimization["seed"],
        logging_steps=optimization["logging_steps"],
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=optimization["save_total_limit"],
        report_to="none",
        remove_unused_columns=False,
        dataloader_num_workers=2,
        dataloader_pin_memory=True,
        save_safetensors=True,
    )
    collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=None,
        label_pad_token_id=-100,
        pad_to_multiple_of=8,
    )
    trainer = Trainer(
        model=model,
        args=arguments,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        data_collator=collator,
    )
    model.print_trainable_parameters()
    train_result = trainer.train()
    evaluation = trainer.evaluate()
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    merged = trainer.model.merge_and_unload()
    merged.config.use_cache = True
    smoke = _generation_smoke(
        merged, tokenizer, rows["VALIDATION"], config["validation_generation"]
    )
    validation_predictions, validation_inference = _generate_validation_predictions(
        merged,
        tokenizer,
        rows["VALIDATION"],
        config["validation_generation"],
    )
    predictions_path = output_dir / "validation_predictions.jsonl"
    predictions_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in validation_predictions
        ),
        encoding="utf-8",
    )
    checkpoint_evaluation = evaluate_checkpoint_predictions(
        predictions_path,
        candidate_id=run_id,
        policy_path=remote_evaluation_policy_path,
        repo_root=REMOTE_ROOT,
    )
    (output_dir / "validation_evaluation.json").write_text(
        json.dumps(
            checkpoint_evaluation,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    merged.save_pretrained(
        str(merged_dir), safe_serialization=True, max_shard_size="4GB"
    )
    tokenizer.save_pretrained(str(merged_dir))
    log_history = json.loads(json.dumps(trainer.state.log_history, default=float))
    metrics = {
        "train": json.loads(json.dumps(train_result.metrics, default=float)),
        "evaluation": json.loads(json.dumps(evaluation, default=float)),
        "validation_generation": smoke,
        "validation_inference": validation_inference,
        "checkpoint_evaluation": {
            "aggregate": checkpoint_evaluation["aggregate"],
            "slices": checkpoint_evaluation["slices"],
            "promotion": checkpoint_evaluation["promotion"],
            "report_sha256": checkpoint_evaluation["report_sha256"],
        },
        "trainable_parameters": trainable,
        "total_parameters": total,
        "trainable_parameter_fraction": trainable / total,
        "train_token_lengths": train_lengths,
        "validation_token_lengths": validation_lengths,
        "peak_gpu_memory_bytes": torch.cuda.max_memory_allocated(),
        "gpu_name": torch.cuda.get_device_name(0),
        "log_history": log_history,
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts = _hash_tree(output_dir)
    finished_at = _utc_now()
    duration = time.monotonic() - started
    remote_manifest = {
        "run_id": run_id,
        "status": "SUCCEEDED",
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration,
        "code_provenance": code_provenance,
        "preflight": preflight,
        "model": base,
        "method": method,
        "artifacts": artifacts,
        "test_partition_used": False,
        "production_clinical_use_authorized": False,
    }
    (output_dir / "remote_run_manifest.json").write_text(
        json.dumps(remote_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact_volume.commit()
    return {
        "run_id": run_id,
        "status": "SUCCEEDED",
        "output_volume": config["modal"]["artifact_volume"],
        "output_path": str(output_dir),
        "duration_seconds": duration,
        "gpu_name": metrics["gpu_name"],
        "peak_gpu_memory_bytes": metrics["peak_gpu_memory_bytes"],
        "train_metrics": metrics["train"],
        "evaluation_metrics": metrics["evaluation"],
        "validation_generation": {
            key: value for key, value in smoke.items() if key != "receipts"
        },
        "validation_inference": validation_inference,
        "checkpoint_evaluation": {
            "aggregate": checkpoint_evaluation["aggregate"],
            "slices": checkpoint_evaluation["slices"],
            "promotion": checkpoint_evaluation["promotion"],
            "report_sha256": checkpoint_evaluation["report_sha256"],
        },
        "artifact_count": len(artifacts) + 1,
        "artifact_bytes": sum(item["bytes"] for item in artifacts.values()),
    }


def _safe_run_name(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}", value):
        raise ValueError("run_name must contain only letters, digits, dot, underscore, or dash")
    return value


def _local_config_path(value: str) -> Path:
    raw = Path(value)
    resolved = raw.resolve() if raw.is_absolute() else (ROOT / raw).resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise ValueError("config_path must remain inside the repository")
    if not resolved.is_file():
        raise ValueError(f"config_path does not exist: {value}")
    return resolved


@app.local_entrypoint()
def main(run_name: str = "", config_path: str = "", dry_run: bool = False) -> None:
    selected_config_path = _local_config_path(
        config_path or str(DEFAULT_CONFIG_PATH.relative_to(ROOT))
    )
    preflight, _ = preflight_training(selected_config_path)
    if dry_run:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return

    config = load_json_object(selected_config_path)
    tracking = training_tracking(config)
    label = _safe_run_name(
        run_name
        or datetime.now(timezone.utc).strftime(
            f"{tracking['run_name_prefix']}-%Y%m%dT%H%M%SZ"
        )
    )
    experiment_id = tracking["experiment_id"]
    output_dir = ROOT / "experiments/training" / experiment_id / label
    modal_config = config["modal"]
    tracker = RunTracker()
    handle = tracker.start(
        experiment_id=experiment_id,
        output_dir=output_dir,
        config={
            "config_id": config["config_id"],
            "version": config["version"],
            "source_path": str(selected_config_path.relative_to(ROOT)),
            "data": config,
        },
        execution={
            "environment_kind": "MODAL",
            "execution_provider": "Modal",
            "modal": {
                "app_id": modal_config["app_name"],
                "function_name": modal_config["function_name"],
                "region": modal_config["region"],
                "gpu_type": modal_config["gpu_type"],
                "gpu_count": modal_config["gpu_count"],
                "image_identity": tracking["image_identity"],
            },
        },
        models=[
            {
                "role": "BASE",
                "model_provider": "Qwen",
                "model_source": "Hugging Face Hub",
                "model_id": config["base_model"]["model_id"],
                "revision": config["base_model"]["revision"],
                "tokenizer_revision": config["base_model"]["tokenizer_revision"],
                "representation": "BF16_SAFETENSORS",
                "precision": "BF16",
                "remote_only": True,
            }
        ],
        datasets=[
            {
                "dataset_id": "edge-imci-structured-extraction-language-campaign-v1",
                "version": "1.0.0",
                "manifest_path": config["dataset"]["manifest_path"],
                "sha256": preflight["dataset_manifest_sha256"],
                "split": "TRAIN+VALIDATION; TEST PROHIBITED",
                "record_count": (
                    preflight["trainable_record_count"]
                    + preflight["validation_record_count"]
                ),
            }
        ],
        command=[
            "modal",
            "run",
            "-m",
            "edge_imci.training.modal_finetune",
            "--run-name",
            label,
            "--config-path",
            str(selected_config_path.relative_to(ROOT)),
        ],
    )
    with handle:
        result = train.remote(
            handle.run_id,
            handle.record["provenance"]["git"],
            config,
        )
        handle.record_scientific_metrics(
            {
                "train_metrics": result["train_metrics"],
                "evaluation_metrics": result["evaluation_metrics"],
                "validation_generation": result["validation_generation"],
                "validation_inference": result["validation_inference"],
                "checkpoint_evaluation": result["checkpoint_evaluation"],
                "remote_artifact_location": {
                    "volume": result["output_volume"],
                    "path": result["output_path"],
                    "artifact_count": result["artifact_count"],
                    "artifact_bytes": result["artifact_bytes"],
                },
            }
        )
        handle.record_validation(
            {
                "validator_id": "edge-imci-finetune-input-preflight-v1",
                "version": "1.0.0",
                "status": "PASSED",
                "pass_count": sum(preflight["partition_counts"].values()),
                "fail_count": 0,
                "error_codes": {},
            }
        )
        handle.record_telemetry(
            {
                "gpu_seconds": result["duration_seconds"],
                "job_duration_seconds": result["duration_seconds"],
                "task_status": result["status"],
                "provider_usage": {
                    "gpu_name": result["gpu_name"],
                    "peak_gpu_memory_bytes": result["peak_gpu_memory_bytes"],
                },
            }
        )
        handle.record_usage(
            usage_id=f"{handle.run_id}-modal-training",
            source="Modal training function",
            metrics={
                "gpu_seconds": result["duration_seconds"],
                "train_examples": preflight["trainable_record_count"],
                "validation_examples": preflight["validation_record_count"],
            },
            raw_payload=result,
        )
    result["local_sidecar"] = str(handle.sidecar_path.relative_to(ROOT))
    print(json.dumps(result, indent=2, sort_keys=True))
