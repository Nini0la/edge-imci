"""Deterministic presentation adapters.

These functions render the existing deterministic evaluator output into
worker-facing text and decision-trace evidence. They do NOT call any LLM and
do NOT invent clinical policy. They are thin presentation adapters over
existing trace data.

Human-readable mappings for classifications and actions are derived from the
frozen golden language renderings — the same text a PHC worker would see.
"""

from __future__ import annotations

from typing import Any

from edge_imci.generation.holistic_language_full import (
    ACQUISITION_SPECS,
    render_assistant,
)
from edge_imci.schemas.holistic import (
    HolisticEncounter,
    HolisticEvaluationResult,
)

from app.service.result import PipelineStep, TraceEntry


# --- Human-readable mappings (derived from frozen golden language) ---

_CLASSIFICATION_LABELS: dict[str, str] = {
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
    "FEVER_NO_MALARIA": "Fever — no malaria",
    "FEVER": "Fever",
    "SEVERE_COMPLICATED_MEASLES": "Severe complicated measles",
    "MEASLES_WITH_EYE_OR_MOUTH_COMPLICATIONS": "Measles with eye or mouth complications",
    "MEASLES": "Measles",
    "MASTOIDITIS": "Mastoiditis",
    "ACUTE_EAR_INFECTION": "Acute ear infection",
    "CHRONIC_EAR_INFECTION": "Chronic ear infection",
    "NO_EAR_INFECTION": "No ear infection",
}

