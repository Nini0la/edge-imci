from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_golden import (
    DEFAULT_JSONL_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_APPROVAL_PATH,
    DEFAULT_APPROVAL_YAML_PATH,
    DEFAULT_REVIEW_PATH,
    DEFAULT_SCOPE_DISPOSITIONS_PATH,
    DEFAULT_SCOPE_DISPOSITIONS_YAML_PATH,
    DEFAULT_YAML_PATH,
    DECISION_SET_ID,
    APPROVAL_ID,
    APPROVED_REVIEWED_SEMANTIC_SHA256,
    OXYGEN_REFERRAL_DISPOSITION_ID,
    RECORD_SCHEMA_ID,
    SUITE_ID,
    SCOPE_DISPOSITION_SET_ID,
    VALIDATOR_ID,
    build_holistic_golden_suite,
    load_holistic_golden_suite,
    load_golden_approval,
    load_scope_dispositions,
    validate_holistic_golden_record,
)
from edge_imci.information_policy.holistic_artifacts import load_holistic_artifacts
from edge_imci.schemas.holistic import HolisticClassification
from edge_imci.schemas.trajectory import CorpusRole


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return load_holistic_golden_suite()


def _by_id(records: list[dict]) -> dict[str, dict]:
    return {record["golden_case_id"]: record for record in records}


def test_suite_is_review_sized_unique_and_product_specific(records: list[dict]) -> None:
    assert len(records) == 78
    assert 50 <= len(records) <= 100
    assert len({record["golden_case_id"] for record in records}) == len(records)
    assert all(record["suite_id"] == SUITE_ID for record in records)
    assert all(record["record_schema_id"] == RECORD_SCHEMA_ID for record in records)
    assert all(record["corpus_role"] == CorpusRole.HOLISTIC_PRODUCT_GOLDEN.value for record in records)
    assert all(record["status"] == "FROZEN" for record in records)
    assert all(
        record["review_flags"] == ["HUMAN_DOMAIN_APPROVED", "SEMANTICS_FROZEN"]
        for record in records
    )


def test_committed_jsonl_and_yaml_are_deterministic_mirrors(records: list[dict]) -> None:
    assert records == build_holistic_golden_suite()
    assert yaml.safe_load(DEFAULT_YAML_PATH.read_text(encoding="utf-8")) == records


def test_every_record_recomputes_or_rejects_exactly(records: list[dict]) -> None:
    for record in records:
        validate_holistic_golden_record(record)


def test_all_approved_review_decisions_are_represented(records: list[dict]) -> None:
    represented = {
        question_id
        for record in records
        for question_id in record["provenance"]["review_decision_ids"]
    }
    approved = {
        item["question_id"]
        for item in load_holistic_artifacts().decisions["decisions"]
    }
    assert represented == approved


