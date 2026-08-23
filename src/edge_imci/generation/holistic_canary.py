"""Deterministic source-case selection for the first real teacher canary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import yaml
from jsonschema import Draft202012Validator

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_variants import ROOT, build_pilot_requests


CANARY_SELECTION_ID = "edge-imci-holistic-teacher-canary-selection-v1"
CANARY_SELECTION_PATH = (
    ROOT / "configs" / "generation" / "holistic_teacher_canary_selection_v1.json"
)
CANARY_SELECTION_YAML_PATH = CANARY_SELECTION_PATH.with_suffix(".yaml")
CANARY_SELECTION_SCHEMA_PATH = CANARY_SELECTION_PATH.with_name(
    "holistic_teacher_canary_selection_v1.schema.json"
)
SEMANTIC_CASES_PATH = ROOT / "data" / "golden" / "holistic_product_v1" / "semantic_cases.jsonl"
BAKEOFF_CONFIG_PATH = ROOT / "configs" / "generation" / "holistic_teacher_bakeoff_v1.json"
VARIANT_CONTRACT_PATH = ROOT / "configs" / "generation" / "holistic_language_variant_contract_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _known_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_known_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_known_count(item) for item in value)
    return int(value is not None)


def _evaluation(record: dict[str, Any]) -> dict[str, Any]:
    evaluation = record["expected"].get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError(f"case has no holistic evaluation: {record['golden_case_id']}")
    return evaluation


def _select_lowest(
    records: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]
) -> str:
    matches = sorted(record["golden_case_id"] for record in records if predicate(record))
    if not matches:
        raise ValueError("deterministic canary stratum has no matching case")
    return matches[0]


def _select_highest_known(
    records: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]
) -> str:
    matches = [record for record in records if predicate(record)]
    if not matches:
        raise ValueError("deterministic canary stratum has no matching case")
    ranked = sorted(
        matches,
        key=lambda record: (
            -_known_count(record["input"]["encounter"]),
            record["golden_case_id"],
        ),
    )
    return ranked[0]["golden_case_id"]


def derive_canary_case_ids(records: list[dict[str, Any]] | None = None) -> list[str]:
    rows = records or load_holistic_golden_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)

    def tagged(record: dict[str, Any], *tags: str) -> bool:
        return set(tags).issubset(record["coverage"])

    return [
        _select_lowest(
            rows,
            lambda record: tagged(record, "complete", "low_severity", "explicit_negative"),
        ),
        _select_lowest(
            rows,
            lambda record: tagged(
                record,
                "complete",
                "bronchodilator_reassessment",
                "complete_post_reassessment",
            ),
        ),
        _select_highest_known(
            rows,
            lambda record: tagged(record, "complete", "all_pathways")
            and not _evaluation(record)["urgent_action_required"],
        ),
        _select_highest_known(
            rows,
            lambda record: tagged(record, "complete", "all_pathways")
            and _evaluation(record)["urgent_action_required"],
        ),
        _select_highest_known(
            rows,
            lambda record: tagged(record, "incomplete", "multiple_omissions"),
        ),
        _select_lowest(
            rows,
            lambda record: tagged(record, "incomplete", "urgent_incomplete"),
        ),
    ]


def load_canary_selection() -> dict[str, Any]:
    selection = _load_json(CANARY_SELECTION_PATH)
    Draft202012Validator(_load_json(CANARY_SELECTION_SCHEMA_PATH)).validate(selection)
    if selection["selection_id"] != CANARY_SELECTION_ID:
        raise ValueError("incorrect teacher canary selection ID")
    expected_pins = {
        "semantic_cases_sha256": _sha256(SEMANTIC_CASES_PATH),
        "teacher_bakeoff_config_sha256": _sha256(BAKEOFF_CONFIG_PATH),
        "language_variant_contract_sha256": _sha256(VARIANT_CONTRACT_PATH),
    }
    if selection["source_pins"] != expected_pins:
        raise ValueError("teacher canary source pins have drifted")
    selected = [item["selected_case_id"] for item in selection["strata"]]
    if selected != derive_canary_case_ids():
        raise ValueError("recorded canary cases differ from deterministic selection")
    if len(selected) != len(set(selected)):
        raise ValueError("teacher canary case IDs must be unique")
    return selection


def build_canary_source_requests() -> list[dict[str, Any]]:
    """Return the selected 12 blind requests without authorizing or calling a teacher."""

    selection = load_canary_selection()
    case_ids = [item["selected_case_id"] for item in selection["strata"]]
    requests = {
        (item["semantic_case_id"], item["strategy_id"]): item
        for item in build_pilot_requests()
    }
    selected = [
        requests[(case_id, strategy_id)]
        for case_id in case_ids
        for strategy_id in selection["prompt_strategy_ids"]
    ]
    if len(selected) != selection["expected_request_count"]:
        raise ValueError("teacher canary request count differs from selection")
    if any(item["generation_authorized"] for item in selected):
        raise ValueError("teacher canary selection must not authorize generation")
    return selected


def write_yaml_mirror() -> None:
    selection = _load_json(CANARY_SELECTION_PATH)
    CANARY_SELECTION_YAML_PATH.write_text(
        f"# Generated from {CANARY_SELECTION_PATH.relative_to(ROOT)}; edit canonical JSON.\n"
        + yaml.safe_dump(selection, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