_ACTION_LABELS: dict[str, str] = {
    "COMPLETE_ASSESSMENT_QUICKLY": "Complete the remaining assessment quickly.",
    "GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY": "Give the indicated pre-referral treatment immediately.",
    "PREVENT_LOW_BLOOD_SUGAR": "Prevent low blood sugar.",
    "KEEP_WARM": "Keep the child warm.",
    "URGENT_REFERRAL": "Arrange urgent referral.",
    "REFER_TO_HOSPITAL": "Refer the child to hospital.",
    "GIVE_DIAZEPAM_IF_CONVULSING_NOW": "Give diazepam because the child is convulsing now.",
    "GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC": "Give the first dose of an appropriate antibiotic.",
    "GIVE_ORAL_AMOXICILLIN_5_DAYS": "Give oral amoxicillin for 5 days.",
    "GIVE_FIRST_DOSE_AMOXICILLIN_AND_REFER": "Give the first dose of amoxicillin, then refer the child.",
    "GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL": "Give a rapid-acting inhaled bronchodilator trial.",
    "REASSESS_BREATHING_AFTER_BRONCHODILATOR": "Reassess breathing after the bronchodilator trial.",
    "GIVE_INHALED_BRONCHODILATOR_5_DAYS": "Give an inhaled bronchodilator for 5 days.",
    "REFER_FOR_TB_OR_ASTHMA_ASSESSMENT": "Refer for TB or asthma assessment.",
    "REFER_FOR_OXYGEN_SATURATION_BELOW_90": "Refer the child because the oxygen saturation is below 90%.",
    "SOOTHE_THROAT_AND_RELIEVE_COUGH": "Soothe the throat and relieve the cough with a safe remedy.",
    "ADVISE_WHEN_TO_RETURN_IMMEDIATELY": "Advise the caregiver when to return immediately.",
    "FOLLOW_UP_2_DAYS_IF_FEVER_PERSISTS": "Follow up in 2 days if the fever persists.",
    "FOLLOW_UP_3_DAYS": "Follow up in 3 days.",
    "FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS": "Follow up in 3 days if the fever persists.",
    "FOLLOW_UP_5_DAYS": "Follow up in 5 days.",
    "FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING": "Follow up in 5 days if the child is not improving.",
    "GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C": "Give fluid for severe dehydration (Plan C).",
    "GIVE_FLUID_ZINC_AND_FOOD_PLAN_B": "Give fluid, zinc, and food according to Plan B.",
    "GIVE_FLUID_ZINC_AND_FOOD_PLAN_A": "Give fluid, zinc, and food according to Plan A.",
    "FREQUENT_ORS_SIPS_DURING_REFERRAL": "Give frequent ORS sips during referral.",
    "CONTINUE_BREASTFEEDING": "Continue breastfeeding.",
    "TREAT_DEHYDRATION_BEFORE_REFERRAL": "Treat dehydration before referral.",
    "ADVISE_FEEDING_FOR_PERSISTENT_DIARRHOEA": "Advise feeding for persistent diarrhoea.",
    "GIVE_MULTIVITAMINS_MINERALS_ZINC_14_DAYS": "Give multivitamins, minerals, and zinc for 14 days.",
    "GIVE_CIPROFLOXACIN_3_DAYS": "Give ciprofloxacin for 3 days.",
    "GIVE_CHOLERA_ANTIBIOTIC_PER_LOCAL_PROTOCOL": "Give cholera antibiotic per local protocol.",
    "REASSESS_DEHYDRATION_AFTER_PLAN_B": "Reassess dehydration after Plan B.",
    "REASSESS_DEHYDRATION_AFTER_PLAN_C": "Reassess dehydration after Plan C.",
    "GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT": "Give the first dose of severe malaria treatment.",
    "GIVE_FIRST_LINE_ORAL_ANTIMALARIAL": "Give the first-line oral antimalarial.",
    "GIVE_PARACETAMOL_FOR_HIGH_FEVER": "Give paracetamol for high fever.",
    "GIVE_PARACETAMOL_FOR_EAR_PAIN": "Give paracetamol for ear pain.",
    "GIVE_APPROPRIATE_ANTIBIOTIC_FOR_IDENTIFIED_BACTERIAL_CAUSE": "Give the appropriate antibiotic for the identified bacterial cause.",
    "REFER_PROLONGED_FEVER_FOR_ASSESSMENT": "Refer for assessment of prolonged fever.",
    "GIVE_VITAMIN_A_TREATMENT": "Give vitamin A treatment.",
    "APPLY_TETRACYCLINE_EYE_OINTMENT": "Apply tetracycline eye ointment.",
    "TREAT_MOUTH_ULCERS_WITH_GENTIAN_VIOLET": "Treat mouth ulcers with gentian violet.",
    "GIVE_ANTIBIOTIC_5_DAYS": "Give the indicated antibiotic for 5 days.",
    "DRY_EAR_BY_WICKING": "Dry the ear by wicking.",
    "GIVE_TOPICAL_QUINOLONE_EARDROPS_14_DAYS": "Give topical quinolone eardrops for 14 days.",
    "NO_EAR_TREATMENT": "No ear treatment is indicated.",
}

# --- Rule descriptions (from the frozen rule set, human-readable) ---

