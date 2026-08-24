"""Model-facing structured encounter contracts and deterministic adapters."""

from edge_imci.model_io.encounter import (
    MODEL_FACING_ENCOUNTER_SCHEMA_ID,
    MODEL_FACING_ENCOUNTER_SCHEMA_PATH,
    MODEL_TARGET_EXPORTER_ID,
    canonical_model_target_json,
    model_target_to_holistic_encounter,
    project_model_facing_encounter,
    validate_model_facing_encounter,
)

__all__ = [
    "MODEL_FACING_ENCOUNTER_SCHEMA_ID",
    "MODEL_FACING_ENCOUNTER_SCHEMA_PATH",
    "MODEL_TARGET_EXPORTER_ID",
    "canonical_model_target_json",
    "model_target_to_holistic_encounter",
    "project_model_facing_encounter",
    "validate_model_facing_encounter",
]
