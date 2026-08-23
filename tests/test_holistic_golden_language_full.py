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
    DEFAULT_FULL_APPROVAL_PATH,
    DEFAULT_FULL_APPROVAL_YAML_PATH,
    DEFAULT_LANGUAGE_PATH,
    DEFAULT_LANGUAGE_YAML_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REVIEW_PATH,
    FULL_LANGUAGE_SUITE_ID,
    FULL_LANGUAGE_APPROVAL_ID,
    APPROVED_REMEDIATED_LANGUAGE_SHA256,
    APPROVED_RESPONSE_GRAMMAR_SHA256,
    PRE_FORMAT_LANGUAGE_SHA256,
    PRE_REMEDIATION_LANGUAGE_SHA256,
    RESPONSE_GRAMMAR_ID,
    SEMANTIC_CASES_SHA256,
    build_full_language_suite,
    load_full_language_approval,
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


def test_frozen_anchor_inputs_and_alignments_are_preserved_in_the_approved_full_layer(
    records: list[dict],
) -> None:
    anchors = {record["golden_case_id"]: record for record in load_language_calibration()}
    full = _by_id(records)
    assert len(anchors) == 16
    for case_id, anchor in anchors.items():
        assert full[case_id]["conversation"][0] == anchor["conversation"][0]
        assert full[case_id]["alignment"] == anchor["alignment"]
        assert "Project-owner approved" in full[case_id]["review"]["notes"]
    assert all(record["status"] == "FROZEN" for record in records)
    assert all(
        record["review"]["semantic_faithfulness"] == "APPROVED_FOR_HACKATHON_SCOPE"
        for record in records
    )
    assert all(
        record["review"]["interaction_quality"] == "APPROVED_FOR_HACKATHON_SCOPE"
        for record in records
    )
    assert all(
        record["review"]["phc_suitability"]
        == "PROJECT_OWNER_APPROVED_FOR_HACKATHON_DEMO_NOT_FIELD_VALIDATED"
        for record in records
    )
    assert all(record["review"]["reviewer"] == "PROJECT_OWNER" for record in records)


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


def test_manifest_freezes_the_approved_full_layer_and_opens_controlled_next_stages(
    records: list[dict],
) -> None:
    manifest = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["suite_id"] == FULL_LANGUAGE_SUITE_ID
    assert manifest["lifecycle_status"] == "FROZEN"
    assert manifest["case_count"] == len(records)
    assert manifest["frozen_calibration_source_count"] == 16
    assert manifest["format_remediated_anchor_count"] == 16
    assert manifest["draft_rendering_count"] == 0
    assert manifest["frozen_rendering_count"] == 78
    assert manifest["artifact_pins"]["response_grammar_id"] == RESPONSE_GRAMMAR_ID
    assert manifest["artifact_pins"]["full_language_approval_id"] == FULL_LANGUAGE_APPROVAL_ID
    assert manifest["pre_format_review"] == {
        "report": "docs/product_holistic_golden_language_review_v1_report.md",
        "language_renderings_sha256": PRE_FORMAT_LANGUAGE_SHA256,
        "result": "PASS_WITH_MINOR_FORMATTING_NOTES",
        "findings_addressed": ["LGR-FR-001", "LGR-FR-002"],
    }
    assert manifest["format_re_review"] == {
        "report": "docs/product_holistic_golden_language_format_re_review_v1.md",
        "language_renderings_sha256": PRE_REMEDIATION_LANGUAGE_SHA256,
        "result": "READY_AFTER_LANGUAGE_REMEDIATION",
        "findings_addressed": ["LGR-GR-001", "LGR-GR-002", "LGR-GR-003", "LGR-GR-004"],
    }
    assert manifest["review_status"] == "PROJECT_OWNER_APPROVED_AND_FROZEN_FOR_HACKATHON_SCOPE"
    assert manifest["semantic_source"]["sha256"] == SEMANTIC_CASES_SHA256
    assert manifest["language_renderings_sha256"] == hashlib.sha256(
        DEFAULT_LANGUAGE_PATH.read_bytes()
    ).hexdigest()
    assert manifest["approval"] == {
        "approval_id": FULL_LANGUAGE_APPROVAL_ID,
        "reviewed_language_renderings_sha256": APPROVED_REMEDIATED_LANGUAGE_SHA256,
        "frozen_language_renderings_sha256": manifest["language_renderings_sha256"],
        "approval_record": "docs/product_holistic_golden_language_full_approval_v1.md",
        "response_grammar_sha256": APPROVED_RESPONSE_GRAMMAR_SHA256,
        "qualified_phc_field_validation_completed": False,
    }
    assert manifest["eligibility"] == {
        "COMPONENT_VALIDATION": True,
        "DOMAIN_REVIEW": True,
        "HOLISTIC_GENERATION": True,
        "PRODUCT_EVALUATION": True,
        "TEACHER_BAKEOFF": True,
        "TRAINING": False,
    }


