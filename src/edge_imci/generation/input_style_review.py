"""Revalidate and promote the bounded input-language style canary.

The immutable attempt records remain unchanged. This exporter documents the
closed-enum infrastructure failure, revalidates each raw response under the
corrected schema, applies the delegated human review decisions, and promotes
only approved user-language variants into extraction canary records.
"""

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
from edge_imci.generation.holistic_style_canary import (
    RUN_DIR,
    STYLE_CONFIGURATIONS,
    validate_style_candidate,
)
from edge_imci.generation.holistic_variants import (
    build_variant_record,
    parse_candidate_output,
)
from edge_imci.training.structured_extraction import (
    build_structured_extraction_record,
    format_structured_extraction_messages,
)


ROOT = Path(__file__).resolve().parents[3]
REVIEW_PATH = (
    ROOT / "configs" / "generation" / "input_language_style_canary_review_v1.json"
)
OUTPUT_DIR = ROOT / "data" / "canary" / "input_language_styles_v1"
LANGUAGE_VARIANTS_PATH = OUTPUT_DIR / "language_variants.jsonl"
CANONICAL_RECORDS_PATH = OUTPUT_DIR / "canonical_records.jsonl"
CHAT_MESSAGES_PATH = OUTPUT_DIR / "chat_messages.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
REPORT_PATH = ROOT / "docs" / "input_language_style_canary_review_v1.md"


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


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _attempts() -> dict[tuple[str, str], dict[str, Any]]:
    results: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted((RUN_DIR / "attempts").glob("*/terminal.json")):
        attempt = _load_json(path)
        key = (attempt["semantic_case_id"], attempt["prompt"]["strategy_id"])
        if key in results:
            raise ValueError(f"duplicate style-canary attempt: {key}")
        results[key] = attempt
    if len(results) != 12:
        raise ValueError("style-canary review requires exactly twelve terminal attempts")
    return results


def _noise_by_style() -> dict[str, tuple[str, ...]]:
    return {
        item["variant_style"]: tuple(item["noise_profile"])
        for item in STYLE_CONFIGURATIONS
    }


