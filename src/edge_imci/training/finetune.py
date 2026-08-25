"""Fail-closed preparation for structured-extraction fine-tuning runs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = (
    ROOT / "configs/training/qwen3_0_6b_structured_extraction_lora_v1.json"
)
MODEL_SCHEMA_PATH = ROOT / "configs/model_io/model_facing_encounter_v1.schema.json"


class FineTunePreflightError(ValueError):
    """Raised before paid compute when a pinned training input is inconsistent."""


def load_json_object(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FineTunePreflightError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(repo_root: Path, value: str) -> Path:
    path = (repo_root / value).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError as error:
        raise FineTunePreflightError(f"path escapes repository root: {value}") from error
    if not path.is_file():
        raise FineTunePreflightError(f"required training input is missing: {value}")
    return path


def _iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise FineTunePreflightError(f"blank JSONL record at {path}:{line_number}")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise FineTunePreflightError(
                    f"invalid JSON at {path}:{line_number}: {error.msg}"
                ) from error
            if not isinstance(value, dict):
                raise FineTunePreflightError(
                    f"JSONL record at {path}:{line_number} is not an object"
                )
            yield line_number, value


def _validate_messages(
    row: dict[str, Any],
    *,
    line_number: int,
    target_validator: Draft202012Validator,
) -> None:
    messages = row.get("messages")
    if not isinstance(messages, list) or [item.get("role") for item in messages] != [
        "system",
        "user",
        "assistant",
    ]:
        raise FineTunePreflightError(
            f"record {line_number} must contain system/user/assistant messages"
        )
    for message in messages:
        if not isinstance(message.get("content"), str) or not message["content"]:
            raise FineTunePreflightError(
                f"record {line_number} contains an empty/non-string message"
            )
    try:
        target = json.loads(messages[-1]["content"])
    except json.JSONDecodeError as error:
        raise FineTunePreflightError(
            f"assistant target at record {line_number} is not JSON: {error.msg}"
        ) from error
    if not isinstance(target, dict):
        raise FineTunePreflightError(
            f"assistant target at record {line_number} is not a JSON object"
        )
    errors = sorted(
        target_validator.iter_errors(target), key=lambda item: list(item.absolute_path)
    )
    if errors:
        location = "/".join(str(item) for item in errors[0].absolute_path) or "<root>"
        raise FineTunePreflightError(
            f"assistant target at record {line_number} fails schema at {location}: "
            f"{errors[0].message}"
        )


def preflight_training(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    repo_root: str | Path = ROOT,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Validate authorization, hashes, splits, records, and model identity.

    The returned rows intentionally include only the authorized TRAIN and
    VALIDATION partitions. The held-out TEST partition is counted and checked
    but never returned to a trainer.
    """

    root = Path(repo_root).resolve()
    config_file = Path(config_path)
    if not config_file.is_absolute():
        config_file = _resolve(root, str(config_file))
    config = load_json_object(config_file)
    dataset_config = config.get("dataset", {})
    base_model = config.get("base_model", {})
    if config.get("training_stage") != "STRUCTURED_EXTRACTION_SFT_V1":
        raise FineTunePreflightError("unexpected training stage")

    release_path = _resolve(root, dataset_config["release_path"])
    manifest_path = _resolve(root, dataset_config["manifest_path"])
    chat_path = _resolve(root, dataset_config["chat_messages_path"])
    schema_path = _resolve(
        root, str(MODEL_SCHEMA_PATH.relative_to(ROOT))
    )
    release = load_json_object(release_path)
    manifest = load_json_object(manifest_path)

    historical_authorization = manifest.get("authorization", {})
    if historical_authorization.get("training_authorized") is not False:
        raise FineTunePreflightError(
            "historical corpus manifest must remain training-unauthorized; use a separate release"
        )

    authorization = release.get("authorization", {})
    if release.get("status") != "AUTHORIZED_FOR_EXPLORATORY_SFT" or not authorization.get(
        "training_authorized"
    ):
        raise FineTunePreflightError("dataset release does not authorize training")
    if authorization.get("test_partition_use_authorized") is not False:
        raise FineTunePreflightError("release must explicitly prohibit TEST partition use")
    if authorization.get("production_clinical_use_authorized") is not False:
        raise FineTunePreflightError("training release cannot authorize clinical use")

    release_model = release.get("model", {})
    for key in ("model_id", "revision"):
        if release_model.get(key) != base_model.get(key):
            raise FineTunePreflightError(f"released model {key} does not match config")
    if base_model.get("revision") != base_model.get("tokenizer_revision"):
        raise FineTunePreflightError("model and tokenizer revisions must be identical")
    tokenization = config.get("tokenization", {})
    expected_tokenization_guards = {
        "assistant_only_loss": True,
        "enable_thinking": False,
        "truncation_allowed": False,
    }
    for key, expected in expected_tokenization_guards.items():
        if tokenization.get(key) is not expected:
            raise FineTunePreflightError(f"required tokenization guard is disabled: {key}")

    released_dataset = release.get("dataset", {})
    pinned_inputs = (
        (manifest_path, released_dataset.get("manifest_sha256"), "manifest"),
        (chat_path, released_dataset.get("chat_messages_sha256"), "chat messages"),
    )
    for path, expected, label in pinned_inputs:
        actual = sha256_file(path)
        if actual != expected:
            raise FineTunePreflightError(
                f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
            )

    manifest_asset = manifest.get("assets", {}).get(
        dataset_config["chat_messages_path"], {}
    )
    if manifest_asset.get("sha256") != released_dataset.get("chat_messages_sha256"):
        raise FineTunePreflightError("manifest and release disagree on chat data hash")
    if manifest.get("campaign_id") != released_dataset.get("campaign_id"):
        raise FineTunePreflightError("manifest and release campaign IDs disagree")

    target_validator = Draft202012Validator(load_json_object(schema_path))
    partition_counts: Counter[str] = Counter()
    parent_partitions: dict[str, set[str]] = defaultdict(set)
    seen_example_ids: set[str] = set()
    selected: dict[str, list[dict[str, Any]]] = {"TRAIN": [], "VALIDATION": []}
    allowed_partitions = set(selected) | {"TEST"}
    for line_number, row in _iter_jsonl(chat_path):
        example_id = row.get("example_id")
        if not isinstance(example_id, str) or not example_id:
            raise FineTunePreflightError(f"record {line_number} lacks example_id")
        if example_id in seen_example_ids:
            raise FineTunePreflightError(f"duplicate example_id: {example_id}")
        seen_example_ids.add(example_id)
        partition = row.get("partition")
        if partition not in allowed_partitions:
            raise FineTunePreflightError(
                f"record {line_number} has unexpected partition: {partition}"
            )
        source_case_id = row.get("source_case_id")
        if not isinstance(source_case_id, str) or not source_case_id:
            raise FineTunePreflightError(f"record {line_number} lacks source_case_id")
        _validate_messages(
            row, line_number=line_number, target_validator=target_validator
        )
        partition_counts[partition] += 1
        parent_partitions[source_case_id].add(partition)
        if partition in selected:
            selected[partition].append(row)

    leaked = sorted(
        source for source, partitions in parent_partitions.items() if len(partitions) != 1
    )
    if leaked:
        raise FineTunePreflightError(
            f"parent encounter appears in multiple partitions: {leaked[:5]}"
        )
    expected_counts = {
        **released_dataset.get("authorized_partitions", {}),
        **released_dataset.get("prohibited_partitions", {}),
    }
    if dict(partition_counts) != expected_counts:
        raise FineTunePreflightError(
            f"partition counts differ from release: {dict(partition_counts)}"
        )
    if dict(partition_counts) != manifest.get("partition_counts"):
        raise FineTunePreflightError("partition counts differ from dataset manifest")
    if sum(partition_counts.values()) != manifest.get("record_count"):
        raise FineTunePreflightError("record count differs from dataset manifest")

    summary = {
        "status": "READY",
        "config_id": config["config_id"],
        "config_sha256": sha256_file(config_file),
        "release_id": release["release_id"],
        "release_sha256": sha256_file(release_path),
        "model_id": base_model["model_id"],
        "model_revision": base_model["revision"],
        "dataset_manifest_sha256": sha256_file(manifest_path),
        "chat_messages_sha256": sha256_file(chat_path),
        "partition_counts": dict(partition_counts),
        "trainable_record_count": len(selected["TRAIN"]),
        "validation_record_count": len(selected["VALIDATION"]),
        "test_record_count_checked_but_not_loaded": partition_counts["TEST"],
        "parent_case_count": len(parent_partitions),
        "test_partition_returned_to_trainer": False,
        "production_clinical_use_authorized": False,
    }
    return summary, selected
