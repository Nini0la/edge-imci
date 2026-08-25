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

import os
from typing import Any

from app.extractor.base import EncounterExtractor, ExtractionError
from app.extractor.modal import ModalEncounterExtractor
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
from edge_imci.model_io.encounter import (
    model_target_to_holistic_encounter,
    validate_model_facing_encounter,
)
from edge_imci.schemas.holistic import HolisticEncounter

EXTRACTOR_MODE_ENV = "EDGEIMCI_EXTRACTOR"
MODAL_DEMO_TEXT = (
    "The child is 18 months old and has had cough or difficult breathing for 3 "
    "days. The child was calm and I counted 52 breaths in one full minute. There "
    "is no chest indrawing, no stridor when calm, no wheezing, and no history of "
    "recurrent wheeze. A pulse oximeter is available and the oxygen saturation is "
    "96 percent. The child is not HIV exposed or infected. No bronchodilator trial "
    "was done. The child is able to drink or breastfeed, does not vomit everything, "
    "has had no convulsions, is not convulsing now, and is not lethargic or "
    "unconscious. The child does not have diarrhoea, fever, or an ear problem."
)

_EXAMPLE_LABELS = {
    "hpg-001-all-negative": "Routine: all findings negative",
    "hpg-068-cross-four-pathways": "Multiple pathways",
    "hpg-071-incomplete-entry-unknown": "Incomplete assessment",
    "hpg-073-incomplete-known-urgent": "Urgent and incomplete",
    "hpg-076-complete-danger-plus-all-pathways": "Urgent complete assessment",
}


def _encounter_from_dict(
    target: dict[str, Any], encounter_id: str
) -> HolisticEncounter:
    """Validate and adapt the public model target through the canonical seam."""

    validate_model_facing_encounter(target)
    return model_target_to_holistic_encounter(target, encounter_id=encounter_id)


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
    rendered = render_worker_response(eval_result, preview.structured_encounter)

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


def create_default_service(
    extractor_mode: str | None = None,
) -> tuple[EncounterExtractor, list[dict[str, str]]]:
    """Create explicitly configured extraction and example components.

    Returns:
        A tuple of ``(extractor, example_cases)``. Each example contains the
        approved worker submission so the UI never reaches into extractor internals.
    """
    mode = (extractor_mode or os.environ.get(EXTRACTOR_MODE_ENV, "stub")).lower()
    fixture_extractor = StubEncounterExtractor()
    if mode == "stub":
        extractor: EncounterExtractor = fixture_extractor
    elif mode == "modal":
        extractor = ModalEncounterExtractor()
    else:
        raise ValueError(f"unsupported extractor mode: {mode}")

    examples = [
        {
            "id": case_id,
            "label": label,
            "text": fixture_extractor.fixture_text(case_id),
        }
        for case_id, label in _EXAMPLE_LABELS.items()
    ]
    if mode == "modal":
        examples.insert(
            0,
            {
                "id": "selected-model-demo-pneumonia",
                "label": "Selected model demo: pneumonia",
                "text": MODAL_DEMO_TEXT,
            },
        )
    return extractor, examples
