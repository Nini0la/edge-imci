"""Approved dataset-policy constraints for structured extraction v1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DATASET_POLICY_ID = "edge-imci-structured-extraction-dataset-policy-v1"
SPLIT_POLICY_ID = "edge-imci-parent-semantic-split-v1"
DATASET_POLICY_PATH = (
    ROOT / "configs" / "training" / "structured_extraction_dataset_policy_v1.json"
)
DATASET_POLICY_YAML_PATH = DATASET_POLICY_PATH.with_suffix(".yaml")
_PARTITIONS = ("TRAIN", "VALIDATION", "TEST")


def load_structured_extraction_dataset_policy() -> dict[str, Any]:
    policy = json.loads(DATASET_POLICY_PATH.read_text(encoding="utf-8"))
    expected = {
        "policy_id": DATASET_POLICY_ID,
        "policy_version": "1.0.0",
        "status": "APPROVED_FOR_DATASET_DESIGN",
        "authority": "PROJECT_OWNER_DECISION",
        "clinical_rule_change": False,
    }
    for key, value in expected.items():
        if policy.get(key) != value:
            raise ValueError(f"incorrect structured-extraction dataset policy {key}")
    split = policy.get("split_policy", {})
    if split.get("split_policy_id") != SPLIT_POLICY_ID:
        raise ValueError("incorrect parent semantic split policy ID")
    if split.get("assignment_unit") != "PARENT_SEMANTIC_CASE":
        raise ValueError("language variants must split by parent semantic case")
    if split.get("variant_inheritance_required") is not True:
        raise ValueError("all variants must inherit their parent partition")
    if split.get("cross_partition_parent_overlap_allowed") is not False:
        raise ValueError("parent semantic cases cannot cross partitions")
    ranges = split.get("partitions", {})
    if [ranges.get(name) for name in _PARTITIONS] != [
        [0, 8000],
        [8000, 9000],
        [9000, 10000],
    ]:
        raise ValueError("incorrect parent split bucket ranges")
    if policy["authorization"] != {
        "bulk_generation_authorized": False,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }:
        raise ValueError("dataset policy must not authorize generation, training, or clinical use")
    return policy


def parent_semantic_partition(parent_case_id: str) -> str:
    """Assign one parent semantic encounter before any language variants exist."""

    if not parent_case_id:
        raise ValueError("parent_case_id is required")
    policy = load_structured_extraction_dataset_policy()
    split = policy["split_policy"]
    forced = split["forced_parent_assignments"]
    if parent_case_id in forced:
        return forced[parent_case_id]
    material = f"{split['seed']}|{parent_case_id}".encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % 10000
    for partition in _PARTITIONS:
        lower, upper = split["partitions"][partition]
        if lower <= bucket < upper:
            return partition
    raise AssertionError("split bucket was not assigned")


def assert_target_corpus_eligible(target: dict[str, Any]) -> None:
    """Reject target states explicitly deferred from the v1 corpus."""

    diarrhoea = target.get("diarrhoea")
    if diarrhoea is not None and (
        diarrhoea.get("rehydration_stage") is not None
        or diarrhoea.get("post_rehydration") is not None
    ):
        raise ValueError(
            "longitudinal Plan B/C reassessment state is corpus-ineligible until an approved evaluator exists"
        )
