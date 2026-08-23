from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language import load_language_calibration
from edge_imci.generation.holistic_language_full import (
    ACTION_SENTENCES,
    ACQUISITION_SPECS,
    CLASSIFICATION_LABELS,
    DEFAULT_GRAMMAR_PATH,
    DEFAULT_GRAMMAR_YAML_PATH,
    DEFAULT_LANGUAGE_PATH,
    DEFAULT_LANGUAGE_YAML_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REVIEW_PATH,
    FULL_LANGUAGE_SUITE_ID,
    PRE_FORMAT_LANGUAGE_SHA256,
    RESPONSE_GRAMMAR_ID,
    SEMANTIC_CASES_SHA256,
    build_full_language_suite,
    load_full_language_suite,
    load_response_grammar,
    render_assistant,
)


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return load_full_language_suite()


def _by_id(records: list[dict]) -> dict[str, dict]:
    return {record["golden_case_id"]: record for record in records}


def test_full_language_suite_covers_all_78_frozen_semantic_cases(records: list[dict]) -> None:
    semantics = load_holistic_golden_suite()
    assert len(records) == len(semantics) == 78
    assert [record["golden_case_id"] for record in records] == [
        record["golden_case_id"] for record in semantics
    ]
    assert len({record["rendering_id"] for record in records}) == 78


def test_frozen_anchor_inputs_and_alignments_are_preserved_while_all_records_return_to_review(
    records: list[dict],
) -> None:
    anchors = {record["golden_case_id"]: record for record in load_language_calibration()}
    full = _by_id(records)
    assert len(anchors) == 16
    for case_id, anchor in anchors.items():
        assert full[case_id]["conversation"][0] == anchor["conversation"][0]
        assert full[case_id]["alignment"] == anchor["alignment"]
        assert "Format-remediated from frozen calibration v1" in full[case_id]["review"][
            "notes"
        ]
    assert all(record["status"] == "DRAFT_FOR_HUMAN_REVIEW" for record in records)
    assert all(record["review"]["semantic_faithfulness"] == "PENDING" for record in records)
    assert all(record["review"]["interaction_quality"] == "PENDING" for record in records)
    assert all(record["review"]["phc_suitability"] == "PENDING" for record in records)


def test_full_suite_is_deterministic_and_yaml_is_a_mirror(records: list[dict]) -> None:
    assert records == build_full_language_suite()
    assert yaml.safe_load(DEFAULT_LANGUAGE_YAML_PATH.read_text(encoding="utf-8")) == records


def test_every_frozen_classification_action_and_missing_field_has_language_support() -> None:
    semantics = load_holistic_golden_suite()
    classifications = set()
    actions = set()
    missing = set()
    for record in semantics:
        if record["expected"]["kind"] == "SCHEMA_REJECTION":
            continue
        evaluation = record["expected"]["evaluation"]
        classifications.update(item["classification"] for item in evaluation["final_classifications"])
        actions.update(evaluation["final_actions"] or evaluation["urgent_actions"])
        missing.update(
            field
            for fields in evaluation["missing_elements"].values()
            for field in fields
        )
    assert classifications == set(CLASSIFICATION_LABELS)
    assert actions <= set(ACTION_SENTENCES)
    assert missing <= set(ACQUISITION_SPECS)


def test_manifest_keeps_unreviewed_full_layer_out_of_downstream_uses(records: list[dict]) -> None:
    manifest = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["suite_id"] == FULL_LANGUAGE_SUITE_ID
    assert manifest["lifecycle_status"] == "PROPOSED_FOR_REVIEW"
    assert manifest["case_count"] == len(records)
    assert manifest["frozen_calibration_source_count"] == 16
    assert manifest["format_remediated_anchor_count"] == 16
    assert manifest["draft_rendering_count"] == 78
    assert manifest["artifact_pins"]["response_grammar_id"] == RESPONSE_GRAMMAR_ID
    assert manifest["pre_format_review"] == {
        "report": "docs/product_holistic_golden_language_review_v1_report.md",
        "language_renderings_sha256": PRE_FORMAT_LANGUAGE_SHA256,
        "result": "PASS_WITH_MINOR_FORMATTING_NOTES",
        "findings_addressed": ["LGR-FR-001", "LGR-FR-002"],
    }
    assert manifest["review_status"] == "78_FORMAT_NORMALIZED_RENDERINGS_PENDING_REVIEW"
    assert manifest["semantic_source"]["sha256"] == SEMANTIC_CASES_SHA256
    assert manifest["language_renderings_sha256"] == hashlib.sha256(
        DEFAULT_LANGUAGE_PATH.read_bytes()
    ).hexdigest()
    assert manifest["eligibility"] == {
        "COMPONENT_VALIDATION": True,
        "DOMAIN_REVIEW": True,
        "HOLISTIC_GENERATION": False,
        "PRODUCT_EVALUATION": False,
        "TEACHER_BAKEOFF": False,
        "TRAINING": False,
    }


