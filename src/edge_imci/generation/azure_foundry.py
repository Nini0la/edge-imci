"""Azure Foundry Responses API transport for authorized teacher bake-offs.

The checked-in execution configuration is intentionally blocked. This module
can construct and normalize requests without network access; a remote call is
possible only when both the immutable schedule and a separately authorized
execution configuration pass their gates.
"""

from __future__ import annotations

import copy
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from decimal import Decimal
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlsplit, urlunsplit

from jsonschema import Draft202012Validator, FormatChecker

from edge_imci.generation.holistic_variants import (
    ATTEMPT_SCHEMA_ID,
    CANDIDATE_SCHEMA_PATH,
    ROOT,
    parse_candidate_output,
    validate_attempt_record,
    validate_candidate,
)


AZURE_EXECUTION_CONFIG_ID = "edge-imci-azure-foundry-teacher-execution-v1"
AZURE_EXECUTION_CONFIG_PATH = (
    ROOT / "configs" / "generation" / "azure_foundry_teacher_execution_v1.json"
)
AZURE_EXECUTION_SCHEMA_PATH = AZURE_EXECUTION_CONFIG_PATH.with_name(
    "azure_foundry_teacher_execution_v1.schema.json"
)

_UNSUPPORTED_AZURE_STRUCTURED_OUTPUT_KEYWORDS = frozenset(
    {
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minimum",
        "maximum",
        "multipleOf",
        "patternProperties",
        "unevaluatedProperties",
        "propertyNames",
        "minProperties",
        "maxProperties",
        "unevaluatedItems",
        "contains",
        "minContains",
        "maxContains",
        "minItems",
        "maxItems",
        "uniqueItems",
    }
)


@dataclass(frozen=True)
class AzureProviderResponse:
    """Secret-free subset of one Azure Responses API result."""

    output_text: str
    provider_request_id: str | None
    usage: dict[str, Any]
    latency_ms: int


class AzureResponsesTransport(Protocol):
    def create(self, payload: Mapping[str, Any]) -> AzureProviderResponse: ...


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_azure_execution_config(path: Path = AZURE_EXECUTION_CONFIG_PATH) -> dict[str, Any]:
    config = _load_json(path)
    schema = _load_json(AZURE_EXECUTION_SCHEMA_PATH)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(config)
    if config["execution_config_id"] != AZURE_EXECUTION_CONFIG_ID:
        raise ValueError("incorrect Azure teacher execution configuration ID")
    return config


def require_authorized_execution_config(config: Mapping[str, Any]) -> None:
    """Reject incomplete, secret-bearing, or unbounded remote-call settings."""

    Draft202012Validator(_load_json(AZURE_EXECUTION_SCHEMA_PATH)).validate(dict(config))
    if config["status"] != "AUTHORIZED_FOR_RECORDED_BAKEOFF_ONLY":
        raise PermissionError("Azure teacher execution is not project-owner authorized")
    if config["remote_calls_authorized"] is not True:
        raise PermissionError("Azure remote calls are disabled")
    if config["authentication"]["mode"] not in {"API_KEY", "ENTRA_ID"}:
        raise ValueError("Azure authentication mode is unresolved")
    if not config["deployments"]:
        raise ValueError("at least one exact Azure deployment snapshot is required")
    if config["limits"]["maximum_remote_attempts"] is None:
        raise ValueError("an explicit remote-attempt ceiling is required")
    if config["limits"]["maximum_budget_usd"] is None:
        raise ValueError("an explicit USD budget ceiling is required")
    if config["authentication"]["mode"] == "API_KEY":
        if not config["authentication"]["api_key_environment"]:
            raise ValueError("API-key authentication requires a secret environment name")
    elif config["authentication"]["api_key_environment"] is not None:
        raise ValueError("Entra ID configuration must not name an API-key environment")


