from __future__ import annotations

import json
from pathlib import Path

from edge_imci.generation.azure_batch import (
    ingest_generation_batch_outputs,
    prepare_generation_batch,
)
from edge_imci.review.synthetic_batch import prepare_primary_review_batch


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = (
    ROOT
    / "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v16"
)


def _fixture(tmp_path: Path):
    original_schedule = json.loads((RUN_DIR / "schedule.json").read_text(encoding="utf-8"))
    terminal = next(
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((RUN_DIR / "attempts").glob("*/terminal.json"))
        if json.loads(path.read_text(encoding="utf-8"))["status"]
        == "PENDING_HUMAN_REVIEW"
    )
    unit = next(
        item
        for item in original_schedule["units"]
        if item["request_id"] == terminal["request_id"]
    )
    configuration = next(
        item
        for item in original_schedule["configurations"]
        if item["configuration_id"] == unit["configuration_id"]
    )
    schedule = {
        **original_schedule,
        "configurations": [configuration],
        "units": [unit],
    }
    schedule_path = tmp_path / "schedule.json"
    schedule_path.write_text(json.dumps(schedule), encoding="utf-8")
    source = {
        "request_sha256": unit["source_request_sha256"],
        "semantic_case_id": unit["semantic_case_id"],
        "strategy_id": configuration["strategy_id"],
        "prompt_id": configuration["prompt_id"],
        "prompt_version": configuration["prompt_version"],
        "prompt_sha256": configuration["prompt_sha256"],
        "rendered_prompt": "Render the supplied immutable test source package.",
    }
    requests_path = tmp_path / "source_requests.jsonl"
    requests_path.write_text(json.dumps(source) + "\n", encoding="utf-8")
    return schedule_path, requests_path, terminal


def test_generation_batch_preparation_and_ingestion_are_zero_call(tmp_path: Path) -> None:
    schedule, requests, terminal = _fixture(tmp_path)
    pipeline = tmp_path / "generation"
    manifest = prepare_generation_batch(
        source_requests_path=requests,
        schedule_path=schedule,
        output_dir=pipeline,
        deployment_name="gpt41-global-batch-test",
    )
    assert manifest["status"] == "GENERATION_BATCH_PREPARED_ZERO_CALL"
    assert manifest["request_count"] == 1
    assert manifest["remote_call_performed"] is False
    batch_line = json.loads((pipeline / "generation_batch_input.jsonl").read_text())
    assert batch_line["url"] == "/v1/responses"
    assert batch_line["body"]["model"] == "gpt41-global-batch-test"
    index = json.loads((pipeline / "generation_batch_index.json").read_text())
    custom_id = next(iter(index))
    provider_output = {
        "custom_id": custom_id,
        "response": {
            "status_code": 200,
            "request_id": "azure-batch-request-test",
            "body": {
                "id": "response-test",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(terminal["candidate"]),
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        },
        "error": None,
    }
    output_path = tmp_path / "provider_output.jsonl"
    output_path.write_text(json.dumps(provider_output) + "\n", encoding="utf-8")
    report = ingest_generation_batch_outputs(
        pipeline_dir=pipeline,
        batch_output_paths=[output_path],
        requested_at="2026-08-24T00:00:00Z",
        completed_at="2026-08-25T00:00:00Z",
    )
    assert report["status"] == "GENERATION_BATCH_INGESTED"
    assert report["status_counts"] == {"PENDING_HUMAN_REVIEW": 1}

    review_dir = tmp_path / "review"
    review_manifest = prepare_primary_review_batch(
        records_path=pipeline / "terminal_attempts.jsonl",
        output_dir=review_dir,
        model="reviewer-test",
    )
    assert review_manifest["input_kind"] == "GENERATION_ATTEMPTS"
    assert review_manifest["subject_count"] == 1
