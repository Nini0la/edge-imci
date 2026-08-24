"""Materialize the delegated semantic review of input-style qualification v2."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from edge_imci.generation.holistic_canary_execute import _atomic_write
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "holistic-input-style-pathway-qualification-gpt41-20250414-v2"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
REVIEW_PATH = ROOT / "configs" / "generation" / "input_style_pathway_qualification_review_v2.json"
REPORT_PATH = ROOT / "docs" / "input_style_pathway_qualification_review_v2.md"

ANNOTATION_ONLY_OVERRIDES = {
    ("NIGERIAN_ENGLISH", "hpg-027-diarrhoea-no-dehydration"),
    ("NIGERIAN_ENGLISH", "hpg-055-fever-severe-measles-cornea"),
    ("NIGERIAN_PIDGIN", "hpg-021-resp-post-bronchodilator-fast"),
    ("NIGERIAN_PIDGIN", "hpg-027-diarrhoea-no-dehydration"),
    ("NIGERIAN_PIDGIN", "hpg-055-fever-severe-measles-cornea"),
    ("NIGERIAN_PIDGIN", "hpg-068-cross-four-pathways"),
    ("NOISY_TYPED_ENGLISH", "hpg-075-contradiction-drinking"),
    ("TELEGRAPHIC_PHC_NOTE", "hpg-069-cross-urgent-dehydration-ear"),
}

SEMANTIC_REJECTION_REASONS = {
    ("NIGERIAN_PIDGIN", "hpg-028-diarrhoea-some-dehydration"): "Diarrhoea-specific eager/thirsty drinking status was omitted.",
    ("NIGERIAN_PIDGIN", "hpg-046-fever-no-risk"): "Wording for the negative lethargy/unconsciousness finding can mean the child is not conscious.",
    ("NIGERIAN_PIDGIN", "hpg-075-contradiction-drinking"): "The general known-negative drinking danger sign was inverted and the separate diarrhoea-specific drinking status of UNABLE was not preserved.",
    ("NOISY_TYPED_ENGLISH", "hpg-028-diarrhoea-some-dehydration"): "Diarrhoea-specific eager/thirsty drinking status was omitted.",
    ("NOISY_TYPED_ENGLISH", "hpg-061-ear-no-infection"): "Known-negative caregiver ear-discharge history was weakened to absence of a report.",
    ("NOISY_TYPED_ENGLISH", "hpg-069-cross-urgent-dehydration-ear"): "Known-negative caregiver ear-discharge history was weakened to absence of a report.",
    ("TELEGRAPHIC_PHC_NOTE", "hpg-014-resp-chest-hiv-positive"): "Known-negative danger sign was rendered as the risky double negative 'not unable'.",
    ("TELEGRAPHIC_PHC_NOTE", "hpg-016-resp-oximeter-89-9"): "Known-negative danger sign was rendered as the risky double negative 'not unable'.",
    ("TELEGRAPHIC_PHC_NOTE", "hpg-031-diarrhoea-severe-age-24-cholera"): "Known-negative danger sign was rendered as the risky double negative 'not unable'.",
    ("TELEGRAPHIC_PHC_NOTE", "hpg-065-ear-observed-pus-no-history"): "Known-negative caregiver ear-discharge history was weakened to absence of a report.",
}


def _load_attempts() -> list[dict[str, Any]]:
    attempts = []
    for path in sorted((RUN_DIR / "attempts").glob("*/terminal.json")):
        attempts.append(json.loads(path.read_text(encoding="utf-8")))
    if len(attempts) != 96:
        raise ValueError(f"expected 96 terminal attempts, found {len(attempts)}")
    return attempts


def _style_for(attempt: dict[str, Any], requests: dict[str, dict[str, Any]]) -> str:
    return requests[attempt["request_sha256"]]["variant_style"]


def build_review() -> dict[str, Any]:
    requests = {
        item["request_sha256"]: item
        for item in json.loads((RUN_DIR / "source_requests.json").read_text(encoding="utf-8"))
    }
    attempts = _load_attempts()
    summaries: dict[str, Counter[str]] = defaultdict(Counter)
    exceptions = []
    for attempt in attempts:
        style = _style_for(attempt, requests)
        key = (style, attempt["semantic_case_id"])
        if key in SEMANTIC_REJECTION_REASONS:
            decision = "SEMANTIC_REJECT"
            rationale = SEMANTIC_REJECTION_REASONS[key]
        elif attempt["status"] == "PENDING_HUMAN_REVIEW":
            decision = "SEMANTIC_APPROVE"
            rationale = "Deterministic validation passed; no additional semantic defect identified in delegated review."
        elif key in ANNOTATION_ONLY_OVERRIDES:
            decision = "SEMANTIC_APPROVE_ANNOTATION_OVERRIDE"
            rationale = "Submission is semantically faithful; rejection is confined to evidence-span annotation or guard coverage."
        else:
            raise ValueError(f"unreviewed deterministic rejection: {key}")
        summaries[style][decision] += 1
        if decision != "SEMANTIC_APPROVE":
            exceptions.append(
                {
                    "variant_style": style,
                    "semantic_case_id": attempt["semantic_case_id"],
                    "attempt_id": attempt["attempt_id"],
                    "deterministic_status": attempt["status"],
                    "error_codes": attempt["validation"]["error_codes"],
                    "review_decision": decision,
                    "rationale": rationale,
                }
            )
    style_decisions = []
    for style in sorted(summaries):
        counts = summaries[style]
        approved = counts["SEMANTIC_APPROVE"] + counts["SEMANTIC_APPROVE_ANNOTATION_OVERRIDE"]
        systematic_semantic_failures = any(
            sum(
                item["variant_style"] == style
                and item["review_decision"] == "SEMANTIC_REJECT"
                and phrase in item["rationale"]
                for item in exceptions
            )
            >= 2
            for phrase in (
                "drinking status",
                "ear-discharge history",
                "double negative",
            )
        )
        qualified = approved >= 22 and not systematic_semantic_failures
        style_decisions.append(
            {
                "variant_style": style,
                "attempts": 24,
                "semantic_approved": approved,
                "semantic_rejected": counts["SEMANTIC_REJECT"],
                "annotation_only_overrides": counts["SEMANTIC_APPROVE_ANNOTATION_OVERRIDE"],
                "minimum_semantic_approvals_required": 22,
                "systematic_semantic_failure_present": systematic_semantic_failures,
                "release_decision": "QUALIFIED" if qualified else "REMEDIATE_AND_REQUALIFY",
            }
        )
    return {
        "review_schema_id": "edge-imci-input-style-pathway-qualification-review-v1",
        "generation_run_id": RUN_ID,
        "authority": "PROJECT_OWNER_DELEGATED_REVIEW",
        "lifecycle": "COMPLETE",
        "review_policy": {
            "matched_parents_per_style": 24,
            "minimum_semantic_approvals": 22,
            "minimum_rate": "91.7%",
            "systematic_same-class_semantic_failures_allowed": 0,
            "annotation_only_rejections_may_be_overridden_but_attempt_evidence_remains_immutable": True,
        },
        "style_decisions": style_decisions,
        "exceptions": sorted(exceptions, key=lambda item: (item["variant_style"], item["semantic_case_id"])),
        "scope_guard": {
            "bulk_generation_authorized_by_this_review": False,
            "training_authorized": False,
            "production_clinical_use_authorized": False,
        },
    }


def write_review() -> dict[str, Any]:
    review = build_review()
    _atomic_write(REVIEW_PATH, review)
    lines = [
        "# EdgeIMCI input-style pathway qualification v2 review",
        "",
        "> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `COMPLETE` · Review of 96 immutable Azure GPT-4.1 attempts; no training or production-clinical authorization.",
        "",
        "## Outcome",
        "",
        "| Style | Approved | Rejected | Annotation overrides | Decision |",
        "|---|---:|---:|---:|---|",
    ]
    for item in review["style_decisions"]:
        lines.append(
            f"| {item['variant_style']} | {item['semantic_approved']}/24 | {item['semantic_rejected']} | {item['annotation_only_overrides']} | {item['release_decision']} |"
        )
    lines.extend(
        [
            "",
            "Nigerian English v1.3.1 qualifies. The other three recipes require prompt remediation and a fresh matched-parent qualification; their v2 attempts remain useful immutable evidence but are not released into a bulk contract.",
            "",
            "## Semantic rejections",
            "",
        ]
    )
    for item in review["exceptions"]:
        if item["review_decision"] == "SEMANTIC_REJECT":
            lines.append(f"- `{item['variant_style']}` / `{item['semantic_case_id']}` — {item['rationale']}")
    lines.extend(
        [
            "",
            "## Annotation-only overrides",
            "",
            "These submissions are semantically approved, while their original deterministic terminal status is preserved.",
            "",
        ]
    )
    for item in review["exceptions"]:
        if item["review_decision"] == "SEMANTIC_APPROVE_ANNOTATION_OVERRIDE":
            lines.append(f"- `{item['variant_style']}` / `{item['semantic_case_id']}` — {', '.join(item['error_codes'])}")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review


def main() -> int:
    review = write_review()
    print(json.dumps({"status": "OK", "style_decisions": review["style_decisions"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
