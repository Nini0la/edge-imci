"""Resumable, append-only executor for the authorized GPT-4.1 canary.

This module is intentionally specific to the immutable 12-unit canary package.
It persists a REQUESTED receipt before network I/O and a distinct terminal
record afterward. A lone REQUESTED receipt is never retried automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.azure_foundry import (
    OpenAIAzureResponsesTransport,
    execute_authorized_unit,
    require_authorized_execution_config,
)
from edge_imci.generation.holistic_bakeoff import derive_resume_state
from edge_imci.generation.holistic_canary import build_canary_source_requests
from edge_imci.generation.holistic_canary_run import (
    CANARY_EXECUTION_PATH,
    CANARY_PREFLIGHT_PATH,
    CANARY_RUN_DIR,
    CANARY_RUN_ID,
    CANARY_SCHEDULE_PATH,
    validate_secret_environment,
)
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_variants import validate_attempt_record


ATTEMPTS_DIR = CANARY_RUN_DIR / "attempts"
RUN_STATE_PATH = CANARY_RUN_DIR / "run_state.json"
RESERVATION_PER_ATTEMPT_USD = Decimal("0.02")
_SUCCESS_STATUS = "PENDING_HUMAN_REVIEW"


class CanaryExecutionStopped(RuntimeError):
    """A safe stop whose message contains no provider secret or payload."""


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _exclusive_write(path: Path, value: Mapping[str, Any]) -> None:
    """Create one evidence artifact exactly once and durably flush it."""

    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_bytes(dict(value)))
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # fdopen owns the descriptor after successful construction.
        raise


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    """Replace a derived summary; immutable evidence remains in attempts/."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_bytes(dict(value)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_secure_env(env_path: Path) -> None:
    """Load only the two validated Azure names without returning their values."""

    validate_secret_environment(env_path)
    allowed = {"AZURE_OPENAI_BASE_URL", "AZURE_OPENAI_API_KEY"}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        name = key.strip()
        if name in allowed:
            os.environ[name] = value.strip()


class AppendOnlyAttemptStore:
    """Persist request and terminal events separately for crash-safe resumption."""

    def __init__(self, root: Path = ATTEMPTS_DIR) -> None:
        self.root = root

    def persist(self, attempt: dict[str, Any]) -> None:
        validate_attempt_record(attempt)
        event_name = "requested.json" if attempt["status"] == "REQUESTED" else "terminal.json"
        _exclusive_write(self.root / attempt["attempt_id"] / event_name, attempt)

    def latest_attempts(self) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        results: list[dict[str, Any]] = []
        for attempt_dir in sorted(path for path in self.root.iterdir() if path.is_dir()):
            requested_path = attempt_dir / "requested.json"
            terminal_path = attempt_dir / "terminal.json"
            if not requested_path.is_file():
                raise ValueError(f"attempt directory lacks requested receipt: {attempt_dir.name}")
            requested = _load_json(requested_path)
            validate_attempt_record(requested)
            latest = _load_json(terminal_path) if terminal_path.is_file() else requested
            validate_attempt_record(latest)
            if latest["attempt_id"] != requested["attempt_id"]:
                raise ValueError("terminal attempt ID differs from requested receipt")
            results.append(latest)
        return results