@pytest.mark.parametrize(
    "use",
    [
        CorpusUse.HOLISTIC_GENERATION,
        CorpusUse.PRODUCT_EVALUATION,
        CorpusUse.TEACHER_BAKEOFF,
        CorpusUse.TRAINING,
    ],
)
def test_full_language_draft_rejects_premature_use(use: CorpusUse) -> None:
    with pytest.raises(ValueError, match="is not eligible"):
        load_full_language_suite(corpus_use=use)


def test_full_language_draft_allows_review_and_component_validation() -> None:
    assert load_full_language_suite(corpus_use=CorpusUse.DOMAIN_REVIEW)
    assert load_full_language_suite(corpus_use=CorpusUse.COMPONENT_VALIDATION)


def test_state_counts_and_urgent_leading_behavior_are_preserved(records: list[dict]) -> None:
    assert sum(record["alignment"]["expected_state"] == "COMPLETE" for record in records) == 60
    assert sum(record["alignment"]["expected_state"] == "INCOMPLETE" for record in records) == 16
    assert sum(record["alignment"]["expected_state"] == "SCHEMA_REJECTION" for record in records) == 2
    for record in records:
        assistant = record["conversation"][1]["content"]
        if record["alignment"]["urgent_action_required"] is True:
            assert assistant.startswith("URGENT:")
        if record["alignment"]["expected_state"] == "INCOMPLETE":
            assert record["alignment"]["final_synthesis_authorized"] is False
            assert not record["alignment"]["classifications_covered"]


def test_every_assistant_response_uses_the_deterministic_state_grammar(
    records: list[dict],
) -> None:
    semantics = {
        record["golden_case_id"]: record for record in load_holistic_golden_suite()
    }
    for record in records:
        semantic = semantics[record["golden_case_id"]]
        assert record["conversation"][1]["content"] == render_assistant(semantic)
        assistant = record["conversation"][1]["content"]
        state = record["alignment"]["expected_state"]
        urgent = record["alignment"]["urgent_action_required"]
        if state == "COMPLETE":
            assert "Classifications:\n- " in assistant
            expected_heading = "Immediate management:\n- " if urgent else "Management:\n- "
            assert expected_heading in assistant
        elif state == "INCOMPLETE":
            assert "ASSESSMENT INCOMPLETE" in assistant
            expected_heading = "Information still needed:\n- " if urgent else "Information needed:\n- "
            assert expected_heading in assistant
        else:
            assert assistant.startswith("OUTSIDE SUPPORTED SCOPE")


def test_response_grammar_is_approved_versioned_and_mirrored() -> None:
    grammar = load_response_grammar()
    assert grammar["grammar_id"] == RESPONSE_GRAMMAR_ID
    assert grammar["pre_format_review"]["language_renderings_sha256"] == (
        PRE_FORMAT_LANGUAGE_SHA256
    )
    assert grammar["change_control"]["clinical_semantics_changed"] is False
    assert grammar["change_control"]["semantic_alignment_changed"] is False
    assert grammar["change_control"]["full_language_records_return_to_review"] is True
    assert yaml.safe_load(DEFAULT_GRAMMAR_YAML_PATH.read_text(encoding="utf-8")) == grammar
    assert json.loads(DEFAULT_GRAMMAR_PATH.read_text(encoding="utf-8")) == grammar


def test_user_facing_full_language_does_not_leak_internal_ids(records: list[dict]) -> None:
    for record in records:
        for turn in record["conversation"]:
            assert "IMCI-MSC-" not in turn["content"]
            assert not any(action in turn["content"] for action in ACTION_SENTENCES)


def test_review_package_contains_all_cases_and_correct_lifecycle_counts(records: list[dict]) -> None:
    review = DEFAULT_REVIEW_PATH.read_text(encoding="utf-8")
    assert "not training data" in review.lower()
    for record in records:
        assert f"## {record['golden_case_id']}" in review
    assert review.count("**Lifecycle:** `FROZEN`") == 0
    assert review.count("**Lifecycle:** `DRAFT_FOR_HUMAN_REVIEW`") == 78
    assert RESPONSE_GRAMMAR_ID in review
    assert PRE_FORMAT_LANGUAGE_SHA256 in review
    assert not Path("data/train").exists()


def test_scope_rejections_are_clear_and_do_not_synthesize_management(records: list[dict]) -> None:
    by_id = _by_id(records)
    for case_id in ("hpg-077-out-of-scope-age-1", "hpg-078-out-of-scope-age-60"):
        assistant = by_id[case_id]["conversation"][1]["content"].lower()
        assert assistant.startswith("outside supported scope")
        assert "cannot provide" in assistant
        assert "classification" in assistant
        assert "management" in assistant
