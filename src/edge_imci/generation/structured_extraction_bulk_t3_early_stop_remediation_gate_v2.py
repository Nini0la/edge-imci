"""Run the six-case lower-temperature gate after the early T3 stop."""

from __future__ import annotations

import json
from typing import Any

from edge_imci.generation import structured_extraction_bulk_t1_remediation_gate as base
from edge_imci.generation.holistic_variants import ROOT

RUN_ID = "structured-extraction-bulk-t3-early-stop-remediation-gate-gpt41-20250414-v2"
AUTHORIZATION_PATH = ROOT / "configs/generation/structured_extraction_bulk_t3_early_stop_remediation_gate_v2.json"
STYLE_CONFIGURATIONS = (
    {
        "variant_style": "NOISY_TYPED_ENGLISH", "strategy_id": "phc-noisy-typed-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_9.txt",
        "prompt_id": "edge-imci-phc-noisy-typed-english", "prompt_version": "1.2.9",
        "temperature": 0.3,
        "case_ids": (
            "hpg-016-resp-oximeter-89-9", "hpg-023-resp-child-not-calm",
            "hpg-032-diarrhoea-duration-13", "hpg-057-fever-malaria-and-measles",
        ),
        "noise_profile": ("ARTICLE_OMISSION", "PUNCTUATION_LOSS", "CASING_VARIATION", "SENTENCE_FRAGMENTS", "SPELLING_NOISE"),
    },
    {
        "variant_style": "TELEGRAPHIC_PHC_NOTE", "strategy_id": "phc-telegraphic-note-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_telegraphic_note_v1_1_6.txt",
        "prompt_id": "edge-imci-phc-telegraphic-note", "prompt_version": "1.1.6",
        "temperature": 0.3,
        "case_ids": ("hpg-003-danger-vomits-everything", "hpg-060-fever-test-result-unknown"),
        "noise_profile": ("ABBREVIATION_DENSITY_MEDIUM", "SENTENCE_FRAGMENTS", "TELEGRAPHIC_COMPRESSION"),
    },
)

def _load_authorization() -> dict[str, Any]:
    value = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    expected = {
        "authorization_id": "edge-imci-structured-extraction-bulk-t3-early-stop-remediation-gate-v2",
        "status": "AUTHORIZED_FOR_TARGETED_EXECUTION", "authority": "PROJECT_OWNER_DELEGATION",
        "generation_run_id": RUN_ID, "maximum_remote_attempts": 6,
        "semantic_retries": False, "teacher_target_blind": True,
        "training_authorized": False, "production_clinical_use_authorized": False,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"incorrect lower-temperature gate authorization {key}")
    return value

def _configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = AUTHORIZATION_PATH
    base.EXPECTED_ATTEMPTS = 6
    base.STYLE_CONFIGURATIONS = STYLE_CONFIGURATIONS
    base.load_authorization = _load_authorization

def main() -> int:
    _configure()
    return base.main()

if __name__ == "__main__":
    raise SystemExit(main())
