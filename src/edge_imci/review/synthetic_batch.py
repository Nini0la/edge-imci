"""Zero-call preparation and reconciliation for automated synthetic-data review.

The module deliberately does not submit provider jobs.  It prepares Azure/OpenAI
Responses Batch JSONL, ingests immutable provider output files, routes a stronger
adjudication batch, and exports only records that satisfy the frozen policy.
No Codex or human review is required for normal operation; ambiguous records are
held rather than promoted.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from edge_imci.generation.azure_foundry import azure_structured_output_schema
from edge_imci.generation.holistic_variants import ROOT
from edge_imci.generation.holistic_variants import SEMANTIC_CASES_SHA256
from edge_imci.generation.holistic_golden import SUITE_ID
from edge_imci.generation.shorthand_realization import assess_shorthand_realization
from edge_imci.model_io.encounter import (
    MODEL_FACING_ENCOUNTER_SCHEMA_ID,
    MODEL_TARGET_EXPORTER_ID,
    model_facing_schema_sha256,
    project_model_facing_encounter,
)
from edge_imci.training.dataset_policy import (
    DATASET_POLICY_ID,
    SPLIT_POLICY_ID,
    parent_semantic_partition,
)
from edge_imci.training.structured_extraction import (
    STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID,
    validate_structured_extraction_record,
)


REVIEW_CONTRACT_ID = "edge-imci-synthetic-language-review-v1"
REVIEW_SCHEMA_ID = "edge-imci-synthetic-language-review-output-v1"
REVIEW_SUBJECT_SCHEMA_ID = "edge-imci-synthetic-language-review-subject-v1"
REVIEW_CONTRACT_PATH = ROOT / "configs/review/synthetic_language_review_v1.json"
REVIEW_SCHEMA_PATH = (
    ROOT / "configs/review/synthetic_language_review_output_v1.schema.json"
)
REVIEW_PROMPT_PATH = ROOT / "prompts/review/synthetic_language_reviewer_v1.txt"

_STRATEGY_STYLES: dict[str, tuple[str, list[str]]] = {
    "phc-natural-complete-v1": ("NATURAL_CONVERSATIONAL_ENGLISH", []),
    "phc-concise-complete-v1": ("CLINICAL_STANDARD_ENGLISH", []),
    "phc-nigerian-english-v1": ("NIGERIAN_ENGLISH", []),
    "phc-nigerian-pidgin-v1": ("NIGERIAN_PIDGIN", []),
    "phc-noisy-typed-english-v1": (
        "NOISY_TYPED_ENGLISH",
        [
            "ARTICLE_OMISSION",
            "PUNCTUATION_LOSS",
            "CASING_VARIATION",
            "SENTENCE_FRAGMENTS",
            "SPELLING_NOISE",
        ],
    ),
    "phc-telegraphic-note-v1": (
        "TELEGRAPHIC_PHC_NOTE",
        [
            "ABBREVIATION_DENSITY_MEDIUM",
            "SENTENCE_FRAGMENTS",
            "TELEGRAPHIC_COMPRESSION",
        ],
    ),
    "phc-subjectless-unpunctuated-v1": (
        "SUBJECTLESS_UNPUNCTUATED_SHORTHAND",
        [
            "SUBJECT_OMISSION",
            "PUNCTUATION_LOSS",
            "SENTENCE_FRAGMENTS",
            "TELEGRAPHIC_COMPRESSION",
        ],
    ),
}


class ReviewPipelineError(ValueError):
    """Raised when immutable review evidence cannot be reconciled safely."""


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReviewPipelineError(f"{path} must contain one JSON object")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ReviewPipelineError(f"{path}:{line_number} must be a JSON object")
        rows.append(value)
    return rows


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _canonical_jsonl(rows: Iterable[Mapping[str, Any]]) -> str:
    return "".join(_canonical_json(dict(row)) + "\n" for row in rows)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_hash(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_jsonl(rows), encoding="utf-8")


def load_review_contract(path: Path = REVIEW_CONTRACT_PATH) -> dict[str, Any]:
    contract = _load_json(path)
    if contract.get("contract_id") != REVIEW_CONTRACT_ID:
        raise ReviewPipelineError("incorrect synthetic-language review contract ID")
    if contract.get("status") != "PREPARED_ZERO_CALL_REQUIRES_REMOTE_AUTHORIZATION":
        raise ReviewPipelineError("review contract lifecycle is not the zero-call state")
    if contract.get("review_schema_id") != REVIEW_SCHEMA_ID:
        raise ReviewPipelineError("review contract and output schema IDs differ")
    authorization = contract.get("authorization", {})
    if set(authorization) != {
        "remote_calls_authorized",
        "automatic_dataset_promotion_authorized",
        "training_authorized",
        "production_clinical_use_authorized",
    }:
        raise ReviewPipelineError("review authorization fields differ")
    if (
        authorization["remote_calls_authorized"] is not False
        or authorization["training_authorized"] is not False
        or authorization["production_clinical_use_authorized"] is not False
        or not isinstance(authorization["automatic_dataset_promotion_authorized"], bool)
    ):
        raise ReviewPipelineError("review infrastructure must not authorize remote calls or training")
    routing = contract["routing"]
    if routing.get("primary_reviews_every_parseable_candidate") is not True:
        raise ReviewPipelineError("primary automated review must cover every candidate")
    fraction = routing.get("pass_audit_fraction")
    if not isinstance(fraction, (int, float)) or not 0 <= fraction <= 1:
        raise ReviewPipelineError("pass audit fraction must be between zero and one")
    minimum_audit = routing.get("minimum_pass_audit_count_per_style")
    if not isinstance(minimum_audit, int) or minimum_audit < 0:
        raise ReviewPipelineError("minimum pass audit count per style must be nonnegative")
    if not REVIEW_PROMPT_PATH.is_file() or not REVIEW_SCHEMA_PATH.is_file():
        raise ReviewPipelineError("review prompt and output schema are required")
    return contract


_STRUCTURAL_NULL_CONTAINERS = frozenset(
    {
        "respiratory",
        "diarrhoea",
        "diarrhoea.post_rehydration",
        "fever",
        "ear",
    }
)


def _flatten_target(value: Any, prefix: str = "") -> tuple[list[dict[str, Any]], list[str]]:
    known: list[dict[str, Any]] = []
    unknown: list[str] = []
    if value is None:
        if prefix not in _STRUCTURAL_NULL_CONTAINERS:
            unknown.append(prefix)
    elif isinstance(value, dict):
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else key
            child_known, child_unknown = _flatten_target(value[key], child)
            known.extend(child_known)
            unknown.extend(child_unknown)
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            child = f"{prefix}[{index}]"
            child_known, child_unknown = _flatten_target(child_value, child)
            known.extend(child_known)
            unknown.extend(child_unknown)
    else:
        known.append({"fact_id": prefix, "value": value})
    return known, unknown


def _is_high_risk(record: Mapping[str, Any]) -> bool:
    case_id = str(record["source_case_id"]).casefold()
    if any(marker in case_id for marker in ("danger", "urgent", "severe", "incomplete", "contradiction", "out-of-scope", "oos-")):
        return True
    target = record["target"]
    danger = target.get("danger_signs") or {}
    if any(value is True for value in danger.values()):
        return True
    respiratory = target.get("respiratory") or {}
    saturation = respiratory.get("oxygen_saturation_percent")
    if isinstance(saturation, (int, float)) and saturation < 90:
        return True
    if respiratory.get("chest_indrawing") is True or respiratory.get("stridor_when_calm") is True:
        return True
    diarrhoea = target.get("diarrhoea") or {}
    if any(
        diarrhoea.get(field) in {"VERY_SLOW", "ABNORMALLY_SLEEPY", "UNABLE"}
        for field in ("drinking_status", "skin_pinch", "general_condition")
    ):
        return True
    fever = target.get("fever") or {}
    if fever.get("stiff_neck") is True or fever.get("corneal_clouding") is True:
        return True
    ear = target.get("ear") or {}
    if ear.get("tender_swelling_behind_ear") is True:
        return True
    return any(
        target.get(group) is not None
        for group in ("respiratory", "diarrhoea", "fever", "ear")
    ) and sum(target.get(group) is not None for group in ("respiratory", "diarrhoea", "fever", "ear")) >= 3


def build_review_subjects_from_canonical_records(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build review subjects from model-neutral extraction records.

    A future generation batch may construct the same subject shape before
    promotion.  Canonical records are accepted here to make the already-exported
    campaign immediately usable as reviewer calibration and dry-run material.
    """

    subjects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in records:
        record = copy.deepcopy(dict(raw))
        validate_structured_extraction_record(record)
        if record["record_schema_id"] != STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID:
            raise ReviewPipelineError("unsupported canonical extraction record")
        subject_id = record["example_id"]
        if subject_id in seen:
            raise ReviewPipelineError(f"duplicate review subject ID: {subject_id}")
        seen.add(subject_id)
        known, unknown = _flatten_target(record["target"])
        subjects.append(
            {
                "review_subject_schema_id": REVIEW_SUBJECT_SCHEMA_ID,
                "subject_id": subject_id,
                "source_case_id": record["source_case_id"],
                "variant_id": record["variant_id"],
                "partition": record["partition"],
                "variant_style": record["language_provenance"]["variant_style"],
                "candidate_text": record["input"]["content"],
                "known_facts": known,
                "unknown_fields": unknown,
                "untrusted_teacher_evidence": [],
                "deterministic_validation": {"passed": True, "error_codes": []},
                "high_risk": _is_high_risk(record),
                "canonical_record": record,
            }
        )
    return sorted(subjects, key=lambda item: item["subject_id"])


