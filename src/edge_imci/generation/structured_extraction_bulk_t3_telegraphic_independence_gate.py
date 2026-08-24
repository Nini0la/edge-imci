"""Run the telegraphic independent-field gate after the v7 quality stop."""

from __future__ import annotations

import json
from typing import Any

from edge_imci.generation import structured_extraction_bulk_t1_remediation_gate as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "structured-extraction-bulk-t3-telegraphic-independence-gate-gpt41-20250414-v1"
AUTHORIZATION_PATH = ROOT / "configs/generation/structured_extraction_bulk_t3_telegraphic_independence_gate_v1.json"
STYLE_CONFIGURATIONS = (
    {
        "variant_style": "TELEGRAPHIC_PHC_NOTE",
        "strategy_id": "phc-telegraphic-note-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_telegraphic_note_v1_1_9.txt",
        "prompt_id": "edge-imci-phc-telegraphic-note",
        "prompt_version": "1.1.9",
        "temperature": 0.3,
        "case_ids": (
            "hpg-041-fever-high-positive",
            "hpg-052-fever-identified-bacterial-cause",
            "hpg-055-fever-severe-measles-cornea",
            "hpg-058-fever-measles-last-three-months",
            "hpg-076-complete-danger-plus-all-pathways",
        ),
        "noise_profile": (
            "ABBREVIATION_DENSITY_MEDIUM",
            "SENTENCE_FRAGMENTS",
            "TELEGRAPHIC_COMPRESSION",
        ),
    },
)


def _load_authorization() -> dict[str, Any]:
    value = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    expected = {
        "authorization_id": "edge-imci-structured-extraction-bulk-t3-telegraphic-independence-gate-v1",
        "status": "AUTHORIZED_FOR_TARGETED_EXECUTION",
        "authority": "PROJECT_OWNER_DELEGATION",
        "generation_run_id": RUN_ID,
        "maximum_remote_attempts": 5,
        "semantic_retries": False,
        "teacher_target_blind": True,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"incorrect telegraphic independence gate authorization {key}")
    return value


def _configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = AUTHORIZATION_PATH
    base.EXPECTED_ATTEMPTS = 5
    base.STYLE_CONFIGURATIONS = STYLE_CONFIGURATIONS
    base.load_authorization = _load_authorization


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
