"""One-use Modal runner for the authorized schema-informed base diagnostic."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal

from edge_imci.evaluation.modal_one_shot_test import (
    PRIVATE_ROOT,
    _load_state,
    _sha256,
    _verified_model_source,
    _write_json,
    artifact_volume,
    model_cache_volume,
    private_test_volume,
)
from edge_imci.experiments.provenance import atomic_write_json, hash_file
from edge_imci.training.modal_finetune import (
    MODEL_CACHE_PATH,
    OUTPUT_ROOT,
    REMOTE_ROOT,
    ROOT,
    _generate_validation_predictions,
    training_image,
)

APP_NAME = "edge-imci-qwen3-0-6b-posthoc-base-control"
AUTHORIZATION_RELATIVE_PATH = Path(
    "configs/evaluation/qwen3_0_6b_posthoc_schema_informed_base_control_v1.json"
)
DEFAULT_LOCAL_REPORT = Path(
    "experiments/evaluation/qwen3-0.6b-posthoc-base-control-v1/aggregate_report.json"
)

app = modal.App(APP_NAME)
posthoc_image = training_image.add_local_dir(
    str(ROOT / "experiments/evaluation/qwen3-0.6b-one-shot-test-v1"),
    remote_path="/workspace/experiments/evaluation/qwen3-0.6b-one-shot-test-v1",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@app.function(
    image=posthoc_image,
    gpu="A10G",
    timeout=30 * 60,
    volumes={
        str(MODEL_CACHE_PATH): model_cache_volume,
        str(PRIVATE_ROOT): private_test_volume,
        str(OUTPUT_ROOT): artifact_volume,
    },
)
def run_authorized_posthoc_base_control(
    expected_authorization_sha256: str,
) -> dict[str, Any]:
    """Consume the authorization, run only the corrected base, and aggregate."""

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from edge_imci.evaluation.base_control_prompt import (
        apply_schema_informed_base_prompt,
        load_schema_informed_base_system_prompt,
    )
    from edge_imci.evaluation.one_shot_test import load_authorized_test_rows
    from edge_imci.evaluation.posthoc_base_control import (
        evaluate_posthoc_base_control_predictions,
        load_posthoc_base_control_authorization,
    )

    started = time.monotonic()
    private_test_volume.reload()
    artifact_volume.reload()
    authorization_path = REMOTE_ROOT / AUTHORIZATION_RELATIVE_PATH
    authorization_file, authorization, policy = (
        load_posthoc_base_control_authorization(
            authorization_path, repo_root=REMOTE_ROOT
        )
    )
    authorization_sha256 = hash_file(authorization_file)[0]
    if authorization_sha256 != expected_authorization_sha256:
        raise RuntimeError("post-hoc authorization SHA-256 changed")
    if _sha256(Path(__file__)) != authorization["runner"]["sha256"]:
        raise RuntimeError("post-hoc runner SHA-256 mismatch")

    original_id = authorization["original_evidence"]["authorization_id"]
    original_state = _load_state(original_id)
    if (
        original_state.get("status") != "CLOSED"
        or original_state.get("aggregate_report_sha256")
        != authorization["original_evidence"]["aggregate_report_sha256"]
    ):
        raise RuntimeError("original TEST closure evidence differs")

    diagnostic_id = authorization["diagnostic_id"]
    run_root = PRIVATE_ROOT / original_id / "posthoc" / diagnostic_id
    if run_root.exists():
        raise RuntimeError("post-hoc TEST authorization has already been consumed")
    run_root.mkdir(parents=True)
    state_path = run_root / "state.json"
    state = {
        "schema_version": "1.0.0",
        "diagnostic_id": diagnostic_id,
        "status": "RUNNING",
        "use_count": 1,
        "authorization_sha256": authorization_sha256,
        "started_at": _utc_now(),
        "post_hoc": True,
    }
    _write_json(state_path, state)
    private_test_volume.commit()

    try:
        rows = load_authorized_test_rows(policy, repo_root=REMOTE_ROOT)
        treatment = authorization["prompt_treatment"]
        prompt, prompt_hashes = load_schema_informed_base_system_prompt(
            REMOTE_ROOT / treatment["schema_path"],
            REMOTE_ROOT / treatment["example_output_path"],
        )
        rows = apply_schema_informed_base_prompt(rows, prompt)
        comparison = authorization["comparison"]
        candidates = {
            candidate["candidate_id"]: candidate for candidate in policy["candidates"]
        }
        candidate = candidates[comparison["source_base_candidate_id"]]
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
            model, tokenizer, rows, authorization["generation"]
        )
        base_path = run_root / "corrected_base_predictions.jsonl"
        base_path.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                for row in predictions
            ),
            encoding="utf-8",
        )
        selected_id = comparison["historical_selected_candidate_id"]
        selected_path = (
            PRIVATE_ROOT / original_id / "predictions" / f"{selected_id}.jsonl"
        )
        report = evaluate_posthoc_base_control_predictions(
            base_path,
            selected_path,
            authorization_path=authorization_path,
            repo_root=REMOTE_ROOT,
        )
        duration_seconds = time.monotonic() - started
        report["execution"] = {
            "environment_kind": "MODAL",
            "app_name": APP_NAME,
            "gpu_type": "A10G",
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_seconds": duration_seconds,
            "inference": inference,
            "verified_artifact": verified_artifact,
            "prompt_treatment": prompt_hashes,
        }
        report["closed_at"] = _utc_now()
        report.pop("report_sha256", None)
        from edge_imci.experiments.provenance import hash_canonical

        report["report_sha256"] = hash_canonical(report)
        _write_json(run_root / "aggregate_report.json", report)
        state.update(
            {
                "status": "CLOSED",
                "closed_at": report["closed_at"],
                "report_sha256": report["report_sha256"],
            }
        )
        _write_json(state_path, state)
        private_test_volume.commit()
        model_cache_volume.commit()
        return report
    except BaseException as error:
        state.update(
            {
                "status": "FAILED_CLOSED",
                "closed_at": _utc_now(),
                "failure_type": type(error).__name__,
            }
        )
        _write_json(state_path, state)
        private_test_volume.commit()
        raise


@app.local_entrypoint()
def main(
    output: str = str(DEFAULT_LOCAL_REPORT),
    authorization_path: str = str(AUTHORIZATION_RELATIVE_PATH),
    dry_run: bool = False,
) -> None:
    """Validate or execute the authorized one-use post-hoc diagnostic."""

    from edge_imci.evaluation.posthoc_base_control import (
        load_posthoc_base_control_authorization,
    )

    authorization_file, authorization, _ = load_posthoc_base_control_authorization(
        authorization_path, repo_root=ROOT
    )
    authorization_sha256 = hash_file(authorization_file)[0]
    if dry_run:
        print(
            json.dumps(
                {
                    "diagnostic_id": authorization["diagnostic_id"],
                    "status": authorization["status"],
                    "partition": "TEST",
                    "new_candidate_inference": [
                        authorization["comparison"]["corrected_base_candidate_id"]
                    ],
                    "historical_selected_reused": authorization["comparison"][
                        "historical_selected_candidate_id"
                    ],
                    "authorization_sha256": authorization_sha256,
                    "remote_execution_started": False,
                    "test_rows_loaded": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    destination = Path(output)
    if not destination.is_absolute():
        destination = ROOT / destination
    if destination.exists():
        raise RuntimeError("local post-hoc aggregate report already exists")
    report = run_authorized_posthoc_base_control.remote(authorization_sha256)
    atomic_write_json(destination, report)
    print(
        json.dumps(
            {
                "diagnostic_id": report["diagnostic_id"],
                "status": report["status"],
                "report_sha256": report["report_sha256"],
                "candidate_results": {
                    candidate_id: result["aggregate"]
                    for candidate_id, result in report["candidate_results"].items()
                },
                "paired_comparison": report["paired_comparison"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"aggregate_report={destination}")
