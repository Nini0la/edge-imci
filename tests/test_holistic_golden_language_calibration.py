from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.holistic_language import (
    CALIBRATION_DRAFTS,
    DEFAULT_CALIBRATION_PATH,
    DEFAULT_CALIBRATION_YAML_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REVIEW_PATH,
    LANGUAGE_CALIBRATION_ID,
    LANGUAGE_RECORD_SCHEMA_ID,
    SEMANTIC_CASES_SHA256,
    build_language_calibration,
    load_language_calibration,
    missing_language_markers,
)


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return load_language_calibration()


def _by_id(records: list[dict]) -> dict[str, dict]:
    return {record["golden_case_id"]: record for record in records}


def test_calibration_is_the_exact_proposed_sixteen_case_set(records: list[dict]) -> None:
    assert len(records) == 16
    assert [record["golden_case_id"] for record in records] == list(CALIBRATION_DRAFTS)
    assert len({record["rendering_id"] for record in records}) == 16


def test_committed_calibration_is_deterministic_and_mirrored(records: list[dict]) -> None:
    assert records == build_language_calibration()
    assert yaml.safe_load(DEFAULT_CALIBRATION_YAML_PATH.read_text(encoding="utf-8")) == records


def test_every_record_is_a_review_draft_pinned_to_frozen_semantics(records: list[dict]) -> None:
    for record in records:
        assert record["record_schema_id"] == LANGUAGE_RECORD_SCHEMA_ID
        assert record["status"] == "DRAFT_FOR_HUMAN_REVIEW"
        assert record["corpus_role"] == "HOLISTIC_GOLDEN_LANGUAGE_CALIBRATION"
        assert record["semantic_source"]["semantic_cases_sha256"] == SEMANTIC_CASES_SHA256
        assert record["review"] == {
            "semantic_faithfulness": "PENDING",
            "interaction_quality": "PENDING",
            "phc_suitability": "PENDING",
            "reviewer": None,
            "notes": "",
        }


def test_manifest_hash_scope_and_noneligibility_are_explicit(records: list[dict]) -> None:
    manifest = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["suite_id"] == LANGUAGE_CALIBRATION_ID
    assert manifest["lifecycle_status"] == "PROPOSED_FOR_REVIEW"
    assert manifest["case_count"] == len(records)
    assert manifest["semantic_source"]["sha256"] == SEMANTIC_CASES_SHA256
    assert manifest["language_calibration_sha256"] == hashlib.sha256(
        DEFAULT_CALIBRATION_PATH.read_bytes()
    ).hexdigest()
    assert manifest["review_status"] == "PENDING_HUMAN_LANGUAGE_REVIEW"
    assert manifest["technical_editorial_review"] == {
        "record": "docs/product_holistic_golden_language_technical_review_v1.md",
        "status": "PASS_TECHNICAL_ALIGNMENT_READY_FOR_HUMAN_LANGUAGE_REVIEW",
        "same_agent_review": True,
        "language_calibration_sha256": manifest["language_calibration_sha256"],
    }
    assert manifest["eligibility"] == {
        "COMPONENT_VALIDATION": True,
        "DOMAIN_REVIEW": True,
        "HOLISTIC_GENERATION": False,
        "PRODUCT_EVALUATION": False,
        "TEACHER_BAKEOFF": False,
        "TRAINING": False,
    }
    assert manifest["production_clinical_use_authorized"] is False


@pytest.mark.parametrize(
    "use",
    [
        CorpusUse.HOLISTIC_GENERATION,
        CorpusUse.PRODUCT_EVALUATION,
        CorpusUse.TEACHER_BAKEOFF,
        CorpusUse.TRAINING,
    ],
)
def test_unreviewed_language_calibration_rejects_premature_use(use: CorpusUse) -> None:
    with pytest.raises(ValueError, match="is not eligible"):
        load_language_calibration(corpus_use=use)


def test_language_calibration_allows_only_review_and_component_validation() -> None:
    assert load_language_calibration(corpus_use=CorpusUse.DOMAIN_REVIEW)
    assert load_language_calibration(corpus_use=CorpusUse.COMPONENT_VALIDATION)


