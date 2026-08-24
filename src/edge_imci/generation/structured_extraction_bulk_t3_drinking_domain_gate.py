"""Run the Pidgin/noisy diarrhoea drinking-domain boundary gate after v8."""

from __future__ import annotations

import json
from typing import Any

from edge_imci.generation import structured_extraction_bulk_t1_remediation_gate as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "structured-extraction-bulk-t3-drinking-domain-gate-gpt41-20250414-v1"
AUTHORIZATION_PATH = ROOT / "configs/generation/structured_extraction_bulk_t3_drinking_domain_gate_v1.json"
CASES = ("hpg-027-diarrhoea-no-dehydration", "hpg-029-diarrhoea-severe-plan-c-under-24m", "hpg-075-contradiction-drinking")
STYLE_CONFIGURATIONS = (
    {"variant_style": "NIGERIAN_PIDGIN", "strategy_id": "phc-nigerian-pidgin-v1", "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_2_7.txt", "prompt_id": "edge-imci-phc-nigerian-pidgin", "prompt_version": "1.2.7", "temperature": 0.7, "case_ids": CASES, "noise_profile": ()},
    {"variant_style": "NOISY_TYPED_ENGLISH", "strategy_id": "phc-noisy-typed-english-v1", "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_11.txt", "prompt_id": "edge-imci-phc-noisy-typed-english", "prompt_version": "1.2.11", "temperature": 0.3, "case_ids": CASES, "noise_profile": ("ARTICLE_OMISSION", "PUNCTUATION_LOSS", "CASING_VARIATION", "SENTENCE_FRAGMENTS", "SPELLING_NOISE")},
)


def _load_authorization() -> dict[str, Any]:
    value = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    expected = {"authorization_id": "edge-imci-structured-extraction-bulk-t3-drinking-domain-gate-v1", "status": "AUTHORIZED_FOR_TARGETED_EXECUTION", "authority": "PROJECT_OWNER_DELEGATION", "generation_run_id": RUN_ID, "maximum_remote_attempts": 6, "semantic_retries": False, "teacher_target_blind": True, "training_authorized": False, "production_clinical_use_authorized": False}
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"incorrect drinking-domain gate authorization {key}")
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
