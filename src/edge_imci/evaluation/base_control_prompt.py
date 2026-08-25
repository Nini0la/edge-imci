"""Schema-informed prompting for an untuned structured-extraction control."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_INFORMED_BASE_PROMPT_ID = "edge-imci-schema-informed-base-control-v1"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def build_schema_informed_base_system_prompt(
    schema: Mapping[str, Any], example_output: Mapping[str, Any]
) -> str:
    """Give an untuned model the complete output contract and a valid example."""

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example_output)
    return (
        "Convert the PHC worker's findings into exactly one JSON object. Preserve "
        "explicitly stated positives, negatives, measurements, durations, and "
        "qualifiers. Use JSON null for UNKNOWN; never infer an unmentioned finding "
        "as negative. Include every required field, use only schema-defined fields, "
        "and output JSON only.\n\n"
        "Complete JSON Schema:\n"
        f"{_canonical_json(schema)}\n\n"
        "Example of a schema-valid output (format illustration only; do not copy its "
        "values unless the user's findings support them):\n"
        f"{_canonical_json(example_output)}"
    )


def load_schema_informed_base_system_prompt(
    schema_path: str | Path, example_output_path: str | Path
) -> tuple[str, dict[str, str]]:
    """Build the prompt from versioned artifacts and return reproducibility hashes."""

    schema_file = Path(schema_path)
    example_file = Path(example_output_path)
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    example = json.loads(example_file.read_text(encoding="utf-8"))
    if not isinstance(schema, dict) or not isinstance(example, dict):
        raise ValueError("base-control schema and example output must be JSON objects")
    prompt = build_schema_informed_base_system_prompt(schema, example)
    return prompt, {
        "prompt_id": SCHEMA_INFORMED_BASE_PROMPT_ID,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(schema_file.read_bytes()).hexdigest(),
        "example_output_sha256": hashlib.sha256(example_file.read_bytes()).hexdigest(),
    }


def apply_schema_informed_base_prompt(
    rows: Sequence[Mapping[str, Any]], prompt: str
) -> list[dict[str, Any]]:
    """Replace only the system message, without mutating frozen evaluation rows."""

    prepared: list[dict[str, Any]] = []
    for row in rows:
        copied = copy.deepcopy(dict(row))
        messages = copied.get("messages")
        if (
            not isinstance(messages, list)
            or len(messages) != 3
            or [message.get("role") for message in messages]
            != ["system", "user", "assistant"]
        ):
            raise ValueError("evaluation row must contain system, user, assistant messages")
        messages[0] = {"role": "system", "content": prompt}
        prepared.append(copied)
    return prepared
