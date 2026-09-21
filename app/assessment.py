"""Assessment-scoped evidence acquisition around the unchanged clinical engine.

The extractor proposes observations; only worker-reviewed patches are accepted.
Requirements and urgency come from the holistic evaluator, never from the model.
This request-oriented demo keeps its accepted encounter in the local client.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from typing import Any

from app.extractor.base import ExtractionError, INVALID_AI_INTERPRETATION_MESSAGE
from app.language_understanding import LanguageUnderstandingError, LanguageUnderstandingProvider
from app.service.render import humanize_missing_element
from app.service.result import ExtractionPreview
from app.service.service import evaluate_extracted_findings
from edge_imci.evaluation.holistic import evaluate_holistic_encounter
from edge_imci.generation.holistic_language_full import (
    ACQUISITION_SPECS,
    _CONTRADICTION_CLARIFICATIONS,
)
from edge_imci.model_io.encounter import (
    MODEL_FACING_ENCOUNTER_SCHEMA_PATH, model_target_to_holistic_encounter,
)
from edge_imci.schemas.case import GeneralDangerSignObservations
from edge_imci.schemas.holistic import (
    HolisticDiarrhoeaObservations,
    HolisticEarObservations,
    HolisticFeverObservations,
    HolisticPatientFacts,
    HolisticRespiratoryObservations,
    MajorAssessment,
)


ASSESSMENTS = {
    "danger": (MajorAssessment.GENERAL_DANGER_SIGNS, "danger_signs", None),
    "respiratory": (MajorAssessment.RESPIRATORY, "respiratory", "patient_facts.has_cough_or_difficult_breathing"),
    "diarrhoea": (MajorAssessment.DIARRHOEA, "diarrhoea", "patient_facts.has_diarrhoea"),
    "fever": (MajorAssessment.FEVER, "fever", "patient_facts.has_fever"),
    "ear": (MajorAssessment.EAR_PROBLEM, "ear", "patient_facts.has_ear_problem"),
}

# Default dataclasses supply shape only. No observation is defaulted to absent.
_TEMPLATE = {
    "patient_facts": asdict(HolisticPatientFacts(None, None, None, None, None)),
    "danger_signs": asdict(GeneralDangerSignObservations()),
    "respiratory": asdict(HolisticRespiratoryObservations()),
    "diarrhoea": asdict(HolisticDiarrhoeaObservations()),
    "fever": asdict(HolisticFeverObservations()),
    "ear": asdict(HolisticEarObservations()),
}


class AssessmentError(ValueError):
    """A safe, worker-facing request or evidence validation failure."""


def _leaves(value: dict, prefix: str = "") -> dict[str, Any]:
    result = {}
    for name, item in value.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(item, dict):
            result.update(_leaves(item, path))
        else:
            result[path] = item
    return result


_FIELDS = tuple(_leaves(_TEMPLATE))
_SUPPORTED_FIELDS = tuple(
    field for field in _FIELDS
    if field not in {"diarrhoea.rehydration_stage", "diarrhoea.post_rehydration"}
)
_MEASUREMENT_GROUPS = (
    ("respiratory.respiratory_rate", "respiratory.child_calm", "respiratory.breaths_counted_one_minute"),
    ("respiratory.post_bronchodilator_respiratory_rate", "respiratory.post_bronchodilator_child_calm", "respiratory.post_bronchodilator_breaths_counted_one_minute"),
)


def _get(target: dict, path: str) -> Any:
    value: Any = target
    for part in path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def _set(target: dict, path: str, value: Any) -> None:
    node = target
    template = _TEMPLATE
    parts = path.split(".")
    for part in parts[:-1]:
        template = template[part]
        if node.get(part) is None:
            node[part] = deepcopy(template)
        node = node[part]
    node[parts[-1]] = value


def _target(value: Any = None) -> dict:
    target = deepcopy(_TEMPLATE if value is None else value)
    try:
        model_target_to_holistic_encounter(target, encounter_id="assessment-draft")
    except Exception:
        raise AssessmentError(
            "The encounter is invalid or outside the supported initial sick-child scope. "
            "Review the age and observations; accepted findings have not been changed."
        ) from None
    return target


def _assessment(value: Any) -> str:
    if not isinstance(value, str) or value not in ASSESSMENTS:
        raise AssessmentError("Select one of the existing IMCI assessments.")
    return value


def _capture_scope(value: Any) -> str:
    """A whole report is a capture scope, never a sixth clinical assessment."""
    if isinstance(value, str) and value == "full-note":
        return value
    return _assessment(value)


def _in_scope(field: str, assessment: str) -> bool:
    if assessment == "full-note":
        return field in _SUPPORTED_FIELDS
    _, prefix, entry = ASSESSMENTS[assessment]
    return (
        field.startswith(prefix + ".") or field == entry
        or field == "patient_facts.age_months"
        or (assessment == "diarrhoea" and field == "danger_signs.lethargic_or_unconscious")
    )


def assessment_schema() -> dict:
    """Expose supported observation controls, not clinical requirements or rules."""
    raw = MODEL_FACING_ENCOUNTER_SCHEMA_PATH.read_bytes()
    schema = json.loads(raw)
    fields = {}
    units = {
        "patient_facts.age_months": "months",
        "respiratory.cough_duration_days": "days",
        "diarrhoea.duration_days": "days",
        "fever.fever_duration_days": "days",
        "ear.ear_discharge_duration_days": "days",
        "respiratory.respiratory_rate": "breaths per minute",
        "respiratory.post_bronchodilator_respiratory_rate": "breaths per minute",
        "respiratory.oxygen_saturation_percent": "%",
        "fever.temperature_c": "deg C",
    }

    def visit(node: dict, path: str = "", nullable: bool = False) -> None:
        if "$ref" in node:
            visit(schema["$defs"][node["$ref"].removeprefix("#/$defs/")], path, nullable)
        elif "oneOf" in node or "anyOf" in node:
            branches = node.get("oneOf", node.get("anyOf", []))
            for child in branches:
                if child.get("type") != "null":
                    visit(child, path, nullable or any(branch.get("type") == "null" for branch in branches))
        elif "properties" in node:
            for name, child in node["properties"].items():
                visit(child, f"{path}.{name}" if path else name)
        elif path in _SUPPORTED_FIELDS:
            types = node["type"] if isinstance(node["type"], list) else [node["type"]]
            kind = "boolean" if "boolean" in types else "enum" if "enum" in node else next(item for item in types if item != "null")
            control = {
                "path": path, "label": humanize_missing_element(path), "kind": kind,
                "nullable": nullable or "null" in types,
                "assessments": [assessment for assessment in ASSESSMENTS if _in_scope(path, assessment)],
            }
            if kind == "enum":
                control["options"] = [
                    {"value": value, "label": value.replace("_", " ").capitalize()}
                    for value in node["enum"] if value is not None
                ]
            for bound in ("minimum", "maximum"):
                if bound in node:
                    control[bound] = node[bound]
            if path in units:
                control["unit"] = units[path]
            fields[path] = control

    visit(schema)
    return {"schema_id": schema["$id"], "schema_sha256": hashlib.sha256(raw).hexdigest(), "fields": fields}


def _question(field: str) -> dict[str, str]:
    if field == "respiratory.stridor_when_calm":
        text = "Is there stridor when the child is calm?"
    elif field in ACQUISITION_SPECS:
        text = ACQUISITION_SPECS[field][1]
    else:
        text = f"Confirm {humanize_missing_element(field).lower()}."
    return {"field": field, "text": text}


def evaluate_assessment(body: dict) -> dict:
    target = _target(body.get("encounter"))
    attempted = body.get("attempted", [])
    if not isinstance(attempted, list) or len(attempted) > len(ASSESSMENTS):
        raise AssessmentError("Invalid assessment attempt list.")
    for assessment in attempted:
        _assessment(assessment)
    encounter = model_target_to_holistic_encounter(target, encounter_id="assessment-draft")
    result = evaluate_holistic_encounter(encounter)
    preview = ExtractionPreview(
        input_text="Worker-reviewed assessment evidence",
        extraction_mode="reviewed-assessment-evidence",
        matched_case_id=None, structured_encounter=target, schema_valid=True,
    )
    analysis = evaluate_extracted_findings(preview)
    payload = {**asdict(analysis), "state": analysis.state}
    progress = {}
    shared_missing = result.missing_elements.get(MajorAssessment.ENCOUNTER, ())
    urgent_rules = {
        trace.rule_id for trace in result.action_trace if trace.action in result.urgent_actions
    }
    for assessment, (group, prefix, entry) in ASSESSMENTS.items():
        missing_set = set(result.missing_elements.get(group, ()))
        if entry in shared_missing:
            missing_set.add(entry)
        # Age is a shared encounter prerequisite, not a new clinical requirement.
        if "patient_facts.age_months" in shared_missing:
            missing_set.add("patient_facts.age_months")
        missing = [field for field in _SUPPORTED_FIELDS if field in missing_set]
        known = any(
            _get(target, field) is not None
            for field in _SUPPORTED_FIELDS
            if field.startswith(prefix + ".") or field == entry
        )
        blockers = list(result.contradictions) + list(result.unresolved_question_ids)
        # Do not auto-activate a pathway or silently ignore evidence under a NO entry.
        if entry and _get(target, entry) is False and any(
            value is not None for value in _leaves(target.get(prefix) or {}).values()
        ):
            blockers.append(
                f"Findings were supplied for {group.value.replace('_', ' ')} but its entry answer is absent. "
                "Review the entry answer and explicitly correct or retract conflicting findings."
            )
        if (
            entry and _get(target, entry) is True and not missing
            and result.missing_elements.get(MajorAssessment.GENERAL_DANGER_SIGNS)
        ):
            blockers.append("Complete the general danger signs assessment before confirming this assessment's dependencies.")
        urgent = any(
            trace.pathway == group and trace.rule_id in urgent_rules
            for trace in result.internal_classifications
        )
        status = (
            "URGENT" if urgent else "NOT_STARTED" if not known and assessment not in attempted
            else "INCOMPLETE" if missing or blockers else "COMPLETE"
        )
        question = _question(missing[0]) if missing else None
        decision = "ASK" if question else "COMPLETE"
        if blockers:
            question = None
            decision = "BLOCK"
            for contradiction in result.contradictions:
                clarifications = _CONTRADICTION_CLARIFICATIONS.get(contradiction, ())
                relevant = [item for item in clarifications if _in_scope(item[0], assessment)]
                if relevant:
                    field = relevant[0][0]
                    text = " ".join(item[2] for item in relevant)
                    if field in {item for group in _MEASUREMENT_GROUPS for item in group}:
                        text += " Report the repeated count and explicitly confirm both calm and full-minute counting conditions."
                    question = {"field": field, "text": text}
                    decision = "ASK"
                    break
        # An urgent encounter interrupts ordinary questioning in every section.
        if result.urgent_action_required:
            decision, question = "URGENT", None
        progress[assessment] = {
            "status": status, "decision": decision, "missing_fields": missing,
            "question": question, "blockers": blockers,
        }
    return {"encounter": target, "analysis": payload, "assessments": progress}


def extract_assessment(body: dict, language_provider: LanguageUnderstandingProvider) -> dict:
    assessment = _capture_scope(body.get("assessment"))
    target = _target(body.get("encounter"))
    findings = body.get("findings")
    if not isinstance(findings, str) or not 0 < len(findings.strip()) <= 8000:
        raise AssessmentError("Provide a short assessment report of 1 to 8,000 characters.")
    question_field = body.get("question_field")
    question_context = None
    if assessment == "full-note" and "question_field" in body:
        raise AssessmentError("A full assessment report cannot answer a follow-up question. Select its assessment instead.")
    if question_field is not None:
        current = evaluate_assessment({"encounter": target})["assessments"][assessment]["question"]
        if not isinstance(question_field, str) or not current or current["field"] != question_field:
            raise AssessmentError("The follow-up question is stale. Refresh the assessment and try again.")
        question_context = current
    try:
        extraction = language_provider.understand(
            findings.strip(),
            {"assessment": "Full assessment report" if assessment == "full-note" else ASSESSMENTS[assessment][0].value,
             "id": assessment},
            question_context, deepcopy(target),
        )
        if not isinstance(extraction.canonical_evidence, dict):
            raise AssessmentError(INVALID_AI_INTERPRETATION_MESSAGE)
        proposed = _target(extraction.canonical_evidence)
        uncertain_fields = {item["field"] for item in extraction.uncertainties if item["field"] is not None}
        if any(field not in _SUPPORTED_FIELDS or _get(proposed, field) is not None for field in uncertain_fields):
            raise AssessmentError(INVALID_AI_INTERPRETATION_MESSAGE)
    except (AssessmentError, LanguageUnderstandingError):
        raise
    except Exception:
        raise ExtractionError(INVALID_AI_INTERPRETATION_MESSAGE) from None
    changes = []
    for field in _SUPPORTED_FIELDS:
        value, previous = _get(proposed, field), _get(target, field)
        # An extraction null is omission, never a deletion or evidence of absence.
        if value is None and field not in uncertain_fields:
            continue
        changes.append({
            "field": field, "label": humanize_missing_element(field),
            "previous": previous, "value": value,
            "conflict": previous is not None and (type(value) is not type(previous) or value != previous),
            "outside_assessment": not _in_scope(field, assessment),
            "uncertain": field in uncertain_fields,
        })
    warnings = [
        "Review every proposed observation against the report, especially negatives, numbers, and qualifiers. "
        "The model can be wrong even when its JSON is valid."
    ]
    if not changes:
        warnings.append("No new usable evidence was extracted. Omitted or ambiguous findings remain unknown.")
    if any(change["outside_assessment"] for change in changes):
        warnings.append("Evidence outside the selected assessment needs an explicit review choice; it will not be silently applied or discarded.")
    if any(change["field"] in {field for group in _MEASUREMENT_GROUPS for field in group} for change in changes):
        warnings.append("For a repeated breathing count, report the rate and reconfirm that this count was made while calm for one full minute. Old validity evidence cannot validate a new count.")
    return {
        "assessment": assessment, "input_text": findings.strip(),
        "extraction_mode": language_provider.mode_label, "changes": changes,
        "warnings": warnings + list(extraction.warnings),
        "candidate_encounter": proposed,
        "english_rendering": extraction.english_rendering,
        "uncertainties": list(extraction.uncertainties),
        "evidence_spans": list(extraction.evidence_spans),
        "understanding": {
            "provider": extraction.provider, "model": extraction.model,
            "request_id": extraction.request_id, "prompt_version": extraction.prompt_version,
            "usage": extraction.usage,
        },
    }


def _validate_review_values(changes: list[dict]) -> None:
    candidate, original = deepcopy(_TEMPLATE), deepcopy(_TEMPLATE)
    for change in changes:
        uncertain = change.get("uncertain", False)
        if not isinstance(uncertain, bool) or (uncertain and change["value"] is not None):
            raise AssessmentError("Invalid observation uncertainty.")
        _set(candidate, change["field"], deepcopy(change["value"]))
        _set(original, change["field"], deepcopy(change["previous"]))
    # Validate report-only shapes even when a row will be kept or made unknown.
    _target(candidate)
    _target(original)


def prepare_assessment_review(body: dict) -> dict:
    """Rebase original candidate rows for review, without accepting any evidence.

    The client owns encounter state and must serialize accepts and guard its local
    revision. Disjoint fields alone do not establish clinical independence.
    """
    if not isinstance(body, dict):
        raise AssessmentError("Invalid evidence review.")
    assessment = _capture_scope(body.get("assessment"))
    target = _target(body.get("encounter"))
    changes = body.get("changes")
    if not isinstance(changes, list) or len(changes) > len(_SUPPORTED_FIELDS):
        raise AssessmentError("Invalid evidence review.")
    reviewed, changed_fields, seen = [], [], set()
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("field"), str):
            raise AssessmentError("Invalid observation update.")
        field = change["field"]
        if field not in _SUPPORTED_FIELDS or field in seen or "value" not in change or "previous" not in change:
            raise AssessmentError("Invalid or repeated observation field.")
        seen.add(field)
        value, previous = change["value"], _get(target, field)
        uncertain = change.get("uncertain", False)
        review_changed = type(previous) is not type(change["previous"]) or previous != change["previous"]
        if review_changed:
            changed_fields.append(field)
        reviewed.append({
            **deepcopy(change), "previous": previous,
            "conflict": previous is not None and (type(previous) is not type(value) or previous != value),
            "outside_assessment": not _in_scope(field, assessment),
            "uncertain": uncertain, "review_changed": review_changed,
        })
    _validate_review_values(changes)
    return {"changes": reviewed, "changed_fields": changed_fields}


def accept_assessment(body: dict) -> dict:
    assessment = _capture_scope(body.get("assessment"))
    target = _target(body.get("encounter"))
    previous_target = deepcopy(target)
    if body.get("confirmed") is not True:
        raise AssessmentError("Worker confirmation is required before applying findings.")
    changes, resolutions = body.get("changes"), body.get("resolutions", {})
    if not isinstance(changes, list) or len(changes) > len(_SUPPORTED_FIELDS) or not isinstance(resolutions, dict):
        raise AssessmentError("Invalid evidence review.")
    seen = set()
    applied = set()
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("field"), str):
            raise AssessmentError("Invalid observation update.")
        field = change["field"]
        if field not in _SUPPORTED_FIELDS or field in seen or "value" not in change or "previous" not in change:
            raise AssessmentError("Invalid or repeated observation field.")
        seen.add(field)
        previous = _get(target, field)
        if type(previous) is not type(change["previous"]) or previous != change["previous"]:
            raise AssessmentError("Accepted evidence has changed. Interpret and review this report again.")
        value = change["value"]
        conflict = previous is not None and (type(previous) is not type(value) or previous != value)
        review_changed = change.get("review_changed", False)
        if not isinstance(review_changed, bool):
            raise AssessmentError("Invalid evidence review.")
        choice = resolutions.get(field)
        if (conflict or review_changed or not _in_scope(field, assessment) or value is None) and choice is None:
            raise AssessmentError("Explicitly resolve each conflicting, changed-since-capture, out-of-assessment, or retracted observation.")
        if choice not in (None, "replace", "keep", "unknown"):
            raise AssessmentError("Invalid evidence review choice.")
        if choice != "keep":
            _set(target, field, None if choice == "unknown" else value)
            applied.add(field)
    if not resolutions.keys() <= seen:
        raise AssessmentError("Resolve only submitted observation fields.")
    _validate_review_values(changes)
    # Keep acquisition episodes linked without altering observations or thresholds.
    # Same-valued explicit reconfirmations are retained in extraction for this check.
    for rate, *qualifiers in _MEASUREMENT_GROUPS:
        changed_rate = rate in applied and _get(target, rate) is not None and _get(target, rate) != _get(previous_target, rate)
        if changed_rate and any(_get(target, qualifier) is True and qualifier not in applied for qualifier in qualifiers):
            raise AssessmentError("A new breathing count cannot inherit old validity evidence. Report the count and explicitly reconfirm calm and full-minute counting, or retract the old qualifiers to unknown.")
        repaired_validity = any(
            qualifier in applied and _get(previous_target, qualifier) is False and _get(target, qualifier) is True
            for qualifier in qualifiers
        )
        if repaired_validity and _get(target, rate) is not None and any(field not in applied for field in (rate, *qualifiers)):
            raise AssessmentError("An invalid breathing count must be repeated. Report the repeated rate and both validity conditions together, or explicitly retract the old rate to unknown.")
    attempted = body.get("attempted", [])
    if not isinstance(attempted, list):
        raise AssessmentError("Invalid assessment attempt list.")
    for item in attempted:
        _assessment(item)
    # Ownership, not section scope: age is shared and lethargy belongs to danger.
    newly_attempted = [
        name for name, (_, prefix, entry) in ASSESSMENTS.items()
        if any(field.startswith(prefix + ".") or field == entry for field in applied)
    ] if assessment == "full-note" else [assessment]
    return evaluate_assessment({
        "encounter": target, "attempted": list(dict.fromkeys([*attempted, *newly_attempted])),
    })
