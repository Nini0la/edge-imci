"""One-shot Modal inference for aggregate-only reserved-TEST evidence."""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal

from edge_imci.experiments.provenance import atomic_write_json, hash_canonical, hash_file
from edge_imci.training.modal_finetune import (
    MODEL_CACHE_PATH,
    OUTPUT_ROOT,
    REMOTE_ROOT,
    ROOT,
    _generate_validation_predictions,
    artifact_volume,
    model_cache_volume,
    training_image,
)

APP_NAME = "edge-imci-qwen3-0-6b-one-shot-test"
POLICY_RELATIVE_PATH = Path("configs/evaluation/qwen3_0_6b_one_shot_test_v1.json")
RECOVERY_RELATIVE_PATH = Path(
    "configs/evaluation/qwen3_0_6b_one_shot_test_recovery_v1.json"
)
FINALIZATION_RECOVERY_RELATIVE_PATH = Path(
    "configs/evaluation/qwen3_0_6b_one_shot_test_finalization_recovery_v2.json"
)
PRIVATE_ROOT = Path("/private-test-evidence")
DEFAULT_LOCAL_REPORT = Path(
    "experiments/evaluation/qwen3-0.6b-one-shot-test-v1/aggregate_report.json"
)
DEFAULT_LOCAL_RECOVERY_REPORT = Path(
    "experiments/evaluation/qwen3-0.6b-one-shot-test-v1/aggregate_report_recovery_v1.json"
)
DEFAULT_LOCAL_FINAL_REPORT = Path(
    "experiments/evaluation/qwen3-0.6b-one-shot-test-v1/aggregate_report_final_v1.json"
)
DEFAULT_LOCAL_FINAL_REPORT_V2 = Path(
    "experiments/evaluation/qwen3-0.6b-one-shot-test-v1/aggregate_report_final_v2.json"
)