def test_review_decision_applicability_is_exact_for_all_thirteen_decisions(
    records: list[dict],
) -> None:
    actual: dict[str, set[str]] = {
        item["question_id"]: set()
        for item in load_holistic_artifacts().decisions["decisions"]
    }
    for record in records:
        for question_id in record["provenance"]["review_decision_ids"]:
            actual[question_id].add(record["golden_case_id"])

    expected = {
        "IP-CQ-001": {
            "hpg-002-danger-unable-to-drink-or-breastfeed",
            "hpg-003-danger-vomits-everything",
            "hpg-004-danger-had-convulsions",
            "hpg-005-danger-lethargic-or-unconscious",
            "hpg-006-danger-convulsing-now",
            "hpg-037-diarrhoea-positive-drinking-reuse",
            "hpg-070-cross-multiple-urgent",
            "hpg-073-incomplete-known-urgent",
            "hpg-076-complete-danger-plus-all-pathways",
        },
        "IP-CQ-002": {
            "hpg-037-diarrhoea-positive-drinking-reuse",
            "hpg-038-diarrhoea-negative-does-not-reuse",
            "hpg-075-contradiction-drinking",
        },
        "IP-CQ-003": {
            record["golden_case_id"]
            for record in records
            if record["input"]["encounter"].get("patient_facts", {}).get(
                "has_cough_or_difficult_breathing"
            )
            is True
        },
        "IP-CQ-004": {
            "hpg-034-diarrhoea-severe-persistent",
            "hpg-055-fever-severe-measles-cornea",
            "hpg-069-cross-urgent-dehydration-ear",
            "hpg-070-cross-multiple-urgent",
            "hpg-076-complete-danger-plus-all-pathways",
        },
        "MSC-CQ-SCOPE-001": {
            "hpg-001-all-negative",
            "hpg-071-incomplete-entry-unknown",
            "hpg-072-incomplete-multiple-groups",
            "hpg-073-incomplete-known-urgent",
            "hpg-074-incomplete-internal-classification-withheld",
            "hpg-077-out-of-scope-age-1",
            "hpg-078-out-of-scope-age-60",
        },
        "MSC-CQ-RESP-001": {
            "hpg-020-resp-post-bronchodilator-improved",
            "hpg-021-resp-post-bronchodilator-fast",
            "hpg-022-resp-trial-outstanding",
        },
        "MSC-CQ-RESP-002": {"hpg-014-resp-chest-hiv-positive"},
        "MSC-CQ-DIARRHOEA-001": {
            "hpg-030-diarrhoea-severe-age-24-no-cholera",
            "hpg-031-diarrhoea-severe-age-24-cholera",
            "hpg-040-diarrhoea-cholera-context-unknown",
        },
        "MSC-CQ-REASSESS-001": {
            "hpg-028-diarrhoea-some-dehydration",
            "hpg-029-diarrhoea-severe-plan-c-under-24m",
            "hpg-030-diarrhoea-severe-age-24-no-cholera",
            "hpg-031-diarrhoea-severe-age-24-cholera",
            "hpg-034-diarrhoea-severe-persistent",
            "hpg-040-diarrhoea-cholera-context-unknown",
        },
        "MSC-CQ-FEVER-001": {
            record["golden_case_id"]
            for record in records
            if record["input"]["encounter"].get("patient_facts", {}).get("has_fever")
            is True
        },
        "MSC-CQ-FEVER-002": {"hpg-052-fever-identified-bacterial-cause"},
        "MSC-CQ-FEVER-003": {
            record["golden_case_id"]
            for record in records
            if record["input"]["encounter"].get("patient_facts", {}).get("has_fever")
            is True
        },
        "MSC-CQ-EAR-001": {"hpg-065-ear-observed-pus-no-history"},
    }
    assert actual == expected
    assert all(case_ids for case_ids in actual.values())
    assert all(len(case_ids) < len(records) for case_ids in actual.values())


def test_coverage_tags_are_unique_within_each_case(records: list[dict]) -> None:
    for record in records:
        assert len(record["coverage"]) == len(set(record["coverage"]))


def test_oxygen_referral_disposition_provenance_is_exact(records: list[dict]) -> None:
    carrying = {
        record["golden_case_id"]
        for record in records
        if OXYGEN_REFERRAL_DISPOSITION_ID
        in record["provenance"]["product_policy_disposition_ids"]
    }
    assert carrying == {"hpg-016-resp-oximeter-89-9"}


def test_non_firing_requirement_and_scope_provenance_is_explicit(records: list[dict]) -> None:
    for record in records:
        citations = record["provenance"]["requirement_citations"]
        expected = record["expected"]
        if expected["kind"] == "SCHEMA_REJECTION":
            assert any(item["provenance_type"] == "SCOPE_BOUNDARY" for item in citations)
            continue
        evaluation = expected["evaluation"]
        missing = {
            field
            for fields in evaluation["missing_elements"].values()
            for field in fields
        }
        cited_fields = {field for item in citations for field in item["fields"]}
        assert missing <= cited_fields
        if evaluation["contradictions"]:
            assert any(
                item["provenance_type"] == "EVIDENCE_VALIDITY_REQUIREMENT"
                for item in citations
            )
        if not evaluation["supported_encounter_complete"]:
            assert citations
    assert _by_id(records)["hpg-001-all-negative"]["provenance"][
        "requirement_citations"
    ]


