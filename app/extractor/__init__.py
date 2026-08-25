"""Extractor interface with offline fixture and selected Modal implementations.

The extractor is the only learned component in the EdgeIMCI pipeline. Its job
is to convert free-form PHC-worker language into a structured model-facing
encounter JSON. Everything downstream (validation, completeness, classification,
management) is deterministic.

``StubEncounterExtractor`` uses frozen fixture texts for offline development.
``ModalEncounterExtractor`` calls the provisionally selected Qwen3-0.6B
checkpoint and enforces its run, weights, parse, and schema contract.
"""

from __future__ import annotations

from app.extractor.base import EncounterExtractor, ExtractionError, ExtractionResult
from app.extractor.modal import ModalEncounterExtractor
from app.extractor.stub import StubEncounterExtractor

__all__ = [
    "EncounterExtractor",
    "ExtractionError",
    "ExtractionResult",
    "ModalEncounterExtractor",
    "StubEncounterExtractor",
]
