"""Stub encounter extractor for prototype development.

This extractor does NOT call any model. It matches the input text against a
small set of frozen, approved fixture cases and returns the corresponding
pre-structured encounter. This is for application development only — when the
fine-tuned extraction model is ready, it will replace this stub at the
``EncounterExtractor`` boundary.

The fixture texts come from the frozen holistic product golden language
layer (``language_renderings_v1.jsonl``). No new clinical examples are invented.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.extractor.base import ExtractionError, ExtractionResult

_FIXTURES_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "stub_encounters.json"
)


def _load_fixtures() -> list[dict[str, Any]]:
    """Load frozen fixture encounters from the prototype fixture file."""

    if not _FIXTURES_PATH.exists():
        raise FileNotFoundError(f"Stub fixtures not found: {_FIXTURES_PATH}")
    data = json.loads(_FIXTURES_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Stub fixtures must be a list")
    return data


class StubEncounterExtractor:
    """Fixture-based extractor for the prototype/MVP interface.

    Matches input text against known frozen PHC-worker submissions and returns
    the pre-structured encounter. Uses normalized whitespace comparison so
    minor formatting differences don't break the match.

    The workstation can swap this for ``ModalEncounterExtractor`` without
    changing the application service or frontend contract.
    """

    def __init__(self) -> None:
        self._fixtures = _load_fixtures()
        # Build a normalized text -> fixture map for exact matching
        self._text_map: dict[str, dict[str, Any]] = {}
        for fixture in self._fixtures:
            normalized = self._normalize(fixture["user_text"])
            self._text_map[normalized] = fixture

    @property
    def mode_label(self) -> str:
        return "Prototype / stub extraction"

    def extract(self, free_text: str) -> ExtractionResult:
        """Attempt to match the input text against frozen fixture cases.

        Raises ``ExtractionError`` if no fixture matches. In the future, the
        real extractor will handle arbitrary text via model inference.
        """

        normalized = self._normalize(free_text)
        if not normalized:
            raise ExtractionError(
                "Enter the assessment findings before analyzing the encounter."
            )

        fixture = self._text_map.get(normalized)

        if fixture is None:
            raise ExtractionError(
                "No matching fixture case found. The stub extractor only "
                "recognizes approved example encounters. Use the example "
                "buttons below to load a case."
            )

        return ExtractionResult(
            encounter=fixture["encounter"],
            extraction_mode=self.mode_label,
            matched_case_id=fixture["case_id"],
        )

    def fixture_text(self, case_id: str) -> str:
        """Return the approved worker submission for one prototype example."""

        for fixture in self._fixtures:
            if fixture["case_id"] == case_id:
                return str(fixture["user_text"])
        raise KeyError(case_id)

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize whitespace for robust matching."""
        return " ".join(text.split())
