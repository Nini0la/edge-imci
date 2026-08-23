"""Controlled whole-encounter PHC input variants over frozen golden language.

This module builds production-shaped teacher requests and validates returned
user-language candidates. It never calls a model. The approved assistant target
and semantic alignment are attached deterministically from the frozen parent.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite


ROOT = Path(__file__).resolve().parents[3]

VARIANT_CONTRACT_ID = "edge-imci-holistic-language-variant-contract-v1"
CANDIDATE_SCHEMA_ID = "edge-imci-holistic-language-variant-candidate-v1"
VARIANT_RECORD_SCHEMA_ID = "edge-imci-holistic-language-variant-record-v1"
ATTEMPT_SCHEMA_ID = "edge-imci-holistic-teacher-attempt-v1"
VARIANT_VALIDATOR_ID = "edge-imci-holistic-language-variant-validator-v1"

SEMANTIC_CASES_SHA256 = "9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f"
FROZEN_LANGUAGE_SHA256 = "9b9c1b67a73c2e5763f5507bc55e618d28149bdee6c7c4329ecc8a868e3860a0"
RESPONSE_GRAMMAR_SHA256 = "1fd793607f077cd4d44a9cf73349803d32ef1e69e3aab82d00fe0bda330f4873"

CONTRACT_PATH = ROOT / "configs" / "generation" / "holistic_language_variant_contract_v1.json"
CONTRACT_YAML_PATH = CONTRACT_PATH.with_suffix(".yaml")
PILOT_CONFIG_PATH = ROOT / "configs" / "generation" / "holistic_teacher_bakeoff_v1.json"
PILOT_CONFIG_YAML_PATH = PILOT_CONFIG_PATH.with_suffix(".yaml")
CANDIDATE_SCHEMA_PATH = (
    ROOT / "configs" / "generation" / "holistic_language_variant_candidate_v1.schema.json"
)
VARIANT_RECORD_SCHEMA_PATH = (
    ROOT / "configs" / "generation" / "holistic_language_variant_record_v1.schema.json"
)
ATTEMPT_SCHEMA_PATH = (
    ROOT / "configs" / "generation" / "holistic_teacher_attempt_v1.schema.json"
)

_INTERNAL_MARKERS = (
    "IMCI-MSC-",
    "edge-imci-",
    "source_value_sha256",
    "fact_evidence",
    "candidate_schema_id",
    "patient_facts.",
    "danger_signs.",
    "respiratory.",
    "diarrhoea.",
    "fever.",
    "ear.",
)

_ENCOUNTER_PROVENANCE_FIELDS = frozenset({"encounter_id", "schema_version"})


@dataclass(frozen=True)
class CandidateValidation:
    deterministic_pass: bool
    error_codes: tuple[str, ...]
    requires_human_semantic_review: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "deterministic_pass": self.deterministic_pass,
            "error_codes": list(self.error_codes),
            "requires_human_semantic_review": self.requires_human_semantic_review,
        }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _validator(
    schema_path: Path, *, referenced_schema_paths: Iterable[Path] = ()
) -> Draft202012Validator:
    schema = _load_json(schema_path)
    registry = Registry()
    for referenced_path in referenced_schema_paths:
        referenced = _load_json(referenced_path)
        registry = registry.with_resource(
            referenced["$id"], Resource.from_contents(referenced)
        )
    return Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


def _clinical_encounter(semantic_record: dict[str, Any]) -> dict[str, Any]:
    """Return only teacher-renderable clinical content from the frozen encounter."""

    encounter = semantic_record["input"]["encounter"]
    return {
        key: value
        for key, value in encounter.items()
        if key not in _ENCOUNTER_PROVENANCE_FIELDS
    }


def load_variant_contract() -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    if contract.get("contract_id") != VARIANT_CONTRACT_ID:
        raise ValueError("incorrect holistic language variant contract ID")
    if contract.get("status") != "PROPOSED_FOR_PROJECT_OWNER_REVIEW":
        raise ValueError("variant contract must remain proposed until separately approved")
    pins = contract.get("source_pins", {})
    expected = {
        "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
        "frozen_language_renderings_sha256": FROZEN_LANGUAGE_SHA256,
        "response_grammar_sha256": RESPONSE_GRAMMAR_SHA256,
    }
    for key, value in expected.items():
        if pins.get(key) != value:
            raise ValueError(f"variant contract has incorrect source pin {key}")
    no_waste = contract.get("no_waste_policy", {})
    if no_waste.get("mock_teacher_allowed") is not False:
        raise ValueError("variant contract must forbid mock teachers")
    if no_waste.get("persist_test_mutations") is not False:
        raise ValueError("variant contract must forbid persistence of test mutations")
    if no_waste.get("teacher_called_during_infrastructure_validation") is not False:
        raise ValueError("infrastructure validation must not call a teacher")
    if contract.get("validation_policy", {}).get("training_eligibility_before_dataset_approval") is not False:
        raise ValueError("variant contract cannot authorize training eligibility")
    return contract


def load_pilot_config() -> dict[str, Any]:
    config = _load_json(PILOT_CONFIG_PATH)
    if config.get("experiment_id") != "holistic-teacher-prompt-bakeoff-v1":
        raise ValueError("incorrect holistic teacher bake-off experiment ID")
    if config.get("status") != "BLOCKED_PENDING_TEACHER_BUDGET_AND_REMOTE_CALL_AUTHORIZATION":
        raise ValueError("pilot config has incorrect authorization state")
    if config.get("mock_teacher") is not False or config.get("actual_generation_authorized") is not False:
        raise ValueError("pilot infrastructure must not authorize generation")
    if config.get("teacher_models") != []:
        raise ValueError("teacher models require explicit project-owner authorization")
    source = config.get("source", {})
    if source.get("semantic_cases_sha256") != SEMANTIC_CASES_SHA256:
        raise ValueError("pilot config has incorrect semantic source hash")
    if source.get("language_renderings_sha256") != FROZEN_LANGUAGE_SHA256:
        raise ValueError("pilot config has incorrect frozen language hash")
    for pin in config.get("artifact_pins", []):
        path = ROOT / pin["path"]
        if pin.get("sha256") != _sha256(path):
            raise ValueError(f"pilot artifact hash mismatch: {path}")
    strategies = config.get("prompt_strategies", [])
    if len(strategies) != 2:
        raise ValueError("pilot config must define exactly two input-rendering strategies")
    for strategy in strategies:
        path = ROOT / strategy["prompt_path"]
        if not strategy.get("prompt_id") or not strategy.get("prompt_version"):
            raise ValueError("pilot prompts require stable IDs and versions")
        if strategy.get("prompt_sha256") != _sha256(path):
            raise ValueError(f"prompt hash mismatch: {path}")
        if strategy.get("teacher_output") != "USER_SUBMISSION_AND_FACT_EVIDENCE_ONLY":
            raise ValueError("pilot teacher must not generate the assistant target")
        if strategy.get("assistant_target") != "ATTACH_FROZEN_CANONICAL_RESPONSE":
            raise ValueError("pilot must attach the frozen assistant target")
    return config


def _flatten_known(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        items: list[tuple[str, Any]] = []
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else key
            items.extend(_flatten_known(value[key], child))
        return items
    if isinstance(value, list):
        items = []
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            items.extend(_flatten_known(item, child))
        return items
    return [(prefix, value)]


def source_fact_specs(semantic_record: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"fact_id": fact_id, "source_value_sha256": _canonical_hash(value)}
        for fact_id, value in _flatten_known(_clinical_encounter(semantic_record))
    ]


def build_source_package(
    semantic_record: dict[str, Any], parent_language: dict[str, Any], strategy_id: str
) -> dict[str, Any]:
    if semantic_record["golden_case_id"] != parent_language["golden_case_id"]:
        raise ValueError("semantic and language parent IDs differ")
    return {
        "candidate_schema_id": CANDIDATE_SCHEMA_ID,
        "semantic_case_id": semantic_record["golden_case_id"],
        "strategy_id": strategy_id,
        "structured_encounter": _clinical_encounter(semantic_record),
        "required_fact_evidence": source_fact_specs(semantic_record),
        "unknown_values_are_not_negative": True,
        "assistant_response_attached_after_validation": True,
        "assistant_response_is_not_teacher_output": True,
        "output_shape": {
            "candidate_schema_id": CANDIDATE_SCHEMA_ID,
            "semantic_case_id": semantic_record["golden_case_id"],
            "strategy_id": strategy_id,
            "user_submission": "string",
            "fact_evidence": [
                {
                    "fact_id": "string",
                    "source_value_sha256": "64 lowercase hex characters",
                    "evidence_text": "exact substring of user_submission",
                }
            ],
        },
    }


def build_pilot_requests() -> list[dict[str, Any]]:
    load_variant_contract()
    config = load_pilot_config()
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    parents = load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    if len(parents) != config["source"]["case_count"]:
        raise ValueError("pilot case count differs from the frozen full language layer")
    requests: list[dict[str, Any]] = []
    for strategy in config["prompt_strategies"]:
        prompt_template = (ROOT / strategy["prompt_path"]).read_text(encoding="utf-8")
        if prompt_template.count("{{SOURCE_PACKAGE_JSON}}") != 1:
            raise ValueError("prompt template must contain one source-package placeholder")
        for parent in parents:
            case_id = parent["golden_case_id"]
            package = build_source_package(semantics[case_id], parent, strategy["strategy_id"])
            rendered_prompt = prompt_template.replace(
                "{{SOURCE_PACKAGE_JSON}}",
                json.dumps(package, ensure_ascii=False, sort_keys=True),
            )
            request_identity = {
                "experiment_id": config["experiment_id"],
                "semantic_case_id": case_id,
                "strategy_id": strategy["strategy_id"],
                "prompt_id": strategy["prompt_id"],
                "prompt_version": strategy["prompt_version"],
                "prompt_sha256": strategy["prompt_sha256"],
                "source_package_sha256": _canonical_hash(package),
            }
            request_sha256 = _canonical_hash(
                {**request_identity, "rendered_prompt": rendered_prompt}
            )
            requests.append(
                {
                    "request_id": f"{case_id}__{strategy['strategy_id']}",
                    **request_identity,
                    "request_sha256": request_sha256,
                    "source_package": package,
                    "rendered_prompt": rendered_prompt,
                    "teacher_model": None,
                    "generation_authorized": False,
                }
            )
    return requests


def parse_candidate_output(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```json") and cleaned.endswith("```"):
        cleaned = cleaned[7:-3].strip()
    elif cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("teacher candidate must be one JSON object")
    return value


def _normalized_surface(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate_candidate(
    candidate: dict[str, Any],
    semantic_record: dict[str, Any],
    parent_language: dict[str, Any],
    strategy_id: str,
) -> CandidateValidation:
    errors: list[str] = []
    schema_errors = list(_validator(CANDIDATE_SCHEMA_PATH).iter_errors(candidate))
    if schema_errors:
        return CandidateValidation(False, ("SCHEMA_INVALID",))

    case_id = semantic_record["golden_case_id"]
    if candidate["semantic_case_id"] != case_id or parent_language["golden_case_id"] != case_id:
        errors.append("CANDIDATE_ID_MISMATCH")
    if candidate["strategy_id"] != strategy_id:
        errors.append("STRATEGY_ID_MISMATCH")

    expected = {
        item["fact_id"]: item["source_value_sha256"]
        for item in source_fact_specs(semantic_record)
    }
    evidence_items = candidate["fact_evidence"]
    actual_ids = [item["fact_id"] for item in evidence_items]
    if len(actual_ids) != len(set(actual_ids)):
        errors.append("FACT_ID_DUPLICATE")
    if set(actual_ids) != set(expected):
        errors.append("FACT_SET_MISMATCH")
    for item in evidence_items:
        fact_id = item["fact_id"]
        if fact_id in expected and item["source_value_sha256"] != expected[fact_id]:
            errors.append("FACT_VALUE_HASH_MISMATCH")
        if item["evidence_text"] not in candidate["user_submission"]:
            errors.append("EVIDENCE_SPAN_MISSING")

    submission = candidate["user_submission"]
    if any(marker.casefold() in submission.casefold() for marker in _INTERNAL_MARKERS):
        errors.append("INTERNAL_IDENTIFIER_LEAKAGE")
    if any(heading in submission for heading in ("Classifications:", "Management:", "Immediate management:")):
        errors.append("ASSISTANT_CONTENT_IN_USER_SUBMISSION")
    canonical_user = parent_language["conversation"][0]["content"]
    if _normalized_surface(submission) == _normalized_surface(canonical_user):
        errors.append("DUPLICATE_CANONICAL_USER_SUBMISSION")

    return CandidateValidation(not errors, tuple(dict.fromkeys(errors)))


def build_variant_record(
    *,
    candidate: dict[str, Any],
    semantic_record: dict[str, Any],
    parent_language: dict[str, Any],
    request: dict[str, Any],
    generation_run_id: str,
    attempt_id: str,
    teacher_provider: str,
    teacher_model: str,
    teacher_snapshot: str,
    renderer_git_commit: str,
    generated_at: str,
) -> dict[str, Any]:
    validation = validate_candidate(
        candidate,
        semantic_record,
        parent_language,
        request["strategy_id"],
    )
    if not validation.deterministic_pass:
        raise ValueError(f"candidate failed deterministic validation: {validation.error_codes}")
    record = {
        "record_schema_id": VARIANT_RECORD_SCHEMA_ID,
        "variant_id": f"{candidate['semantic_case_id']}__{candidate['strategy_id']}__v1",
        "semantic_case_id": candidate["semantic_case_id"],
        "status": "PENDING_HUMAN_REVIEW",
        "parent_source": {
            "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
            "frozen_language_renderings_sha256": FROZEN_LANGUAGE_SHA256,
            "parent_rendering_id": parent_language["rendering_id"],
        },
        "conversation": [
            {"role": "user", "content": candidate["user_submission"]},
            {
                "role": "assistant",
                "content": parent_language["conversation"][1]["content"],
            },
        ],
        "alignment": parent_language["alignment"],
        "generation_provenance": {
            "generation_run_id": generation_run_id,
            "attempt_id": attempt_id,
            "teacher_provider": teacher_provider,
            "teacher_model": teacher_model,
            "teacher_snapshot": teacher_snapshot,
            "strategy_id": candidate["strategy_id"],
            "prompt_id": request["prompt_id"],
            "prompt_version": request["prompt_version"],
            "prompt_sha256": request["prompt_sha256"],
            "request_sha256": request["request_sha256"],
            "renderer_git_commit": renderer_git_commit,
            "generated_at": generated_at,
            "variant_contract_id": VARIANT_CONTRACT_ID,
            "validator_id": VARIANT_VALIDATOR_ID,
        },
        "validation": validation.to_dict(),
        "review": {
            "semantic_faithfulness": "PENDING",
            "naturalness": "PENDING",
            "phc_suitability": "PENDING",
            "reviewer": None,
        },
        "eligibility": {
            "teacher_bakeoff": True,
            "corpus_candidate": False,
            "training": False,
        },
    }
    _validator(VARIANT_RECORD_SCHEMA_PATH).validate(record)
    if record["conversation"][1] != parent_language["conversation"][1]:
        raise ValueError("variant record changed the frozen assistant target")
    if record["alignment"] != parent_language["alignment"]:
        raise ValueError("variant record changed the frozen semantic alignment")
    return record


def validate_attempt_record(record: dict[str, Any]) -> None:
    """Validate one persisted real-teacher attempt, including its candidate."""

    _validator(
        ATTEMPT_SCHEMA_PATH,
        referenced_schema_paths=(CANDIDATE_SCHEMA_PATH,),
    ).validate(record)


def summarize_attempts(attempts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(attempts)
    configurations: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        configurations.setdefault(row["configuration_id"], []).append(row)
    summaries = []
    for configuration_id in sorted(configurations):
        items = configurations[configuration_id]
        deterministic_passes = sum(
            item["validation"]["deterministic_pass"] for item in items
        )
        approved = sum(item["status"] == "APPROVED_CORPUS_CANDIDATE" for item in items)
        errors: dict[str, int] = {}
        for item in items:
            for code in item["validation"]["error_codes"]:
                errors[code] = errors.get(code, 0) + 1
        summaries.append(
            {
                "configuration_id": configuration_id,
                "attempt_count": len(items),
                "deterministic_pass_count": deterministic_passes,
                "deterministic_pass_rate": deterministic_passes / len(items),
                "human_approved_count": approved,
                "error_code_counts": errors,
            }
        )
    return {
        "attempt_count": len(rows),
        "configuration_count": len(configurations),
        "configurations": summaries,
        "winner_selected": False,
        "bulk_generation_authorized": False,
        "training_authorized": False,
    }


def write_yaml_mirrors() -> None:
    for source, mirror in (
        (CONTRACT_PATH, CONTRACT_YAML_PATH),
        (PILOT_CONFIG_PATH, PILOT_CONFIG_YAML_PATH),
    ):
        value = _load_json(source)
        mirror.write_text(
            f"# Generated from {source.relative_to(ROOT)}; edit canonical JSON.\n"
            + yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=100),
            encoding="utf-8",
        )
