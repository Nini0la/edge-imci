from __future__ import annotations

from pathlib import Path

from edge_imci.experiments.provenance import hash_file
from edge_imci.experiments.registry import (
    ExperimentRegistry,
    load_json_object,
    validate_against_schema,
)
from edge_imci.inference.modal_structured_extraction import (
    MODEL_WEIGHTS_SHA256,
    TRAINING_RUN_ID,
)

ROOT = Path(__file__).resolve().parents[1]
DESIGNATION_PATH = (
    ROOT / "configs/deployment/qwen3_0_6b_provisional_product_candidate_v1.json"
)
DESIGNATION_SCHEMA_PATH = (
    ROOT / "configs/deployment/provisional_product_candidate_v1.schema.json"
)


def test_provisional_candidate_is_pinned_across_product_and_adtc_paths() -> None:
    designation = load_json_object(DESIGNATION_PATH)
    validate_against_schema(designation, DESIGNATION_SCHEMA_PATH)
    candidate = designation["candidate"]

    assert designation["status"] == (
        "PROVISIONAL_PRODUCT_AND_SUBMISSION_PLACEHOLDER"
    )
    assert all(
        designation["roles"][role]
        for role in (
            "current_product_model",
            "submission_placeholder",
            "adtc_profiling_source",
        )
    )
    assert candidate["training_run_id"] == TRAINING_RUN_ID
    assert candidate["model_weights_sha256"] == MODEL_WEIGHTS_SHA256

    registry = ExperimentRegistry()
    registry.validate()
    target_profile = registry.get("selected-artifact-target-profile-v1")
    adtc_profile = registry.get("selected-artifact-official-adtc-v1")
    for experiment in (target_profile, adtc_profile):
        assert experiment["material_configuration"]["source_training_run_id"] == (
            TRAINING_RUN_ID
        )
        assert experiment["material_configuration"][
            "source_model_weights_sha256"
        ] == MODEL_WEIGHTS_SHA256

    branches = {item["branch_id"]: item for item in registry.branches["branches"]}
    assert branches["target-hardware-profile"]["state"] == "SELECTED"
    assert branches["official-adtc-final"]["state"] == "SELECTED"


def test_designation_evidence_and_own_digest_are_current() -> None:
    designation = load_json_object(DESIGNATION_PATH)
    for path_key, digest_key in (
        ("reserved_test_report", "reserved_test_report_sha256"),
        ("posthoc_base_report", "posthoc_base_report_sha256"),
    ):
        report = load_json_object(ROOT / designation["evidence"][path_key])
        assert report["report_sha256"] == designation["evidence"][digest_key]

    designation_sha256 = hash_file(DESIGNATION_PATH)[0]
    registry = ExperimentRegistry()
    for experiment_id in (
        "selected-artifact-target-profile-v1",
        "selected-artifact-official-adtc-v1",
    ):
        experiment = registry.get(experiment_id)
        reference = next(
            item
            for item in experiment["reproducibility"]["references"]
            if item["reference_id"] == "qwen3-0.6b-provisional-product-candidate-v1"
        )
        assert reference["sha256"] == designation_sha256
