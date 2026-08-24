"""Metrics for model-facing encounter extraction and clinical equivalence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from jsonschema import ValidationError

from edge_imci.evaluation.holistic import evaluate_holistic_encounter
from edge_imci.model_io.encounter import (
    model_target_to_holistic_encounter,
    validate_model_facing_encounter,
)


_MISSING = object()
_MEASUREMENT_PATHS = frozenset(
    {
        "patient_facts.age_months",
        "respiratory.respiratory_rate",
        "respiratory.oxygen_saturation_percent",
        "respiratory.post_bronchodilator_respiratory_rate",
        "fever.temperature_c",
    }
)
_DURATION_PATHS = frozenset(
    {
        "respiratory.cough_duration_days",
        "diarrhoea.duration_days",
        "fever.fever_duration_days",
        "ear.ear_discharge_duration_days",
    }
)
_QUALIFIER_PATHS = frozenset(
    {
        "patient_facts.has_cough_or_difficult_breathing",
        "danger_signs.unable_to_drink_or_breastfeed",
        "danger_signs.lethargic_or_unconscious",
        "respiratory.stridor_when_calm",
        "respiratory.child_calm",
        "respiratory.breaths_counted_one_minute",
        "respiratory.hiv_exposed_or_infected",
        "fever.obvious_cause_of_fever_present",
        "fever.identified_bacterial_cause_present",
        "fever.fever_present_every_day",
        "fever.measles_within_last_3_months",
        "fever.mouth_ulcers_deep_or_extensive",
        "ear.ear_discharge_reported",
        "ear.pus_draining_from_ear",
    }
)
_PRE_POST_PATH_PREFIXES = (
    "respiratory.bronchodilator_trial_completed",
    "respiratory.post_bronchodilator_",
    "diarrhoea.rehydration_stage",
    "diarrhoea.post_rehydration",
)


@dataclass(frozen=True)
class StructuredExtractionMetrics:
    schema_valid: bool
    whole_record_exact_match: bool
    field_accuracy: float
    known_positive_precision: float
    known_positive_recall: float
    known_negative_accuracy: float | None
    unknown_preservation_accuracy: float | None
    measurement_accuracy: float | None
    duration_accuracy: float | None
    qualifier_accuracy: float | None
    acquisition_mode_accuracy: float | None
    pre_post_intervention_accuracy: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionEquivalenceMetrics:
    prediction_accepted_by_adapter: bool
    gold_pipeline_state: str
    predicted_pipeline_state: str
    completeness_equivalent: bool
    classification_equivalent: bool
    urgency_equivalent: bool
    urgent_action_equivalent: bool
    referral_behavior_equivalent: bool
    management_equivalent: bool
    missing_information_equivalent: bool
    contradiction_state_equivalent: bool
    decision_equivalent: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_model_target_json(text: str) -> dict[str, Any]:
    """Parse exactly one JSON object and reject duplicate object keys."""

    def pairs_to_dict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is not allowed: {value}")

    parsed = json.loads(
        text,
        object_pairs_hook=pairs_to_dict,
        parse_constant=reject_constant,
    )
    if not isinstance(parsed, dict):
        raise ValueError("model target must be one JSON object")
    return parsed


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    result: dict[str, Any] = {}
    for key in sorted(value):
        child = f"{prefix}.{key}" if prefix else key
        result.update(_flatten(value[key], child))
    return result


def _accuracy_for_paths(
    gold: dict[str, Any], predicted: dict[str, Any], paths: set[str] | frozenset[str]
) -> float | None:
    relevant = sorted(path for path in paths if path in gold)
    if not relevant:
        return None
    return sum(predicted.get(path, _MISSING) == gold[path] for path in relevant) / len(relevant)


def _ratio(numerator: int, denominator: int, *, empty: float = 1.0) -> float:
    return numerator / denominator if denominator else empty


def score_structured_extraction(
    gold_target: dict[str, Any], predicted_target: dict[str, Any]
) -> StructuredExtractionMetrics:
    """Score semantic state without running clinical decision logic."""

    validate_model_facing_encounter(gold_target)
    try:
        validate_model_facing_encounter(predicted_target)
        schema_valid = True
    except (ValidationError, ValueError):
        schema_valid = False

    gold = _flatten(gold_target)
    predicted = _flatten(predicted_target)
    all_paths = sorted(set(gold) | set(predicted))
    field_accuracy = _ratio(
        sum(gold.get(path, _MISSING) == predicted.get(path, _MISSING) for path in all_paths),
        len(all_paths),
    )

    gold_positive = {path for path, value in gold.items() if value is True}
    predicted_positive = {path for path, value in predicted.items() if value is True}
    true_positive = len(gold_positive & predicted_positive)

    gold_negative = {path for path, value in gold.items() if value is False}
    gold_unknown = {path for path, value in gold.items() if value is None}
    pre_post_paths = {
        path
        for path in gold
        if any(
            path == prefix or path.startswith(prefix + ".")
            for prefix in _PRE_POST_PATH_PREFIXES
        )
    }
    return StructuredExtractionMetrics(
        schema_valid=schema_valid,
        whole_record_exact_match=schema_valid and predicted_target == gold_target,
        field_accuracy=field_accuracy,
        known_positive_precision=_ratio(true_positive, len(predicted_positive)),
        known_positive_recall=_ratio(true_positive, len(gold_positive)),
        known_negative_accuracy=(
            _ratio(
                sum(predicted.get(path, _MISSING) is False for path in gold_negative),
                len(gold_negative),
            )
            if gold_negative
            else None
        ),
        unknown_preservation_accuracy=(
            _ratio(
                sum(predicted.get(path, _MISSING) is None for path in gold_unknown),
                len(gold_unknown),
            )
            if gold_unknown
            else None
        ),
        measurement_accuracy=_accuracy_for_paths(gold, predicted, _MEASUREMENT_PATHS),
        duration_accuracy=_accuracy_for_paths(gold, predicted, _DURATION_PATHS),
        qualifier_accuracy=_accuracy_for_paths(gold, predicted, _QUALIFIER_PATHS),
        # The v1 source substrate does not encode generic per-observation
        # acquisition mode, so reporting a synthetic score would be misleading.
        acquisition_mode_accuracy=None,
        pre_post_intervention_accuracy=_accuracy_for_paths(gold, predicted, pre_post_paths),
    )


def _pipeline_state(target: dict[str, Any], *, encounter_id: str) -> dict[str, Any]:
    try:
        validate_model_facing_encounter(target)
    except (ValidationError, ValueError):
        return {"state": "SCHEMA_INVALID"}
    try:
        encounter = model_target_to_holistic_encounter(target, encounter_id=encounter_id)
    except ValueError as exc:
        message = str(exc)
        if "age_months" in message:
            return {"state": "OUT_OF_SCOPE_AGE"}
        if "treatment-stage" in message:
            return {"state": "UNSUPPORTED_REHYDRATION_STAGE"}
        return {"state": f"ADAPTER_REJECTED:{message}"}
    return {"state": "EVALUATED", "evaluation": evaluate_holistic_encounter(encounter).to_dict()}


def _classification_signature(evaluation: dict[str, Any]) -> tuple[tuple[str, str, str, str], ...]:
    rows: list[tuple[str, str, str, str]] = []
    for kind in ("internal_classifications", "final_classifications"):
        for item in evaluation[kind]:
            rows.append((kind, item["pathway"], item["classification"], item["stage"]))
    return tuple(sorted(rows))


def _action_signature(evaluation: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for kind in ("urgent_actions", "intermediate_actions", "deferred_actions", "final_actions"):
        rows.extend((kind, action) for action in evaluation[kind])
    return tuple(sorted(rows))


def _referral_signature(evaluation: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(
        row for row in _action_signature(evaluation) if "REFER" in row[1]
    )


def compare_decision_equivalence(
    gold_target: dict[str, Any], predicted_target: dict[str, Any]
) -> DecisionEquivalenceMetrics:
    """Compare clinical results produced by the same deterministic engine."""

    gold = _pipeline_state(gold_target, encounter_id="gold-extraction-eval")
    predicted = _pipeline_state(predicted_target, encounter_id="predicted-extraction-eval")
    gold_state = gold["state"]
    predicted_state = predicted["state"]
    accepted = predicted_state == "EVALUATED"

    if gold_state != "EVALUATED" or predicted_state != "EVALUATED":
        equivalent_rejection = gold_state == predicted_state
        return DecisionEquivalenceMetrics(
            prediction_accepted_by_adapter=accepted,
            gold_pipeline_state=gold_state,
            predicted_pipeline_state=predicted_state,
            completeness_equivalent=equivalent_rejection,
            classification_equivalent=equivalent_rejection,
            urgency_equivalent=equivalent_rejection,
            urgent_action_equivalent=equivalent_rejection,
            referral_behavior_equivalent=equivalent_rejection,
            management_equivalent=equivalent_rejection,
            missing_information_equivalent=equivalent_rejection,
            contradiction_state_equivalent=equivalent_rejection,
            decision_equivalent=equivalent_rejection,
        )

    gold_evaluation = gold["evaluation"]
    predicted_evaluation = predicted["evaluation"]
    completeness = (
        gold_evaluation["supported_encounter_complete"]
        == predicted_evaluation["supported_encounter_complete"]
        and gold_evaluation["final_holistic_synthesis_authorized"]
        == predicted_evaluation["final_holistic_synthesis_authorized"]
    )
    classification = _classification_signature(gold_evaluation) == _classification_signature(
        predicted_evaluation
    )
    urgency = gold_evaluation["urgent_action_required"] == predicted_evaluation[
        "urgent_action_required"
    ]
    urgent_actions = gold_evaluation["urgent_actions"] == predicted_evaluation["urgent_actions"]
    referral = _referral_signature(gold_evaluation) == _referral_signature(predicted_evaluation)
    management = _action_signature(gold_evaluation) == _action_signature(predicted_evaluation)
    missing = (
        gold_evaluation["missing_elements"] == predicted_evaluation["missing_elements"]
        and gold_evaluation["unresolved_question_ids"]
        == predicted_evaluation["unresolved_question_ids"]
    )
    contradictions = gold_evaluation["contradictions"] == predicted_evaluation["contradictions"]
    values = (
        completeness,
        classification,
        urgency,
        urgent_actions,
        referral,
        management,
        missing,
        contradictions,
    )
    return DecisionEquivalenceMetrics(
        prediction_accepted_by_adapter=True,
        gold_pipeline_state=gold_state,
        predicted_pipeline_state=predicted_state,
        completeness_equivalent=completeness,
        classification_equivalent=classification,
        urgency_equivalent=urgency,
        urgent_action_equivalent=urgent_actions,
        referral_behavior_equivalent=referral,
        management_equivalent=management,
        missing_information_equivalent=missing,
        contradiction_state_equivalent=contradictions,
        decision_equivalent=all(values),
    )
