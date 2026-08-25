from __future__ import annotations

import copy
import json
from threading import Thread
from urllib.request import Request, urlopen

import pytest

from app.api import make_server, result_payload
from app.extractor.base import INVALID_AI_INTERPRETATION_MESSAGE, ExtractionResult
from app.service import (
    analyze_freeform_findings,
    create_default_service,
    evaluate_extracted_findings,
    extract_freeform_findings,
)


EXPECTED_STATES = [
    "COMPLETE",
    "COMPLETE",
    "INCOMPLETE",
    "URGENT_INCOMPLETE",
    "URGENT_COMPLETE",
]


def test_approved_examples_cover_primary_ui_states() -> None:
    extractor, examples = create_default_service()

    results = [
        analyze_freeform_findings(example["text"], extractor=extractor)
        for example in examples
    ]

    assert [result.state for result in results] == EXPECTED_STATES
    assert all(result.structured_view for result in results)
    assert all(
        result.pipeline_trace[-1].label == "Worker-facing presentation"
        for result in results
    )


@pytest.mark.parametrize("findings", ["", "   ", "This child is 18 months old."])
def test_stub_does_not_invent_a_complete_encounter_from_partial_input(
    findings: str,
) -> None:
    extractor, _ = create_default_service()

    result = analyze_freeform_findings(findings, extractor=extractor)

    assert result.state == "ERROR"
    assert not result.schema_valid
    assert result.matched_case_id is None


def test_examples_include_text_needed_by_the_ui() -> None:
    _, examples = create_default_service()

    assert len(examples) == 5
    assert all(set(example) == {"id", "label", "text"} for example in examples)
    assert all(example["text"].strip() for example in examples)


def test_out_of_scope_age_has_a_dedicated_ui_state() -> None:
    base_extractor, examples = create_default_service()
    base = base_extractor.extract(examples[0]["text"]).encounter
    encounter = copy.deepcopy(base)
    encounter["patient_facts"]["age_months"] = 1

    class OutOfScopeExtractor:
        mode_label = "test"

        def extract(self, free_text: str) -> ExtractionResult:
            return ExtractionResult(
                encounter=encounter, extraction_mode=self.mode_label
            )

    result = analyze_freeform_findings(
        "One-month-old child", extractor=OutOfScopeExtractor()
    )

    assert result.state == "OUT_OF_SCOPE"
    assert result.error is None
    assert result.rendered_response.startswith("OUTSIDE SUPPORTED SCOPE")


def test_result_payload_includes_derived_state() -> None:
    extractor, examples = create_default_service()
    result = analyze_freeform_findings(examples[2]["text"], extractor=extractor)

    payload = result_payload(result)

    assert payload["state"] == "INCOMPLETE"
    assert payload["structured_view"]


def test_worker_response_uses_approved_deterministic_action_order() -> None:
    extractor, examples = create_default_service()
    result = analyze_freeform_findings(examples[0]["text"], extractor=extractor)

    assert result.rendered_response.startswith("Classifications:")


def test_partial_model_target_renders_incomplete_assessment_directive() -> None:
    encounter = {
        "danger_signs": {
            "convulsing_now": None,
            "had_convulsions": None,
            "lethargic_or_unconscious": None,
            "unable_to_drink_or_breastfeed": None,
            "vomits_everything": None,
        },
        "diarrhoea": None,
        "ear": None,
        "fever": None,
        "patient_facts": {
            "age_months": 20,
            "has_cough_or_difficult_breathing": True,
            "has_diarrhoea": None,
            "has_ear_problem": None,
            "has_fever": None,
        },
        "respiratory": {
            "breaths_counted_one_minute": None,
            "bronchodilator_trial_completed": None,
            "chest_indrawing": None,
            "child_calm": None,
            "cough_duration_days": None,
            "hiv_exposed_or_infected": None,
            "oxygen_saturation_percent": None,
            "post_bronchodilator_breaths_counted_one_minute": None,
            "post_bronchodilator_chest_indrawing": None,
            "post_bronchodilator_child_calm": None,
            "post_bronchodilator_respiratory_rate": None,
            "pulse_oximeter_available": None,
            "recurrent_wheeze": None,
            "respiratory_rate": None,
            "stridor_when_calm": None,
            "wheezing": None,
        },
    }

    class PartialExtractor:
        mode_label = "test partial extractor"

        def extract(self, free_text: str) -> ExtractionResult:
            return ExtractionResult(encounter=encounter, extraction_mode=self.mode_label)

    result = analyze_freeform_findings(
        "The child is 20 months old and has cough.", extractor=PartialExtractor()
    )

    assert result.state == "INCOMPLETE"
    assert result.schema_valid
    assert result.classifications == []
    assert result.rendered_response.startswith("ASSESSMENT INCOMPLETE")
    assert "Information needed:" in result.rendered_response
    assert result.rendered_response.endswith("these findings are supplied.")


def test_worker_review_separates_extraction_from_decision_engine() -> None:
    extractor, examples = create_default_service()

    preview = extract_freeform_findings(examples[3]["text"], extractor=extractor)

    assert preview.state == "READY_FOR_REVIEW"
    assert [step.label for step in preview.pipeline_trace] == [
        "Language interpretation",
        "Structured encounter validation",
    ]

    result = evaluate_extracted_findings(preview)

    assert result.state == "URGENT_INCOMPLETE"
    assert result.pipeline_trace[-1].label == "Worker-facing presentation"


def test_downstream_schema_failure_does_not_expose_validator_details() -> None:
    class InvalidExtractor:
        mode_label = "test invalid extractor"

        def extract(self, free_text: str) -> ExtractionResult:
            return ExtractionResult(
                encounter={"unexpected_internal_field": True},
                extraction_mode=self.mode_label,
            )

    preview = extract_freeform_findings(
        "The child is 22 months and is coughing.", extractor=InvalidExtractor()
    )

    assert preview.error == INVALID_AI_INTERPRETATION_MESSAGE
    assert "unexpected_internal_field" not in preview.error


def test_http_api_exposes_examples_and_analysis() -> None:
    server = make_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with urlopen(f"{base_url}/api/examples") as response:
            examples = json.load(response)["examples"]

        extract_request = Request(
            f"{base_url}/api/extract",
            data=json.dumps({"findings": examples[3]["text"]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(extract_request) as response:
            preview = json.load(response)

        assert preview["state"] == "READY_FOR_REVIEW"

        evaluate_request = Request(
            f"{base_url}/api/evaluate",
            data=json.dumps(preview).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(evaluate_request) as response:
            result = json.load(response)

        assert result["state"] == "URGENT_INCOMPLETE"
        assert result["is_urgent"] is True
        assert result["rendered_response"].startswith("URGENT:")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
