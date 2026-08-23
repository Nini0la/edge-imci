from __future__ import annotations

import copy
import json
from decimal import Decimal

import pytest
import yaml
from jsonschema import Draft202012Validator

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.azure_foundry import (
    AZURE_EXECUTION_CONFIG_PATH,
    AZURE_EXECUTION_SCHEMA_PATH,
    AzureProviderResponse,
    azure_structured_output_schema,
    build_azure_responses_payload,
    build_requested_attempt,
    complete_attempt_from_response,
    complete_attempt_from_transport_failure,
    execute_authorized_unit,
    load_azure_execution_config,
    normalize_azure_v1_base_url,
    require_authorized_execution_config,
)
from edge_imci.generation.holistic_bakeoff import build_bakeoff_schedule
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_variants import (
    CANDIDATE_SCHEMA_ID,
    CANDIDATE_SCHEMA_PATH,
    build_pilot_requests,
    source_fact_specs,
)


def _source_request() -> dict:
    return next(
        item
        for item in build_pilot_requests()
        if item["strategy_id"] == "phc-concise-complete-v1"
    )


def _configuration(request: dict) -> dict:
    return {
        "configuration_id": "azure-gpt-4-1__phc-concise-complete-v1",
        "teacher_provider": "AZURE_OPENAI",
        "teacher_model": "gpt-4.1",
        "teacher_snapshot": "gpt-4.1-2025-04-14",
        "strategy_id": request["strategy_id"],
        "prompt_id": request["prompt_id"],
        "prompt_version": request["prompt_version"],
        "prompt_sha256": request["prompt_sha256"],
        "sampling_config": {"temperature": 0.2},
        "max_output_tokens": 2000,
    }


def _schedule(request: dict) -> dict:
    return build_bakeoff_schedule(
        generation_run_id="azure-in-memory-test",
        created_at="2026-08-23T00:00:00Z",
        authorization={
            "project_owner": "test-owner",
            "approved_at": "2026-08-23T00:00:00Z",
            "variant_contract_approved": True,
            "remote_calls_authorized": True,
            "budget": {"currency": "USD", "maximum_amount": 1.0},
        },
        teacher_configurations=[_configuration(request)],
        source_requests=[request],
    )


def _records(case_id: str) -> tuple[dict, dict]:
    semantic = next(
        item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
        if item["golden_case_id"] == case_id
    )
    parent = next(
        item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
        if item["golden_case_id"] == case_id
    )
    return semantic, parent


def _candidate(semantic: dict, parent: dict, strategy_id: str) -> dict:
    submission = parent["conversation"][0]["content"] + " Assessment is fully recorded."
    return {
        "candidate_schema_id": CANDIDATE_SCHEMA_ID,
        "semantic_case_id": semantic["golden_case_id"],
        "strategy_id": strategy_id,
        "user_submission": submission,
        "fact_evidence": [
            {"fact_id": item["fact_id"], "evidence_text": submission}
            for item in source_fact_specs(semantic)
        ],
    }


def _authorized_execution_config() -> dict:
    config = load_azure_execution_config()
    config.update(
        {
            "status": "AUTHORIZED_FOR_RECORDED_BAKEOFF_ONLY",
            "remote_calls_authorized": True,
        }
    )
    config["authentication"] = {
        "mode": "API_KEY",
        "api_key_environment": "AZURE_OPENAI_API_KEY",
    }
    config["deployments"] = [
        {
            "deployment_name": "edgeimci-teacher-deployment",
            "model_family": "gpt-4.1",
            "model_snapshot": "gpt-4.1-2025-04-14",
            "structured_outputs_supported": True,
        }
    ]
    config["limits"] = {
        "maximum_remote_attempts": 2,
        "maximum_budget_usd": 1.0,
    }
    return config