def test_frozen_full_language_still_rejects_direct_training_use() -> None:
    with pytest.raises(ValueError, match="is not eligible"):
        load_full_language_suite(corpus_use=CorpusUse.TRAINING)


@pytest.mark.parametrize(
    "use",
    [
        CorpusUse.DOMAIN_REVIEW,
        CorpusUse.COMPONENT_VALIDATION,
        CorpusUse.HOLISTIC_GENERATION,
        CorpusUse.PRODUCT_EVALUATION,
        CorpusUse.TEACHER_BAKEOFF,
    ],
)
def test_frozen_full_language_allows_approved_uses(use: CorpusUse) -> None:
    assert load_full_language_suite(corpus_use=use)


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
    assert grammar["format_re_review"]["language_renderings_sha256"] == (
        PRE_REMEDIATION_LANGUAGE_SHA256
    )
    assert set(grammar["presentation_order"]["action_priority"]) == set(ACTION_SENTENCES)
    assert grammar["change_control"]["clinical_semantics_changed"] is False
    assert grammar["change_control"]["semantic_alignment_changed"] is False
    assert grammar["change_control"]["full_language_records_return_to_review"] is True
    assert yaml.safe_load(DEFAULT_GRAMMAR_YAML_PATH.read_text(encoding="utf-8")) == grammar
    assert json.loads(DEFAULT_GRAMMAR_PATH.read_text(encoding="utf-8")) == grammar


def test_full_language_approval_is_pinned_and_mirrored() -> None:
    approval = load_full_language_approval()
    assert approval["approval_id"] == FULL_LANGUAGE_APPROVAL_ID
    assert approval["reviewed_language_renderings_sha256"] == (
        APPROVED_REMEDIATED_LANGUAGE_SHA256
    )
    assert approval["response_grammar_sha256"] == hashlib.sha256(
        DEFAULT_GRAMMAR_PATH.read_bytes()
    ).hexdigest()
    assert approval["frozen_language_renderings_sha256"] == hashlib.sha256(
        DEFAULT_LANGUAGE_PATH.read_bytes()
    ).hexdigest()
    assert yaml.safe_load(DEFAULT_FULL_APPROVAL_YAML_PATH.read_text(encoding="utf-8")) == approval
    assert json.loads(DEFAULT_FULL_APPROVAL_PATH.read_text(encoding="utf-8")) == approval


def test_remediation_orders_actions_and_acquisitions_without_changing_semantics(
    records: list[dict],
) -> None:
    by_id = _by_id(records)

    convulsing = by_id["hpg-070-cross-multiple-urgent"]["conversation"][1]["content"]
    assert convulsing.index("Give diazepam") < convulsing.index(
        "Complete the remaining assessment quickly"
    )

    pneumonia = by_id["hpg-008-resp-age-2-rate-50"]["conversation"][1]["content"]
    assert pneumonia.index("Give oral amoxicillin") < pneumonia.index(
        "Advise the caregiver"
    ) < pneumonia.index("Follow up")

    severe_persistent = by_id["hpg-034-diarrhoea-severe-persistent"]["conversation"][1]["content"]
    assert severe_persistent.index("Treat dehydration before referral") < severe_persistent.index(
        "Refer the child to hospital"
    )

    bronchodilator = by_id["hpg-022-resp-trial-outstanding"]["conversation"][1]["content"]
    ordered_phrases = (
        "Complete the indicated rapid-acting inhaled bronchodilator trial",
        "Confirm that the child is calm",
        "count breaths for one full minute",
        "Measure and report the post-bronchodilator respiratory rate",
        "Reassess chest indrawing",
    )
    assert [bronchodilator.index(phrase) for phrase in ordered_phrases] == sorted(
        bronchodilator.index(phrase) for phrase in ordered_phrases
    )

    multi = by_id["hpg-072-incomplete-multiple-groups"]["conversation"][1]["content"]
    ordered_phrases = (
        "vomits everything",
        "respiratory rate",
        "malaria-risk category",
        "ear problem",
    )
    assert [multi.index(phrase) for phrase in ordered_phrases] == sorted(
        multi.index(phrase) for phrase in ordered_phrases
    )


def test_remediation_restores_referral_qualifier_and_natural_conflict_language(
    records: list[dict],
) -> None:
    by_id = _by_id(records)
    referral = by_id["hpg-014-resp-chest-hiv-positive"]["conversation"][1]["content"]
    assert "referral, not urgent referral" in referral

    conflict = by_id["hpg-075-contradiction-drinking"]["conversation"][1]["content"]
    assert "UNABLE observed" not in conflict
    assert "general danger-sign assessment says the child can drink or breastfeed" in conflict


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
    assert review.count("**Lifecycle:** `FROZEN`") == 78
    assert review.count("**Lifecycle:** `DRAFT_FOR_HUMAN_REVIEW`") == 0
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
