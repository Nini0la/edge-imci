"""CLI for the zero-call unattended synthetic-data review pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from edge_imci.review.synthetic_batch import (
    REVIEW_CONTRACT_PATH,
    finalize_review_pipeline,
    ingest_primary_reviews,
    prepare_primary_review_batch,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare-primary")
    prepare.add_argument("records")
    prepare.add_argument("--output-dir", required=True)
    prepare.add_argument("--model")
    prepare.add_argument("--contract", default=str(REVIEW_CONTRACT_PATH))

    ingest = commands.add_parser("ingest-primary")
    ingest.add_argument("--pipeline-dir", required=True)
    ingest.add_argument("--primary-output", required=True)
    ingest.add_argument("--adjudicator-model")
    ingest.add_argument("--contract", default=str(REVIEW_CONTRACT_PATH))

    finalize = commands.add_parser("finalize")
    finalize.add_argument("--pipeline-dir", required=True)
    finalize.add_argument("--adjudicator-output")
    finalize.add_argument("--contract", default=str(REVIEW_CONTRACT_PATH))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare-primary":
        result = prepare_primary_review_batch(
            records_path=Path(args.records),
            output_dir=Path(args.output_dir),
            model=args.model,
            contract_path=Path(args.contract),
        )
    elif args.command == "ingest-primary":
        result = ingest_primary_reviews(
            pipeline_dir=Path(args.pipeline_dir),
            primary_output_path=Path(args.primary_output),
            adjudicator_model=args.adjudicator_model,
            contract_path=Path(args.contract),
        )
    else:
        result = finalize_review_pipeline(
            pipeline_dir=Path(args.pipeline_dir),
            adjudicator_output_path=(
                Path(args.adjudicator_output) if args.adjudicator_output else None
            ),
            contract_path=Path(args.contract),
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
