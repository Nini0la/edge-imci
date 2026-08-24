"""Application-facing result contract.

The UI depends only on this object. It never touches internal clinical modules
directly. This keeps the learned/deterministic boundary clean and lets the
frontend evolve independently of the clinical engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PipelineStep:
    """One stage of the processing pipeline for the technical trace view."""

    label: str
    kind: str  # "LEARNED" or "DETERMINISTIC"
    detail: str = ""


@dataclass(frozen=True)
class TraceEntry:
    """One deterministic reasoning step for the 'Why' view.

    Attributes:
        classification: Human-readable classification name.
        pathway: Clinical pathway (e.g. "Respiratory", "General danger signs").
        findings: Structured findings that triggered this classification.
        rule_description: Human-readable description of the deterministic rule.
        rule_id: Internal rule ID (hidden from worker view, shown in technical panel).
    """

    classification: str
    pathway: str
    findings: tuple[tuple[str, str], ...]
    rule_description: str
    rule_id: str


@dataclass(frozen=True)
class ExtractionPreview:
    """Structured interpretation presented to the worker before evaluation."""

    input_text: str
    extraction_mode: str
    matched_case_id: str | None
    structured_encounter: dict[str, Any]
    schema_valid: bool
    structured_view: list[tuple[str, str]] = field(default_factory=list)
    extraction_warnings: list[str] = field(default_factory=list)
    pipeline_trace: list[PipelineStep] = field(default_factory=list)
    error: str | None = None
    outside_supported_scope: bool = False

    @property
    def state(self) -> str:
        if self.error:
            return "ERROR"
        if self.outside_supported_scope:
            return "OUT_OF_SCOPE"
        return "READY_FOR_REVIEW"


@dataclass(frozen=True)
class AnalysisResult:
    """Full result of analyzing a free-form PHC submission.

    This is the single object the UI renders. It contains everything the
    frontend needs: the structured encounter, clinical result, rendered
    worker-facing response, decision trace, and pipeline trace.
    """

    # Input
    input_text: str
    extraction_mode: str
    matched_case_id: str | None

    # Structured encounter (model-facing JSON)
    structured_encounter: dict[str, Any]
    schema_valid: bool

    # Completeness / contradictions
    is_complete: bool
    structured_view: list[tuple[str, str]] = field(default_factory=list)
    extraction_warnings: list[str] = field(default_factory=list)
    missing_elements: dict[str, list[str]] = field(default_factory=dict)
    contradictions: list[str] = field(default_factory=list)

    # Clinical result
    is_urgent: bool = False
    classifications: list[str] = field(default_factory=list)
    urgent_actions: list[str] = field(default_factory=list)
    final_actions: list[str] = field(default_factory=list)
    deferred_actions: list[str] = field(default_factory=list)

    # Worker-facing rendered response (deterministic)
    rendered_response: str = ""

    # Decision trace (deterministic, from evaluator)
    decision_trace: list[TraceEntry] = field(default_factory=list)

    # Pipeline trace (architectural)
    pipeline_trace: list[PipelineStep] = field(default_factory=list)

    # Error state
    error: str | None = None
    outside_supported_scope: bool = False

    @property
    def state(self) -> str:
        """High-level UI state label."""
        if self.error:
            return "ERROR"
        if self.outside_supported_scope:
            return "OUT_OF_SCOPE"
        if self.is_urgent and not self.is_complete:
            return "URGENT_INCOMPLETE"
        if self.is_urgent:
            return "URGENT_COMPLETE"
        if not self.is_complete:
            return "INCOMPLETE"
        return "COMPLETE"