def test_checked_in_execution_config_is_valid_and_cannot_call_azure() -> None:
    schema = json.loads(AZURE_EXECUTION_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    config = load_azure_execution_config()

    assert config["status"] == "BLOCKED_PENDING_PROJECT_OWNER_AUTHORIZATION"
    assert config["remote_calls_authorized"] is False
    assert config["authentication"] == {
        "mode": "API_KEY",
        "api_key_environment": "AZURE_OPENAI_API_KEY",
    }
    assert config["deployments"] == [
        {
            "deployment_name": "gpt-4.1",
            "model_family": "gpt-4.1",
            "model_snapshot": "2025-04-14",
            "structured_outputs_supported": True,
        }
    ]
    mirror_path = AZURE_EXECUTION_CONFIG_PATH.with_suffix(".yaml")
    assert yaml.safe_load(mirror_path.read_text(encoding="utf-8")) == config
    assert "sk-" not in AZURE_EXECUTION_CONFIG_PATH.read_text(encoding="utf-8").casefold()
    with pytest.raises(PermissionError):
        require_authorized_execution_config(config)


def test_authorized_config_requires_snapshot_attempt_and_budget_pins() -> None:
    config = load_azure_execution_config()
    config.update(
        {
            "status": "AUTHORIZED_FOR_RECORDED_BAKEOFF_ONLY",
            "remote_calls_authorized": True,
        }
    )
    config["authentication"] = {
        "mode": "API_KEY",
        "api_key_environment": "AZURE_OPENAI_API_KEY",
    }
    config["deployments"] = []
    with pytest.raises(ValueError, match="deployment snapshot"):
        require_authorized_execution_config(config)

    config["deployments"] = [
        {
            "deployment_name": "edgeimci-teacher-deployment",
            "model_family": "gpt-4.1",
            "model_snapshot": "gpt-4.1-2025-04-14",
            "structured_outputs_supported": True,
        }
    ]
    with pytest.raises(ValueError, match="attempt ceiling"):
        require_authorized_execution_config(config)
    config["limits"]["maximum_remote_attempts"] = 1
    with pytest.raises(ValueError, match="budget ceiling"):
        require_authorized_execution_config(config)
    config["limits"]["maximum_budget_usd"] = 1.0
    require_authorized_execution_config(config)


def test_base_url_normalization_rejects_credentials_and_non_v1_paths() -> None:
    expected = "https://edgeimci.openai.azure.com/openai/v1/"
    assert normalize_azure_v1_base_url("https://edgeimci.openai.azure.com") == expected
    assert normalize_azure_v1_base_url(expected) == expected
    with pytest.raises(ValueError):
        normalize_azure_v1_base_url("http://edgeimci.openai.azure.com")
    with pytest.raises(ValueError):
        normalize_azure_v1_base_url("https://user:secret@edgeimci.openai.azure.com")
    with pytest.raises(ValueError):
        normalize_azure_v1_base_url("https://edgeimci.openai.azure.com/openai/deployments")


def test_payload_uses_blind_prompt_store_false_and_azure_schema_subset() -> None:
    request = _source_request()
    payload = build_azure_responses_payload(
        source_request=request,
        configuration=_configuration(request),
        deployment_name="edgeimci-teacher-deployment",
    )

    assert payload["model"] == "edgeimci-teacher-deployment"
    assert payload["input"] == request["rendered_prompt"]
    assert payload["store"] is False
    assert "canonical assistant" not in payload["input"].casefold()
    assert "classifications_covered" not in request["source_package"]["structured_encounter"]
    assert "actions_covered" not in request["source_package"]["structured_encounter"]
    provider_schema = payload["text"]["format"]["schema"]
    serialized_schema = json.dumps(provider_schema)
    for unsupported in (
        "const",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "uniqueItems",
    ):
        assert unsupported not in serialized_schema
    assert provider_schema["additionalProperties"] is False
    assert provider_schema["properties"]["candidate_schema_id"]["enum"] == [
        CANDIDATE_SCHEMA_ID
    ]
    assert provider_schema["properties"]["semantic_case_id"]["enum"] == [
        request["semantic_case_id"]
    ]
    assert provider_schema["properties"]["strategy_id"]["enum"] == [
        request["strategy_id"]
    ]
    canonical = json.loads(CANDIDATE_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert "minLength" in json.dumps(canonical)
    assert "minLength" not in json.dumps(azure_structured_output_schema(canonical))


def test_response_is_normalized_to_reviewable_attempt_without_target_data() -> None:
    request = _source_request()
    schedule = _schedule(request)
    unit = schedule["units"][0]
    receipt = build_requested_attempt(
        schedule=schedule,
        unit=unit,
        requested_at="2026-08-23T00:00:00Z",
        retry_count=0,
    )
    semantic, parent = _records(unit["semantic_case_id"])
    candidate = _candidate(semantic, parent, unit["strategy_id"])
    response = AzureProviderResponse(
        output_text=json.dumps(candidate),
        provider_request_id="resp_azure_test",
        usage={
            "input_tokens": 900,
            "output_tokens": 600,
            "input_tokens_details": {"cached_tokens": 100},
        },
        latency_ms=1200,
    )

    attempt = complete_attempt_from_response(
        receipt=receipt,
        response=response,
        completed_at="2026-08-23T00:00:02Z",
        semantic_record=semantic,
        parent_language=parent,
    )

    assert attempt["status"] == "PENDING_HUMAN_REVIEW"
    assert attempt["validation"]["deterministic_pass"] is True
    assert attempt["usage"] == {
        "input_tokens": 900,
        "output_tokens": 600,
        "cached_input_tokens": 100,
        "latency_ms": 1200,
        "retry_count": 0,
        "provider_request_id": "resp_azure_test",
        "raw_usage": response.usage,
    }
    serialized = json.dumps(attempt)
    assert parent["conversation"][1]["content"] not in serialized
    assert "api_key" not in serialized.casefold()


def test_parse_and_transport_failures_are_immutable_attempt_states() -> None:
    request = _source_request()
    schedule = _schedule(request)
    unit = schedule["units"][0]
    receipt = build_requested_attempt(
        schedule=schedule,
        unit=unit,
        requested_at="2026-08-23T00:00:00Z",
        retry_count=0,
    )
    semantic, parent = _records(unit["semantic_case_id"])

    parsed_failure = complete_attempt_from_response(
        receipt=receipt,
        response=AzureProviderResponse("not-json", "resp_known", {}, 500),
        completed_at="2026-08-23T00:00:01Z",
        semantic_record=semantic,
        parent_language=parent,
    )
    assert parsed_failure["status"] == "PARSE_FAILED"
    assert parsed_failure["usage"]["provider_request_id"] == "resp_known"

    schema_failure = complete_attempt_from_response(
        receipt=receipt,
        response=AzureProviderResponse(
            json.dumps({"not": "a candidate"}), "resp_schema", {}, 500
        ),
        completed_at="2026-08-23T00:00:01Z",
        semantic_record=semantic,
        parent_language=parent,
    )
    assert schema_failure["status"] == "PARSE_FAILED"
    assert schema_failure["candidate"] is None
    assert schema_failure["validation"]["error_codes"] == ["SCHEMA_INVALID"]

    transport_failure = complete_attempt_from_transport_failure(
        receipt=copy.deepcopy(receipt),
        completed_at="2026-08-23T00:00:01Z",
        latency_ms=500,
        error_code="AZURE_CONNECTION_FAILED",
    )
    assert transport_failure["status"] == "TRANSPORT_FAILED"
    assert transport_failure["raw_response"] is None
    assert transport_failure["usage"]["provider_request_id"] is None
    assert transport_failure["validation"]["error_codes"] == [
        "AZURE_CONNECTION_FAILED"
    ]


def test_payload_rejects_unrecorded_sampling_parameters() -> None:
    request = _source_request()
    configuration = _configuration(request)
    configuration["sampling_config"] = {"temperature": 0.2, "seed": 7}
    with pytest.raises(ValueError, match="unsupported v1 sampling keys"):
        build_azure_responses_payload(
            source_request=request,
            configuration=configuration,
            deployment_name="edgeimci-teacher-deployment",
        )


def test_executor_persists_receipt_before_fake_transport_and_terminal_result() -> None:
    request = _source_request()
    schedule = _schedule(request)
    unit = schedule["units"][0]
    semantic, parent = _records(unit["semantic_case_id"])
    candidate = _candidate(semantic, parent, unit["strategy_id"])
    events: list[tuple[str, str]] = []

    class FakeTransport:
        def create(self, payload: dict) -> AzureProviderResponse:
            assert events == [("persist", "REQUESTED")]
            events.append(("transport", payload["model"]))
            return AzureProviderResponse(
                json.dumps(candidate),
                "resp_fake",
                {"input_tokens": 900, "output_tokens": 600},
                1000,
            )

    result = execute_authorized_unit(
        execution_config=_authorized_execution_config(),
        schedule=schedule,
        unit=unit,
        source_request=request,
        semantic_record=semantic,
        parent_language=parent,
        transport=FakeTransport(),
        persist_attempt=lambda item: events.append(("persist", item["status"])),
        requested_at="2026-08-23T00:00:00Z",
        completed_at="2026-08-23T00:00:01Z",
        retry_count=0,
        remote_attempts_already_started=0,
        accounted_cost_usd=Decimal("0.00"),
        maximum_next_attempt_cost_usd=Decimal("0.02"),
    )

    assert result["status"] == "PENDING_HUMAN_REVIEW"
    assert events == [
        ("persist", "REQUESTED"),
        ("transport", "edgeimci-teacher-deployment"),
        ("persist", "PENDING_HUMAN_REVIEW"),
    ]


def test_executor_does_not_call_when_attempt_or_budget_ceiling_would_be_exceeded() -> None:
    request = _source_request()
    schedule = _schedule(request)
    unit = schedule["units"][0]
    semantic, parent = _records(unit["semantic_case_id"])

    class NeverTransport:
        def create(self, payload: dict) -> AzureProviderResponse:
            raise AssertionError("transport must not be called")

    common = {
        "execution_config": _authorized_execution_config(),
        "schedule": schedule,
        "unit": unit,
        "source_request": request,
        "semantic_record": semantic,
        "parent_language": parent,
        "transport": NeverTransport(),
        "persist_attempt": lambda item: (_ for _ in ()).throw(
            AssertionError("nothing may be persisted before limits pass")
        ),
        "requested_at": "2026-08-23T00:00:00Z",
        "completed_at": "2026-08-23T00:00:01Z",
        "retry_count": 0,
    }
    with pytest.raises(PermissionError, match="attempt ceiling"):
        execute_authorized_unit(
            **common,
            remote_attempts_already_started=2,
            accounted_cost_usd=Decimal("0.00"),
            maximum_next_attempt_cost_usd=Decimal("0.02"),
        )
    with pytest.raises(PermissionError, match="budget ceiling"):
        execute_authorized_unit(
            **common,
            remote_attempts_already_started=0,
            accounted_cost_usd=Decimal("0.99"),
            maximum_next_attempt_cost_usd=Decimal("0.02"),
        )

    schedule["authorization"]["budget"]["maximum_amount"] = 0.01
    with pytest.raises(PermissionError, match="budget ceiling"):
        execute_authorized_unit(
            **common,
            remote_attempts_already_started=0,
            accounted_cost_usd=Decimal("0.00"),
            maximum_next_attempt_cost_usd=Decimal("0.02"),
        )


def test_ambiguous_transport_error_leaves_only_requested_receipt() -> None:
    request = _source_request()
    schedule = _schedule(request)
    unit = schedule["units"][0]
    semantic, parent = _records(unit["semantic_case_id"])
    persisted: list[dict] = []

    class TimeoutTransport:
        def create(self, payload: dict) -> AzureProviderResponse:
            raise TimeoutError("simulated uncertain provider outcome")

    with pytest.raises(TimeoutError):
        execute_authorized_unit(
            execution_config=_authorized_execution_config(),
            schedule=schedule,
            unit=unit,
            source_request=request,
            semantic_record=semantic,
            parent_language=parent,
            transport=TimeoutTransport(),
            persist_attempt=persisted.append,
            requested_at="2026-08-23T00:00:00Z",
            completed_at="2026-08-23T00:00:01Z",
            retry_count=0,
            remote_attempts_already_started=0,
            accounted_cost_usd=Decimal("0.00"),
            maximum_next_attempt_cost_usd=Decimal("0.02"),
        )
    assert [item["status"] for item in persisted] == ["REQUESTED"]