def test_incomplete_requests_preserve_acquisition_modes(records: list[dict]) -> None:
    by_id = _by_id(records)
    grouped = by_id["hpg-072-incomplete-multiple-groups"]["alignment"]
    assert grouped["acquisition_requests"] == [
        {
            "observation_id": "danger_signs.vomits_everything",
            "acquisition_mode": "CAREGIVER_QUESTION",
        },
        {
            "observation_id": "respiratory.respiratory_rate",
            "acquisition_mode": "MEASUREMENT",
        },
        {"observation_id": "fever.malaria_risk", "acquisition_mode": "AREA_CONTEXT"},
        {
            "observation_id": "patient_facts.has_ear_problem",
            "acquisition_mode": "CAREGIVER_QUESTION",
        },
    ]
    urgent = by_id["hpg-073-incomplete-known-urgent"]["alignment"]
    assert urgent["expected_state"] == "INCOMPLETE"
    assert urgent["urgent_action_required"] is True
    assert urgent["final_synthesis_authorized"] is False
    contradiction = by_id["hpg-075-contradiction-drinking"]["alignment"]
    assert {item["acquisition_mode"] for item in contradiction["acquisition_requests"]} == {
        "CLINICIAN_OBSERVATION"
    }


def test_urgent_and_nonurgent_referral_language_remain_distinct(records: list[dict]) -> None:
    by_id = _by_id(records)
    hiv = by_id["hpg-014-resp-chest-hiv-positive"]["conversation"][1]["content"]
    oxygen = by_id["hpg-016-resp-oximeter-89-9"]["conversation"][1]["content"]
    urgent = by_id["hpg-070-cross-multiple-urgent"]["conversation"][1]["content"]
    assert not hiv.startswith("URGENT:")
    assert "referral, not urgent referral" in hiv.lower()
    assert not oxygen.startswith("URGENT:")
    assert "referral, not urgent referral" in oxygen.lower()
    assert urgent.startswith("URGENT:")


def test_generic_treatment_renderings_do_not_invent_drugs(records: list[dict]) -> None:
    by_id = _by_id(records)
    cholera = by_id["hpg-031-diarrhoea-severe-age-24-cholera"]["conversation"][1][
        "content"
    ]
    bacterial = by_id["hpg-052-fever-identified-bacterial-cause"]["conversation"][1][
        "content"
    ]
    assert "applicable local protocol" in cholera
    assert "appropriate antibiotic treatment" in bacterial
    assert "applicable protocol" in bacterial
    for unencoded_drug in ("amoxicillin", "ciprofloxacin", "erythromycin", "tetracycline"):
        assert unencoded_drug not in cholera.lower()
        assert unencoded_drug not in bacterial.lower()


def test_user_facing_text_does_not_leak_internal_identifiers(records: list[dict]) -> None:
    for record in records:
        for turn in record["conversation"]:
            assert "IMCI-MSC-" not in turn["content"]
            assert not any(line.startswith("    ") for line in turn["content"].splitlines())
            assert not any(
                action in turn["content"] for action in record["alignment"]["actions_covered"]
            )
        assert "no general danger signs" not in record["conversation"][0]["content"].lower()


def test_every_response_explicitly_covers_its_semantic_targets(records: list[dict]) -> None:
    for record in records:
        assert missing_language_markers(record) == []


def test_review_package_contains_all_drafts_and_pending_fields(records: list[dict]) -> None:
    review = DEFAULT_REVIEW_PATH.read_text(encoding="utf-8")
    assert "not training data" in review.lower()
    assert "Frozen semantic target" in review
    assert "Acquisition requests" in review
    for record in records:
        assert f"## {record['golden_case_id']}" in review
    assert review.count("Semantic faithfulness: `PENDING`") == len(records)
    assert review.count("Interaction quality: `PENDING`") == len(records)
    assert review.count("PHC suitability: `PENDING`") == len(records)
    assert not Path("data/train").exists()


def test_technical_editorial_review_is_hash_pinned_without_claiming_human_approval() -> None:
    review = Path("docs/product_holistic_golden_language_technical_review_v1.md").read_text(
        encoding="utf-8"
    )
    digest = hashlib.sha256(DEFAULT_CALIBRATION_PATH.read_bytes()).hexdigest()
    assert digest in review
    assert "PASS_TECHNICAL_ALIGNMENT_READY_FOR_HUMAN_LANGUAGE_REVIEW" in review
    assert "not human/domain or PHC-worker approval" in review
    assert "same coding agent authored and performed" in review.lower()
