"""Prepare the blocked six-style mass-generation source package without remote I/O."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from edge_imci.generation.holistic_variants import ROOT, build_source_package
from edge_imci.generation.structured_extraction_bulk_wave import campaign_semantics
from edge_imci.training.dataset_policy import parent_semantic_partition


CAMPAIGN_CONFIG_PATH = ROOT / "configs/generation/azure_batch_mass_campaign_v1.json"
REGULAR_ENGLISH_QUALIFICATION_PATH = (
    ROOT / "configs/generation/regular_english_qualification_v1.json"
)
EXPECTED_STYLES = {
    "NATURAL_CONVERSATIONAL_ENGLISH",
    "CLINICAL_STANDARD_ENGLISH",
    "NIGERIAN_ENGLISH",
    "NIGERIAN_PIDGIN",
    "NOISY_TYPED_ENGLISH",
    "TELEGRAPHIC_PHC_NOTE",
}


class MassCampaignError(ValueError):
    """Raised when a mass-campaign package is incomplete or internally inconsistent."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def load_mass_campaign_config(path: Path = CAMPAIGN_CONFIG_PATH) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise MassCampaignError("mass campaign config must be one JSON object")
    if config.get("status") != "PREPARED_BLOCKED_PENDING_QUALIFICATION_CALIBRATION_AND_AUTHORIZATION":
        raise MassCampaignError("mass campaign must remain in the blocked preparation state")
    authorization = config.get("authorization") or {}
    if any(authorization.values()):
        raise MassCampaignError("preparation config must not authorize execution or promotion")
    allocations = config["allocation"]["styles"]
    if set(allocations) != EXPECTED_STYLES:
        raise MassCampaignError("mass campaign must contain exactly the six required styles")
    if sum(allocations.values()) != config["allocation"]["total_attempts"]:
        raise MassCampaignError("style allocation does not equal total attempts")
    prompts = config["prompts"]
    if {item["variant_style"] for item in prompts} != EXPECTED_STYLES:
        raise MassCampaignError("prompt set does not cover the six required styles")
    return config


def _parent_order(parent_ids: Iterable[str], *, seed: str, style: str) -> list[str]:
    return sorted(
        parent_ids,
        key=lambda case_id: hashlib.sha256(
            f"{seed}|{style}|{case_id}".encode("utf-8")
        ).hexdigest(),
    )