_RULE_DESCRIPTIONS: dict[str, str] = {
    "IMCI-MSC-GDS-UNABLE-TO-DRINK": "Child is unable to drink or breastfeed — general danger sign.",
    "IMCI-MSC-GDS-VOMITS-EVERYTHING": "Child vomits everything — general danger sign.",
    "IMCI-MSC-GDS-CONVULSIONS-HISTORY": "Child has had convulsions during this illness — general danger sign.",
    "IMCI-MSC-GDS-LETHARGIC-OR-UNCONSCIOUS": "Child is lethargic or unconscious — general danger sign.",
    "IMCI-MSC-GDS-CONVULSING-NOW": "Child is convulsing now — general danger sign requiring immediate action.",
    "IMCI-MSC-RESP-FAST-BREATHING-2-12M": "Fast breathing threshold for age 2–11 months (≥50/min).",
    "IMCI-MSC-RESP-FAST-BREATHING-12-60M": "Fast breathing threshold for age 12–59 months (≥40/min).",
    "IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING": "Pneumonia classification — fast breathing present, no severe sign.",
    "IMCI-MSC-RESP-PNEUMONIA-CHEST-INDRAWING": "Pneumonia classification — chest indrawing present, no severe sign.",
    "IMCI-MSC-RESP-HIV-CHEST-INDRAWING": "Chest indrawing with HIV exposure — pneumonia classification, referral required.",
    "IMCI-MSC-RESP-SEVERE-DANGER-SIGN": "Severe pneumonia or very severe disease — danger sign present with respiratory complaint.",
    "IMCI-MSC-RESP-SEVERE-STRIDOR": "Stridor when calm — severe pneumonia or very severe disease.",
    "IMCI-MSC-RESP-WHEEZE-BRONCHODILATOR-REASSESS": "Wheezing with fast breathing or chest indrawing requires bronchodilator trial and reassessment.",
    "IMCI-MSC-RESP-WHEEZE-HOME-TREATMENT": "Wheezing resolved after bronchodilator — home treatment with inhaled bronchodilator.",
    "IMCI-MSC-RESP-COUGH-OR-COLD": "Cough or cold — no fast breathing, no chest indrawing, no stridor.",
    "IMCI-MSC-RESP-PROLONGED-OR-RECURRENT": "Cough lasting more than 30 days or recurrent wheeze — refer for TB or asthma assessment.",
    "IMCI-MSC-RESP-OXYGEN-SATURATION": "Oxygen saturation below 90% — referral required.",
    "IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION": "Severe dehydration classification — two or more severe signs.",
    "IMCI-MSC-DIARRHOEA-SOME-DEHYDRATION": "Some dehydration classification — two or more signs, less severe.",
    "IMCI-MSC-DIARRHOEA-NO-DEHYDRATION": "No dehydration — fewer than two dehydration signs.",
    "IMCI-MSC-DIARRHOEA-DYSENTERY": "Blood in stool — dysentery classification.",
    "IMCI-MSC-DIARRHOEA-PERSISTENT": "Diarrhoea lasting 14 days or more — persistent diarrhoea.",
    "IMCI-MSC-DIARRHOEA-SEVERE-PERSISTENT": "Persistent diarrhoea with severe dehydration — severe persistent diarrhoea.",
    "IMCI-MSC-DIARRHOEA-CHOLERA-CONTEXT": "Cholera context confirmed — cholera antibiotic indicated.",
    "IMCI-MSC-FEVER-VERY-SEVERE": "Stiff neck or very severe febrile disease classification.",
    "IMCI-MSC-FEVER-MALARIA": "Malaria classification — malaria risk with positive test or no test in high-risk area.",
    "IMCI-MSC-FEVER-NO-MALARIA": "Fever, no malaria — malaria risk present but test negative.",
    "IMCI-MSC-FEVER-NO-MALARIA-RISK": "No malaria risk — fever classification.",
    "IMCI-MSC-FEVER-HIGH-TEMPERATURE": "High fever (≥38.5°C) — give paracetamol.",
    "IMCI-MSC-FEVER-PROLONGED": "Fever lasting 7 days or more — refer for prolonged fever assessment.",
    "IMCI-MSC-FEVER-IDENTIFIED-BACTERIAL-CAUSE": "Identified bacterial cause — give appropriate antibiotic.",
    "IMCI-MSC-MEASLES-SEVERE-COMPLICATED": "Severe complicated measles — urgent referral required.",
    "IMCI-MSC-MEASLES-EYE-OR-MOUTH-COMPLICATIONS": "Measles with eye or mouth complications.",
    "IMCI-MSC-MEASLES": "Measles classification — generalized rash with cough, red eyes, or mouth ulcers.",
    "IMCI-MSC-EAR-MASTOIDITIS": "Tender swelling behind the ear — mastoiditis, urgent referral.",
    "IMCI-MSC-EAR-ACUTE-INFECTION": "Ear pain or discharge for less than 14 days — acute ear infection.",
    "IMCI-MSC-EAR-CHRONIC-INFECTION": "Ear discharge for 14 days or more — chronic ear infection.",
    "IMCI-MSC-EAR-NO-INFECTION": "No ear pain, no discharge, no swelling — no ear infection.",
}

# --- Pathway display names ---

