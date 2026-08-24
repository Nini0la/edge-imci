"""Materialize the delegated semantic review of the 250-attempt T2 gate."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from edge_imci.generation.holistic_canary_execute import _atomic_write
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "structured-extraction-language-bulk-gpt41-20250414-v4"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
REVIEW_PATH = RUN_DIR / "reviews" / "T2_review.json"
REPORT_PATH = ROOT / "docs" / "structured_extraction_bulk_t2_review.md"

SEMANTIC_REJECTED = {
    ("phc-nigerian-english-v1", "hpg-028-diarrhoea-some-dehydration"): "Merged general ability with diarrhoea drinking status and repeated the general finding as a double negative.",
    ("phc-nigerian-english-v1", "hpg-057-fever-malaria-and-measles"): "Invented a deep/extensive mouth-ulcer negative whose source value is UNKNOWN.",
    ("phc-nigerian-pidgin-v1", "hpg-007-resp-age-2-rate-49"): "Teacher output was not parseable as the required candidate JSON.",
    ("phc-nigerian-pidgin-v1", "hpg-024-resp-count-not-one-minute"): "Known ability to drink was weakened to not observing inability.",
    ("phc-nigerian-pidgin-v1", "hpg-057-fever-malaria-and-measles"): "Known ability to drink was rendered as a double negative.",
    ("phc-nigerian-pidgin-v1", "hpg-069-cross-urgent-dehydration-ear"): "Reported ear-discharge history lost caregiver/history provenance and became a current-state statement.",
    ("phc-nigerian-pidgin-v1", "hpg-068-cross-four-pathways"): "Reported ear-discharge history lost caregiver/history provenance and became a current-state statement.",
    ("phc-nigerian-pidgin-v1", "hpg-013-resp-chest-hiv-negative"): "Pulse oximeter unavailable was changed to pulse oximeter not used.",
    ("phc-nigerian-pidgin-v1", "hpg-043-fever-high-test-unavailable"): "Negative lethargy/unconsciousness wording could state that the child is not conscious.",
    ("phc-nigerian-pidgin-v1", "hpg-003-danger-vomits-everything"): "Negative cough/difficult-breathing entry used an OR construction whose second half reads positive.",
    ("phc-noisy-typed-english-v1", "hpg-037-diarrhoea-positive-drinking-reuse"): "Reversed inability to drink into ability and omitted the supplied diarrhoea duration.",
    ("phc-noisy-typed-english-v1", "hpg-056-fever-severe-stiff-neck"): "Omitted the supplied negative measles-cough observation.",
    ("phc-noisy-typed-english-v1", "hpg-059-fever-malaria-risk-unknown"): "Omitted the supplied negative measles-cough observation.",
    ("phc-noisy-typed-english-v1", "hpg-070-cross-multiple-urgent"): "Reversed the supplied no-diarrhoea entry and made lethargy/unconsciousness polarity ambiguous.",
    ("phc-noisy-typed-english-v1", "hpg-009-resp-age-11-rate-50"): "Omitted chest-indrawing absence and attached that fact ID to unrelated cough-duration text.",
    ("phc-noisy-typed-english-v1", "hpg-044-fever-low-obvious-cause"): "Used unsafe predicate-suffix negation for the cough/difficult-breathing entry.",
    ("phc-telegraphic-note-v1", "hpg-065-ear-observed-pus-no-history"): "Known-negative reported ear-discharge history was weakened to no report.",
    ("phc-telegraphic-note-v1", "hpg-068-cross-four-pathways"): "Known-negative reported ear-discharge history was weakened to no report.",
    ("phc-telegraphic-note-v1", "hpg-069-cross-urgent-dehydration-ear"): "Known-negative reported ear-discharge history was weakened to no report.",
}


def _attempts() -> list[dict[str, Any]]:
    rows = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (RUN_DIR / "attempts").glob("*/terminal.json")
    ]
    if len(rows) != 250:
        raise ValueError(f"T2 review requires 250 attempts, found {len(rows)}")
    return rows


def _style(attempt: dict[str, Any]) -> str:
    return attempt["configuration_id"].split("__")[1]


def _pass_sample(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_style: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in attempts:
        if attempt["status"] == "PENDING_HUMAN_REVIEW":
            by_style[_style(attempt)].append(attempt)
    sample: list[dict[str, Any]] = []
    for style in sorted(by_style):
        ranked = sorted(
            by_style[style],
            key=lambda item: hashlib.sha256(
                f"T2|{item['attempt_id']}".encode()
            ).hexdigest(),
        )
        sample.extend(ranked[:10])
    if len(sample) != 40:
        raise ValueError("T2 pass sample must contain ten candidates per style")
    return sample


def build_review() -> dict[str, Any]:
    attempts = _attempts()
    raw_rejections = [x for x in attempts if x["status"] != "PENDING_HUMAN_REVIEW"]
    sample = _pass_sample(attempts)
    review_set = {x["attempt_id"]: x for x in (*raw_rejections, *sample)}
    if len(raw_rejections) != 30 or len(review_set) != 70:
        raise ValueError("T2 review scope drift")
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "attempts": 0, "raw_passes": 0, "raw_rejections": 0,
            "reviewed": 0, "semantic_approved": 0, "semantic_rejected": 0,
            "annotation_only_overrides": 0,
        }
    )
    for attempt in attempts:
        row = counts[_style(attempt)]
        row["attempts"] += 1
        row["raw_passes" if attempt["status"] == "PENDING_HUMAN_REVIEW" else "raw_rejections"] += 1
    decisions = []
    for attempt in review_set.values():
        style = _style(attempt)
        rationale = SEMANTIC_REJECTED.get((style, attempt["semantic_case_id"]))
        if rationale:
            decision = "SEMANTIC_REJECT"
        elif attempt["status"] == "PENDING_HUMAN_REVIEW":
            decision = "SEMANTIC_APPROVE"
            rationale = "Required deterministic-pass sample; no semantic defect identified."
        else:
            decision = "SEMANTIC_APPROVE_ANNOTATION_OVERRIDE"
            rationale = "Candidate is semantically faithful; raw rejection is annotation/lexical coverage only."
        row = counts[style]
        row["reviewed"] += 1
        if decision == "SEMANTIC_REJECT":
            row["semantic_rejected"] += 1
        else:
            row["semantic_approved"] += 1
            if decision.endswith("ANNOTATION_OVERRIDE"):
                row["annotation_only_overrides"] += 1
        decisions.append(
            {
                "attempt_id": attempt["attempt_id"],
                "semantic_case_id": attempt["semantic_case_id"],
                "strategy_id": style,
                "deterministic_status": attempt["status"],
                "error_codes": attempt["validation"]["error_codes"],
                "review_decision": decision,
                "rationale": rationale,
            }
        )
    semantic_failures = sum(x["review_decision"] == "SEMANTIC_REJECT" for x in decisions)
    if semantic_failures != 19:
        raise ValueError(f"expected 19 semantic failures, found {semantic_failures}")
    return {
        "review_schema_id": "edge-imci-structured-extraction-bulk-tranche-review-v1",
        "tranche_id": "T2",
        "status": "REMEDIATION_REQUIRED",
        "authority": "PROJECT_OWNER_DELEGATED_REVIEW",
        "generation_run_id": RUN_ID,
        "attempts": 250,
        "review_scope": {
            "all_deterministic_rejections_reviewed": 30,
            "deterministic_pass_sample_reviewed": 40,
            "pass_sample_per_style": 10,
            "total_unique_attempts_reviewed": 70,
        },
        "style_summary": dict(sorted(counts.items())),
        "semantic_failure_count": semantic_failures,
        "release_decision": "BLOCK_T3_REMEDIATE_PROMPTS_AND_VALIDATORS",
        "decisions": sorted(decisions, key=lambda x: x["attempt_id"]),
        "authorization": {
            "next_tranche_released": False,
            "training_authorized": False,
            "production_clinical_use_authorized": False,
        },
    }


def main() -> int:
    review = build_review()
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(REVIEW_PATH, review)
    REPORT_PATH.write_text(
        "# Structured-extraction bulk T2 review\n\n"
        "> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `REMEDIATION_REQUIRED` · T3, training and production clinical use are not released.\n\n"
        "T2 completed 250 attempts without transport failure: 220 raw deterministic passes and 30 raw rejections. Review covered all 30 rejections plus 10 deterministic passes per style (70 unique attempts). Nineteen candidates had semantic defects.\n\n"
        "The principal remaining problems are Pidgin acquisition/polarity phrasing, noisy-note fact omission, unsupplied nested fever detail, and telegraphic loss of caregiver ear-history provenance. Exact replacement prompts must pass a targeted gate before T3.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": review["status"], "reviewed": 70, "semantic_failures": 19}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