def test_manifest_pins_approval_lifecycle_hash_and_eligibility(records: list[dict]) -> None:
    manifest = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["suite_id"] == SUITE_ID
    assert manifest["lifecycle_status"] == "FROZEN"
    assert manifest["case_count"] == len(records)
    assert manifest["artifact_pins"]["review_decision_set_id"] == DECISION_SET_ID
    assert (
        manifest["artifact_pins"]["oxygen_referral_disposition_id"]
        == OXYGEN_REFERRAL_DISPOSITION_ID
    )
    assert manifest["artifact_pins"]["scope_disposition_set_id"] == SCOPE_DISPOSITION_SET_ID
    assert manifest["artifact_pins"]["validator_id"] == VALIDATOR_ID
    assert manifest["artifact_pins"]["approval_id"] == APPROVAL_ID
    assert manifest["semantic_cases_sha256"] == hashlib.sha256(DEFAULT_JSONL_PATH.read_bytes()).hexdigest()
    assert manifest["unknown_semantics"] == {
        "omitted_is_unknown": True,
        "unknown_is_negative": False,
    }
    assert manifest["eligibility"]["DOMAIN_REVIEW"] is True
    for use in ("HOLISTIC_GENERATION", "PRODUCT_EVALUATION", "TEACHER_BAKEOFF"):
        assert manifest["eligibility"][use] is True
    assert manifest["eligibility"]["TRAINING"] is False
    assert manifest["freeze_blockers"] == []
    assert manifest["review_required_before_freeze"] is False
    assert manifest["approval"] == {
        "approval_id": APPROVAL_ID,
        "reviewed_semantic_cases_sha256": APPROVED_REVIEWED_SEMANTIC_SHA256,
        "frozen_semantic_cases_sha256": manifest["semantic_cases_sha256"],
        "approved_for_hackathon_scope": True,
    }


def test_frozen_suite_loader_still_rejects_direct_training_use() -> None:
    with pytest.raises(ValueError, match="is not eligible"):
        load_holistic_golden_suite(corpus_use=CorpusUse.TRAINING)


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
def test_frozen_suite_loader_allows_approved_uses(use: CorpusUse) -> None:
    assert load_holistic_golden_suite(corpus_use=use)


def test_every_encoded_classification_family_has_a_review_case(records: list[dict]) -> None:
    covered = {
        trace["classification"]
        for record in records
        if record["expected"]["kind"] == "HOLISTIC_EVALUATION"
        for trace in record["expected"]["evaluation"]["internal_classifications"]
    }
    assert covered == {classification.value for classification in HolisticClassification}


def test_required_semantic_families_are_explicitly_covered(records: list[dict]) -> None:
    tags = {tag for record in records for tag in record["coverage"]}
    assert {
        "complete",
        "low_severity",
        "simultaneous_classifications",
        "integrated_action_plan",
        "cross_pathway_action_dependency",
        "urgent_incomplete",
        "grouped_missing_elements",
        "explicit_negative_omission_twin",
        "bronchodilator_reassessment",
        "complete_post_reassessment",
        "plan_b",
        "plan_c",
        "malaria",
        "measles",
        "mastoiditis",
        "contradiction",
        "schema_rejection",
    } <= tags


def test_incomplete_cases_withhold_final_synthesis_but_keep_known_urgency(records: list[dict]) -> None:
    by_id = _by_id(records)
    urgent = by_id["hpg-073-incomplete-known-urgent"]["expected"]["evaluation"]
    assert urgent["supported_encounter_complete"] is False
    assert urgent["urgent_action_required"] is True
    assert urgent["urgent_actions"]
    assert urgent["final_classifications"] == []
    assert urgent["final_actions"] == []
    nonurgent = by_id["hpg-071-incomplete-entry-unknown"]["expected"]["evaluation"]
    assert nonurgent["urgent_action_required"] is False
    assert nonurgent["final_classifications"] == []
    assert nonurgent["final_actions"] == []