_PATHWAY_LABELS: dict[str, str] = {
    "supported_encounter": "Supported encounter",
    "general_danger_signs": "General danger signs",
    "respiratory": "Respiratory",
    "diarrhoea": "Diarrhoea",
    "fever": "Fever",
    "ear_problem": "Ear problem",
}

# --- Field display names for structured encounter view ---

_FIELD_LABELS: list[tuple[str, str, Any]] = [
    # (path, display_label, formatter)
    (
        "patient_facts.age_months",
        "Age",
        lambda v: f"{v} months" if v is not None else "Unknown",
    ),
    (
        "patient_facts.has_cough_or_difficult_breathing",
        "Cough / difficult breathing",
        lambda v: _bool_label(v),
    ),
    ("patient_facts.has_diarrhoea", "Diarrhoea", lambda v: _bool_label(v)),
    ("patient_facts.has_fever", "Fever", lambda v: _bool_label(v)),
    ("patient_facts.has_ear_problem", "Ear problem", lambda v: _bool_label(v)),
    (
        "danger_signs.unable_to_drink_or_breastfeed",
        "Unable to drink or breastfeed",
        lambda v: _bool_label(v),
    ),
    ("danger_signs.vomits_everything", "Vomits everything", lambda v: _bool_label(v)),
    ("danger_signs.had_convulsions", "Had convulsions", lambda v: _bool_label(v)),
    (
        "danger_signs.lethargic_or_unconscious",
        "Lethargic or unconscious",
        lambda v: _bool_label(v),
    ),
    ("danger_signs.convulsing_now", "Convulsing now", lambda v: _bool_label(v)),
    (
        "respiratory.cough_duration_days",
        "Cough duration",
        lambda v: f"{v} days" if v is not None else "Unknown",
    ),
    (
        "respiratory.respiratory_rate",
        "Respiratory rate",
        lambda v: f"{v}/min" if v is not None else "Unknown",
    ),
    (
        "respiratory.chest_indrawing",
        "Chest indrawing",
        lambda v: _bool_label(v, present_absent=True),
    ),
    (
        "respiratory.stridor_when_calm",
        "Stridor when calm",
        lambda v: _bool_label(v, present_absent=True),
    ),
    ("respiratory.wheezing", "Wheezing", lambda v: _bool_label(v, present_absent=True)),
    (
        "respiratory.recurrent_wheeze",
        "Recurrent wheeze",
        lambda v: _bool_label(v, present_absent=True),
    ),
    ("respiratory.child_calm", "Child calm", lambda v: _bool_label(v)),
    (
        "respiratory.breaths_counted_one_minute",
        "Breaths counted for one minute",
        lambda v: _bool_label(v),
    ),
    (
        "respiratory.pulse_oximeter_available",
        "Pulse oximeter available",
        lambda v: _bool_label(v),
    ),
    (
        "respiratory.oxygen_saturation_percent",
        "Oxygen saturation",
        lambda v: f"{v}%" if v is not None else "Unknown",
    ),
    (
        "respiratory.hiv_exposed_or_infected",
        "HIV exposed or infected",
        lambda v: _bool_label(v),
    ),
    (
        "respiratory.bronchodilator_trial_completed",
        "Bronchodilator trial completed",
        lambda v: _bool_label(v),
    ),
    (
        "respiratory.post_bronchodilator_respiratory_rate",
        "Post-bronchodilator RR",
        lambda v: f"{v}/min" if v is not None else "Unknown",
    ),
    (
        "respiratory.post_bronchodilator_chest_indrawing",
        "Post-bronchodilator chest indrawing",
        lambda v: _bool_label(v, present_absent=True),
    ),
    (
        "respiratory.post_bronchodilator_child_calm",
        "Post-bronchodilator child calm",
        lambda v: _bool_label(v),
    ),
    (
        "respiratory.post_bronchodilator_breaths_counted_one_minute",
        "Post-bronchodilator breaths counted",
        lambda v: _bool_label(v),
    ),
    (
        "diarrhoea.duration_days",
        "Diarrhoea duration",
        lambda v: f"{v} days" if v is not None else "Unknown",
    ),
    (
        "diarrhoea.blood_in_stool",
        "Blood in stool",
        lambda v: _bool_label(v, present_absent=True),
    ),
    (
        "diarrhoea.dehydration.restless_or_irritable",
        "Restless or irritable",
        lambda v: _bool_label(v),
    ),
    (
        "diarrhoea.dehydration.sunken_eyes",
        "Sunken eyes",
        lambda v: _bool_label(v, present_absent=True),
    ),
    (
        "diarrhoea.dehydration.drinking_status",
        "Drinking status",
        lambda v: v.replace("_", " ").lower() if v else "Unknown",
    ),
    (
        "diarrhoea.dehydration.skin_pinch",
        "Skin pinch",
        lambda v: v.replace("_", " ").lower() if v else "Unknown",
    ),
    ("diarrhoea.cholera_in_area", "Cholera in area", lambda v: _bool_label(v)),
    (
        "fever.temperature_c",
        "Temperature",
        lambda v: f"{v}°C" if v is not None else "Unknown",
    ),
    (
        "fever.malaria_risk",
        "Malaria risk",
        lambda v: v.replace("_", " ").lower() if v else "Unknown",
    ),
    (
        "fever.fever_duration_days",
        "Fever duration",
        lambda v: f"{v} days" if v is not None else "Unknown",
    ),
    ("fever.fever_present_every_day", "Fever every day", lambda v: _bool_label(v)),
    ("fever.stiff_neck", "Stiff neck", lambda v: _bool_label(v, present_absent=True)),
    ("fever.runny_nose", "Runny nose", lambda v: _bool_label(v, present_absent=True)),
    (
        "fever.obvious_cause_of_fever_present",
        "Obvious cause of fever",
        lambda v: _bool_label(v),
    ),
    (
        "fever.identified_bacterial_cause_present",
        "Identified bacterial cause",
        lambda v: _bool_label(v),
    ),
    (
        "fever.malaria_test_available",
        "Malaria test available",
        lambda v: _bool_label(v),
    ),
    (
        "fever.malaria_test_result",
        "Malaria test result",
        lambda v: v.lower() if v else "Unknown",
    ),
    (
        "fever.measles_within_last_3_months",
        "Measles in last 3 months",
        lambda v: _bool_label(v),
    ),
    (
        "fever.generalized_rash",
        "Generalized rash",
        lambda v: _bool_label(v, present_absent=True),
    ),
    ("fever.measles_cough", "Measles cough", lambda v: _bool_label(v)),
    ("fever.red_eyes", "Red eyes", lambda v: _bool_label(v, present_absent=True)),
    (
        "fever.mouth_ulcers",
        "Mouth ulcers",
        lambda v: _bool_label(v, present_absent=True),
    ),
    (
        "fever.pus_draining_from_eye",
        "Pus draining from eye",
        lambda v: _bool_label(v, present_absent=True),
    ),
    (
        "fever.clouding_of_cornea",
        "Clouding of cornea",
        lambda v: _bool_label(v, present_absent=True),
    ),
    ("ear.ear_pain", "Ear pain", lambda v: _bool_label(v, present_absent=True)),
    ("ear.ear_discharge_reported", "Ear discharge reported", lambda v: _bool_label(v)),
    (
        "ear.ear_discharge_duration_days",
        "Ear discharge duration",
        lambda v: f"{v} days" if v is not None else "Unknown",
    ),
    (
        "ear.pus_draining_from_ear",
        "Pus draining from ear",
        lambda v: _bool_label(v, present_absent=True),
    ),
    (
        "ear.tender_swelling_behind_ear",
        "Tender swelling behind ear",
        lambda v: _bool_label(v, present_absent=True),
    ),
]