def normalize_azure_v1_base_url(value: str) -> str:
    """Normalize an Azure OpenAI resource or Foundry project to its v1 base URL."""

    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Azure OpenAI base URL must be an absolute HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Azure OpenAI base URL cannot contain credentials, query, or fragment")
    host = (parsed.hostname or "").casefold()
    path = parsed.path.rstrip("/")
    if host.endswith(".openai.azure.com"):
        if not path:
            path = "/openai/v1"
        elif path != "/openai/v1":
            raise ValueError("Azure OpenAI resource path must be empty or /openai/v1")
    elif host.endswith(".services.ai.azure.com"):
        parts = [part for part in path.split("/") if part]
        if len(parts) == 3 and parts[:2] == ["api", "projects"]:
            path += "/openai/v1"
        elif not (
            len(parts) == 5
            and parts[:2] == ["api", "projects"]
            and parts[3:] == ["openai", "v1"]
        ):
            raise ValueError(
                "Foundry project path must be /api/projects/<project> with optional /openai/v1"
            )
    else:
        raise ValueError("unsupported Azure OpenAI or Foundry endpoint host")
    return urlunsplit((parsed.scheme, parsed.netloc, path + "/", "", ""))


def azure_structured_output_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Remove provider-unsupported constraints; local validation remains canonical."""

    def visit(value: Any) -> Any:
        if isinstance(value, dict):
            result = {
                key: visit(child)
                for key, child in value.items()
                if key not in _UNSUPPORTED_AZURE_STRUCTURED_OUTPUT_KEYWORDS
                and key not in {"$schema", "$id", "const"}
            }
            if "const" in value:
                result["enum"] = [visit(value["const"])]
            return result
        if isinstance(value, list):
            return [visit(item) for item in value]
        return value

    result = visit(copy.deepcopy(dict(schema)))
    if result.get("additionalProperties") is not False:
        raise ValueError("structured output root must forbid additional properties")
    return result


def build_azure_responses_payload(
    *,
    source_request: Mapping[str, Any],
    configuration: Mapping[str, Any],
    deployment_name: str,
) -> dict[str, Any]:
    """Build one Responses API payload without performing a remote call."""

    if source_request["strategy_id"] != configuration["strategy_id"]:
        raise ValueError("source request and teacher configuration strategies differ")
    for key in ("prompt_id", "prompt_version", "prompt_sha256"):
        if source_request[key] != configuration[key]:
            raise ValueError(f"source request and teacher configuration differ on {key}")
    sampling = dict(configuration["sampling_config"])
    unsupported = set(sampling) - {"temperature", "top_p"}
    if unsupported:
        raise ValueError(f"unsupported v1 sampling keys: {sorted(unsupported)}")
    provider_schema = azure_structured_output_schema(_load_json(CANDIDATE_SCHEMA_PATH))
    provider_schema["properties"]["semantic_case_id"]["enum"] = [
        source_request["semantic_case_id"]
    ]
    provider_schema["properties"]["strategy_id"]["enum"] = [
        source_request["strategy_id"]
    ]
    payload = {
        "model": deployment_name,
        "input": source_request["rendered_prompt"],
        "max_output_tokens": configuration["max_output_tokens"],
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "edge_imci_holistic_language_variant_v1",
                "strict": True,
                "schema": provider_schema,
            }
        },
        **sampling,
    }
    return payload


def build_requested_attempt(
    *,
    schedule: Mapping[str, Any],
    unit: Mapping[str, Any],
    requested_at: str,
    retry_count: int,
) -> dict[str, Any]:
    """Create the immutable pre-call receipt that must be persisted before I/O."""

    if schedule["authorization"]["remote_calls_authorized"] is not True:
        raise PermissionError("the immutable schedule does not authorize remote calls")
    configuration = next(
        item
        for item in schedule["configurations"]
        if item["configuration_id"] == unit["configuration_id"]
    )
    attempt = {
        "attempt_schema_id": ATTEMPT_SCHEMA_ID,
        "generation_run_id": schedule["generation_run_id"],
        "attempt_id": f"{unit['request_id']}__attempt-{retry_count + 1}",
        "request_id": unit["request_id"],
        "configuration_id": unit["configuration_id"],
        "semantic_case_id": unit["semantic_case_id"],
        "status": "REQUESTED",
        "teacher": {
            "provider": configuration["teacher_provider"],
            "model": configuration["teacher_model"],
            "snapshot": configuration["teacher_snapshot"],
        },
        "prompt": {
            "strategy_id": configuration["strategy_id"],
            "prompt_id": configuration["prompt_id"],
            "prompt_version": configuration["prompt_version"],
            "prompt_sha256": configuration["prompt_sha256"],
        },
        "generation_parameters": {
            "sampling_config": configuration["sampling_config"],
            "max_output_tokens": configuration["max_output_tokens"],
        },
        "request_sha256": unit["source_request_sha256"],
        "requested_at": requested_at,
        "completed_at": None,
        "raw_response": None,
        "candidate": None,
        "validation": {
            "deterministic_pass": False,
            "error_codes": [],
            "requires_human_semantic_review": True,
        },
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "cached_input_tokens": None,
            "latency_ms": None,
            "retry_count": retry_count,
            "provider_request_id": None,
            "raw_usage": None,
        },
    }
    validate_attempt_record(attempt)
    return attempt


def _require_matching_deployment(
    config: Mapping[str, Any], configuration: Mapping[str, Any]
) -> str:
    if configuration["teacher_provider"] != "AZURE_OPENAI":
        raise ValueError("scheduled teacher provider is not Azure OpenAI")
    matches = [
        item
        for item in config["deployments"]
        if item["model_family"] == configuration["teacher_model"]
        and item["model_snapshot"] == configuration["teacher_snapshot"]
    ]
    if len(matches) != 1:
        raise ValueError("scheduled teacher model and snapshot are not uniquely pinned")
    return matches[0]["deployment_name"]


def execute_authorized_unit(
    *,
    execution_config: Mapping[str, Any],
    schedule: Mapping[str, Any],
    unit: Mapping[str, Any],
    source_request: Mapping[str, Any],
    semantic_record: Mapping[str, Any],
    parent_language: Mapping[str, Any],
    transport: AzureResponsesTransport,
    persist_attempt: Callable[[dict[str, Any]], None],
    requested_at: str,
    completed_at: str,
    retry_count: int,
    remote_attempts_already_started: int,
    accounted_cost_usd: Decimal,
    maximum_next_attempt_cost_usd: Decimal,
) -> dict[str, Any]:
    """Execute one bounded unit after persisting its REQUESTED receipt.

    Provider exceptions deliberately propagate after the receipt is persisted.
    The receipt therefore remains REQUESTED and requires reconciliation; this
    function never guesses that an ambiguous timeout was safe to retry.
    """

    require_authorized_execution_config(execution_config)
    if schedule["authorization"]["remote_calls_authorized"] is not True:
        raise PermissionError("the immutable schedule does not authorize remote calls")
    configuration = next(
        item
        for item in schedule["configurations"]
        if item["configuration_id"] == unit["configuration_id"]
    )
    deployment_name = _require_matching_deployment(execution_config, configuration)
    if source_request["request_sha256"] != unit["source_request_sha256"]:
        raise ValueError("source request hash differs from immutable schedule")
    if source_request["semantic_case_id"] != unit["semantic_case_id"]:
        raise ValueError("source request case differs from immutable schedule")
    if remote_attempts_already_started >= execution_config["limits"][
        "maximum_remote_attempts"
    ]:
        raise PermissionError("remote-attempt ceiling has been reached")
    if retry_count > schedule["retry_policy"]["transport_retry_limit"]:
        raise PermissionError("scheduled transport-retry ceiling has been reached")
    if maximum_next_attempt_cost_usd <= 0:
        raise ValueError("next-attempt cost reservation must be positive")
    projected = accounted_cost_usd + maximum_next_attempt_cost_usd
    schedule_budget = schedule["authorization"]["budget"]
    if schedule_budget["currency"] != "USD":
        raise ValueError("Azure v1 execution currently requires a USD schedule budget")
    ceiling = min(
        Decimal(str(execution_config["limits"]["maximum_budget_usd"])),
        Decimal(str(schedule_budget["maximum_amount"])),
    )
    if projected > ceiling:
        raise PermissionError("next call would exceed the recorded budget ceiling")

    receipt = build_requested_attempt(
        schedule=schedule,
        unit=unit,
        requested_at=requested_at,
        retry_count=retry_count,
    )
    persist_attempt(copy.deepcopy(receipt))
    payload = build_azure_responses_payload(
        source_request=source_request,
        configuration=configuration,
        deployment_name=deployment_name,
    )
    response = transport.create(payload)
    completed = complete_attempt_from_response(
        receipt=receipt,
        response=response,
        completed_at=completed_at,
        semantic_record=semantic_record,
        parent_language=parent_language,
    )
    persist_attempt(copy.deepcopy(completed))
    return completed


def complete_attempt_from_response(
    *,
    receipt: Mapping[str, Any],
    response: AzureProviderResponse,
    completed_at: str,
    semantic_record: Mapping[str, Any],
    parent_language: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize one provider result into the canonical immutable attempt shape."""

    attempt = copy.deepcopy(dict(receipt))
    if attempt["status"] != "REQUESTED":
        raise ValueError("only a REQUESTED receipt can be completed")
    attempt["completed_at"] = completed_at
    attempt["raw_response"] = response.output_text
    usage = response.usage
    input_details = usage.get("input_tokens_details") or {}
    attempt["usage"] = {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cached_input_tokens": input_details.get("cached_tokens", 0),
        "latency_ms": response.latency_ms,
        "retry_count": receipt["usage"]["retry_count"],
        "provider_request_id": response.provider_request_id,
        "raw_usage": copy.deepcopy(usage),
    }
    try:
        candidate = parse_candidate_output(response.output_text)
    except (json.JSONDecodeError, ValueError):
        attempt["status"] = "PARSE_FAILED"
        attempt["validation"]["error_codes"] = ["TEACHER_OUTPUT_PARSE_FAILED"]
    else:
        validation = validate_candidate(
            candidate,
            dict(semantic_record),
            dict(parent_language),
            receipt["prompt"]["strategy_id"],
        )
        if validation.error_codes == ("SCHEMA_INVALID",):
            attempt["status"] = "PARSE_FAILED"
            attempt["validation"] = validation.to_dict()
        else:
            attempt["candidate"] = candidate
            attempt["validation"] = validation.to_dict()
            attempt["status"] = (
                "PENDING_HUMAN_REVIEW"
                if validation.deterministic_pass
                else "DETERMINISTIC_REJECTED"
            )
    validate_attempt_record(attempt)
    return attempt


