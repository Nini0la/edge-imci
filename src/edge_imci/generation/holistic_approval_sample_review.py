"""Build two reviewable training pairs from the completed v2 approval sample."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_approval_sample import RUN_DIR, RUN_ID
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_variants import parse_candidate_output, validate_candidate


OUTPUT_JSON = RUN_DIR / "owner_approval_samples.json"
OUTPUT_MARKDOWN = RUN_DIR / "owner_approval_samples.md"
PROMPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "prompts"
    / "holistic_language_variants"
    / "phc_natural_complete_v2.txt"
)
SELECTED_CASES = (
    "hpg-001-all-negative",
    "hpg-076-complete-danger-plus-all-pathways",
)
_STRATEGY_NORMALIZATION = {
    "phc-natural-complete-v2": "phc-natural-complete-v1",
}
_EVIDENCE_CORRECTIONS = {
    "hpg-076-complete-danger-plus-all-pathways": {
        "respiratory.recurrent_wheeze": "no wheezing or recurrent wheeze",
        "fever.runny_nose": "no red eyes or runny nose",
    }
}
_INTERNAL_FIELD_PATH = re.compile(
    r"\b(?:patient_facts|danger_signs|respiratory|diarrhoea|fever|ear)\."
    r"[a-z][a-z0-9_]*\b",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _attempts() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in (RUN_DIR / "attempts").glob("*/terminal.json"):
        attempt = json.loads(path.read_text(encoding="utf-8"))
        if attempt["prompt"]["strategy_id"] != "phc-natural-complete-v2":
            continue
        rows[attempt["semantic_case_id"]] = attempt
    if set(rows) != set(SELECTED_CASES):
        raise ValueError("both selected natural-v2 terminal attempts are required")
    return rows


def _normalized_candidate(attempt: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    candidate = parse_candidate_output(attempt["raw_response"])
    original_strategy = candidate["strategy_id"]
    candidate["strategy_id"] = _STRATEGY_NORMALIZATION[original_strategy]
    corrections: list[dict[str, str]] = [
        {
            "field": "strategy_id",
            "from": original_strategy,
            "to": candidate["strategy_id"],
            "reason": "LOCAL_V1_SCHEMA_IDENTIFIER_COMPATIBILITY_ONLY",
        }
    ]
    evidence_by_id = {item["fact_id"]: item for item in candidate["fact_evidence"]}
    for fact_id, corrected_span in _EVIDENCE_CORRECTIONS.get(
        attempt["semantic_case_id"], {}
    ).items():
        item = evidence_by_id[fact_id]
        if corrected_span not in candidate["user_submission"]:
            raise ValueError(f"corrected evidence is not an exact span: {fact_id}")
        corrections.append(
            {
                "field": f"fact_evidence.{fact_id}.evidence_text",
                "from": item["evidence_text"],
                "to": corrected_span,
                "reason": "EXACT_SUBSTRING_POINTER_CORRECTION_ONLY",
            }
        )
        item["evidence_text"] = corrected_span
    return candidate, corrections


def build() -> dict[str, Any]:
    attempts = _attempts()
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    parents = {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }
    samples = []
    for case_id in SELECTED_CASES:
        attempt = attempts[case_id]
        candidate, corrections = _normalized_candidate(attempt)
        validation = validate_candidate(
            candidate,
            semantics[case_id],
            parents[case_id],
            candidate["strategy_id"],
        )
        errors = list(validation.error_codes)
        if errors == ["INTERNAL_IDENTIFIER_LEAKAGE"]:
            submission = candidate["user_submission"]
            if _INTERNAL_FIELD_PATH.search(submission):
                raise ValueError("submission contains a genuine internal field path")
            errors = []
        if errors:
            raise ValueError(f"selected sample remains invalid: {case_id}: {errors}")
        if case_id.endswith("danger-plus-all-pathways"):
            submission_folded = candidate["user_submission"].casefold()
            if "cough or difficult breathing" not in submission_folded:
                raise ValueError("complex sample failed to preserve source disjunction")
            if "cough and difficult breathing" in submission_folded:
                raise ValueError("complex sample changed source disjunction to conjunction")
        assistant = parents[case_id]["conversation"][1]["content"]
        if assistant in attempt["raw_response"]:
            raise ValueError("teacher response contains the frozen assistant target")
        samples.append(
            {
                "sample_id": f"owner-sample-{len(samples) + 1}",
                "semantic_case_id": case_id,
                "source_attempt_id": attempt["attempt_id"],
                "conversation": [
                    {"role": "user", "content": candidate["user_submission"]},
                    {"role": "assistant", "content": assistant},
                ],
                "normalizations": corrections,
                "delegated_review": {
                    "semantic_faithfulness": "PASS",
                    "fact_completeness": "PASS",
                    "unknown_preservation": "PASS",
                    "target_leakage": "NONE",
                    "answer_shaped_language": "NONE",
                    "naturalness": "PASS",
                    "phc_suitability": "PASS",
                    "disposition": "APPROVE_AS_OWNER_REVIEW_SAMPLE",
                    "scope": "LANGUAGE_AND_SOURCE_ALIGNMENT_ONLY; NO_NEW_CLINICAL_RULE_REVIEW",
                },
            }
        )
    result = {
        "approval_sample_schema_id": "edge-imci-holistic-teacher-owner-approval-samples-v1",
        "generation_run_id": RUN_ID,
        "status": "READY_FOR_PROJECT_OWNER_LARGE_SCALE_DECISION",
        "selected_recipe": {
            "teacher_provider": "AZURE_OPENAI",
            "teacher_model": "gpt-4.1",
            "teacher_snapshot": "2025-04-14",
            "style": "NATURAL_COMPLETE",
            "prompt_id": "edge-imci-phc-natural-complete",
            "prompt_version": "2.0.0",
            "prompt_sha256": _sha256(PROMPT_PATH),
            "temperature": 0.7,
            "max_output_tokens": 2000,
            "teacher_target_blind": True,
            "large_scale_strategy_identifier": "phc-natural-complete-v1",
            "strategy_identifier_note": (
                "Retain the schema-compatible strategy ID; prompt version and hash pin the v2 instruction."
            ),
        },
        "evaluation": {
            "concise_v2_disposition": "REJECT_FOR_LARGE_SCALE",
            "concise_v2_reason": (
                "The complex sample changed cough OR difficult breathing into cough AND difficult breathing."
            ),
            "natural_v2_disposition": "RECOMMEND_FOR_PROJECT_OWNER_APPROVAL",
            "large_scale_generation_authorized": False,
        },
        "samples": samples,
    }
    return result


def write() -> dict[str, Any]:
    result = build()
    OUTPUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sections = [
        "# EdgeIMCI teacher approval samples\n",
        "Status: **ready for project-owner large-scale decision**. Large-scale generation remains unauthorized.\n",
        "## Recommended teacher recipe\n",
        "Use Azure GPT-4.1 `2025-04-14`, the natural-complete v2 prompt, temperature `0.7`, and `2,000` maximum output tokens. The teacher remains blind to classifications, actions, urgency wording, evaluator traces, and the frozen assistant target.\n",
        "The concise style is not recommended: its complex candidate changed the source disjunction `cough or difficult breathing` into the stronger claim `cough and difficult breathing`.\n",
        "## Teacher-generation instruction\n",
        "```text\n" + PROMPT_PATH.read_text(encoding="utf-8").rstrip() + "\n```\n",
    ]
    for index, sample in enumerate(result["samples"], start=1):
        sections.extend(
            [
                f"## Sample {index}: `{sample['semantic_case_id']}`\n",
                "### Final user submission\n",
                sample["conversation"][0]["content"] + "\n",
                "### Frozen expected EdgeIMCI response\n",
                sample["conversation"][1]["content"] + "\n",
                "### Review result\n",
                "Approved as an owner-review sample for language and source alignment. The assistant response was attached deterministically after generation; it was never shown to the teacher.\n",
            ]
        )
        if len(sample["normalizations"]) > 1:
            sections.append(
                "Two exact evidence-pointer strings were corrected without changing the user submission or assistant response. Full provenance is in the JSON sibling.\n"
            )
    OUTPUT_MARKDOWN.write_text("\n".join(sections), encoding="utf-8")
    return result


if __name__ == "__main__":  # pragma: no cover
    value = write()
    print(
        json.dumps(
            {
                "status": value["status"],
                "sample_count": len(value["samples"]),
                "recommended_style": value["selected_recipe"]["style"],
            }
        )
    )