def _bool_label(v: Any, *, present_absent: bool = False) -> str:
    if v is None:
        return "Unknown"
    if present_absent:
        return "Present" if v else "Absent"
    return "Yes" if v else "No"


def humanize_classification(value: str) -> str:
    return _CLASSIFICATION_LABELS.get(value, value.replace("_", " ").lower())


def humanize_action(value: str) -> str:
    return _ACTION_LABELS.get(value, value.replace("_", " ").lower())


def humanize_missing_element(field_path: str) -> str:
    """Convert an internal field path to a human-readable assessment item."""
    # Map known field paths to natural descriptions
    _MISSING_LABELS = {
        "patient_facts.age_months": "Child's age",
        "patient_facts.has_cough_or_difficult_breathing": "Whether the child has cough or difficult breathing",
        "patient_facts.has_diarrhoea": "Whether the child has diarrhoea",
        "patient_facts.has_fever": "Whether the child has fever",
        "patient_facts.has_ear_problem": "Whether the child has an ear problem",
        "danger_signs.unable_to_drink_or_breastfeed": "Whether the child is unable to drink or breastfeed",
        "danger_signs.vomits_everything": "Whether the child vomits everything",
        "danger_signs.had_convulsions": "Whether the child has had convulsions",
        "danger_signs.lethargic_or_unconscious": "Whether the child is lethargic or unconscious",
        "danger_signs.convulsing_now": "Whether the child is convulsing now",
    }
    if field_path in _MISSING_LABELS:
        return _MISSING_LABELS[field_path]
    for path, label, _ in _FIELD_LABELS:
        if path == field_path:
            return label
    return field_path.split(".")[-1].replace("_", " ")


