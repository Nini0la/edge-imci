"""Bounded, manually authored language calibration over frozen holistic semantics."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from textwrap import dedent
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from edge_imci.corpus_policy import CorpusUse, assert_corpus_use_allowed
from edge_imci.generation.holistic_golden import (
    DEFAULT_JSONL_PATH as SEMANTIC_JSONL_PATH,
    SUITE_ID,
    load_holistic_golden_suite,
)

ROOT = Path(__file__).resolve().parents[3]
LANGUAGE_RECORD_SCHEMA_ID = "edge-imci-holistic-golden-language-record-v1"
LANGUAGE_CALIBRATION_ID = "edge-imci-holistic-golden-language-calibration-v1"
LANGUAGE_BUILDER_ID = "edge-imci-holistic-golden-language-calibration-builder-v1"
LANGUAGE_APPROVAL_ID = "edge-imci-holistic-golden-language-approval-v1"
SEMANTIC_CASES_SHA256 = "9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f"
APPROVED_REVIEWED_LANGUAGE_SHA256 = "4e05eae23aa7cc4a9371925035ee46564debf6bb004900fd37a4fefe606256b9"

DEFAULT_SCHEMA_PATH = ROOT / "configs" / "rendering" / "holistic_golden_language_record_v1.schema.json"
DEFAULT_CALIBRATION_PATH = ROOT / "data" / "golden" / "holistic_product_v1" / "language_calibration_v1.jsonl"
DEFAULT_CALIBRATION_YAML_PATH = DEFAULT_CALIBRATION_PATH.with_suffix(".yaml")
DEFAULT_MANIFEST_PATH = (
    ROOT / "data" / "golden" / "holistic_product_v1" / "language_calibration_manifest_v1.json"
)
DEFAULT_APPROVAL_PATH = ROOT / "configs" / "rendering" / "holistic_golden_language_approval_v1.json"
DEFAULT_APPROVAL_YAML_PATH = DEFAULT_APPROVAL_PATH.with_suffix(".yaml")
DEFAULT_REVIEW_PATH = ROOT / "docs" / "product_holistic_golden_language_calibration_review_v1.md"


def _draft(user: str, assistant: str, *, acquisitions: tuple[tuple[str, str], ...] = (), clarification_targets: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "user": dedent(user).strip(),
        "assistant": dedent(assistant).strip(),
        "acquisitions": acquisitions,
        "clarification_targets": clarification_targets,
    }


CALIBRATION_DRAFTS: dict[str, dict[str, Any]] = {
    "hpg-001-all-negative": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. There is no cough or difficult breathing, no diarrhoea, no fever, and no ear problem.
        """,
        """
        The supported assessment is complete. None of the currently supported IMCI classifications is triggered, and no management action is indicated by these pathways.
        """,
    ),
    "hpg-008-resp-age-2-rate-50": _draft(
        """
        This child is 2 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. The child has had cough or difficult breathing for 3 days. While calm, the respiratory rate counted for one full minute is 50 breaths per minute. There is no chest indrawing, stridor, wheeze, or recurrent wheeze. A pulse oximeter is not available. There is no diarrhoea, fever, or ear problem.
        """,
        """
        Classification: Pneumonia.

        Give oral amoxicillin for 5 days. Soothe the throat and relieve the cough with a safe remedy. Advise the caregiver when to return immediately, and follow up in 3 days.
        """,
    ),
    "hpg-014-resp-chest-hiv-positive": _draft(
        """
        This child is 18 months old and is HIV-exposed or HIV-infected. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. The child has had cough or difficult breathing for 3 days. While calm, the respiratory rate counted for one full minute is 35 breaths per minute. Chest indrawing is present, with no stridor, wheeze, or recurrent wheeze. A pulse oximeter is not available. There is no diarrhoea, fever, or ear problem.
        """,
        """
        Classification: Pneumonia.

        Give the first dose of amoxicillin, then refer the child. This finding alone calls for referral, not urgent referral.
        """,
    ),
    "hpg-016-resp-oximeter-89-9": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. The child has had cough or difficult breathing for 3 days. While calm, the respiratory rate counted for one full minute is 35 breaths per minute. There is no chest indrawing, stridor, wheeze, or recurrent wheeze. Pulse oximetry is available and the oxygen saturation is 89.9%. There is no diarrhoea, fever, or ear problem.
        """,
        """
        Classification: Cough or cold.

        Refer the child because the oxygen saturation is below 90%. This finding alone calls for referral, not urgent referral. Soothe the throat and relieve the cough with a safe remedy, advise the caregiver when to return immediately, and follow up in 5 days if the child is not improving.
        """,
    ),
    "hpg-020-resp-post-bronchodilator-improved": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. The child has had cough or difficult breathing for 3 days. Initially, while calm and counted for one full minute, the respiratory rate was 45 breaths per minute. Wheeze was present, with no chest indrawing, stridor, or recurrent wheeze. A pulse oximeter was not available. A rapid-acting inhaled bronchodilator trial was completed. On reassessment, while calm and counted for one full minute, the respiratory rate was 35 breaths per minute and there was no chest indrawing. There is no diarrhoea, fever, or ear problem.
        """,
        """
        The bronchodilator trial and breathing reassessment are complete, so use the post-treatment findings for classification.

        Classification: Cough or cold.

        Give an inhaled bronchodilator for 5 days. Soothe the throat and relieve the cough with a safe remedy. Advise the caregiver when to return immediately, and follow up in 5 days if the child is not improving.
        """,
    ),
    "hpg-028-diarrhoea-some-dehydration": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. The child has had diarrhoea for 3 days, with no blood in the stool. The child is restless or irritable and has sunken eyes, drinks normally when offered fluid, and the abdominal skin pinch returns normally. There is no cough or difficult breathing, fever, or ear problem.
        """,
        """
        Classification: Some dehydration.

        Give fluid, zinc, and food according to Plan B, then reassess and reclassify dehydration after Plan B. Advise the caregiver when to return immediately, and follow up in 5 days if the child is not improving.
        """,
    ),
    "hpg-031-diarrhoea-severe-age-24-cholera": _draft(
        """
        This child is 24 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. The child has had diarrhoea for 3 days, with no blood in the stool. The child is not restless or irritable, has sunken eyes, drinks poorly when offered fluid, and the abdominal skin pinch returns normally. Cholera is present in the area. There is no cough or difficult breathing, fever, or ear problem.
        """,
        """
        Classification: Severe dehydration.

        Give fluid for severe dehydration according to Plan C, then reassess and reclassify dehydration after Plan C. Give the antibiotic for cholera specified by the applicable local protocol.
        """,
    ),
    "hpg-052-fever-identified-bacterial-cause": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. Fever has been present for 2 days and the measured temperature is 38.0°C. This is a high-malaria-risk area; testing is available and the malaria test is negative. There is no stiff neck, runny nose, obvious cause of fever, generalized rash, measles in the last 3 months, measles-associated cough, or red eyes. A bacterial cause of fever has been identified. There is no cough or difficult breathing, diarrhoea, or ear problem.
        """,
        """
        Classification: Fever—no malaria.

        Give the appropriate antibiotic treatment specified by the applicable protocol for the identified bacterial cause. Advise the caregiver when to return immediately, and follow up in 3 days if the fever persists.
        """,
    ),
    "hpg-055-fever-severe-measles-cornea": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. Fever has been present for 2 days and the measured temperature is 38.0°C. This is a high-malaria-risk area; testing is available and the malaria test is negative. There is no stiff neck, runny nose, obvious or identified bacterial cause of fever, or measles in the last 3 months. The child has a generalized rash, red eyes, and clouding of the cornea, with no mouth ulcers or pus draining from the eye. There is no cough or difficult breathing, diarrhoea, or ear problem.
        """,
        """
        URGENT: Arrange urgent referral.

        Classifications: Fever—no malaria; severe complicated measles.

        Before referral, give vitamin A treatment and the first dose of an appropriate antibiotic, and apply tetracycline eye ointment. Routine fever home-care and scheduled follow-up instructions must not delay or compete with this urgent referral workflow.
        """,
    ),
    "hpg-068-cross-four-pathways": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. Cough or difficult breathing has been present for 3 days. While calm, the respiratory rate counted for one full minute is 42 breaths per minute, with no chest indrawing, stridor, wheeze, or recurrent wheeze; a pulse oximeter is not available. Diarrhoea has been present for 3 days with blood in the stool; the child is not restless, has no sunken eyes, drinks normally, and the skin pinch returns normally. Fever has been present for 2 days at 38.0°C in a high-malaria-risk area; the malaria test is positive. There is no stiff neck, runny nose, obvious or identified bacterial cause, or measles in the last 3 months. There is a generalized rash with cough, but no red eyes, mouth ulcers, eye pus, or corneal clouding. The child has ear pain, with no reported discharge, no pus draining, and no tender swelling behind the ear.
        """,
        """
        Classifications: Pneumonia; no dehydration and dysentery; malaria and measles; acute ear infection.

        Management:
        - Pneumonia: Give oral amoxicillin for 5 days, soothe the throat and relieve the cough with a safe remedy, and follow up in 3 days.
        - Diarrhoea and dysentery: Give Plan A fluid, zinc, and food, and give ciprofloxacin for 3 days.
        - Malaria and measles: Give the first-line oral antimalarial and give vitamin A treatment. Follow up in 3 days if fever persists.
        - Acute ear infection: Give the indicated antibiotic for 5 days, give paracetamol for ear pain, dry the ear by wicking, and follow up in 5 days.
        - Also follow up in 5 days if the child is not improving. Advise the caregiver when to return immediately.
        """,
    ),
    "hpg-070-cross-multiple-urgent": _draft(
        """
        This child is 18 months old and is convulsing now. The child can drink or breastfeed, does not vomit everything, has had no earlier convulsions during this illness, and is not lethargic or unconscious. Cough or difficult breathing has been present for 3 days. While calm, the respiratory rate counted for one full minute is 35 breaths per minute; stridor is present, with no chest indrawing or wheeze, and no pulse oximeter is available. There is no diarrhoea. Fever has been present for 2 days at 38.0°C in a high-malaria-risk area; the malaria test is negative and the child has a stiff neck. There is no runny nose, obvious or identified bacterial cause, recent measles, generalized rash, measles-associated cough, or red eyes. There is an ear problem with tender swelling behind the ear, but no ear pain, reported discharge, or pus draining.
        """,
        """
        URGENT: Give the indicated pre-referral treatment immediately and arrange urgent referral.

        Classifications: Very severe disease; severe pneumonia or very severe disease; very severe febrile disease; mastoiditis.

        Give diazepam because the child is convulsing now. Give the first dose of an appropriate antibiotic and the first dose of severe-malaria treatment, prevent low blood sugar, keep the child warm, and give paracetamol for ear pain. Complete the remaining assessment quickly, but do not delay urgent referral.
        """,
    ),
    "hpg-071-incomplete-entry-unknown": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. There is no cough or difficult breathing, no fever, and no ear problem.
        """,
        """
        I need one more finding before I can provide the final classifications and management plan.

        Ask the caregiver whether the child has diarrhoea and report the answer. An unmentioned answer cannot be treated as no.
        """,
        acquisitions=(("patient_facts.has_diarrhoea", "CAREGIVER_QUESTION"),),
    ),
    "hpg-072-incomplete-multiple-groups": _draft(
        """
        This child is 18 months old. The child can drink or breastfeed, has had no convulsions, is not lethargic or unconscious, and is not convulsing now. Cough or difficult breathing has been present for 3 days; the child is calm, there is no chest indrawing, stridor, or wheeze, and breaths were counted for one full minute, but the respiratory-rate value was not recorded. A pulse oximeter is not available. There is no diarrhoea. Fever has been present for 2 days at 38.0°C; the malaria test is available and negative. There is no stiff neck, runny nose, obvious or identified bacterial cause, recent measles, generalized rash, measles-associated cough, or red eyes.
        """,
        """
        I need the following assessment findings before I can provide the final classifications and management plan. Please complete them together:

        - Ask the caregiver whether the child vomits everything.
        - Count the respiratory rate for one full minute while the child is calm and report the breaths per minute.
        - Provide the malaria-risk category of the area: high, low, or no malaria risk. Do not infer this from a place name.
        - Ask the caregiver whether the child has an ear problem, including ear pain or ear discharge.
        """,
        acquisitions=(
            ("danger_signs.vomits_everything", "CAREGIVER_QUESTION"),
            ("respiratory.respiratory_rate", "MEASUREMENT"),
            ("fever.malaria_risk", "AREA_CONTEXT"),
            ("patient_facts.has_ear_problem", "CAREGIVER_QUESTION"),
        ),
    ),
    "hpg-073-incomplete-known-urgent": _draft(
        """
        The child is convulsing now. The child can drink or breastfeed, has had no earlier convulsions during this illness, and is not lethargic or unconscious. The child's age and the rest of the major assessment were not supplied.
        """,
        """
        URGENT: Give diazepam because the child is convulsing now. Give the indicated pre-referral treatment immediately, prevent low blood sugar, keep the child warm, and arrange urgent referral. Do not delay referral.

        A complete set of classifications and management actions still requires the remaining findings. While urgent treatment and referral are being arranged, complete the assessment quickly:

        - Ask the caregiver whether the child vomits everything.
        - Confirm the child's age in completed months from the caregiver or record.
        - Ask and report whether the child has cough or difficult breathing, diarrhoea, fever, or an ear problem.
        """,
        acquisitions=(
            ("danger_signs.vomits_everything", "CAREGIVER_QUESTION"),
            ("patient_facts.age_months", "HISTORY_OR_RECORD"),
            ("patient_facts.has_cough_or_difficult_breathing", "CAREGIVER_QUESTION"),
            ("patient_facts.has_diarrhoea", "CAREGIVER_QUESTION"),
            ("patient_facts.has_ear_problem", "CAREGIVER_QUESTION"),
            ("patient_facts.has_fever", "CAREGIVER_QUESTION"),
        ),
    ),
    "hpg-075-contradiction-drinking": _draft(
        """
        This child is 18 months old. The general danger-sign assessment recorded that the child is able to drink or breastfeed. The child does not vomit everything, has had no convulsions during this illness, is not lethargic or unconscious, and is not convulsing now. The child has had diarrhoea for 3 days with no blood in the stool. During the diarrhoea assessment, the child was recorded as unable to drink when offered fluid. The child is not restless, has no sunken eyes, and the skin pinch returns normally. There is no cough or difficult breathing, fever, or ear problem.
        """,
        """
        These findings conflict: the general danger-sign assessment says the child can drink or breastfeed, while the diarrhoea assessment records that the child is unable to drink. Do not choose one result or issue a final classification yet.

        Clinically reassess the child's ability to drink or breastfeed and the diarrhoea-specific drinking response, then record consistent findings in both relevant sections.
        """,
        acquisitions=(
            ("danger_signs.unable_to_drink_or_breastfeed", "CLINICIAN_OBSERVATION"),
            ("diarrhoea.dehydration.drinking_status", "CLINICIAN_OBSERVATION"),
        ),
        clarification_targets=(
            "danger_signs.unable_to_drink_or_breastfeed",
            "diarrhoea.dehydration.drinking_status",
        ),
    ),
    "hpg-077-out-of-scope-age-1": _draft(
        """
        This infant is 1 month old. There are no reported general danger signs, cough or difficult breathing, diarrhoea, fever, or ear problem.
        """,
        """
        This encounter is outside the supported EdgeIMCI major sick-child scope, which starts at 2 completed months and ends before 60 months. I cannot provide an IMCI classification or management synthesis from this workflow. Use the applicable approved young-infant assessment pathway.
        """,
    ),
}

_CLASSIFICATION_MARKERS = {
    "ACUTE_EAR_INFECTION": r"\bacute ear infection\b",
    "COUGH_OR_COLD": r"\bcough or cold\b",
    "DYSENTERY": r"\bdysentery\b",
    "FEVER_NO_MALARIA": r"\bfever[— -]+no malaria\b",
    "MALARIA": r"\bmalaria\b",
    "MASTOIDITIS": r"\bmastoiditis\b",
    "MEASLES": r"\bmeasles\b",
    "NO_DEHYDRATION": r"\bno dehydration\b",
    "PNEUMONIA": r"\bpneumonia\b",
    "SEVERE_COMPLICATED_MEASLES": r"\bsevere complicated measles\b",
    "SEVERE_DEHYDRATION": r"\bsevere dehydration\b",
    "SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE": r"\bsevere pneumonia or very severe disease\b",
    "SOME_DEHYDRATION": r"\bsome dehydration\b",
    "VERY_SEVERE_DISEASE": r"\bvery severe disease\b",
    "VERY_SEVERE_FEBRILE_DISEASE": r"\bvery severe febrile disease\b",
}

_ACTION_MARKERS = {
    "ADVISE_WHEN_TO_RETURN_IMMEDIATELY": r"\badvise\b.{0,40}\breturn immediately\b",
    "APPLY_TETRACYCLINE_EYE_OINTMENT": r"\bapply tetracycline eye ointment\b",
    "COMPLETE_ASSESSMENT_QUICKLY": r"\bcomplete\b.{0,30}\bassessment quickly\b",
    "DRY_EAR_BY_WICKING": r"\bdry the ear by wicking\b",
    "FOLLOW_UP_3_DAYS": r"\bfollow up in 3 days\b",
    "FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS": r"\bfollow up in 3 days if (?:the )?fever persists\b",
    "FOLLOW_UP_5_DAYS": r"\bfollow up in 5 days\b",
    "FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING": r"\bfollow up in 5 days if the child is not improving\b",
    "GIVE_ANTIBIOTIC_5_DAYS": r"\bgive\b.{0,35}\bantibiotic for 5 days\b",
    "GIVE_APPROPRIATE_ANTIBIOTIC_FOR_IDENTIFIED_BACTERIAL_CAUSE": r"\bappropriate antibiotic treatment\b.{0,80}\bidentified bacterial cause\b",
    "GIVE_CHOLERA_ANTIBIOTIC_PER_LOCAL_PROTOCOL": r"\bantibiotic for cholera\b.{0,60}\b(?:local|applicable) protocol\b",
    "GIVE_CIPROFLOXACIN_3_DAYS": r"\bgive ciprofloxacin for 3 days\b",
    "GIVE_DIAZEPAM_IF_CONVULSING_NOW": r"\bgive diazepam\b.{0,50}\bconvulsing now\b",
    "GIVE_FIRST_DOSE_AMOXICILLIN_AND_REFER": r"\bfirst dose of amoxicillin\b.{0,40}\brefer\b",
    "GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC": r"\bfirst dose of an appropriate antibiotic\b",
    "GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT": r"\bfirst dose of severe[- ]malaria treatment\b",
    "GIVE_FIRST_LINE_ORAL_ANTIMALARIAL": r"\bfirst-line oral antimalarial\b",
    "GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C": r"\bfluid for severe dehydration according to plan c\b",
    "GIVE_FLUID_ZINC_AND_FOOD_PLAN_A": r"\bplan a fluid, zinc, and food\b",
    "GIVE_FLUID_ZINC_AND_FOOD_PLAN_B": r"\bfluid, zinc, and food according to plan b\b",
    "GIVE_INHALED_BRONCHODILATOR_5_DAYS": r"\binhaled bronchodilator for 5 days\b",
    "GIVE_ORAL_AMOXICILLIN_5_DAYS": r"\boral amoxicillin for 5 days\b",
    "GIVE_PARACETAMOL_FOR_EAR_PAIN": r"\bgive paracetamol for ear pain\b",
    "GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY": r"\bpre-referral treatment immediately\b",
    "GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL": r"\bbronchodilator trial\b",
    "GIVE_VITAMIN_A_TREATMENT": r"\bgive vitamin a treatment\b",
    "KEEP_WARM": r"\bkeep the child warm\b",
    "PREVENT_LOW_BLOOD_SUGAR": r"\bprevent low blood sugar\b",
    "REASSESS_BREATHING_AFTER_BRONCHODILATOR": r"\bbreathing reassessment\b",
    "REASSESS_DEHYDRATION_AFTER_PLAN_B": r"\breassess and reclassify dehydration after plan b\b",
    "REASSESS_DEHYDRATION_AFTER_PLAN_C": r"\breassess and reclassify dehydration after plan c\b",
    "REFER_FOR_OXYGEN_SATURATION_BELOW_90": r"\brefer\b.{0,50}\boxygen saturation is below 90%",
    "SOOTHE_THROAT_AND_RELIEVE_COUGH": r"\bsoothe the throat and relieve the cough\b.{0,30}\bsafe remedy\b",
    "URGENT_REFERRAL": r"\barrange urgent referral\b",
}

_ACQUISITION_MARKERS = {
    "danger_signs.unable_to_drink_or_breastfeed": r"\bability to drink or breastfeed\b",
    "danger_signs.vomits_everything": r"\bvomits everything\b",
    "diarrhoea.dehydration.drinking_status": r"\bdiarrhoea-specific drinking response\b",
    "fever.malaria_risk": r"\bmalaria-risk category of the area\b",
    "patient_facts.age_months": r"\bage in completed months\b",
    "patient_facts.has_cough_or_difficult_breathing": r"\bcough or difficult breathing\b",
    "patient_facts.has_diarrhoea": r"\bdiarrhoea\b",
    "patient_facts.has_ear_problem": r"\bear problem\b",
    "patient_facts.has_fever": r"\bfever\b",
    "respiratory.respiratory_rate": r"\brespiratory rate\b.{0,60}\bone full minute\b|\bone full minute\b.{0,60}\brespiratory rate\b",
}


def missing_language_markers(record: dict[str, Any]) -> list[str]:
    """Return expected semantic concepts not explicitly visible in the response."""

    assistant = record["conversation"][1]["content"].lower()
    alignment = record["alignment"]
    missing: list[str] = []
    for classification in alignment["classifications_covered"]:
        if not re.search(_CLASSIFICATION_MARKERS[classification], assistant, re.DOTALL):
            missing.append(f"classification:{classification}")
    for action in alignment["actions_covered"]:
        if not re.search(_ACTION_MARKERS[action], assistant, re.DOTALL):
            missing.append(f"action:{action}")
    for request in alignment["acquisition_requests"]:
        observation_id = request["observation_id"]
        if not re.search(_ACQUISITION_MARKERS[observation_id], assistant, re.DOTALL):
            missing.append(f"acquisition:{observation_id}")
    if alignment["deferred_actions_acknowledged"] and not re.search(
        r"\broutine\b.{0,80}\b(?:follow-up|home-care)\b.{0,80}\b(?:delay|compete)\b",
        assistant,
        re.DOTALL,
    ):
        missing.append("deferred-actions:urgent-workflow")
    if alignment["contradictions_covered"] and "conflict" not in assistant:
        missing.append("contradiction:explicit")
    return missing


def _semantic_records() -> dict[str, dict[str, Any]]:
    actual_hash = hashlib.sha256(SEMANTIC_JSONL_PATH.read_bytes()).hexdigest()
    if actual_hash != SEMANTIC_CASES_SHA256:
        raise ValueError("frozen semantic suite hash does not match language calibration pin")
    return {item["golden_case_id"]: item for item in load_holistic_golden_suite()}


def load_language_approval() -> dict[str, Any]:
    artifact = json.loads(DEFAULT_APPROVAL_PATH.read_text(encoding="utf-8"))
    expected = {
        "approval_id": LANGUAGE_APPROVAL_ID,
        "status": "APPROVED_AND_FROZEN_FOR_HACKATHON_SCOPE",
        "calibration_id": LANGUAGE_CALIBRATION_ID,
        "reviewed_language_calibration_sha256": APPROVED_REVIEWED_LANGUAGE_SHA256,
        "semantic_suite_id": SUITE_ID,
        "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
        "approval_authority": "PROJECT_OWNER",
        "production_clinical_use_authorized": False,
        "qualified_phc_field_validation_completed": False,
    }
    for key, value in expected.items():
        if artifact.get(key) != value:
            raise ValueError(f"incorrect holistic golden language approval {key}")
    frozen_hash = artifact.get("frozen_language_calibration_sha256")
    if not isinstance(frozen_hash, str) or len(frozen_hash) != 64:
        raise ValueError("language approval must pin the frozen calibration hash")
    approval_basis = artifact.get("approval_basis", {})
    if approval_basis.get("independent_language_review_completed") is not True:
        raise ValueError("language approval must record the completed independent review")
    if approval_basis.get("independent_language_review_findings_remediated") != [
        "LGR-IR-001",
        "LGR-IR-002",
    ]:
        raise ValueError("language approval must record both independent-review remediations")
    if artifact.get("freeze_transformation") != {
        "conversation_content_changed": True,
        "semantic_alignment_changed": False,
        "changes": [
            "APPLY_INDEPENDENT_LANGUAGE_REMEDIATIONS_LGR_IR_001_AND_LGR_IR_002",
            "SET_RECORD_STATUS_FROZEN",
            "RECORD_PROJECT_OWNER_HACKATHON_APPROVAL",
            "PIN_APPROVAL_IN_MANIFEST",
            "AUTHORIZE_FULL_GOLDEN_LANGUAGE_AUTHORING_AND_PRODUCT_EVALUATION",
        ],
    }:
        raise ValueError("incorrect language calibration freeze transformation")
    if artifact.get("eligibility_authorized") != {
        "HOLISTIC_GENERATION": True,
        "PRODUCT_EVALUATION": True,
        "TEACHER_BAKEOFF": False,
        "TRAINING": False,
    }:
        raise ValueError("incorrect approved language calibration eligibility")
    return artifact


def _flatten_missing(missing: dict[str, list[str]]) -> list[str]:
    return sorted(field for fields in missing.values() for field in fields)


def _alignment(record: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    expected = record["expected"]
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
    classifications = [item["classification"] for item in evaluation["final_classifications"]]
    actions = evaluation["final_actions"] or evaluation["urgent_actions"]
    return {
        "expected_state": "COMPLETE" if evaluation["supported_encounter_complete"] else "INCOMPLETE",
        "supported_encounter_complete": evaluation["supported_encounter_complete"],
        "final_synthesis_authorized": evaluation["final_holistic_synthesis_authorized"],
        "urgent_action_required": evaluation["urgent_action_required"],
        "classifications_covered": classifications,
        "actions_covered": list(actions),
        "deferred_actions_acknowledged": list(evaluation["deferred_actions"]),
        "missing_elements_covered": _flatten_missing(evaluation["missing_elements"]),
        "contradictions_covered": list(evaluation["contradictions"]),
        "acquisition_requests": [
            {"observation_id": item[0], "acquisition_mode": item[1]}
            for item in draft["acquisitions"]
        ],
        "clarification_targets": list(draft["clarification_targets"]),
    }


def build_language_calibration() -> list[dict[str, Any]]:
    semantics = _semantic_records()
    records: list[dict[str, Any]] = []
    for golden_case_id, draft in CALIBRATION_DRAFTS.items():
        source = semantics[golden_case_id]
        records.append(
            {
                "record_schema_id": LANGUAGE_RECORD_SCHEMA_ID,
                "rendering_id": f"{golden_case_id}-language-v1",
                "golden_case_id": golden_case_id,
                "status": "FROZEN",
                "corpus_role": "HOLISTIC_GOLDEN_LANGUAGE_CALIBRATION",
                "semantic_source": {
                    "suite_id": SUITE_ID,
                    "semantic_cases_sha256": SEMANTIC_CASES_SHA256,
                    "golden_case_logic_signature": source["metadata"]["logic_signature"],
                },
                "conversation": [
                    {"role": "user", "content": draft["user"]},
                    {"role": "assistant", "content": draft["assistant"]},
                ],
                "alignment": _alignment(source, draft),
                "review": {
                    "semantic_faithfulness": "APPROVED_FOR_HACKATHON_SCOPE",
                    "interaction_quality": "APPROVED_FOR_HACKATHON_SCOPE",
                    "phc_suitability": "PROJECT_OWNER_APPROVED_FOR_HACKATHON_DEMO_NOT_FIELD_VALIDATED",
                    "reviewer": "PROJECT_OWNER",
                    "notes": "Approval is bounded to the hackathon language calibration and is not qualified PHC field validation.",
                },
            }
        )
    return records


def validate_language_record(record: dict[str, Any], semantic_record: dict[str, Any]) -> None:
    schema = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(record)
    if record["semantic_source"]["golden_case_logic_signature"] != semantic_record["metadata"]["logic_signature"]:
        raise ValueError("language record does not pin the golden case logic signature")
    expected_alignment = _alignment(semantic_record, CALIBRATION_DRAFTS[record["golden_case_id"]])
    if record["alignment"] != expected_alignment:
        raise ValueError("language alignment does not exactly match frozen semantics")
    assistant = record["conversation"][1]["content"]
    if "IMCI-MSC-" in assistant or any(action in assistant for action in record["alignment"]["actions_covered"]):
        raise ValueError("user-facing rendering leaks internal rule or action identifiers")
    alignment = record["alignment"]
    if alignment["expected_state"] == "INCOMPLETE" and not re.search(
        r"\bfinal classifications?\b|\bcomplete set of classifications\b",
        assistant.lower(),
    ):
        raise ValueError("incomplete rendering must explicitly withhold final classification")
    if alignment["urgent_action_required"] is True and not assistant.startswith("URGENT:"):
        raise ValueError("urgent rendering must lead with urgency")
    if alignment["expected_state"] == "SCHEMA_REJECTION" and "outside" not in assistant.lower():
        raise ValueError("schema rejection must state that the encounter is outside scope")
    missing_markers = missing_language_markers(record)
    if missing_markers:
        raise ValueError(f"language rendering omits semantic concepts: {missing_markers}")
    missing = set(alignment["missing_elements_covered"])
    requested = {item["observation_id"] for item in alignment["acquisition_requests"]}
    if alignment["clarification_targets"]:
        if requested != set(alignment["clarification_targets"]):
            raise ValueError("contradiction clarification targets and acquisitions must match")
    elif requested != missing:
        raise ValueError("incomplete acquisition requests must exactly cover missing elements")


def load_language_calibration(*, corpus_use: CorpusUse = CorpusUse.DOMAIN_REVIEW) -> list[dict[str, Any]]:
    assert_corpus_use_allowed(DEFAULT_CALIBRATION_PATH, corpus_use, manifest_path=DEFAULT_MANIFEST_PATH)
    records = [
        json.loads(line)
        for line in DEFAULT_CALIBRATION_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]
    semantics = _semantic_records()
    for record in records:
        validate_language_record(record, semantics[record["golden_case_id"]])
    return records


def _manifest(records: list[dict[str, Any]], content_hash: str) -> dict[str, Any]:
    return {
        "suite_id": LANGUAGE_CALIBRATION_ID,
        "lifecycle_status": "FROZEN",
        "corpus_role": "HOLISTIC_GOLDEN_LANGUAGE_CALIBRATION",
        "assets": [
            str(DEFAULT_CALIBRATION_PATH.relative_to(ROOT)),
            str(DEFAULT_CALIBRATION_YAML_PATH.relative_to(ROOT)),
        ],
        "case_count": len(records),
        "semantic_source": {
            "suite_id": SUITE_ID,
            "path": str(SEMANTIC_JSONL_PATH.relative_to(ROOT)),
            "sha256": SEMANTIC_CASES_SHA256,
        },
        "artifact_pins": {
            "record_schema_id": LANGUAGE_RECORD_SCHEMA_ID,
            "builder_id": LANGUAGE_BUILDER_ID,
            "approval_id": LANGUAGE_APPROVAL_ID,
        },
        "language_calibration_sha256": content_hash,
        "review_status": "PROJECT_OWNER_APPROVED_FOR_HACKATHON_SCOPE",
        "approval": {
            "approval_id": LANGUAGE_APPROVAL_ID,
            "reviewed_language_calibration_sha256": APPROVED_REVIEWED_LANGUAGE_SHA256,
            "frozen_language_calibration_sha256": content_hash,
            "qualified_phc_field_validation_completed": False,
        },
        "technical_editorial_review": {
            "record": "docs/product_holistic_golden_language_technical_review_v1.md",
            "status": "PASS_TECHNICAL_ALIGNMENT_READY_FOR_HUMAN_LANGUAGE_REVIEW",
            "same_agent_review": True,
            "reviewed_language_calibration_sha256": APPROVED_REVIEWED_LANGUAGE_SHA256,
        },
        "independent_language_review": {
            "record": "docs/product_holistic_golden_language_independent_review_v1.md",
            "status": "READY_AFTER_LANGUAGE_REMEDIATION",
            "reviewed_language_calibration_sha256": APPROVED_REVIEWED_LANGUAGE_SHA256,
            "remediated_findings": ["LGR-IR-001", "LGR-IR-002"],
            "qualified_phc_field_validation": False,
        },
        "eligibility": {
            "DOMAIN_REVIEW": True,
            "COMPONENT_VALIDATION": True,
            "HOLISTIC_GENERATION": True,
            "PRODUCT_EVALUATION": True,
            "TEACHER_BAKEOFF": False,
            "TRAINING": False,
        },
        "production_clinical_use_authorized": False,
    }


def render_language_calibration_review(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Product holistic golden language calibration v1 — review package",
        "",
        "> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Review surface for the project-owner-approved and frozen hackathon language calibration.",
        "",
        f"**Status:** 16 calibration renderings approved and frozen for the bounded hackathon scope, pinned to semantic SHA-256 `{SEMANTIC_CASES_SHA256}`.",
        "",
        "These are approved style anchors for completing the 78-case golden language layer. They are not training data, production clinical authorization, or qualified PHC field validation.",
        "",
    ]
    for record in records:
        alignment = record["alignment"]
        classifications = ", ".join(alignment["classifications_covered"]) or "none"
        actions = ", ".join(alignment["actions_covered"]) or "none"
        deferred = ", ".join(alignment["deferred_actions_acknowledged"]) or "none"
        missing = ", ".join(alignment["missing_elements_covered"]) or "none"
        contradictions = "; ".join(alignment["contradictions_covered"]) or "none"
        acquisitions = (
            "; ".join(
                f"{item['observation_id']} via {item['acquisition_mode']}"
                for item in alignment["acquisition_requests"]
            )
            or "none"
        )
        lines.extend(
            [
                f"## {record['golden_case_id']}",
                "",
                f"**State:** `{alignment['expected_state']}` · **Urgent:** `{alignment['urgent_action_required']}`",
                "",
                "### Frozen semantic target",
                "",
                f"- Final classifications: {classifications}",
                f"- Immediate/final actions: {actions}",
                f"- Deferred actions: {deferred}",
                f"- Missing elements: {missing}",
                f"- Contradictions: {contradictions}",
                f"- Acquisition requests: {acquisitions}",
                "",
                "### PHC-worker submission",
                "",
                record["conversation"][0]["content"],
                "",
                "### Proposed EdgeIMCI response",
                "",
                record["conversation"][1]["content"],
                "",
                "### Approval disposition",
                "",
                "- Semantic faithfulness: `APPROVED_FOR_HACKATHON_SCOPE`",
                "- Interaction quality: `APPROVED_FOR_HACKATHON_SCOPE`",
                "- PHC suitability: `PROJECT_OWNER_APPROVED_FOR_HACKATHON_DEMO_NOT_FIELD_VALIDATED`",
                "- Reviewer: `PROJECT_OWNER`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_language_calibration() -> list[dict[str, Any]]:
    approval = load_language_approval()
    records = build_language_calibration()
    semantics = _semantic_records()
    for record in records:
        validate_language_record(record, semantics[record["golden_case_id"]])
    content = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    if content_hash != approval["frozen_language_calibration_sha256"]:
        raise ValueError("generated frozen language calibration does not match approved hash")
    DEFAULT_CALIBRATION_PATH.write_text(content, encoding="utf-8")
    DEFAULT_CALIBRATION_YAML_PATH.write_text(
        "# Generated from the canonical JSONL; do not edit this mirror.\n"
        + yaml.safe_dump(records, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    DEFAULT_MANIFEST_PATH.write_text(
        json.dumps(_manifest(records, content_hash), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    DEFAULT_APPROVAL_YAML_PATH.write_text(
        "# Generated from the canonical JSON; do not edit this mirror.\n"
        + yaml.safe_dump(approval, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    DEFAULT_REVIEW_PATH.write_text(render_language_calibration_review(records), encoding="utf-8")
    return records
