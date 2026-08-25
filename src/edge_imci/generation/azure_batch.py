"""Zero-call Azure OpenAI Responses Batch preparation and result ingestion.

This module creates the documented JSONL request format and normalizes returned
Batch output into the same immutable terminal-attempt contract used by the
standard Azure execution lane. It never uploads a file, submits a batch, polls
a provider, downloads results, or authorizes spending.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from edge_imci.generation.azure_foundry import (
    AzureProviderResponse,
    build_azure_responses_payload,
    build_requested_attempt,
    complete_attempt_from_response,
    complete_attempt_from_transport_failure,
)
from edge_imci.generation.holistic_middle_gate import validate_middle_candidate
from edge_imci.generation.language_semantic_guards import validate_language_semantics
from edge_imci.generation.structured_extraction_bulk_wave import (
    campaign_parent_languages,
    campaign_semantics,
)


class AzureBatchArtifactError(ValueError):
    """Raised when a prepared or returned Batch artifact cannot be reconciled."""


_STRATEGY_STYLES = {
    "phc-natural-complete-v1": "NATURAL_CONVERSATIONAL_ENGLISH",
    "phc-concise-complete-v1": "CLINICAL_STANDARD_ENGLISH",
    "phc-nigerian-english-v1": "NIGERIAN_ENGLISH",
    "phc-nigerian-pidgin-v1": "NIGERIAN_PIDGIN",
    "phc-noisy-typed-english-v1": "NOISY_TYPED_ENGLISH",
    "phc-telegraphic-note-v1": "TELEGRAPHIC_PHC_NOTE",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AzureBatchArtifactError(f"{path} must contain one JSON object")
    return value


def _load_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    value = json.loads(text) if text.lstrip().startswith("[") else None
    if value is not None:
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise AzureBatchArtifactError(f"{path} JSON array must contain objects")
        return value
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise AzureBatchArtifactError(f"{path}:{line_number} must be an object")
        rows.append(item)
    return rows


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(_canonical_json(dict(item)) + "\n" for item in rows),
        encoding="utf-8",
    )


def _custom_id(request_id: str) -> str:
    return "edge-generation-" + hashlib.sha256(request_id.encode()).hexdigest()[:32]


def prepare_generation_batch(
    *,
    source_requests_path: Path,
    schedule_path: Path,
    output_dir: Path,
    deployment_name: str,
) -> dict[str, Any]:
    """Materialize an Azure Responses Global Batch input without remote I/O."""

    if not deployment_name:
        raise AzureBatchArtifactError("an exact Azure Batch deployment name is required")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"generation batch directory is not empty: {output_dir}")
    schedule = _load_json(schedule_path)
    if schedule.get("authorization", {}).get("remote_calls_authorized") is not True:
        raise PermissionError("the generation schedule does not authorize remote execution")
    requests = _load_rows(source_requests_path)
    request_by_hash = {item["request_sha256"]: item for item in requests}
    if len(request_by_hash) != len(requests):
        raise AzureBatchArtifactError("source requests contain duplicate hashes")
    configurations = {
        item["configuration_id"]: item for item in schedule["configurations"]
    }
    lines: list[dict[str, Any]] = []
    index: dict[str, Any] = {}
    for unit in schedule["units"]:
        request = request_by_hash.get(unit["source_request_sha256"])
        if request is None:
            raise AzureBatchArtifactError(
                f"schedule unit lacks source request: {unit['request_id']}"
            )
        configuration = configurations[unit["configuration_id"]]
        payload = build_azure_responses_payload(
            source_request=request,
            configuration=configuration,
            deployment_name=deployment_name,
        )
        custom_id = _custom_id(unit["request_id"])
        lines.append(
            {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses",
                "body": payload,
            }
        )
        index[custom_id] = {
            "request_id": unit["request_id"],
            "source_request_sha256": unit["source_request_sha256"],
            "unit_sha256": _canonical_hash(unit),
        }
    if len(lines) != len(schedule["units"]):
        raise AzureBatchArtifactError("generation Batch line count differs from schedule")
    _write_jsonl(output_dir / "generation_batch_input.jsonl", lines)
    _write_json(output_dir / "generation_batch_index.json", index)
    _write_json(output_dir / "schedule.json", schedule)
    manifest = {
        "pipeline_id": "edge-imci-azure-openai-generation-batch-v1",
        "status": "GENERATION_BATCH_PREPARED_ZERO_CALL",
        "generation_run_id": schedule["generation_run_id"],
        "deployment_name": deployment_name,
        "request_count": len(lines),
        "schedule_sha256": hashlib.sha256(schedule_path.read_bytes()).hexdigest(),
        "source_requests_sha256": hashlib.sha256(
            source_requests_path.read_bytes()
        ).hexdigest(),
        "batch_input_sha256": hashlib.sha256(
            (output_dir / "generation_batch_input.jsonl").read_bytes()
        ).hexdigest(),
        "remote_call_performed": False,
        "training_authorized": False,
    }
    _write_json(output_dir / "generation_batch_manifest.json", manifest)
    return manifest


def _extract_output_text(body: Mapping[str, Any]) -> str:
    direct = body.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    texts: list[str] = []
    for item in body.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if (
                isinstance(content, dict)
                and content.get("type") == "output_text"
                and isinstance(content.get("text"), str)
            ):
                texts.append(content["text"])
    if not texts:
        raise AzureBatchArtifactError("generation Batch result has no output text")
    return "".join(texts)


def _candidate_validator(variant_style: str):
    def validate(candidate, semantic_record, parent_language, strategy_id):
        baseline = validate_middle_candidate(
            candidate, semantic_record, parent_language, strategy_id
        )
        semantic = validate_language_semantics(
            candidate, semantic_record, variant_style=variant_style
        )
        errors = tuple(dict.fromkeys((*baseline.error_codes, *semantic.error_codes)))
        return type(baseline)(not errors, errors, True)

    return validate


def ingest_generation_batch_outputs(
    *,
    pipeline_dir: Path,
    batch_output_paths: Iterable[Path],
    requested_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Normalize Azure Batch output/error rows into terminal attempt JSONL."""

    schedule = _load_json(pipeline_dir / "schedule.json")
    index = _load_json(pipeline_dir / "generation_batch_index.json")
    units = {item["request_id"]: item for item in schedule["units"]}
    rows: list[dict[str, Any]] = []
    for path in batch_output_paths:
        rows.extend(_load_rows(path))
    row_by_custom_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        custom_id = row.get("custom_id")
        if custom_id not in index:
            raise AzureBatchArtifactError(f"unexpected generation custom_id: {custom_id}")
        if custom_id in row_by_custom_id:
            raise AzureBatchArtifactError(f"duplicate generation custom_id: {custom_id}")
        row_by_custom_id[custom_id] = row
    semantics = campaign_semantics()
    parents = campaign_parent_languages()
    terminals: list[dict[str, Any]] = []
    for custom_id, index_item in sorted(index.items()):
        unit = units[index_item["request_id"]]
        receipt = build_requested_attempt(
            schedule=schedule,
            unit=unit,
            requested_at=requested_at,
            retry_count=0,
        )
        row = row_by_custom_id.get(custom_id)
        if row is None:
            terminal = complete_attempt_from_transport_failure(
                receipt=receipt,
                completed_at=completed_at,
                latency_ms=0,
                error_code="AZURE_BATCH_RESULT_MISSING",
            )
        else:
            response = row.get("response") or {}
            if row.get("error") is not None or response.get("status_code") != 200:
                terminal = complete_attempt_from_transport_failure(
                    receipt=receipt,
                    completed_at=completed_at,
                    latency_ms=0,
                    error_code="AZURE_BATCH_ITEM_FAILED",
                    provider_request_id=response.get("request_id"),
                )
            else:
                body = response.get("body") or {}
                strategy_id = receipt["prompt"]["strategy_id"]
                variant_style = _STRATEGY_STYLES.get(strategy_id)
                if variant_style is None:
                    raise AzureBatchArtifactError(
                        f"no review style mapping for strategy: {strategy_id}"
                    )
                provider_response = AzureProviderResponse(
                    output_text=_extract_output_text(body),
                    provider_request_id=response.get("request_id") or body.get("id"),
                    usage=copy.deepcopy(body.get("usage") or {}),
                    latency_ms=0,
                )
                terminal = complete_attempt_from_response(
                    receipt=receipt,
                    response=provider_response,
                    completed_at=completed_at,
                    semantic_record=semantics[unit["semantic_case_id"]],
                    parent_language=parents[unit["semantic_case_id"]],
                    candidate_validator=_candidate_validator(variant_style),
                )
        terminals.append(terminal)
    _write_jsonl(pipeline_dir / "terminal_attempts.jsonl", terminals)
    status_counts: dict[str, int] = {}
    per_style: dict[str, dict[str, Any]] = {}
    for item in terminals:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
        strategy_id = (item.get("prompt") or {}).get("strategy_id")
        style = _STRATEGY_STYLES.get(strategy_id, strategy_id or "UNKNOWN")
        style_report = per_style.setdefault(
            style,
            {
                "attempts": 0,
                "status_counts": {},
                "deterministic_passes": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )
        style_report["attempts"] += 1
        style_report["status_counts"][item["status"]] = (
            style_report["status_counts"].get(item["status"], 0) + 1
        )
        style_report["deterministic_passes"] += bool(
            (item.get("validation") or {}).get("deterministic_pass")
        )
        usage = item.get("usage") or {}
        style_report["input_tokens"] += usage.get("input_tokens", 0) or 0
        style_report["output_tokens"] += usage.get("output_tokens", 0) or 0
    rates = (schedule.get("planning") or {}).get(
        "generation_batch_rates_per_million_tokens"
    )
    for style_report in per_style.values():
        style_report["deterministic_pass_rate"] = style_report[
            "deterministic_passes"
        ] / max(1, style_report["attempts"])
        style_report["status_counts"] = dict(sorted(style_report["status_counts"].items()))
        if rates:
            style_report["estimated_cost_usd"] = round(
                (
                    style_report["input_tokens"] * rates["input"]
                    + style_report["output_tokens"] * rates["output"]
                )
                / 1_000_000,
                6,
            )
    report = {
        "pipeline_id": "edge-imci-azure-openai-generation-batch-v1",
        "status": "GENERATION_BATCH_INGESTED",
        "generation_run_id": schedule["generation_run_id"],
        "scheduled": len(index),
        "provider_rows": len(row_by_custom_id),
        "terminal_attempts": len(terminals),
        "status_counts": dict(sorted(status_counts.items())),
        "per_style": dict(sorted(per_style.items())),
        "review_input": "terminal_attempts.jsonl",
        "training_authorized": False,
    }
    _write_json(pipeline_dir / "generation_ingest_report.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--source-requests", required=True)
    prepare.add_argument("--schedule", required=True)
    prepare.add_argument("--output-dir", required=True)
    prepare.add_argument("--deployment", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--pipeline-dir", required=True)
    ingest.add_argument("--batch-output", nargs="+", required=True)
    ingest.add_argument("--requested-at", required=True)
    ingest.add_argument("--completed-at", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = prepare_generation_batch(
            source_requests_path=Path(args.source_requests),
            schedule_path=Path(args.schedule),
            output_dir=Path(args.output_dir),
            deployment_name=args.deployment,
        )
    else:
        result = ingest_generation_batch_outputs(
            pipeline_dir=Path(args.pipeline_dir),
            batch_output_paths=[Path(item) for item in args.batch_output],
            requested_at=args.requested_at,
            completed_at=args.completed_at,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
