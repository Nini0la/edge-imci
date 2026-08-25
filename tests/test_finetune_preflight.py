from __future__ import annotations

import json
from pathlib import Path

import pytest

from edge_imci.training import finetune
from edge_imci.training.finetune import (
    DEFAULT_CONFIG_PATH,
    FineTunePreflightError,
    preflight_training,
    training_tracking,
)

ROOT = Path(__file__).resolve().parents[1]
QWEN_1_7B_CONFIG = (
    ROOT / "configs/training/qwen3_1_7b_structured_extraction_lora_v1.json"
)


def test_first_sft_release_is_pinned_and_test_is_not_loaded() -> None:
    summary, selected = preflight_training()
    assert summary["status"] == "READY"
    assert summary["model_id"] == "Qwen/Qwen3-0.6B"
    assert summary["model_revision"] == "c1899de289a04d12100db370d81485cdf75e47ca"
    assert summary["partition_counts"] == {
        "TRAIN": 1239,
        "VALIDATION": 115,
        "TEST": 143,
    }
    assert set(selected) == {"TRAIN", "VALIDATION"}
    assert len(selected["TRAIN"]) == 1239
    assert len(selected["VALIDATION"]) == 115
    assert all(row["partition"] != "TEST" for rows in selected.values() for row in rows)


def test_preflight_fails_closed_on_data_hash_drift(monkeypatch) -> None:
    actual_sha256_file = finetune.sha256_file

    def drift_chat_hash(path):
        if str(path).endswith("chat_messages.jsonl"):
            return "0" * 64
        return actual_sha256_file(path)

    monkeypatch.setattr(finetune, "sha256_file", drift_chat_hash)
    with pytest.raises(FineTunePreflightError, match="chat messages SHA-256 mismatch"):
        preflight_training()


def test_release_does_not_claim_deployment_or_clinical_authority() -> None:
    release = json.loads(
        (DEFAULT_CONFIG_PATH.parent / "structured_extraction_sft_release_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert release["execution"]["formal_asus_admission_artifact"] is None
    assert release["authorization"] == {
        "training_authorized": True,
        "test_partition_use_authorized": False,
        "production_clinical_use_authorized": False,
        "deployment_authorized": False,
    }


def test_preflight_rejects_disabling_assistant_only_loss(tmp_path) -> None:
    config = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["tokenization"]["assistant_only_loss"] = False
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(FineTunePreflightError, match="assistant_only_loss"):
        preflight_training(config_path)


def test_qwen3_1_7b_preflight_reuses_data_without_loading_test() -> None:
    summary, selected = preflight_training(QWEN_1_7B_CONFIG)
    config = json.loads(QWEN_1_7B_CONFIG.read_text(encoding="utf-8"))

    assert summary["model_id"] == "Qwen/Qwen3-1.7B"
    assert summary["model_revision"] == "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
    assert summary["experiment_id"] == (
        "qwen3-1.7b-structured-extraction-sft-v1-modal"
    )
    assert summary["test_record_count_checked_but_not_loaded"] == 143
    assert summary["test_partition_returned_to_trainer"] is False
    assert set(selected) == {"TRAIN", "VALIDATION"}
    assert config["optimization"]["per_device_train_batch_size"] == 2
    assert config["optimization"]["gradient_accumulation_steps"] == 8
    assert config["modal"]["gpu_type"] == "A10G"


def test_new_training_lanes_require_explicit_tracking_metadata() -> None:
    config = json.loads(QWEN_1_7B_CONFIG.read_text(encoding="utf-8"))
    del config["tracking"]
    with pytest.raises(FineTunePreflightError, match="tracking metadata"):
        training_tracking(config)