def _render_runtime_incomplete(eval_result: HolisticEvaluationResult) -> str:
    """Render incomplete runtime states beyond the frozen golden field slices."""

    blocks: list[str] = []
    if eval_result.urgent_action_required:
        blocks.append("URGENT: Act now and do not delay referral.")
        if eval_result.urgent_actions:
            blocks.append(
                "Immediate management:\n"
                + "\n".join(
                    f"- {humanize_action(action.value)}"
                    for action in eval_result.urgent_actions
                )
            )

    blocks.append("ASSESSMENT INCOMPLETE")
    if eval_result.contradictions:
        blocks.append(
            "Conflicting or invalid findings:\n"
            + "\n".join(f"- {item}." for item in eval_result.contradictions)
        )

    requests: list[str] = []
    for fields in eval_result.missing_elements.values():
        for field in fields:
            approved = ACQUISITION_SPECS.get(field)
            if approved:
                requests.append(approved[1])
            else:
                requests.append(f"Confirm {humanize_missing_element(field).lower()}.")
    if requests:
        heading = (
            "Information still needed:"
            if eval_result.urgent_action_required
            else "Information needed:"
        )
        blocks.append(heading + "\n" + "\n".join(f"- {item}" for item in requests))

    if eval_result.urgent_action_required:
        blocks.append(
            "Complete these checks rapidly, but do not delay referral. The final holistic "
            "classifications and complete management plan remain pending."
        )
    else:
        blocks.append(
            "I cannot provide the final classifications and complete management plan until "
            "these findings are supplied."
        )
    return "\n\n".join(blocks)


def render_worker_response(
    eval_result: HolisticEvaluationResult,
    model_target: dict[str, Any],
) -> str:
    """Render with the approved deterministic response grammar."""

    semantic_record = {
        "input": {"kind": "HOLISTIC_ENCOUNTER", "encounter": model_target},
        "expected": {
            "kind": "HOLISTIC_EVALUATION",
            "evaluation": eval_result.to_dict(),
        },
    }
    missing = {
        field
        for fields in eval_result.missing_elements.values()
        for field in fields
    }
    if not eval_result.supported_encounter_complete and not missing.issubset(
        ACQUISITION_SPECS
    ):
        return _render_runtime_incomplete(eval_result)
    return render_assistant(semantic_record)


