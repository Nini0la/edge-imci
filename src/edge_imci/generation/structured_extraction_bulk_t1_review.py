"""Materialize the delegated semantic review of the combined 250-attempt T1 gate."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from edge_imci.generation.holistic_canary_execute import _atomic_write
from edge_imci.generation.holistic_variants import ROOT


RUN_IDS = (
    "structured-extraction-language-bulk-gpt41-20250414-v1",
    "structured-extraction-language-bulk-gpt41-20250414-v3",
)
OUTPUT_DIR = (
    ROOT
    / "experiments"
    / "generation"
    / "structured-extraction-language-bulk-gpt41-20250414-v3"
    / "reviews"
)
REVIEW_PATH = OUTPUT_DIR / "T1_review.json"
REPORT_PATH = ROOT / "docs" / "structured_extraction_bulk_t1_review.md"

SEMANTIC_REJECTED_DETERMINISTIC = {
    ("phc-nigerian-english-v1", "hpg-049-fever-duration-7"): "Invented a negative pus-from-eye finding whose source state is UNKNOWN.",
    ("phc-nigerian-english-v1", "hpg-068-cross-four-pathways"): "Invented that fever was not present every day although that field is UNKNOWN.",
    ("phc-nigerian-pidgin-v1", "hpg-054-fever-measles-eye"): "Omitted supplied fever/measles assessment facts, including corneal and measles-cough negatives.",
    ("phc-nigerian-pidgin-v1", "hpg-060-fever-test-result-unknown"): "Changed no identified bacterial cause into a broader claim that no bacterial cause exists.",
    ("phc-nigerian-pidgin-v1", "hpg-071-incomplete-entry-unknown"): "Weakened the known-negative ear-problem fact into absence of a caregiver report.",
    ("phc-noisy-typed-english-v1", "hpg-060-fever-test-result-unknown"): "Added a risky double negative and duplicated the general drinking fact.",
    ("phc-noisy-typed-english-v1", "hpg-068-cross-four-pathways"): "Reversed generalized rash from positive to negative and omitted supplied facts.",
    ("phc-noisy-typed-english-v1", "hpg-072-incomplete-multiple-groups"): "Omitted supplied respiratory context from an incomplete encounter.",
    ("phc-telegraphic-note-v1", "hpg-011-resp-age-12-rate-40"): "Invented negative ear-discharge history under a null ear assessment.",
    ("phc-telegraphic-note-v1", "hpg-015-resp-stridor"): "Invented negative ear-discharge history under a null ear assessment.",
    ("phc-telegraphic-note-v1", "hpg-070-cross-multiple-urgent"): "Teacher output was schema-invalid and contained no reviewable candidate.",
}

SEMANTIC_REJECTED_PASS_SAMPLE = {
    ("phc-nigerian-english-v1", "hpg-016-resp-oximeter-89-9"): "Reversed the supplied positive cough/difficult-breathing entry into 'no cough or difficult breathing'.",
    ("phc-nigerian-pidgin-v1", "hpg-020-resp-post-bronchodilator-improved"): "Did not preserve the separate positive initial wheezing fact; only recurrent-wheeze absence remained.",
    ("phc-telegraphic-note-v1", "hpg-037-diarrhoea-positive-drinking-reuse"): "Reversed inability to drink or breastfeed into ability to drink or breastfeed.",
}


def _attempts() -> list[dict[str, Any]]:
    rows = []
    for run_id in RUN_IDS:
        for path in (
            ROOT / "experiments" / "generation" / run_id / "attempts"
        ).glob("*/terminal.json"):
            rows.append(json.loads(path.read_text(encoding="utf-8")))
    if len(rows) != 250:
        raise ValueError(f"combined T1 must contain 250 attempts, found {len(rows)}")
    return rows


def _style(attempt: dict[str, Any]) -> str:
    return attempt["configuration_id"].split("__")[1]


def _pass_sample(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_style: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in attempts:
        if attempt["status"] == "PENDING_HUMAN_REVIEW":
            by_style[_style(attempt)].append(attempt)
    sample = []
    for style in sorted(by_style):
        ranked = sorted(
            by_style[style],
            key=lambda item: hashlib.sha256(
                f"T1|{item['attempt_id']}".encode()
            ).hexdigest(),
        )
        sample.extend(ranked[:10])
    if len(sample) != 40:
        raise ValueError("T1 pass sample must contain 10 attempts per style")
    return sample


def build_review() -> dict[str, Any]:
    attempts = _attempts()
    deterministic_rejections = [
        item for item in attempts if item["status"] != "PENDING_HUMAN_REVIEW"
    ]
    if len(deterministic_rejections) != 23:
        raise ValueError("T1 must contain 23 deterministic rejections")
    sample = _pass_sample(attempts)
    decisions = []
    style_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "attempts": 0,
            "raw_passes": 0,
            "raw_rejections": 0,
            "reviewed": 0,
            "semantic_approved": 0,
            "semantic_rejected": 0,
            "annotation_only_overrides": 0,
        }
    )
    for attempt in attempts:
        style_counts[_style(attempt)]["attempts"] += 1
        key = "raw_passes" if attempt["status"] == "PENDING_HUMAN_REVIEW" else "raw_rejections"
        style_counts[_style(attempt)][key] += 1
    review_set = {item["attempt_id"]: item for item in (*deterministic_rejections, *sample)}
    for attempt in review_set.values():
        style = _style(attempt)
        key = (style, attempt["semantic_case_id"])
        reason = SEMANTIC_REJECTED_DETERMINISTIC.get(key) or SEMANTIC_REJECTED_PASS_SAMPLE.get(key)
        if reason:
            decision = "SEMANTIC_REJECT"
        elif attempt["status"] == "PENDING_HUMAN_REVIEW":
            decision = "SEMANTIC_APPROVE"
            reason = "Required deterministic-pass sample; no semantic defect identified."
        else:
            decision = "SEMANTIC_APPROVE_ANNOTATION_OVERRIDE"
            reason = "Submission is semantically faithful; terminal rejection is confined to evidence annotation/guard coverage."
        counts = style_counts[style]
        counts["reviewed"] += 1
        if decision == "SEMANTIC_REJECT":
            counts["semantic_rejected"] += 1
        else:
            counts["semantic_approved"] += 1
            if decision.endswith("ANNOTATION_OVERRIDE"):
                counts["annotation_only_overrides"] += 1
        decisions.append(
            {
                "attempt_id": attempt["attempt_id"],
                "semantic_case_id": attempt["semantic_case_id"],
                "strategy_id": style,
                "deterministic_status": attempt["status"],
                "error_codes": attempt["validation"]["error_codes"],
                "review_decision": decision,
                "rationale": reason,
            }
        )
    return {
        "review_schema_id": "edge-imci-structured-extraction-bulk-tranche-review-v1",
        "tranche_id": "T1",
        "status": "REMEDIATION_REQUIRED",
        "authority": "PROJECT_OWNER_DELEGATED_REVIEW",
        "combined_generation_run_ids": list(RUN_IDS),
        "combined_attempts": 250,
        "review_scope": {
            "all_deterministic_rejections_reviewed": 23,
            "deterministic_pass_sample_reviewed": 40,
            "pass_sample_per_style": 10,
            "total_unique_attempts_reviewed": len(review_set),
        },
        "style_summary": dict(sorted(style_counts.items())),
        "semantic_failure_count": sum(
            item["review_decision"] == "SEMANTIC_REJECT" for item in decisions
        ),
        "annotation_only_override_count": sum(
            item["review_decision"] == "SEMANTIC_APPROVE_ANNOTATION_OVERRIDE"
            for item in decisions
        ),
        "release_decision": "BLOCK_T2_REMEDIATE_PROMPTS_AND_VALIDATORS",
        "blocking_findings": [
            "Positive cough/difficult-breathing polarity reversal escaped deterministic validation.",
            "Unable-to-drink polarity reversal escaped deterministic validation.",
            "Initial wheezing was lost into a recurrent-wheeze negative.",
            "Null nested ear/fever facts were invented systematically in affected styles.",
            "Complex cases showed fact omission and one rash polarity reversal.",
        ],
        "decisions": sorted(decisions, key=lambda item: item["attempt_id"]),
        "authorization": {
            "next_tranche_released": False,
            "training_authorized": False,
            "production_clinical_use_authorized": False,
        },
    }


def write_review() -> dict[str, Any]:
    review = build_review()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _atomic_write(REVIEW_PATH, review)
    lines = [
        "# Structured-extraction bulk T1 review",
        "",
        "> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `REMEDIATION_REQUIRED` · Combined review of 250 immutable attempts; T2, training and production clinical use are not released.",
        "",
        "T1 produced 227 raw deterministic passes and 23 raw rejections. Review covered every rejection plus 10 deterministic passes per style (63 unique attempts total). Fourteen reviewed attempts contained semantic defects; 12 raw rejections were annotation-only overrides.",
        "",
        "| Style | Attempts | Raw pass | Reviewed | Semantic defects | Annotation overrides |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for style, item in review["style_summary"].items():
        lines.append(
            f"| {style} | {item['attempts']} | {item['raw_passes']} | {item['reviewed']} | {item['semantic_rejected']} | {item['annotation_only_overrides']} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "T2 is blocked. Prompt and deterministic-polarity remediation must pass a targeted gate before a new exact-slot continuation can be prepared. The 250 T1 attempts remain immutable and will not be regenerated.",
            "",
            "## Blocking findings",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in review["blocking_findings"])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review


def main() -> int:
    review = write_review()
    print(json.dumps({"status": review["status"], "reviewed": review["review_scope"]["total_unique_attempts_reviewed"], "semantic_failures": review["semantic_failure_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