def _apply_evidence_overrides(
    candidate: dict[str, Any], decision: dict[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(candidate)
    overrides = decision.get("evidence_overrides", {})
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


def build_reviewed_style_canary() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    review = _load_json(REVIEW_PATH)
    if review["status"] != "COMPLETE":
        raise ValueError("style-canary review is not complete")
    if review["authorization"] != {
        "bulk_generation_authorized": False,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }:
        raise ValueError("style review must not authorize scale, training, or clinical use")
    attempts = _attempts()
    requests = {
        (item["semantic_case_id"], item["strategy_id"]): item
        for item in json.loads((RUN_DIR / "source_requests.json").read_text(encoding="utf-8"))
    }
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    parents = {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }
    noise = _noise_by_style()
    language_variants: list[dict[str, Any]] = []
    canonical_records: list[dict[str, Any]] = []
    chat_records: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []

    for decision in review["candidate_decisions"]:
        case_id = decision["semantic_case_id"]
        strategy_id = decision["strategy_id"]
        attempt = attempts[(case_id, strategy_id)]
        if attempt["status"] != "PARSE_FAILED" or attempt["validation"]["error_codes"] != [
            "SCHEMA_INVALID"
        ]:
            raise ValueError("review expected the immutable closed-enum failure record")
        candidate = _apply_evidence_overrides(
            parse_candidate_output(attempt["raw_response"]), decision
        )
        revalidation = validate_style_candidate(
            candidate, semantics[case_id], parents[case_id], strategy_id
        )
        approved = decision["decision"] == "APPROVED_CORPUS_CANDIDATE"
        if approved != revalidation.deterministic_pass:
            raise ValueError(
                f"delegated decision and corrected deterministic result differ: {case_id}/{strategy_id}"
            )
        audit.append(
            {
                "semantic_case_id": case_id,
                "strategy_id": strategy_id,
                "variant_style": decision["variant_style"],
                "immutable_attempt_status": attempt["status"],
                "corrected_revalidation": revalidation.to_dict(),
                "review_decision": decision["decision"],
                "reason_codes": decision["reason_codes"],
                "evidence_annotation_remediated": bool(decision.get("evidence_overrides")),
            }
        )
        if not approved:
            continue
        request = requests[(case_id, strategy_id)]
        variant = build_variant_record(
            candidate=candidate,
            semantic_record=semantics[case_id],
            parent_language=parents[case_id],
            request=request,
            generation_run_id=attempt["generation_run_id"],
            attempt_id=attempt["attempt_id"],
            teacher_provider=attempt["teacher"]["provider"],
            teacher_model=attempt["teacher"]["model"],
            teacher_snapshot=attempt["teacher"]["snapshot"],
            renderer_git_commit=review["renderer_git_commit"],
            generated_at=attempt["completed_at"],
            candidate_validator=validate_style_candidate,
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
            variant_style=decision["variant_style"],
            noise_profile=noise[decision["variant_style"]],
        )
        messages = format_structured_extraction_messages(extraction)
        language_variants.append(variant)
        canonical_records.append(extraction)
        chat_records.append(
            {
                "example_id": extraction["example_id"],
                "source_case_id": case_id,
                "variant_id": variant["variant_id"],
                "partition": extraction["partition"],
                "messages": messages,
            }
        )
    return language_variants, canonical_records, chat_records, audit


def _render_report(
    audit: list[dict[str, Any]], canonical: list[dict[str, Any]], review: dict[str, Any]
) -> str:
    style_counts = Counter(item["language_provenance"]["variant_style"] for item in canonical)
    lines = [
        "# EdgeIMCI input-language style canary review v1",
        "",
        "> **Authority:** `PROJECT_OWNER_DELEGATED_HACKATHON_REVIEW` · **Lifecycle:** `COMPLETE` · This is not expert linguistic certification or authorization for bulk generation/training.",
        "",
        "The 12 immutable Azure attempts were incorrectly recorded as `SCHEMA_INVALID` because the candidate schema's closed strategy enumeration still named only the older prompt strategies. No attempt was retried. Raw JSON responses were revalidated under the corrected schema, while the original attempt evidence remained unchanged.",
        "",
        "## Outcome",
        "",
        f"- Approved corpus candidates: **{len(canonical)}**",
        f"- Rejected candidates: **{len(audit) - len(canonical)}**",
        "- Remote request starts: **12**",
        "- Retries: **0**",
        "",
        "| Style | Approved | Recipe decision |",
        "|---|---:|---|",
    ]
    for style, recipe in review["recipe_decisions"].items():
        lines.append(f"| `{style}` | {style_counts.get(style, 0)}/3 | `{recipe}` |")
    lines.extend(
        [
            "",
            "## Candidate decisions",
            "",
            "| Style | Case | Decision | Reason codes |",
            "|---|---|---|---|",
        ]
    )
    for item in audit:
        reasons = ", ".join(f"`{code}`" for code in item["reason_codes"])
        lines.append(
            f"| `{item['variant_style']}` | `{item['semantic_case_id']}` | "
            f"`{item['review_decision']}` | {reasons} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Nigerian Pidgin and telegraphic PHC-note recipes passed all three matched semantic probes and may proceed to further controlled generation. The Pidgin decision is a project-level hackathon suitability review, not broad sociolinguistic certification.",
            "",
            "Nigerian English and noisy typed English require prompt remediation before scale. The rejected phrasing weakened a known negative into absence of a report or represented it with a double negative; either could train UNKNOWN/negative confusion.",
            "",
            "All approved language variants are paired with deterministic model-facing JSON targets. Their frozen downstream assistant responses remain preserved in language records but are absent from extraction SFT records and messages.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reviewed_style_canary() -> dict[str, Any]:
    language, canonical, chats, audit = build_reviewed_style_canary()
    review = _load_json(REVIEW_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payloads = {
        LANGUAGE_VARIANTS_PATH: _canonical_jsonl(language),
        CANONICAL_RECORDS_PATH: _canonical_jsonl(canonical),
        CHAT_MESSAGES_PATH: _canonical_jsonl(chats),
    }
    for path, payload in payloads.items():
        path.write_text(payload, encoding="utf-8")
    audit_path = RUN_DIR / "corrected_revalidation_and_review.json"
    audit_payload = {
        "review_id": review["review_id"],
        "status": "COMPLETE",
        "immutable_attempts_preserved": True,
        "attempt_count": len(audit),
        "approved_count": len(canonical),
        "rejected_count": len(audit) - len(canonical),
        "candidate_results": audit,
    }
    audit_path.write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_PATH.write_text(_render_report(audit, canonical, review), encoding="utf-8")
    manifest = {
        "canary_id": "edge-imci-input-language-styles-canary-v1",
        "status": "REVIEW_COMPLETE",
        "review_id": review["review_id"],
        "attempt_count": len(audit),
        "approved_record_count": len(canonical),
        "rejected_record_count": len(audit) - len(canonical),
        "style_counts": dict(
            sorted(Counter(row["language_provenance"]["variant_style"] for row in canonical).items())
        ),
        "assets": {
            str(path.relative_to(ROOT)): {"sha256": _sha256(payload.encode("utf-8"))}
            for path, payload in payloads.items()
        },
        "validation": {
            "immutable_attempt_evidence_preserved": True,
            "closed_enum_failure_remediated_without_remote_retry": True,
            "unknown_preservation_checked": True,
            "connector_and_epistemic_qualifier_guards_applied": True,
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
    write_reviewed_style_canary()
