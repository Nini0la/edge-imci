"""Canonical training records and model-specific serialization boundaries."""

from edge_imci.training.dataset_policy import (
    DATASET_POLICY_ID,
    SPLIT_POLICY_ID,
    parent_semantic_partition,
)
from edge_imci.training.structured_extraction import (
    STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID,
    build_structured_extraction_record,
    format_structured_extraction_messages,
    validate_structured_extraction_record,
)

__all__ = [
    "DATASET_POLICY_ID",
    "SPLIT_POLICY_ID",
    "STRUCTURED_EXTRACTION_RECORD_SCHEMA_ID",
    "build_structured_extraction_record",
    "format_structured_extraction_messages",
    "parent_semantic_partition",
    "validate_structured_extraction_record",
]
