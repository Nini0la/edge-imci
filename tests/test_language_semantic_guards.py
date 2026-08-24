from __future__ import annotations

import copy
import glob
import json
from pathlib import Path

from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.language_semantic_guards import (
    _numeric_evidence_matches,
    load_style_contract,
    validate_language_semantics,
)


ROOT = Path(__file__).resolve().parents[1]


def _semantics() -> dict[str, dict]:
    return {
        row["golden_case_id"]: row for row in load_holistic_golden_suite()
    }


def _terminal(pattern: str) -> dict:
    matches = glob.glob(str(ROOT / pattern))
    assert len(matches) == 1
    return json.loads(Path(matches[0]).read_text(encoding="utf-8"))


def test_style_contract_is_bounded_and_does_not_authorize_scale_or_training() -> None:
    contract = load_style_contract()
    assert contract["authorization"] == {
        "bounded_canary_remote_calls_authorized": True,
        "maximum_remote_attempts": 12,
        "maximum_budget_usd": 1.0,
        "bulk_generation_authorized": False,
        "training_authorized": False,
    }
    assert "NIGERIAN_PIDGIN" in contract["variant_styles"]
    assert "TELEGRAPHIC_COMPRESSION" in contract["noise_profiles"]


def test_real_or_to_and_failure_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/holistic-teacher-middle-regression-gpt41-20250414-v1/"
        "attempts/*hpg-041-fever-high-positive*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NATURAL_CONVERSATIONAL_ENGLISH",
    )
    assert "LOGICAL_CONNECTOR_OR_TO_AND" in result.error_codes


def test_real_dropped_identification_qualifier_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/holistic-teacher-middle-gate-gpt41-20250414-v1/"
        "attempts/*hpg-041-fever-high-positive*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NATURAL_CONVERSATIONAL_ENGLISH",
    )
    assert "EPISTEMIC_QUALIFIER_DROPPED" in result.error_codes


def test_unknown_diarrhoea_mention_is_rejected_even_if_not_in_evidence() -> None:
    terminal = _terminal(
        "experiments/generation/holistic-teacher-middle-gate-gpt41-20250414-v1/"
        "attempts/*hpg-071-incomplete-entry-unknown*/terminal.json"
    )
    candidate = copy.deepcopy(terminal["candidate"])
    candidate["user_submission"] += " Diarrhoea status is not known."
    result = validate_language_semantics(
        candidate,
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NOISY_TYPED_ENGLISH",
    )
    assert "UNKNOWN_FIELD_MENTIONED" in result.error_codes
    assert "patient_facts.has_diarrhoea" in result.details


def test_target_side_leakage_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/holistic-teacher-middle-gate-gpt41-20250414-v1/"
        "attempts/*hpg-020-resp-post-bronchodilator-improved*/terminal.json"
    )
    candidate = copy.deepcopy(terminal["candidate"])
    candidate["user_submission"] += " Classification is cough or cold."
    result = validate_language_semantics(
        candidate,
        _semantics()[terminal["semantic_case_id"]],
        variant_style="CLINICAL_STANDARD_ENGLISH",
    )
    assert "TARGET_SIDE_INFORMATION_LEAKAGE" in result.error_codes


def test_absence_of_report_does_not_count_as_known_negative() -> None:
    terminal = _terminal(
        "experiments/generation/holistic-input-style-canary-gpt41-20250414-v1/"
        "attempts/*phc-nigerian-english-v1__hpg-041*/terminal.json"
    )
    candidate = json.loads(terminal["raw_response"])
    result = validate_language_semantics(
        candidate,
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_ENGLISH",
    )
    assert "NEGATIVE_EVIDENCE_WEAKENED_OR_DOUBLE_NEGATED" in result.error_codes


def test_noisy_double_negative_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/holistic-input-style-canary-gpt41-20250414-v1/"
        "attempts/*phc-noisy-typed-english-v1__hpg-071*/terminal.json"
    )
    candidate = json.loads(terminal["raw_response"])
    result = validate_language_semantics(
        candidate,
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NOISY_TYPED_ENGLISH",
    )
    assert "NEGATIVE_EVIDENCE_WEAKENED_OR_DOUBLE_NEGATED" in result.error_codes


def test_real_patient_for_area_malaria_risk_shift_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/holistic-input-style-remediation-gpt41-20250414-v1/"
        "attempts/*phc-nigerian-english-v1*__hpg-041*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_ENGLISH",
    )
    assert "MALARIA_RISK_CONTEXT_SHIFT" in result.error_codes


def test_real_general_ability_does_not_encode_normal_diarrhoea_drinking() -> None:
    terminal = _terminal(
        "experiments/generation/"
        "holistic-nigerian-english-v1-2-pathway-pilot-gpt41-20250414-v1/"
        "attempts/*hpg-028-diarrhoea-some-dehydration*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_ENGLISH",
    )
    assert "DIARRHOEA_DRINKING_STATUS_DISTINCTION_LOST" in result.error_codes


