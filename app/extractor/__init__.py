"""Extractor interface and stub implementation.

The extractor is the only learned component in the EdgeIMCI pipeline. Its job
is to convert free-form PHC-worker language into a structured model-facing
encounter JSON. Everything downstream (validation, completeness, classification,
management) is deterministic.

The current ``StubEncounterExtractor`` uses a small set of frozen fixture texts
from approved holistic cases. When the real fine-tuned model is ready, it will
implement the same ``EncounterExtractor`` protocol and be swapped in without
touching the UI or deterministic pipeline.
"""

from __future__ import annotations

from app.extractor.base import EncounterExtractor, ExtractionResult
from app.extractor.stub import StubEncounterExtractor

__all__ = [
    "EncounterExtractor",
    "ExtractionResult",
    "StubEncounterExtractor",
]