def complete_attempt_from_transport_failure(
    *,
    receipt: Mapping[str, Any],
    completed_at: str,
    latency_ms: int,
    error_code: str,
    provider_request_id: str | None = None,
) -> dict[str, Any]:
    """Record a secret-free transport failure without guessing call completion."""

    attempt = copy.deepcopy(dict(receipt))
    if attempt["status"] != "REQUESTED":
        raise ValueError("only a REQUESTED receipt can fail in transport")
    attempt["status"] = "TRANSPORT_FAILED"
    attempt["completed_at"] = completed_at
    attempt["validation"]["error_codes"] = [error_code]
    attempt["usage"].update(
        {
            "latency_ms": latency_ms,
            "provider_request_id": provider_request_id,
            "raw_usage": {"transport_error_code": error_code},
        }
    )
    validate_attempt_record(attempt)
    return attempt


class OpenAIAzureResponsesTransport:
    """Lazy OpenAI-SDK transport; construction reads secrets only from env."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        require_authorized_execution_config(config)
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only with azure extra
            raise RuntimeError("install EdgeIMCI with the 'azure' extra") from exc

        base_url_name = config["base_url_environment"]
        base_url_value = os.environ.get(base_url_name)
        if not base_url_value:
            raise RuntimeError(f"missing required environment variable: {base_url_name}")
        base_url = normalize_azure_v1_base_url(base_url_value)
        project_endpoint = (urlsplit(base_url).hostname or "").endswith(
            ".services.ai.azure.com"
        )
        auth = config["authentication"]
        if auth["mode"] == "API_KEY":
            secret_name = auth["api_key_environment"]
            secret = os.environ.get(secret_name)
            if not secret:
                raise RuntimeError(f"missing required environment variable: {secret_name}")
            client_options: dict[str, Any] = {
                "base_url": base_url,
                "api_key": secret,
                "max_retries": 0,
            }
            if project_endpoint:
                client_options["default_headers"] = {"api-key": secret}
            self._client = OpenAI(**client_options)
        else:
            try:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            except ImportError as exc:  # pragma: no cover - azure-only dependency
                raise RuntimeError("install EdgeIMCI with the 'azure' extra") from exc
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://ai.azure.com/.default",
            )
            self._client = OpenAI(
                base_url=base_url,
                api_key=token_provider,
                max_retries=0,
            )

    def create(self, payload: Mapping[str, Any]) -> AzureProviderResponse:
        started = time.monotonic()
        result = self._client.responses.create(**dict(payload))
        latency_ms = round((time.monotonic() - started) * 1000)
        usage = result.usage.model_dump(mode="json") if result.usage else {}
        return AzureProviderResponse(
            output_text=result.output_text,
            provider_request_id=result.id,
            usage=usage,
            latency_ms=latency_ms,
        )
