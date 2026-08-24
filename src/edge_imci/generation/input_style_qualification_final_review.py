"""Freeze the reviewed prompt-release decisions before bulk scheduling."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from edge_imci.generation.holistic_canary_execute import _atomic_write
from edge_imci.generation.holistic_variants import ROOT


OUTPUT = ROOT / "configs" / "generation" / "input_style_qualification_release_v1.json"
REPORT = ROOT / "docs" / "input_style_qualification_release_v1.md"

PROMPTS = (
    ("NIGERIAN_ENGLISH", "phc-nigerian-english-v1", "1.3.1", "prompts/holistic_language_variants/phc_nigerian_english_v1_3_1.txt"),
    ("NIGERIAN_PIDGIN", "phc-nigerian-pidgin-v1", "1.2.1", "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_2_1.txt"),
    ("NOISY_TYPED_ENGLISH", "phc-noisy-typed-english-v1", "1.2.1", "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_1.txt"),
    ("TELEGRAPHIC_PHC_NOTE", "phc-telegraphic-note-v1", "1.1.0", "prompts/holistic_language_variants/phc_telegraphic_note_v1_1.txt"),
)


def _terminal_counts(run_id: str, *, style_token: str | None = None) -> dict[str, int]:
    attempts_dir = ROOT / "experiments" / "generation" / run_id / "attempts"
    counts: dict[str, int] = {}
    for path in attempts_dir.glob("*/terminal.json"):
        row = json.loads(path.read_text(encoding="utf-8"))
        if style_token and style_token not in row["configuration_id"]:
            continue
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts


def build_release() -> dict[str, Any]:
    v2 = _terminal_counts(
        "holistic-input-style-pathway-qualification-gpt41-20250414-v2",
        style_token="phc-nigerian-english-v1",
    )
    v3_pidgin = _terminal_counts(
        "holistic-input-style-pathway-qualification-gpt41-20250414-v3",
        style_token="phc-nigerian-pidgin-v1",
    )
    v3_noisy = _terminal_counts(
        "holistic-input-style-pathway-qualification-gpt41-20250414-v3",
        style_token="phc-noisy-typed-english-v1",
    )
    v3_tele = _terminal_counts(
        "holistic-input-style-pathway-qualification-gpt41-20250414-v3",
        style_token="phc-telegraphic-note-v1",
    )
    if v2 != {"PENDING_HUMAN_REVIEW": 22, "DETERMINISTIC_REJECTED": 2}:
        raise ValueError(f"unexpected Nigerian English evidence: {v2}")
    if v3_pidgin != {"TRANSPORT_FAILED": 1, "PENDING_HUMAN_REVIEW": 23}:
        raise ValueError(f"unexpected Pidgin v1.1 evidence: {v3_pidgin}")
    if v3_noisy != {"PENDING_HUMAN_REVIEW": 19, "DETERMINISTIC_REJECTED": 5}:
        raise ValueError(f"unexpected noisy v1.2 evidence: {v3_noisy}")
    if v3_tele != {"PENDING_HUMAN_REVIEW": 21, "DETERMINISTIC_REJECTED": 3}:
        raise ValueError(f"unexpected telegraphic evidence: {v3_tele}")
    release_items = []
    evidence: dict[str, dict[str, Any]] = {
        "NIGERIAN_ENGLISH": {
            "semantic_approved": 24,
            "semantic_rejected": 0,
            "matched_parent_denominator": 24,
            "annotation_only_overrides": 2,
            "qualification_method": "FULL_MATCHED_PARENT_GATE",
            "evidence_runs": ["holistic-input-style-pathway-qualification-gpt41-20250414-v2"],
        },
        "NIGERIAN_PIDGIN": {
            "semantic_approved": 24,
            "semantic_rejected": 0,
            "matched_parent_denominator": 24,
            "annotation_only_overrides": 1,
            "qualification_method": "FULL_BASE_GATE_PLUS_TARGETED_PROMPT_DELTA_GATES",
            "evidence_runs": [
                "holistic-input-style-pathway-qualification-gpt41-20250414-v3",
                "holistic-input-style-pathway-qualification-replacement-gpt41-20250414-v1",
                "holistic-pidgin-v1-2-drinking-gate-gpt41-20250414-v1",
                "holistic-pidgin-v1-2-1-null-ear-gate-gpt41-20250414-v1",
            ],
            "trace_note": "The v1.1 base covered 23 usable parents; v1.2 covered the missing drinking parent; v1.2.1 re-gated both parent-null regressions. Failed attempts remain immutable evidence.",
        },
        "NOISY_TYPED_ENGLISH": {
            "semantic_approved": 23,
            "semantic_rejected": 1,
            "matched_parent_denominator": 24,
            "annotation_only_overrides": 1,
            "qualification_method": "TARGETED_GATE_PLUS_DISJOINT_SUPPLEMENT_TO_FULL_24",
            "evidence_runs": [
                "holistic-noisy-v1-2-1-null-boundary-gate-gpt41-20250414-v1",
                "holistic-noisy-v1-2-1-supplemental-qualification-gpt41-20250414-v1",
            ],
            "rejected_parent": "hpg-068-cross-four-pathways",
            "rejection_reason": "Isolated omission of multiple supplied facts; candidate remains rejected and is not promotable.",
        },
        "TELEGRAPHIC_PHC_NOTE": {
            "semantic_approved": 24,
            "semantic_rejected": 0,
            "matched_parent_denominator": 24,
            "annotation_only_overrides": 3,
            "qualification_method": "FULL_MATCHED_PARENT_GATE",
            "evidence_runs": ["holistic-input-style-pathway-qualification-gpt41-20250414-v3"],
        },
    }
    for style, strategy, version, relative in PROMPTS:
        path = ROOT / relative
        item = {
            "variant_style": style,
            "strategy_id": strategy,
            "prompt_id": f"edge-imci-{strategy.removesuffix('-v1')}",
            "prompt_version": version,
            "prompt_path": relative,
            "prompt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            **evidence[style],
            "release_decision": "QUALIFIED_FOR_GUARDED_BULK",
        }
        release_items.append(item)
    return {
        "release_schema_id": "edge-imci-input-style-qualification-release-v1",
        "status": "FROZEN_FOR_GUARDED_BULK",
        "authority": "PROJECT_OWNER_DELEGATED_EXECUTION_AND_REVIEW",
        "release_policy": {
            "minimum_semantic_approvals_per_24": 22,
            "systematic_same-class_semantic_failures_allowed": 0,
            "annotation_only_attempt_status_may_be_overridden_for_style_qualification": True,
            "annotation_or_semantic_rejected_candidates_promotable": False,
        },
        "qualified_prompts": release_items,
        "scope_guard": {
            "teacher_target_blind": True,
            "bulk_requires_separate_versioned_contract": True,
            "training_authorized": False,
            "production_clinical_use_authorized": False,
        },
    }


def write_release() -> dict[str, Any]:
    release = build_release()
    _atomic_write(OUTPUT, release)
    lines = [
        "# EdgeIMCI input-style qualification release v1",
        "",
        "> **Authority:** `PROJECT_OWNER_DELEGATED_EXECUTION_AND_REVIEW` · **Lifecycle:** `FROZEN_FOR_GUARDED_BULK` · Prompt release only; training and production clinical use remain unauthorized.",
        "",
        "| Style | Exact prompt | Semantic result | Qualification method |",
        "|---|---|---:|---|",
    ]
    for item in release["qualified_prompts"]:
        lines.append(
            f"| {item['variant_style']} | `{item['prompt_version']}` / `{item['prompt_sha256'][:12]}…` | {item['semantic_approved']}/{item['matched_parent_denominator']} | {item['qualification_method']} |"
        )
    lines.extend(
        [
            "",
            "Only candidates that pass deterministic validation and subsequent corpus review may be promoted. Annotation-only overrides above qualify the recipe, not the rejected attempt record itself. All failed, rejected, and transport-failed attempts remain immutable evidence.",
            "",
            "The exact prompt paths and full hashes are canonical in `configs/generation/input_style_qualification_release_v1.json`.",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return release


def main() -> int:
    release = write_release()
    print(json.dumps({"status": release["status"], "qualified_prompts": len(release["qualified_prompts"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
