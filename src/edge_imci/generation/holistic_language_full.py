"""Deterministic, grammar-normalized drafts for the 78-case golden language layer.

Frozen calibration history is preserved separately. Its user submissions and
semantic alignments are reused, while all assistant responses return to review
after deterministic formatting under the approved response grammar.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from edge_imci.corpus_policy import CorpusUse, assert_corpus_use_allowed
from edge_imci.generation.holistic_golden import (
    DEFAULT_JSONL_PATH as SEMANTIC_JSONL_PATH,
    SUITE_ID as SEMANTIC_SUITE_ID,
    load_holistic_golden_suite,
)
from edge_imci.generation.holistic_language import (
    DEFAULT_SCHEMA_PATH,
    LANGUAGE_APPROVAL_ID,
    LANGUAGE_RECORD_SCHEMA_ID,
    SEMANTIC_CASES_SHA256,
    load_language_calibration,
)

ROOT = Path(__file__).resolve().parents[3]
FULL_LANGUAGE_SUITE_ID = "edge-imci-holistic-product-golden-language-v1"
FULL_LANGUAGE_BUILDER_ID = "edge-imci-holistic-product-golden-language-builder-v1"
FULL_LANGUAGE_APPROVAL_ID = "edge-imci-holistic-product-golden-language-approval-v1"
RESPONSE_GRAMMAR_ID = "edge-imci-response-grammar-v1"
PRE_FORMAT_LANGUAGE_SHA256 = "9840b57e5e7b21193d7d5596de7cf1b574285fae280c5f8365cafd3d637f7dbe"
PRE_REMEDIATION_LANGUAGE_SHA256 = "713d223436c7b1b2daf10006d7e239ae1d7681dc6cccb771cea7d906a2bf2d94"
APPROVED_REMEDIATED_LANGUAGE_SHA256 = "78d4a503eecf603ad69dd1d26edb1fa7cd258c310ece95bdfb892688158dd665"
APPROVED_RESPONSE_GRAMMAR_SHA256 = "1fd793607f077cd4d44a9cf73349803d32ef1e69e3aab82d00fe0bda330f4873"
DEFAULT_LANGUAGE_PATH = ROOT / "data" / "golden" / "holistic_product_v1" / "language_renderings_v1.jsonl"
DEFAULT_LANGUAGE_YAML_PATH = DEFAULT_LANGUAGE_PATH.with_suffix(".yaml")
DEFAULT_MANIFEST_PATH = ROOT / "data" / "golden" / "holistic_product_v1" / "language_manifest_v1.json"
DEFAULT_REVIEW_PATH = ROOT / "docs" / "product_holistic_golden_language_review_v1.md"
DEFAULT_GRAMMAR_PATH = ROOT / "configs" / "rendering" / "edgeimci_response_grammar_v1.json"
DEFAULT_GRAMMAR_YAML_PATH = DEFAULT_GRAMMAR_PATH.with_suffix(".yaml")
DEFAULT_FULL_APPROVAL_PATH = ROOT / "configs" / "rendering" / "holistic_golden_full_language_approval_v1.json"
DEFAULT_FULL_APPROVAL_YAML_PATH = DEFAULT_FULL_APPROVAL_PATH.with_suffix(".yaml")
DEFAULT_PRE_FORMAT_REVIEW_PATH = ROOT / "docs" / "product_holistic_golden_language_review_v1_report.md"

CLASSIFICATION_LABELS = {
    "VERY_SEVERE_DISEASE": "Very severe disease",
    "SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE": "Severe pneumonia or very severe disease",
    "PNEUMONIA": "Pneumonia",
    "COUGH_OR_COLD": "Cough or cold",
    "SEVERE_DEHYDRATION": "Severe dehydration",
    "SOME_DEHYDRATION": "Some dehydration",
    "NO_DEHYDRATION": "No dehydration",
    "SEVERE_PERSISTENT_DIARRHOEA": "Severe persistent diarrhoea",
    "PERSISTENT_DIARRHOEA": "Persistent diarrhoea",
    "DYSENTERY": "Dysentery",
    "VERY_SEVERE_FEBRILE_DISEASE": "Very severe febrile disease",
    "MALARIA": "Malaria",
    "FEVER_NO_MALARIA": "Fever—no malaria",
    "FEVER": "Fever",
    "SEVERE_COMPLICATED_MEASLES": "Severe complicated measles",
    "MEASLES_WITH_EYE_OR_MOUTH_COMPLICATIONS": "Measles with eye or mouth complications",
    "MEASLES": "Measles",
    "MASTOIDITIS": "Mastoiditis",
    "ACUTE_EAR_INFECTION": "Acute ear infection",
    "CHRONIC_EAR_INFECTION": "Chronic ear infection",
    "NO_EAR_INFECTION": "No ear infection",
}

ACTION_SENTENCES = {
    "COMPLETE_ASSESSMENT_QUICKLY": "Complete the remaining assessment quickly.",
    "GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY": "Give the indicated pre-referral treatment immediately.",
    "PREVENT_LOW_BLOOD_SUGAR": "Prevent low blood sugar.",
    "KEEP_WARM": "Keep the child warm.",
    "URGENT_REFERRAL": "Arrange urgent referral.",
    "REFER_TO_HOSPITAL": "Refer the child to hospital.",
    "GIVE_DIAZEPAM_IF_CONVULSING_NOW": "Give diazepam if the child is convulsing now.",
    "GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC": "Give the first dose of an appropriate antibiotic.",
    "GIVE_ORAL_AMOXICILLIN_5_DAYS": "Give oral amoxicillin for 5 days.",
    "GIVE_FIRST_DOSE_AMOXICILLIN_AND_REFER": (
        "Give the first dose of amoxicillin, then refer the child. This finding alone calls for "
        "referral, not urgent referral."
    ),
    "GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL": "Give the rapid-acting inhaled bronchodilator trial.",
    "REASSESS_BREATHING_AFTER_BRONCHODILATOR": "Reassess breathing after the bronchodilator trial.",
    "GIVE_INHALED_BRONCHODILATOR_5_DAYS": "Give an inhaled bronchodilator for 5 days.",
    "REFER_FOR_TB_OR_ASTHMA_ASSESSMENT": "Refer for tuberculosis or asthma assessment.",
    "REFER_FOR_OXYGEN_SATURATION_BELOW_90": "Refer because the oxygen saturation is below 90%; this finding alone calls for referral, not urgent referral.",
    "SOOTHE_THROAT_AND_RELIEVE_COUGH": "Soothe the throat and relieve the cough with a safe remedy.",
    "ADVISE_WHEN_TO_RETURN_IMMEDIATELY": "Advise the caregiver when to return immediately.",
    "FOLLOW_UP_2_DAYS_IF_FEVER_PERSISTS": "Follow up in 2 days if the fever persists.",
    "FOLLOW_UP_3_DAYS": "Follow up in 3 days.",
    "FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS": "Follow up in 3 days if the fever persists.",
    "FOLLOW_UP_5_DAYS": "Follow up in 5 days.",
    "FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING": "Follow up in 5 days if the child is not improving.",
    "GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C": "Give fluid for severe dehydration according to Plan C.",
    "GIVE_FLUID_ZINC_AND_FOOD_PLAN_B": "Give fluid, zinc, and food according to Plan B.",
    "GIVE_FLUID_ZINC_AND_FOOD_PLAN_A": "Give fluid, zinc, and food according to Plan A.",
    "FREQUENT_ORS_SIPS_DURING_REFERRAL": "Give frequent sips of ORS during referral.",
    "CONTINUE_BREASTFEEDING": "Continue breastfeeding during referral.",
    "TREAT_DEHYDRATION_BEFORE_REFERRAL": "Treat dehydration before referral unless another severe classification prevents this.",
    "ADVISE_FEEDING_FOR_PERSISTENT_DIARRHOEA": "Advise the caregiver about feeding for persistent diarrhoea.",
    "GIVE_MULTIVITAMINS_MINERALS_ZINC_14_DAYS": "Give multivitamins, minerals, and zinc for 14 days.",
    "GIVE_CIPROFLOXACIN_3_DAYS": "Give ciprofloxacin for 3 days.",
    "GIVE_CHOLERA_ANTIBIOTIC_PER_LOCAL_PROTOCOL": "Give the antibiotic for cholera specified by the applicable local protocol.",
    "REASSESS_DEHYDRATION_AFTER_PLAN_B": "Reassess and reclassify dehydration after Plan B.",
    "REASSESS_DEHYDRATION_AFTER_PLAN_C": "Reassess and reclassify dehydration after Plan C.",
    "GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT": "Give the first dose of severe-malaria treatment.",
    "GIVE_FIRST_LINE_ORAL_ANTIMALARIAL": "Give the first-line oral antimalarial.",
    "GIVE_PARACETAMOL_FOR_HIGH_FEVER": "Give paracetamol for high fever.",
    "GIVE_PARACETAMOL_FOR_EAR_PAIN": "Give paracetamol for ear pain.",
    "GIVE_APPROPRIATE_ANTIBIOTIC_FOR_IDENTIFIED_BACTERIAL_CAUSE": "Give the appropriate antibiotic treatment specified by the applicable protocol for the identified bacterial cause.",
    "REFER_PROLONGED_FEVER_FOR_ASSESSMENT": "Refer for assessment of prolonged fever.",
    "GIVE_VITAMIN_A_TREATMENT": "Give vitamin A treatment.",
    "APPLY_TETRACYCLINE_EYE_OINTMENT": "Apply tetracycline eye ointment.",
    "TREAT_MOUTH_ULCERS_WITH_GENTIAN_VIOLET": "Treat mouth ulcers with gentian violet.",
    "GIVE_ANTIBIOTIC_5_DAYS": "Give the indicated antibiotic for 5 days.",
    "DRY_EAR_BY_WICKING": "Dry the ear by wicking.",
    "GIVE_TOPICAL_QUINOLONE_EARDROPS_14_DAYS": "Give topical quinolone eardrops for 14 days.",
    "NO_EAR_TREATMENT": "No ear treatment is indicated.",
}

ACQUISITION_SPECS = {
    "danger_signs.vomits_everything": ("CAREGIVER_QUESTION", "Ask the caregiver whether the child vomits everything."),
    "diarrhoea.cholera_in_area": ("AREA_CONTEXT", "Confirm whether cholera is present in the area."),
    "diarrhoea.dehydration.drinking_status": ("CLINICIAN_OBSERVATION", "Offer fluid and observe whether the child drinks normally, eagerly or thirstily, poorly, or is unable to drink."),
    "diarrhoea.duration_days": ("CAREGIVER_QUESTION", "Ask the caregiver how many days the child has had diarrhoea."),
    "ear.ear_discharge_duration_days": ("CAREGIVER_QUESTION", "Ask the caregiver how many days the ear discharge has been present."),
    "fever.malaria_risk": ("AREA_CONTEXT", "Provide the malaria-risk category of the area: high, low, or no malaria risk."),
    "fever.malaria_test_result": ("DIAGNOSTIC_TEST", "Perform or report the indicated malaria test result."),
    "patient_facts.age_months": ("HISTORY_OR_RECORD", "Confirm the child's age in completed months from the caregiver or record."),
    "patient_facts.has_cough_or_difficult_breathing": ("CAREGIVER_QUESTION", "Ask whether the child has cough or difficult breathing."),
    "patient_facts.has_diarrhoea": ("CAREGIVER_QUESTION", "Ask whether the child has diarrhoea."),
    "patient_facts.has_ear_problem": ("CAREGIVER_QUESTION", "Ask whether the child has an ear problem, including ear pain or discharge."),
    "patient_facts.has_fever": ("CAREGIVER_QUESTION", "Ask whether the child has fever and report the measured temperature when applicable."),
    "respiratory.bronchodilator_trial_completed": ("INTERVENTION_REASSESSMENT", "Complete the indicated rapid-acting inhaled bronchodilator trial and record that it was completed."),
    "respiratory.hiv_exposed_or_infected": ("HISTORY_OR_RECORD", "Confirm from the history or record whether the child is HIV-exposed or HIV-infected."),
    "respiratory.oxygen_saturation_percent": ("MEASUREMENT", "Measure and report the oxygen saturation."),
    "respiratory.post_bronchodilator_breaths_counted_one_minute": ("MEASUREMENT", "During post-bronchodilator reassessment, count breaths for one full minute."),
    "respiratory.post_bronchodilator_chest_indrawing": ("CLINICIAN_OBSERVATION", "Reassess chest indrawing after the bronchodilator trial."),
    "respiratory.post_bronchodilator_child_calm": ("CLINICIAN_OBSERVATION", "Confirm that the child is calm for the post-bronchodilator breathing reassessment."),
    "respiratory.post_bronchodilator_respiratory_rate": ("MEASUREMENT", "Measure and report the post-bronchodilator respiratory rate while the child is calm."),
    "respiratory.respiratory_rate": ("MEASUREMENT", "Count the respiratory rate for one full minute while the child is calm and report the breaths per minute."),
}

_CONTRADICTION_CLARIFICATIONS = {
    "respiratory observations are invalid because the child was not calm": (
        ("respiratory.child_calm", "CLINICIAN_OBSERVATION", "Settle the child and confirm that the child is calm."),
        ("respiratory.respiratory_rate", "MEASUREMENT", "Repeat the respiratory-rate count for one full minute while the child is calm."),
    ),
    "respiratory rate is invalid because breaths were not counted for one minute": (
        ("respiratory.breaths_counted_one_minute", "MEASUREMENT", "Repeat the breath count for one full minute."),
        ("respiratory.respiratory_rate", "MEASUREMENT", "Report the repeated respiratory-rate value while the child is calm."),
    ),
    "UNABLE observed drinking conflicts with a negative general danger sign": (
        ("danger_signs.unable_to_drink_or_breastfeed", "CLINICIAN_OBSERVATION", "Clinically reassess the child's ability to drink or breastfeed."),
        ("diarrhoea.dehydration.drinking_status", "CLINICIAN_OBSERVATION", "Reassess the diarrhoea-specific drinking response."),
    ),
}

CONTRADICTION_SENTENCES = {
    "respiratory observations are invalid because the child was not calm": (
        "respiratory observations are invalid because the child was not calm"
    ),
    "respiratory rate is invalid because breaths were not counted for one minute": (
        "respiratory rate is invalid because breaths were not counted for one minute"
    ),
    "UNABLE observed drinking conflicts with a negative general danger sign": (
        "The general danger-sign assessment says the child can drink or breastfeed, but the "
        "diarrhoea assessment records the child as unable to drink"
    ),
}


def load_response_grammar() -> dict[str, Any]:
    grammar = json.loads(DEFAULT_GRAMMAR_PATH.read_text(encoding="utf-8"))
    expected = {
        "grammar_id": RESPONSE_GRAMMAR_ID,
        "status": "APPROVED_FOR_GOLDEN_LANGUAGE_REMEDIATION",
        "approval_authority": "PROJECT_OWNER",
    }
    for key, value in expected.items():
        if grammar.get(key) != value:
            raise ValueError(f"incorrect EdgeIMCI response grammar {key}")
    if grammar.get("semantic_source") != {
        "suite_id": SEMANTIC_SUITE_ID,
        "sha256": SEMANTIC_CASES_SHA256,
    }:
        raise ValueError("response grammar has incorrect semantic source")
    pre_format = grammar.get("pre_format_review", {})
    if pre_format.get("language_renderings_sha256") != PRE_FORMAT_LANGUAGE_SHA256:
        raise ValueError("response grammar has incorrect pre-format language hash")
    format_re_review = grammar.get("format_re_review", {})
    if format_re_review.get("language_renderings_sha256") != PRE_REMEDIATION_LANGUAGE_SHA256:
        raise ValueError("response grammar has incorrect pre-remediation language hash")
    if format_re_review.get("findings_addressed") != [
        "LGR-GR-001",
        "LGR-GR-002",
        "LGR-GR-003",
        "LGR-GR-004",
    ]:
        raise ValueError("response grammar has incorrect remediation finding set")
    presentation_order = grammar.get("presentation_order", {})
    action_priority = presentation_order.get("action_priority", {})
    if set(action_priority) != set(ACTION_SENTENCES):
        raise ValueError("response grammar action priority must cover every supported action")
    clarification_observations = {
        observation_id
        for requests in _CONTRADICTION_CLARIFICATIONS.values()
        for observation_id, _, _ in requests
    }
    acquisition_priority = presentation_order.get("acquisition_priority", {})
    if set(acquisition_priority) != set(ACQUISITION_SPECS) | clarification_observations:
        raise ValueError("response grammar acquisition priority must cover every supported request")
    if presentation_order.get("stable_within_equal_priority") is not True:
        raise ValueError("response grammar must preserve source order within equal priorities")
    change_control = grammar.get("change_control", {})
    if change_control.get("clinical_semantics_changed") is not False:
        raise ValueError("response grammar must not change clinical semantics")
    if change_control.get("semantic_alignment_changed") is not False:
        raise ValueError("response grammar must not change semantic alignment")
    if change_control.get("full_language_records_return_to_review") is not True:
        raise ValueError("response grammar must return full-language records to review")
    if any(
        change_control.get(key) is not False
        for key in (
            "teacher_bakeoff_authorized",
            "training_authorized",
            "production_clinical_use_authorized",
        )
    ):
        raise ValueError("response grammar cannot authorize downstream or production use")
    return grammar


def load_full_language_approval() -> dict[str, Any]:
    approval = json.loads(DEFAULT_FULL_APPROVAL_PATH.read_text(encoding="utf-8"))
    expected = {
        "approval_id": FULL_LANGUAGE_APPROVAL_ID,
        "status": "APPROVED_AND_FROZEN_FOR_HACKATHON_SCOPE",
        "approval_authority": "PROJECT_OWNER",
        "language_suite_id": FULL_LANGUAGE_SUITE_ID,
        "reviewed_language_renderings_sha256": APPROVED_REMEDIATED_LANGUAGE_SHA256,
        "semantic_suite_id": SEMANTIC_SUITE_ID,
        "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
        "response_grammar_id": RESPONSE_GRAMMAR_ID,
        "response_grammar_sha256": APPROVED_RESPONSE_GRAMMAR_SHA256,
        "production_clinical_use_authorized": False,
        "qualified_phc_field_validation_completed": False,
    }
    for key, value in expected.items():
        if approval.get(key) != value:
            raise ValueError(f"incorrect full golden language approval {key}")
    if hashlib.sha256(DEFAULT_GRAMMAR_PATH.read_bytes()).hexdigest() != APPROVED_RESPONSE_GRAMMAR_SHA256:
        raise ValueError("approved response grammar hash does not match the canonical grammar")
    frozen_hash = approval.get("frozen_language_renderings_sha256")
    if not isinstance(frozen_hash, str) or len(frozen_hash) != 64:
        raise ValueError("full language approval must pin the frozen language hash")
    if approval.get("eligibility_authorized") != {
        "HOLISTIC_GENERATION": True,
        "PRODUCT_EVALUATION": True,
        "TEACHER_BAKEOFF": True,
        "TRAINING": False,
    }:
        raise ValueError("incorrect approved full language eligibility")
    return approval


def _known_bool(label: str, value: bool | None) -> str | None:
    if value is None:
        return None
    return label if value else f"no {label}"


def render_encounter_input(encounter: dict[str, Any]) -> str:
    facts = encounter["patient_facts"]
    parts: list[str] = []
    if facts["age_months"] is not None:
        parts.append(f"This child is {facts['age_months']} months old.")

    danger = encounter["danger_signs"]
    danger_parts = []
    if danger["unable_to_drink_or_breastfeed"] is not None:
        danger_parts.append(
            "is unable to drink or breastfeed"
            if danger["unable_to_drink_or_breastfeed"]
            else "can drink or breastfeed"
        )
    if danger["vomits_everything"] is not None:
        danger_parts.append("vomits everything" if danger["vomits_everything"] else "does not vomit everything")
    if danger["had_convulsions"] is not None:
        danger_parts.append(
            "has had convulsions during this illness"
            if danger["had_convulsions"]
            else "has had no convulsions during this illness"
        )
    if danger["lethargic_or_unconscious"] is not None:
        danger_parts.append(
            "is lethargic or unconscious"
            if danger["lethargic_or_unconscious"]
            else "is not lethargic or unconscious"
        )
    if danger["convulsing_now"] is not None:
        danger_parts.append("is convulsing now" if danger["convulsing_now"] else "is not convulsing now")
    if danger_parts:
        parts.append("The child " + _join(danger_parts) + ".")

    respiratory = encounter.get("respiratory")
    if facts["has_cough_or_difficult_breathing"] is False:
        parts.append("There is no cough or difficult breathing.")
    elif facts["has_cough_or_difficult_breathing"] is True and respiratory is not None:
        resp = ["The child has cough or difficult breathing"]
        if respiratory["cough_duration_days"] is not None:
            resp[0] += f" for {respiratory['cough_duration_days']} days"
        resp[0] += "."
        if respiratory["child_calm"] is not None:
            resp.append("The child was calm." if respiratory["child_calm"] else "The child was not calm.")
        if respiratory["breaths_counted_one_minute"] is not None:
            resp.append(
                "Breaths were counted for one full minute."
                if respiratory["breaths_counted_one_minute"]
                else "Breaths were not counted for one full minute."
            )
        if respiratory["respiratory_rate"] is not None:
            resp.append(f"The recorded respiratory rate is {respiratory['respiratory_rate']} breaths per minute.")
        for key, present, absent in (
            ("chest_indrawing", "Chest indrawing is present.", "There is no chest indrawing."),
            ("stridor_when_calm", "Stridor is present while calm.", "There is no stridor while calm."),
            ("wheezing", "Wheezing is present.", "There is no wheezing."),
            ("recurrent_wheeze", "There is recurrent wheeze.", "There is no recurrent wheeze."),
        ):
            if respiratory[key] is not None:
                resp.append(present if respiratory[key] else absent)
        if respiratory["pulse_oximeter_available"] is not None:
            resp.append(
                "A pulse oximeter is available."
                if respiratory["pulse_oximeter_available"]
                else "A pulse oximeter is not available."
            )
        if respiratory["oxygen_saturation_percent"] is not None:
            resp.append(f"The oxygen saturation is {respiratory['oxygen_saturation_percent']}%.")
        if respiratory["hiv_exposed_or_infected"] is not None:
            resp.append(
                "The child is HIV-exposed or HIV-infected."
                if respiratory["hiv_exposed_or_infected"]
                else "The child is not known to be HIV-exposed or HIV-infected."
            )
        if respiratory["bronchodilator_trial_completed"] is not None:
            resp.append(
                "The indicated rapid-acting inhaled bronchodilator trial was completed."
                if respiratory["bronchodilator_trial_completed"]
                else "The indicated rapid-acting inhaled bronchodilator trial has not been completed."
            )
        post_fields = (
            respiratory["post_bronchodilator_child_calm"],
            respiratory["post_bronchodilator_breaths_counted_one_minute"],
            respiratory["post_bronchodilator_respiratory_rate"],
            respiratory["post_bronchodilator_chest_indrawing"],
        )
        if any(value is not None for value in post_fields):
            post = []
            if post_fields[0] is not None:
                post.append("the child was calm" if post_fields[0] else "the child was not calm")
            if post_fields[1] is not None:
                post.append("breaths were counted for one full minute" if post_fields[1] else "breaths were not counted for one full minute")
            if post_fields[2] is not None:
                post.append(f"the respiratory rate was {post_fields[2]} breaths per minute")
            if post_fields[3] is not None:
                post.append("chest indrawing was present" if post_fields[3] else "there was no chest indrawing")
            resp.append("On post-bronchodilator reassessment, " + _join(post) + ".")
        parts.append(" ".join(resp))

    diarrhoea = encounter.get("diarrhoea")
    if facts["has_diarrhoea"] is False:
        parts.append("There is no diarrhoea.")
    elif facts["has_diarrhoea"] is True and diarrhoea is not None:
        dia = ["The child has diarrhoea"]
        if diarrhoea["duration_days"] is not None:
            dia[0] += f" for {diarrhoea['duration_days']} days"
        dia[0] += "."
        if diarrhoea["blood_in_stool"] is not None:
            dia.append("There is blood in the stool." if diarrhoea["blood_in_stool"] else "There is no blood in the stool.")
        dehydration = diarrhoea["dehydration"]
        for key, present, absent in (
            ("restless_or_irritable", "The child is restless or irritable.", "The child is not restless or irritable."),
            ("sunken_eyes", "The eyes are sunken.", "The eyes are not sunken."),
        ):
            if dehydration[key] is not None:
                dia.append(present if dehydration[key] else absent)
        drinking = dehydration["drinking_status"]
        if drinking is not None:
            drinking_text = {
                "NORMAL": "drinks normally",
                "EAGER_OR_THIRSTY": "drinks eagerly and appears thirsty",
                "POORLY": "drinks poorly",
                "UNABLE": "is unable to drink",
            }[drinking]
            dia.append(f"When offered fluid, the child {drinking_text}.")
        if dehydration["skin_pinch"] is not None:
            pinch = {"NORMAL": "normally", "SLOWLY": "slowly", "VERY_SLOWLY": "very slowly"}[
                dehydration["skin_pinch"]
            ]
            dia.append(f"The abdominal skin pinch returns {pinch}.")
        if diarrhoea["cholera_in_area"] is not None:
            dia.append("Cholera is present in the area." if diarrhoea["cholera_in_area"] else "Cholera is not present in the area.")
        if diarrhoea["rehydration_stage"] is not None:
            dia.append(f"The recorded rehydration stage is {diarrhoea['rehydration_stage'].lower().replace('_', ' ')}.")
        if diarrhoea["post_rehydration"] is not None:
            dia.append("Post-rehydration findings were supplied for a new complete assessment.")
        parts.append(" ".join(dia))

    fever = encounter.get("fever")
    if facts["has_fever"] is False:
        parts.append("There is no fever.")
    elif facts["has_fever"] is True and fever is not None:
        feb = ["The child has fever."]
        if fever["temperature_c"] is not None:
            feb.append(f"The measured temperature is {fever['temperature_c']}°C.")
        if fever["fever_duration_days"] is not None:
            feb.append(f"Fever has been present for {fever['fever_duration_days']} days.")
        if fever["fever_present_every_day"] is not None:
            feb.append("Fever has been present every day." if fever["fever_present_every_day"] else "Fever has not been present every day.")
        if fever["malaria_risk"] is not None:
            risk = {"HIGH": "high", "LOW": "low", "NONE_NO_TRAVEL": "no"}[fever["malaria_risk"]]
            feb.append(f"This is a {risk}-malaria-risk area.")
        for key, present, absent in (
            ("stiff_neck", "A stiff neck is present.", "There is no stiff neck."),
            ("runny_nose", "A runny nose is present.", "There is no runny nose."),
            ("obvious_cause_of_fever_present", "An obvious cause of fever is present.", "No obvious cause of fever is present."),
            ("identified_bacterial_cause_present", "A bacterial cause of fever has been identified.", "No bacterial cause of fever has been identified."),
            ("measles_within_last_3_months", "The child has had measles within the last 3 months.", "The child has not had measles within the last 3 months."),
            ("generalized_rash", "A generalized rash is present.", "There is no generalized rash."),
            ("measles_cough", "The measles assessment records cough.", "The measles assessment records no cough."),
            ("red_eyes", "The eyes are red.", "The eyes are not red."),
            ("mouth_ulcers", "Mouth ulcers are present.", "There are no mouth ulcers."),
            ("mouth_ulcers_deep_or_extensive", "The mouth ulcers are deep or extensive.", "The mouth ulcers are not deep or extensive."),
            ("pus_draining_from_eye", "Pus is draining from the eye.", "There is no pus draining from the eye."),
            ("clouding_of_cornea", "Clouding of the cornea is present.", "There is no clouding of the cornea."),
        ):
            if fever[key] is not None:
                feb.append(present if fever[key] else absent)
        if fever["malaria_test_available"] is not None:
            feb.append("Malaria testing is available." if fever["malaria_test_available"] else "Malaria testing is not available.")
        if fever["malaria_test_result"] is not None:
            feb.append(f"The malaria test is {fever['malaria_test_result'].lower()}.")
        parts.append(" ".join(feb))

    ear = encounter.get("ear")
    if facts["has_ear_problem"] is False:
        parts.append("There is no ear problem.")
    elif facts["has_ear_problem"] is True and ear is not None:
        ear_parts = ["The child has an ear problem."]
        for key, present, absent in (
            ("ear_pain", "Ear pain is present.", "There is no ear pain."),
            ("ear_discharge_reported", "The caregiver reports ear discharge.", "The caregiver reports no ear discharge."),
            ("pus_draining_from_ear", "Pus is draining from the ear.", "There is no pus draining from the ear."),
            ("tender_swelling_behind_ear", "Tender swelling is present behind the ear.", "There is no tender swelling behind the ear."),
        ):
            if ear[key] is not None:
                ear_parts.append(present if ear[key] else absent)
        if ear["ear_discharge_duration_days"] is not None:
            ear_parts.append(f"Ear discharge has been present for {ear['ear_discharge_duration_days']} days.")
        parts.append(" ".join(ear_parts))
    return " ".join(parts)


def _join(items: list[str]) -> str:
    if len(items) < 2:
        return items[0] if items else ""
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _flatten_missing(missing: dict[str, list[str]]) -> list[str]:
    return sorted(field for fields in missing.values() for field in fields)


def _clarifications(evaluation: dict[str, Any]) -> tuple[list[dict[str, str]], list[str], list[str]]:
    requests: list[dict[str, str]] = []
    targets: list[str] = []
    prompts: list[str] = []
    for contradiction in evaluation["contradictions"]:
        for observation_id, mode, prompt in _CONTRADICTION_CLARIFICATIONS[contradiction]:
            if observation_id not in targets:
                targets.append(observation_id)
                requests.append({"observation_id": observation_id, "acquisition_mode": mode})
                prompts.append(prompt)
    return requests, targets, prompts


def _ordered_action_ids(actions: list[str] | tuple[str, ...]) -> list[str]:
    priorities = load_response_grammar()["presentation_order"]["action_priority"]
    return sorted(actions, key=priorities.__getitem__)


def _ordered_missing_fields(missing: dict[str, list[str]]) -> list[str]:
    priorities = load_response_grammar()["presentation_order"]["acquisition_priority"]
    return sorted(_flatten_missing(missing), key=priorities.__getitem__)


def _alignment(semantic_record: dict[str, Any]) -> dict[str, Any]:
    expected = semantic_record["expected"]
    if expected["kind"] == "SCHEMA_REJECTION":
        return {
            "expected_state": "SCHEMA_REJECTION",
            "supported_encounter_complete": None,
            "final_synthesis_authorized": None,
            "urgent_action_required": None,
            "classifications_covered": [],
            "actions_covered": [],
            "deferred_actions_acknowledged": [],
            "missing_elements_covered": [],
            "contradictions_covered": [],
            "acquisition_requests": [],
            "clarification_targets": [],
        }
    evaluation = expected["evaluation"]
    missing = _flatten_missing(evaluation["missing_elements"])
    requests = [
        {"observation_id": field, "acquisition_mode": ACQUISITION_SPECS[field][0]}
        for field in missing
    ]
    clarification_requests, targets, _ = _clarifications(evaluation)
    requests.extend(clarification_requests)
    return {
        "expected_state": "COMPLETE" if evaluation["supported_encounter_complete"] else "INCOMPLETE",
        "supported_encounter_complete": evaluation["supported_encounter_complete"],
        "final_synthesis_authorized": evaluation["final_holistic_synthesis_authorized"],
        "urgent_action_required": evaluation["urgent_action_required"],
        "classifications_covered": [item["classification"] for item in evaluation["final_classifications"]],
        "actions_covered": list(evaluation["final_actions"] or evaluation["urgent_actions"]),
        "deferred_actions_acknowledged": list(evaluation["deferred_actions"]),
        "missing_elements_covered": missing,
        "contradictions_covered": list(evaluation["contradictions"]),
        "acquisition_requests": requests,
        "clarification_targets": targets,
    }


def _action_sentence(action: str, semantic_record: dict[str, Any]) -> str:
    encounter = semantic_record.get("input", {}).get("encounter", {})
    respiratory = encounter.get("respiratory") or {}
    post_treatment_available = (
        respiratory.get("bronchodilator_trial_completed") is True
        and respiratory.get("post_bronchodilator_child_calm") is not None
    )
    if post_treatment_available and action == "GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL":
        return "The rapid-acting inhaled bronchodilator trial was completed."
    if post_treatment_available and action == "REASSESS_BREATHING_AFTER_BRONCHODILATOR":
        return "Breathing was reassessed after the bronchodilator trial."
    return ACTION_SENTENCES[action]


def _response_state(expected: dict[str, Any]) -> str:
    if expected["kind"] == "SCHEMA_REJECTION":
        return "OUT_OF_SCOPE"
    evaluation = expected["evaluation"]
    if evaluation["supported_encounter_complete"]:
        return "URGENT_COMPLETE" if evaluation["urgent_action_required"] else "COMPLETE"
    return "URGENT_INCOMPLETE" if evaluation["urgent_action_required"] else "INCOMPLETE"


def render_assistant(semantic_record: dict[str, Any]) -> str:
    load_response_grammar()
    expected = semantic_record["expected"]
    if expected["kind"] == "SCHEMA_REJECTION":
        return (
            "OUTSIDE SUPPORTED SCOPE\n\n"
            "This encounter is outside the supported EdgeIMCI major sick-child scope, which starts "
            "at 2 completed months and ends before 60 months. I cannot provide a classification or "
            "management plan from this workflow. Use the applicable approved age-specific pathway."
        )
    evaluation = expected["evaluation"]
    blocks: list[str] = []
    if evaluation["urgent_action_required"]:
        blocks.append("URGENT: Act now and do not delay referral.")

    if evaluation["supported_encounter_complete"]:
        classifications = [
            CLASSIFICATION_LABELS[item["classification"]]
            for item in evaluation["final_classifications"]
        ]
        classification_lines = classifications or [
            "None of the currently supported classifications is triggered."
        ]
        blocks.append(
            "Classifications:\n" + "\n".join(f"- {item}" for item in classification_lines)
        )
        actions = _ordered_action_ids(evaluation["final_actions"])
        action_lines = [
            _action_sentence(action, semantic_record) for action in actions
        ] or ["No management action is indicated by the supported assessment."]
        management_heading = (
            "Immediate management:" if evaluation["urgent_action_required"] else "Management:"
        )
        blocks.append(
            management_heading + "\n" + "\n".join(f"- {item}" for item in action_lines)
        )
        if evaluation["deferred_actions"]:
            blocks.append(
                "Deferred routine care:\n"
                "- Routine home-care counselling and scheduled follow-up are deferred so they do "
                "not delay or compete with the urgent referral workflow."
            )
        return "\n\n".join(blocks)

    urgent_actions = _ordered_action_ids(evaluation["urgent_actions"])
    if urgent_actions:
        blocks.append(
            "Immediate management:\n"
            + "\n".join(
                f"- {_action_sentence(item, semantic_record)}" for item in urgent_actions
            )
        )
    blocks.append("ASSESSMENT INCOMPLETE")
    requests = [
        ACQUISITION_SPECS[field][1]
        for field in _ordered_missing_fields(evaluation["missing_elements"])
    ]
    _, _, clarification_prompts = _clarifications(evaluation)
    if evaluation["contradictions"]:
        blocks.append(
            "Conflicting or invalid findings:\n"
            + "\n".join(
                f"- {CONTRADICTION_SENTENCES[item]}."
                for item in evaluation["contradictions"]
            )
        )
    requests.extend(clarification_prompts)
    if requests:
        heading = (
            "Information still needed:"
            if evaluation["urgent_action_required"]
            else "Information needed:"
        )
        blocks.append(heading + "\n" + "\n".join(f"- {item}" for item in requests))
    if evaluation["urgent_action_required"]:
        blocks.append(
            "Complete these checks rapidly, but do not delay referral. The final holistic "
            "classifications and complete management plan remain pending."
        )
    else:
        blocks.append(
            "I cannot provide the final classifications and complete management plan until these "
            "findings are supplied."
        )
    return "\n\n".join(blocks)


def build_full_language_suite() -> list[dict[str, Any]]:
    load_response_grammar()
    actual_hash = hashlib.sha256(SEMANTIC_JSONL_PATH.read_bytes()).hexdigest()
    if actual_hash != SEMANTIC_CASES_SHA256:
        raise ValueError("frozen semantic suite hash does not match full language pin")
    semantics = load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    anchors = {item["golden_case_id"]: item for item in load_language_calibration(corpus_use=CorpusUse.HOLISTIC_GENERATION)}
    records: list[dict[str, Any]] = []
    for semantic in semantics:
        case_id = semantic["golden_case_id"]
        anchor = anchors.get(case_id)
        if case_id in anchors:
            alignment = anchor["alignment"]
            user_content = anchor["conversation"][0]["content"]
            notes = (
                "Project-owner approved for the bounded hackathon after language remediation; "
                "the frozen calibration user submission and semantic alignment are preserved. "
                "This is not qualified PHC field validation."
            )
        else:
            alignment = _alignment(semantic)
            user_content = render_encounter_input(semantic["input"]["encounter"])
            notes = (
                "Project-owner approved for the bounded hackathon after language remediation. "
                "This is not qualified PHC field validation."
            )
        conversation = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": render_assistant(semantic)},
        ]
        review = {
            "semantic_faithfulness": "APPROVED_FOR_HACKATHON_SCOPE",
            "interaction_quality": "APPROVED_FOR_HACKATHON_SCOPE",
            "phc_suitability": "PROJECT_OWNER_APPROVED_FOR_HACKATHON_DEMO_NOT_FIELD_VALIDATED",
            "reviewer": "PROJECT_OWNER",
            "notes": notes,
        }
        records.append(
            {
                "record_schema_id": LANGUAGE_RECORD_SCHEMA_ID,
                "rendering_id": f"{case_id}-language-v1",
                "golden_case_id": case_id,
                "status": "FROZEN",
                "corpus_role": "HOLISTIC_PRODUCT_GOLDEN_LANGUAGE",
                "semantic_source": {
                    "suite_id": SEMANTIC_SUITE_ID,
                    "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
                    "golden_case_logic_signature": semantic["metadata"]["logic_signature"],
                },
                "conversation": conversation,
                "alignment": alignment,
                "review": review,
            }
        )
    return records


def validate_response_grammar(record: dict[str, Any], semantic: dict[str, Any]) -> None:
    load_response_grammar()
    assistant = record["conversation"][1]["content"]
    state = _response_state(semantic["expected"])
    alignment = record["alignment"]

    if state == "OUT_OF_SCOPE":
        if not assistant.startswith("OUTSIDE SUPPORTED SCOPE\n\n"):
            raise ValueError("out-of-scope response has incorrect grammar")
        if "Classifications:" in assistant or "Management:" in assistant:
            raise ValueError("out-of-scope response must not synthesize classifications or management")
        return

    if state == "URGENT_COMPLETE" or state == "URGENT_INCOMPLETE":
        if not assistant.startswith("URGENT: Act now and do not delay referral."):
            raise ValueError("urgent response must begin with the exact urgent delimiter")
    elif assistant.startswith("URGENT:"):
        raise ValueError("non-urgent response must not use the urgent delimiter")

    if state == "COMPLETE" or state == "URGENT_COMPLETE":
        expected_start = "Classifications:" if state == "COMPLETE" else "\n\nClassifications:"
        if expected_start not in assistant:
            raise ValueError("complete response must use the plural classifications heading")
        for classification in alignment["classifications_covered"]:
            if f"- {CLASSIFICATION_LABELS[classification]}" not in assistant:
                raise ValueError(f"response omits classification bullet {classification}")
        if not alignment["classifications_covered"] and (
            "- None of the currently supported classifications is triggered." not in assistant
        ):
            raise ValueError("no-classification response must use the canonical classification bullet")
        management_heading = (
            "Immediate management:" if state == "URGENT_COMPLETE" else "Management:"
        )
        if f"\n\n{management_heading}\n" not in assistant:
            raise ValueError("complete response has incorrect management heading")
        for action in alignment["actions_covered"]:
            if f"- {_action_sentence(action, semantic)}" not in assistant:
                raise ValueError(f"response omits action bullet {action}")
        if not alignment["actions_covered"] and (
            "- No management action is indicated by the supported assessment." not in assistant
        ):
            raise ValueError("no-action response must use the canonical management bullet")
        if alignment["deferred_actions_acknowledged"]:
            if "\n\nDeferred routine care:\n- " not in assistant:
                raise ValueError("response omits canonical deferred-care section")
        elif "Deferred routine care:" in assistant:
            raise ValueError("response invents a deferred-care section")
        if "ASSESSMENT INCOMPLETE" in assistant:
            raise ValueError("complete response must not use the incomplete delimiter")
        return

    if "ASSESSMENT INCOMPLETE" not in assistant:
        raise ValueError("incomplete response must use the canonical incomplete delimiter")
    information_heading = (
        "Information still needed:" if state == "URGENT_INCOMPLETE" else "Information needed:"
    )
    if f"\n\n{information_heading}\n" not in assistant:
        raise ValueError("incomplete response has incorrect information heading")
    if state == "URGENT_INCOMPLETE":
        if "\n\nImmediate management:\n" not in assistant:
            raise ValueError("urgent incomplete response omits immediate management")
        for action in alignment["actions_covered"]:
            if f"- {_action_sentence(action, semantic)}" not in assistant:
                raise ValueError(f"urgent incomplete response omits action bullet {action}")
    elif "Immediate management:" in assistant:
        raise ValueError("non-urgent incomplete response invents immediate management")
    for request in alignment["acquisition_requests"]:
        field = request["observation_id"]
        if field in alignment["clarification_targets"]:
            prompt = next(
                prompt
                for observation_id, _, prompt in sum(
                    (_CONTRADICTION_CLARIFICATIONS[key] for key in alignment["contradictions_covered"]),
                    (),
                )
                if observation_id == field
            )
        else:
            prompt = ACQUISITION_SPECS[field][1]
        if f"- {prompt}" not in assistant:
            raise ValueError(f"incomplete response omits acquisition bullet {field}")
    if alignment["contradictions_covered"]:
        if "\n\nConflicting or invalid findings:\n" not in assistant:
            raise ValueError("contradictory response omits conflict heading")
    elif "Conflicting or invalid findings:" in assistant:
        raise ValueError("response invents a conflict section")


def validate_full_language_record(
    record: dict[str, Any], semantic: dict[str, Any], anchor: dict[str, Any] | None
) -> None:
    schema = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(record)
    expected_alignment = anchor["alignment"] if anchor is not None else _alignment(semantic)
    if record["alignment"] != expected_alignment:
        raise ValueError("full language alignment does not exactly match its semantic/style source")
    if record["semantic_source"]["golden_case_logic_signature"] != semantic["metadata"]["logic_signature"]:
        raise ValueError("full language record has incorrect case logic signature")
    if anchor is not None:
        if record["conversation"][0] != anchor["conversation"][0]:
            raise ValueError("format remediation changed a frozen-anchor user submission")
        if record["alignment"] != anchor["alignment"]:
            raise ValueError("format remediation changed frozen-anchor semantic alignment")
    elif record["conversation"][0]["content"] != render_encounter_input(
        semantic["input"]["encounter"]
    ):
        raise ValueError("generated full-language user submission is not deterministic")
    if record["conversation"][1]["content"] != render_assistant(semantic):
        raise ValueError("full-language assistant response is not deterministic")
    if record["status"] != "FROZEN":
        raise ValueError("approved full-language records must be frozen")
    if record["review"] != {
        "semantic_faithfulness": "APPROVED_FOR_HACKATHON_SCOPE",
        "interaction_quality": "APPROVED_FOR_HACKATHON_SCOPE",
        "phc_suitability": "PROJECT_OWNER_APPROVED_FOR_HACKATHON_DEMO_NOT_FIELD_VALIDATED",
        "reviewer": "PROJECT_OWNER",
        "notes": record["review"]["notes"],
    }:
        raise ValueError("approved full-language records have incorrect review disposition")
    for turn in record["conversation"]:
        if "IMCI-MSC-" in turn["content"]:
            raise ValueError("user-facing full-language text leaks internal rule IDs")
        if any(action in turn["content"] for action in ACTION_SENTENCES):
            raise ValueError("user-facing full-language text leaks internal action IDs")
    validate_response_grammar(record, semantic)


def load_full_language_suite(*, corpus_use: CorpusUse = CorpusUse.DOMAIN_REVIEW) -> list[dict[str, Any]]:
    assert_corpus_use_allowed(DEFAULT_LANGUAGE_PATH, corpus_use, manifest_path=DEFAULT_MANIFEST_PATH)
    approval = load_full_language_approval()
    actual_hash = hashlib.sha256(DEFAULT_LANGUAGE_PATH.read_bytes()).hexdigest()
    if actual_hash != approval["frozen_language_renderings_sha256"]:
        raise ValueError("frozen full language hash does not match project-owner approval")
    records = [json.loads(line) for line in DEFAULT_LANGUAGE_PATH.read_text(encoding="utf-8").splitlines() if line]
    semantics = {item["golden_case_id"]: item for item in load_holistic_golden_suite()}
    anchors = {item["golden_case_id"]: item for item in load_language_calibration()}
    for record in records:
        validate_full_language_record(record, semantics[record["golden_case_id"]], anchors.get(record["golden_case_id"]))
    return records


def _manifest(
    records: list[dict[str, Any]], content_hash: str, approval: dict[str, Any]
) -> dict[str, Any]:
    return {
        "suite_id": FULL_LANGUAGE_SUITE_ID,
        "lifecycle_status": "FROZEN",
        "corpus_role": "HOLISTIC_PRODUCT_GOLDEN_LANGUAGE",
        "assets": [str(DEFAULT_LANGUAGE_PATH.relative_to(ROOT)), str(DEFAULT_LANGUAGE_YAML_PATH.relative_to(ROOT))],
        "case_count": len(records),
        "frozen_calibration_source_count": 16,
        "format_remediated_anchor_count": 16,
        "draft_rendering_count": 0,
        "frozen_rendering_count": len(records),
        "semantic_source": {
            "suite_id": SEMANTIC_SUITE_ID,
            "path": str(SEMANTIC_JSONL_PATH.relative_to(ROOT)),
            "sha256": SEMANTIC_CASES_SHA256,
        },
        "artifact_pins": {
            "record_schema_id": LANGUAGE_RECORD_SCHEMA_ID,
            "builder_id": FULL_LANGUAGE_BUILDER_ID,
            "style_approval_id": LANGUAGE_APPROVAL_ID,
            "response_grammar_id": RESPONSE_GRAMMAR_ID,
            "full_language_approval_id": FULL_LANGUAGE_APPROVAL_ID,
        },
        "pre_format_review": {
            "report": str(DEFAULT_PRE_FORMAT_REVIEW_PATH.relative_to(ROOT)),
            "language_renderings_sha256": PRE_FORMAT_LANGUAGE_SHA256,
            "result": "PASS_WITH_MINOR_FORMATTING_NOTES",
            "findings_addressed": ["LGR-FR-001", "LGR-FR-002"],
        },
        "format_re_review": {
            "report": "docs/product_holistic_golden_language_format_re_review_v1.md",
            "language_renderings_sha256": PRE_REMEDIATION_LANGUAGE_SHA256,
            "result": "READY_AFTER_LANGUAGE_REMEDIATION",
            "findings_addressed": ["LGR-GR-001", "LGR-GR-002", "LGR-GR-003", "LGR-GR-004"],
        },
        "language_renderings_sha256": content_hash,
        "review_status": "PROJECT_OWNER_APPROVED_AND_FROZEN_FOR_HACKATHON_SCOPE",
        "approval": {
            "approval_id": FULL_LANGUAGE_APPROVAL_ID,
            "reviewed_language_renderings_sha256": APPROVED_REMEDIATED_LANGUAGE_SHA256,
            "frozen_language_renderings_sha256": content_hash,
            "approval_record": "docs/product_holistic_golden_language_full_approval_v1.md",
            "response_grammar_sha256": APPROVED_RESPONSE_GRAMMAR_SHA256,
            "qualified_phc_field_validation_completed": False,
        },
        "eligibility": {
            "DOMAIN_REVIEW": True,
            "COMPONENT_VALIDATION": True,
            "HOLISTIC_GENERATION": True,
            "PRODUCT_EVALUATION": True,
            "TEACHER_BAKEOFF": True,
            "TRAINING": False,
        },
        "production_clinical_use_authorized": False,
        "qualified_phc_field_validation_completed": False,
    }


def render_full_language_review(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Product holistic golden language suite v1 — review package",
        "",
        "> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Review surface for the project-owner-approved and frozen full golden language layer.",
        "",
        f"**Status:** {len(records)} language records approved and frozen for the bounded hackathon scope. The frozen 16-case calibration remains unchanged as historical evidence.",
        "",
        f"**Frozen semantic source:** `{SEMANTIC_CASES_SHA256}`.",
        "",
        f"**Approved response grammar:** `{RESPONSE_GRAMMAR_ID}`.",
        "",
        f"**Pre-format reviewed language hash:** `{PRE_FORMAT_LANGUAGE_SHA256}`.",
        "",
        f"**Pre-remediation re-reviewed language hash:** `{PRE_REMEDIATION_LANGUAGE_SHA256}`.",
        "",
        "This artifact may now support controlled language-variant work, teacher bake-off, and product evaluation. It is not training data, production clinical authorization, or qualified PHC field validation.",
        "",
    ]
    for record in records:
        alignment = record["alignment"]
        lines.extend(
            [
                f"## {record['golden_case_id']}",
                "",
                f"**Lifecycle:** `{record['status']}` · **State:** `{alignment['expected_state']}` · **Urgent:** `{alignment['urgent_action_required']}`",
                "",
                "### PHC-worker submission",
                "",
                record["conversation"][0]["content"],
                "",
                "### EdgeIMCI response",
                "",
                record["conversation"][1]["content"],
                "",
                "### Approval disposition",
                "",
                f"- Semantic faithfulness: `{record['review']['semantic_faithfulness']}`",
                f"- Interaction quality: `{record['review']['interaction_quality']}`",
                f"- PHC suitability: `{record['review']['phc_suitability']}`",
                f"- Reviewer: `{record['review']['reviewer']}`",
                f"- Notes: {record['review']['notes']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_full_language_suite() -> list[dict[str, Any]]:
    grammar = load_response_grammar()
    approval = load_full_language_approval()
    records = build_full_language_suite()
    semantics = {item["golden_case_id"]: item for item in load_holistic_golden_suite()}
    anchors = {item["golden_case_id"]: item for item in load_language_calibration()}
    for record in records:
        validate_full_language_record(record, semantics[record["golden_case_id"]], anchors.get(record["golden_case_id"]))
    content = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    if content_hash != approval["frozen_language_renderings_sha256"]:
        raise ValueError("generated frozen full language does not match approved hash")
    DEFAULT_LANGUAGE_PATH.write_text(content, encoding="utf-8")
    DEFAULT_LANGUAGE_YAML_PATH.write_text(
        "# Generated from the canonical JSONL; do not edit this mirror.\n"
        + yaml.safe_dump(records, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    DEFAULT_MANIFEST_PATH.write_text(
        json.dumps(_manifest(records, content_hash, approval), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    DEFAULT_GRAMMAR_YAML_PATH.write_text(
        "# Generated from the canonical JSON; do not edit this mirror.\n"
        + yaml.safe_dump(grammar, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    DEFAULT_FULL_APPROVAL_YAML_PATH.write_text(
        "# Generated from the canonical JSON; do not edit this mirror.\n"
        + yaml.safe_dump(approval, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    DEFAULT_REVIEW_PATH.write_text(render_full_language_review(records), encoding="utf-8")
    return records
