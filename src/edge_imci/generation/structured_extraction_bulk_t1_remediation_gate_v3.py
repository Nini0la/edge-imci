"""Run the final three-case T1 remediation gate with exact revised prompts."""

from __future__ import annotations

import json
from typing import Any

from edge_imci.generation import structured_extraction_bulk_t1_remediation_gate as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v3"
AUTHORIZATION_PATH = ROOT / "configs/generation/structured_extraction_bulk_t1_remediation_gate_v3.json"
STYLE_CONFIGURATIONS = (
    {
        "variant_style": "NIGERIAN_ENGLISH",
        "strategy_id": "phc-nigerian-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_nigerian_english_v1_3_4.txt",
        "prompt_id": "edge-imci-phc-nigerian-english",
        "prompt_version": "1.3.4",
        "case_ids": ("hpg-068-cross-four-pathways",),
        "noise_profile": (),
    },
    {
        "variant_style": "NOISY_TYPED_ENGLISH",
        "strategy_id": "phc-noisy-typed-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_4.txt",
        "prompt_id": "edge-imci-phc-noisy-typed-english",
        "prompt_version": "1.2.4",
        "case_ids": (
            "hpg-068-cross-four-pathways",
            "hpg-075-contradiction-drinking",
        ),
        "noise_profile": (
            "ARTICLE_OMISSION",
            "PUNCTUATION_LOSS",
            "CASING_VARIATION",
            "SENTENCE_FRAGMENTS",
            "SPELLING_NOISE",
        ),
    },
)


def _load_authorization() -> dict[str, Any]:
    value = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    expected = {
        "authorization_id": "edge-imci-structured-extraction-bulk-t1-remediation-gate-v3",
        "status": "AUTHORIZED_FOR_TARGETED_EXECUTION",
        "authority": "PROJECT_OWNER_DELEGATION",
        "generation_run_id": RUN_ID,
        "maximum_remote_attempts": 3,
        "semantic_retries": False,
        "teacher_target_blind": True,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"incorrect third remediation authorization {key}")
    return value


def _configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = AUTHORIZATION_PATH
    base.EXPECTED_ATTEMPTS = 3
    base.STYLE_CONFIGURATIONS = STYLE_CONFIGURATIONS
    base.load_authorization = _load_authorization


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
