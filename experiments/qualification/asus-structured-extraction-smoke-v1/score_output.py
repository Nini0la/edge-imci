"""Score one raw ASUS smoke-test response against the frozen expected target."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from edge_imci.evaluation.structured_extraction import (
    compare_decision_equivalence,
    parse_model_target_json,
    score_structured_extraction,
)


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, help="File containing the raw model response")
    args = parser.parse_args()

    raw = args.output.read_text(encoding="utf-8")
    report: dict[str, object] = {
        "fixture_id": "edge-imci-asus-structured-extraction-smoke-v1",
        "raw_output_path": str(args.output),
        "raw_output_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }
    try:
        predicted = parse_model_target_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        report.update({"parse_valid": False, "parse_error": str(exc)})
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2

    gold = json.loads((ROOT / "expected_target.json").read_text(encoding="utf-8"))
    extraction = score_structured_extraction(gold, predicted)
    decision = compare_decision_equivalence(gold, predicted)
    report.update(
        {
            "parse_valid": True,
            "structured_extraction": extraction.to_dict(),
            "decision_equivalence": decision.to_dict(),
        }
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if extraction.whole_record_exact_match and decision.decision_equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())
