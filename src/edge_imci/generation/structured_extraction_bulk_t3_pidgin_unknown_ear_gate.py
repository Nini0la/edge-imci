"""Gate absent versus known caregiver ear history in Pidgin after v12."""

from __future__ import annotations

import json
from typing import Any

from edge_imci.generation import structured_extraction_bulk_t1_remediation_gate as base
from edge_imci.generation.holistic_variants import ROOT


RUN_ID = "structured-extraction-bulk-t3-pidgin-unknown-ear-gate-gpt41-20250414-v1"
AUTHORIZATION_PATH = ROOT / "configs/generation/structured_extraction_bulk_t3_pidgin_unknown_ear_gate_v1.json"
STYLE_CONFIGURATIONS = (
    {"variant_style": "NIGERIAN_PIDGIN", "strategy_id": "phc-nigerian-pidgin-v1", "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_2_10.txt", "prompt_id": "edge-imci-phc-nigerian-pidgin", "prompt_version": "1.2.10", "temperature": 0.3, "case_ids": ("hpg-001-all-negative", "hpg-050-fever-duration-8-not-every-day", "hpg-065-ear-observed-pus-no-history", "hpg-071-incomplete-entry-unknown"), "noise_profile": ()},
)


def _load_authorization() -> dict[str, Any]:
    value = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    expected = {"authorization_id": "edge-imci-structured-extraction-bulk-t3-pidgin-unknown-ear-gate-v1", "status": "AUTHORIZED_FOR_TARGETED_EXECUTION", "authority": "PROJECT_OWNER_DELEGATION", "generation_run_id": RUN_ID, "maximum_remote_attempts": 4, "semantic_retries": False, "teacher_target_blind": True, "training_authorized": False, "production_clinical_use_authorized": False}
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"incorrect Pidgin unknown-ear gate authorization {key}")
    return value


def _configure() -> None:
    base.RUN_ID = RUN_ID
    base.RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
    base.AUTHORIZATION_PATH = AUTHORIZATION_PATH
    base.EXPECTED_ATTEMPTS = 4
    base.STYLE_CONFIGURATIONS = STYLE_CONFIGURATIONS
    base.load_authorization = _load_authorization


def main() -> int:
    _configure()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
