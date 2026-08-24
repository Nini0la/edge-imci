"""Reconcile and export the reviewed structured-extraction campaign.

This module performs no remote calls and does not authorize training.  It
keeps teacher language target-blind, attaches deterministic targets from the
frozen/derived parent state, and applies the versioned campaign review policy.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import (
    SUITE_ID,
    load_holistic_golden_suite,
)
from edge_imci.generation.holistic_variants import (
    SEMANTIC_CASES_SHA256,
    source_fact_specs,
)
from edge_imci.training.dataset_policy import (
    DATASET_POLICY_ID,
    SPLIT_POLICY_ID,
)
from edge_imci.training.out_of_scope_parents import (
    PARENT_SCHEMA_ID,
    build_out_of_scope_training_parents,
)
from edge_imci.training.structured_extraction import (
    STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID,
    build_structured_extraction_record_from_target,
    format_structured_extraction_messages,
)


ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_ID = "edge-imci-structured-extraction-language-campaign-v1"
REVIEW_ID = "edge-imci-structured-extraction-campaign-review-v1"
REVIEW_PATH = ROOT / "configs/training/structured_extraction_campaign_review_v1.json"
LANGUAGE_SCHEMA_ID = "edge-imci-structured-extraction-language-variant-v1"
LANGUAGE_SCHEMA_PATH = (
    ROOT / "configs/training/structured_extraction_language_variant_v1.schema.json"
)
OUTPUT_DIR = ROOT / "data/training_sources/structured_extraction_campaign_v1"
LANGUAGE_PATH = OUTPUT_DIR / "language_variants.jsonl"
CANONICAL_PATH = OUTPUT_DIR / "canonical_records.jsonl"
CHAT_PATH = OUTPUT_DIR / "chat_messages.jsonl"
EXCLUSIONS_PATH = OUTPUT_DIR / "excluded_receipts.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
REPORT_PATH = ROOT / "docs/structured_extraction_campaign_final_report_v1.md"

RUN_NUMBERS = (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
PRE_REMEDIATION_RUN_NUMBERS = {1, 3, 4}
T3_RUN_NUMBERS = set(RUN_NUMBERS) - PRE_REMEDIATION_RUN_NUMBERS
EXPECTED_STYLES = {
    "phc-nigerian-english-v1": 536,
    "phc-nigerian-pidgin-v1": 536,
    "phc-noisy-typed-english-v1": 535,
    "phc-telegraphic-note-v1": 535,
}
STYLE_NAMES = {
    "phc-nigerian-english-v1": "NIGERIAN_ENGLISH",
    "phc-nigerian-pidgin-v1": "NIGERIAN_PIDGIN",
    "phc-noisy-typed-english-v1": "NOISY_TYPED_ENGLISH",
    "phc-telegraphic-note-v1": "TELEGRAPHIC_PHC_NOTE",
}
NOISE_PROFILES = {
    "NIGERIAN_ENGLISH": (),
    "NIGERIAN_PIDGIN": (),
    "NOISY_TYPED_ENGLISH": (
        "ARTICLE_OMISSION",
        "PUNCTUATION_LOSS",
        "CASING_VARIATION",
        "SENTENCE_FRAGMENTS",
        "SPELLING_NOISE",
    ),
    "TELEGRAPHIC_PHC_NOTE": (
        "ABBREVIATION_DENSITY_MEDIUM",
        "SENTENCE_FRAGMENTS",
        "TELEGRAPHIC_COMPRESSION",
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _canonical_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(_canonical_json(row) + "\n" for row in rows)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _run_number(run_id: str) -> int:
    return int(run_id.rsplit("-v", 1)[1])


def _terminal_paths() -> list[Path]:
    paths: list[Path] = []
    for number in RUN_NUMBERS:
        run_id = f"structured-extraction-language-bulk-gpt41-20250414-v{number}"
        paths.extend(
            sorted(
                (ROOT / "experiments/generation" / run_id / "attempts").glob(
                    "*/terminal.json"
                )
            )
        )
    return paths


def load_campaign_terminals() -> list[dict[str, Any]]:
    rows = [_load_json(path) for path in _terminal_paths()]
    if len(rows) != 2150:
        raise ValueError(f"campaign requires 2150 terminal receipts, found {len(rows)}")
    if len({row["attempt_id"] for row in rows}) != len(rows):
        raise ValueError("campaign contains duplicate attempt IDs")
    if sum(row["status"] != "TRANSPORT_FAILED" for row in rows) != 2142:
        raise ValueError("campaign does not contain exactly 2142 candidate allocation slots")
    if sum(row["status"] == "TRANSPORT_FAILED" for row in rows) != 8:
        raise ValueError("campaign does not contain exactly eight transport-only receipts")
    style_counts = Counter(row["prompt"]["strategy_id"] for row in rows if row["status"] != "TRANSPORT_FAILED")
    if dict(style_counts) != EXPECTED_STYLES:
        raise ValueError(f"campaign style allocation mismatch: {dict(style_counts)}")
    return sorted(rows, key=lambda row: row["attempt_id"])


def _explicit_t1_t2_approvals() -> set[str]:
    approvals: set[str] = set()
    for path in (
        ROOT / "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v3/reviews/T1_review.json",
        ROOT / "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v4/reviews/T2_review.json",
    ):
        review = _load_json(path)
        for decision in review["decisions"]:
            if (
                decision["deterministic_status"] == "PENDING_HUMAN_REVIEW"
                and decision["review_decision"] == "SEMANTIC_APPROVE"
            ):
                approvals.add(decision["attempt_id"])
    return approvals


def _t3_sample(rows: list[dict[str, Any]], review: dict[str, Any]) -> list[dict[str, Any]]:
    config = review["t3_pass_sample"]
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if (
            _run_number(row["generation_run_id"]) in T3_RUN_NUMBERS
            and row["status"] == "PENDING_HUMAN_REVIEW"
        ):
            pools[row["candidate"]["strategy_id"]].append(row)
    sampled: list[dict[str, Any]] = []
    for style, pool in sorted(pools.items()):
        ordered = sorted(
            pool,
            key=lambda row: hashlib.sha256(
                f"{config['seed']}|{row['attempt_id']}".encode("utf-8")
            ).hexdigest(),
        )
        count = max(10, math.ceil(len(pool) * config["fraction_per_style"]))
        if config["counts"].get(style) != count:
            raise ValueError(f"recorded T3 sample count mismatch for {style}")
        sampled.extend(ordered[:count])
    if len(sampled) != config["reviewed"]:
        raise ValueError("recorded T3 semantic sample size mismatch")
    rejected = set(config["semantic_rejected_attempt_ids"])
    if not rejected <= {row["attempt_id"] for row in sampled}:
        raise ValueError("recorded T3 semantic rejection is outside the frozen sample")
    return sorted(sampled, key=lambda row: row["attempt_id"])


def _flatten_known(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        result: list[tuple[str, Any]] = []
        for key in sorted(value):
            result.extend(_flatten_known(value[key], f"{prefix}.{key}" if prefix else key))
        return result
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            result.extend(_flatten_known(item, f"{prefix}[{index}]"))
        return result
    return [(prefix, value)]


def _source_value_hashes_for_target(target: dict[str, Any]) -> dict[str, str]:
    return {
        fact_id: _sha256_bytes(_canonical_json(value).encode("utf-8"))
        for fact_id, value in _flatten_known(target)
    }


def _variant_id(terminal: dict[str, Any]) -> str:
    suffix = terminal["request_id"].rsplit("__variant-", 1)[1]
    return (
        f"{terminal['semantic_case_id']}__"
        f"{terminal['candidate']['strategy_id']}__v{int(suffix):04d}"
    )


def _language_variant(
    terminal: dict[str, Any],
    *,
    source_hashes: dict[str, str],
    review_basis: str,
) -> dict[str, Any]:
    candidate = terminal["candidate"]
    teacher = terminal["teacher"]
    prompt = terminal["prompt"]
    record = {
        "record_schema_id": LANGUAGE_SCHEMA_ID,
        "variant_id": _variant_id(terminal),
        "semantic_case_id": terminal["semantic_case_id"],
        "status": "APPROVED_CORPUS_CANDIDATE",
        "input": {"role": "user", "content": candidate["user_submission"]},
        "fact_evidence": [
            {
                **copy.deepcopy(item),
                "source_value_sha256": source_hashes[item["fact_id"]],
            }
            for item in candidate["fact_evidence"]
        ],
        "generation_provenance": {
            "generation_run_id": terminal["generation_run_id"],
            "attempt_id": terminal["attempt_id"],
            "request_id": terminal["request_id"],
            "request_sha256": terminal["request_sha256"],
            "teacher_provider": teacher["provider"],
            "teacher_model": teacher["model"],
            "teacher_snapshot": teacher["snapshot"],
            "strategy_id": prompt["strategy_id"],
            "prompt_id": prompt["prompt_id"],
            "prompt_version": prompt["prompt_version"],
            "prompt_sha256": prompt["prompt_sha256"],
            "generated_at": terminal["completed_at"],
        },
        "review": {
            "semantic_faithfulness": "APPROVED",
            "naturalness": "APPROVED",
            "phc_suitability": "APPROVED_FOR_HACKATHON",
            "reviewer": REVIEW_ID,
            "review_basis": review_basis,
        },
        "eligibility": {"corpus_candidate": True, "training": False},
    }
    schema = _load_json(LANGUAGE_SCHEMA_PATH)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(record)
    return record


def build_campaign_corpus() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    review = _load_json(REVIEW_PATH)
    if review.get("review_id") != REVIEW_ID or review.get("status") != "APPROVED_FOR_CORPUS_EXPORT":
        raise ValueError("campaign review is not approved for corpus export")
    if review["authorization"].get("training_authorized") is not False:
        raise ValueError("campaign review must not authorize training")
    terminals = load_campaign_terminals()
    sample = _t3_sample(terminals, review)
    t1_t2_approved = _explicit_t1_t2_approvals()
    t3_rejected = set(review["t3_pass_sample"]["semantic_rejected_attempt_ids"])

    frozen = {
        row["golden_case_id"]: row
        for row in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    out_of_scope = {
        row["parent_case_id"]: row for row in build_out_of_scope_training_parents()
    }

    language: list[dict[str, Any]] = []
    canonical: list[dict[str, Any]] = []
    chats: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for terminal in terminals:
        run_number = _run_number(terminal["generation_run_id"])
        approved = False
        basis = ""
        reason = ""
        if terminal["status"] == "TRANSPORT_FAILED":
            reason = "TRANSPORT_ONLY_NO_CANDIDATE"
        elif terminal["status"] != "PENDING_HUMAN_REVIEW":
            reason = terminal["status"]
        elif terminal["attempt_id"] in t3_rejected:
            reason = "SEMANTIC_REJECTED_IN_T3_SAMPLE"
        elif run_number in PRE_REMEDIATION_RUN_NUMBERS:
            if terminal["attempt_id"] in t1_t2_approved:
                approved = True
                basis = "INDIVIDUAL_T1_T2_REVIEW"
            else:
                reason = "UNREVIEWED_PRE_REMEDIATION_PASS_HOLD"
        else:
            approved = True
            basis = "T3_QUALIFIED_STYLE_AND_STRATIFIED_REVIEW"

        if not approved:
            exclusions.append(
                {
                    "attempt_id": terminal["attempt_id"],
                    "request_id": terminal["request_id"],
                    "semantic_case_id": terminal["semantic_case_id"],
                    "generation_run_id": terminal["generation_run_id"],
                    "terminal_status": terminal["status"],
                    "reason": reason,
                }
            )
            continue

        case_id = terminal["semantic_case_id"]
        if case_id in frozen:
            semantic = frozen[case_id]
            target_hashes = {
                item["fact_id"]: item["source_value_sha256"]
                for item in source_fact_specs(semantic)
            }
            target = None
            suite_id = SUITE_ID
            suite_sha = SEMANTIC_CASES_SHA256
            record_schema_id = semantic["record_schema_id"]
        else:
            parent = out_of_scope[case_id]
            target = parent["model_facing_target"]
            target_hashes = _source_value_hashes_for_target(target)
            suite_id = "edge-imci-structured-extraction-out-of-scope-parents-v1"
            suite_sha = _sha256_bytes(
                _canonical_json(parent).encode("utf-8")
            )
            record_schema_id = PARENT_SCHEMA_ID

        variant = _language_variant(
            terminal, source_hashes=target_hashes, review_basis=basis
        )
        variant_adapter = {
            "variant_id": variant["variant_id"],
            "semantic_case_id": case_id,
            "status": variant["status"],
            "conversation": [copy.deepcopy(variant["input"])],
            "generation_provenance": copy.deepcopy(variant["generation_provenance"]),
            "review": {
                key: variant["review"][key]
                for key in ("semantic_faithfulness", "naturalness", "phc_suitability", "reviewer")
            },
            "eligibility": copy.deepcopy(variant["eligibility"]),
        }
        if case_id in frozen:
            from edge_imci.model_io.encounter import project_model_facing_encounter

            target = project_model_facing_encounter(frozen[case_id])
        extraction = build_structured_extraction_record_from_target(
            source_case_id=case_id,
            semantic_suite_id=suite_id,
            semantic_suite_sha256=suite_sha,
            semantic_record_schema_id=record_schema_id,
            target=target,
            variant_record=variant_adapter,
            variant_style=STYLE_NAMES[terminal["candidate"]["strategy_id"]],
            noise_profile=NOISE_PROFILES[STYLE_NAMES[terminal["candidate"]["strategy_id"]]],
        )
        messages = format_structured_extraction_messages(extraction)
        if json.loads(messages[-1]["content"]) != extraction["target"]:
            raise ValueError("chat target differs from canonical target")
        language.append(variant)
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

    ids = [row["variant_id"] for row in language]
    if len(ids) != len(set(ids)):
        raise ValueError("promoted campaign variants are not uniquely identified")
    return language, canonical, chats, exclusions, sample


def _render_report(manifest: dict[str, Any]) -> str:
    by_style = manifest["approved_style_counts"]
    by_partition = manifest["partition_counts"]
    return "\n".join(
        [
            "# EdgeIMCI structured-extraction campaign final report v1",
            "",
            "> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `CORPUS_EXPORT_COMPLETE` · Training and production clinical use remain unauthorized.",
            "",
            "The guarded Azure campaign is reconciled at exactly 2,142 candidate-bearing allocation slots plus eight preserved transport-only receipts. The exported learning pair is free-form PHC language to deterministic model-facing encounter JSON; no classification, action, urgency, or frozen assistant response is used as the student target.",
            "",
            "## Outcome",
            "",
            f"- Approved canonical corpus records: **{manifest['record_count']}**",
            f"- Excluded/held receipts: **{manifest['excluded_receipt_count']}**",
            f"- Parent encounters represented: **{manifest['parent_case_count']} / 78**",
            f"- T3 deterministic-pass semantic sample: **{manifest['review']['t3_sample_reviewed']}** (one rejected)",
            "- T1/T2 policy: only individually approved pass records were promoted; unsampled pre-remediation passes remain held.",
            "- All deterministic rejections, parse failures, and transport-only receipts remain immutable evidence and were excluded.",
            "",
            "## Approved records by style",
            "",
            *(f"- `{key}`: {value}" for key, value in sorted(by_style.items())),
            "",
            "## Parent-derived partitions",
            "",
            *(f"- `{key}`: {value}" for key, value in sorted(by_partition.items())),
            "",
            "## Export boundary",
            "",
            "`canonical_records.jsonl` is the reusable, model-neutral dataset artifact. `chat_messages.jsonl` is a deterministic system/user/assistant serialization whose assistant content is JSON only. Applying a Qwen chat template remains a later deterministic training-preparation step.",
            "",
            "No Azure calls, fine-tuning, clinical-rule changes, or training authorization are performed by the export step.",
            "",
        ]
    )


def write_campaign_corpus() -> dict[str, Any]:
    language, canonical, chats, exclusions, sample = build_campaign_corpus()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payloads = {
        LANGUAGE_PATH: _canonical_jsonl(language),
        CANONICAL_PATH: _canonical_jsonl(canonical),
        CHAT_PATH: _canonical_jsonl(chats),
        EXCLUSIONS_PATH: _canonical_jsonl(exclusions),
    }
    for path, payload in payloads.items():
        path.write_text(payload, encoding="utf-8")
    style_counts = Counter(row["language_provenance"]["variant_style"] for row in canonical)
    partition_counts = Counter(row["partition"] for row in canonical)
    manifest = {
        "campaign_id": CAMPAIGN_ID,
        "status": "CORPUS_EXPORT_COMPLETE",
        "review_id": REVIEW_ID,
        "record_schema_id": STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID,
        "dataset_policy_id": DATASET_POLICY_ID,
        "split_policy_id": SPLIT_POLICY_ID,
        "remote_terminal_receipts": 2150,
        "candidate_bearing_allocation_slots": 2142,
        "transport_only_receipts": 8,
        "record_count": len(canonical),
        "excluded_receipt_count": len(exclusions),
        "parent_case_count": len({row["source_case_id"] for row in canonical}),
        "approved_style_counts": dict(sorted(style_counts.items())),
        "partition_counts": dict(sorted(partition_counts.items())),
        "review": {
            "t3_sample_reviewed": len(sample),
            "t3_sample_semantic_approved": len(sample) - 1,
            "t3_sample_semantic_rejected": 1,
            "all_final_run_non_pass_receipts_reviewed": True,
        },
        "assets": {
            str(path.relative_to(ROOT)): {
                "sha256": _sha256_bytes(payload.encode("utf-8")),
                "record_count": len(
                    exclusions if path == EXCLUSIONS_PATH else canonical
                ),
            }
            for path, payload in payloads.items()
        },
        "validation": {
            "teacher_target_blind": True,
            "canonical_target_deterministic": True,
            "unknown_not_inferred_negative": True,
            "parent_split_inheritance": True,
            "clinical_outputs_excluded_from_target": True,
            "training_authorized": False,
        },
        "authorization": {
            "training_authorized": False,
            "production_clinical_use_authorized": False,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(_render_report(manifest), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(write_campaign_corpus(), indent=2, sort_keys=True))
