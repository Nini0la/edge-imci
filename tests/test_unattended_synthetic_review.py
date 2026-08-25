from __future__ import annotations

import json
from pathlib import Path

from edge_imci.review.synthetic_batch import (
    REVIEW_CONTRACT_PATH,
    finalize_review_pipeline,
    ingest_primary_reviews,
    prepare_primary_review_batch,
)


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_RECORDS = (
    ROOT / "data/training_sources/structured_extraction_campaign_v1/canonical_records.jsonl"
)


def _first_record(path: Path = CAMPAIGN_RECORDS) -> dict:
    return next(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if '"source_case_id":"hpg-001-all-negative"' in line
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _contract(tmp_path: Path, *, audit_fraction: float = 0.0) -> Path:
    contract = json.loads(REVIEW_CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["routing"]["pass_audit_fraction"] = audit_fraction
    contract["routing"]["minimum_pass_audit_count_per_style"] = 0
    contract["acceptance"]["minimum_acceptance_rate_per_style"] = 0.0
    contract["acceptance"]["maximum_critical_error_rate_per_style"] = 1.0
    contract["authorization"]["automatic_dataset_promotion_authorized"] = True
    path = tmp_path / "review_contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    return path


def _review(subject: dict, *, verdict: str = "PASS") -> dict:
    if verdict == "PASS":
        assessments = [
            {
                "fact_id": item["fact_id"],
                "status": "MATCHED",
                "evidence_text": subject["candidate_text"],
                "issue_code": None,
            }
            for item in subject["known_facts"]
        ]
        error_codes: list[str] = []
        summary = "All source facts are faithfully represented."
    else:
        assessments = []
        for index, item in enumerate(subject["known_facts"]):
            assessments.append(
                {
                    "fact_id": item["fact_id"],
                    "status": "MISSING" if index == 0 else "MATCHED",
                    "evidence_text": None if index == 0 else subject["candidate_text"],
                    "issue_code": "FACT_MISSING" if index == 0 else None,
                }
            )
        error_codes = ["FACT_MISSING"]
        summary = "One required fact is missing."
    return {
        "review_schema_id": "edge-imci-synthetic-language-review-output-v1",
        "subject_id": subject["subject_id"],
        "verdict": verdict,
        "error_codes": error_codes,
        "fact_assessments": assessments,
        "unknown_violations": [],
        "unsupported_claims": [],
        "style_assessment": "PASS",
        "risk_level": "LOW",
        "summary": summary,
    }


def _batch_output(custom_id: str, review: dict) -> dict:
    return {
        "custom_id": custom_id,
        "response": {
            "status_code": 200,
            "request_id": "provider-request-test",
            "body": {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps(review)}
                        ],
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 20},
            },
        },
        "error": None,
    }


def _prepare_one(tmp_path: Path, *, audit_fraction: float = 0.0):
    records = tmp_path / "records.jsonl"
    _write_jsonl(records, [_first_record()])
    pipeline = tmp_path / "pipeline"
    contract = _contract(tmp_path, audit_fraction=audit_fraction)
    manifest = prepare_primary_review_batch(
        records_path=records,
        output_dir=pipeline,
        model="primary-test",
        contract_path=contract,
    )
    subject = json.loads((pipeline / "subjects.jsonl").read_text().splitlines()[0])
    custom_id = next(iter(json.loads((pipeline / "primary_index.json").read_text())))
    return pipeline, contract, manifest, subject, custom_id


def test_prepare_is_zero_call_and_covers_every_record(tmp_path: Path) -> None:
    records = tmp_path / "records.jsonl"
    rows = CAMPAIGN_RECORDS.read_text(encoding="utf-8").splitlines()[:3]
    records.write_text("\n".join(rows) + "\n", encoding="utf-8")
    pipeline = tmp_path / "pipeline"
    manifest = prepare_primary_review_batch(
        records_path=records,
        output_dir=pipeline,
        model="primary-test",
    )
    assert manifest["status"] == "PRIMARY_BATCH_PREPARED_ZERO_CALL"
    assert manifest["subject_count"] == 3
    assert manifest["authorization"]["remote_calls_authorized"] is False
    lines = [json.loads(line) for line in (pipeline / "primary_batch_input.jsonl").read_text().splitlines()]
    assert len(lines) == 3
    assert all(line["url"] == "/v1/responses" for line in lines)
    assert all(line["body"]["text"]["format"]["strict"] is True for line in lines)


