"""Thin application service that orchestrates the EdgeIMCI pipeline.

This is the single entry point for the UI. It coordinates:
    1. Extraction (learned) — free text → structured encounter
    2. Schema validation (deterministic)
    3. Completeness / contradiction (deterministic)
    4. Clinical classification (deterministic IMCI engine)
    5. Management / referral (deterministic)
    6. Worker-facing rendering (deterministic)

The clinical core is accessed only through ``evaluate_holistic_encounter`` and
the frozen language renderings. No clinical logic is duplicated or modified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.extractor.base import ExtractionError
from app.extractor.stub import StubEncounterExtractor
from app.service.render import (
    render_worker_response,
    build_decision_trace,
    build_pipeline_trace,
    format_structured_encounter,
    humanize_action,
    humanize_classification,
    humanize_missing_element,
)
from app.service.result import AnalysisResult, ExtractionPreview, PipelineStep

from edge_imci.evaluation.holistic import evaluate_holistic_encounter
from edge_imci.schemas.holistic import (
    HOLISTIC_SCHEMA_VERSION,
    HolisticEncounter,
)

_ROOT = Path(__file__).resolve().parents[2]
_RENDERINGS_PATH = (
    _ROOT / "data" / "golden" / "holistic_product_v1" / "language_renderings_v1.jsonl"
)

_EXAMPLE_LABELS = {
    "hpg-001-all-negative": "Routine: all findings negative",
    "hpg-068-cross-four-pathways": "Multiple pathways",
    "hpg-071-incomplete-entry-unknown": "Incomplete assessment",
    "hpg-073-incomplete-known-urgent": "Urgent and incomplete",
    "hpg-076-complete-danger-plus-all-pathways": "Urgent complete assessment",
}


def _load_renderings() -> dict[str, dict[str, Any]]:
    """Load frozen language renderings for worker-facing response text."""
    if not _RENDERINGS_PATH.exists():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for line in _RENDERINGS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        case_id = record["golden_case_id"]
        result[case_id] = record
    return result


def _encounter_from_dict(
    target: dict[str, Any], encounter_id: str
) -> HolisticEncounter:
    """Adapt a model-facing encounter dict to the internal HolisticEncounter.

    This mirrors the existing ``model_target_to_holistic_encounter`` adapter
    but is kept local to avoid depending on uncommitted modules.
    """
    from edge_imci.generation.holistic_golden import encounter_from_dict

    payload = dict(target)
    payload["encounter_id"] = encounter_id
    payload["schema_version"] = HOLISTIC_SCHEMA_VERSION
    return encounter_from_dict(payload)


def _is_outside_supported_scope(error: Exception) -> bool:
    message = str(error).lower()
    return "age_months must be at least 2 and less than 60" in message


def extract_freeform_findings(
    free_text: str,
    *,
    extractor: Any | None = None,
) -> ExtractionPreview:
    """Extract and validate findings for explicit worker review."""

    if extractor is None:
        extractor = StubEncounterExtractor()

    pipeline_trace: list[PipelineStep] = []

    # Step 1: Extraction (learned)
    pipeline_trace.append(
        PipelineStep(
            label="Language interpretation",
            kind="LEARNED",
            detail=f"Extractor: {extractor.mode_label}",
        )
    )

    try:
        extraction = extractor.extract(free_text)
    except ExtractionError as exc:
        pipeline_trace.extend(build_pipeline_trace(None, None, failed=True))
        return ExtractionPreview(
            input_text=free_text,
            extraction_mode=extractor.mode_label,
            matched_case_id=None,
            structured_encounter={},
            schema_valid=False,
            error=str(exc),
            pipeline_trace=pipeline_trace,
        )

    # Step 2: Schema validation (deterministic)
    pipeline_trace.append(
        PipelineStep(
            label="Structured encounter validation",
            kind="DETERMINISTIC",
            detail="Schema: model-facing-encounter-v1",
        )
    )

    encounter_id = extraction.matched_case_id or "prototype-encounter"

    try:
        _encounter_from_dict(extraction.encounter, encounter_id)
    except Exception as exc:
        pipeline_trace.extend(build_pipeline_trace(None, None, failed=True))
        if _is_outside_supported_scope(exc):
            return ExtractionPreview(
                input_text=free_text,
                extraction_mode=extraction.extraction_mode,
                matched_case_id=extraction.matched_case_id,
                structured_encounter=extraction.encounter,
                schema_valid=False,
                outside_supported_scope=True,
                pipeline_trace=pipeline_trace,
            )
        return ExtractionPreview(
            input_text=free_text,
            extraction_mode=extraction.extraction_mode,
            matched_case_id=extraction.matched_case_id,
            structured_encounter=extraction.encounter,
            schema_valid=False,
            error=f"Schema validation failed: {exc}",
            pipeline_trace=pipeline_trace,
        )

    return ExtractionPreview(
        input_text=free_text,
        extraction_mode=extraction.extraction_mode,
        matched_case_id=extraction.matched_case_id,
        structured_encounter=extraction.encounter,
        structured_view=format_structured_encounter(extraction.encounter),
        schema_valid=True,
        extraction_warnings=list(extraction.warnings),
        pipeline_trace=pipeline_trace,
    )


def evaluate_extracted_findings(preview: ExtractionPreview) -> AnalysisResult:
    """Run the deterministic engine after the worker verifies extraction."""

    if preview.error or preview.outside_supported_scope:
        rendered = ""
        if preview.outside_supported_scope:
            rendered = (
                "OUTSIDE SUPPORTED SCOPE\n\n"
                "This encounter is outside the supported EdgeIMCI major sick-child scope. "
                "Use the applicable approved age-specific pathway."
            )
        return AnalysisResult(
            input_text=preview.input_text,
            extraction_mode=preview.extraction_mode,
            matched_case_id=preview.matched_case_id,
            structured_encounter=preview.structured_encounter,
            structured_view=preview.structured_view,
            schema_valid=preview.schema_valid,
            extraction_warnings=preview.extraction_warnings,
            is_complete=False,
            error=preview.error,
            outside_supported_scope=preview.outside_supported_scope,
            rendered_response=rendered,
            pipeline_trace=preview.pipeline_trace,
        )

    encounter_id = preview.matched_case_id or "prototype-encounter"
    try:
        encounter = _encounter_from_dict(preview.structured_encounter, encounter_id)
    except Exception as exc:
        return AnalysisResult(
            input_text=preview.input_text,
            extraction_mode=preview.extraction_mode,
            matched_case_id=preview.matched_case_id,
            structured_encounter=preview.structured_encounter,
            structured_view=preview.structured_view,
            schema_valid=False,
            is_complete=False,
            error=f"Structured encounter validation failed: {exc}",
            pipeline_trace=preview.pipeline_trace,
        )

    pipeline_trace = list(preview.pipeline_trace)
    pipeline_trace.append(
        PipelineStep(
            label="Completeness / contradiction handling",
            kind="DETERMINISTIC",
            detail="Policy: imci-major-sick-child-holistic-completeness-v2",
        )
    )
    pipeline_trace.append(
        PipelineStep(
            label="Clinical classification",
            kind="DETERMINISTIC",
            detail="Engine: imci-major-sick-child-v1",
        )
    )
    pipeline_trace.append(
        PipelineStep(
            label="Management / referral",
            kind="DETERMINISTIC",
            detail="Actions derived from deterministic rules",
        )
    )
    pipeline_trace.append(
        PipelineStep(
            label="Worker-facing presentation",
            kind="DETERMINISTIC",
            detail="Grammar: edgeimci-response-grammar-v1",
        )
    )

    eval_result = evaluate_holistic_encounter(encounter)

    # Step 6: Worker-facing rendering (deterministic)
    renderings = _load_renderings()
    rendered = render_worker_response(eval_result, preview.matched_case_id, renderings)

    # Build decision trace from deterministic evidence
    decision_trace = build_decision_trace(eval_result, encounter)

    # Format structured encounter for the "How EdgeIMCI interpreted" view
    structured_view = format_structured_encounter(preview.structured_encounter)

    # Extract human-readable lists
    classifications = [
        humanize_classification(c.classification.value)
        for c in eval_result.final_classifications
    ]
    urgent_actions = [humanize_action(a.value) for a in eval_result.urgent_actions]
    final_actions = [humanize_action(a.value) for a in eval_result.final_actions]
    deferred_actions = [humanize_action(a.value) for a in eval_result.deferred_actions]

    missing: dict[str, list[str]] = {}
    for pathway, fields in eval_result.missing_elements.items():
        key = pathway.value.replace("_", " ").title()
        missing[key] = [humanize_missing_element(f) for f in fields]

    return AnalysisResult(
        input_text=preview.input_text,
        extraction_mode=preview.extraction_mode,
        matched_case_id=preview.matched_case_id,
        structured_encounter=preview.structured_encounter,
        structured_view=structured_view,
        schema_valid=True,
        extraction_warnings=preview.extraction_warnings,
        is_complete=eval_result.supported_encounter_complete,
        missing_elements=missing,
        contradictions=list(eval_result.contradictions),
        is_urgent=eval_result.urgent_action_required,
        classifications=classifications,
        urgent_actions=urgent_actions,
        final_actions=final_actions,
        deferred_actions=deferred_actions,
        rendered_response=rendered,
        decision_trace=decision_trace,
        pipeline_trace=pipeline_trace,
    )


def analyze_freeform_findings(
    free_text: str,
    *,
    extractor: Any | None = None,
) -> AnalysisResult:
    """Compatibility entry point for one-step non-interactive callers."""

    preview = extract_freeform_findings(free_text, extractor=extractor)
    return evaluate_extracted_findings(preview)


def create_default_service() -> tuple[Any, list[dict[str, str]]]:
    """Create the default service components for the prototype.

    Returns:
        A tuple of ``(extractor, example_cases)``. Each example contains the
        approved worker submission so the UI never reaches into extractor internals.
    """
    extractor = StubEncounterExtractor()
    examples = [
        {
            "id": case_id,
            "label": label,
            "text": extractor.fixture_text(case_id),
        }
        for case_id, label in _EXAMPLE_LABELS.items()
    ]
    return extractor, examples
