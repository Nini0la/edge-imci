"""Build distinct extraction-only parents for out-of-scope age training.

These records teach truthful age and finding extraction. They contain no
clinical classifications or actions; the deterministic adapter remains the
sole owner of the supported-age scope decision.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from edge_imci.generation.holistic_golden import SUITE_ID, load_holistic_golden_suite
from edge_imci.generation.holistic_variants import SEMANTIC_CASES_SHA256
from edge_imci.model_io.encounter import (
    MODEL_FACING_ENCOUNTER_SCHEMA_PATH,
    model_target_to_holistic_encounter,
    project_model_facing_encounter,
)
from edge_imci.training.dataset_policy import parent_semantic_partition


ROOT = Path(__file__).resolve().parents[3]
PARENT_SCHEMA_ID = "edge-imci-structured-extraction-out-of-scope-parent-v1"
PARENT_SCHEMA_PATH = (
    ROOT
    / "configs"
    / "training"
    / "structured_extraction_out_of_scope_parent_v1.schema.json"
)
OUTPUT_DIR = ROOT / "data" / "training_sources" / "structured_extraction_out_of_scope_v1"
PARENTS_PATH = OUTPUT_DIR / "parent_cases.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
SOURCE_DEFINITIONS = (
    {
        "parent_case_id": "oos-extract-young-respiratory-001",
        "base_frozen_case_id": "hpg-020-resp-post-bronchodilator-improved",
        "age_months": 1,
    },
    {
        "parent_case_id": "oos-extract-older-fever-001",
        "base_frozen_case_id": "hpg-041-fever-high-positive",
        "age_months": 60,
    },
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validator() -> Draft202012Validator:
    model_schema = json.loads(MODEL_FACING_ENCOUNTER_SCHEMA_PATH.read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        model_schema["$id"], Resource.from_contents(model_schema)
    )
    schema = json.loads(PARENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=registry)


def build_out_of_scope_training_parents() -> list[dict[str, Any]]:
    frozen = {item["golden_case_id"]: item for item in load_holistic_golden_suite()}
    records: list[dict[str, Any]] = []
    for definition in SOURCE_DEFINITIONS:
        base = frozen[definition["base_frozen_case_id"]]
        target = project_model_facing_encounter(base)
        target = copy.deepcopy(target)
        target["patient_facts"]["age_months"] = definition["age_months"]
        parent_id = definition["parent_case_id"]
        if parent_semantic_partition(parent_id) != "TRAIN":
            raise ValueError("out-of-scope extraction parent must be forced to TRAIN")
        try:
            model_target_to_holistic_encounter(target, encounter_id=parent_id)
        except ValueError as exc:
            error = str(exc)
        else:  # pragma: no cover - the deterministic scope checker must reject
            raise ValueError("out-of-scope training parent unexpectedly entered the engine")
        if error != "age_months must be at least 2 and less than 60":
            raise ValueError(f"unexpected deterministic scope outcome: {error}")
        record = {
            "parent_record_schema_id": PARENT_SCHEMA_ID,
            "parent_case_id": parent_id,
            "corpus_role": "STRUCTURED_EXTRACTION_TRAINING_PARENT",
            "partition": "TRAIN",
            "model_facing_target": target,
            "expected_adapter_outcome": {
                "owner": "DETERMINISTIC_SCOPE_CHECKER",
                "kind": "SCHEMA_REJECTION",
                "error": error,
            },
            "source_provenance": {
                "semantic_suite_id": SUITE_ID,
                "semantic_suite_sha256": SEMANTIC_CASES_SHA256,
                "base_frozen_case_id": definition["base_frozen_case_id"],
                "base_frozen_record_sha256": _sha256(_canonical_bytes(base)),
                "transformation": "AGE_ONLY_REPLACEMENT_FOR_SCOPE_EXTRACTION",
            },
            "language_generation_status": "NOT_STARTED_REVIEWED_VARIANT_REQUIRED",
            "authorization": {
                "bulk_generation_authorized": False,
                "training_authorized": False,
            },
        }
        _validator().validate(record)
        records.append(record)
    if {row["parent_case_id"] for row in records} & {
        "hpg-077-out-of-scope-age-1",
        "hpg-078-out-of-scope-age-60",
    }:
        raise ValueError("training parents overlap the frozen out-of-scope evaluation set")
    return records


def write_out_of_scope_training_parents() -> dict[str, Any]:
    records = build_out_of_scope_training_parents()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        _canonical_bytes(record).decode("utf-8") + "\n" for record in records
    )
    PARENTS_PATH.write_text(payload, encoding="utf-8")
    manifest = {
        "source_set_id": "edge-imci-structured-extraction-out-of-scope-parents-v1",
        "status": "PARENTS_READY_LANGUAGE_NOT_GENERATED",
        "parent_count": len(records),
        "parent_case_ids": [row["parent_case_id"] for row in records],
        "partition": "TRAIN",
        "evaluation_parent_case_ids": [
            "hpg-077-out-of-scope-age-1",
            "hpg-078-out-of-scope-age-60",
        ],
        "training_and_evaluation_parents_disjoint": True,
        "scope_decision_owner": "DETERMINISTIC_SCOPE_CHECKER",
        "clinical_outputs_in_model_target": False,
        "parents_sha256": _sha256(payload.encode("utf-8")),
        "next_gate": "GENERATE_AND_REVIEW_INPUT_LANGUAGE_BEFORE_SFT_PAIRING",
        "authorization": {
            "bulk_generation_authorized": False,
            "training_authorized": False,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    write_out_of_scope_training_parents()
