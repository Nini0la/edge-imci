from __future__ import annotations

import copy

import pytest

from app.extractor.base import (
    AI_SERVICE_UNAVAILABLE_MESSAGE,
    INVALID_AI_INTERPRETATION_MESSAGE,
    ExtractionError,
)
from app.extractor.modal import (
    MODEL_WEIGHTS_SHA256,
    TRAINING_RUN_ID,
    ModalEncounterExtractor,
)
from app.service import create_default_service
from edge_imci.inference.modal_structured_extraction import (
    MODEL_WEIGHTS_SHA256 as INFERENCE_WEIGHTS_SHA256,
)
from edge_imci.inference.modal_structured_extraction import (
    TRAINING_RUN_ID as INFERENCE_RUN_ID,
)


def _valid_response() -> dict[str, object]:
    stub, examples = create_default_service("stub")
    encounter = stub.extract(examples[0]["text"]).encounter
    return {
        "training_run_id": TRAINING_RUN_ID,
        "model_weights_sha256": MODEL_WEIGHTS_SHA256,
        "parsed_target": encounter,
        "schema_valid": True,
        "parse_error": None,
        "schema_error": None,
        "adapter_error": None,
    }


def test_modal_extractor_pins_selected_checkpoint_and_returns_model_target() -> None:
    response = _valid_response()
    extractor = ModalEncounterExtractor(invoke=lambda _: response)

    extraction = extractor.extract("Novel worker findings")

    assert TRAINING_RUN_ID == INFERENCE_RUN_ID
    assert MODEL_WEIGHTS_SHA256 == INFERENCE_WEIGHTS_SHA256
    assert extraction.encounter == response["parsed_target"]
    assert extraction.matched_case_id is None
    assert "Qwen3-0.6B" in extraction.extraction_mode


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("training_run_id", "wrong-run", AI_SERVICE_UNAVAILABLE_MESSAGE),
        ("model_weights_sha256", "wrong-hash", AI_SERVICE_UNAVAILABLE_MESSAGE),
        ("schema_valid", False, INVALID_AI_INTERPRETATION_MESSAGE),
        ("parse_error", "invalid JSON", INVALID_AI_INTERPRETATION_MESSAGE),
        ("schema_error", "invalid keys", INVALID_AI_INTERPRETATION_MESSAGE),
        ("adapter_error", "cannot adapt", INVALID_AI_INTERPRETATION_MESSAGE),
    ],
)
def test_modal_extractor_fails_closed(
    field: str, value: object, message: str
) -> None:
    response = copy.deepcopy(_valid_response())
    response[field] = value
    extractor = ModalEncounterExtractor(invoke=lambda _: response)

    with pytest.raises(ExtractionError) as raised:
        extractor.extract("Novel worker findings")

    assert str(raised.value) == message
    assert str(value) not in str(raised.value)


def test_modal_extractor_does_not_expose_schema_validator_dump() -> None:
    response = _valid_response()
    response["schema_error"] = (
        "ValidationError: Additional properties are not allowed "
        "('kid_coughing', 'mild_cough_or_difficult_breathing' were unexpected)"
    )

    preview = ModalEncounterExtractor(invoke=lambda _: response)

    with pytest.raises(ExtractionError) as raised:
        preview.extract("The child is 22 months and is coughing.")

    assert str(raised.value) == INVALID_AI_INTERPRETATION_MESSAGE
    assert "ValidationError" not in str(raised.value)
    assert "kid_coughing" not in str(raised.value)


def test_modal_service_mode_exposes_verified_demo_input() -> None:
    extractor, examples = create_default_service("modal")

    assert isinstance(extractor, ModalEncounterExtractor)
    assert examples[0]["id"] == "selected-model-demo-pneumonia"
    assert "able to drink or breastfeed" in examples[0]["text"]
