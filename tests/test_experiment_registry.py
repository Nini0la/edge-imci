from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from edge_imci.experiments.registry import (
    DEFAULT_BRANCH_PATH,
    DEFAULT_MATRIX_PATH,
    SCHEMA_DIR,
    ExperimentRegistry,
    load_json_object,
    render_matrix_yaml,
    sync_matrix_yaml,
)


def _experiment(**overrides):
    value = {
        "experiment_id": "fake-ready-v1",
        "definition_version": "1.0.0",
        "experiment_type": "SYNTHETIC_GENERATION",
        "priority": "CORE",
        "status": "READY",
        "hypothesis": "Fixture-only metadata can exercise the registry.",
        "decision_question": "Does the fixture validate?",
        "branch_id": "fake-core",
        "prerequisites": [],
        "branch_trigger": None,
        "material_configuration": {"factor": "A"},
        "reproducibility": {"required_reference_kinds": [], "references": [], "unresolved_inputs": []},
        "evidence": [
            {
                "evidence_id": "fake_metric",
                "evidence_class": "SCIENTIFIC",
                "applicability": "APPLICABLE",
                "artifact_ref": None,
            }
        ],
        "run_ids": [],
    }
    value.update(overrides)
    return value


def fake_registry(tmp_path: Path, experiment: dict | None = None) -> ExperimentRegistry:
    matrix = {
        "schema_version": "1.0.0",
        "registry_id": "fake-registry-v1",
        "experiments": [experiment or _experiment()],
    }
    branches = {
        "schema_version": "1.0.0",
        "campaign_id": "fake-campaign-v1",
        "branches": [
            {
                "branch_id": "fake-core",
                "title": "Fake core",
                "priority": "CORE",
                "critical_path": True,
                "state": "OPEN",
                "evidence_trigger": "Fixture exists",
                "prerequisites": [],
                "expected_comparison": "Fake A versus fake B",
                "experiment_ids": [(experiment or matrix["experiments"][0])["experiment_id"]],
            }
        ],
    }
    matrix_path = tmp_path / "matrix.json"
    branch_path = tmp_path / "branches.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    branch_path.write_text(json.dumps(branches), encoding="utf-8")
    return ExperimentRegistry(matrix_path, branch_path, repo_root=tmp_path, schema_dir=SCHEMA_DIR)


def test_current_registry_and_campaign_encode_required_priority_decisions() -> None:
    registry = ExperimentRegistry()
    registry.validate()
    branches = {item["branch_id"]: item for item in registry.branches["branches"]}

    assert branches["qwen3-0.6b-sft-v1"]["priority"] == "CORE"
    assert branches["qwen3-0.6b-sft-v1"]["state"] == "SELECTED"
    assert "Modal" in branches["qwen3-0.6b-sft-v1"]["title"]
    assert branches["qwen3-1.7b-sft-v1"]["priority"] == "CONDITIONAL"
    assert branches["qwen3-1.7b-sft-v1"]["state"] == "CLOSED"
    assert branches["fast-standard-api-generation"]["critical_path"] is True
    assert branches["azure-batch-scale"]["priority"] == "CONDITIONAL"
    assert branches["azure-batch-scale"]["state"] == "DORMANT"
    assert branches["quantization"]["evidence_trigger"].startswith("Baseline target profile")
    assert branches["lundin-external"]["priority"] == "OPTIONAL"
    assert branches["lundin-external"]["critical_path"] is False
    statuses = {
        item["experiment_id"]: item["status"]
        for item in registry.matrix["experiments"]
    }
    assert {
        experiment_id
        for experiment_id, status in statuses.items()
        if status == "SUPERSEDED"
    } == {
        "qwen3-1.7b-base-holistic-baseline-v1",
        "qwen3-1.7b-sft-v1-modal",
        "qwen3-1.7b-sft-v1-classification-eval",
        "qwen3-1.7b-sft-v1-management-eval",
        "qwen3-1.7b-sft-v1-completeness-eval",
        "qwen3-1.7b-sft-v1-urgent-incomplete-eval",
        "qwen3-0.6b-lower-bound-v1",
    }
    assert all(
        status in {"PLANNED", "READY", "COMPLETE", "SUPERSEDED"}
        for status in statuses.values()
    )
    assert statuses["qwen3-0.6b-structured-extraction-sft-v1-modal"] == "COMPLETE"
    assert statuses["qwen3-1.7b-structured-extraction-sft-v1-modal"] == "COMPLETE"


def test_yaml_mirror_is_deterministic_and_semantically_equal(tmp_path: Path) -> None:
    canonical = load_json_object(DEFAULT_MATRIX_PATH)
    output = tmp_path / "matrix.yaml"

    sync_matrix_yaml(DEFAULT_MATRIX_PATH, output)

    assert yaml.safe_load(output.read_text(encoding="utf-8")) == canonical
    assert output.read_text(encoding="utf-8") == render_matrix_yaml(canonical)


def test_registry_rejects_duplicate_ids_and_invalid_enumerations(tmp_path: Path) -> None:
    registry = fake_registry(tmp_path)
    duplicate = deepcopy(registry.matrix["experiments"][0])
    registry.matrix["experiments"].append(duplicate)
    with pytest.raises(ValueError, match="unique"):
        registry.validate()

    registry = fake_registry(tmp_path, _experiment(priority="URGENT"))
    with pytest.raises(ValueError, match="schema validation"):
        registry.validate()


def test_ready_rejects_unresolved_reproducibility_inputs(tmp_path: Path) -> None:
    experiment = _experiment()
    experiment["reproducibility"] = {
        "required_reference_kinds": ["MODEL"],
        "references": [],
        "unresolved_inputs": ["model snapshot"],
    }
    registry = fake_registry(tmp_path, experiment)

    with pytest.raises(ValueError, match="unresolved reproducibility"):
        registry.validate()


def test_explicit_applicability_and_safe_references(tmp_path: Path) -> None:
    experiment = _experiment()
    experiment["evidence"][0]["applicability"] = "NOT_APPLICABLE"
    experiment["evidence"][0]["artifact_ref"] = "missing.json"
    with pytest.raises(ValueError, match="not-applicable"):
        fake_registry(tmp_path, experiment).validate()

    experiment = _experiment()
    experiment["evidence"][0]["artifact_ref"] = "../escape.json"
    with pytest.raises(ValueError, match="escapes root"):
        fake_registry(tmp_path, experiment).validate()


def test_committed_yaml_is_current() -> None:
    canonical = load_json_object(DEFAULT_MATRIX_PATH)
    mirror = DEFAULT_MATRIX_PATH.with_suffix(".yaml")
    assert yaml.safe_load(mirror.read_text(encoding="utf-8")) == canonical
    assert mirror.read_text(encoding="utf-8") == render_matrix_yaml(canonical)
    assert DEFAULT_BRANCH_PATH.exists()
