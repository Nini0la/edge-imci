import hashlib
import json
from pathlib import Path

from edge_imci.evaluation.structured_extraction import (
    compare_decision_equivalence,
    parse_model_target_json,
    score_structured_extraction,
)
from edge_imci.model_io.encounter import validate_model_facing_encounter


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "experiments" / "qualification" / "asus-structured-extraction-smoke-v1"


def test_asus_smoke_gold_is_valid_exact_and_decision_equivalent() -> None:
    raw = (FIXTURE / "expected_target.json").read_text(encoding="utf-8")
    target = parse_model_target_json(raw)
    validate_model_facing_encounter(target)

    extraction = score_structured_extraction(target, target)
    decision = compare_decision_equivalence(target, target)

    assert extraction.schema_valid is True
    assert extraction.whole_record_exact_match is True
    assert extraction.unknown_preservation_accuracy == 1.0
    assert decision.decision_equivalent is True


def test_asus_smoke_manifest_pins_current_fixture_bytes() -> None:
    manifest = json.loads((FIXTURE / "fixture_manifest.json").read_text(encoding="utf-8"))
    assert manifest["fixture_id"] == "edge-imci-asus-structured-extraction-smoke-v1"
    assert manifest["source"]["partition"] == "TRAIN"
    assert manifest["formal_admission_evidence"] is False
    for relative_path, expected_sha256 in manifest["assets"].items():
        actual_sha256 = hashlib.sha256((FIXTURE / relative_path).read_bytes()).hexdigest()
        assert actual_sha256 == expected_sha256


def test_asus_smoke_matches_approved_canonical_training_example() -> None:
    manifest = json.loads((FIXTURE / "fixture_manifest.json").read_text(encoding="utf-8"))
    records_path = (
        ROOT
        / "data"
        / "training_sources"
        / "structured_extraction_campaign_v1"
        / "canonical_records.jsonl"
    )
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    source = next(
        record
        for record in records
        if record["example_id"] == manifest["source"]["language_example_id"]
    )

    assert source["partition"] == "TRAIN"
    assert source["input"]["content"] + "\n" == (FIXTURE / "user_prompt.txt").read_text(
        encoding="utf-8"
    )
    assert source["target"] == json.loads(
        (FIXTURE / "expected_target.json").read_text(encoding="utf-8")
    )