def test_real_negative_ear_history_weakened_to_nonreport_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/"
        "holistic-nigerian-english-v1-2-pathway-pilot-gpt41-20250414-v1/"
        "attempts/*hpg-065-ear-observed-pus-no-history*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_ENGLISH",
    )
    assert "KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT" in result.error_codes


def test_real_explicit_normal_drinking_and_positive_ear_history_pass_new_guards() -> None:
    semantics = _semantics()
    patterns = (
        "experiments/generation/"
        "holistic-nigerian-english-v1-2-pathway-pilot-gpt41-20250414-v1/"
        "attempts/*hpg-027-diarrhoea-no-dehydration*/terminal.json",
        "experiments/generation/"
        "holistic-nigerian-english-v1-2-pathway-pilot-gpt41-20250414-v1/"
        "attempts/*hpg-064-ear-chronic-discharge-14*/terminal.json",
    )
    for pattern in patterns:
        terminal = _terminal(pattern)
        result = validate_language_semantics(
            terminal["candidate"],
            semantics[terminal["semantic_case_id"]],
            variant_style="NIGERIAN_ENGLISH",
        )
        assert result.passed, result


def test_real_v13_gate_rejects_invented_negative_ear_history() -> None:
    semantics = _semantics()
    for case_id in (
        "hpg-027-diarrhoea-no-dehydration",
        "hpg-028-diarrhoea-some-dehydration",
    ):
        terminal = _terminal(
            "experiments/generation/"
            "holistic-input-style-pathway-qualification-gpt41-20250414-v1/"
            f"attempts/*{case_id}*/terminal.json"
        )
        result = validate_language_semantics(
            terminal["candidate"],
            semantics[case_id],
            variant_style="NIGERIAN_ENGLISH",
        )
        assert "UNKNOWN_FIELD_MENTIONED" in result.error_codes
        assert "ear.ear_discharge_reported" in result.details


def test_existing_approved_natural_canary_passes_new_surface_guards() -> None:
    semantics = _semantics()
    patterns = (
        "experiments/generation/holistic-teacher-middle-gate-gpt41-20250414-v1/"
        "attempts/*hpg-020-resp-post-bronchodilator-improved*/terminal.json",
        "experiments/generation/holistic-teacher-middle-regression-gpt41-20250414-v1/"
        "attempts/*hpg-014-resp-chest-hiv-positive*/terminal.json",
        "experiments/generation/holistic-teacher-middle-gate-gpt41-20250414-v1/"
        "attempts/*hpg-071-incomplete-entry-unknown*/terminal.json",
    )
    for pattern in patterns:
        terminal = _terminal(pattern)
        result = validate_language_semantics(
            terminal["candidate"],
            semantics[terminal["semantic_case_id"]],
            variant_style="NATURAL_CONVERSATIONAL_ENGLISH",
        )
        assert result.passed, result


def test_drinking_guard_accepts_explicit_status_label_and_pidgin_normal() -> None:
    semantics = _semantics()
    patterns = (
        (
            "experiments/generation/holistic-input-style-pathway-qualification-gpt41-20250414-v2/"
            "attempts/*phc-noisy-typed-english-v1*hpg-075*/terminal.json",
            "NOISY_TYPED_ENGLISH",
        ),
        (
            "experiments/generation/holistic-input-style-pathway-qualification-gpt41-20250414-v2/"
            "attempts/*phc-nigerian-pidgin-v1*hpg-027*/terminal.json",
            "NIGERIAN_PIDGIN",
        ),
    )
    for pattern, style in patterns:
        terminal = _terminal(pattern)
        result = validate_language_semantics(
            terminal["candidate"],
            semantics[terminal["semantic_case_id"]],
            variant_style=style,
        )
        assert "DIARRHOEA_DRINKING_STATUS_DISTINCTION_LOST" not in result.error_codes


def test_double_negative_guard_rejects_no_inability() -> None:
    terminal = _terminal(
        "experiments/generation/holistic-input-style-pathway-qualification-gpt41-20250414-v2/"
        "attempts/*phc-telegraphic-note-v1*hpg-065*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="TELEGRAPHIC_PHC_NOTE",
    )
    assert "NEGATIVE_EVIDENCE_WEAKENED_OR_DOUBLE_NEGATED" in result.error_codes


def test_bulk_t1_positive_cough_entry_polarity_reversal_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v3/"
        "attempts/*phc-nigerian-english-v1*__hpg-016*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_ENGLISH",
    )
    assert "COUGH_ENTRY_POLARITY_REVERSED" in result.error_codes


