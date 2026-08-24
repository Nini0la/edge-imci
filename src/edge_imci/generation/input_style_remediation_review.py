"""Review and export the bounded v1.1 input-style remediation canary."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_style_canary import validate_style_candidate
from edge_imci.generation.holistic_style_remediation import RUN_DIR, STYLE_CONFIGURATIONS
from edge_imci.generation.holistic_variants import build_variant_record
from edge_imci.training.structured_extraction import (
    build_structured_extraction_record,
    format_structured_extraction_messages,
)


ROOT = Path(__file__).resolve().parents[3]
REVIEW_PATH = (
    ROOT
    / "configs"
    / "generation"
    / "input_language_style_remediation_review_v1.json"
)
OUTPUT_DIR = ROOT / "data" / "canary" / "input_language_style_remediation_v1"
LANGUAGE_VARIANTS_PATH = OUTPUT_DIR / "language_variants.jsonl"
CANONICAL_RECORDS_PATH = OUTPUT_DIR / "canonical_records.jsonl"
CHAT_MESSAGES_PATH = OUTPUT_DIR / "chat_messages.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
REPORT_PATH = ROOT / "docs" / "input_language_style_remediation_review_v1.md"


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
    attempts: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted((RUN_DIR / "attempts").glob("*/terminal.json")):
        attempt = _load_json(path)
        key = (attempt["semantic_case_id"], attempt["prompt"]["strategy_id"])
        if key in attempts:
            raise ValueError(f"duplicate remediation attempt: {key}")
        attempts[key] = attempt
    if len(attempts) != 6:
        raise ValueError("remediation review requires six terminal attempts")
    return attempts


def _noise_by_style() -> dict[str, tuple[str, ...]]:
    return {
        item["variant_style"]: tuple(item["noise_profile"])
        for item in STYLE_CONFIGURATIONS
    }


def build_reviewed_remediation_canary() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    review = _load_json(REVIEW_PATH)
    if review["status"] != "COMPLETE":
        raise ValueError("remediation review is incomplete")
    if review["authorization"] != {
        "additional_remote_calls_authorized": False,
        "bulk_generation_authorized": False,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }:
        raise ValueError("remediation review exceeds its authorization boundary")
    attempts = _attempts()
    requests = {
        (item["semantic_case_id"], item["strategy_id"]): item
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
    noise = _noise_by_style()
    language: list[dict[str, Any]] = []
    canonical: list[dict[str, Any]] = []
    chats: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for decision in review["candidate_decisions"]:
        case_id = decision["semantic_case_id"]
        strategy_id = decision["strategy_id"]
        attempt = attempts[(case_id, strategy_id)]
        if attempt["status"] != "PENDING_HUMAN_REVIEW":
            raise ValueError("only deterministically reviewable attempts may be reviewed")
        candidate = attempt["candidate"]
        validation = validate_style_candidate(
            candidate, semantics[case_id], parents[case_id], strategy_id
        )
        approved = decision["decision"] == "APPROVED_CORPUS_CANDIDATE"
        if approved != validation.deterministic_pass:
            raise ValueError(
                f"review and current deterministic result differ: {case_id}/{strategy_id}"
            )
        audit.append(
            {
                "semantic_case_id": case_id,
                "strategy_id": strategy_id,
                "variant_style": decision["variant_style"],
                "prompt_version": attempt["prompt"]["prompt_version"],
                "original_attempt_status": attempt["status"],
                "current_validation": validation.to_dict(),
                "review_decision": decision["decision"],
                "reason_codes": decision["reason_codes"],
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
        variant["variant_id"] = (
            f"{case_id}__{strategy_id}__prompt-v1-1__v1"
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
    return language, canonical, chats, audit


def _render_report(
    review: dict[str, Any], audit: list[dict[str, Any]], canonical: list[dict[str, Any]]
) -> str:
    counts = Counter(item["language_provenance"]["variant_style"] for item in canonical)
    lines = [
        "# EdgeIMCI input-language style remediation review v1",
        "",
        "> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `COMPLETE` · No additional remote calls, bulk generation, training, or clinical-use authorization.",
        "",
        "Six GPT-4.1 v1.1 remediation attempts retested Nigerian English and noisy typed English over the same three matched encounters. All six passed the original deterministic gate; delegated semantic review approved five and rejected one newly identified malaria-risk context shift.",
        "",
        "## Run outcome",
        "",
        "- Remote request starts: **6**",
        "- Retries: **0**",
        "- Deterministic passes at generation time: **6/6**",
        f"- Approved corpus candidates after semantic review: **{len(canonical)}/6**",
        "- Reserved exposure: **$0.18** (not billing evidence)",
        "",
        "| Recipe | Approved | Decision |",
        "|---|---:|---|",
        f"| Nigerian English v1.1 | {counts.get('NIGERIAN_ENGLISH', 0)}/3 | `REVISE_BEFORE_SCALE` |",
        f"| Noisy typed English v1.1 | {counts.get('NOISY_TYPED_ENGLISH', 0)}/3 | `APPROVED_FOR_FURTHER_CONTROLLED_GENERATION` |",
        "",
        "## Candidate decisions",
        "",
        "| Style | Case | Decision | Reason |",
        "|---|---|---|---|",
    ]
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
            "The original known-negative defect is resolved in every v1.1 output: none uses absence-of-report wording or a double negative for ability to drink or breastfeed.",
            "",
            "Noisy typed English v1.1 is approved for further controlled generation. Nigerian English v1.1 remains unapproved because the fever example recast the area's malaria-risk category as the child's individual risk. The new deterministic `MALARIA_RISK_CONTEXT_SHIFT` guard captures this failure.",
            "",
            "Nigerian English v1.2 is prepared with explicit area/setting wording but has not been remotely validated. It must pass a separately authorized bounded gate before scale.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reviewed_remediation_canary() -> dict[str, Any]:
    language, canonical, chats, audit = build_reviewed_remediation_canary()
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
        "attempt_count": len(audit),
        "approved_count": len(canonical),
        "rejected_count": len(audit) - len(canonical),
        "candidate_results": audit,
    }
    (RUN_DIR / "review_results.json").write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_PATH.write_text(_render_report(review, audit, canonical), encoding="utf-8")
    manifest = {
        "canary_id": "edge-imci-input-language-style-remediation-canary-v1",
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
        "authorization": review["authorization"],
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    write_reviewed_remediation_canary()
