"""Deterministic projection into the model-facing encounter contract.

The model contract contains observations and supported encounter context only.
It deliberately excludes identities, oracle outputs, rules, actions, provenance,
and presentation text. JSON ``null`` remains UNKNOWN and is never converted to
``false``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from edge_imci.generation.holistic_golden import encounter_from_dict
from edge_imci.schemas.holistic import HOLISTIC_SCHEMA_VERSION, HolisticEncounter


ROOT = Path(
    os.environ.get("EDGE_IMCI_REPO_ROOT", Path(__file__).resolve().parents[3])
).resolve()
MODEL_FACING_ENCOUNTER_SCHEMA_ID = "edge-imci-model-facing-encounter-v1"
MODEL_TARGET_EXPORTER_ID = "edge-imci-model-target-exporter-v1"
MODEL_FACING_ENCOUNTER_SCHEMA_PATH = (
    ROOT / "configs" / "model_io" / "model_facing_encounter_v1.schema.json"
)
_INTERNAL_ENCOUNTER_FIELDS = frozenset({"encounter_id", "schema_version"})


def _load_schema() -> dict[str, Any]:
    schema = json.loads(MODEL_FACING_ENCOUNTER_SCHEMA_PATH.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ValueError("model-facing encounter schema must be a JSON object")
    return schema


def model_facing_schema_sha256() -> str:
    """Return the byte-level pin for the versioned model-facing schema."""

    return hashlib.sha256(MODEL_FACING_ENCOUNTER_SCHEMA_PATH.read_bytes()).hexdigest()


def validate_model_facing_encounter(target: dict[str, Any]) -> None:
    """Validate a target against the public model-facing contract."""

    try:
        json.dumps(target, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("model-facing encounter must be strict JSON data") from exc
    Draft202012Validator(_load_schema()).validate(target)


def project_model_facing_encounter(semantic_record: dict[str, Any]) -> dict[str, Any]:
    """Project one frozen semantic record into a leakage-free model target.

    The projection is intentionally a strict allow-by-schema operation. Only
    the runtime identity and internal schema version are removed from the
    frozen encounter; any future unreviewed source field makes validation fail
    instead of silently entering the learned target.
    """

    try:
        encounter = semantic_record["input"]["encounter"]
    except (KeyError, TypeError) as exc:
        raise ValueError("semantic record does not contain input.encounter") from exc
    if not isinstance(encounter, dict):
        raise ValueError("semantic record input.encounter must be an object")
    target = {
        key: copy.deepcopy(value)
        for key, value in encounter.items()
        if key not in _INTERNAL_ENCOUNTER_FIELDS
    }
    validate_model_facing_encounter(target)
    return target


def model_target_to_holistic_encounter(
    target: dict[str, Any], *, encounter_id: str
) -> HolisticEncounter:
    """Validate and adapt a predicted target to the existing clinical engine.

    Scope and unsupported treatment-stage checks remain deterministic in the
    existing internal constructor. In particular, truthful ages outside the
    supported 2-to-under-60-month range are represented by the public schema
    and rejected here rather than being altered by the extractor.
    """

    if not encounter_id:
        raise ValueError("encounter_id is required at the adapter boundary")
    validate_model_facing_encounter(target)
    payload = copy.deepcopy(target)
    payload["encounter_id"] = encounter_id
    payload["schema_version"] = HOLISTIC_SCHEMA_VERSION
    return encounter_from_dict(payload)


def canonical_model_target_json(target: dict[str, Any]) -> str:
    """Return a stable, compact JSON serialization suitable for SFT messages."""

    validate_model_facing_encounter(target)
    return json.dumps(
        target,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