def test_bulk_t1_initial_and_recurrent_wheeze_conflation_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v3/"
        "attempts/*phc-nigerian-pidgin-v1*__hpg-020*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_PIDGIN",
    )
    assert "WHEEZING_POLARITY_REVERSED" in result.error_codes
    assert "WHEEZING_AND_RECURRENT_WHEEZE_CONFLATED" in result.error_codes
    assert "MEASUREMENT_OR_DURATION_SHIFT" in result.error_codes
    assert "respiratory.cough_duration_days" in result.details


def test_bulk_t1_unable_to_drink_polarity_reversal_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v3/"
        "attempts/*phc-telegraphic-note-v1*__hpg-037*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="TELEGRAPHIC_PHC_NOTE",
    )
    assert "DANGER_DRINKING_POLARITY_REVERSED" in result.error_codes


def test_bulk_t1_known_negative_ear_problem_weakened_to_nonreport_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v3/"
        "attempts/*phc-nigerian-pidgin-v1*__hpg-071*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_PIDGIN",
    )
    assert "KNOWN_NEGATIVE_EAR_PROBLEM_WEAKENED_TO_NONREPORT" in result.error_codes


def test_bulk_t1_generalized_rash_polarity_reversal_is_rejected() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v3/"
        "attempts/*phc-noisy-typed-english-v1*__hpg-068*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NOISY_TYPED_ENGLISH",
    )
    assert "GENERALIZED_RASH_POLARITY_REVERSED" in result.error_codes


def test_numeric_guard_accepts_sentence_punctuation_but_not_decimal_shift() -> None:
    assert _numeric_evidence_matches(35, "The respiratory rate is 35.")
    assert _numeric_evidence_matches(38.0, "Temperature 38.0°C.")
    assert not _numeric_evidence_matches(35, "The respiratory rate is 35.5.")


def test_bulk_remediation_rejects_derived_summary_and_ear_entry_conflation() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v1/"
        "attempts/*phc-nigerian-english-v1*__hpg-068*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_ENGLISH",
    )
    assert "TARGET_SIDE_INFORMATION_LEAKAGE" in result.error_codes
    assert "EAR_PROBLEM_ENTRY_CONFLATED_WITH_NESTED_FINDING" in result.error_codes


def test_bulk_remediation_rejects_pidgin_patient_risk_context_shift() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v1/"
        "attempts/*phc-nigerian-pidgin-v1*__hpg-054*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_PIDGIN",
    )
    assert "MALARIA_RISK_CONTEXT_SHIFT" in result.error_codes


def test_bulk_remediation_rejects_nonreport_and_bacterial_existence_shift() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v1/"
        "attempts/*phc-noisy-typed-english-v1*__hpg-068*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NOISY_TYPED_ENGLISH",
    )
    assert "KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT" in result.error_codes
    assert "EPISTEMIC_QUALIFIER_DROPPED" in result.error_codes


def test_bulk_remediation_rejects_derived_no_dehydration_summary() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v1/"
        "attempts/*phc-telegraphic-note-v1*__hpg-037*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="TELEGRAPHIC_PHC_NOTE",
    )
    assert "TARGET_SIDE_INFORMATION_LEAKAGE" in result.error_codes


def test_second_remediation_rejects_no_reported_ear_discharge() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v2/"
        "attempts/*phc-nigerian-english-v1*__hpg-068*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NIGERIAN_ENGLISH",
    )
    assert "KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT" in result.error_codes


def test_second_remediation_rejects_past_only_current_cough_entry() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v2/"
        "attempts/*phc-noisy-typed-english-v1*__hpg-068*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NOISY_TYPED_ENGLISH",
    )
    assert "CURRENT_COUGH_ENTRY_SHIFTED_TO_PAST_ONLY" in result.error_codes


def test_second_remediation_rejects_no_ear_problem_reported() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-bulk-t1-remediation-gate-gpt41-20250414-v2/"
        "attempts/*phc-noisy-typed-english-v1*__hpg-075*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NOISY_TYPED_ENGLISH",
    )
    assert "KNOWN_NEGATIVE_EAR_PROBLEM_WEAKENED_TO_NONREPORT" in result.error_codes


def test_t2_remediation_rejects_stiff_neck_polarity_reversal() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-bulk-t2-remediation-gate-gpt41-20250414-v2/"
        "attempts/*phc-noisy-typed-english-v1*__hpg-056*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NOISY_TYPED_ENGLISH",
    )
    assert "STIFF_NECK_POLARITY_REVERSED" in result.error_codes


def test_t3_early_stop_rejects_vomiting_weakened_to_nonreport() -> None:
    terminal = _terminal(
        "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v5/"
        "attempts/*phc-noisy-typed-english-v1*__hpg-032*/terminal.json"
    )
    result = validate_language_semantics(
        terminal["candidate"],
        _semantics()[terminal["semantic_case_id"]],
        variant_style="NOISY_TYPED_ENGLISH",
    )
    assert "KNOWN_NEGATIVE_VOMITING_WEAKENED_TO_NONREPORT" in result.error_codes
