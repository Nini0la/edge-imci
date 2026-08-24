"""Run the 11-case gate after the second T3 quality stop."""

from __future__ import annotations
import json
from typing import Any
from edge_imci.generation import structured_extraction_bulk_t1_remediation_gate as base
from edge_imci.generation.holistic_variants import ROOT

RUN_ID = "structured-extraction-bulk-t3-second-early-stop-gate-gpt41-20250414-v1"
AUTHORIZATION_PATH = ROOT / "configs/generation/structured_extraction_bulk_t3_second_early_stop_gate_v1.json"
STYLE_CONFIGURATIONS = (
    {"variant_style":"NIGERIAN_PIDGIN","strategy_id":"phc-nigerian-pidgin-v1","prompt_path":"prompts/holistic_language_variants/phc_nigerian_pidgin_v1_2_6.txt","prompt_id":"edge-imci-phc-nigerian-pidgin","prompt_version":"1.2.6","temperature":0.7,"case_ids":("hpg-058-fever-measles-last-three-months",),"noise_profile":()},
    {"variant_style":"NOISY_TYPED_ENGLISH","strategy_id":"phc-noisy-typed-english-v1","prompt_path":"prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_10.txt","prompt_id":"edge-imci-phc-noisy-typed-english","prompt_version":"1.2.10","temperature":0.3,"case_ids":("hpg-065-ear-observed-pus-no-history","hpg-066-ear-mastoiditis","hpg-076-complete-danger-plus-all-pathways"),"noise_profile":("ARTICLE_OMISSION","PUNCTUATION_LOSS","CASING_VARIATION","SENTENCE_FRAGMENTS","SPELLING_NOISE")},
    {"variant_style":"TELEGRAPHIC_PHC_NOTE","strategy_id":"phc-telegraphic-note-v1","prompt_path":"prompts/holistic_language_variants/phc_telegraphic_note_v1_1_7.txt","prompt_id":"edge-imci-phc-telegraphic-note","prompt_version":"1.1.7","temperature":0.3,"case_ids":("hpg-001-all-negative","hpg-002-danger-unable-to-drink-or-breastfeed","hpg-005-danger-lethargic-or-unconscious","hpg-034-diarrhoea-severe-persistent","hpg-041-fever-high-positive","hpg-071-incomplete-entry-unknown"),"noise_profile":("ABBREVIATION_DENSITY_MEDIUM","SENTENCE_FRAGMENTS","TELEGRAPHIC_COMPRESSION")},
)

def _load_authorization() -> dict[str, Any]:
    value=json.loads(AUTHORIZATION_PATH.read_text())
    expected={"authorization_id":"edge-imci-structured-extraction-bulk-t3-second-early-stop-gate-v1","status":"AUTHORIZED_FOR_TARGETED_EXECUTION","authority":"PROJECT_OWNER_DELEGATION","generation_run_id":RUN_ID,"maximum_remote_attempts":10,"semantic_retries":False,"teacher_target_blind":True,"training_authorized":False,"production_clinical_use_authorized":False}
    for key, expected_value in expected.items():
        if value.get(key)!=expected_value: raise ValueError(f"incorrect second early-stop gate authorization {key}")
    return value

def _configure() -> None:
    base.RUN_ID=RUN_ID; base.RUN_DIR=ROOT/"experiments"/"generation"/RUN_ID
    base.AUTHORIZATION_PATH=AUTHORIZATION_PATH; base.EXPECTED_ATTEMPTS=10
    base.STYLE_CONFIGURATIONS=STYLE_CONFIGURATIONS; base.load_authorization=_load_authorization

def main() -> int:
    _configure(); return base.main()

if __name__ == "__main__": raise SystemExit(main())