app = modal.App(APP_NAME)
private_test_volume = modal.Volume.from_name(
    "edge-imci-private-test-evidence", create_if_missing=True
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", value):
        raise ValueError(f"invalid {label}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_remote_policy() -> tuple[Path, dict[str, Any], str]:
    from edge_imci.evaluation.one_shot_test import load_one_shot_test_policy

    path = REMOTE_ROOT / POLICY_RELATIVE_PATH
    policy_file, policy = load_one_shot_test_policy(path, repo_root=REMOTE_ROOT)
    return policy_file, policy, hash_file(policy_file)[0]


def _load_remote_recovery() -> tuple[Path, dict[str, Any], str]:
    from edge_imci.evaluation.one_shot_test import load_one_shot_test_recovery

    path = REMOTE_ROOT / RECOVERY_RELATIVE_PATH
    recovery_file, recovery = load_one_shot_test_recovery(path, repo_root=REMOTE_ROOT)
    return recovery_file, recovery, hash_file(recovery_file)[0]


def _load_remote_finalization_recovery() -> tuple[Path, dict[str, Any], str]:
    from edge_imci.evaluation.one_shot_test import (
        load_one_shot_test_finalization_recovery,
    )

    path = REMOTE_ROOT / FINALIZATION_RECOVERY_RELATIVE_PATH
    recovery_file, recovery = load_one_shot_test_finalization_recovery(
        path, repo_root=REMOTE_ROOT
    )
    return recovery_file, recovery, hash_file(recovery_file)[0]


def _state_path(authorization_id: str) -> Path:
    return PRIVATE_ROOT / authorization_id / "state.json"


def _load_state(authorization_id: str) -> dict[str, Any]:
    path = _state_path(authorization_id)
    if not path.is_file():
        raise RuntimeError("one-shot TEST state does not exist")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("one-shot TEST state is invalid")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _require_running_state(
    authorization_id: str, policy_sha256: str
) -> dict[str, Any]:
    state = _load_state(authorization_id)
    if state.get("status") not in {
        "RUNNING",
        "RECOVERY_RUNNING",
        "FINALIZATION_RUNNING",
    }:
        raise RuntimeError("one-shot TEST is not in an executable state")
    if state.get("policy_sha256") != policy_sha256:
        raise RuntimeError("one-shot TEST policy hash changed after authorization")
    if state.get("attempt_count") != 1:
        raise RuntimeError("one-shot TEST attempt count is not exactly one")
    if state["status"] == "RECOVERY_RUNNING" and state.get("recovery_count") != 1:
        raise RuntimeError("TEST recovery count is not exactly one")
    finalization_count = state.get("finalization_recovery_count")
    if state["status"] == "FINALIZATION_RUNNING" and (
        not isinstance(finalization_count, int) or finalization_count < 1
    ):
        raise RuntimeError("TEST finalization recovery count is invalid")
    return state


@app.function(
    image=training_image,
    timeout=5 * 60,
    volumes={str(PRIVATE_ROOT): private_test_volume},
)
def begin_one_shot_test(expected_policy_sha256: str) -> dict[str, Any]:
    """Consume the sole authorization before any TEST inference starts."""

    private_test_volume.reload()
    _, policy, actual_policy_sha256 = _load_remote_policy()
    if actual_policy_sha256 != expected_policy_sha256:
        raise RuntimeError("local and Modal TEST policy hashes differ")
    authorization_id = _safe_identifier(policy["authorization_id"], "authorization_id")
    PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
    run_root = PRIVATE_ROOT / authorization_id
    if run_root.exists():
        raise RuntimeError("one-shot TEST authorization has already been consumed")
    run_root.mkdir()
    (run_root / "predictions").mkdir()
    (run_root / "candidate_receipts").mkdir()
    state = {
        "schema_version": "1.0.0",
        "authorization_id": authorization_id,
        "evaluation_id": policy["evaluation_id"],
        "status": "RUNNING",
        "attempt_count": 1,
        "started_at": _utc_now(),
        "policy_sha256": actual_policy_sha256,
        "expected_candidate_ids": [
            candidate["candidate_id"] for candidate in policy["candidates"]
        ],
        "completed_candidate_ids": [],
        "aggregate_only": True,
        "routine_record_review_performed": False,
    }
    _write_json(_state_path(authorization_id), state)
    private_test_volume.commit()
    return {
        "authorization_id": authorization_id,
        "status": state["status"],
        "attempt_count": 1,
        "policy_sha256": actual_policy_sha256,
    }


@app.function(
    image=training_image,
    timeout=5 * 60,
    volumes={str(PRIVATE_ROOT): private_test_volume},
)
def begin_one_shot_recovery(
    expected_policy_sha256: str, expected_recovery_sha256: str
) -> dict[str, Any]:
    """Authorize one infrastructure-only continuation without rerunning evidence."""

    private_test_volume.reload()
    _, policy, policy_sha256 = _load_remote_policy()
    _, recovery, recovery_sha256 = _load_remote_recovery()
    if policy_sha256 != expected_policy_sha256:
        raise RuntimeError("local and Modal TEST policy hashes differ")
    if recovery_sha256 != expected_recovery_sha256:
        raise RuntimeError("local and Modal TEST recovery hashes differ")
    if recovery["original_policy_sha256"] != policy_sha256:
        raise RuntimeError("TEST recovery references a different policy")
    if recovery["runner_sha256"] != _sha256(Path(__file__)):
        raise RuntimeError("TEST recovery runner SHA-256 mismatch")

    authorization_id = _safe_identifier(
        recovery["original_authorization_id"], "authorization_id"
    )
    recovery_id = _safe_identifier(recovery["recovery_id"], "recovery_id")
    state_path = _state_path(authorization_id)
    if _sha256(state_path) != recovery["failed_closed_state_sha256"]:
        raise RuntimeError("failed-closed TEST state differs from recovery authorization")
    state = _load_state(authorization_id)
    if state.get("status") != "FAILED_CLOSED":
        raise RuntimeError("TEST recovery requires FAILED_CLOSED state")
    if state.get("attempt_count") != 1 or state.get("recovery_count"):
        raise RuntimeError("TEST recovery has already been consumed")
    if state.get("policy_sha256") != policy_sha256:
        raise RuntimeError("failed TEST state references a different policy")

    preserved = {
        item["candidate_id"]: item for item in recovery["preserved_candidates"]
    }
    completed = set(state.get("completed_candidate_ids", []))
    if completed != set(preserved):
        raise RuntimeError("preserved candidates differ from completed TEST state")
    expected = {candidate["candidate_id"] for candidate in policy["candidates"]}
    remaining = set(recovery["remaining_candidate_ids"])
    if completed | remaining != expected or completed & remaining:
        raise RuntimeError("recovery candidates do not partition the frozen candidates")

    run_root = PRIVATE_ROOT / authorization_id
    for candidate_id, pin in preserved.items():
        receipt_path = run_root / "candidate_receipts" / f"{candidate_id}.json"
        prediction_path = run_root / "predictions" / f"{candidate_id}.jsonl"
        if _sha256(receipt_path) != pin["receipt_sha256"]:
            raise RuntimeError("preserved candidate receipt SHA-256 mismatch")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("prediction_sha256") != pin["prediction_sha256"]:
            raise RuntimeError("preserved prediction receipt hash mismatch")
        if _sha256(prediction_path) != pin["prediction_sha256"]:
            raise RuntimeError("preserved prediction SHA-256 mismatch")
        with prediction_path.open(encoding="utf-8") as handle:
            record_count = sum(1 for line in handle if line.strip())
        if record_count != pin["prediction_record_count"]:
            raise RuntimeError("preserved prediction record count mismatch")

    state.update(
        {
            "status": "RECOVERY_RUNNING",
            "recovery_count": 1,
            "recovery_id": recovery_id,
            "recovery_policy_sha256": recovery_sha256,
            "recovery_started_at": _utc_now(),
            "prior_failed_closed": {
                "closed_at": state["closed_at"],
                "closure_reason": state["closure_reason"],
                "failure_type": state["failure_type"],
                "state_sha256": recovery["failed_closed_state_sha256"],
            },
        }
    )
    _write_json(state_path, state)
    private_test_volume.commit()
    return {
        "authorization_id": authorization_id,
        "status": state["status"],
        "attempt_count": state["attempt_count"],
        "recovery_count": state["recovery_count"],
        "policy_sha256": policy_sha256,
        "recovery_policy_sha256": recovery_sha256,
        "remaining_candidate_ids": recovery["remaining_candidate_ids"],
    }


@app.function(
    image=training_image,
    timeout=5 * 60,
    volumes={str(PRIVATE_ROOT): private_test_volume},
)
def begin_one_shot_finalization_recovery(
    expected_policy_sha256: str, expected_finalization_recovery_sha256: str
) -> dict[str, Any]:
    """Authorize aggregate-only completion after all frozen inference succeeded."""

    private_test_volume.reload()
    _, policy, policy_sha256 = _load_remote_policy()
    _, recovery, recovery_sha256 = _load_remote_finalization_recovery()
    if policy_sha256 != expected_policy_sha256:
        raise RuntimeError("local and Modal TEST policy hashes differ")
    if recovery_sha256 != expected_finalization_recovery_sha256:
        raise RuntimeError("local and Modal finalization recovery hashes differ")
    if recovery["original_policy_sha256"] != policy_sha256:
        raise RuntimeError("finalization recovery references a different policy")
    if recovery["runner_sha256"] != _sha256(Path(__file__)):
        raise RuntimeError("finalization recovery runner SHA-256 mismatch")

    authorization_id = _safe_identifier(
        recovery["original_authorization_id"], "authorization_id"
    )
    finalization_recovery_id = _safe_identifier(
        recovery["finalization_recovery_id"], "finalization_recovery_id"
    )
    state_path = _state_path(authorization_id)
    if _sha256(state_path) != recovery["failed_closed_state_sha256"]:
        raise RuntimeError("failed aggregation state differs from authorization")
    state = _load_state(authorization_id)
    if state.get("status") != "FAILED_CLOSED":
        raise RuntimeError("finalization recovery requires FAILED_CLOSED state")
    if state.get("failure_type") != recovery["failure"]["type"]:
        raise RuntimeError("finalization failure type differs from authorization")
    if state.get("policy_sha256") != policy_sha256:
        raise RuntimeError("failed aggregation state references a different policy")
    if state.get("recovery_policy_sha256") != recovery["inference_recovery_sha256"]:
        raise RuntimeError("inference recovery SHA-256 differs")
    sequence = recovery.get("finalization_recovery_sequence", 1)
    previous_sequence = state.get("finalization_recovery_count", 0)
    if previous_sequence != sequence - 1:
        raise RuntimeError("TEST finalization recovery sequence is invalid")
    if sequence > 1 and state.get(
        "finalization_recovery_sha256"
    ) != recovery.get("prior_finalization_recovery_sha256"):
        raise RuntimeError("prior finalization recovery SHA-256 differs")

    completed_pins = {
        item["candidate_id"]: item for item in recovery["completed_candidates"]
    }
    expected = {candidate["candidate_id"] for candidate in policy["candidates"]}
    if set(state.get("completed_candidate_ids", [])) != expected:
        raise RuntimeError("not all frozen candidates completed inference")
    if set(completed_pins) != expected:
        raise RuntimeError("finalization pins differ from frozen candidates")
    run_root = PRIVATE_ROOT / authorization_id
    for candidate_id, pin in completed_pins.items():
        receipt_path = run_root / "candidate_receipts" / f"{candidate_id}.json"
        prediction_path = run_root / "predictions" / f"{candidate_id}.jsonl"
        if _sha256(receipt_path) != pin["receipt_sha256"]:
            raise RuntimeError("completed candidate receipt SHA-256 mismatch")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("prediction_sha256") != pin["prediction_sha256"]:
            raise RuntimeError("completed prediction receipt hash mismatch")
        if _sha256(prediction_path) != pin["prediction_sha256"]:
            raise RuntimeError("completed prediction SHA-256 mismatch")
        with prediction_path.open(encoding="utf-8") as handle:
            record_count = sum(1 for line in handle if line.strip())
        if record_count != pin["prediction_record_count"]:
            raise RuntimeError("completed prediction record count mismatch")

    prior_aggregation_failure = {
        "closed_at": state["closed_at"],
        "closure_reason": state["closure_reason"],
        "failure_type": state["failure_type"],
        "state_sha256": recovery["failed_closed_state_sha256"],
    }
    if state.get("prior_aggregation_failure") is not None:
        prior_aggregation_failure["previous"] = state["prior_aggregation_failure"]
    state.update(
        {
            "status": "FINALIZATION_RUNNING",
            "finalization_recovery_count": sequence,
            "finalization_recovery_id": finalization_recovery_id,
            "finalization_recovery_sha256": recovery_sha256,
            "finalization_recovery_started_at": _utc_now(),
            "prior_aggregation_failure": prior_aggregation_failure,
        }
    )
    _write_json(state_path, state)
    private_test_volume.commit()
    return {
        "authorization_id": authorization_id,
        "status": state["status"],
        "policy_sha256": policy_sha256,
        "finalization_recovery_sha256": recovery_sha256,
        "candidate_inference_started": False,
    }


def _verified_model_source(candidate: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if candidate["kind"] == "HF_BASE":
        from huggingface_hub import snapshot_download

        snapshot = Path(
            snapshot_download(
                repo_id=candidate["model_id"],
                revision=candidate["revision"],
                cache_dir=str(MODEL_CACHE_PATH),
            )
        )
        weights_path = snapshot / "model.safetensors"
        actual_weights_sha256 = _sha256(weights_path)
        if actual_weights_sha256 != candidate["model_weights_sha256"]:
            raise RuntimeError("base model weights SHA-256 mismatch")
        return str(snapshot), {
            "kind": "HF_BASE",
            "model_id": candidate["model_id"],
            "revision": candidate["revision"],
            "model_weights_sha256": actual_weights_sha256,
        }

    artifact = candidate["artifact"]
    source_dir = OUTPUT_ROOT / artifact["path"]
    manifest_path = source_dir / "remote_run_manifest.json"
    model_dir = source_dir / "merged"
    if not manifest_path.is_file() or not model_dir.is_dir():
        raise FileNotFoundError("fine-tuned checkpoint evidence is incomplete")
    manifest_sha256 = _sha256(manifest_path)
    if manifest_sha256 != artifact["manifest_sha256"]:
        raise RuntimeError("fine-tuned checkpoint manifest SHA-256 mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != artifact["training_run_id"]:
        raise RuntimeError("fine-tuned checkpoint run identity mismatch")
    if manifest.get("status") != "SUCCEEDED" or manifest.get("test_partition_used") is not False:
        raise RuntimeError("fine-tuned checkpoint is not eligible for reserved TEST")
    weights_path = model_dir / "model.safetensors"
    actual_weights_sha256 = _sha256(weights_path)
    if actual_weights_sha256 != candidate["model_weights_sha256"]:
        raise RuntimeError("fine-tuned model weights SHA-256 mismatch")
    recorded = manifest.get("artifacts", {}).get("merged/model.safetensors", {})
    if recorded.get("sha256") != actual_weights_sha256:
        raise RuntimeError("checkpoint manifest and merged weights disagree")
    return str(model_dir), {
        "kind": "REMOTE_MERGED",
        "training_run_id": artifact["training_run_id"],
        "cell_id": artifact["cell_id"],
        "manifest_sha256": manifest_sha256,
        "model_weights_sha256": actual_weights_sha256,
    }

@app.function(
    image=training_image,
    gpu="A10G",
    timeout=30 * 60,
    volumes={
        str(MODEL_CACHE_PATH): model_cache_volume,
        str(OUTPUT_ROOT): artifact_volume,
        str(PRIVATE_ROOT): private_test_volume,
    },
)
def run_one_shot_candidate(
    authorization_id: str, candidate_id: str, expected_policy_sha256: str
) -> dict[str, Any]:
    """Run one frozen candidate and retain predictions only on the private volume."""

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from edge_imci.evaluation.one_shot_test import load_authorized_test_rows
    from edge_imci.evaluation.base_control_prompt import (
        apply_schema_informed_base_prompt,
        load_schema_informed_base_system_prompt,
    )
    from edge_imci.evaluation.one_shot_test import candidate_prompt_treatment

    started = time.monotonic()
    authorization_id = _safe_identifier(authorization_id, "authorization_id")
    candidate_id = _safe_identifier(candidate_id, "candidate_id")
    private_test_volume.reload()
    artifact_volume.reload()
    _, policy, policy_sha256 = _load_remote_policy()
    if policy_sha256 != expected_policy_sha256:
        raise RuntimeError("TEST policy hash changed")
    state = _require_running_state(authorization_id, policy_sha256)
    candidates = {
        candidate["candidate_id"]: candidate for candidate in policy["candidates"]
    }
    if candidate_id not in candidates:
        raise RuntimeError("candidate is not preregistered")
    if candidate_id in state["completed_candidate_ids"]:
        raise RuntimeError("candidate TEST inference already exists")
    candidate = candidates[candidate_id]
    predictions_path = PRIVATE_ROOT / authorization_id / "predictions" / f"{candidate_id}.jsonl"
    receipt_path = (
        PRIVATE_ROOT / authorization_id / "candidate_receipts" / f"{candidate_id}.json"
    )
    if predictions_path.exists() or receipt_path.exists():
        raise RuntimeError("candidate TEST evidence path already exists")

    rows = load_authorized_test_rows(policy, repo_root=REMOTE_ROOT)
    prompt_receipt = {"kind": candidate_prompt_treatment(candidate)}
    treatment = candidate.get("prompt_treatment")
    if prompt_receipt["kind"] == "SCHEMA_INFORMED_BASE_CONTROL_V1":
        schema_path = REMOTE_ROOT / treatment["schema_path"]
        example_path = REMOTE_ROOT / treatment["example_output_path"]
        prompt, prompt_hashes = load_schema_informed_base_system_prompt(
            schema_path, example_path
        )
        expected_hashes = {
            "prompt_sha256": treatment["prompt_sha256"],
            "schema_sha256": treatment["schema_sha256"],
            "example_output_sha256": treatment["example_output_sha256"],
        }
        if any(prompt_hashes[name] != value for name, value in expected_hashes.items()):
            raise RuntimeError("schema-informed base prompt evidence SHA-256 mismatch")
        rows = apply_schema_informed_base_prompt(rows, prompt)
        prompt_receipt.update(prompt_hashes)
    model_source, verified_artifact = _verified_model_source(candidate)
    tokenizer = AutoTokenizer.from_pretrained(model_source, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_source,
        local_files_only=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    ).to("cuda")
    model.eval()
    predictions, inference = _generate_validation_predictions(
        model, tokenizer, rows, policy["generation"]
    )
    predictions_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in predictions
        ),
        encoding="utf-8",
    )
    duration_seconds = time.monotonic() - started
    receipt = {
        "schema_version": "1.0.0",
        "authorization_id": authorization_id,
        "candidate_id": candidate_id,
        "status": "SUCCEEDED",
        "policy_sha256": policy_sha256,
        "test_record_count": len(rows),
        "prediction_record_count": len(predictions),
        "prediction_sha256": _sha256(predictions_path),
        "private_prediction_path": str(predictions_path),
        "verified_artifact": verified_artifact,
        "generation": policy["generation"],
        "prompt_treatment": prompt_receipt,
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_seconds": duration_seconds,
        "inference": inference,
        "routine_record_review_performed": False,
        "finished_at": _utc_now(),
    }
    _write_json(receipt_path, receipt)
    state["completed_candidate_ids"].append(candidate_id)
    _write_json(_state_path(authorization_id), state)
    private_test_volume.commit()
    if candidate["kind"] == "HF_BASE":
        model_cache_volume.commit()
    return {
        "authorization_id": authorization_id,
        "candidate_id": candidate_id,
        "status": "SUCCEEDED",
        "prediction_record_count": len(predictions),
        "prediction_sha256": receipt["prediction_sha256"],
        "verified_artifact": verified_artifact,
        "gpu_name": receipt["gpu_name"],
        "gpu_seconds": duration_seconds,
        "inference": inference,
        "routine_record_review_performed": False,
    }

@app.function(
    image=training_image,
    timeout=15 * 60,
    volumes={str(PRIVATE_ROOT): private_test_volume},
)
def finalize_one_shot_test(
    authorization_id: str, expected_policy_sha256: str
) -> dict[str, Any]:
    """Aggregate private TEST evidence, seal it, and return no row-level content."""

    from edge_imci.evaluation.one_shot_test import evaluate_one_shot_test_predictions

    authorization_id = _safe_identifier(authorization_id, "authorization_id")
    private_test_volume.reload()
    _, policy, policy_sha256 = _load_remote_policy()
    if policy_sha256 != expected_policy_sha256:
        raise RuntimeError("TEST policy hash changed")
    state = _require_running_state(authorization_id, policy_sha256)
    is_recovery = state["status"] == "RECOVERY_RUNNING"
    is_finalization_recovery = state["status"] == "FINALIZATION_RUNNING"
    expected = [candidate["candidate_id"] for candidate in policy["candidates"]]
    if sorted(state["completed_candidate_ids"]) != sorted(expected):
        raise RuntimeError("not every preregistered candidate completed TEST inference")
    run_root = PRIVATE_ROOT / authorization_id
    prediction_paths = {
        candidate_id: run_root / "predictions" / f"{candidate_id}.jsonl"
        for candidate_id in expected
    }
    report = evaluate_one_shot_test_predictions(
        prediction_paths,
        policy_path=REMOTE_ROOT / POLICY_RELATIVE_PATH,
        repo_root=REMOTE_ROOT,
    )
    receipts = [
        json.loads(
            (run_root / "candidate_receipts" / f"{candidate_id}.json").read_text(
                encoding="utf-8"
            )
        )
        for candidate_id in expected
    ]
    total_gpu_seconds = sum(receipt["gpu_seconds"] for receipt in receipts)
    rate = policy["execution"]["a10g_gpu_rate_per_second"]
    report["execution"] = {
        "environment_kind": "MODAL",
        "app_name": APP_NAME,
        "gpu_type": policy["execution"]["gpu_type"],
        "candidate_job_count": len(receipts),
        "candidate_jobs": [
            {
                "candidate_id": receipt["candidate_id"],
                "gpu_name": receipt["gpu_name"],
                "gpu_seconds": receipt["gpu_seconds"],
                "inference": receipt["inference"],
                "verified_artifact": receipt["verified_artifact"],
            }
            for receipt in receipts
        ],
        "total_gpu_seconds": total_gpu_seconds,
        "estimated_gpu_cost": total_gpu_seconds * rate,
        "gpu_rate_per_second": rate,
        "currency": policy["execution"]["currency"],
        "cost_scope": "GPU_TIME_ONLY",
        "private_evidence_volume": policy["execution"]["private_evidence_volume"],
    }
    if state.get("recovery_count") == 1:
        recovery_finished_candidate_ids = {
            receipt["candidate_id"]
            for receipt in receipts
            if receipt["finished_at"] >= state["recovery_started_at"]
        }
        report["recovery"] = {
            "recovery_id": state["recovery_id"],
            "recovery_policy_sha256": state["recovery_policy_sha256"],
            "recovery_count": state["recovery_count"],
            "prior_failed_closed": state["prior_failed_closed"],
            "preserved_candidate_ids": [
                candidate_id
                for candidate_id in expected
                if candidate_id not in recovery_finished_candidate_ids
            ],
        }
    if is_finalization_recovery:
        report["finalization_recovery"] = {
            "finalization_recovery_id": state["finalization_recovery_id"],
            "finalization_recovery_sha256": state[
                "finalization_recovery_sha256"
            ],
            "finalization_recovery_count": state["finalization_recovery_count"],
            "prior_aggregation_failure": state["prior_aggregation_failure"],
            "candidate_inference_repeated": False,
        }
    report["closed_at"] = _utc_now()
    report["test_status"] = "CLOSED"
    if is_finalization_recovery:
        report["closure_reason"] = "AUTHORIZED_AGGREGATE_ONLY_COMPLETION"
    elif is_recovery:
        report["closure_reason"] = "AUTHORIZED_INFRASTRUCTURE_CONTINUATION_COMPLETED"
    else:
        report["closure_reason"] = "AUTHORIZED_ONE_SHOT_COMPLETED"
    report.pop("report_sha256", None)
    report["report_sha256"] = hash_canonical(report)
    _write_json(run_root / "aggregate_report.json", report)
    state.update(
        {
            "status": "CLOSED",
            "closed_at": report["closed_at"],
            "closure_reason": report["closure_reason"],
            "aggregate_report_sha256": report["report_sha256"],
        }
    )
    _write_json(_state_path(authorization_id), state)
    private_test_volume.commit()
    return report

@app.function(
    image=training_image,
    timeout=5 * 60,
    volumes={str(PRIVATE_ROOT): private_test_volume},
)
def close_failed_one_shot_test(
    authorization_id: str, expected_policy_sha256: str, failure_type: str
) -> dict[str, Any]:
    """Fail closed after any consumed authorization that cannot complete."""

    authorization_id = _safe_identifier(authorization_id, "authorization_id")
    failure_type = _safe_identifier(failure_type, "failure_type")
    private_test_volume.reload()
    _, _, policy_sha256 = _load_remote_policy()
    if policy_sha256 != expected_policy_sha256:
        raise RuntimeError("TEST policy hash changed")
    state = _require_running_state(authorization_id, policy_sha256)
    is_recovery = state["status"] == "RECOVERY_RUNNING"
    is_finalization_recovery = state["status"] == "FINALIZATION_RUNNING"
    state.update(
        {
            "status": "FAILED_CLOSED",
            "closed_at": _utc_now(),
            "closure_reason": (
                "AUTHORIZED_AGGREGATE_ONLY_COMPLETION_FAILED"
                if is_finalization_recovery
                else (
                    "AUTHORIZED_INFRASTRUCTURE_CONTINUATION_FAILED"
                    if is_recovery
                    else "AUTHORIZED_ONE_SHOT_FAILED"
                )
            ),
            "failure_type": failure_type,
        }
    )
    _write_json(_state_path(authorization_id), state)
    private_test_volume.commit()
    return {
        "schema_version": "1.0.0",
        "authorization_id": authorization_id,
        "test_status": "FAILED_CLOSED",
        "closed_at": state["closed_at"],
        "closure_reason": state["closure_reason"],
        "failure_type": failure_type,
        "policy_sha256": policy_sha256,
        "aggregate_only": True,
        "routine_record_review_performed": False,
    }


@app.local_entrypoint()
def main(
    output: str = str(DEFAULT_LOCAL_REPORT),
    policy_path: str = str(POLICY_RELATIVE_PATH),
    recovery_path: str = "",
    finalization_recovery_path: str = "",
    dry_run: bool = False,
) -> None:
    """Run a frozen TEST, inference recovery, or aggregate-only completion."""

    from edge_imci.evaluation.one_shot_test import (
        load_one_shot_test_finalization_recovery,
        load_one_shot_test_policy,
        load_one_shot_test_recovery,
    )

    if recovery_path and finalization_recovery_path:
        raise RuntimeError("choose exactly one TEST recovery mode")
    policy_file, policy = load_one_shot_test_policy(policy_path, repo_root=ROOT)
    policy_sha256 = hash_file(policy_file)[0]
    recovery = None
    recovery_sha256 = None
    finalization_recovery = None
    finalization_recovery_sha256 = None
    if recovery_path:
        recovery_file, recovery = load_one_shot_test_recovery(
            recovery_path, repo_root=ROOT
        )
        recovery_sha256 = hash_file(recovery_file)[0]
        if recovery["original_policy_sha256"] != policy_sha256:
            raise RuntimeError("TEST recovery references a different policy")
    if finalization_recovery_path:
        finalization_file, finalization_recovery = (
            load_one_shot_test_finalization_recovery(
                finalization_recovery_path, repo_root=ROOT
            )
        )
        finalization_recovery_sha256 = hash_file(finalization_file)[0]
        if finalization_recovery["original_policy_sha256"] != policy_sha256:
            raise RuntimeError(
                "TEST finalization recovery references a different policy"
            )
    destination = Path(output)
    if finalization_recovery is not None and output == str(DEFAULT_LOCAL_REPORT):
        destination = (
            DEFAULT_LOCAL_FINAL_REPORT_V2
            if finalization_recovery.get("finalization_recovery_sequence") == 2
            else DEFAULT_LOCAL_FINAL_REPORT
        )
    elif recovery is not None and output == str(DEFAULT_LOCAL_REPORT):
        destination = DEFAULT_LOCAL_RECOVERY_REPORT
    if not destination.is_absolute():
        destination = ROOT / destination
    if finalization_recovery is not None:
        execution_mode = "AGGREGATE_ONLY_COMPLETION"
        candidate_ids: list[str] = []
        recovery_id = finalization_recovery["finalization_recovery_id"]
        active_recovery_sha256 = finalization_recovery_sha256
    elif recovery is not None:
        execution_mode = "INFRASTRUCTURE_ONLY_CONTINUATION"
        candidate_ids = recovery["remaining_candidate_ids"]
        recovery_id = recovery["recovery_id"]
        active_recovery_sha256 = recovery_sha256
    else:
        execution_mode = "ONE_SHOT"
        candidate_ids = [
            candidate["candidate_id"] for candidate in policy["candidates"]
        ]
        recovery_id = None
        active_recovery_sha256 = None

    if dry_run:
        print(
            json.dumps(
                {
                    "authorization_id": policy["authorization_id"],
                    "execution_mode": execution_mode,
                    "candidate_ids": candidate_ids,
                    "expected_test_record_count": policy["dataset"][
                        "expected_record_count"
                    ],
                    "policy_sha256": policy_sha256,
                    "recovery_id": recovery_id,
                    "recovery_policy_sha256": active_recovery_sha256,
                    "remote_execution_started": False,
                    "test_rows_loaded": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    if destination.exists():
        raise RuntimeError("local one-shot TEST aggregate report already exists")

    if finalization_recovery is not None:
        begin = begin_one_shot_finalization_recovery.remote(
            policy_sha256, finalization_recovery_sha256
        )
    elif recovery is not None:
        begin = begin_one_shot_recovery.remote(policy_sha256, recovery_sha256)
    else:
        begin = begin_one_shot_test.remote(policy_sha256)
    authorization_id = begin["authorization_id"]
    try:
        for candidate_id in candidate_ids:
            run_one_shot_candidate.remote(
                authorization_id, candidate_id, policy_sha256
            )
        report = finalize_one_shot_test.remote(authorization_id, policy_sha256)
    except BaseException as error:
        closure = close_failed_one_shot_test.remote(
            authorization_id, policy_sha256, type(error).__name__
        )
        atomic_write_json(destination, closure)
        raise

    atomic_write_json(destination, report)
    print(
        json.dumps(
            {
                "authorization_id": report["authorization_id"],
                "test_status": report["test_status"],
                "passed": report["pass_fail"]["passed"],
                "report_sha256": report["report_sha256"],
                "candidate_results": {
                    candidate_id: result["aggregate"]
                    for candidate_id, result in report["candidate_results"].items()
                },
                "paired_comparison": report["paired_comparison"],
                "estimated_gpu_cost": report["execution"]["estimated_gpu_cost"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"aggregate_report={destination}")