def build_decision_trace(
    eval_result: HolisticEvaluationResult,
    encounter: HolisticEncounter,
) -> list[TraceEntry]:
    """Build the 'Why EdgeIMCI reached this result' trace from deterministic evidence.

    Each entry shows the classification, the pathway, the structured findings
    that triggered it, and a human-readable rule description. No LLM is involved.
    """

    traces: list[TraceEntry] = []

    for ct in eval_result.final_classifications:
        pathway_label = _PATHWAY_LABELS.get(ct.pathway.value, ct.pathway.value)
        rule_desc = _RULE_DESCRIPTIONS.get(
            ct.rule_id, f"Deterministic rule: {ct.rule_id}"
        )

        # Gather relevant findings for this classification
        findings = _gather_findings_for_classification(ct, encounter)

        traces.append(
            TraceEntry(
                classification=humanize_classification(ct.classification.value),
                pathway=pathway_label,
                findings=findings,
                rule_description=rule_desc,
                rule_id=ct.rule_id,
            )
        )

    # For incomplete encounters, add a synthesis-withheld entry
    if not eval_result.supported_encounter_complete:
        missing_findings: list[tuple[str, str]] = []
        for pathway, fields in eval_result.missing_elements.items():
            pathway_label = _PATHWAY_LABELS.get(pathway.value, pathway.value)
            for field in fields:
                missing_findings.append((humanize_missing_element(field), "UNKNOWN"))

        if eval_result.contradictions:
            for c in eval_result.contradictions:
                missing_findings.append((c, "CONFLICT"))

        traces.append(
            TraceEntry(
                classification="Final holistic classification withheld",
                pathway="Completeness check",
                findings=tuple(missing_findings),
                rule_description="Required supported assessment element is unresolved or conflicting. Completeness check: FAILED.",
                rule_id="COMPLETENESS_GATE",
            )
        )

    return traces


