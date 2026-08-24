"""Deterministic surface guards for controlled PHC language variants.

These checks target failure modes already observed in real teacher attempts.
They supplement rather than replace human semantic review, especially for
Nigerian Pidgin and intentionally noisy input.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
STYLE_CONTRACT_ID = "edge-imci-input-language-style-contract-v1"
STYLE_CONTRACT_PATH = (
    ROOT / "configs" / "generation" / "input_language_style_contract_v1.json"
)

_DRINK_AND_BREASTFEED = re.compile(
    r"\b(?:drink|drinking)\s+and\s+(?:to\s+)?breastfeed(?:ing)?\b",
    re.IGNORECASE,
)
_WEAK_OR_DOUBLE_NEGATIVE_DRINKING = re.compile(
    r"\b(?:(?:no\s+(?:report|history|mention)\s+of\s+being\s+unable|not\s+unable)\s+"
    r"to\s+drink\s+or\s+breastfeed|no\s+inability\s+to\s+drink\s+or\s+breastfeed)\b",
    re.IGNORECASE,
)
_VOMITING_ABSENCE_OF_REPORT = re.compile(
    r"\b(?:vomit(?:s|ing)?\s+everything)\b[^.]{0,25}\b(?:not\s+reported|not\s+mentioned|unknown)\b|"
    r"\bno\s+(?:report|mention)\s+of\s+vomit(?:s|ing)?\s+everything\b",
    re.IGNORECASE,
)
_BACTERIAL_CAUSE = re.compile(r"\bbacter(?:ial|ia)\b", re.IGNORECASE)
_IDENTIFICATION_QUALIFIER = re.compile(
    r"\b(?:identif\w*|known|found|noted|reported|see|seen)\b",
    re.IGNORECASE,
)
_TARGET_LEAKAGE = re.compile(
    r"\b(?:classification|classify as|urgent referral|required referral|plan [abc]|"
    r"amoxicillin|antimalarial|treatment plan|management plan|rule[_ -]?id|schema|"
    r"no danger signs?|does not have any danger signs?|no dehydration)\b",
    re.IGNORECASE,
)
_PATIENT_AS_MALARIA_RISK_SETTING = re.compile(
    r"\b(?:the\s+)?(?:child|patient|pt|pikin)\s+(?:is\s+)?at\s+(?:a\s+)?"
    r"(?:high|low|no)\s+risk\s+(?:for|of)\s+malaria\b",
    re.IGNORECASE,
)
_PIDGIN_PATIENT_AS_MALARIA_RISK_SETTING = re.compile(
    r"\b(?:e|pikin|child)\s+(?:get|dey(?:\s+for)?)\s+(?:a\s+)?"
    r"(?:high|low|no)\s+malaria\s+risk\b",
    re.IGNORECASE,
)
_EAR_DISCHARGE_ABSENCE_OF_REPORT = re.compile(
    r"\b(?:no\s+report\s+of\s+ear\s+discharge|"
    r"no\s+reported\s+ear\s+discharge|"
    r"ear\s+discharge\s+(?:is|was)\s+not\s+reported|"
    r"ear\s+discharge\s+not\s+reported|"
    r"no\s+ear\s+discharge\s+(?:is\s+)?reported)\b",
    re.IGNORECASE,
)
_EAR_PROBLEM_ABSENCE_OF_REPORT = re.compile(
    r"\b(?:no\s+report\s+of\s+(?:an?\s+)?ear\s+problem|"
    r"no\s+ear\s+problem\s+reported|"
    r"(?:ear\s+problem|ear\s+wahala)\s+(?:is|was)?\s*not\s+reported|"
    r"caregiver\s+(?:did\s+not|didn't|no)\s+(?:report|talk|mention).{0,25}\bear\s+problem)\b",
    re.IGNORECASE,
)
_POSITIVE_ABILITY = re.compile(
    r"\b(?:able\s+to\s+drink|(?:can|fit)\s+drink|fit\s+to\s+drink)\b",
    re.IGNORECASE,
)
_NEGATIVE_ABILITY = re.compile(
    r"\b(?:unable\s+to\s+drink|not\s+able\s+to\s+drink|cannot\s+drink|"
    r"can't\s+drink|(?:no|nor)\s+fit\s+drink)\b",
    re.IGNORECASE,
)
_NEGATIVE_COUGH_ENTRY = re.compile(
    r"\b(?:no|not|without|does\s+not\s+have|doesn't\s+have|no\s+get|no\s+dey)\b"
    r"[^.]{0,35}\b(?:cough|difficult\s+breathing|difficulty\s+breathing)\b",
    re.IGNORECASE,
)
_PAST_ONLY_COUGH_ENTRY = re.compile(
    r"(?<!has )\bhad\s+(?:a\s+)?(?:cough|cough\s+or\s+(?:difficult|difficulty)\s+breathing)\b",
    re.IGNORECASE,
)
_NEGATIVE_WHEEZE = re.compile(
    r"\b(?:no|not|without)\b[^.]{0,30}\bwheez|\bwheez\w*\b[^.]{0,20}\b(?:absent|not\s+present)\b",
    re.IGNORECASE,
)
_NEGATIVE_RASH = re.compile(
    r"\b(?:no|not|without)\b[^.]{0,25}\b(?:generalized|generalised)?\s*rash\b|"
    r"\b(?:generalized|generalised)\s+rash\b[^.]{0,20}\b(?:absent|negative)\b",
    re.IGNORECASE,
)
_NEGATIVE_STIFF_NECK = re.compile(
    r"\b(?:no|not|without)\b[^.]{0,25}\bstiff\s+neck\b|"
    r"\bstiff\s+neck\b[^.]{0,20}\b(?:absent|negative|not\s+seen|not\s+observed)\b",
    re.IGNORECASE,
)
_POSITIVE_EAR_PROBLEM = re.compile(
    r"\b(?:ear\s+problem|ear\s+wahala|ear\s+issue|problem\s+with\s+(?:the\s+)?ear)\b",
    re.IGNORECASE,
)
_BACTERIAL_EXISTENCE_NEGATION = re.compile(
    r"\b(?:identified\s+)?bacterial\s+cause\s+(?:is\s+)?(?:absent|not\s+present)|"
    r"\bno\s+bacterial\s+cause\s+(?:exists?|is\s+present)\b",
    re.IGNORECASE,
)
_DRINKING_STATUS_EVIDENCE: dict[str, re.Pattern[str]] = {
    "NORMAL": re.compile(
        r"\b(?:drinks?|drinking(?:\s+status)?)\b[^.]{0,40}\bnormal(?:ly)?\b|"
        r"\bnormal(?:ly)?\b[^.]{0,40}\b(?:drinks?|drinking)\b|"
        r"\b(?:drink|drinking)\b[^.]{0,30}\b(?:well\s+as\s+usual|as\s+usual)\b",
        re.IGNORECASE,
    ),
    "EAGER_OR_THIRSTY": re.compile(r"\b(?:eager(?:ly)?|thirst(?:y|ily)?)\b", re.IGNORECASE),
    "POORLY": re.compile(r"\b(?:poor|poorly)\b", re.IGNORECASE),
    "UNABLE": re.compile(
        r"\b(?:unable|not\s+able|cannot|can't)\s+to\s+drink\b|"
        r"\bdrinking\s+status\s*[:=-]?\s*unable\b|"
        r"\b(?:no|nor)\s+fit\s+drink\b",
        re.IGNORECASE,
    ),
}

# This lexicon is deliberately conservative and covers null fields exercised by
# the bounded canary. It is not a general medical-language ontology.
_NULL_FIELD_TERMS: dict[str, tuple[re.Pattern[str], ...]] = {
    "patient_facts.has_diarrhoea": (
        re.compile(r"\bdiarrh(?:oea|ea)\b", re.IGNORECASE),
        re.compile(r"\b(?:loose|watery)\s+stools?\b", re.IGNORECASE),
        re.compile(r"\brunning stomach\b", re.IGNORECASE),
        re.compile(r"\bpurging\b", re.IGNORECASE),
    ),
    "respiratory.hiv_exposed_or_infected": (
        re.compile(r"\bhiv\b", re.IGNORECASE),
    ),
    "respiratory.oxygen_saturation_percent": (
        re.compile(r"\b(?:oxygen saturation|spo2|sats?)\b", re.IGNORECASE),
    ),
    "ear.ear_discharge_reported": (
        re.compile(r"\bear discharge\b", re.IGNORECASE),
        re.compile(r"\bdischarge from (?:the )?ear\b", re.IGNORECASE),
    ),
    "fever.fever_present_every_day": (
        re.compile(r"\b(?:every day|daily)\b", re.IGNORECASE),
    ),
    "fever.clouding_of_cornea": (
        re.compile(r"\b(?:cloud(?:ing|y)|cornea)\b", re.IGNORECASE),
    ),
    "fever.mouth_ulcers": (
        re.compile(r"\bmouth ulcers?\b", re.IGNORECASE),
    ),
    "fever.mouth_ulcers_deep_or_extensive": (
        re.compile(r"\b(?:deep|extensive)\s+mouth ulcers?\b", re.IGNORECASE),
    ),
    "fever.pus_draining_from_eye": (
        re.compile(r"\b(?:pus|discharge)\s+(?:draining\s+)?from (?:the )?eye\b", re.IGNORECASE),
    ),
}


@dataclass(frozen=True)
class LanguageSemanticGuardResult:
    passed: bool
    error_codes: tuple[str, ...]
    details: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "error_codes": list(self.error_codes),
            "details": list(self.details),
            "human_semantic_review_required": True,
        }


def load_style_contract() -> dict[str, Any]:
    contract = json.loads(STYLE_CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != STYLE_CONTRACT_ID:
        raise ValueError("incorrect input-language style contract ID")
    if contract.get("status") != "APPROVED_FOR_BOUNDED_CANARIES":
        raise ValueError("input-language style contract is not canary-approved")
    authorization = contract.get("authorization", {})
    if authorization.get("bounded_canary_remote_calls_authorized") is not True:
        raise ValueError("bounded language canary calls are not authorized")
    if authorization.get("bulk_generation_authorized") is not False:
        raise ValueError("style contract must not authorize bulk generation")
    if authorization.get("training_authorized") is not False:
        raise ValueError("style contract must not authorize training")
    return contract


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    result: dict[str, Any] = {}
    for key, child_value in value.items():
        child = f"{prefix}.{key}" if prefix else key
        result.update(_flatten(child_value, child))
    return result


def _field_is_unknown(flattened: dict[str, Any], field: str) -> bool:
    parts = field.split(".")
    for length in range(len(parts), 0, -1):
        candidate = ".".join(parts[:length])
        if candidate in flattened:
            return flattened[candidate] is None
    return False


def _numeric_evidence_matches(value: int | float, text: str) -> bool:
    if isinstance(value, float) and value.is_integer():
        alternatives = (str(int(value)), f"{value:.1f}")
    else:
        alternatives = (str(value),)
    return any(
        re.search(rf"(?<![\d.]){re.escape(item)}(?!\d|[.]\d)", text)
        for item in alternatives
    )


def validate_language_semantics(
    candidate: dict[str, Any],
    semantic_record: dict[str, Any],
    *,
    variant_style: str,
) -> LanguageSemanticGuardResult:
    """Check known canary failure modes without claiming full semantic proof."""

    contract = load_style_contract()
    if variant_style not in contract["variant_styles"]:
        raise ValueError(f"unknown input-language variant style: {variant_style}")
    submission = candidate.get("user_submission", "")
    evidence = {
        item.get("fact_id"): item.get("evidence_text", "")
        for item in candidate.get("fact_evidence", [])
        if isinstance(item, dict)
    }
    errors: list[str] = []
    details: list[str] = []

    if _DRINK_AND_BREASTFEED.search(submission):
        errors.append("LOGICAL_CONNECTOR_OR_TO_AND")
        details.append("unable-to-drink evidence strengthened 'or' to 'and'")

    if _WEAK_OR_DOUBLE_NEGATIVE_DRINKING.search(submission):
        errors.append("NEGATIVE_EVIDENCE_WEAKENED_OR_DOUBLE_NEGATED")
        details.append(
            "known ability to drink or breastfeed was rendered as absence-of-report "
            "or a double negative"
        )

    if _VOMITING_ABSENCE_OF_REPORT.search(submission):
        errors.append("KNOWN_NEGATIVE_VOMITING_WEAKENED_TO_NONREPORT")
        details.append("known vomiting-everything state was weakened to absence of report")

    bacterial = evidence.get("fever.identified_bacterial_cause_present")
    if bacterial and _BACTERIAL_CAUSE.search(bacterial) and not _IDENTIFICATION_QUALIFIER.search(
        bacterial
    ):
        errors.append("EPISTEMIC_QUALIFIER_DROPPED")
        details.append("bacterial-cause evidence omitted identification/observation qualification")

    malaria_risk = evidence.get("fever.malaria_risk")
    if malaria_risk and (
        _PATIENT_AS_MALARIA_RISK_SETTING.search(malaria_risk)
        or _PIDGIN_PATIENT_AS_MALARIA_RISK_SETTING.search(malaria_risk)
    ):
        errors.append("MALARIA_RISK_CONTEXT_SHIFT")
        details.append("area/setting malaria risk was recast as the child's individual risk")

    encounter = semantic_record["input"]["encounter"]
    flattened = _flatten(
        {
            key: value
            for key, value in encounter.items()
            if key not in {"encounter_id", "schema_version"}
        }
    )
    drinking_status = flattened.get("diarrhoea.dehydration.drinking_status")
    drinking_evidence = evidence.get("diarrhoea.dehydration.drinking_status", "")
    expected_drinking_pattern = _DRINKING_STATUS_EVIDENCE.get(drinking_status)
    if (
        expected_drinking_pattern is not None
        and not expected_drinking_pattern.search(drinking_evidence)
    ):
        errors.append("DIARRHOEA_DRINKING_STATUS_DISTINCTION_LOST")
        details.append(
            "diarrhoea-specific drinking status was weakened or conflated with "
            "general ability to drink or breastfeed"
        )

    ear_discharge_reported = flattened.get("ear.ear_discharge_reported")
    ear_discharge_evidence = evidence.get("ear.ear_discharge_reported", "")
    if (
        ear_discharge_reported is False
        and _EAR_DISCHARGE_ABSENCE_OF_REPORT.search(ear_discharge_evidence)
    ):
        errors.append("KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT")
        details.append(
            "known-negative ear-discharge history was weakened to absence of a report"
        )

    ear_problem = flattened.get("patient_facts.has_ear_problem")
    ear_problem_evidence = evidence.get("patient_facts.has_ear_problem", "")
    if ear_problem is False and _EAR_PROBLEM_ABSENCE_OF_REPORT.search(ear_problem_evidence):
        errors.append("KNOWN_NEGATIVE_EAR_PROBLEM_WEAKENED_TO_NONREPORT")
        details.append("known-negative ear-problem entry was weakened to absence of a report")
    elif ear_problem is True and not _POSITIVE_EAR_PROBLEM.search(ear_problem_evidence):
        errors.append("EAR_PROBLEM_ENTRY_CONFLATED_WITH_NESTED_FINDING")
        details.append("positive ear-problem entry was not independently expressed")

    identified_bacterial = flattened.get("fever.identified_bacterial_cause_present")
    bacterial_evidence = evidence.get("fever.identified_bacterial_cause_present", "")
    if identified_bacterial is False and _BACTERIAL_EXISTENCE_NEGATION.search(
        bacterial_evidence
    ):
        errors.append("EPISTEMIC_QUALIFIER_DROPPED")
        details.append("no identified bacterial cause was recast as cause non-existence")

    unable = flattened.get("danger_signs.unable_to_drink_or_breastfeed")
    unable_evidence = evidence.get("danger_signs.unable_to_drink_or_breastfeed", "")
    if unable is True and _POSITIVE_ABILITY.search(unable_evidence):
        errors.append("DANGER_DRINKING_POLARITY_REVERSED")
        details.append("inability to drink or breastfeed was rendered as ability")
    elif unable is False and _NEGATIVE_ABILITY.search(unable_evidence):
        errors.append("DANGER_DRINKING_POLARITY_REVERSED")
        details.append("ability to drink or breastfeed was rendered as inability")

    cough_entry = flattened.get("patient_facts.has_cough_or_difficult_breathing")
    cough_evidence = evidence.get("patient_facts.has_cough_or_difficult_breathing", "")
    if cough_entry is True and _NEGATIVE_COUGH_ENTRY.search(cough_evidence):
        errors.append("COUGH_ENTRY_POLARITY_REVERSED")
        details.append("positive cough/difficult-breathing entry was rendered as negative")
    elif cough_entry is True and _PAST_ONLY_COUGH_ENTRY.search(cough_evidence):
        errors.append("CURRENT_COUGH_ENTRY_SHIFTED_TO_PAST_ONLY")
        details.append("current cough/difficult-breathing entry was rendered as past-only")

    wheezing = flattened.get("respiratory.wheezing")
    wheezing_evidence = evidence.get("respiratory.wheezing", "")
    recurrent = flattened.get("respiratory.recurrent_wheeze")
    recurrent_evidence = evidence.get("respiratory.recurrent_wheeze", "")
    if wheezing is True and _NEGATIVE_WHEEZE.search(wheezing_evidence):
        errors.append("WHEEZING_POLARITY_REVERSED")
        details.append("positive wheezing was rendered as absent")
    if (
        wheezing is not None
        and recurrent is not None
        and wheezing != recurrent
        and wheezing_evidence
        and wheezing_evidence == recurrent_evidence
    ):
        errors.append("WHEEZING_AND_RECURRENT_WHEEZE_CONFLATED")
        details.append("different wheezing and recurrent-wheeze states share one evidence claim")

    rash = flattened.get("fever.generalized_rash")
    rash_evidence = evidence.get("fever.generalized_rash", "")
    if rash is True and _NEGATIVE_RASH.search(rash_evidence):
        errors.append("GENERALIZED_RASH_POLARITY_REVERSED")
        details.append("positive generalized rash was rendered as negative")

    stiff_neck = flattened.get("fever.stiff_neck")
    stiff_neck_evidence = evidence.get("fever.stiff_neck", "")
    if stiff_neck is True and _NEGATIVE_STIFF_NECK.search(stiff_neck_evidence):
        errors.append("STIFF_NECK_POLARITY_REVERSED")
        details.append("positive stiff neck was rendered as negative")

    for field, value in flattened.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        numeric_evidence = evidence.get(field, "")
        if numeric_evidence and not _numeric_evidence_matches(value, numeric_evidence):
            errors.append("MEASUREMENT_OR_DURATION_SHIFT")
            details.append(field)

    for field, patterns in _NULL_FIELD_TERMS.items():
        if _field_is_unknown(flattened, field) and any(
            pattern.search(submission) for pattern in patterns
        ):
            errors.append("UNKNOWN_FIELD_MENTIONED")
            details.append(field)

    if _TARGET_LEAKAGE.search(submission):
        errors.append("TARGET_SIDE_INFORMATION_LEAKAGE")
        details.append("submission contains downstream decision or internal-target terminology")

    return LanguageSemanticGuardResult(
        passed=not errors,
        error_codes=tuple(dict.fromkeys(errors)),
        details=tuple(dict.fromkeys(details)),
    )