def test_severe_measles_source_treatments_remain_in_immediate_urgent_workflow(
    records: list[dict],
) -> None:
    evaluation = _by_id(records)["hpg-055-fever-severe-measles-cornea"]["expected"][
        "evaluation"
    ]
    required = {
        "GIVE_VITAMIN_A_TREATMENT",
        "GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC",
        "APPLY_TETRACYCLINE_EYE_OINTMENT",
        "URGENT_REFERRAL",
    }
    assert required <= set(evaluation["urgent_actions"])
    assert required <= set(evaluation["final_actions"])
    assert not required & set(evaluation["deferred_actions"])


def test_explicit_negative_and_omission_remain_distinct(records: list[dict]) -> None:
    by_id = _by_id(records)
    complete = by_id["hpg-001-all-negative"]["expected"]["evaluation"]
    omitted = by_id["hpg-071-incomplete-entry-unknown"]["expected"]["evaluation"]
    assert complete["supported_encounter_complete"] is True
    assert omitted["supported_encounter_complete"] is False
    assert "patient_facts.has_diarrhoea" in omitted["missing_elements"]["supported_encounter"]


def test_out_of_scope_cases_are_schema_rejections(records: list[dict]) -> None:
    rejected = [record for record in records if "out_of_scope" in record["coverage"]]
    assert len(rejected) == 2
    assert all(record["expected"]["kind"] == "SCHEMA_REJECTION" for record in rejected)


def test_later_plan_reassessment_gap_is_resolved_by_versioned_product_scope() -> None:
    manifest = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    artifact = load_scope_dispositions()
    assert manifest["known_coverage_gaps"] == []
    assert manifest["freeze_blockers"] == []
    assert manifest["scope_dispositions"] == artifact["dispositions"]
    disposition = artifact["dispositions"][0]
    assert disposition["gap_id"] == "HPG-GAP-REASSESS-001"
    assert disposition["status"] == "RESOLVED_BY_PRODUCT_SCOPE"
    assert disposition["rationale_type"] == "PRODUCT_SCOPE_DECISION"
    assert artifact["clinical_rule_change"] is False
    yaml_mirror = yaml.safe_load(DEFAULT_SCOPE_DISPOSITIONS_YAML_PATH.read_text(encoding="utf-8"))
    assert yaml_mirror == json.loads(DEFAULT_SCOPE_DISPOSITIONS_PATH.read_text(encoding="utf-8"))


def test_human_domain_approval_is_versioned_and_mirrored() -> None:
    approval = load_golden_approval()
    manifest = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert approval["approval_id"] == APPROVAL_ID
    assert approval["reviewed_semantic_cases_sha256"] == APPROVED_REVIEWED_SEMANTIC_SHA256
    assert approval["frozen_semantic_cases_sha256"] == manifest["semantic_cases_sha256"]
    assert approval["approval_basis"]["explicit_human_domain_disposition"] == "APPROVED"
    assert approval["freeze_transformation"]["semantic_expectations_changed"] is False
    assert approval["frozen_record_schema_id"] == RECORD_SCHEMA_ID
    assert approval["frozen_validator_id"] == VALIDATOR_ID
    assert yaml.safe_load(DEFAULT_APPROVAL_YAML_PATH.read_text(encoding="utf-8")) == approval
    assert approval == json.loads(DEFAULT_APPROVAL_PATH.read_text(encoding="utf-8"))


def test_suite_contains_semantics_only_and_review_package_is_complete(records: list[dict]) -> None:
    serialized = DEFAULT_JSONL_PATH.read_text(encoding="utf-8")
    assert "conversation" not in serialized
    assert "rendering" not in serialized
    assert "assistant_message" not in serialized
    review = DEFAULT_REVIEW_PATH.read_text(encoding="utf-8")
    assert "not training data" in review.lower()
    assert "HPG-GAP-REASSESS-001" in review
    for record in records:
        assert f"`{record['golden_case_id']}`" in review
    assert not Path("data/train").exists()
    assert not Path("data/validation").exists()