def build_mass_campaign(
    config_path: Path = CAMPAIGN_CONFIG_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Build deterministic source requests, blocked schedule template, and preflight."""

    config = load_mass_campaign_config(config_path)
    semantics = campaign_semantics()
    requests: list[dict[str, Any]] = []
    units_by_style: dict[str, list[dict[str, Any]]] = {}
    configurations: list[dict[str, Any]] = []
    parent_counts: Counter[str] = Counter()
    partition_counts: Counter[str] = Counter()
    prompt_pins: dict[str, Any] = {}
    for prompt in config["prompts"]:
        style = prompt["variant_style"]
        prompt_path = ROOT / prompt["prompt_path"]
        if not prompt_path.is_file():
            raise MassCampaignError(f"missing campaign prompt: {prompt_path}")
        template = prompt_path.read_text(encoding="utf-8")
        prompt_sha = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        prompt_pins[style] = {
            "path": prompt["prompt_path"],
            "version": prompt["prompt_version"],
            "sha256": prompt_sha,
            "qualification": prompt["qualification"],
        }
        configuration_id = (
            f"azure-gpt41-20250414__{prompt['strategy_id']}__"
            f"prompt-v{prompt['prompt_version'].replace('.', '-')}"
        )
        configurations.append(
            {
                "configuration_id": configuration_id,
                "teacher_provider": config["teacher"]["provider"],
                "teacher_model": config["teacher"]["model"],
                "teacher_snapshot": config["teacher"]["snapshot"],
                "strategy_id": prompt["strategy_id"],
                "prompt_id": prompt["prompt_id"],
                "prompt_version": prompt["prompt_version"],
                "prompt_sha256": prompt_sha,
                "sampling_config": {"temperature": prompt["temperature"]},
                "max_output_tokens": config["teacher"]["max_output_tokens"],
            }
        )
        ordered_parents = _parent_order(
            semantics, seed=config["allocation"]["seed"], style=style
        )
        style_units: list[dict[str, Any]] = []
        quota = config["allocation"]["styles"][style]
        for ordinal in range(quota):
            case_id = ordered_parents[ordinal % len(ordered_parents)]
            variant_index = ordinal // len(ordered_parents) + 1
            package = build_source_package(semantics[case_id], prompt["strategy_id"])
            rendered = template.replace(
                "{{SOURCE_PACKAGE_JSON}}",
                json.dumps(package, ensure_ascii=False, sort_keys=True),
            )
            identity = {
                "experiment_id": config["campaign_id"],
                "semantic_case_id": case_id,
                "parent_partition": parent_semantic_partition(case_id),
                "strategy_id": prompt["strategy_id"],
                "variant_style": style,
                "variant_index": variant_index,
                "prompt_id": prompt["prompt_id"],
                "prompt_version": prompt["prompt_version"],
                "prompt_sha256": prompt_sha,
                "source_package_sha256": _canonical_hash(package),
            }
            request = {
                **identity,
                "request_id_suffix": f"__variant-{variant_index:04d}",
                "request_sha256": _canonical_hash({**identity, "rendered_prompt": rendered}),
                "source_package": package,
                "rendered_prompt": rendered,
            }
            requests.append(request)
            request_id = (
                f"{config['generation_run_id']}__{configuration_id}__{case_id}"
                f"__variant-{variant_index:04d}"
            )
            style_units.append(
                {
                    "request_id": request_id,
                    "configuration_id": configuration_id,
                    "semantic_case_id": case_id,
                    "strategy_id": prompt["strategy_id"],
                    "source_request_sha256": request["request_sha256"],
                    "review_item_id": "review-" + hashlib.sha256(request_id.encode()).hexdigest()[:24],
                }
            )
            parent_counts[case_id] += 1
            partition_counts[identity["parent_partition"]] += 1
        units_by_style[style] = style_units

    interleaved_units: list[dict[str, Any]] = []
    for ordinal in range(max(map(len, units_by_style.values()))):
        for prompt in config["prompts"]:
            style_units = units_by_style[prompt["variant_style"]]
            if ordinal < len(style_units):
                interleaved_units.append(style_units[ordinal])
    total = config["allocation"]["total_attempts"]
    if len(requests) != total or len(interleaved_units) != total:
        raise MassCampaignError("prepared campaign count differs from allocation")
    hashes = [item["request_sha256"] for item in requests]
    request_ids = [item["request_id"] for item in interleaved_units]
    if len(hashes) != len(set(hashes)) or len(request_ids) != len(set(request_ids)):
        raise MassCampaignError("mass campaign identities are not unique")

    schedule = {
        "schedule_schema_id": "edge-imci-holistic-teacher-bakeoff-schedule-v1",
        "generation_run_id": config["generation_run_id"],
        "experiment_id": config["campaign_id"],
        "created_at": None,
        "authorization": {
            "project_owner": None,
            "approved_at": None,
            "variant_contract_approved": False,
            "remote_calls_authorized": False,
            "budget": {
                "currency": config["cost_estimate"]["currency"],
                "maximum_amount": None,
            },
        },
        "source_pins": {"campaign_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest()},
        "retry_policy": {
            "transport_retry_limit": 1,
            "semantic_retry": False,
            "uncertain_request_policy": "RECONCILE_BEFORE_RETRY",
        },
        "planning": config["cost_estimate"],
        "configurations": configurations,
        "units": interleaved_units,
    }
    blockers = [key for key, passed in config["launch_gates"].items() if not passed]
    generation_cost_per_attempt = (
        config["cost_estimate"]["generation_tokens_per_attempt"]["input"]
        * config["cost_estimate"]["generation_batch_rates_per_million_tokens"]["input"]
        + config["cost_estimate"]["generation_tokens_per_attempt"]["output"]
        * config["cost_estimate"]["generation_batch_rates_per_million_tokens"]["output"]
    ) / 1_000_000
    preflight = {
        "campaign_id": config["campaign_id"],
        "status": "BLOCKED_NOT_AUTHORIZED",
        "request_count": total,
        "style_attempt_counts": config["allocation"]["styles"],
        "parent_count": len(semantics),
        "parent_attempt_count_range": [min(parent_counts.values()), max(parent_counts.values())],
        "partition_attempt_counts": dict(sorted(partition_counts.items())),
        "prompt_pins": prompt_pins,
        "estimated_generation_cost_usd": config["cost_estimate"]["estimated_generation_cost"],
        "estimated_generation_cost_by_style_usd": {
            style: round(count * generation_cost_per_attempt, 6)
            for style, count in config["allocation"]["styles"].items()
        },
        "required_configuration": config["required_configuration"],
        "blockers": blockers,
        "remote_call_performed": False,
        "training_authorized": False,
    }
    return requests, schedule, preflight


def prepare_mass_campaign(
    *, output_dir: Path, config_path: Path = CAMPAIGN_CONFIG_PATH
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"mass campaign output directory is not empty: {output_dir}")
    requests, schedule, preflight = build_mass_campaign(config_path)
    _write_jsonl(output_dir / "source_requests.jsonl", requests)
    _write_json(output_dir / "schedule_template.json", schedule)
    preflight["assets"] = {
        "source_requests.jsonl": hashlib.sha256(
            (output_dir / "source_requests.jsonl").read_bytes()
        ).hexdigest(),
        "schedule_template.json": hashlib.sha256(
            (output_dir / "schedule_template.json").read_bytes()
        ).hexdigest(),
    }
    _write_json(output_dir / "preflight_report.json", preflight)
    return preflight


def prepare_regular_english_canary(
    *, output_dir: Path, qualification_path: Path = REGULAR_ENGLISH_QUALIFICATION_PATH
) -> dict[str, Any]:
    """Prepare the 14-request synchronous canary package without executing it."""

    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"regular-English canary directory is not empty: {output_dir}")
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    if qualification["authorization"]["remote_calls_authorized"] is not False:
        raise MassCampaignError("regular-English canary preparation must remain unauthorized")
    semantics = campaign_semantics()
    requests: list[dict[str, Any]] = []
    configurations: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    run_id = "edge-imci-regular-english-canary-v1"
    for prompt in qualification["candidate_prompts"]:
        prompt_path = ROOT / prompt["prompt_path"]
        template = prompt_path.read_text(encoding="utf-8")
        prompt_sha = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        configuration_id = (
            f"azure-gpt41-20250414__{prompt['strategy_id']}__"
            f"prompt-v{prompt['prompt_version'].replace('.', '-')}"
        )
        configurations.append(
            {
                "configuration_id": configuration_id,
                "teacher_provider": "AZURE_OPENAI",
                "teacher_model": "gpt-4.1",
                "teacher_snapshot": "2025-04-14",
                "strategy_id": prompt["strategy_id"],
                "prompt_id": prompt["prompt_id"],
                "prompt_version": prompt["prompt_version"],
                "prompt_sha256": prompt_sha,
                "sampling_config": {"temperature": prompt["temperature"]},
                "max_output_tokens": 2200,
            }
        )
        for case_id in qualification["canary"]["case_ids"]:
            package = build_source_package(semantics[case_id], prompt["strategy_id"])
            rendered = template.replace(
                "{{SOURCE_PACKAGE_JSON}}",
                json.dumps(package, ensure_ascii=False, sort_keys=True),
            )
            identity = {
                "experiment_id": qualification["qualification_id"],
                "semantic_case_id": case_id,
                "strategy_id": prompt["strategy_id"],
                "variant_style": prompt["variant_style"],
                "variant_index": 1,
                "prompt_id": prompt["prompt_id"],
                "prompt_version": prompt["prompt_version"],
                "prompt_sha256": prompt_sha,
                "source_package_sha256": _canonical_hash(package),
            }
            request = {
                **identity,
                "request_id_suffix": "__variant-0001",
                "request_sha256": _canonical_hash({**identity, "rendered_prompt": rendered}),
                "source_package": package,
                "rendered_prompt": rendered,
            }
            requests.append(request)
            request_id = f"{run_id}__{configuration_id}__{case_id}__variant-0001"
            units.append(
                {
                    "request_id": request_id,
                    "configuration_id": configuration_id,
                    "semantic_case_id": case_id,
                    "strategy_id": prompt["strategy_id"],
                    "source_request_sha256": request["request_sha256"],
                    "review_item_id": "review-" + hashlib.sha256(request_id.encode()).hexdigest()[:24],
                }
            )
    expected = len(qualification["candidate_prompts"]) * len(
        qualification["canary"]["case_ids"]
    )
    if len(requests) != expected:
        raise MassCampaignError("regular-English canary request count differs")
    schedule = {
        "schedule_schema_id": "edge-imci-holistic-teacher-bakeoff-schedule-v1",
        "generation_run_id": run_id,
        "experiment_id": qualification["qualification_id"],
        "created_at": None,
        "authorization": {
            "project_owner": None,
            "approved_at": None,
            "variant_contract_approved": False,
            "remote_calls_authorized": False,
            "budget": {"currency": "USD", "maximum_amount": None},
        },
        "source_pins": {
            "qualification_sha256": hashlib.sha256(qualification_path.read_bytes()).hexdigest()
        },
        "retry_policy": {
            "transport_retry_limit": 1,
            "semantic_retry": False,
            "uncertain_request_policy": "RECONCILE_BEFORE_RETRY",
        },
        "configurations": configurations,
        "units": units,
    }
    _write_jsonl(output_dir / "source_requests.jsonl", requests)
    _write_json(output_dir / "schedule_template.json", schedule)
    report = {
        "status": "CANARY_PREPARED_BLOCKED_NOT_AUTHORIZED",
        "request_count": len(requests),
        "style_counts": dict(sorted(Counter(item["variant_style"] for item in requests).items())),
        "historical_evidence": qualification["historical_evidence"],
        "qualification_gates": qualification["canary"],
        "remote_call_performed": False,
        "bulk_generation_authorized": False,
    }
    _write_json(output_dir / "preflight_report.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config", default=str(CAMPAIGN_CONFIG_PATH))
    parser.add_argument("--regular-english-canary", action="store_true")
    args = parser.parse_args(argv)
    if args.regular_english_canary:
        result = prepare_regular_english_canary(output_dir=Path(args.output_dir))
    else:
        result = prepare_mass_campaign(
            output_dir=Path(args.output_dir), config_path=Path(args.config)
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
