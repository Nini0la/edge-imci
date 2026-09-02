"""Export the project-owner-authorized seven-style training dataset."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from edge_imci.review.synthetic_batch import build_review_subjects_from_generation_attempts
from edge_imci.training.out_of_scope_parents import (
    PARENT_SCHEMA_ID,
    build_out_of_scope_training_parents,
)
from edge_imci.training.structured_extraction import (
    format_structured_extraction_messages,
    validate_structured_extraction_record,
)


ROOT = Path(__file__).resolve().parents[3]
AUTHORIZATION_PATH = (
    ROOT / "configs/training/structured_extraction_seven_style_auto_promotion_v1.json"
)
DATASET_V1_DIR = ROOT / "data/training_sources/structured_extraction_campaign_v1"
OUTPUT_DIR = ROOT / "data/training_sources/structured_extraction_seven_style_v2"
CANONICAL_PATH = OUTPUT_DIR / "canonical_records.jsonl"
CHAT_PATH = OUTPUT_DIR / "chat_messages.jsonl"
TRAIN_PATH = OUTPUT_DIR / "train.jsonl"
VALIDATION_PATH = OUTPUT_DIR / "validation.jsonl"
TEST_PATH = OUTPUT_DIR / "test.jsonl"
DUPLICATE_REPORT_PATH = OUTPUT_DIR / "duplicate_report.json"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _payload(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return "".join(_canonical_json(row) + "\n" for row in rows).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _asset(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload = _payload(rows)
    path.write_bytes(payload)
    return {
        "record_count": len(rows),
        "sha256": _sha256(payload),
    }


def _normalize_out_of_scope_provenance(records: list[dict[str, Any]]) -> None:
    parents = {
        item["parent_case_id"]: item for item in build_out_of_scope_training_parents()
    }
    for record in records:
        parent = parents.get(record["source_case_id"])
        if parent is None:
            continue
        provenance = record["provenance"]
        provenance["semantic_suite_id"] = (
            "edge-imci-structured-extraction-out-of-scope-parents-v1"
        )
        provenance["semantic_suite_sha256"] = _sha256(
            _canonical_json(parent).encode("utf-8")
        )
        provenance["semantic_record_schema_id"] = PARENT_SCHEMA_ID
        validate_structured_extraction_record(record)


def build_expanded_dataset() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    authorization = _load_json(AUTHORIZATION_PATH)
    if authorization.get("status") != "AUTHORIZED_FOR_AUTO_PROMOTION":
        raise PermissionError("seven-style auto-promotion is not authorized")
    if authorization["policy"].get("semantic_review_waived") is not True:
        raise PermissionError("semantic-review waiver is absent")
    if authorization["authorization"].get("dataset_export_authorized") is not True:
        raise PermissionError("dataset export is not authorized")

    source = ROOT / authorization["source"]["path"]
    source_payload = source.read_bytes()
    if _sha256(source_payload) != authorization["source"]["sha256"]:
        raise ValueError("authorized deterministic-pass source hash changed")
    attempts = _load_jsonl(source)
    expected = authorization["source"]["expected_record_count"]
    if len(attempts) != expected:
        raise ValueError("deterministic-pass source count changed")
    for attempt in attempts:
        validation = attempt.get("validation") or {}
        if (
            attempt.get("status") != "PENDING_HUMAN_REVIEW"
            or validation.get("deterministic_pass") is not True
            or validation.get("error_codes")
            or not isinstance(attempt.get("candidate"), dict)
        ):
            raise ValueError("auto-promotion source contains a non-pass record")

    subjects = build_review_subjects_from_generation_attempts(attempts)
    if len(subjects) != expected:
        raise ValueError("not every deterministic pass converted to a canonical record")
    promoted = [subject["canonical_record"] for subject in subjects]
    if {record["partition"] for record in promoted} != {"TRAIN"}:
        raise ValueError("auto-promotion may contain TRAIN parents only")
    _normalize_out_of_scope_provenance(promoted)

    existing = _load_jsonl(DATASET_V1_DIR / "canonical_records.jsonl")
    canonical = sorted(existing + promoted, key=lambda row: row["example_id"])
    example_ids = [row["example_id"] for row in canonical]
    variant_ids = [row["variant_id"] for row in canonical]
    if len(example_ids) != len(set(example_ids)) or len(variant_ids) != len(set(variant_ids)):
        raise ValueError("expanded dataset identities are not unique")
    for record in canonical:
        validate_structured_extraction_record(record)

    chats = [
        {
            "example_id": record["example_id"],
            "source_case_id": record["source_case_id"],
            "variant_id": record["variant_id"],
            "partition": record["partition"],
            "messages": format_structured_extraction_messages(record),
        }
        for record in canonical
    ]
    text_counts = Counter(record["input"]["content"] for record in promoted)
    style_rows: dict[str, list[dict[str, Any]]] = {}
    for record in promoted:
        style_rows.setdefault(record["language_provenance"]["variant_style"], []).append(record)
    duplicate_report = {
        "scope": "AUTO_PROMOTED_NEW_RECORDS_ONLY",
        "record_count": len(promoted),
        "unique_text_count": len(text_counts),
        "duplicate_row_count": len(promoted) - len(text_counts),
        "duplicated_text_group_count": sum(count > 1 for count in text_counts.values()),
        "maximum_text_multiplicity": max(text_counts.values()),
        "exact_duplicates_retained": True,
        "by_style": {
            style: {
                "record_count": len(rows),
                "unique_text_count": len({row["input"]["content"] for row in rows}),
            }
            for style, rows in sorted(style_rows.items())
        },
    }
    return canonical, chats, duplicate_report


def write_expanded_dataset() -> dict[str, Any]:
    canonical, chats, duplicate_report = build_expanded_dataset()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assets: dict[str, Any] = {}
    assets[str(CANONICAL_PATH.relative_to(ROOT))] = _asset(CANONICAL_PATH, canonical)
    assets[str(CHAT_PATH.relative_to(ROOT))] = _asset(CHAT_PATH, chats)
    for partition, path in (
        ("TRAIN", TRAIN_PATH),
        ("VALIDATION", VALIDATION_PATH),
        ("TEST", TEST_PATH),
    ):
        rows = [row for row in chats if row["partition"] == partition]
        assets[str(path.relative_to(ROOT))] = _asset(path, rows)
    _write_json(DUPLICATE_REPORT_PATH, duplicate_report)
    duplicate_payload = DUPLICATE_REPORT_PATH.read_bytes()
    assets[str(DUPLICATE_REPORT_PATH.relative_to(ROOT))] = {
        "sha256": _sha256(duplicate_payload)
    }

    style_counts = Counter(
        row["language_provenance"]["variant_style"] for row in canonical
    )
    partition_counts = Counter(row["partition"] for row in canonical)
    promoted_count = 5666
    manifest = {
        "campaign_id": "edge-imci-structured-extraction-seven-style-v2",
        "dataset_release_id": "edge-imci-structured-extraction-seven-style-v2",
        "status": "AUTO_PROMOTED_FOR_EXPERIMENTAL_TRAINING",
        "record_schema_id": "edge-imci-structured-extraction-sft-record-v1",
        "record_count": len(canonical),
        "promoted_record_count": promoted_count,
        "existing_v1_record_count": len(canonical) - promoted_count,
        "parent_case_count": len({row["source_case_id"] for row in canonical}),
        "style_counts": dict(sorted(style_counts.items())),
        "partition_counts": dict(sorted(partition_counts.items())),
        "source_dataset_v1_manifest_sha256": _sha256(
            (DATASET_V1_DIR / "manifest.json").read_bytes()
        ),
        "auto_promotion_authorization": str(AUTHORIZATION_PATH.relative_to(ROOT)),
        "auto_promotion_authorization_sha256": _sha256(AUTHORIZATION_PATH.read_bytes()),
        "review_policy": {
            "authority": "PROJECT_OWNER",
            "semantic_review_waived": True,
            "acceptance_basis": "DETERMINISTIC_PASS",
        },
        "validation": {
            "all_promoted_records_deterministic_passes": True,
            "all_promoted_records_inherit_train_partition": True,
            "parent_split_inheritance": True,
            "clinical_outputs_excluded_from_target": True,
            "assistant_targets_regenerated_deterministically": True,
            "exact_duplicates_retained_and_reported": True,
        },
        "authorization": {
            "experimental_finetuning_authorized": True,
            "training_authorized": False,
            "test_unsealing_authorized": False,
            "deployment_authorized": False,
            "production_clinical_use_authorized": False,
        },
        "assets": assets,
    }
    _write_json(MANIFEST_PATH, manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(write_expanded_dataset(), indent=2, sort_keys=True))
