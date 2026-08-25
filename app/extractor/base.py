"""Extractor interface — the learned/deterministic seam.

The extractor converts free-form PHC-worker text into a structured encounter
dictionary that conforms to the model-facing encounter schema. This is the
*only* learned component in the pipeline. Everything downstream is deterministic.

When the fine-tuned Qwen extraction model is ready, it will implement this
interface and be injected into the application service without UI or pipeline
changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ExtractionResult:
    """Output of the extraction step.

    Attributes:
        encounter: Structured encounter dict conforming to
            ``model_facing_encounter_v1.schema.json``.
        extraction_mode: Human-readable label for the extraction mode
            (e.g. ``"stub"``, ``"qwen3-0.6b-sft-v1"``).
        matched_case_id: The frozen case ID this extraction was derived from,
            or ``None`` if the extractor produced a novel extraction.
        warnings: Non-fatal extraction warnings (e.g. ambiguous phrasing).
    """

    encounter: dict[str, Any]
    extraction_mode: str
    matched_case_id: str | None = None
    warnings: tuple[str, ...] = ()


@runtime_checkable
class EncounterExtractor(Protocol):
    """Learned extractor interface: free-form text -> structured encounter.

    Implementations:
        - ``StubEncounterExtractor`` — fixture-based, for prototype development.
        - ``ModalEncounterExtractor`` — selected fine-tuned model inference.
    """

    @property
    def mode_label(self) -> str:
        """Human-readable label for this extraction mode."""
        ...

    def extract(self, free_text: str) -> ExtractionResult:
        """Convert free-form PHC-worker text into a structured encounter.

        Args:
            free_text: Raw PHC-worker assessment findings as submitted.

        Returns:
            An ``ExtractionResult`` containing the structured encounter dict,
            the extraction mode label, and optional warnings.

        Raises:
            ExtractionError: If the text cannot be parsed into a valid
                encounter structure.
        """
        ...


class ExtractionError(Exception):
    """Raised when the extractor cannot produce a valid encounter."""


INVALID_AI_INTERPRETATION_MESSAGE = (
    "The AI interpretation was invalid, so no result was used. Review the "
    "assessment findings and try again, or continue with the approved assessment "
    "pathway without AI assistance."
)

AI_SERVICE_UNAVAILABLE_MESSAGE = (
    "The AI interpretation service is unavailable, so no result was used. Try "
    "again, or continue with the approved assessment pathway without AI assistance."
)