def build_review_subjects_from_generation_attempts(
    attempts: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build pre-promotion subjects from normalized generation terminals.

    Parse/transport failures contain no reviewable candidate and are omitted;
    their generation status remains exclusion evidence upstream. Deterministic
    rejections with a parseable candidate are reviewed but can never be rescued
    by this pipeline.
    """

    # Imports are local to avoid making the canonical-record path depend on the
    # historical campaign executor during ordinary use.
    from edge_imci.generation.structured_extraction_bulk_wave import campaign_semantics

    semantics = campaign_semantics()
    subjects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in attempts:
        terminal = copy.deepcopy(dict(raw))
        candidate = terminal.get("candidate")
        if not isinstance(candidate, dict):
            continue
        case_id = terminal.get("semantic_case_id")
        if case_id not in semantics:
            raise ReviewPipelineError(f"generation attempt has unknown semantic case: {case_id}")
        strategy_id = (terminal.get("prompt") or {}).get("strategy_id")
        if strategy_id not in _STRATEGY_STYLES:
            raise ReviewPipelineError(f"generation attempt has unknown strategy: {strategy_id}")
        variant_style, noise_profile = _STRATEGY_STYLES[strategy_id]
        variant_suffix = str(terminal["request_id"]).rsplit("__variant-", 1)[-1]
        if not variant_suffix.isdigit():
            raise ReviewPipelineError("generation request does not identify a variant slot")
        variant_id = f"{case_id}__{strategy_id}__v{int(variant_suffix):04d}"
        example_id = f"extract__{variant_id}"
        if example_id in seen:
            raise ReviewPipelineError(f"duplicate generated review subject: {example_id}")
        seen.add(example_id)
        semantic = semantics[case_id]
        target = project_model_facing_encounter(semantic)
        prompt = terminal["prompt"]
        teacher = terminal["teacher"]
        if str(case_id).startswith("oos-extract-"):
            semantic_suite_id = "edge-imci-structured-extraction-out-of-scope-parents-v1"
            semantic_suite_sha = _canonical_hash(semantic)
        else:
            semantic_suite_id = SUITE_ID
            semantic_suite_sha = SEMANTIC_CASES_SHA256
        provisional_record = {
            "record_schema_id": STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID,
            "example_id": example_id,
            "source_case_id": case_id,
            "variant_id": variant_id,
            "partition": parent_semantic_partition(case_id),
            "input": {"role": "user", "content": candidate["user_submission"]},
            "language_provenance": {
                "variant_style": variant_style,
                "noise_profile": noise_profile,
                "style_contract_id": "edge-imci-input-language-style-contract-v1",
            },
            "target": target,
            "provenance": {
                "semantic_suite_id": semantic_suite_id,
                "semantic_suite_sha256": semantic_suite_sha,
                "semantic_record_schema_id": semantic["record_schema_id"],
                "variant_run_id": terminal["generation_run_id"],
                "teacher_provider": teacher["provider"],
                "teacher_model": teacher["model"],
                "teacher_snapshot": teacher["snapshot"],
                "prompt_id": prompt["prompt_id"],
                "prompt_version": prompt["prompt_version"],
                "prompt_sha256": prompt["prompt_sha256"],
                "target_schema_id": MODEL_FACING_ENCOUNTER_SCHEMA_ID,
                "target_schema_sha256": model_facing_schema_sha256(),
                "target_exporter_id": MODEL_TARGET_EXPORTER_ID,
                "dataset_policy_id": DATASET_POLICY_ID,
                "split_policy_id": SPLIT_POLICY_ID,
            },
            "eligibility": {"corpus_candidate": True, "training": False},
        }
        validate_structured_extraction_record(provisional_record)
        known, unknown = _flatten_target(target)
        deterministic = terminal.get("validation") or {}
        subjects.append(
            {
                "review_subject_schema_id": REVIEW_SUBJECT_SCHEMA_ID,
                "subject_id": example_id,
                "source_case_id": case_id,
                "variant_id": variant_id,
                "partition": provisional_record["partition"],
                "variant_style": variant_style,
                "candidate_text": candidate["user_submission"],
                "known_facts": known,
                "unknown_fields": unknown,
                "untrusted_teacher_evidence": copy.deepcopy(
                    candidate.get("fact_evidence") or []
                ),
                "deterministic_validation": {
                    "passed": bool(deterministic.get("deterministic_pass")),
                    "error_codes": list(deterministic.get("error_codes") or []),
                },
                "high_risk": _is_high_risk(provisional_record),
                "canonical_record": provisional_record,
            }
        )
    return sorted(subjects, key=lambda item: item["subject_id"])


def _validate_subject(subject: Mapping[str, Any]) -> None:
    required = {
        "review_subject_schema_id",
        "subject_id",
        "source_case_id",
        "variant_id",
        "partition",
        "variant_style",
        "candidate_text",
        "known_facts",
        "unknown_fields",
        "untrusted_teacher_evidence",
        "deterministic_validation",
        "high_risk",
        "canonical_record",
    }
    if set(subject) != required:
        raise ReviewPipelineError(
            f"review subject fields differ: {sorted(set(subject) ^ required)}"
        )
    if subject["review_subject_schema_id"] != REVIEW_SUBJECT_SCHEMA_ID:
        raise ReviewPipelineError("incorrect review subject schema ID")
    if not subject["subject_id"] or not subject["candidate_text"]:
        raise ReviewPipelineError("review subject requires identity and candidate text")
    fact_ids = [item.get("fact_id") for item in subject["known_facts"]]
    if not fact_ids or len(fact_ids) != len(set(fact_ids)):
        raise ReviewPipelineError("review subject known facts must be nonempty and unique")
    unknown_fields = subject["unknown_fields"]
    if (
        not isinstance(unknown_fields, list)
        or any(not isinstance(field, str) or not field for field in unknown_fields)
        or len(unknown_fields) != len(set(unknown_fields))
        or any(field in _STRUCTURAL_NULL_CONTAINERS for field in unknown_fields)
    ):
        raise ReviewPipelineError(
            "review subject unknown fields must be unique scalar observations"
        )
    validate_structured_extraction_record(dict(subject["canonical_record"]))


def _review_package(subject: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "subject_id": subject["subject_id"],
        "source_case_id": subject["source_case_id"],
        "requested_style": subject["variant_style"],
        "expected_risk_level": "HIGH" if subject["high_risk"] else "LOW",
        "known_facts": subject["known_facts"],
        "unknown_fields": subject["unknown_fields"],
        "candidate_note": subject["candidate_text"],
        "untrusted_teacher_evidence": subject["untrusted_teacher_evidence"],
    }


def _provider_review_schema(subject: Mapping[str, Any]) -> dict[str, Any]:
    schema = azure_structured_output_schema(_load_json(REVIEW_SCHEMA_PATH))
    schema["properties"]["subject_id"]["enum"] = [subject["subject_id"]]
    fact_ids = [item["fact_id"] for item in subject["known_facts"]]
    schema["properties"]["fact_assessments"]["items"]["properties"]["fact_id"][
        "enum"
    ] = fact_ids
    return schema


def _batch_custom_id(tier: str, subject_id: str) -> str:
    digest = hashlib.sha256(f"{tier}|{subject_id}".encode("utf-8")).hexdigest()[:32]
    return f"edge-review-{tier[0].lower()}-{digest}"


def _batch_line(
    subject: Mapping[str, Any], *, tier: str, model: str, max_output_tokens: int, temperature: float
) -> dict[str, Any]:
    prompt = REVIEW_PROMPT_PATH.read_text(encoding="utf-8")
    return {
        "custom_id": _batch_custom_id(tier, subject["subject_id"]),
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": model,
            "input": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": "REVIEW_PACKAGE_JSON:\n" + _canonical_json(_review_package(subject)),
                },
            ],
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "edge_imci_synthetic_language_review_v1",
                    "strict": True,
                    "schema": _provider_review_schema(subject),
                }
            },
        },
    }


def prepare_primary_review_batch(
    *,
    records_path: Path,
    output_dir: Path,
    model: str | None = None,
    contract_path: Path = REVIEW_CONTRACT_PATH,
) -> dict[str, Any]:
    """Prepare primary review JSONL and immutable subject/index artifacts."""

    contract = load_review_contract(contract_path)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"review output directory is not empty: {output_dir}")
    input_rows = _load_jsonl(records_path)
    if not input_rows:
        raise ReviewPipelineError("review input contains no records")
    if input_rows[0].get("record_schema_id") == STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID:
        subjects = build_review_subjects_from_canonical_records(input_rows)
        input_kind = "CANONICAL_RECORDS"
    elif input_rows[0].get("attempt_schema_id"):
        subjects = build_review_subjects_from_generation_attempts(input_rows)
        input_kind = "GENERATION_ATTEMPTS"
    else:
        raise ReviewPipelineError("review input is neither canonical records nor generation attempts")
    if not subjects:
        raise ReviewPipelineError("review input contains no parseable candidates")
    for subject in subjects:
        _validate_subject(subject)
    primary = contract["models"]["primary"]
    selected_model = model or primary["model"]
    lines = [
        _batch_line(
            subject,
            tier="PRIMARY",
            model=selected_model,
            max_output_tokens=primary["max_output_tokens"],
            temperature=primary["temperature"],
        )
        for subject in subjects
    ]
    index = {
        line["custom_id"]: {
            "subject_id": subject["subject_id"],
            "subject_sha256": _canonical_hash(subject),
        }
        for line, subject in zip(lines, subjects)
    }
    budget = contract["budget"]
    planned_adjudications = math.ceil(
        len(subjects) * budget["planning_adjudication_fraction"]
    )
    estimated_primary_cost = _planned_review_cost(
        count=len(subjects), tier="primary", contract=contract
    )
    estimated_adjudication_cost = _planned_review_cost(
        count=planned_adjudications, tier="adjudicator", contract=contract
    )
    estimated_review_cost = estimated_primary_cost + estimated_adjudication_cost
    if estimated_review_cost > budget["maximum_review_budget"]:
        raise PermissionError("planned unattended review exceeds the configured budget")
    _write_jsonl(output_dir / "subjects.jsonl", subjects)
    _write_jsonl(output_dir / "primary_batch_input.jsonl", lines)
    _write_json(output_dir / "primary_index.json", index)
    manifest = {
        "pipeline_id": "edge-imci-unattended-synthetic-review-v1",
        "status": "PRIMARY_BATCH_PREPARED_ZERO_CALL",
        "contract_id": REVIEW_CONTRACT_ID,
        "contract_sha256": _sha256_bytes(contract_path.read_bytes()),
        "review_prompt_sha256": _sha256_bytes(REVIEW_PROMPT_PATH.read_bytes()),
        "review_schema_sha256": _sha256_bytes(REVIEW_SCHEMA_PATH.read_bytes()),
        "subject_count": len(subjects),
        "input_kind": input_kind,
        "primary_model": selected_model,
        "review_cost_estimate": {
            "currency": budget["currency"],
            "primary_usd": round(estimated_primary_cost, 6),
            "planned_adjudication_usd": round(estimated_adjudication_cost, 6),
            "total_usd": round(estimated_review_cost, 6),
            "maximum_review_budget_usd": budget["maximum_review_budget"],
            "estimate_only": True,
        },
        "assets": {
            "subjects.jsonl": _sha256_bytes((output_dir / "subjects.jsonl").read_bytes()),
            "primary_batch_input.jsonl": _sha256_bytes(
                (output_dir / "primary_batch_input.jsonl").read_bytes()
            ),
            "primary_index.json": _sha256_bytes(
                (output_dir / "primary_index.json").read_bytes()
            ),
        },
        "authorization": copy.deepcopy(contract["authorization"]),
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def _extract_response_text(body: Mapping[str, Any]) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    texts: list[str] = []
    for item in body.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if content.get("type") == "output_text" and isinstance(text, str):
                texts.append(text)
    if not texts:
        raise ReviewPipelineError("batch response contains no output text")
    return "".join(texts)


def _validate_review(review: dict[str, Any], subject: Mapping[str, Any]) -> None:
    Draft202012Validator(_load_json(REVIEW_SCHEMA_PATH)).validate(review)
    if review["review_schema_id"] != REVIEW_SCHEMA_ID:
        raise ReviewPipelineError("incorrect automated review schema ID")
    if review["subject_id"] != subject["subject_id"]:
        raise ReviewPipelineError("automated review belongs to another subject")
    expected_risk = "HIGH" if subject["high_risk"] else "LOW"
    if review["risk_level"] != expected_risk:
        raise ReviewPipelineError("automated review risk label differs from deterministic routing")
    expected = {item["fact_id"] for item in subject["known_facts"]}
    assessments = review["fact_assessments"]
    actual = [item["fact_id"] for item in assessments]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ReviewPipelineError("automated review fact assessment set is incomplete")
    text = subject["candidate_text"]
    for item in assessments:
        evidence = item["evidence_text"]
        if item["status"] == "MATCHED":
            if not evidence or evidence not in text or item["issue_code"] is not None:
                raise ReviewPipelineError("MATCHED fact assessment has invalid evidence")
        elif item["issue_code"] is None:
            raise ReviewPipelineError("non-MATCHED fact assessment requires an issue code")
        elif item["issue_code"] not in review["error_codes"]:
            raise ReviewPipelineError("fact issue code is absent from top-level error codes")
    if review["unknown_violations"] and "UNKNOWN_RENDERED_AS_KNOWN" not in review["error_codes"]:
        raise ReviewPipelineError("unknown-field violations require their top-level error code")
    if review["unsupported_claims"] and "UNSUPPORTED_CLAIM" not in review["error_codes"]:
        raise ReviewPipelineError("unsupported claims require their top-level error code")
    if review["style_assessment"] != "PASS" and not (
        {"STYLE_MISMATCH", "UNNATURAL_OR_UNUSABLE_LANGUAGE", "EVIDENCE_AMBIGUOUS"}
        & set(review["error_codes"])
    ):
        raise ReviewPipelineError("style failure or uncertainty requires a style error code")
    clean = (
        not review["error_codes"]
        and all(item["status"] == "MATCHED" for item in assessments)
        and not review["unknown_violations"]
        and not review["unsupported_claims"]
        and review["style_assessment"] == "PASS"
    )
    if (review["verdict"] == "PASS") != clean:
        raise ReviewPipelineError("automated review verdict is inconsistent with its findings")


def _ingest_batch_output(
    *,
    output_path: Path,
    index: Mapping[str, Any],
    subjects: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = _load_jsonl(output_path)
    seen: set[str] = set()
    receipts: list[dict[str, Any]] = []
    for row in rows:
        custom_id = row.get("custom_id")
        if custom_id not in index:
            raise ReviewPipelineError(f"unexpected batch custom_id: {custom_id}")
        if custom_id in seen:
            raise ReviewPipelineError(f"duplicate batch custom_id: {custom_id}")
        seen.add(custom_id)
        subject_id = index[custom_id]["subject_id"]
        subject = subjects[subject_id]
        receipt: dict[str, Any] = {
            "custom_id": custom_id,
            "subject_id": subject_id,
            "status": "INVALID",
            "review": None,
            "error": None,
            "usage": {},
        }
        try:
            response = row.get("response") or {}
            if row.get("error") is not None or response.get("status_code") != 200:
                raise ReviewPipelineError("provider batch item failed")
            body = response.get("body") or {}
            receipt["usage"] = copy.deepcopy(body.get("usage") or {})
            raw = _extract_response_text(body)
            review = json.loads(raw)
            if not isinstance(review, dict):
                raise ReviewPipelineError("automated review is not a JSON object")
            _validate_review(review, subject)
        except (json.JSONDecodeError, ReviewPipelineError, ValidationError, TypeError, ValueError) as exc:
            receipt["error"] = type(exc).__name__
        else:
            receipt["status"] = "VALID"
            receipt["review"] = review
        receipts.append(receipt)
    for custom_id, item in index.items():
        if custom_id not in seen:
            receipts.append(
                {
                    "custom_id": custom_id,
                    "subject_id": item["subject_id"],
                    "status": "MISSING",
                    "review": None,
                    "error": "MISSING_BATCH_RESULT",
                    "usage": {},
                }
            )
    return sorted(receipts, key=lambda item: item["subject_id"])


def _audit_selected(subject_id: str, *, seed: str, fraction: float) -> bool:
    bucket = int(hashlib.sha256(f"{seed}|{subject_id}".encode()).hexdigest()[:12], 16)
    return bucket / float(16**12) < fraction


def _audit_subject_ids(
    subjects: Iterable[Mapping[str, Any]],
    *,
    seed: str,
    fraction: float,
    minimum_per_style: int,
) -> set[str]:
    by_style: dict[str, list[str]] = defaultdict(list)
    for subject in subjects:
        by_style[subject["variant_style"]].append(subject["subject_id"])
    selected: set[str] = set()
    for style, subject_ids in by_style.items():
        ranked = sorted(
            subject_ids,
            key=lambda subject_id: hashlib.sha256(
                f"{seed}|{style}|{subject_id}".encode("utf-8")
            ).hexdigest(),
        )
        count = min(len(ranked), max(minimum_per_style, math.ceil(len(ranked) * fraction)))
        selected.update(ranked[:count])
    return selected


def _planned_review_cost(*, count: int, tier: str, contract: Mapping[str, Any]) -> float:
    budget = contract["budget"]
    tokens = budget["planning_tokens_per_review"]
    rates = budget["batch_rates_per_million_tokens"][tier]
    return count * (
        tokens["input"] * rates["input"] + tokens["output"] * rates["output"]
    ) / 1_000_000


def _usage_cost(
    receipts: Iterable[Mapping[str, Any]], *, tier: str, contract: Mapping[str, Any]
) -> float:
    rates = contract["budget"]["batch_rates_per_million_tokens"][tier]
    return sum(
        (
            ((item.get("usage") or {}).get("input_tokens", 0) or 0) * rates["input"]
            + ((item.get("usage") or {}).get("output_tokens", 0) or 0) * rates["output"]
        )
        / 1_000_000
        for item in receipts
    )


def ingest_primary_reviews(
    *,
    pipeline_dir: Path,
    primary_output_path: Path,
    adjudicator_model: str | None = None,
    contract_path: Path = REVIEW_CONTRACT_PATH,
) -> dict[str, Any]:
    """Ingest primary output and prepare the independently routed adjudication batch."""

    contract = load_review_contract(contract_path)
    subjects_list = _load_jsonl(pipeline_dir / "subjects.jsonl")
    subjects = {item["subject_id"]: item for item in subjects_list}
    index = _load_json(pipeline_dir / "primary_index.json")
    receipts = _ingest_batch_output(
        output_path=primary_output_path, index=index, subjects=subjects
    )
    receipt_by_subject = {item["subject_id"]: item for item in receipts}
    routing = contract["routing"]
    pass_subjects = [
        subject
        for subject in subjects_list
        if receipt_by_subject[subject["subject_id"]]["status"] == "VALID"
        and receipt_by_subject[subject["subject_id"]]["review"]["verdict"] == "PASS"
    ]
    audited_pass_ids = _audit_subject_ids(
        pass_subjects,
        seed=routing["pass_audit_seed"],
        fraction=routing["pass_audit_fraction"],
        minimum_per_style=routing["minimum_pass_audit_count_per_style"],
    )
    routed: list[dict[str, Any]] = []
    route_reasons: dict[str, list[str]] = {}
    for subject in subjects_list:
        receipt = receipt_by_subject[subject["subject_id"]]
        reasons: list[str] = []
        review = receipt.get("review")
        if receipt["status"] != "VALID":
            reasons.append("PRIMARY_INVALID_OR_MISSING")
        elif review["verdict"] in {"FAIL", "UNCERTAIN"} and routing[
            "adjudicate_primary_fail_or_uncertain"
        ]:
            reasons.append(f"PRIMARY_{review['verdict']}")
        if subject["high_risk"] and routing["adjudicate_all_high_risk"]:
            reasons.append("HIGH_RISK")
        if (
            receipt["status"] == "VALID"
            and review["verdict"] == "PASS"
            and subject["subject_id"] in audited_pass_ids
        ):
            reasons.append("DETERMINISTIC_PASS_AUDIT")
        if reasons and receipt["status"] == "VALID":
            routed.append(subject)
            route_reasons[subject["subject_id"]] = list(dict.fromkeys(reasons))
    adjudicator = contract["models"]["adjudicator"]
    selected_model = adjudicator_model or adjudicator["model"]
    primary_usage_cost = _usage_cost(receipts, tier="primary", contract=contract)
    primary_budget_cost = max(
        primary_usage_cost,
        _planned_review_cost(count=len(subjects_list), tier="primary", contract=contract),
    )
    adjudication_cost = _planned_review_cost(
        count=len(routed), tier="adjudicator", contract=contract
    )
    projected_review_cost = primary_budget_cost + adjudication_cost
    if projected_review_cost > contract["budget"]["maximum_review_budget"]:
        raise PermissionError("routed adjudication would exceed the review budget")
    lines = [
        _batch_line(
            subject,
            tier="ADJUDICATOR",
            model=selected_model,
            max_output_tokens=adjudicator["max_output_tokens"],
            temperature=adjudicator["temperature"],
        )
        for subject in routed
    ]
    adjudication_index = {
        line["custom_id"]: {
            "subject_id": subject["subject_id"],
            "subject_sha256": _canonical_hash(subject),
            "route_reasons": route_reasons[subject["subject_id"]],
        }
        for line, subject in zip(lines, routed)
    }
    _write_jsonl(pipeline_dir / "primary_reviews.jsonl", receipts)
    _write_jsonl(pipeline_dir / "adjudicator_batch_input.jsonl", lines)
    _write_json(pipeline_dir / "adjudicator_index.json", adjudication_index)
    summary = {
        "status": "ADJUDICATOR_BATCH_PREPARED_ZERO_CALL",
        "primary_subjects": len(subjects_list),
        "valid_primary_reviews": sum(item["status"] == "VALID" for item in receipts),
        "invalid_or_missing_primary_reviews": sum(
            item["status"] != "VALID" for item in receipts
        ),
        "adjudicator_subjects": len(routed),
        "adjudicator_model": selected_model,
        "route_reason_counts": dict(
            sorted(Counter(reason for values in route_reasons.values() for reason in values).items())
        ),
        "audited_pass_subjects": len(audited_pass_ids),
        "projected_review_cost": {
            "currency": contract["budget"]["currency"],
            "primary_usd": round(primary_budget_cost, 6),
            "adjudication_usd": round(adjudication_cost, 6),
            "total_usd": round(projected_review_cost, 6),
            "maximum_review_budget_usd": contract["budget"]["maximum_review_budget"],
            "estimate_only": True,
        },
    }
    _write_json(pipeline_dir / "primary_ingest_summary.json", summary)
    return summary


def _review_error_codes(receipt: Mapping[str, Any]) -> set[str]:
    review = receipt.get("review")
    return set(review["error_codes"]) if isinstance(review, dict) else set()


def finalize_review_pipeline(
    *,
    pipeline_dir: Path,
    adjudicator_output_path: Path | None,
    contract_path: Path = REVIEW_CONTRACT_PATH,
) -> dict[str, Any]:
    """Resolve reviews conservatively and export approved records only if gates pass."""

    contract = load_review_contract(contract_path)
    subjects_list = _load_jsonl(pipeline_dir / "subjects.jsonl")
    subjects = {item["subject_id"]: item for item in subjects_list}
    primary = {
        item["subject_id"]: item
        for item in _load_jsonl(pipeline_dir / "primary_reviews.jsonl")
    }
    adjudicator_index = _load_json(pipeline_dir / "adjudicator_index.json")
    if adjudicator_index:
        if adjudicator_output_path is None:
            raise ReviewPipelineError("adjudicator batch output is required")
        adjudicator_rows = _ingest_batch_output(
            output_path=adjudicator_output_path,
            index=adjudicator_index,
            subjects=subjects,
        )
    else:
        adjudicator_rows = []
    _write_jsonl(pipeline_dir / "adjudicator_reviews.jsonl", adjudicator_rows)
    adjudicator = {item["subject_id"]: item for item in adjudicator_rows}

    decisions: list[dict[str, Any]] = []
    provisional: list[dict[str, Any]] = []
    for subject in subjects_list:
        subject_id = subject["subject_id"]
        primary_receipt = primary[subject_id]
        adjudication_required = any(
            item["subject_id"] == subject_id for item in adjudicator_index.values()
        )
        decision = "HOLD"
        reasons: list[str] = []
        if not subject["deterministic_validation"]["passed"]:
            decision = "EXCLUDE"
            reasons.append("DETERMINISTIC_REJECTION")
        elif primary_receipt["status"] != "VALID":
            reasons.append("PRIMARY_INVALID_OR_MISSING")
        elif primary_receipt["review"]["verdict"] != "PASS":
            reasons.append(f"PRIMARY_{primary_receipt['review']['verdict']}")
        elif adjudication_required:
            adjudicator_receipt = adjudicator.get(subject_id)
            if adjudicator_receipt is None or adjudicator_receipt["status"] != "VALID":
                reasons.append("ADJUDICATOR_INVALID_OR_MISSING")
            elif adjudicator_receipt["review"]["verdict"] != "PASS":
                reasons.append(f"ADJUDICATOR_{adjudicator_receipt['review']['verdict']}")
            else:
                decision = "ACCEPT"
                reasons.append("PRIMARY_AND_ADJUDICATOR_PASS")
        else:
            decision = "ACCEPT"
            reasons.append("PRIMARY_PASS_NOT_ROUTED")
        if decision == "ACCEPT":
            provisional.append(subject["canonical_record"])
        decisions.append(
            {
                "subject_id": subject_id,
                "variant_style": subject["variant_style"],
                "decision": decision,
                "reasons": reasons,
                "primary_verdict": (
                    primary_receipt["review"]["verdict"]
                    if primary_receipt["status"] == "VALID"
                    else None
                ),
                "adjudicator_verdict": (
                    adjudicator[subject_id]["review"]["verdict"]
                    if subject_id in adjudicator
                    and adjudicator[subject_id]["status"] == "VALID"
                    else None
                ),
            }
        )

    acceptance = contract["acceptance"]
    gates: list[dict[str, Any]] = []
    completion_rate = sum(item["status"] == "VALID" for item in primary.values()) / max(
        1, len(subjects_list)
    )
    invalid_count = sum(item["status"] != "VALID" for item in primary.values()) + sum(
        item["status"] != "VALID" for item in adjudicator.values()
    )
    review_count = len(primary) + len(adjudicator)
    invalid_rate = invalid_count / max(1, review_count)
    gates.extend(
        [
            {
                "gate": "PRIMARY_COMPLETION_RATE",
                "value": completion_rate,
                "threshold": acceptance["minimum_batch_completion_rate"],
                "passed": completion_rate >= acceptance["minimum_batch_completion_rate"],
            },
            {
                "gate": "INVALID_REVIEW_RATE",
                "value": invalid_rate,
                "threshold": acceptance["maximum_invalid_review_rate"],
                "passed": invalid_rate <= acceptance["maximum_invalid_review_rate"],
            },
        ]
    )
    critical = set(acceptance["critical_error_codes"])
    by_style_subjects: dict[str, list[str]] = defaultdict(list)
    for subject in subjects_list:
        by_style_subjects[subject["variant_style"]].append(subject["subject_id"])
    accepted_ids = {item["subject_id"] for item in decisions if item["decision"] == "ACCEPT"}
    style_reports: dict[str, Any] = {}
    for style, subject_ids in sorted(by_style_subjects.items()):
        style_acceptance = len(set(subject_ids) & accepted_ids) / len(subject_ids)
        critical_ids = {
            subject_id
            for subject_id in subject_ids
            if _review_error_codes(primary[subject_id]) & critical
            or _review_error_codes(adjudicator.get(subject_id, {})) & critical
        }
        critical_rate = len(critical_ids) / len(subject_ids)
        style_primary = [primary[subject_id] for subject_id in subject_ids]
        style_adjudicator = [
            adjudicator[subject_id] for subject_id in subject_ids if subject_id in adjudicator
        ]
        style_decisions = [item for item in decisions if item["subject_id"] in subject_ids]
        style_reports[style] = {
            "subjects": len(subject_ids),
            "deterministic_passes": sum(
                subjects[subject_id]["deterministic_validation"]["passed"]
                for subject_id in subject_ids
            ),
            "primary_valid": sum(item["status"] == "VALID" for item in style_primary),
            "primary_verdicts": dict(
                sorted(
                    Counter(
                        item["review"]["verdict"]
                        for item in style_primary
                        if item["status"] == "VALID"
                    ).items()
                )
            ),
            "adjudicated": len(style_adjudicator),
            "adjudicator_verdicts": dict(
                sorted(
                    Counter(
                        item["review"]["verdict"]
                        for item in style_adjudicator
                        if item["status"] == "VALID"
                    ).items()
                )
            ),
            "decisions": dict(
                sorted(Counter(item["decision"] for item in style_decisions).items())
            ),
            "acceptance_rate": style_acceptance,
            "critical_error_rate": critical_rate,
            "usage": {
                "primary_input_tokens": sum(
                    (item.get("usage") or {}).get("input_tokens", 0) or 0
                    for item in style_primary
                ),
                "primary_output_tokens": sum(
                    (item.get("usage") or {}).get("output_tokens", 0) or 0
                    for item in style_primary
                ),
                "adjudicator_input_tokens": sum(
                    (item.get("usage") or {}).get("input_tokens", 0) or 0
                    for item in style_adjudicator
                ),
                "adjudicator_output_tokens": sum(
                    (item.get("usage") or {}).get("output_tokens", 0) or 0
                    for item in style_adjudicator
                ),
            },
            "estimated_cost_usd": round(
                _usage_cost(style_primary, tier="primary", contract=contract)
                + _usage_cost(style_adjudicator, tier="adjudicator", contract=contract),
                6,
            ),
        }
        if style == "SUBJECTLESS_UNPUNCTUATED_SHORTHAND":
            realizations = [
                assess_shorthand_realization(subjects[subject_id]["candidate_text"])
                for subject_id in subject_ids
            ]
            accepted_realizations = [
                realization
                for subject_id, realization in zip(subject_ids, realizations)
                if subject_id in accepted_ids
            ]
            style_reports[style]["realization"] = {
                "assessed": len(realizations),
                "subject_omission_rate": sum(
                    item["subject_omission"] for item in realizations
                ) / len(realizations),
                "punctuation_loss_rate": sum(
                    item["punctuation_loss"] for item in realizations
                ) / len(realizations),
                "joint_rate": sum(
                    item["joint_subject_omission_and_punctuation_loss"]
                    for item in realizations
                ) / len(realizations),
                "accepted_joint_count": sum(
                    item["joint_subject_omission_and_punctuation_loss"]
                    for item in accepted_realizations
                ),
            }
        gates.extend(
            [
                {
                    "gate": f"STYLE_ACCEPTANCE_RATE:{style}",
                    "value": style_acceptance,
                    "threshold": acceptance["minimum_acceptance_rate_per_style"],
                    "passed": style_acceptance >= acceptance["minimum_acceptance_rate_per_style"],
                },
                {
                    "gate": f"STYLE_CRITICAL_ERROR_RATE:{style}",
                    "value": critical_rate,
                    "threshold": acceptance["maximum_critical_error_rate_per_style"],
                    "passed": critical_rate <= acceptance["maximum_critical_error_rate_per_style"],
                },
            ]
        )
    run_ids = {
        subject["canonical_record"]["provenance"]["variant_run_id"]
        for subject in subjects_list
    }
    if run_ids == {"edge-imci-three-gap-azure-batch-attack-v1"}:
        shorthand = style_reports.get("SUBJECTLESS_UNPUNCTUATED_SHORTHAND", {})
        accepted_joint = (shorthand.get("realization") or {}).get(
            "accepted_joint_count", 0
        )
        gates.append(
            {
                "gate": "SUBJECTLESS_UNPUNCTUATED_ACCEPTED_RECORD_QUOTA",
                "value": accepted_joint,
                "threshold": 1500,
                "passed": accepted_joint >= 1500,
            }
        )
    actual_usage_cost = _usage_cost(primary.values(), tier="primary", contract=contract) + _usage_cost(
        adjudicator.values(), tier="adjudicator", contract=contract
    )
    projected_summary_path = pipeline_dir / "primary_ingest_summary.json"
    projected_cost = 0.0
    if projected_summary_path.is_file():
        projected_cost = (_load_json(projected_summary_path).get("projected_review_cost") or {}).get(
            "total_usd", 0.0
        )
    budget_cost = max(actual_usage_cost, projected_cost)
    gates.append(
        {
            "gate": "REVIEW_BUDGET_USD",
            "value": budget_cost,
            "threshold": contract["budget"]["maximum_review_budget"],
            "passed": budget_cost <= contract["budget"]["maximum_review_budget"],
        }
    )
    gate_passed = all(item["passed"] for item in gates)
    _write_jsonl(pipeline_dir / "review_decisions.jsonl", decisions)
    _write_jsonl(pipeline_dir / "provisional_accepted_records.jsonl", provisional)
    promotion_authorized = contract["authorization"][
        "automatic_dataset_promotion_authorized"
    ]
    approved = provisional if gate_passed and promotion_authorized else []
    _write_jsonl(pipeline_dir / "approved_records.jsonl", approved)
    held_ids = [item["subject_id"] for item in decisions if item["decision"] == "HOLD"]
    excluded_ids = [item["subject_id"] for item in decisions if item["decision"] == "EXCLUDE"]
    report = {
        "pipeline_id": "edge-imci-unattended-synthetic-review-v1",
        "status": (
            "APPROVED_RECORDS_EXPORTED"
            if gate_passed and promotion_authorized
            else (
                "BLOCKED_PENDING_AUTOMATIC_PROMOTION_AUTHORIZATION"
                if gate_passed
                else "BLOCKED_BY_QUALITY_GATES"
            )
        ),
        "subject_count": len(subjects_list),
        "provisional_accept_count": len(provisional),
        "approved_record_count": len(approved),
        "held_count": len(held_ids),
        "excluded_count": len(excluded_ids),
        "held_subject_ids": held_ids,
        "excluded_subject_ids": excluded_ids,
        "gates": gates,
        "per_style": style_reports,
        "adjudication_agreement": {
            "valid_pairs": sum(
                subject_id in adjudicator
                and primary[subject_id]["status"] == "VALID"
                and adjudicator[subject_id]["status"] == "VALID"
                for subject_id in subjects
            ),
            "matching_verdicts": sum(
                subject_id in adjudicator
                and primary[subject_id]["status"] == "VALID"
                and adjudicator[subject_id]["status"] == "VALID"
                and primary[subject_id]["review"]["verdict"]
                == adjudicator[subject_id]["review"]["verdict"]
                for subject_id in subjects
            ),
        },
        "usage": {
            "primary_input_tokens": sum(
                (item.get("usage") or {}).get("input_tokens", 0) or 0
                for item in primary.values()
            ),
            "primary_output_tokens": sum(
                (item.get("usage") or {}).get("output_tokens", 0) or 0
                for item in primary.values()
            ),
            "adjudicator_input_tokens": sum(
                (item.get("usage") or {}).get("input_tokens", 0) or 0
                for item in adjudicator.values()
            ),
            "adjudicator_output_tokens": sum(
                (item.get("usage") or {}).get("output_tokens", 0) or 0
                for item in adjudicator.values()
            ),
        },
        "cost": {
            "currency": contract["budget"]["currency"],
            "usage_derived_estimate_usd": round(actual_usage_cost, 6),
            "budget_gate_estimate_usd": round(budget_cost, 6),
            "maximum_review_budget_usd": contract["budget"]["maximum_review_budget"],
            "estimate_only": True,
        },
        "authorization": {
            "training_authorized": False,
            "production_clinical_use_authorized": False,
        },
    }
    _write_json(pipeline_dir / "final_report.json", report)
    return report
