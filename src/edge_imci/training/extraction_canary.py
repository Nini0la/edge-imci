"""Promote reviewed teacher attempts into a structured-extraction canary.

This module performs no remote calls. It reuses three explicitly approved PHC
submissions, preserves their frozen language-variant records for audit, and
pairs only the user message with a deterministic model-facing target.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import (
    DEFAULT_JSONL_PATH,
    SUITE_ID,
    load_holistic_golden_suite,
)
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_variants import (
    FROZEN_LANGUAGE_SHA256,
    SEMANTIC_CASES_SHA256,
    VARIANT_CONTRACT_ID,
    VARIANT_RECORD_SCHEMA_ID,
    VARIANT_RECORD_SCHEMA_PATH,
    VARIANT_VALIDATOR_ID,
    source_fact_specs,
)
from edge_imci.training.dataset_policy import DATASET_POLICY_ID, SPLIT_POLICY_ID
from edge_imci.training.structured_extraction import (
    STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID,
    build_structured_extraction_record,
    format_structured_extraction_messages,
)


ROOT = Path(__file__).resolve().parents[3]
CANARY_ID = "edge-imci-structured-extraction-canary-v1"
APPROVAL_ID = "edge-imci-structured-extraction-canary-approval-v1"
APPROVAL_PATH = (
    ROOT / "configs" / "training" / "structured_extraction_canary_approval_v1.json"
)
OUTPUT_DIR = ROOT / "data" / "canary" / "structured_extraction_v1"
LANGUAGE_VARIANTS_PATH = OUTPUT_DIR / "language_variants.jsonl"
CANONICAL_RECORDS_PATH = OUTPUT_DIR / "canonical_records.jsonl"
CHAT_MESSAGES_PATH = OUTPUT_DIR / "chat_messages.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
REVIEW_PATH = ROOT / "docs" / "structured_extraction_canary_samples_v1.md"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _canonical_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for row in rows
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_repo_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("canary source path escapes the repository") from exc
    return path


def load_canary_approval() -> dict[str, Any]:
    approval = _load_json(APPROVAL_PATH)
    expected = {
        "approval_id": APPROVAL_ID,
        "status": "APPROVED_FOR_EXTRACTION_CANARY_ONLY",
        "authority": "PROJECT_OWNER_DECISION",
        "clinical_rule_change": False,
        "bulk_generation_authorized": False,
        "training_authorized": False,
    }
    for key, value in expected.items():
        if approval.get(key) != value:
            raise ValueError(f"incorrect extraction canary approval {key}")
    attempts = approval.get("approved_attempts", [])
    if len(attempts) != 3:
        raise ValueError("extraction canary must contain exactly three approved attempts")
    case_ids = [item.get("semantic_case_id") for item in attempts]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("extraction canary approval contains duplicate semantic cases")
    return approval


def _approved_language_variant(
    *,
    approval_item: dict[str, Any],
    approval: dict[str, Any],
    semantic_record: dict[str, Any],
    parent_language: dict[str, Any],
) -> dict[str, Any]:
    terminal = _load_json(_safe_repo_path(approval_item["attempt_path"]))
    case_id = approval_item["semantic_case_id"]
    if terminal.get("semantic_case_id") != case_id:
        raise ValueError("approved attempt semantic case does not match approval")
    if terminal.get("status") != "PENDING_HUMAN_REVIEW":
        raise ValueError("only a deterministically valid reviewable attempt may be promoted")
    if terminal.get("validation") != {
        "deterministic_pass": True,
        "error_codes": [],
        "requires_human_semantic_review": True,
    }:
        raise ValueError("approved attempt did not pass deterministic validation")
    prompt = terminal["prompt"]
    teacher = terminal["teacher"]
    candidate = terminal["candidate"]
    source_hashes = {
        item["fact_id"]: item["source_value_sha256"]
        for item in source_fact_specs(semantic_record)
    }
    record = {
        "record_schema_id": VARIANT_RECORD_SCHEMA_ID,
        "variant_id": (
            f"{case_id}__natural-complete-prompt-v"
            f"{prompt['prompt_version'].replace('.', '-')}__v1"
        ),
        "semantic_case_id": case_id,
        "status": "APPROVED_CORPUS_CANDIDATE",
        "parent_source": {
            "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
            "frozen_language_renderings_sha256": FROZEN_LANGUAGE_SHA256,
            "parent_rendering_id": parent_language["rendering_id"],
        },
        "conversation": [
            {"role": "user", "content": candidate["user_submission"]},
            copy.deepcopy(parent_language["conversation"][1]),
        ],
        "fact_evidence": [
            {**copy.deepcopy(item), "source_value_sha256": source_hashes[item["fact_id"]]}
            for item in candidate["fact_evidence"]
        ],
        "alignment": copy.deepcopy(parent_language["alignment"]),
        "generation_provenance": {
            "generation_run_id": terminal["generation_run_id"],
            "attempt_id": terminal["attempt_id"],
            "teacher_provider": teacher["provider"],
            "teacher_model": teacher["model"],
            "teacher_snapshot": teacher["snapshot"],
            "strategy_id": prompt["strategy_id"],
            "prompt_id": prompt["prompt_id"],
            "prompt_version": prompt["prompt_version"],
            "prompt_sha256": prompt["prompt_sha256"],
            "request_sha256": terminal["request_sha256"],
            "renderer_git_commit": approval["provenance_qualification"]["renderer_git_commit"],
            "generated_at": terminal["completed_at"],
            "variant_contract_id": VARIANT_CONTRACT_ID,
            "validator_id": VARIANT_VALIDATOR_ID,
        },
        "validation": copy.deepcopy(terminal["validation"]),
        "review": {
            **copy.deepcopy(approval_item["review"]),
            "reviewer": approval["approved_by"],
        },
        "eligibility": {
            "teacher_bakeoff": True,
            "corpus_candidate": True,
            "training": False,
        },
    }
    schema = _load_json(VARIANT_RECORD_SCHEMA_PATH)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(record)
    return record


def build_extraction_canary() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Build reviewed variants, canonical records, and chat messages in memory."""

    approval = load_canary_approval()
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    language = {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }
    variants: list[dict[str, Any]] = []
    canonical: list[dict[str, Any]] = []
    chats: list[dict[str, Any]] = []
    for approved in approval["approved_attempts"]:
        case_id = approved["semantic_case_id"]
        variant = _approved_language_variant(
            approval_item=approved,
            approval=approval,
            semantic_record=semantics[case_id],
            parent_language=language[case_id],
        )
        extraction = build_structured_extraction_record(
            semantic_record=semantics[case_id],
            variant_record=variant,
            variant_style="NATURAL_CONVERSATIONAL_ENGLISH",
        )
        messages = format_structured_extraction_messages(extraction)
        frozen_assistant = variant["conversation"][1]["content"]
        if frozen_assistant in json.dumps(extraction, ensure_ascii=False):
            raise ValueError("frozen assistant response leaked into extraction record")
        if json.loads(messages[-1]["content"]) != extraction["target"]:
            raise ValueError("chat assistant message is not the canonical JSON target")
        variants.append(variant)
        canonical.append(extraction)
        chats.append(
            {
                "example_id": extraction["example_id"],
                "source_case_id": case_id,
                "variant_id": variant["variant_id"],
                "partition": extraction["partition"],
                "messages": messages,
            }
        )
    if len({row["source_case_id"] for row in canonical}) != len(canonical):
        raise ValueError("canary contains duplicate parent semantic encounters")
    return variants, canonical, chats


