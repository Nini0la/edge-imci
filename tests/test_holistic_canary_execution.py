from __future__ import annotations

import json
from pathlib import Path

import pytest

from edge_imci.generation.azure_foundry import AzureProviderResponse
from edge_imci.generation.holistic_canary_execute import (
    AppendOnlyAttemptStore,
    CanaryExecutionStopped,
    _execution_order,
    run_authorized_canary,
)
from edge_imci.generation.holistic_canary_run import CANARY_SCHEDULE_PATH
from edge_imci.generation.holistic_variants import CANDIDATE_SCHEMA_ID


def _secure_env(path: Path) -> None:
    path.write_text(
        "AZURE_OPENAI_BASE_URL=https://fixture.services.ai.azure.com/api/projects/test\n"
        "AZURE_OPENAI_API_KEY=test-only-secret\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


class SchemaShapedTransport:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, payload: dict) -> AzureProviderResponse:
        self.calls.append(payload)
        schema = payload["text"]["format"]["schema"]
        case_id = schema["properties"]["semantic_case_id"]["enum"][0]
        strategy_id = schema["properties"]["strategy_id"]["enum"][0]
        source = json.loads(payload["input"].split("SOURCE_PACKAGE_JSON:\n", 1)[1])
        submission = "The health worker recorded all supplied encounter findings in this assessment."
        candidate = {
            "candidate_schema_id": CANDIDATE_SCHEMA_ID,
            "semantic_case_id": case_id,
            "strategy_id": strategy_id,
            "user_submission": submission,
            "fact_evidence": [
                {"fact_id": fact_id, "evidence_text": submission}
                for fact_id in source["required_fact_ids"]
            ],
        }
        return AzureProviderResponse(
            output_text=json.dumps(candidate),
            provider_request_id=f"resp-{len(self.calls)}",
            usage={"input_tokens": 100, "output_tokens": 50},
            latency_ms=10,
        )


def test_execution_order_starts_with_simple_then_complex_gate() -> None:
    schedule = json.loads(CANARY_SCHEDULE_PATH.read_text(encoding="utf-8"))
    ordered = _execution_order(schedule)
    assert [item["semantic_case_id"] for item in ordered[:2]] == [
        "hpg-001-all-negative",
        "hpg-076-complete-danger-plus-all-pathways",
    ]
    assert all(item["strategy_id"] == "phc-concise-complete-v1" for item in ordered[:2])
    assert len({item["request_id"] for item in ordered}) == 12


def test_attempt_store_keeps_requested_and_terminal_events(tmp_path: Path) -> None:
    store = AppendOnlyAttemptStore(tmp_path / "attempts")
    # The complete executor integration below supplies schema-valid records; this
    # test focuses on exclusive event paths through an actual one-unit run.
    env_path = tmp_path / ".env"
    _secure_env(env_path)
    transport = SchemaShapedTransport()
    state = run_authorized_canary(
        env_path=env_path,
        max_new_attempts=1,
        transport=transport,
        store=store,
        run_state_path=tmp_path / "run_state.json",
    )
    assert state["remote_attempts_started"] == 1
    attempt_dirs = list((tmp_path / "attempts").iterdir())
    assert len(attempt_dirs) == 1
    assert (attempt_dirs[0] / "requested.json").is_file()
    assert (attempt_dirs[0] / "terminal.json").is_file()
    assert store.latest_attempts()[0]["status"] == "PENDING_HUMAN_REVIEW"


def test_resume_does_not_repeat_completed_unit(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    _secure_env(env_path)
    store = AppendOnlyAttemptStore(tmp_path / "attempts")
    first = SchemaShapedTransport()
    run_authorized_canary(
        env_path=env_path,
        max_new_attempts=1,
        transport=first,
        store=store,
        run_state_path=tmp_path / "run_state.json",
    )
    second = SchemaShapedTransport()
    state = run_authorized_canary(
        env_path=env_path,
        max_new_attempts=1,
        transport=second,
        store=store,
        run_state_path=tmp_path / "run_state.json",
    )
    assert state["remote_attempts_started"] == 2
    assert len(second.calls) == 1
    assert store.latest_attempts()[1]["semantic_case_id"] == (
        "hpg-076-complete-danger-plus-all-pathways"
    )


def test_ambiguous_error_leaves_requested_and_blocks_resume(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    _secure_env(env_path)
    store = AppendOnlyAttemptStore(tmp_path / "attempts")

    class TimeoutTransport:
        def create(self, payload: dict) -> AzureProviderResponse:
            raise TimeoutError("uncertain outcome")

    with pytest.raises(CanaryExecutionStopped, match="TimeoutError"):
        run_authorized_canary(
            env_path=env_path,
            max_new_attempts=1,
            transport=TimeoutTransport(),
            store=store,
            run_state_path=tmp_path / "run_state.json",
        )
    assert store.latest_attempts()[0]["status"] == "REQUESTED"
    with pytest.raises(CanaryExecutionStopped, match="reconciliation"):
        run_authorized_canary(
            env_path=env_path,
            max_new_attempts=1,
            transport=SchemaShapedTransport(),
            store=store,
            run_state_path=tmp_path / "run_state.json",
        )
