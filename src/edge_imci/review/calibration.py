"""Prepare and score a frozen reviewer calibration set from delegated reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from edge_imci.generation.holistic_variants import ROOT
from edge_imci.review.synthetic_batch import (
    REVIEW_CONTRACT_PATH,
    build_review_subjects_from_generation_attempts,
    ingest_primary_reviews,
    load_review_contract,
    prepare_primary_review_batch,
)


HISTORICAL_REVIEWS = (
    ROOT
    / "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v3/reviews/T1_review.json",
    ROOT
    / "experiments/generation/structured-extraction-language-bulk-gpt41-20250414-v4/reviews/T2_review.json",
)


class CalibrationError(ValueError):
    """Raised when calibration evidence cannot be reconciled."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def _human_label(decision: str) -> str:
    if decision.startswith("SEMANTIC_APPROVE"):
        return "PASS"
    if decision == "SEMANTIC_REJECT":
        return "FAIL"
    raise CalibrationError(f"unsupported historical review decision: {decision}")


def _terminal_for_attempt(attempt_id: str) -> dict[str, Any]:
    run_id = attempt_id.split("__", 1)[0]
    path = ROOT / "experiments/generation" / run_id / "attempts" / attempt_id / "terminal.json"
    if not path.is_file():
        raise CalibrationError(f"historical terminal is missing: {attempt_id}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("attempt_id") != attempt_id:
        raise CalibrationError(f"historical terminal identity differs: {attempt_id}")
    return value


def _rank(seed: str, value: str) -> str:
    return hashlib.sha256(f"{seed}|{value}".encode("utf-8")).hexdigest()


def historical_calibration_cases(
    *, maximum_cases: int = 64, seed: str = "edge-imci-review-calibration-v1"
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select a deterministic, label-balanced set of parseable historical cases."""

    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen: set[str] = set()
    for review_path in HISTORICAL_REVIEWS:
        review = json.loads(review_path.read_text(encoding="utf-8"))
        for decision in review["decisions"]:
            attempt_id = decision["attempt_id"]
            if attempt_id in seen:
                continue
            seen.add(attempt_id)
            terminal = _terminal_for_attempt(attempt_id)
            if not isinstance(terminal.get("candidate"), dict):
                continue
            subject = build_review_subjects_from_generation_attempts([terminal])[0]
            label = {
                "subject_id": subject["subject_id"],
                "attempt_id": attempt_id,
                "variant_style": subject["variant_style"],
                "human_label": _human_label(decision["review_decision"]),
                "human_decision": decision["review_decision"],
                "high_risk": subject["high_risk"],
                "rationale": decision["rationale"],
                "source_review": str(review_path.relative_to(ROOT)),
            }
            candidates.append((terminal, label))
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for terminal, label in candidates:
        grouped[(label["variant_style"], label["human_label"])].append((terminal, label))
    for values in grouped.values():
        values.sort(key=lambda item: _rank(seed, item[1]["attempt_id"]))

    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    keys = sorted(grouped)
    cursor = 0
    while len(selected) < min(maximum_cases, len(candidates)):
        added = False
        for key in keys:
            values = grouped[key]
            if cursor < len(values) and len(selected) < maximum_cases:
                selected.append(values[cursor])
                added = True
        if not added:
            break
        cursor += 1
    attempts = [item[0] for item in selected]
    labels = [item[1] for item in selected]
    if not attempts or {item["human_label"] for item in labels} != {"PASS", "FAIL"}:
        raise CalibrationError("calibration selection must contain PASS and FAIL labels")
    return attempts, labels


def prepare_historical_calibration(
    *,
    output_dir: Path,
    model: str | None = None,
    maximum_cases: int = 64,
    contract_path: Path = REVIEW_CONTRACT_PATH,
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"calibration output directory is not empty: {output_dir}")
    attempts, labels = historical_calibration_cases(maximum_cases=maximum_cases)
    attempts_path = output_dir / "historical_attempts.jsonl"
    labels_path = output_dir / "human_labels.jsonl"
    _write_jsonl(attempts_path, attempts)
    _write_jsonl(labels_path, labels)
    manifest = prepare_primary_review_batch(
        records_path=attempts_path,
        output_dir=output_dir / "review_pipeline",
        model=model,
        contract_path=contract_path,
    )
    summary = {
        "status": "CALIBRATION_BATCH_PREPARED_ZERO_CALL",
        "case_count": len(labels),
        "label_counts": dict(sorted(Counter(item["human_label"] for item in labels).items())),
        "style_counts": dict(sorted(Counter(item["variant_style"] for item in labels).items())),
        "primary_model": manifest["primary_model"],
        "batch_input": "review_pipeline/primary_batch_input.jsonl",
        "remote_call_performed": False,
    }
    _write_json(output_dir / "calibration_manifest.json", summary)
    return summary


def score_historical_calibration(
    *,
    calibration_dir: Path,
    primary_output_path: Path,
    contract_path: Path = REVIEW_CONTRACT_PATH,
) -> dict[str, Any]:
    """Measure agreement, false acceptance, and false rejection from Batch output."""

    contract = load_review_contract(contract_path)
    pipeline_dir = calibration_dir / "review_pipeline"
    ingest_primary_reviews(
        pipeline_dir=pipeline_dir,
        primary_output_path=primary_output_path,
        contract_path=contract_path,
    )
    labels = {
        item["subject_id"]: item
        for item in (
            json.loads(line)
            for line in (calibration_dir / "human_labels.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    receipts = [
        json.loads(line)
        for line in (pipeline_dir / "primary_reviews.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    valid = [item for item in receipts if item["status"] == "VALID"]
    confusion = Counter()
    per_style: dict[str, Counter[str]] = defaultdict(Counter)
    for receipt in valid:
        human = labels[receipt["subject_id"]]["human_label"]
        predicted = "PASS" if receipt["review"]["verdict"] == "PASS" else "FAIL"
        confusion[f"human_{human.lower()}_predicted_{predicted.lower()}"] += 1
        per_style[labels[receipt["subject_id"]]["variant_style"]][
            f"human_{human.lower()}_predicted_{predicted.lower()}"
        ] += 1
    human_fail = sum(item["human_label"] == "FAIL" for item in labels.values())
    human_pass = sum(item["human_label"] == "PASS" for item in labels.values())
    high_risk_fail = sum(
        item["human_label"] == "FAIL" and item["high_risk"] for item in labels.values()
    )
    false_acceptance = confusion["human_fail_predicted_pass"] / max(1, human_fail)
    false_rejection = confusion["human_pass_predicted_fail"] / max(1, human_pass)
    high_risk_false_accepts = sum(
        receipt["status"] == "VALID"
        and labels[receipt["subject_id"]]["human_label"] == "FAIL"
        and labels[receipt["subject_id"]]["high_risk"]
        and receipt["review"]["verdict"] == "PASS"
        for receipt in receipts
    )
    high_risk_false_acceptance = high_risk_false_accepts / max(1, high_risk_fail)
    agreement = (
        confusion["human_pass_predicted_pass"] + confusion["human_fail_predicted_fail"]
    ) / max(1, len(labels))
    completion = len(valid) / max(1, len(labels))
    gates_config = contract["calibration"]
    gates = [
        {"gate": "MINIMUM_CASES", "value": len(labels), "threshold": gates_config["minimum_cases"], "passed": len(labels) >= gates_config["minimum_cases"]},
        {"gate": "COMPLETION_RATE", "value": completion, "threshold": gates_config["minimum_completion_rate"], "passed": completion >= gates_config["minimum_completion_rate"]},
        {"gate": "AGREEMENT_RATE", "value": agreement, "threshold": gates_config["minimum_agreement_rate"], "passed": agreement >= gates_config["minimum_agreement_rate"]},
        {"gate": "FALSE_ACCEPTANCE_RATE", "value": false_acceptance, "threshold": gates_config["maximum_false_acceptance_rate"], "passed": false_acceptance <= gates_config["maximum_false_acceptance_rate"]},
        {"gate": "HIGH_RISK_FALSE_ACCEPTANCE_RATE", "value": high_risk_false_acceptance, "threshold": gates_config["maximum_high_risk_false_acceptance_rate"], "passed": high_risk_false_acceptance <= gates_config["maximum_high_risk_false_acceptance_rate"]},
        {"gate": "FALSE_REJECTION_RATE", "value": false_rejection, "threshold": gates_config["maximum_false_rejection_rate"], "passed": false_rejection <= gates_config["maximum_false_rejection_rate"]},
    ]
    report = {
        "status": "CALIBRATION_PASSED" if all(item["passed"] for item in gates) else "CALIBRATION_FAILED",
        "case_count": len(labels),
        "valid_prediction_count": len(valid),
        "agreement_rate": agreement,
        "false_acceptance_rate": false_acceptance,
        "false_rejection_rate": false_rejection,
        "high_risk_false_acceptance_rate": high_risk_false_acceptance,
        "confusion": dict(sorted(confusion.items())),
        "per_style_confusion": {
            style: dict(sorted(values.items())) for style, values in sorted(per_style.items())
        },
        "gates": gates,
        "automatic_prompt_adjustment_performed": False,
    }
    _write_json(calibration_dir / "calibration_report.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--output-dir", required=True)
    prepare.add_argument("--model")
    prepare.add_argument("--maximum-cases", type=int, default=64)
    prepare.add_argument("--contract", default=str(REVIEW_CONTRACT_PATH))
    score = commands.add_parser("score")
    score.add_argument("--calibration-dir", required=True)
    score.add_argument("--primary-output", required=True)
    score.add_argument("--contract", default=str(REVIEW_CONTRACT_PATH))
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare_historical_calibration(
            output_dir=Path(args.output_dir),
            model=args.model,
            maximum_cases=args.maximum_cases,
            contract_path=Path(args.contract),
        )
    else:
        result = score_historical_calibration(
            calibration_dir=Path(args.calibration_dir),
            primary_output_path=Path(args.primary_output),
            contract_path=Path(args.contract),
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