def _render_review(
    canonical: list[dict[str, Any]], chats: list[dict[str, Any]]
) -> str:
    lines = [
        "# EdgeIMCI structured-extraction canary samples v1",
        "",
        "> **Authority:** `PROJECT_OWNER_APPROVED_CANARY` · **Lifecycle:** `APPROVED_EXTRACTION_CANARY` · Three reused teacher submissions; no remote calls, bulk generation or training authorization.",
        "",
        "These samples demonstrate the new primary learning pair. The user message comes from an already reviewed teacher attempt. The assistant message is deterministic canonical JSON projected from the frozen semantic source; it contains no classification, action, urgency or frozen assistant prose.",
        "",
    ]
    chat_by_id = {row["example_id"]: row for row in chats}
    for index, record in enumerate(canonical, start=1):
        chat = chat_by_id[record["example_id"]]
        lines.extend(
            [
                f"## {index}. `{record['source_case_id']}`",
                "",
                f"Partition: `{record['partition']}`  ",
                f"Variant: `{record['variant_id']}`",
                "",
                "### Teacher-generated PHC submission",
                "",
                chat["messages"][1]["content"],
                "",
                "### Expected model response",
                "",
                "```json",
                json.dumps(record["target"], ensure_ascii=False, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Serialization boundary",
            "",
            "`chat_messages.jsonl` contains model-neutral system/user/assistant messages. It does not apply the Qwen tokenizer or chat template. That model-specific transformation remains a deterministic training-configuration step.",
            "",
        ]
    )
    return "\n".join(lines)


def write_extraction_canary() -> dict[str, Any]:
    variants, canonical, chats = build_extraction_canary()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payloads = {
        LANGUAGE_VARIANTS_PATH: _canonical_jsonl(variants),
        CANONICAL_RECORDS_PATH: _canonical_jsonl(canonical),
        CHAT_MESSAGES_PATH: _canonical_jsonl(chats),
    }
    for path, value in payloads.items():
        path.write_text(value, encoding="utf-8")
    REVIEW_PATH.write_text(_render_review(canonical, chats), encoding="utf-8")
    manifest = {
        "canary_id": CANARY_ID,
        "status": "APPROVED_EXTRACTION_CANARY",
        "approval_id": APPROVAL_ID,
        "semantic_suite_id": SUITE_ID,
        "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
        "semantic_source_file_sha256": _sha256_bytes(DEFAULT_JSONL_PATH.read_bytes()),
        "dataset_policy_id": DATASET_POLICY_ID,
        "split_policy_id": SPLIT_POLICY_ID,
        "record_schema_id": STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID,
        "record_count": len(canonical),
        "parent_case_count": len({row["source_case_id"] for row in canonical}),
        "partition_counts": {
            partition: sum(row["partition"] == partition for row in canonical)
            for partition in ("TRAIN", "VALIDATION", "TEST")
        },
        "assets": {
            str(path.relative_to(ROOT)): {
                "sha256": _sha256_bytes(value.encode("utf-8")),
                "record_count": len(variants if path == LANGUAGE_VARIANTS_PATH else canonical),
            }
            for path, value in payloads.items()
        },
        "validation": {
            "approved_language_only": True,
            "parent_split_inheritance": True,
            "frozen_assistant_response_excluded_from_sft": True,
            "target_is_deterministic_projection": True,
            "chat_assistant_is_json_target_only": True,
        },
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
    write_extraction_canary()
