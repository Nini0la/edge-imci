"""Application service layer for the EdgeIMCI prototype.

Orchestrates the full pipeline:
    free text → extractor → structured encounter → deterministic pipeline → result

The UI depends only on ``AnalysisResult`` and ``analyze_freeform_findings``.
The clinical core is never directly accessed from the frontend.
"""

from __future__ import annotations

from app.service.result import (
    AnalysisResult,
    ExtractionPreview,
    PipelineStep,
    TraceEntry,
)
from app.service.service import (
    analyze_freeform_findings,
    create_default_service,
    evaluate_extracted_findings,
    extract_freeform_findings,
)

__all__ = [
    "AnalysisResult",
    "ExtractionPreview",
    "PipelineStep",
    "TraceEntry",
    "analyze_freeform_findings",
    "create_default_service",
    "evaluate_extracted_findings",
    "extract_freeform_findings",
]