def _execution_order(schedule: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Simple gate, complex gate, then the untouched frozen schedule order."""

    units = [dict(item) for item in schedule["units"]]

    def select(case_id: str, strategy_id: str) -> dict[str, Any]:
        matches = [
            item
            for item in units
            if item["semantic_case_id"] == case_id and item["strategy_id"] == strategy_id
        ]
        if len(matches) != 1:
            raise ValueError(f"canary gate is not unique: {case_id}/{strategy_id}")
        return matches[0]

    gates = [
        select("hpg-001-all-negative", "phc-concise-complete-v1"),
        select("hpg-076-complete-danger-plus-all-pathways", "phc-concise-complete-v1"),
    ]
    gate_ids = {item["request_id"] for item in gates}
    return gates + [item for item in units if item["request_id"] not in gate_ids]


def _derived_run_state(
    schedule: Mapping[str, Any], attempts: list[dict[str, Any]], *, updated_at: str
) -> dict[str, Any]:
    resume = derive_resume_state(schedule, attempts)
    totals = {
        "input_tokens": sum(item["usage"]["input_tokens"] or 0 for item in attempts),
        "output_tokens": sum(item["usage"]["output_tokens"] or 0 for item in attempts),
        "cached_input_tokens": sum(
            item["usage"]["cached_input_tokens"] or 0 for item in attempts
        ),
    }
    started = len(attempts)
    return {
        "run_state_schema_id": "edge-imci-holistic-teacher-canary-run-state-v1",
        "generation_run_id": CANARY_RUN_ID,
        "updated_at": updated_at,
        "evidence_model": "APPEND_ONLY_REQUESTED_AND_TERMINAL_RECORDS",
        "remote_attempts_started": started,
        "terminal_attempts": sum(item["status"] != "REQUESTED" for item in attempts),
        "deterministically_reviewable_attempts": sum(
            item["status"] == _SUCCESS_STATUS for item in attempts
        ),
        "reservation_per_started_attempt_usd": float(RESERVATION_PER_ATTEMPT_USD),
        "reserved_total_usd": float(RESERVATION_PER_ATTEMPT_USD * started),
        "reservation_is_not_billing_evidence": True,
        "usage": totals,
        "resume": resume,
    }


def run_authorized_canary(
    *,
    env_path: Path,
    max_new_attempts: int | None = None,
    transport: Any | None = None,
    store: AppendOnlyAttemptStore | None = None,
    run_state_path: Path = RUN_STATE_PATH,
) -> dict[str, Any]:
    """Run pending canary units sequentially, stopping on the first unsafe result."""

    if max_new_attempts is not None and max_new_attempts < 1:
        raise ValueError("max_new_attempts must be positive")
    execution = _load_json(CANARY_EXECUTION_PATH)
    schedule = _load_json(CANARY_SCHEDULE_PATH)
    preflight = _load_json(CANARY_PREFLIGHT_PATH)
    require_authorized_execution_config(execution)
    if preflight["generation_run_id"] != CANARY_RUN_ID:
        raise ValueError("preflight belongs to a different generation run")
    if Decimal(str(preflight["exposure"]["reservation_per_attempt"])) != RESERVATION_PER_ATTEMPT_USD:
        raise ValueError("preflight reservation differs from executor reservation")

    load_secure_env(env_path)
    attempt_store = store or AppendOnlyAttemptStore()
    attempts = attempt_store.latest_attempts()
    resume = derive_resume_state(schedule, attempts)
    reconciliation = [
        item for item in resume["units"] if item["resume_state"] == "RECONCILIATION_REQUIRED"
    ]
    if reconciliation:
        raise CanaryExecutionStopped("an earlier REQUESTED attempt requires reconciliation")
    nonterminal = [
        item
        for item in resume["units"]
        if item["resume_state"] not in {"PENDING", "TERMINAL"}
    ]
    if nonterminal:
        raise CanaryExecutionStopped("the run has a nonterminal transport state")

    source_requests = {
        (item["semantic_case_id"], item["strategy_id"]): item
        for item in build_canary_source_requests()
    }
    semantics = {
        item["golden_case_id"]: item
        for item in load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    }
    parents = {
        item["golden_case_id"]: item
        for item in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
    }
    client = transport or OpenAIAzureResponsesTransport(execution)
    terminal_request_ids = {
        item["request_id"] for item in attempts if item["status"] != "REQUESTED"
    }
    pending = [
        item for item in _execution_order(schedule) if item["request_id"] not in terminal_request_ids
    ]
    if max_new_attempts is not None:
        pending = pending[:max_new_attempts]

    completed_this_invocation = 0
    for unit in pending:
        current = attempt_store.latest_attempts()
        started = len(current)
        request = source_requests[(unit["semantic_case_id"], unit["strategy_id"])]
        try:
            result = execute_authorized_unit(
                execution_config=execution,
                schedule=schedule,
                unit=unit,
                source_request=request,
                semantic_record=semantics[unit["semantic_case_id"]],
                parent_language=parents[unit["semantic_case_id"]],
                transport=client,
                persist_attempt=attempt_store.persist,
                requested_at=_utc_now(),
                completed_at=_utc_now,
                retry_count=0,
                remote_attempts_already_started=started,
                accounted_cost_usd=RESERVATION_PER_ATTEMPT_USD * started,
                maximum_next_attempt_cost_usd=RESERVATION_PER_ATTEMPT_USD,
            )
        except Exception as exc:
            latest = attempt_store.latest_attempts()
            _atomic_write(
                run_state_path,
                _derived_run_state(schedule, latest, updated_at=_utc_now()),
            )
            if isinstance(exc, CanaryExecutionStopped):
                raise
            raise CanaryExecutionStopped(
                f"provider call stopped after receipt persistence ({type(exc).__name__})"
            ) from None
        completed_this_invocation += 1
        latest = attempt_store.latest_attempts()
        _atomic_write(
            run_state_path,
            _derived_run_state(schedule, latest, updated_at=_utc_now()),
        )
        if result["status"] != _SUCCESS_STATUS:
            codes = ",".join(result["validation"]["error_codes"]) or result["status"]
            raise CanaryExecutionStopped(f"deterministic canary gate failed: {codes}")

    latest = attempt_store.latest_attempts()
    state = _derived_run_state(schedule, latest, updated_at=_utc_now())
    state["completed_this_invocation"] = completed_this_invocation
    _atomic_write(run_state_path, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--max-new-attempts", type=int)
    args = parser.parse_args()
    try:
        state = run_authorized_canary(
            env_path=args.env_file,
            max_new_attempts=args.max_new_attempts,
        )
    except CanaryExecutionStopped as exc:
        print(json.dumps({"status": "STOPPED", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": "OK",
                "completed_this_invocation": state["completed_this_invocation"],
                "remote_attempts_started": state["remote_attempts_started"],
                "deterministically_reviewable_attempts": state[
                    "deterministically_reviewable_attempts"
                ],
                "usage": state["usage"],
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
