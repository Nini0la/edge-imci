"""Review and export the 24-parent Nigerian English v1.2 pathway pilot."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_style_canary import validate_style_candidate
from edge_imci.generation.holistic_variants import build_variant_record
from edge_imci.generation.nigerian_english_v12_pilot import RUN_DIR
from edge_imci.training.structured_extraction import (
    build_structured_extraction_record,
    format_structured_extraction_messages,
)


ROOT = Path(__file__).resolve().parents[3]
REVIEW_PATH = (
    ROOT
    / "configs"
    / "generation"
    / "nigerian_english_v1_2_pathway_pilot_review.json"
)
OUTPUT_DIR = ROOT / "data" / "pilot" / "nigerian_english_v1_2_pathway_pilot"
LANGUAGE_VARIANTS_PATH = OUTPUT_DIR / "language_variants.jsonl"
CANONICAL_RECORDS_PATH = OUTPUT_DIR / "canonical_records.jsonl"
CHAT_MESSAGES_PATH = OUTPUT_DIR / "chat_messages.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
REPORT_PATH = ROOT / "docs" / "nigerian_english_v1_2_pathway_pilot_review.md"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _canonical_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
        for row in rows
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _attempts() -> dict[str, dict[str, Any]]:
    attempts: dict[str, dict[str, Any]] = {}
    for path in sorted((RUN_DIR / "attempts").glob("*/terminal.json")):
        attempt = _load_json(path)
        case_id = attempt["semantic_case_id"]
        if case_id in attempts:
            raise ValueError(f"duplicate pathway-pilot attempt: {case_id}")
        attempts[case_id] = attempt
    if len(attempts) != 24:
        raise ValueError("pathway-pilot review requires 24 terminal attempts")
    return attempts


def _apply_evidence_overrides(
    candidate: dict[str, Any], overrides: dict[str, str]
) -> dict[str, Any]:
    result = copy.deepcopy(candidate)
    seen: set[str] = set()
    for evidence in result["fact_evidence"]:
        fact_id = evidence["fact_id"]
        if fact_id in overrides:
            replacement = overrides[fact_id]
            if replacement not in result["user_submission"]:
                raise ValueError(f"evidence override is not an exact span: {fact_id}")
            evidence["evidence_text"] = replacement
            seen.add(fact_id)
    if seen != set(overrides):
        raise ValueError("evidence override names an absent fact")
    return result


def build_reviewed_pilot() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    review = _load_json(REVIEW_PATH)
    if review["status"] != "COMPLETE":
        raise ValueError("pathway-pilot review is incomplete")
    if review["authorization"] != {
        "additional_remote_calls_authorized": False,
        "bulk_generation_authorized": False,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }:
        raise ValueError("pathway-pilot review exceeds its authorization")
    attempts = _attempts()
    approved_ids = set(review["approved_case_ids"])
    rejected = review["rejected_cases"]
    if approved_ids & set(rejected) or approved_ids | set(rejected) != set(attempts):
        raise ValueError("review decisions must partition all 24 attempts")
    requests = {
        item["semantic_case_id"]: item
        for item in json.loads(
            (RUN_DIR / "source_requests.json").read_text(encoding="utf-8")
        )
    }
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    parents = {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }
    language: list[dict[str, Any]] = []
    canonical: list[dict[str, Any]] = []
    chats: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for case_id, attempt in sorted(attempts.items()):
        overrides = review["evidence_overrides"].get(case_id, {})
        candidate = _apply_evidence_overrides(attempt["candidate"], overrides)
        validation = validate_style_candidate(
            candidate,
            semantics[case_id],
            parents[case_id],
            "phc-nigerian-english-v1",
        )
        approved = case_id in approved_ids
        if approved != validation.deterministic_pass:
            raise ValueError(f"review and current validation differ: {case_id}")
        if not approved and set(rejected[case_id]) != set(validation.error_codes):
            raise ValueError(f"recorded rejection reasons differ: {case_id}")
        reason_codes = (
            ["SEMANTICALLY_FAITHFUL", "PHC_SUITABLE"]
            + (["EVIDENCE_ANNOTATION_REMEDIATED"] if overrides else [])
            if approved
            else rejected[case_id]
        )
        audit.append(
            {
                "semantic_case_id": case_id,
                "stratum": requests[case_id]["stratum"],
                "immutable_attempt_status": attempt["status"],
                "current_validation": validation.to_dict(),
                "review_decision": (
                    "APPROVED_CORPUS_CANDIDATE" if approved else "REJECTED"
                ),
                "reason_codes": reason_codes,
                "evidence_annotation_remediated": bool(overrides),
            }
        )
        if not approved:
            continue
        variant = build_variant_record(
            candidate=candidate,
            semantic_record=semantics[case_id],
            parent_language=parents[case_id],
            request=requests[case_id],
            generation_run_id=attempt["generation_run_id"],
            attempt_id=attempt["attempt_id"],
            teacher_provider=attempt["teacher"]["provider"],
            teacher_model=attempt["teacher"]["model"],
            teacher_snapshot=attempt["teacher"]["snapshot"],
            renderer_git_commit=review["renderer_git_commit"],
            generated_at=attempt["completed_at"],
            candidate_validator=validate_style_candidate,
        )
        variant["variant_id"] = (
            f"{case_id}__phc-nigerian-english-v1__prompt-v1-2__pilot-v1"
        )
        variant["status"] = "APPROVED_CORPUS_CANDIDATE"
        variant["review"] = {
            "semantic_faithfulness": "APPROVED",
            "naturalness": "APPROVED",
            "phc_suitability": "APPROVED_FOR_HACKATHON",
            "reviewer": review["reviewer"],
        }
        variant["eligibility"]["corpus_candidate"] = True
        extraction = build_structured_extraction_record(
            semantic_record=semantics[case_id],
            variant_record=variant,
            variant_style="NIGERIAN_ENGLISH",
            noise_profile=(),
        )
        language.append(variant)
        canonical.append(extraction)
        chats.append(
            {
                "example_id": extraction["example_id"],
                "source_case_id": case_id,
                "variant_id": variant["variant_id"],
                "partition": extraction["partition"],
                "messages": format_structured_extraction_messages(extraction),
            }
        )
    return language, canonical, chats, audit


def _render_report(audit: list[dict[str, Any]]) -> str:
    rejected = [item for item in audit if item["review_decision"] == "REJECTED"]
    error_counts = Counter(
        code for item in rejected for code in item["reason_codes"]
    )
    lines = [
        "# EdgeIMCI Nigerian English v1.2 pathway-pilot review",
        "",
        "> **Authority:** PROJECT_OWNER_DELEGATED_REVIEW · **Lifecycle:** COMPLETE · No additional calls, bulk generation, training, or clinical-use authorization.",
        "",
        "The 24-parent pilot broadened Nigerian English v1.2 beyond the three matched validation encounters. It covered danger signs, respiratory assessment, diarrhoea/dehydration, fever/malaria/measles, ear assessment, integrated encounters, incomplete states, and contradictory source observations.",
        "",
        "## Outcome",
        "",
        "- Remote request starts: **24**",
        "- Retries: **0**",
        "- Generation-time deterministic passes: **23/24**",
        "- Approved after strengthened validation and delegated semantic review: **19/24**",
        "- Rejected semantic variants: **5/24**",
        "- Annotation-only remediation: **1/24**",
        "- Reserved exposure: **$0.72** (not billing evidence)",
        "- Token usage: **37,164 input / 20,133 output**",
        "- Recipe decision: REVISE_BEFORE_SCALE",
        "",
        "## Newly exposed failures",
        "",
        "- Diarrhoea-specific drinking status weakened into general ability to drink: "
        f"**{error_counts.get('DIARRHOEA_DRINKING_STATUS_DISTINCTION_LOST', 0)}**",
        "- Known-negative ear-discharge history weakened into absence of reporting: "
        f"**{error_counts.get('KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT', 0)}**",
        "",
        "These are semantic extraction-label failures, not stylistic preferences. In particular, knowing that a child can drink or breastfeed does not establish whether the child drinks normally, poorly, or eagerly/thirstily.",
        "",
        "## Rejected cases",
        "",
        "| Case | Stratum | Reason |",
        "|---|---|---|",
    ]
    for item in rejected:
        reasons = ", ".join(item["reason_codes"])
        lines.append(
            f"| {item['semantic_case_id']} | {item['stratum']} | {reasons} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "The 19 faithful variants are retained as corpus candidates. The five semantic failures remain immutable rejected-attempt evidence. Nigerian English v1.2 should not be scaled further. Prompt v1.3 is prepared with explicit drinking-status and negative ear-history requirements, but it has not been remotely validated and no further calls are authorized.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reviewed_pilot() -> dict[str, Any]:
    language, canonical, chats, audit = build_reviewed_pilot()
    review = _load_json(REVIEW_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payloads = {
        LANGUAGE_VARIANTS_PATH: _canonical_jsonl(language),
        CANONICAL_RECORDS_PATH: _canonical_jsonl(canonical),
        CHAT_MESSAGES_PATH: _canonical_jsonl(chats),
    }
    for path, payload in payloads.items():
        path.write_text(payload, encoding="utf-8")
    audit_payload = {
        "review_id": review["review_id"],
        "status": "COMPLETE",
        "immutable_attempts_preserved": True,
        "attempt_count": len(audit),
        "approved_count": len(canonical),
        "rejected_count": len(audit) - len(canonical),
        "candidate_results": audit,
    }
    (RUN_DIR / "strengthened_revalidation_and_review.json").write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(_render_report(audit), encoding="utf-8")
    manifest = {
        "pilot_id": "edge-imci-nigerian-english-v1-2-pathway-pilot-v1",
        "status": "REVIEW_COMPLETE",
        "review_id": review["review_id"],
        "attempt_count": len(audit),
        "approved_record_count": len(canonical),
        "rejected_record_count": len(audit) - len(canonical),
        "recipe_decision": review["recipe_decision"],
        "next_prompt_version": review["next_prompt_version"],
        "assets": {
            str(path.relative_to(ROOT)): {
                "sha256": _sha256(payload.encode("utf-8"))
            }
            for path, payload in payloads.items()
        },
        "validation": {
            "immutable_attempt_evidence_preserved": True,
            "annotation_remediation_separate_and_auditable": True,
            "diarrhoea_drinking_status_distinction_checked": True,
            "negative_ear_history_strength_checked": True,
            "unknown_preservation_checked": True,
            "target_side_information_excluded": True,
        },
        "authorization": review["authorization"],
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    write_reviewed_pilot()
