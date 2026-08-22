"""Deterministic product-level holistic golden semantic suite construction.

This module creates structured semantics only. It does not render conversation,
generate training examples, or change clinical logic.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from edge_imci.corpus_policy import CorpusUse, assert_corpus_use_allowed
from edge_imci.evaluation.holistic import (
    HOLISTIC_COMPLETENESS_POLICY_ID,
    HOLISTIC_ORACLE_ID,
    HOLISTIC_RULE_SET_ID,
    evaluate_holistic_encounter,
)
from edge_imci.information_policy.holistic_artifacts import load_holistic_artifacts
from edge_imci.schemas.case import DrinkingStatus, GeneralDangerSignObservations, SkinPinch
from edge_imci.schemas.holistic import (
    HOLISTIC_SCHEMA_VERSION,
    DehydrationAssessment,
    HolisticDiarrhoeaObservations,
    HolisticEarObservations,
    HolisticEncounter,
    HolisticFeverObservations,
    HolisticPatientFacts,
    HolisticRespiratoryObservations,
    MalariaRisk,
    MalariaTestResult,
)
from edge_imci.schemas.trajectory import CorpusRole


ROOT = Path(__file__).resolve().parents[3]
SUITE_ID = "edge-imci-holistic-product-golden-v1"
RECORD_SCHEMA_ID = "edge-imci-holistic-golden-semantic-record-v4"
GENERATOR_VERSION = "edge-imci-holistic-golden-generator-v4"
VALIDATOR_ID = "edge-imci-holistic-golden-validator-v4"
DECISION_SET_ID = "imci-major-sick-child-review-decisions-v1"
OXYGEN_REFERRAL_DISPOSITION_ID = "imci-major-sick-child-oxygen-referral-disposition-v1"
SCOPE_DISPOSITION_SET_ID = "edge-imci-holistic-golden-scope-dispositions-v1"
APPROVAL_ID = "edge-imci-holistic-product-golden-approval-v1"
APPROVED_REVIEWED_SEMANTIC_SHA256 = "e8c538ac7a82b8faae7b7e36644eb3c44751c88380621e87625d1f703c5a70a1"
GENERATION_SEED = 20260822
DEFAULT_SCOPE_DISPOSITIONS_PATH = ROOT / "configs" / "golden" / "holistic_product_golden_scope_dispositions_v1.json"
DEFAULT_SCOPE_DISPOSITIONS_YAML_PATH = DEFAULT_SCOPE_DISPOSITIONS_PATH.with_suffix(".yaml")
DEFAULT_APPROVAL_PATH = ROOT / "configs" / "golden" / "holistic_product_golden_approval_v1.json"
DEFAULT_APPROVAL_YAML_PATH = DEFAULT_APPROVAL_PATH.with_suffix(".yaml")
DEFAULT_SUITE_DIR = ROOT / "data" / "golden" / "holistic_product_v1"
DEFAULT_JSONL_PATH = DEFAULT_SUITE_DIR / "semantic_cases.jsonl"
DEFAULT_YAML_PATH = DEFAULT_SUITE_DIR / "semantic_cases.yaml"
DEFAULT_MANIFEST_PATH = DEFAULT_SUITE_DIR / "manifest.json"
DEFAULT_REVIEW_PATH = ROOT / "docs" / "product_holistic_golden_review_v1.md"


@dataclass(frozen=True)
class HolisticGoldenSpec:
    case_id: str
    why: str
    coverage: tuple[str, ...]
    encounter: HolisticEncounter | None = None
    invalid_payload: dict[str, Any] | None = None
    expected_schema_error: str | None = None
    review_decision_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (self.encounter is None) == (self.invalid_payload is None):
            raise ValueError("a golden spec must contain exactly one encounter or invalid payload")


def _values(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {_values(key): _values(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_values(item) for item in value]
    return value


def encounter_to_dict(encounter: HolisticEncounter) -> dict[str, Any]:
    return _values(asdict(encounter))


def load_scope_dispositions() -> dict[str, Any]:
    artifact = json.loads(DEFAULT_SCOPE_DISPOSITIONS_PATH.read_text(encoding="utf-8"))
    expected_pins = {
        "disposition_set_id": SCOPE_DISPOSITION_SET_ID,
        "status": "APPROVED_FOR_HACKATHON_SCOPE",
        "rule_set_id": HOLISTIC_RULE_SET_ID,
        "completeness_policy_id": HOLISTIC_COMPLETENESS_POLICY_ID,
        "review_decision_set_id": DECISION_SET_ID,
        "clinical_rule_change": False,
        "production_clinical_use_authorized": False,
    }
    for key, expected in expected_pins.items():
        if artifact.get(key) != expected:
            raise ValueError(f"incorrect holistic golden scope disposition {key}")
    dispositions = artifact.get("dispositions", [])
    if len(dispositions) != 1 or dispositions[0].get("gap_id") != "HPG-GAP-REASSESS-001":
        raise ValueError("scope disposition set must resolve exactly HPG-GAP-REASSESS-001")
    if dispositions[0].get("status") != "RESOLVED_BY_PRODUCT_SCOPE":
        raise ValueError("HPG-GAP-REASSESS-001 must remain resolved by product scope")
    return artifact


def load_golden_approval() -> dict[str, Any]:
    artifact = json.loads(DEFAULT_APPROVAL_PATH.read_text(encoding="utf-8"))
    expected = {
        "approval_id": APPROVAL_ID,
        "status": "APPROVED_AND_FROZEN_FOR_HACKATHON_SCOPE",
        "suite_id": SUITE_ID,
        "reviewed_semantic_cases_sha256": APPROVED_REVIEWED_SEMANTIC_SHA256,
        "rule_set_id": HOLISTIC_RULE_SET_ID,
        "completeness_policy_id": HOLISTIC_COMPLETENESS_POLICY_ID,
        "review_decision_set_id": DECISION_SET_ID,
        "oxygen_referral_disposition_id": OXYGEN_REFERRAL_DISPOSITION_ID,
        "scope_disposition_set_id": SCOPE_DISPOSITION_SET_ID,
        "oracle_id": HOLISTIC_ORACLE_ID,
        "frozen_record_schema_id": RECORD_SCHEMA_ID,
        "frozen_generator_version": GENERATOR_VERSION,
        "frozen_validator_id": VALIDATOR_ID,
        "production_clinical_use_authorized": False,
    }
    for key, value in expected.items():
        if artifact.get(key) != value:
            raise ValueError(f"incorrect holistic golden approval {key}")
    if artifact.get("eligibility_authorized") != {
        "HOLISTIC_GENERATION": True,
        "PRODUCT_EVALUATION": True,
        "TEACHER_BAKEOFF": True,
        "TRAINING": False,
    }:
        raise ValueError("incorrect post-freeze corpus eligibility approval")
    basis = artifact.get("approval_basis", {})
    if basis.get("explicit_human_domain_disposition") != "APPROVED":
        raise ValueError("holistic golden suite lacks explicit human/domain approval")
    transformation = artifact.get("freeze_transformation", {})
    if transformation.get("semantic_expectations_changed") is not False:
        raise ValueError("freeze approval must record an unchanged semantic target")
    frozen_hash = artifact.get("frozen_semantic_cases_sha256")
    if not isinstance(frozen_hash, str) or len(frozen_hash) != 64:
        raise ValueError("approval must pin the frozen semantic corpus hash")
    return artifact


def encounter_from_dict(value: dict[str, Any]) -> HolisticEncounter:
    facts = value["patient_facts"]
    danger = value["danger_signs"]
    respiratory = value.get("respiratory")
    diarrhoea = value.get("diarrhoea")
    fever = value.get("fever")
    ear = value.get("ear")
    if diarrhoea is not None:
        diarrhoea = dict(diarrhoea)
        dehydration = dict(diarrhoea.get("dehydration") or {})
        if dehydration.get("drinking_status") is not None:
            dehydration["drinking_status"] = DrinkingStatus(dehydration["drinking_status"])
        if dehydration.get("skin_pinch") is not None:
            dehydration["skin_pinch"] = SkinPinch(dehydration["skin_pinch"])
        diarrhoea["dehydration"] = DehydrationAssessment(**dehydration)
        if diarrhoea.get("rehydration_stage") is not None or diarrhoea.get("post_rehydration") is not None:
            raise ValueError("separate Plan B/C treatment-stage submissions do not yet have an approved evaluator")
        # Null placeholders are retained in the serialized input, but the initial
        # assessment constructor does not need to pass them explicitly.
        diarrhoea.pop("post_rehydration", None)
        diarrhoea.pop("rehydration_stage", None)
    if fever is not None:
        fever = dict(fever)
        if fever.get("malaria_risk") is not None:
            fever["malaria_risk"] = MalariaRisk(fever["malaria_risk"])
        if fever.get("malaria_test_result") is not None:
            fever["malaria_test_result"] = MalariaTestResult(fever["malaria_test_result"])
    return HolisticEncounter(
        encounter_id=value["encounter_id"],
        patient_facts=HolisticPatientFacts(**facts),
        danger_signs=GeneralDangerSignObservations(**danger),
        respiratory=HolisticRespiratoryObservations(**respiratory) if respiratory is not None else None,
        diarrhoea=HolisticDiarrhoeaObservations(**diarrhoea) if diarrhoea is not None else None,
        fever=HolisticFeverObservations(**fever) if fever is not None else None,
        ear=HolisticEarObservations(**ear) if ear is not None else None,
        schema_version=value.get("schema_version", HOLISTIC_SCHEMA_VERSION),
    )


def _danger(**changes: bool | None) -> GeneralDangerSignObservations:
    values: dict[str, bool | None] = {
        "unable_to_drink_or_breastfeed": False,
        "vomits_everything": False,
        "had_convulsions": False,
        "lethargic_or_unconscious": False,
        "convulsing_now": False,
    }
    values.update(changes)
    return GeneralDangerSignObservations(**values)


def _facts(**changes: Any) -> HolisticPatientFacts:
    values = {
        "age_months": 18,
        "has_cough_or_difficult_breathing": False,
        "has_diarrhoea": False,
        "has_fever": False,
        "has_ear_problem": False,
    }
    values.update(changes)
    return HolisticPatientFacts(**values)


def _resp(**changes: Any) -> HolisticRespiratoryObservations:
    values = {
        "cough_duration_days": 3,
        "respiratory_rate": 35,
        "chest_indrawing": False,
        "stridor_when_calm": False,
        "wheezing": False,
        "recurrent_wheeze": False,
        "child_calm": True,
        "breaths_counted_one_minute": True,
        "pulse_oximeter_available": False,
    }
    values.update(changes)
    return HolisticRespiratoryObservations(**values)


def _dehydration(**changes: Any) -> DehydrationAssessment:
    values = {
        "restless_or_irritable": False,
        "sunken_eyes": False,
        "drinking_status": DrinkingStatus.NORMAL,
        "skin_pinch": SkinPinch.NORMAL,
    }
    values.update(changes)
    return DehydrationAssessment(**values)


def _diarrhoea(**changes: Any) -> HolisticDiarrhoeaObservations:
    values = {"duration_days": 3, "blood_in_stool": False, "dehydration": _dehydration()}
    values.update(changes)
    return HolisticDiarrhoeaObservations(**values)


def _fever(**changes: Any) -> HolisticFeverObservations:
    values = {
        "temperature_c": 38.0,
        "malaria_risk": MalariaRisk.HIGH,
        "fever_duration_days": 2,
        "stiff_neck": False,
        "runny_nose": False,
        "obvious_cause_of_fever_present": False,
        "identified_bacterial_cause_present": False,
        "malaria_test_available": True,
        "malaria_test_result": MalariaTestResult.NEGATIVE,
        "measles_within_last_3_months": False,
        "generalized_rash": False,
        "measles_cough": False,
        "red_eyes": False,
    }
    values.update(changes)
    return HolisticFeverObservations(**values)


def _ear(**changes: Any) -> HolisticEarObservations:
    values = {
        "ear_pain": False,
        "ear_discharge_reported": False,
        "pus_draining_from_ear": False,
        "tender_swelling_behind_ear": False,
    }
    values.update(changes)
    return HolisticEarObservations(**values)


def _encounter(case_id: str, **changes: Any) -> HolisticEncounter:
    values = {"patient_facts": _facts(), "danger_signs": _danger()}
    values.update(changes)
    return HolisticEncounter(encounter_id=case_id, **values)


def _spec(
    case_id: str,
    why: str,
    coverage: tuple[str, ...],
    encounter: HolisticEncounter,
    *decisions: str,
) -> HolisticGoldenSpec:
    return HolisticGoldenSpec(case_id, why, coverage, encounter=encounter, review_decision_ids=decisions)


def holistic_golden_specs() -> tuple[HolisticGoldenSpec, ...]:
    """Return the fixed, review-sized semantic case design."""

    specs: list[HolisticGoldenSpec] = []
    add = specs.append
    add(_spec("hpg-001-all-negative", "Complete low-severity encounter with every pathway explicitly absent.", ("complete", "low_severity", "explicit_negative"), _encounter("hpg-001-all-negative"), "MSC-CQ-SCOPE-001"))

    for index, (field_name, decision) in enumerate(
        (
            ("unable_to_drink_or_breastfeed", "IP-CQ-002"),
            ("vomits_everything", "IP-CQ-001"),
            ("had_convulsions", "IP-CQ-001"),
            ("lethargic_or_unconscious", "IP-CQ-001"),
            ("convulsing_now", "IP-CQ-001"),
        ),
        start=2,
    ):
        case_id = f"hpg-{index:03d}-danger-{field_name.replace('_', '-')}"
        add(_spec(case_id, f"Complete encounter with {field_name} as the known general danger sign.", ("complete", "danger_sign", "urgent"), _encounter(case_id, danger_signs=_danger(**{field_name: True})), decision))

    respiratory_cases = (
        ("age-2-rate-49", 2, _resp(respiratory_rate=49), ("respiratory_boundary", "age_2", "rate_49")),
        ("age-2-rate-50", 2, _resp(respiratory_rate=50), ("respiratory_boundary", "age_2", "rate_50")),
        ("age-11-rate-50", 11, _resp(respiratory_rate=50), ("respiratory_boundary", "age_11")),
        ("age-12-rate-39", 12, _resp(respiratory_rate=39), ("respiratory_boundary", "age_12", "rate_39")),
        ("age-12-rate-40", 12, _resp(respiratory_rate=40), ("respiratory_boundary", "age_12", "rate_40")),
        ("age-59-rate-40", 59, _resp(respiratory_rate=40), ("respiratory_boundary", "age_59")),
        ("chest-hiv-negative", 18, _resp(chest_indrawing=True, hiv_exposed_or_infected=False), ("chest_indrawing", "hiv_modifier_negative")),
        ("chest-hiv-positive", 18, _resp(chest_indrawing=True, hiv_exposed_or_infected=True), ("chest_indrawing", "hiv_modifier_positive", "referral")),
        ("stridor", 18, _resp(stridor_when_calm=True), ("severe_respiratory", "urgent")),
        ("oximeter-89-9", 18, _resp(pulse_oximeter_available=True, oxygen_saturation_percent=89.9), ("oxygen_boundary", "urgent")),
        ("oximeter-90", 18, _resp(pulse_oximeter_available=True, oxygen_saturation_percent=90.0), ("oxygen_boundary",)),
        ("prolonged-cough", 18, _resp(cough_duration_days=15), ("prolonged_cough", "referral")),
        ("recurrent-wheeze", 18, _resp(wheezing=True, recurrent_wheeze=True), ("recurrent_wheeze", "home_bronchodilator")),
        ("post-bronchodilator-improved", 18, _resp(respiratory_rate=45, wheezing=True, bronchodilator_trial_completed=True, post_bronchodilator_respiratory_rate=35, post_bronchodilator_chest_indrawing=False, post_bronchodilator_child_calm=True, post_bronchodilator_breaths_counted_one_minute=True), ("bronchodilator_reassessment", "complete_post_reassessment", "improved")),
        ("post-bronchodilator-fast", 18, _resp(respiratory_rate=45, wheezing=True, bronchodilator_trial_completed=True, post_bronchodilator_respiratory_rate=42, post_bronchodilator_chest_indrawing=False, post_bronchodilator_child_calm=True, post_bronchodilator_breaths_counted_one_minute=True), ("bronchodilator_reassessment", "complete_post_reassessment", "persistent_fast_breathing")),
    )
    for offset, (slug, age, respiratory, tags) in enumerate(respiratory_cases, start=7):
        case_id = f"hpg-{offset:03d}-resp-{slug}"
        decisions = ("IP-CQ-003", "MSC-CQ-RESP-002") if "chest" in slug else ("IP-CQ-003", "MSC-CQ-RESP-001") if "bronchodilator" in slug else ("IP-CQ-003",)
        add(_spec(case_id, f"Complete respiratory semantic case: {slug}.", ("complete", "respiratory", *tags), _encounter(case_id, patient_facts=_facts(age_months=age, has_cough_or_difficult_breathing=True), respiratory=respiratory), *decisions))

    respiratory_incomplete = (
        ("trial-outstanding", _resp(respiratory_rate=45, wheezing=True), ("bronchodilator_reassessment",)),
        ("child-not-calm", _resp(child_calm=False), ("invalid_evidence", "contradiction")),
        ("count-not-one-minute", _resp(breaths_counted_one_minute=False), ("invalid_evidence", "contradiction")),
        ("oximeter-missing-value", _resp(pulse_oximeter_available=True), ("single_omission", "measurement_missing")),
        ("chest-hiv-unknown", _resp(chest_indrawing=True), ("single_omission", "hiv_modifier_unknown")),
    )
    for offset, (slug, respiratory, tags) in enumerate(respiratory_incomplete, start=22):
        case_id = f"hpg-{offset:03d}-resp-{slug}"
        add(_spec(case_id, f"Incomplete respiratory semantic case: {slug}.", ("incomplete", "respiratory", *tags), _encounter(case_id, patient_facts=_facts(has_cough_or_difficult_breathing=True), respiratory=respiratory), "IP-CQ-003", "MSC-CQ-RESP-001"))

    diarrhoea_cases = (
        ("no-dehydration", 18, _diarrhoea(), ("no_dehydration",)),
        ("some-dehydration", 18, _diarrhoea(dehydration=_dehydration(restless_or_irritable=True, sunken_eyes=True)), ("some_dehydration", "plan_b", "initial_treatment_stage")),
        ("severe-plan-c-under-24m", 18, _diarrhoea(dehydration=_dehydration(sunken_eyes=True, drinking_status=DrinkingStatus.POORLY)), ("severe_dehydration", "plan_c", "initial_treatment_stage")),
        ("severe-age-24-no-cholera", 24, _diarrhoea(dehydration=_dehydration(sunken_eyes=True, drinking_status=DrinkingStatus.POORLY), cholera_in_area=False), ("severe_dehydration", "cholera_context", "age_boundary")),
        ("severe-age-24-cholera", 24, _diarrhoea(dehydration=_dehydration(sunken_eyes=True, drinking_status=DrinkingStatus.POORLY), cholera_in_area=True), ("severe_dehydration", "cholera_action", "local_protocol_generic")),
        ("duration-13", 18, _diarrhoea(duration_days=13), ("duration_boundary", "not_persistent")),
        ("duration-14-persistent", 18, _diarrhoea(duration_days=14), ("duration_boundary", "persistent_diarrhoea")),
        ("severe-persistent", 18, _diarrhoea(duration_days=14, dehydration=_dehydration(restless_or_irritable=True, sunken_eyes=True)), ("severe_persistent_diarrhoea", "urgent")),
        ("dysentery", 18, _diarrhoea(blood_in_stool=True), ("dysentery",)),
        ("persistent-and-dysentery", 18, _diarrhoea(duration_days=14, blood_in_stool=True), ("simultaneous_classifications", "persistent_diarrhoea", "dysentery")),
    )
    for offset, (slug, age, diarrhoea, tags) in enumerate(diarrhoea_cases, start=27):
        case_id = f"hpg-{offset:03d}-diarrhoea-{slug}"
        add(_spec(case_id, f"Complete diarrhoea semantic case: {slug}.", ("complete", "diarrhoea", *tags), _encounter(case_id, patient_facts=_facts(age_months=age, has_diarrhoea=True), diarrhoea=diarrhoea), "MSC-CQ-DIARRHOEA-001", "MSC-CQ-REASSESS-001"))

    reuse_id = "hpg-037-diarrhoea-positive-drinking-reuse"
    add(_spec(reuse_id, "Clinically confirmed inability to drink is reused one-way in dehydration assessment.", ("complete", "diarrhoea", "cross_evidence_reuse", "urgent"), _encounter(reuse_id, patient_facts=_facts(has_diarrhoea=True), danger_signs=_danger(unable_to_drink_or_breastfeed=True), diarrhoea=_diarrhoea(dehydration=_dehydration(sunken_eyes=True, drinking_status=None))), "IP-CQ-001", "IP-CQ-002"))
    missing_drink_id = "hpg-038-diarrhoea-negative-does-not-reuse"
    add(_spec(missing_drink_id, "A negative danger-sign answer does not fill diarrhoea drinking status.", ("incomplete", "diarrhoea", "explicit_negative_omission_twin", "single_omission"), _encounter(missing_drink_id, patient_facts=_facts(has_diarrhoea=True), diarrhoea=_diarrhoea(dehydration=_dehydration(drinking_status=None))), "IP-CQ-002"))
    missing_duration_id = "hpg-039-diarrhoea-duration-unknown"
    add(_spec(missing_duration_id, "Known diarrhoea pathway with duration omitted remains incomplete.", ("incomplete", "diarrhoea", "single_omission"), _encounter(missing_duration_id, patient_facts=_facts(has_diarrhoea=True), diarrhoea=_diarrhoea(duration_days=None)), "MSC-CQ-REASSESS-001"))
    cholera_unknown_id = "hpg-040-diarrhoea-cholera-context-unknown"
    add(_spec(cholera_unknown_id, "Severe dehydration at 24 months requires cholera-area context.", ("incomplete", "diarrhoea", "conditional_omission", "cholera_context"), _encounter(cholera_unknown_id, patient_facts=_facts(age_months=24, has_diarrhoea=True), diarrhoea=_diarrhoea(dehydration=_dehydration(sunken_eyes=True, drinking_status=DrinkingStatus.POORLY))), "MSC-CQ-DIARRHOEA-001"))

    fever_cases = (
        ("high-positive", _fever(malaria_test_result=MalariaTestResult.POSITIVE), ("malaria", "high_risk", "test_positive")),
        ("high-negative", _fever(), ("fever_no_malaria", "high_risk", "test_negative")),
        ("high-test-unavailable", _fever(malaria_test_available=False, malaria_test_result=None), ("malaria", "test_unavailable")),
        ("low-obvious-cause", _fever(malaria_risk=MalariaRisk.LOW, obvious_cause_of_fever_present=True, malaria_test_available=None, malaria_test_result=None), ("fever_no_malaria", "low_risk", "obvious_cause")),
        ("low-no-cause-positive", _fever(malaria_risk=MalariaRisk.LOW, malaria_test_result=MalariaTestResult.POSITIVE), ("malaria", "low_risk", "test_positive")),
        (
            "no-risk",
            _fever(
                malaria_risk=MalariaRisk.NONE_NO_TRAVEL,
                malaria_test_available=None,
                malaria_test_result=None,
            ),
            ("no_malaria_risk",),
        ),
        ("temperature-38-4", _fever(temperature_c=38.4), ("temperature_boundary", "no_high_fever_action")),
        ("temperature-38-5", _fever(temperature_c=38.5), ("temperature_boundary", "high_fever_action")),
        ("duration-7", _fever(fever_duration_days=7), ("duration_boundary", "not_prolonged")),
        ("duration-8-not-every-day", _fever(fever_duration_days=8, fever_present_every_day=False), ("duration_boundary", "not_prolonged")),
        ("duration-8-every-day", _fever(fever_duration_days=8, fever_present_every_day=True), ("prolonged_fever", "referral")),
        ("identified-bacterial-cause", _fever(identified_bacterial_cause_present=True), ("generic_antibiotic_action", "identified_bacterial_cause")),
        ("measles", _fever(generalized_rash=True, measles_cough=True, mouth_ulcers=False, pus_draining_from_eye=False, clouding_of_cornea=False), ("measles",)),
        ("measles-eye", _fever(generalized_rash=True, red_eyes=True, mouth_ulcers=False, pus_draining_from_eye=True, clouding_of_cornea=False), ("measles_eye_or_mouth_complications",)),
        ("severe-measles-cornea", _fever(generalized_rash=True, red_eyes=True, mouth_ulcers=False, pus_draining_from_eye=False, clouding_of_cornea=True), ("severe_complicated_measles", "urgent")),
        ("severe-stiff-neck", _fever(stiff_neck=True), ("very_severe_febrile_disease", "urgent")),
        ("malaria-and-measles", _fever(temperature_c=38.5, malaria_test_result=MalariaTestResult.POSITIVE, generalized_rash=True, measles_cough=True, mouth_ulcers=False, pus_draining_from_eye=False, clouding_of_cornea=False), ("simultaneous_classifications", "malaria", "measles")),
        ("measles-last-three-months", _fever(measles_within_last_3_months=True, mouth_ulcers=False, pus_draining_from_eye=False, clouding_of_cornea=False), ("measles_history", "measles")),
    )
    for offset, (slug, fever, tags) in enumerate(fever_cases, start=41):
        case_id = f"hpg-{offset:03d}-fever-{slug}"
        add(_spec(case_id, f"Complete fever/measles semantic case: {slug}.", ("complete", "fever", *tags), _encounter(case_id, patient_facts=_facts(has_fever=True), fever=fever), "MSC-CQ-FEVER-001", "MSC-CQ-FEVER-002", "MSC-CQ-FEVER-003"))

    fever_missing_id = "hpg-059-fever-malaria-risk-unknown"
    add(_spec(fever_missing_id, "Applicable fever assessment with malaria-area risk context omitted.", ("incomplete", "fever", "case_context_missing", "single_omission"), _encounter(fever_missing_id, patient_facts=_facts(has_fever=True), fever=_fever(malaria_risk=None)), "MSC-CQ-FEVER-003"))
    fever_test_id = "hpg-060-fever-test-result-unknown"
    add(_spec(fever_test_id, "Available required malaria test without a result remains incomplete.", ("incomplete", "fever", "single_omission", "test_result_missing"), _encounter(fever_test_id, patient_facts=_facts(has_fever=True), fever=_fever(malaria_test_result=None)), "MSC-CQ-FEVER-001"))

    ear_cases = (
        ("no-infection", _ear(), ("no_ear_infection",)),
        ("acute-pain", _ear(ear_pain=True), ("acute_ear_infection", "ear_pain")),
        ("acute-discharge-13", _ear(ear_discharge_reported=True, ear_discharge_duration_days=13, pus_draining_from_ear=True), ("acute_ear_infection", "duration_boundary")),
        ("chronic-discharge-14", _ear(ear_discharge_reported=True, ear_discharge_duration_days=14, pus_draining_from_ear=True), ("chronic_ear_infection", "duration_boundary")),
        ("observed-pus-no-history", _ear(pus_draining_from_ear=True), ("acute_ear_infection", "observed_pus", "negative_history")),
        ("mastoiditis", _ear(tender_swelling_behind_ear=True), ("mastoiditis", "urgent")),
    )
    for offset, (slug, ear, tags) in enumerate(ear_cases, start=61):
        case_id = f"hpg-{offset:03d}-ear-{slug}"
        add(_spec(case_id, f"Complete ear semantic case: {slug}.", ("complete", "ear_problem", *tags), _encounter(case_id, patient_facts=_facts(has_ear_problem=True), ear=ear), "MSC-CQ-EAR-001"))
    ear_missing_id = "hpg-067-ear-duration-unknown"
    add(_spec(ear_missing_id, "Reported ear discharge requires its duration.", ("incomplete", "ear_problem", "single_omission"), _encounter(ear_missing_id, patient_facts=_facts(has_ear_problem=True), ear=_ear(ear_discharge_reported=True, pus_draining_from_ear=True)), "MSC-CQ-EAR-001"))

    cross_id = "hpg-068-cross-four-pathways"
    add(_spec(cross_id, "Complete whole encounter with simultaneous respiratory, diarrhoea, malaria/measles, and ear classifications.", ("complete", "whole_encounter", "simultaneous_classifications", "integrated_action_plan", "all_pathways"), _encounter(cross_id, patient_facts=_facts(has_cough_or_difficult_breathing=True, has_diarrhoea=True, has_fever=True, has_ear_problem=True), respiratory=_resp(respiratory_rate=42), diarrhoea=_diarrhoea(blood_in_stool=True), fever=_fever(malaria_test_result=MalariaTestResult.POSITIVE, generalized_rash=True, measles_cough=True, mouth_ulcers=False, pus_draining_from_eye=False, clouding_of_cornea=False), ear=_ear(ear_pain=True)), "IP-CQ-004", "MSC-CQ-FEVER-001"))
    urgent_cross_id = "hpg-069-cross-urgent-dehydration-ear"
    add(_spec(urgent_cross_id, "Mastoiditis changes simultaneous severe-dehydration management to referral transfer actions.", ("complete", "cross_pathway_action_dependency", "urgent", "deferred_routine_actions"), _encounter(urgent_cross_id, patient_facts=_facts(has_diarrhoea=True, has_ear_problem=True), diarrhoea=_diarrhoea(dehydration=_dehydration(sunken_eyes=True, drinking_status=DrinkingStatus.POORLY)), ear=_ear(tender_swelling_behind_ear=True)), "IP-CQ-004", "MSC-CQ-REASSESS-001"))
    multi_urgent_id = "hpg-070-cross-multiple-urgent"
    add(_spec(multi_urgent_id, "Multiple severe findings deduplicate shared urgent actions while retaining traces.", ("complete", "multiple_urgent", "action_deduplication", "integrated_action_plan"), _encounter(multi_urgent_id, patient_facts=_facts(has_cough_or_difficult_breathing=True, has_fever=True, has_ear_problem=True), danger_signs=_danger(convulsing_now=True), respiratory=_resp(stridor_when_calm=True), fever=_fever(stiff_neck=True), ear=_ear(tender_swelling_behind_ear=True)), "IP-CQ-001", "IP-CQ-004"))
    omitted_entry_id = "hpg-071-incomplete-entry-unknown"
    add(_spec(omitted_entry_id, "One omitted pathway-entry answer remains UNKNOWN and blocks holistic synthesis.", ("incomplete", "explicit_negative_omission_twin", "single_omission", "grouped_missing_elements"), _encounter(omitted_entry_id, patient_facts=replace(_facts(), has_diarrhoea=None)), "MSC-CQ-SCOPE-001"))
    multi_omit_id = "hpg-072-incomplete-multiple-groups"
    add(_spec(multi_omit_id, "Multiple omissions are grouped by supported assessment.", ("incomplete", "multiple_omissions", "grouped_missing_elements"), _encounter(multi_omit_id, patient_facts=replace(_facts(has_cough_or_difficult_breathing=True, has_fever=True), has_ear_problem=None), danger_signs=_danger(vomits_everything=None), respiratory=_resp(respiratory_rate=None), fever=_fever(malaria_risk=None)), "IP-CQ-001", "MSC-CQ-FEVER-003"))
    urgent_incomplete_id = "hpg-073-incomplete-known-urgent"
    add(_spec(urgent_incomplete_id, "Known convulsion triggers immediate urgent actions while missing assessment blocks final synthesis.", ("incomplete", "urgent_incomplete", "withhold_final_synthesis", "grouped_missing_elements"), _encounter(urgent_incomplete_id, patient_facts=HolisticPatientFacts(None, None, None, None, None), danger_signs=_danger(convulsing_now=True, vomits_everything=None)), "IP-CQ-001"))
    internal_withheld_id = "hpg-074-incomplete-internal-classification-withheld"
    add(_spec(internal_withheld_id, "A known pneumonia classification remains internal when another encounter entry is unknown.", ("incomplete", "internal_classification", "withhold_final_synthesis"), _encounter(internal_withheld_id, patient_facts=replace(_facts(has_cough_or_difficult_breathing=True), has_ear_problem=None), respiratory=_resp(respiratory_rate=45)), "MSC-CQ-SCOPE-001"))
    contradiction_id = "hpg-075-contradiction-drinking"
    add(_spec(contradiction_id, "Unable drinking status contradicts a clinically established negative general danger sign.", ("incomplete", "contradiction", "cross_evidence"), _encounter(contradiction_id, patient_facts=_facts(has_diarrhoea=True), diarrhoea=_diarrhoea(dehydration=_dehydration(drinking_status=DrinkingStatus.UNABLE))), "IP-CQ-002"))
    severe_complete_id = "hpg-076-complete-danger-plus-all-pathways"
    add(_spec(severe_complete_id, "Urgent finding leads while the complete holistic assessment retains all simultaneous classifications and defers routine actions.", ("complete", "urgent", "all_pathways", "deferred_routine_actions", "holistic_assessment_after_danger"), _encounter(severe_complete_id, patient_facts=_facts(has_cough_or_difficult_breathing=True, has_diarrhoea=True, has_fever=True, has_ear_problem=True), danger_signs=_danger(vomits_everything=True), respiratory=_resp(), diarrhoea=_diarrhoea(), fever=_fever(), ear=_ear()), "IP-CQ-001", "IP-CQ-004"))

    base_payload = encounter_to_dict(_encounter("hpg-077-out-of-scope-age-1"))
    base_payload["patient_facts"]["age_months"] = 1
    add(HolisticGoldenSpec("hpg-077-out-of-scope-age-1", "Young infant is outside the supported major sick-child schema.", ("out_of_scope", "schema_rejection", "age_boundary"), invalid_payload=base_payload, expected_schema_error="age_months must be at least 2 and less than 60", review_decision_ids=("MSC-CQ-SCOPE-001",)))
    high_payload = encounter_to_dict(_encounter("hpg-078-out-of-scope-age-60"))
    high_payload["patient_facts"]["age_months"] = 60
    add(HolisticGoldenSpec("hpg-078-out-of-scope-age-60", "Child aged 60 months is outside the supported major sick-child schema.", ("out_of_scope", "schema_rejection", "age_boundary"), invalid_payload=high_payload, expected_schema_error="age_months must be at least 2 and less than 60", review_decision_ids=("MSC-CQ-SCOPE-001",)))
    return tuple(specs)


def _source_provenance(rule_ids: list[str]) -> dict[str, Any]:
    rule_set = load_holistic_artifacts().rule_set
    by_id = {rule.rule_id: rule for rule in rule_set.rules}
    citations = [
        {"rule_id": rule_id, **by_id[rule_id].source}
        for rule_id in rule_ids
        if rule_id in by_id
    ]
    return {
        "document": rule_set.document,
        "edition": rule_set.edition,
        "source_rule_ids": [item["rule_id"] for item in citations],
        "source_citations": citations,
    }


def _bronchodilator_trial_indicated(
    age_months: int | None,
    respiratory: HolisticRespiratoryObservations,
) -> bool:
    """Return whether the initial respiratory findings trigger the approved trial sequence."""
    if respiratory.wheezing is not True:
        return False
    if respiratory.chest_indrawing is True:
        return True
    if age_months is None or respiratory.respiratory_rate is None:
        return False
    threshold = 50 if age_months < 12 else 40
    return respiratory.respiratory_rate >= threshold


def _derived_review_decision_ids(
    encounter: HolisticEncounter | None,
    coverage: tuple[str, ...] | list[str],
    expected: dict[str, Any],
) -> list[str]:
    """Derive exact approved-decision applicability from semantic factors."""
    applicable: set[str] = set()
    tags = set(coverage)
    if encounter is None:
        applicable.add("MSC-CQ-SCOPE-001")
    else:
        facts = encounter.patient_facts
        danger_values = tuple(asdict(encounter.danger_signs).values())
        known_danger = any(value is True for value in danger_values)
        entries = (
            facts.has_cough_or_difficult_breathing,
            facts.has_diarrhoea,
            facts.has_fever,
            facts.has_ear_problem,
        )
        evaluation = expected["evaluation"]

        if known_danger:
            applicable.add("IP-CQ-001")
        if (
            facts.has_diarrhoea is True
            and encounter.diarrhoea is not None
            and (
                encounter.danger_signs.unable_to_drink_or_breastfeed is True
                or (
                    encounter.danger_signs.unable_to_drink_or_breastfeed is False
                    and encounter.diarrhoea.dehydration.drinking_status
                    in {None, DrinkingStatus.UNABLE}
                )
            )
        ):
            applicable.add("IP-CQ-002")
        if facts.has_cough_or_difficult_breathing is True and encounter.respiratory is not None:
            applicable.add("IP-CQ-003")
        classifications = {
            item["classification"] for item in evaluation["internal_classifications"]
        }
        if evaluation["urgent_action_required"] and (
            evaluation["deferred_actions"]
            or "SEVERE_COMPLICATED_MEASLES" in classifications
            or tags
            & {
                "cross_pathway_action_dependency",
                "multiple_urgent",
                "deferred_routine_actions",
            }
        ):
            applicable.add("IP-CQ-004")
        if (
            all(value is False for value in entries)
            and not known_danger
            or any(value is None for value in entries)
        ):
            applicable.add("MSC-CQ-SCOPE-001")

        respiratory = encounter.respiratory
        if facts.has_cough_or_difficult_breathing is True and respiratory is not None:
            if _bronchodilator_trial_indicated(facts.age_months, respiratory):
                applicable.add("MSC-CQ-RESP-001")
            if respiratory.chest_indrawing is True and respiratory.hiv_exposed_or_infected is True:
                applicable.add("MSC-CQ-RESP-002")

        if facts.has_diarrhoea is True and encounter.diarrhoea is not None:
            if (
                facts.age_months is not None
                and facts.age_months >= 24
                and "SEVERE_DEHYDRATION" in classifications
            ):
                applicable.add("MSC-CQ-DIARRHOEA-001")
            if {
                "REASSESS_DEHYDRATION_AFTER_PLAN_B",
                "REASSESS_DEHYDRATION_AFTER_PLAN_C",
            } & set(evaluation["intermediate_actions"]):
                applicable.add("MSC-CQ-REASSESS-001")

        if facts.has_fever is True and encounter.fever is not None:
            applicable.update({"MSC-CQ-FEVER-001", "MSC-CQ-FEVER-003"})
            if encounter.fever.identified_bacterial_cause_present is True:
                applicable.add("MSC-CQ-FEVER-002")

        if (
            facts.has_ear_problem is True
            and encounter.ear is not None
            and encounter.ear.pus_draining_from_ear is True
            and encounter.ear.ear_discharge_reported is False
            and encounter.ear.tender_swelling_behind_ear is False
        ):
            applicable.add("MSC-CQ-EAR-001")

    decision_order = [
        item["question_id"] for item in load_holistic_artifacts().decisions["decisions"]
    ]
    return [question_id for question_id in decision_order if question_id in applicable]


def _requirement_provenance(
    encounter: HolisticEncounter | None,
    coverage: tuple[str, ...] | list[str],
    expected: dict[str, Any],
) -> list[dict[str, Any]]:
    """Cite non-firing completeness requirements and scope without claiming a rule fired."""
    policy = load_holistic_artifacts().policy
    artifact_path = "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json"
    common = {
        "artifact_id": HOLISTIC_COMPLETENESS_POLICY_ID,
        "artifact_path": artifact_path,
    }
    if encounter is None:
        return [
            {
                "provenance_id": "HC-SCOPE-AGE-2-59",
                "provenance_type": "SCOPE_BOUNDARY",
                **common,
                "artifact_section": "population.age_months",
                "fields": ["patient_facts.age_months"],
            }
        ]

    evaluation = expected["evaluation"]
    missing_fields = {
        field
        for fields in evaluation["missing_elements"].values()
        for field in fields
    }
    entries: list[dict[str, Any]] = []
    always = set(policy["always_required"])
    missing_always = sorted(missing_fields & always)
    if missing_always:
        entries.append(
            {
                "provenance_id": "HC-REQ-ALWAYS",
                "provenance_type": "COMPLETENESS_REQUIREMENT",
                **common,
                "artifact_section": "always_required",
                "fields": missing_always,
            }
        )
    for index, requirement in enumerate(policy["conditional_requirements"], start=1):
        fields = sorted(missing_fields & set(requirement["require"]))
        if fields:
            entries.append(
                {
                    "provenance_id": f"HC-REQ-CONDITIONAL-{index:02d}",
                    "provenance_type": "COMPLETENESS_REQUIREMENT",
                    **common,
                    "artifact_section": f"conditional_requirements[{index - 1}]",
                    "fields": fields,
                    "trigger": requirement["when"],
                }
            )
    if evaluation["contradictions"]:
        invalid_respiratory = all(
            message.startswith("respiratory") for message in evaluation["contradictions"]
        )
        entries.append(
            {
                "provenance_id": (
                    "HC-INVALID-EVIDENCE" if invalid_respiratory else "HC-CONTRADICTION-BLOCKS-COMPLETION"
                ),
                "provenance_type": "EVIDENCE_VALIDITY_REQUIREMENT",
                **common,
                "artifact_section": (
                    "invalid_evidence_blocks_completion"
                    if invalid_respiratory
                    else "contradictions_block_completion"
                ),
                "fields": [],
                "details": list(evaluation["contradictions"]),
            }
        )
    if "low_severity" in coverage and not missing_fields:
        entries.append(
            {
                "provenance_id": "HC-EXPLICIT-NEGATIVE-PATHWAY-EXCLUSION",
                "provenance_type": "COMPLETENESS_REQUIREMENT",
                **common,
                "artifact_section": "always_required + unknown_semantics",
                "fields": list(policy["always_required"]),
                "details": [
                    "All always-required observations are supplied explicitly; negative pathway-entry findings make those pathways not applicable."
                ],
            }
        )
    return entries


def build_holistic_golden_suite() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for spec in holistic_golden_specs():
        if spec.encounter is not None:
            input_payload = encounter_to_dict(spec.encounter)
            evaluation = evaluate_holistic_encounter(spec.encounter).to_dict()
            expected = {"kind": "HOLISTIC_EVALUATION", "evaluation": evaluation}
            rule_ids = evaluation["fired_rule_ids"]
            signature_source = evaluation
        else:
            input_payload = spec.invalid_payload
            expected = {"kind": "SCHEMA_REJECTION", "error": spec.expected_schema_error}
            rule_ids = []
            signature_source = expected
        records.append(
            {
                "record_schema_id": RECORD_SCHEMA_ID,
                "suite_id": SUITE_ID,
                "golden_case_id": spec.case_id,
                "status": "FROZEN",
                "corpus_role": CorpusRole.HOLISTIC_PRODUCT_GOLDEN.value,
                "why": spec.why,
                "coverage": list(spec.coverage),
                "input": {"kind": "HOLISTIC_ENCOUNTER", "encounter": input_payload},
                "expected": expected,
                "provenance": {
                    **_source_provenance(rule_ids),
                    "review_decision_ids": _derived_review_decision_ids(
                        spec.encounter,
                        spec.coverage,
                        expected,
                    ),
                    "requirement_citations": _requirement_provenance(
                        spec.encounter,
                        spec.coverage,
                        expected,
                    ),
                    "product_policy_disposition_ids": (
                        [OXYGEN_REFERRAL_DISPOSITION_ID]
                        if spec.encounter is not None
                        and spec.encounter.respiratory is not None
                        and spec.encounter.respiratory.pulse_oximeter_available is True
                        and spec.encounter.respiratory.oxygen_saturation_percent is not None
                        and spec.encounter.respiratory.oxygen_saturation_percent < 90
                        else []
                    ),
                },
                "metadata": {
                    "holistic_schema_version": HOLISTIC_SCHEMA_VERSION,
                    "rule_set_id": HOLISTIC_RULE_SET_ID,
                    "completeness_policy_id": HOLISTIC_COMPLETENESS_POLICY_ID,
                    "review_decision_set_id": DECISION_SET_ID,
                    "oxygen_referral_disposition_id": OXYGEN_REFERRAL_DISPOSITION_ID,
                    "scope_disposition_set_id": SCOPE_DISPOSITION_SET_ID,
                    "oracle_id": HOLISTIC_ORACLE_ID,
                    "validator_id": VALIDATOR_ID,
                    "generator_version": GENERATOR_VERSION,
                    "approval_id": APPROVAL_ID,
                    "generation_seed": GENERATION_SEED,
                    "logic_signature": hashlib.sha256(
                        json.dumps(signature_source, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest(),
                },
                "review_flags": ["HUMAN_DOMAIN_APPROVED", "SEMANTICS_FROZEN"],
            }
        )
    return records


def validate_holistic_golden_record(record: dict[str, Any]) -> None:
    if record["corpus_role"] != CorpusRole.HOLISTIC_PRODUCT_GOLDEN.value:
        raise ValueError("product golden record has the wrong corpus role")
    metadata = record["metadata"]
    expected_pins = {
        "holistic_schema_version": HOLISTIC_SCHEMA_VERSION,
        "rule_set_id": HOLISTIC_RULE_SET_ID,
        "completeness_policy_id": HOLISTIC_COMPLETENESS_POLICY_ID,
        "review_decision_set_id": DECISION_SET_ID,
        "oxygen_referral_disposition_id": OXYGEN_REFERRAL_DISPOSITION_ID,
        "scope_disposition_set_id": SCOPE_DISPOSITION_SET_ID,
        "oracle_id": HOLISTIC_ORACLE_ID,
        "validator_id": VALIDATOR_ID,
        "approval_id": APPROVAL_ID,
    }
    for key, expected in expected_pins.items():
        if metadata.get(key) != expected:
            raise ValueError(f"incorrect {key} pin")
    if record.get("status") != "FROZEN":
        raise ValueError("golden record must retain frozen lifecycle status")
    if record.get("review_flags") != ["HUMAN_DOMAIN_APPROVED", "SEMANTICS_FROZEN"]:
        raise ValueError("golden record must retain approval and freeze flags")
    payload = record["input"]["encounter"]
    expected = record["expected"]
    signature_source = expected if expected["kind"] == "SCHEMA_REJECTION" else expected["evaluation"]
    expected_signature = hashlib.sha256(
        json.dumps(signature_source, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if metadata.get("logic_signature") != expected_signature:
        raise ValueError("golden logic signature does not match expected semantics")
    approved_decisions = {
        item["question_id"] for item in load_holistic_artifacts().decisions["decisions"]
    }
    review_decisions = record["provenance"]["review_decision_ids"]
    if not set(review_decisions) <= approved_decisions:
        raise ValueError("golden record has unknown review-decision provenance")
    coverage = record["coverage"]
    if len(coverage) != len(set(coverage)):
        raise ValueError("golden record has duplicate coverage tags")
    respiratory_payload = payload.get("respiratory") or {}
    expected_oxygen_dispositions = (
        [OXYGEN_REFERRAL_DISPOSITION_ID]
        if respiratory_payload.get("pulse_oximeter_available") is True
        and respiratory_payload.get("oxygen_saturation_percent") is not None
        and respiratory_payload["oxygen_saturation_percent"] < 90
        else []
    )
    if record["provenance"].get("product_policy_disposition_ids") != expected_oxygen_dispositions:
        raise ValueError("oxygen-referral product-policy provenance is not exact")
    if expected["kind"] == "SCHEMA_REJECTION":
        try:
            encounter_from_dict(payload)
        except ValueError as error:
            if str(error) != expected["error"]:
                raise ValueError("schema rejection changed") from error
        else:
            raise ValueError("expected schema rejection did not occur")
        if review_decisions != _derived_review_decision_ids(None, coverage, expected):
            raise ValueError("schema-rejection review-decision provenance is not exact")
        if record["provenance"]["requirement_citations"] != _requirement_provenance(
            None,
            coverage,
            expected,
        ):
            raise ValueError("schema-rejection requirement provenance is not exact")
        return
    encounter = encounter_from_dict(payload)
    actual = evaluate_holistic_encounter(encounter).to_dict()
    if actual != expected["evaluation"]:
        raise ValueError("holistic evaluation no longer matches the golden record")
    if review_decisions != _derived_review_decision_ids(encounter, coverage, expected):
        raise ValueError("review-decision provenance is not exact")
    if record["provenance"]["requirement_citations"] != _requirement_provenance(
        encounter,
        coverage,
        expected,
    ):
        raise ValueError("requirement provenance is not exact")
    expected_rules = expected["evaluation"]["fired_rule_ids"]
    if record["provenance"]["source_rule_ids"] != [
        item["rule_id"] for item in record["provenance"]["source_citations"]
    ]:
        raise ValueError("source provenance is internally inconsistent")
    canonical_ids = load_holistic_artifacts().rule_set.ids()
    if not set(expected_rules) <= canonical_ids:
        raise ValueError("evaluator fired a rule absent from the pinned clinical artifact")
    if record["provenance"]["source_rule_ids"] != expected_rules:
        raise ValueError("source provenance does not match fired clinical rules")


def write_holistic_golden_suite() -> list[dict[str, Any]]:
    scope_dispositions = load_scope_dispositions()
    approval = load_golden_approval()
    records = build_holistic_golden_suite()
    for record in records:
        validate_holistic_golden_record(record)
    DEFAULT_SUITE_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_content = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
    frozen_hash = hashlib.sha256(jsonl_content.encode()).hexdigest()
    if frozen_hash != approval["frozen_semantic_cases_sha256"]:
        raise ValueError("generated frozen semantic corpus does not match the approved hash")
    DEFAULT_JSONL_PATH.write_text(jsonl_content, encoding="utf-8")
    DEFAULT_YAML_PATH.write_text(
        yaml.safe_dump(records, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    DEFAULT_SCOPE_DISPOSITIONS_YAML_PATH.write_text(
        "# Generated from the canonical JSON; do not edit this mirror.\n"
        + yaml.safe_dump(scope_dispositions, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    DEFAULT_APPROVAL_YAML_PATH.write_text(
        "# Generated from the canonical JSON; do not edit this mirror.\n"
        + yaml.safe_dump(approval, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    DEFAULT_MANIFEST_PATH.write_text(
        json.dumps(
            _manifest(records, semantic_cases_sha256=frozen_hash),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    DEFAULT_REVIEW_PATH.write_text(render_holistic_golden_review(records), encoding="utf-8")
    return records


def load_holistic_golden_suite(
    path: str | Path = DEFAULT_JSONL_PATH,
    *,
    corpus_use: CorpusUse = CorpusUse.DOMAIN_REVIEW,
) -> list[dict[str, Any]]:
    assert_corpus_use_allowed(path, corpus_use, manifest_path=DEFAULT_MANIFEST_PATH)
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def _manifest(
    records: list[dict[str, Any]],
    *,
    semantic_cases_sha256: str | None = None,
) -> dict[str, Any]:
    coverage = sorted({tag for record in records for tag in record["coverage"]})
    complete = sum(
        record["expected"].get("evaluation", {}).get("supported_encounter_complete", False)
        for record in records
    )
    return {
        "suite_id": SUITE_ID,
        "lifecycle_status": "FROZEN",
        "corpus_role": CorpusRole.HOLISTIC_PRODUCT_GOLDEN.value,
        "case_count": len(records),
        "complete_case_count": complete,
        "incomplete_or_rejected_case_count": len(records) - complete,
        "artifact_pins": {
            key: records[0]["metadata"][key]
            for key in (
                "holistic_schema_version",
                "rule_set_id",
                "completeness_policy_id",
                "review_decision_set_id",
                "oxygen_referral_disposition_id",
                "scope_disposition_set_id",
                "oracle_id",
                "validator_id",
                "generator_version",
                "approval_id",
                "generation_seed",
            )
        },
        "semantic_cases_sha256": semantic_cases_sha256,
        "assets": [
            "data/golden/holistic_product_v1/semantic_cases.jsonl",
            "data/golden/holistic_product_v1/semantic_cases.yaml",
        ],
        "coverage_tags": coverage,
        "eligibility": {
            "DOMAIN_REVIEW": True,
            "COMPONENT_VALIDATION": True,
            "HOLISTIC_GENERATION": True,
            "PRODUCT_EVALUATION": True,
            "TEACHER_BAKEOFF": True,
            "TRAINING": False,
        },
        "known_coverage_gaps": [],
        "scope_dispositions": load_scope_dispositions()["dispositions"],
        "freeze_blockers": [],
        "review_required_before_freeze": False,
        "approval": {
            "approval_id": APPROVAL_ID,
            "reviewed_semantic_cases_sha256": APPROVED_REVIEWED_SEMANTIC_SHA256,
            "frozen_semantic_cases_sha256": semantic_cases_sha256,
            "approved_for_hackathon_scope": True,
        },
        "production_clinical_use_authorized": False,
        "unknown_semantics": {
            "omitted_is_unknown": True,
            "unknown_is_negative": False,
        },
    }


def render_holistic_golden_review(records: list[dict[str, Any]]) -> str:
    manifest = _manifest(records)
    lines = [
        "# Product-level holistic golden semantic suite v1 — review package",
        "",
        "> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Generated review surface for the approved and frozen hackathon semantic suite.",
        "",
        "**Status:** `FROZEN` — human/domain approved for the bounded hackathon scope; eligible for golden-language work, teacher bake-off, and product evaluation, but not training data.",
        "",
        f"**Cases:** {len(records)}. **Corpus role:** `{CorpusRole.HOLISTIC_PRODUCT_GOLDEN.value}`.",
        "",
        f"**Pinned substrate:** `{HOLISTIC_RULE_SET_ID}` / `{HOLISTIC_COMPLETENESS_POLICY_ID}` / `{DECISION_SET_ID}` / `{OXYGEN_REFERRAL_DISPOSITION_ID}` / `{SCOPE_DISPOSITION_SET_ID}` / `{HOLISTIC_ORACLE_ID}`.",
        "",
        f"Every evaluable record is deterministically recomputed. Approval is pinned by `{APPROVAL_ID}`; production clinical use remains unauthorized.",
        "",
        "## Resolved product-scope disposition",
        "",
        f"- `{manifest['scope_dispositions'][0]['gap_id']}` — `{manifest['scope_dispositions'][0]['status']}`: {manifest['scope_dispositions'][0]['decision']}",
        "",
        "## Case index",
        "",
        "| Case | Expected state | Urgent | Final classifications | Coverage | Review decisions |",
        "|---|---|---:|---|---|---|",
    ]
    for record in records:
        expected = record["expected"]
        if expected["kind"] == "SCHEMA_REJECTION":
            state = "SCHEMA_REJECTION"
            urgent = "—"
            classifications = "—"
        else:
            evaluation = expected["evaluation"]
            state = "COMPLETE" if evaluation["supported_encounter_complete"] else "INCOMPLETE"
            urgent = "yes" if evaluation["urgent_action_required"] else "no"
            classification_labels = ", ".join(
                item["classification"] for item in evaluation["final_classifications"]
            )
            classifications = classification_labels or ("none" if state == "COMPLETE" else "withheld")
        lines.append(
            f"| `{record['golden_case_id']}` | {state} | {urgent} | {classifications} | "
            f"{', '.join(record['coverage'])} | {', '.join(record['provenance']['review_decision_ids']) or '—'} |"
        )
    lines.extend(["", "## Detailed case review", ""])
    for record in records:
        expected = record["expected"]
        lines.extend(
            [
                f"### {record['golden_case_id']}",
                "",
                f"**Why:** {record['why']}",
                "",
                f"**Coverage:** {', '.join(f'`{item}`' for item in record['coverage'])}",
                "",
                f"**Applicable approved decisions:** {', '.join(f'`{item}`' for item in record['provenance']['review_decision_ids']) or 'none'}",
                "",
                f"**Applicable product-policy dispositions:** {', '.join(f'`{item}`' for item in record['provenance']['product_policy_disposition_ids']) or 'none'}",
                "",
                "**Non-firing requirement / scope provenance:**",
                "",
                "```json",
                json.dumps(record["provenance"]["requirement_citations"], indent=2, sort_keys=True),
                "```",
                "",
                "**Structured input:**",
                "",
                "```json",
                json.dumps(record["input"]["encounter"], indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
        if expected["kind"] == "SCHEMA_REJECTION":
            lines.extend(
                [
                    "**Expected result:** `SCHEMA_REJECTION`",
                    "",
                    f"**Expected error:** {expected['error']}",
                    "",
                ]
            )
        else:
            evaluation = expected["evaluation"]
            internal = [item["classification"] for item in evaluation["internal_classifications"]]
            final = [item["classification"] for item in evaluation["final_classifications"]]
            lines.extend(
                [
                    f"**Complete / final synthesis authorized:** `{evaluation['supported_encounter_complete']}` / `{evaluation['final_holistic_synthesis_authorized']}`",
                    "",
                    f"**Urgent action required:** `{evaluation['urgent_action_required']}`",
                    "",
                    f"**Internal classifications:** {', '.join(f'`{item}`' for item in internal) or 'none'}",
                    "",
                    f"**Final classifications:** {', '.join(f'`{item}`' for item in final) or ('none' if evaluation['supported_encounter_complete'] else 'withheld')}",
                    "",
                    f"**Urgent actions:** {', '.join(f'`{item}`' for item in evaluation['urgent_actions']) or 'none'}",
                    "",
                    f"**Intermediate actions:** {', '.join(f'`{item}`' for item in evaluation['intermediate_actions']) or 'none'}",
                    "",
                    f"**Deferred actions:** {', '.join(f'`{item}`' for item in evaluation['deferred_actions']) or 'none'}",
                    "",
                    f"**Final actions:** {', '.join(f'`{item}`' for item in evaluation['final_actions']) or ('none' if evaluation['supported_encounter_complete'] else 'withheld')}",
                    "",
                    "**Grouped missing elements:**",
                    "",
                    "```json",
                    json.dumps(evaluation["missing_elements"], indent=2, sort_keys=True),
                    "```",
                    "",
                    f"**Contradictions:** {', '.join(evaluation['contradictions']) or 'none'}",
                    "",
                    f"**Fired rules:** {', '.join(f'`{item}`' for item in evaluation['fired_rule_ids']) or 'none'}",
                    "",
                ]
            )
        citations = record["provenance"]["source_citations"]
        lines.extend(["**Source provenance:**", ""])
        if citations:
            lines.extend(
                f"- `{item['rule_id']}` — {item['section']}; PDF page {item['source_pdf_page']}; printed page {item['source_printed_page']}"
                for item in citations
            )
        else:
            lines.append("- No clinical rule fired; review against the pinned scope/completeness policy.")
        lines.extend(
            [
                "",
                "**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance",
                "",
            ]
        )
    lines.extend(
        [
            "",
            "## Review instructions",
            "",
            "Treat these semantic targets as immutable. If a genuine semantic defect is discovered, open change control and create a new reviewed version rather than silently editing the frozen suite.",
            "",
            "Golden-language rendering and controlled teacher/prompt evaluation are now authorized. Bulk synthetic generation and training remain separate gated stages.",
        ]
    )
    return "\n".join(lines) + "\n"