def test_clean_primary_pass_exports_without_codex_or_adjudication(tmp_path: Path) -> None:
    pipeline, contract, _, subject, custom_id = _prepare_one(tmp_path)
    primary_output = tmp_path / "primary_output.jsonl"
    _write_jsonl(primary_output, [_batch_output(custom_id, _review(subject))])
    summary = ingest_primary_reviews(
        pipeline_dir=pipeline,
        primary_output_path=primary_output,
        contract_path=contract,
    )
    assert summary["adjudicator_subjects"] == 0
    report = finalize_review_pipeline(
        pipeline_dir=pipeline,
        adjudicator_output_path=None,
        contract_path=contract,
    )
    assert report["status"] == "APPROVED_RECORDS_EXPORTED"
    assert report["approved_record_count"] == 1
    assert report["authorization"]["training_authorized"] is False


def test_primary_failure_is_adjudicated_but_never_auto_promoted(tmp_path: Path) -> None:
    pipeline, contract, _, subject, custom_id = _prepare_one(tmp_path)
    primary_output = tmp_path / "primary_output.jsonl"
    _write_jsonl(primary_output, [_batch_output(custom_id, _review(subject, verdict="FAIL"))])
    summary = ingest_primary_reviews(
        pipeline_dir=pipeline,
        primary_output_path=primary_output,
        adjudicator_model="adjudicator-test",
        contract_path=contract,
    )
    assert summary["adjudicator_subjects"] == 1
    adjudicator_index = json.loads((pipeline / "adjudicator_index.json").read_text())
    adjudicator_custom_id = next(iter(adjudicator_index))
    adjudicator_output = tmp_path / "adjudicator_output.jsonl"
    _write_jsonl(
        adjudicator_output,
        [_batch_output(adjudicator_custom_id, _review(subject, verdict="PASS"))],
    )
    report = finalize_review_pipeline(
        pipeline_dir=pipeline,
        adjudicator_output_path=adjudicator_output,
        contract_path=contract,
    )
    assert report["approved_record_count"] == 0
    assert report["held_count"] == 1


def test_missing_primary_result_blocks_quality_gate_and_export(tmp_path: Path) -> None:
    pipeline, contract, _, _, _ = _prepare_one(tmp_path)
    empty_output = tmp_path / "empty.jsonl"
    empty_output.write_text("", encoding="utf-8")
    ingest_primary_reviews(
        pipeline_dir=pipeline,
        primary_output_path=empty_output,
        contract_path=contract,
    )
    report = finalize_review_pipeline(
        pipeline_dir=pipeline,
        adjudicator_output_path=None,
        contract_path=contract,
    )
    assert report["status"] == "BLOCKED_BY_QUALITY_GATES"
    assert report["approved_record_count"] == 0
    assert report["held_count"] == 1


def test_schema_invalid_review_is_held_instead_of_aborting_ingestion(tmp_path: Path) -> None:
    pipeline, contract, _, subject, custom_id = _prepare_one(tmp_path)
    invalid = _review(subject)
    invalid.pop("summary")
    output = tmp_path / "invalid.jsonl"
    _write_jsonl(output, [_batch_output(custom_id, invalid)])
    summary = ingest_primary_reviews(
        pipeline_dir=pipeline,
        primary_output_path=output,
        contract_path=contract,
    )
    assert summary["invalid_or_missing_primary_reviews"] == 1
    receipt = json.loads((pipeline / "primary_reviews.jsonl").read_text().splitlines()[0])
    assert receipt["status"] == "INVALID"
    assert receipt["error"] == "ValidationError"