def _gather_findings_for_classification(
    ct: Any,
    encounter: HolisticEncounter,
) -> tuple[tuple[str, str], ...]:
    """Gather the structured findings relevant to a specific classification."""

    findings: list[tuple[str, str]] = []
    facts = encounter.patient_facts

    if ct.pathway.value == "general_danger_signs":
        ds = encounter.danger_signs
        if ds.convulsing_now is True:
            findings.append(("Convulsing now", "Yes"))
        if ds.unable_to_drink_or_breastfeed is True:
            findings.append(("Unable to drink or breastfeed", "Yes"))
        if ds.vomits_everything is True:
            findings.append(("Vomits everything", "Yes"))
        if ds.had_convulsions is True:
            findings.append(("Had convulsions", "Yes"))
        if ds.lethargic_or_unconscious is True:
            findings.append(("Lethargic or unconscious", "Yes"))

    elif ct.pathway.value == "respiratory":
        obs = encounter.respiratory
        if obs:
            if facts.age_months is not None:
                findings.append(("Age", f"{facts.age_months} months"))
            if obs.respiratory_rate is not None:
                findings.append(("Respiratory rate", f"{obs.respiratory_rate}/min"))
            if obs.chest_indrawing is not None:
                findings.append(
                    ("Chest indrawing", "Present" if obs.chest_indrawing else "Absent")
                )
            if obs.stridor_when_calm is not None:
                findings.append(
                    (
                        "Stridor when calm",
                        "Present" if obs.stridor_when_calm else "Absent",
                    )
                )
            if obs.child_calm is not None:
                findings.append(("Child calm", "Yes" if obs.child_calm else "No"))
            if obs.breaths_counted_one_minute is not None:
                findings.append(
                    (
                        "Breaths counted for one minute",
                        "Yes" if obs.breaths_counted_one_minute else "No",
                    )
                )
            if obs.wheezing is not None:
                findings.append(("Wheezing", "Present" if obs.wheezing else "Absent"))
            if obs.oxygen_saturation_percent is not None:
                findings.append(
                    ("Oxygen saturation", f"{obs.oxygen_saturation_percent}%")
                )

    elif ct.pathway.value == "diarrhoea":
        obs = encounter.diarrhoea
        if obs:
            if obs.duration_days is not None:
                findings.append(("Diarrhoea duration", f"{obs.duration_days} days"))
            if obs.blood_in_stool is not None:
                findings.append(
                    ("Blood in stool", "Present" if obs.blood_in_stool else "Absent")
                )
            if obs.dehydration.drinking_status is not None:
                findings.append(
                    ("Drinking status", obs.dehydration.drinking_status.value)
                )
            if obs.dehydration.skin_pinch is not None:
                findings.append(("Skin pinch", obs.dehydration.skin_pinch.value))
            if obs.dehydration.sunken_eyes is not None:
                findings.append(
                    (
                        "Sunken eyes",
                        "Present" if obs.dehydration.sunken_eyes else "Absent",
                    )
                )
            if obs.dehydration.restless_or_irritable is not None:
                findings.append(
                    (
                        "Restless or irritable",
                        "Yes" if obs.dehydration.restless_or_irritable else "No",
                    )
                )

    elif ct.pathway.value == "fever":
        obs = encounter.fever
        if obs:
            if obs.temperature_c is not None:
                findings.append(("Temperature", f"{obs.temperature_c}°C"))
            if obs.malaria_risk is not None:
                findings.append(
                    ("Malaria risk", obs.malaria_risk.value.replace("_", " ").lower())
                )
            if obs.malaria_test_result is not None:
                findings.append(
                    ("Malaria test result", obs.malaria_test_result.value.lower())
                )
            if obs.fever_duration_days is not None:
                findings.append(("Fever duration", f"{obs.fever_duration_days} days"))
            if obs.stiff_neck is not None:
                findings.append(
                    ("Stiff neck", "Present" if obs.stiff_neck else "Absent")
                )
            if obs.generalized_rash is not None:
                findings.append(
                    (
                        "Generalized rash",
                        "Present" if obs.generalized_rash else "Absent",
                    )
                )
            if obs.measles_cough is not None:
                findings.append(("Measles cough", "Yes" if obs.measles_cough else "No"))

    elif ct.pathway.value == "ear_problem":
        obs = encounter.ear
        if obs:
            if obs.ear_pain is not None:
                findings.append(("Ear pain", "Present" if obs.ear_pain else "Absent"))
            if obs.ear_discharge_reported is not None:
                findings.append(
                    (
                        "Ear discharge reported",
                        "Yes" if obs.ear_discharge_reported else "No",
                    )
                )
            if obs.ear_discharge_duration_days is not None:
                findings.append(
                    (
                        "Ear discharge duration",
                        f"{obs.ear_discharge_duration_days} days",
                    )
                )
            if obs.pus_draining_from_ear is not None:
                findings.append(
                    (
                        "Pus draining from ear",
                        "Present" if obs.pus_draining_from_ear else "Absent",
                    )
                )
            if obs.tender_swelling_behind_ear is not None:
                findings.append(
                    (
                        "Tender swelling behind ear",
                        "Present" if obs.tender_swelling_behind_ear else "Absent",
                    )
                )

    return tuple(findings)


def format_structured_encounter(encounter: dict[str, Any]) -> list[tuple[str, str]]:
    """Format a model-facing encounter dict into a clinician-friendly key-value view.

    Returns a list of (label, value) pairs for display in the
    'How EdgeIMCI interpreted the findings' section.
    """

    def _get(obj: dict[str, Any] | None, path: str) -> Any:
        if obj is None:
            return None
        parts = path.split(".")
        current: Any = obj
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    rows: list[tuple[str, str]] = []
    for path, label, formatter in _FIELD_LABELS:
        value = _get(encounter, path)
        rows.append((label, formatter(value)))
    return rows


def build_pipeline_trace(
    eval_result: HolisticEvaluationResult | None,
    encounter: HolisticEncounter | None,
    *,
    failed: bool = False,
) -> list[PipelineStep]:
    """Build the technical pipeline trace showing the architecture."""

    if failed:
        return [
            PipelineStep(
                label="Pipeline halted",
                kind="DETERMINISTIC",
                detail="Extraction or validation failed",
            ),
        ]

    return [
        PipelineStep(
            label="Management / referral",
            kind="DETERMINISTIC",
            detail="Actions derived from deterministic rules",
        ),
    ]
