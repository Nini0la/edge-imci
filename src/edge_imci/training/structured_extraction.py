"""Canonical records for language-to-structured-state fine-tuning.

This module does not generate language, authorize training, or apply a model's
chat template. It deterministically pairs an approved PHC language variant
with the model-facing projection of its frozen semantic source.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from edge_imci.generation.holistic_golden import SUITE_ID
from edge_imci.generation.language_semantic_guards import (
    STYLE_CONTRACT_ID,
    load_style_contract,
)
from edge_imci.model_io.encounter import (
    MODEL_FACING_ENCOUNTER_SCHEMA_ID,
    MODEL_FACING_ENCOUNTER_SCHEMA_PATH,
    MODEL_TARGET_EXPORTER_ID,
    canonical_model_target_json,
    model_facing_schema_sha256,
    project_model_facing_encounter,
)
from edge_imci.training.dataset_policy import (
    DATASET_POLICY_ID,
    SPLIT_POLICY_ID,
    assert_target_corpus_eligible,
    parent_semantic_partition,
)


ROOT = Path(__file__).resolve().parents[3]
STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID = "edge-imci-structured-extraction-sft-record-v1"
STRUCTURED_EXTRACTION_RECORD_SCHEMA_PATH = (
    ROOT / "configs" / "training" / "structured_extraction_sft_record_v1.schema.json"
)
STRUCTURED_EXTRACTION_SYSTEM_INSTRUCTION = (
    "Convert the PHC worker's findings into one JSON object matching the "
    "EdgeIMCI model-facing encounter schema. Preserve explicitly stated "
    "positives, negatives, measurements, durations, and qualifiers. Use null "
    "for UNKNOWN; never infer an unmentioned finding as negative. Output JSON only."
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _record_validator() -> Draft202012Validator:
    model_schema = _load_json(MODEL_FACING_ENCOUNTER_SCHEMA_PATH)
    registry = Registry().with_resource(
        model_schema["$id"], Resource.from_contents(model_schema)
    )
    return Draft202012Validator(
        _load_json(STRUCTURED_EXTRACTION_RECORD_SCHEMA_PATH), registry=registry
    )


def validate_structured_extraction_record(record: dict[str, Any]) -> None:
    _record_validator().validate(record)


def _assert_approved_variant(variant_record: dict[str, Any]) -> None:
    if variant_record.get("status") != "APPROVED_CORPUS_CANDIDATE":
        raise ValueError("only an approved corpus-candidate language variant may be paired")
    review = variant_record.get("review", {})
    expected = {
        "semantic_faithfulness": "APPROVED",
        "naturalness": "APPROVED",
        "phc_suitability": "APPROVED_FOR_HACKATHON",
    }
    for key, value in expected.items():
        if review.get(key) != value:
            raise ValueError(f"language variant lacks approved {key} review")
    eligibility = variant_record.get("eligibility", {})
    if eligibility.get("corpus_candidate") is not True:
        raise ValueError("language variant is not a corpus candidate")
    if eligibility.get("training") is not False:
        raise ValueError("this architecture task must not authorize training")


def build_structured_extraction_record(
    *,
    semantic_record: dict[str, Any],
    variant_record: dict[str, Any],
    variant_style: str,
    noise_profile: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Pair approved language with a target exported from the frozen source."""

    source_case_id = semantic_record.get("golden_case_id")
    if not source_case_id:
        raise ValueError("semantic source case ID is required")
    return build_structured_extraction_record_from_target(
        source_case_id=source_case_id,
        semantic_suite_id=SUITE_ID,
        semantic_suite_sha256=variant_record.get("parent_source", {}).get(
            "semantic_cases_sha256", ""
        ),
        semantic_record_schema_id=semantic_record["record_schema_id"],
        target=project_model_facing_encounter(semantic_record),
        variant_record=variant_record,
        variant_style=variant_style,
        noise_profile=noise_profile,
    )


def build_structured_extraction_record_from_target(
    *,
    source_case_id: str,
    semantic_suite_id: str,
    semantic_suite_sha256: str,
    semantic_record_schema_id: str,
    target: dict[str, Any],
    variant_record: dict[str, Any],
    variant_style: str,
    noise_profile: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Pair approved language with an already projected model-facing target.

    This is used for extraction-only parents, including the distinct
    out-of-scope-age training parents.  It does not adapt the target into the
    clinical engine or let the model own the deterministic scope decision.
    """

    _assert_approved_variant(variant_record)
    style_contract = load_style_contract()
    if variant_style not in style_contract["variant_styles"]:
        raise ValueError(f"unknown language variant style: {variant_style}")
    unknown_noise = set(noise_profile) - set(style_contract["noise_profiles"])
    if unknown_noise:
        raise ValueError(f"unknown language noise profile: {sorted(unknown_noise)}")
    if not source_case_id or variant_record.get("semantic_case_id") != source_case_id:
        raise ValueError("variant and semantic source case IDs do not match")
    conversation = variant_record.get("conversation")
    if not isinstance(conversation, list) or not conversation:
        raise ValueError("variant record does not contain a user submission")
    user_message = conversation[0]
    if user_message.get("role") != "user" or not user_message.get("content"):
        raise ValueError("variant's first conversation item must be a non-empty user message")

    generation = variant_record.get("generation_provenance", {})
    assert_target_corpus_eligible(target)
    variant_id = variant_record["variant_id"]
    record = {
        "record_schema_id": STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID,
        "example_id": f"extract__{variant_id}",
        "source_case_id": source_case_id,
        "variant_id": variant_id,
        "partition": parent_semantic_partition(source_case_id),
        "input": copy.deepcopy(user_message),
        "language_provenance": {
            "variant_style": variant_style,
            "noise_profile": list(noise_profile),
            "style_contract_id": STYLE_CONTRACT_ID,
        },
        "target": target,
        "provenance": {
            "semantic_suite_id": semantic_suite_id,
            "semantic_suite_sha256": semantic_suite_sha256,
            "semantic_record_schema_id": semantic_record_schema_id,
            "variant_run_id": generation["generation_run_id"],
            "teacher_provider": generation["teacher_provider"],
            "teacher_model": generation["teacher_model"],
            "teacher_snapshot": generation["teacher_snapshot"],
            "prompt_id": generation["prompt_id"],
            "prompt_version": generation["prompt_version"],
            "prompt_sha256": generation["prompt_sha256"],
            "target_schema_id": MODEL_FACING_ENCOUNTER_SCHEMA_ID,
            "target_schema_sha256": model_facing_schema_sha256(),
            "target_exporter_id": MODEL_TARGET_EXPORTER_ID,
            "dataset_policy_id": DATASET_POLICY_ID,
            "split_policy_id": SPLIT_POLICY_ID,
        },
        "eligibility": {"corpus_candidate": True, "training": False},
    }
    validate_structured_extraction_record(record)
    return record


def format_structured_extraction_messages(record: dict[str, Any]) -> list[dict[str, str]]:
    """Create model-neutral role messages before any tokenizer chat template."""

    validate_structured_extraction_record(record)
    return [
        {"role": "system", "content": STRUCTURED_EXTRACTION_SYSTEM_INSTRUCTION},
        copy.deepcopy(record["input"]),
        {"role": "assistant", "content": canonical_model_target_json(record["target"])},
    ]
