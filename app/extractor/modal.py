"""Selected Modal checkpoint adapter for the workstation service."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.extractor.base import (
    AI_SERVICE_UNAVAILABLE_MESSAGE,
    INVALID_AI_INTERPRETATION_MESSAGE,
    ExtractionError,
    ExtractionResult,
)


MODAL_APP_NAME = "edge-imci-qwen3-0-6b-inference"
MODAL_FUNCTION_NAME = "infer"
TRAINING_RUN_ID = "251039a3-4adc-4e74-8c30-069eb8aca6de"
MODEL_WEIGHTS_SHA256 = "86bb2507e5e7d04ad35c6c933923b902d21652bd04c401055a97a0d4485fd76a"
logger = logging.getLogger(__name__)


class ModalEncounterExtractor:
    """Call the deployed selected checkpoint and fail closed on invalid output."""

    def __init__(
        self,
        invoke: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self._invoke = invoke or self._invoke_remote

    @property
    def mode_label(self) -> str:
        return "Qwen3-0.6B SFT / selected Modal checkpoint"

    def extract(self, free_text: str) -> ExtractionResult:
        if not free_text.strip():
            raise ExtractionError(
                "Enter the assessment findings before interpreting the encounter."
            )

        try:
            result = self._invoke(free_text.strip())
        except Exception as error:
            logger.exception("Selected model inference request failed")
            raise ExtractionError(AI_SERVICE_UNAVAILABLE_MESSAGE) from error

        if not isinstance(result, dict):
            logger.error("Selected model inference returned a non-object response")
            raise ExtractionError(INVALID_AI_INTERPRETATION_MESSAGE)
        if result.get("training_run_id") != TRAINING_RUN_ID:
            logger.error("Selected model response has an unexpected training run ID")
            raise ExtractionError(AI_SERVICE_UNAVAILABLE_MESSAGE)
        if result.get("model_weights_sha256") != MODEL_WEIGHTS_SHA256:
            logger.error("Selected model response has an unexpected weights checksum")
            raise ExtractionError(AI_SERVICE_UNAVAILABLE_MESSAGE)

        for field in ("parse_error", "schema_error", "adapter_error"):
            if result.get(field):
                logger.error("Selected model output failed %s: %s", field, result[field])
                raise ExtractionError(INVALID_AI_INTERPRETATION_MESSAGE)

        encounter = result.get("parsed_target")
        if result.get("schema_valid") is not True or not isinstance(encounter, dict):
            logger.error("Selected model output did not pass the encounter schema")
            raise ExtractionError(INVALID_AI_INTERPRETATION_MESSAGE)

        return ExtractionResult(
            encounter=encounter,
            extraction_mode=self.mode_label,
            matched_case_id=None,
        )

    @staticmethod
    def _invoke_remote(free_text: str) -> dict[str, Any]:
        try:
            import modal
        except ModuleNotFoundError as error:
            raise ExtractionError(
                "Modal support is not installed. Run with the modal-training extra."
            ) from error

        function = modal.Function.from_name(MODAL_APP_NAME, MODAL_FUNCTION_NAME)
        result = function.remote(free_text)
        if not isinstance(result, dict):
            raise ExtractionError("Modal returned a non-object inference response.")
        return result
