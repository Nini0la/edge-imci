"""Prepare and execute the guarded 2,142-attempt structured-extraction language wave."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from edge_imci.corpus_policy import CorpusUse
from edge_imci.generation.azure_foundry import (
    OpenAIAzureResponsesTransport,
    complete_attempt_from_transport_failure,
    execute_authorized_unit,
    require_authorized_execution_config,
)
from edge_imci.generation.holistic_bakeoff import build_bakeoff_schedule, derive_resume_state
from edge_imci.generation.holistic_canary_execute import (
    AppendOnlyAttemptStore,
    CanaryExecutionStopped,
    _atomic_write,
    _utc_now,
    load_secure_env,
)
from edge_imci.generation.holistic_canary_run import CANARY_EXECUTION_PATH
from edge_imci.generation.holistic_golden import load_holistic_golden_suite
from edge_imci.generation.holistic_language_full import load_full_language_suite
from edge_imci.generation.holistic_middle_gate import validate_middle_candidate
from edge_imci.generation.holistic_variants import ROOT, build_source_package
from edge_imci.generation.language_semantic_guards import validate_language_semantics
from edge_imci.training.dataset_policy import parent_semantic_partition


CONTRACT_PATH = ROOT / "configs" / "generation" / "structured_extraction_bulk_wave_v1.json"
CONTRACT_ID = "edge-imci-structured-extraction-bulk-wave-v1"
RUN_ID = "structured-extraction-language-bulk-gpt41-20250414-v1"
RUN_DIR = ROOT / "experiments" / "generation" / RUN_ID
SKIP_PREFIX_ATTEMPTS = 0
SKIP_COMPLETED_RUN_ID: str | None = None
SKIP_COMPLETED_RUN_IDS: tuple[str, ...] = ()
EXPECTED_COMPLETED_SLOT_COUNT = 250
OOS_PARENTS_PATH = (
    ROOT
    / "data"
    / "training_sources"
    / "structured_extraction_out_of_scope_v1"
    / "parent_cases.jsonl"
)
STYLE_RELEASE_PATH = ROOT / "configs" / "generation" / "input_style_qualification_release_v1.json"
DATASET_POLICY_PATH = ROOT / "configs" / "training" / "structured_extraction_dataset_policy_v1.json"

STYLE_CONFIGURATIONS = (
    {
        "variant_style": "NIGERIAN_ENGLISH",
        "strategy_id": "phc-nigerian-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_nigerian_english_v1_3_1.txt",
        "prompt_id": "edge-imci-phc-nigerian-english",
        "prompt_version": "1.3.1",
        "noise_profile": [],
    },
    {
        "variant_style": "NIGERIAN_PIDGIN",
        "strategy_id": "phc-nigerian-pidgin-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_nigerian_pidgin_v1_2_1.txt",
        "prompt_id": "edge-imci-phc-nigerian-pidgin",
        "prompt_version": "1.2.1",
        "noise_profile": [],
    },
    {
        "variant_style": "NOISY_TYPED_ENGLISH",
        "strategy_id": "phc-noisy-typed-english-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_noisy_typed_english_v1_2_1.txt",
        "prompt_id": "edge-imci-phc-noisy-typed-english",
        "prompt_version": "1.2.1",
        "noise_profile": [
            "ARTICLE_OMISSION",
            "PUNCTUATION_LOSS",
            "CASING_VARIATION",
            "SENTENCE_FRAGMENTS",
            "SPELLING_NOISE",
        ],
    },
    {
        "variant_style": "TELEGRAPHIC_PHC_NOTE",
        "strategy_id": "phc-telegraphic-note-v1",
        "prompt_path": "prompts/holistic_language_variants/phc_telegraphic_note_v1_1.txt",
        "prompt_id": "edge-imci-phc-telegraphic-note",
        "prompt_version": "1.1.0",
        "noise_profile": [
            "ABBREVIATION_DENSITY_MEDIUM",
            "SENTENCE_FRAGMENTS",
            "TELEGRAPHIC_COMPRESSION",
        ],
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_contract() -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    expected = {
        "contract_id": CONTRACT_ID,
        "contract_version": "1.0.0",
        "status": "AUTHORIZED_FOR_GUARDED_EXECUTION",
        "authority": "PROJECT_OWNER_DELEGATION",
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise ValueError(f"incorrect bulk contract {key}")
    pins = contract["source_pins"]
    actual = {
        "semantic_cases_sha256": _sha256(
            ROOT / "data" / "golden" / "holistic_product_v1" / "semantic_cases.jsonl"
        ),
        "out_of_scope_training_parents_sha256": _sha256(OOS_PARENTS_PATH),
        "dataset_policy_sha256": _sha256(DATASET_POLICY_PATH),
        "style_release_sha256": _sha256(STYLE_RELEASE_PATH),
    }
    for key, value in actual.items():
        if pins.get(key) != value:
            raise ValueError(f"bulk contract source pin drift: {key}")
    authorization = contract["authorization"]
    if authorization != {
        "bulk_generation_authorized": True,
        "training_authorized": False,
        "production_clinical_use_authorized": False,
    }:
        raise ValueError("bulk authorization scope is invalid")
    if contract["wave"]["generation_run_id"] != RUN_ID:
        raise ValueError("bulk contract run ID differs from executor")
    return contract


def _oos_semantic_record(parent: dict[str, Any]) -> dict[str, Any]:
    parent_id = parent["parent_case_id"]
    encounter = copy.deepcopy(parent["model_facing_target"])
    encounter["encounter_id"] = parent_id
    encounter["schema_version"] = "edge-imci-major-sick-child-encounter-v1"
    return {
        "record_schema_id": "edge-imci-structured-extraction-generation-parent-v1",
        "golden_case_id": parent_id,
        "input": {"kind": "HOLISTIC_ENCOUNTER", "encounter": encounter},
    }


def campaign_semantics() -> dict[str, dict[str, Any]]:
    frozen = load_holistic_golden_suite(corpus_use=CorpusUse.HOLISTIC_GENERATION)
    evaluation_only = {
        "hpg-077-out-of-scope-age-1",
        "hpg-078-out-of-scope-age-60",
    }
    semantics = {
        row["golden_case_id"]: row
        for row in frozen
        if row["golden_case_id"] not in evaluation_only
    }
    if len(semantics) != 76:
        raise ValueError("bulk campaign must contain 76 frozen non-OOS-evaluation parents")
    for line in OOS_PARENTS_PATH.read_text(encoding="utf-8").splitlines():
        parent = json.loads(line)
        semantics[parent["parent_case_id"]] = _oos_semantic_record(parent)
    if len(semantics) != 78:
        raise ValueError("bulk campaign must contain 78 total parents")
    return semantics


def campaign_parent_languages() -> dict[str, dict[str, Any]]:
    parents = {
        row["golden_case_id"]: row
        for row in load_full_language_suite(corpus_use=CorpusUse.TEACHER_BAKEOFF)
        if row["golden_case_id"]
        not in {"hpg-077-out-of-scope-age-1", "hpg-078-out-of-scope-age-60"}
    }
    for parent_id in (
        "oos-extract-young-respiratory-001",
        "oos-extract-older-fever-001",
    ):
        parents[parent_id] = {
            "golden_case_id": parent_id,
            "rendering_id": f"no-canonical-rendering__{parent_id}",
            "conversation": [
                {"role": "user", "content": f"__no_canonical_user__{parent_id}"},
                {"role": "assistant", "content": ""},
            ],
            "alignment": {},
        }
    if len(parents) != 78:
        raise ValueError("bulk campaign parent-language map must contain 78 parents")
    return parents


def _parent_order(parent_ids: list[str], seed: str) -> list[str]:
    return sorted(
        parent_ids,
        key=lambda parent_id: hashlib.sha256(f"{seed}|order|{parent_id}".encode()).hexdigest(),
    )


def _seventh_slot_styles(parent_order: list[str], seed: str) -> dict[str, set[int]]:
    missing_groups: dict[int, list[str]] = {index: [] for index in range(4)}
    for index, parent_id in enumerate(parent_order):
        missing_groups[index % 4].append(parent_id)
    extra_quotas = {0: 10, 1: 10, 2: 8, 3: 8}
    extras: set[str] = set()
    for style_index, group in missing_groups.items():
        ranked = sorted(
            group,
            key=lambda parent_id: hashlib.sha256(
                f"{seed}|extra|{style_index}|{parent_id}".encode()
            ).hexdigest(),
        )
        extras.update(ranked[: extra_quotas[style_index]])
    result: dict[str, set[int]] = {}
    for index, parent_id in enumerate(parent_order):
        missing = index % 4
        styles = {0, 1, 2, 3} - {missing}
        if parent_id in extras:
            styles.add(missing)
        result[parent_id] = styles
    return result


def build_requests_and_order() -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    contract = load_contract()
    semantics = campaign_semantics()
    seed = contract["allocation"]["seed"]
    parents = _parent_order(list(semantics), seed)
    seventh = _seventh_slot_styles(parents, seed)
    requests: list[dict[str, Any]] = []
    request_hash_by_key: dict[tuple[str, int, int], str] = {}
    parent_attempts: dict[str, int] = {parent_id: 0 for parent_id in parents}
    style_attempts = {style["variant_style"]: 0 for style in STYLE_CONFIGURATIONS}
    partition_attempts: dict[str, int] = {}
    for style_index, style in enumerate(STYLE_CONFIGURATIONS):
        prompt_path = ROOT / style["prompt_path"]
        template = prompt_path.read_text(encoding="utf-8")
        prompt_sha = _sha256(prompt_path)
        expected_pin = contract["qualified_prompt_pins"][style["variant_style"]]
        if expected_pin != {"version": style["prompt_version"], "sha256": prompt_sha}:
            raise ValueError(f"qualified prompt pin drift: {style['variant_style']}")
        for parent_id in parents:
            slots = range(1, 8) if style_index in seventh[parent_id] else range(1, 7)
            package = build_source_package(semantics[parent_id], style["strategy_id"])
            rendered = template.replace(
                "{{SOURCE_PACKAGE_JSON}}",
                json.dumps(package, ensure_ascii=False, sort_keys=True),
            )
            for variant_index in slots:
                identity = {
                    "experiment_id": "structured-extraction-language-bulk-v1",
                    "semantic_case_id": parent_id,
                    "parent_partition": parent_semantic_partition(parent_id),
                    "strategy_id": style["strategy_id"],
                    "variant_style": style["variant_style"],
                    "noise_profile": style["noise_profile"],
                    "variant_index": variant_index,
                    "prompt_id": style["prompt_id"],
                    "prompt_version": style["prompt_version"],
                    "prompt_sha256": prompt_sha,
                    "source_package_sha256": _canonical_hash(package),
                }
                request_sha = _canonical_hash({**identity, "rendered_prompt": rendered})
                request = {
                    **identity,
                    "request_id_suffix": f"__variant-{variant_index:04d}",
                    "request_sha256": request_sha,
                    "source_package": package,
                    "rendered_prompt": rendered,
                }
                requests.append(request)
                request_hash_by_key[(parent_id, style_index, variant_index)] = request_sha
                parent_attempts[parent_id] += 1
                style_attempts[style["variant_style"]] += 1
                partition = identity["parent_partition"]
                partition_attempts[partition] = partition_attempts.get(partition, 0) + 1
    desired_hash_order: list[str] = []
    for variant_index in range(1, 7):
        for style_offset in range(4):
            for parent_index, parent_id in enumerate(parents):
                style_index = (parent_index + style_offset) % 4
                desired_hash_order.append(
                    request_hash_by_key[(parent_id, style_index, variant_index)]
                )
    for parent_index, parent_id in enumerate(parents):
        for style_offset in range(4):
            style_index = (parent_index + style_offset) % 4
            key = (parent_id, style_index, 7)
            if key in request_hash_by_key:
                desired_hash_order.append(request_hash_by_key[key])
    if len(requests) != 2142 or len(desired_hash_order) != 2142:
        raise ValueError("bulk allocation must contain exactly 2,142 attempts")
    if set(desired_hash_order) != {item["request_sha256"] for item in requests}:
        raise ValueError("bulk order and request set differ")
    if sorted(parent_attempts.values()).count(28) != 36:
        raise ValueError("bulk parent allocation does not have 36 expanded parents")
    if style_attempts != contract["allocation"]["expected_style_attempts"]:
        raise ValueError(f"bulk style allocation drift: {style_attempts}")
    manifest = {
        "campaign_parent_count": len(parents),
        "campaign_parent_ids": parents,
        "campaign_parent_set_sha256": _canonical_hash(sorted(parents)),
        "parent_attempt_counts": parent_attempts,
        "style_attempt_counts": style_attempts,
        "partition_attempt_counts": partition_attempts,
        "first_78_unique_parent_count": len(
            {
                next(
                    item["semantic_case_id"]
                    for item in requests
                    if item["request_sha256"] == request_sha
                )
                for request_sha in desired_hash_order[:78]
            }
        ),
    }
    if manifest["first_78_unique_parent_count"] != 78:
        raise ValueError("first 78 units must cover every campaign parent")
    return requests, desired_hash_order, manifest


def _candidate_validator(
    candidate: dict[str, Any],
    semantic_record: dict[str, Any],
    parent_language: dict[str, Any],
    strategy_id: str,
):
    baseline = validate_middle_candidate(
        candidate, semantic_record, parent_language, strategy_id
    )
    style = next(item for item in STYLE_CONFIGURATIONS if item["strategy_id"] == strategy_id)
    semantic = validate_language_semantics(
        candidate,
        semantic_record,
        variant_style=style["variant_style"],
    )
    errors = tuple(dict.fromkeys((*baseline.error_codes, *semantic.error_codes)))
    return type(baseline)(not errors, errors, True)


def _write_json(name: str, value: Any) -> None:
    (RUN_DIR / f"{name}.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _completed_slot_from_terminal(
    terminal: dict[str, Any],
    prior_requests: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, str, int]:
    """Recover an immutable allocation slot, including from a compacted run.

    Completed attempt receipts retain all three slot coordinates. The original
    source-request manifest is preferred when present, but it may be compacted
    after a run stops because rendered prompts make that file needlessly large.
    """

    if prior_requests is not None:
        request = prior_requests[terminal["request_sha256"]]
        return (
            request["semantic_case_id"],
            request["strategy_id"],
            request["variant_index"],
        )
    match = re.search(r"__variant-(\d+)$", terminal["request_id"])
    if match is None:
        raise ValueError("completed request ID does not identify its variant slot")
    prompt = terminal.get("prompt") or {}
    strategy_id = prompt.get("strategy_id")
    if not strategy_id:
        candidate = terminal.get("candidate") or {}
        strategy_id = candidate.get("strategy_id")
    if not strategy_id:
        raise ValueError("completed attempt does not identify its strategy")
    return (
        terminal["semantic_case_id"],
        strategy_id,
        int(match.group(1)),
    )


def _terminal_completes_language_slot(terminal: dict[str, Any]) -> bool:
    """Return false only when no candidate could have been produced."""

    return terminal.get("status") != "TRANSPORT_FAILED"


def prepare(*, approved_by: str, approved_at: str) -> dict[str, Any]:
    if RUN_DIR.exists():
        raise FileExistsError(f"bulk run package already exists: {RUN_DIR}")
    contract = load_contract()
    requests, desired_order, manifest = build_requests_and_order()
    skip_modes = sum(
        bool(value)
        for value in (
            SKIP_PREFIX_ATTEMPTS,
            SKIP_COMPLETED_RUN_ID,
            SKIP_COMPLETED_RUN_IDS,
        )
    )
    if skip_modes > 1:
        raise ValueError("continuation must use exactly one skip mechanism")
    skipped: set[str] = set()
    skipped_slots: set[tuple[str, str, int]] = set()
    if SKIP_PREFIX_ATTEMPTS:
        skipped = set(desired_order[:SKIP_PREFIX_ATTEMPTS])
    elif SKIP_COMPLETED_RUN_ID:
        prior_attempts = (
            ROOT / "experiments" / "generation" / SKIP_COMPLETED_RUN_ID / "attempts"
        )
        for terminal_path in prior_attempts.glob("*/terminal.json"):
            terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
            skipped.add(terminal["request_sha256"])
        if len(skipped) != 31:
            raise ValueError(
                f"continuation requires exactly 31 completed prior requests, found {len(skipped)}"
            )
    elif SKIP_COMPLETED_RUN_IDS:
        for prior_run_id in SKIP_COMPLETED_RUN_IDS:
            prior_run_dir = ROOT / "experiments" / "generation" / prior_run_id
            prior_requests_path = prior_run_dir / "source_requests.json"
            prior_requests = None
            if prior_requests_path.is_file():
                prior_requests = {
                    item["request_sha256"]: item
                    for item in json.loads(prior_requests_path.read_text(encoding="utf-8"))
                }
            for terminal_path in (prior_run_dir / "attempts").glob("*/terminal.json"):
                terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
                if not _terminal_completes_language_slot(terminal):
                    # A transport-only outcome produced no language candidate and
                    # therefore did not complete its allocated semantic slot.
                    # A later exact-slot continuation may retry that same slot.
                    continue
                skipped_slots.add(_completed_slot_from_terminal(terminal, prior_requests))
        if len(skipped_slots) != EXPECTED_COMPLETED_SLOT_COUNT:
            raise ValueError(
                "slot continuation has the wrong number of completed slots: "
                f"found {len(skipped_slots)}"
            )
        request_by_hash = {item["request_sha256"]: item for item in requests}
        skipped = {
            request_sha
            for request_sha in desired_order
            if (
                request_by_hash[request_sha]["semantic_case_id"],
                request_by_hash[request_sha]["strategy_id"],
                request_by_hash[request_sha]["variant_index"],
            )
            in skipped_slots
        }
    if skipped:
        if not skipped <= set(desired_order):
            raise ValueError("prior completed requests are not a subset of this campaign")
        desired_order = [item for item in desired_order if item not in skipped]
        requests = [item for item in requests if item["request_sha256"] not in skipped]
        manifest = {
            **manifest,
            "continuation_skipped_attempts": len(skipped),
            "continuation_skip_mode": (
                "EXACT_COMPLETED_ALLOCATION_SLOTS"
                if SKIP_COMPLETED_RUN_IDS
                else (
                    "EXACT_COMPLETED_REQUEST_HASHES"
                    if SKIP_COMPLETED_RUN_ID
                    else "SCHEDULE_PREFIX"
                )
            ),
            "continuation_prior_run_id": SKIP_COMPLETED_RUN_ID,
            "continuation_prior_run_ids": list(SKIP_COMPLETED_RUN_IDS),
            "continuation_scheduled_attempts": len(requests),
            "combined_campaign_attempts": len(requests) + len(skipped),
        }
    expected_remote_attempts = contract["wave"]["maximum_remote_attempts"]
    if len(requests) != expected_remote_attempts:
        raise ValueError(
            f"prepared request count {len(requests)} differs from contract {expected_remote_attempts}"
        )
    RUN_DIR.mkdir(parents=True)
    configurations = []
    for style in STYLE_CONFIGURATIONS:
        prompt_path = ROOT / style["prompt_path"]
        configurations.append(
            {
                "configuration_id": (
                    "azure-gpt41-20250414__"
                    f"{style['strategy_id']}__prompt-v{style['prompt_version'].replace('.', '-')}"
                ),
                "teacher_provider": "AZURE_OPENAI",
                "teacher_model": "gpt-4.1",
                "teacher_snapshot": "2025-04-14",
                "strategy_id": style["strategy_id"],
                "prompt_id": style["prompt_id"],
                "prompt_version": style["prompt_version"],
                "prompt_sha256": _sha256(prompt_path),
                "sampling_config": {"temperature": style.get("temperature", 0.7)},
                "max_output_tokens": 2200,
            }
        )
    schedule = build_bakeoff_schedule(
        generation_run_id=RUN_ID,
        created_at=approved_at,
        authorization={
            "project_owner": approved_by,
            "approved_at": approved_at,
            "variant_contract_approved": True,
            "remote_calls_authorized": True,
            "budget": {
                "currency": "USD",
                "maximum_amount": contract["wave"]["maximum_budget_usd"],
            },
        },
        teacher_configurations=configurations,
        source_requests=requests,
    )
    units_by_hash = {item["source_request_sha256"]: item for item in schedule["units"]}
    schedule["units"] = [units_by_hash[request_hash] for request_hash in desired_order]
    schedule["retry_policy"]["transport_retry_limit"] = contract["wave"][
        "transport_retry_limit"
    ]
    # Keep the shared schedule schema closed; bulk-specific pins live in the
    # preflight and the canonical contract. The validator slot identifies this
    # run's exact executor/validator implementation.
    schedule["source_pins"]["validator_sha256"] = _sha256(Path(__file__))
    execution = copy.deepcopy(_load_json(CANARY_EXECUTION_PATH))
    execution["limits"] = {
        "maximum_remote_attempts": contract["wave"]["maximum_remote_attempts"],
        "maximum_budget_usd": contract["wave"]["maximum_budget_usd"],
    }
    require_authorized_execution_config(execution)
    preflight = {
        "preflight_schema_id": "edge-imci-structured-extraction-bulk-preflight-v1",
        "generation_run_id": RUN_ID,
        "status": "AUTHORIZED_NOT_STARTED",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "contract_id": contract["contract_id"],
        "contract_sha256": _sha256(CONTRACT_PATH),
        "style_release_sha256": _sha256(STYLE_RELEASE_PATH),
        "dataset_policy_sha256": _sha256(DATASET_POLICY_PATH),
        "out_of_scope_training_parents_sha256": _sha256(OOS_PARENTS_PATH),
        "campaign_parent_set_sha256": manifest["campaign_parent_set_sha256"],
        "bulk_runner_sha256": _sha256(Path(__file__)),
        "scheduled_attempts": len(requests),
        "maximum_budget_usd": contract["wave"]["maximum_budget_usd"],
        "maximum_reserved_total_usd": (
            contract["wave"]["reservation_per_started_attempt_usd"] * len(requests)
        ),
        "teacher_target_blind": True,
        "semantic_retries": False,
        "training_authorized": False,
        "allocation_manifest": manifest,
        "tranches": contract["wave"]["tranches"],
    }
    _write_json("azure_execution_config", execution)
    _write_json("schedule", schedule)
    _write_json("source_requests", requests)
    _write_json("preflight", preflight)
    (RUN_DIR / "preflight.yaml").write_text(
        "# Generated from preflight.json; edit canonical JSON.\n"
        + yaml.safe_dump(preflight, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    (RUN_DIR / "README.md").write_text(
        "# Structured-extraction language bulk wave v1\n\n"
        "> **Authority:** PROJECT_OWNER_DELEGATED_EXECUTION · **Lifecycle:** PREPARED_GUARDED\n\n"
        f"This immutable package schedules {len(requests):,} target-blind Azure GPT-4.1 attempts over 78 campaign parents and four qualified input styles. Rejected candidates are evidence, not corpus records; training remains unauthorized.\n",
        encoding="utf-8",
    )
    return preflight


def _state(
    schedule: dict[str, Any],
    attempts: list[dict[str, Any]],
    requests_by_hash: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    contract = load_contract()
    by_style: dict[str, dict[str, int]] = {}
    by_partition: dict[str, dict[str, int]] = {}
    status_counts: dict[str, int] = {}
    for attempt in attempts:
        request = requests_by_hash[attempt["request_sha256"]]
        status = attempt["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        for key, name in (
            ("variant_style", request["variant_style"]),
            ("parent_partition", request["parent_partition"]),
        ):
            destination = by_style if key == "variant_style" else by_partition
            counts = destination.setdefault(name, {"attempts": 0, "passes": 0, "rejections": 0, "transport_failures": 0})
            counts["attempts"] += 1
            if status == "PENDING_HUMAN_REVIEW":
                counts["passes"] += 1
            elif status in {"PARSE_FAILED", "DETERMINISTIC_REJECTED"}:
                counts["rejections"] += 1
            elif status == "TRANSPORT_FAILED":
                counts["transport_failures"] += 1
    started = len(attempts)
    reservation = Decimal(str(contract["wave"]["reservation_per_started_attempt_usd"]))
    return {
        "run_state_schema_id": "edge-imci-structured-extraction-bulk-state-v1",
        "generation_run_id": RUN_ID,
        "updated_at": _utc_now(),
        "remote_attempts_started": started,
        "terminal_attempts": sum(item["status"] != "REQUESTED" for item in attempts),
        "deterministic_passes": status_counts.get("PENDING_HUMAN_REVIEW", 0),
        "deterministic_rejections": status_counts.get("DETERMINISTIC_REJECTED", 0)
        + status_counts.get("PARSE_FAILED", 0),
        "status_counts": status_counts,
        "by_style": by_style,
        "by_partition": by_partition,
        "reserved_total_usd": float(reservation * started),
        "reservation_is_not_billing_evidence": True,
        "usage": {
            "input_tokens": sum(item["usage"]["input_tokens"] or 0 for item in attempts),
            "output_tokens": sum(item["usage"]["output_tokens"] or 0 for item in attempts),
            "cached_input_tokens": sum(item["usage"]["cached_input_tokens"] or 0 for item in attempts),
        },
        "resume": derive_resume_state(schedule, attempts),
    }


def _require_prior_tranche_release(contract: dict[str, Any], tranche_id: str) -> None:
    tranches = contract["wave"]["tranches"]
    index = next(index for index, item in enumerate(tranches) if item["tranche_id"] == tranche_id)
    if index == 0:
        return
    prior = tranches[index - 1]
    release_path = RUN_DIR / "reviews" / f"{prior['tranche_id']}_release.json"
    release = _load_json(release_path) if release_path.is_file() else None
    if not release or release.get("status") != "RELEASED":
        raise CanaryExecutionStopped(f"{prior['tranche_id']} review release is required")
    if release.get("cumulative_attempts") != prior["cumulative_attempts"]:
        raise CanaryExecutionStopped("prior tranche release has the wrong boundary")
    if release.get("contract_sha256") != _sha256(CONTRACT_PATH):
        raise CanaryExecutionStopped("prior tranche release contract pin drift")


def execute(*, env_path: Path, tranche_id: str) -> dict[str, Any]:
    contract = load_contract()
    tranche = next(
        (item for item in contract["wave"]["tranches"] if item["tranche_id"] == tranche_id),
        None,
    )
    if tranche is None:
        raise ValueError(f"unknown tranche: {tranche_id}")
    _require_prior_tranche_release(contract, tranche_id)
    execution = _load_json(RUN_DIR / "azure_execution_config.json")
    schedule = _load_json(RUN_DIR / "schedule.json")
    preflight = _load_json(RUN_DIR / "preflight.json")
    if preflight["status"] != "AUTHORIZED_NOT_STARTED":
        raise ValueError("bulk preflight is not authorized")
    require_authorized_execution_config(execution)
    load_secure_env(env_path)
    requests_by_hash = {
        item["request_sha256"]: item
        for item in json.loads((RUN_DIR / "source_requests.json").read_text(encoding="utf-8"))
    }
    semantics = campaign_semantics()
    parents = campaign_parent_languages()
    store = AppendOnlyAttemptStore(RUN_DIR / "attempts")
    attempts = store.latest_attempts()
    resume = derive_resume_state(schedule, attempts)
    if any(item["resume_state"] == "RECONCILIATION_REQUIRED" for item in resume["units"]):
        raise CanaryExecutionStopped("an earlier request requires reconciliation")
    if len(attempts) > tranche["cumulative_attempts"]:
        raise CanaryExecutionStopped("run has already passed the requested tranche boundary")
    needed = tranche["cumulative_attempts"] - len(attempts)
    if needed == 0:
        return _state(schedule, attempts, requests_by_hash)
    completed = {item["request_id"] for item in attempts if item["status"] != "REQUESTED"}
    pending = [item for item in schedule["units"] if item["request_id"] not in completed]
    work = pending[:needed]
    if len(work) != needed:
        raise CanaryExecutionStopped("schedule lacks enough pending units for tranche")
    transport = OpenAIAzureResponsesTransport(execution)
    reservation = Decimal(str(contract["wave"]["reservation_per_started_attempt_usd"]))
    concurrency = contract["wave"]["maximum_concurrency"]
    started_before = len(attempts)

    def run_one(unit: dict[str, Any], ordinal: int) -> Exception | None:
        request = requests_by_hash[unit["source_request_sha256"]]
        try:
            execute_authorized_unit(
                execution_config=execution,
                schedule=schedule,
                unit=unit,
                source_request=request,
                semantic_record=semantics[unit["semantic_case_id"]],
                parent_language=parents[unit["semantic_case_id"]],
                transport=transport,
                persist_attempt=store.persist,
                requested_at=_utc_now(),
                completed_at=_utc_now,
                retry_count=0,
                remote_attempts_already_started=started_before + ordinal,
                accounted_cost_usd=reservation * (started_before + ordinal),
                maximum_next_attempt_cost_usd=reservation,
                candidate_validator=_candidate_validator,
            )
        except Exception as exc:  # preserve the receipt and stop after this microbatch
            latest = store.latest_attempts()
            unresolved = [
                item
                for item in latest
                if item["request_id"] == unit["request_id"] and item["status"] == "REQUESTED"
            ]
            if len(unresolved) == 1:
                store.persist(
                    complete_attempt_from_transport_failure(
                        receipt=unresolved[0],
                        completed_at=_utc_now(),
                        latency_ms=0,
                        error_code="PROVIDER_CALL_FAILED_OUTCOME_UNCERTAIN",
                    )
                )
            return exc
        return None

    for batch_start in range(0, len(work), concurrency):
        batch = work[batch_start : batch_start + concurrency]
        failures: list[Exception] = []
        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = {
                pool.submit(run_one, unit, batch_start + offset): unit
                for offset, unit in enumerate(batch)
            }
            for future in as_completed(futures):
                failure = future.result()
                if failure is not None:
                    failures.append(failure)
        current = store.latest_attempts()
        _atomic_write(RUN_DIR / "run_state.json", _state(schedule, current, requests_by_hash))
        if failures:
            raise CanaryExecutionStopped(
                f"bulk provider microbatch stopped after {type(failures[0]).__name__}"
            )
    result = _state(schedule, store.latest_attempts(), requests_by_hash)
    _atomic_write(RUN_DIR / "run_state.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute"))
    parser.add_argument("--approved-by", default="Niniola Adegboyega")
    parser.add_argument("--approved-at")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--tranche", choices=("T1", "T2", "T3"), default="T1")
    args = parser.parse_args()
    if args.command == "prepare":
        approved_at = args.approved_at or datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        preflight = prepare(approved_by=args.approved_by, approved_at=approved_at)
        print(json.dumps({"status": "PREPARED", "scheduled_attempts": preflight["scheduled_attempts"]}))
        return 0
    try:
        result = execute(env_path=args.env_file, tranche_id=args.tranche)
    except CanaryExecutionStopped as exc:
        print(json.dumps({"status": "STOPPED", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": "OK",
                "attempts": result["remote_attempts_started"],
                "deterministic_passes": result["deterministic_passes"],
                "deterministic_rejections": result["deterministic_rejections"],
                "by_style": result["by_style"],
                "usage": result["usage"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
