# EdgeIMCI unattended synthetic-data review v1

> **Authority:** `WORKING_IMPLEMENTATION` · **Lifecycle:** `PREPARED_ZERO_CALL` · Remote execution, automatic corpus promotion, training, and production clinical use remain unauthorized.

This pipeline removes Codex from routine synthetic-data inspection. It prepares provider Batch files, ingests immutable Batch outputs, routes a stronger adjudicator, applies conservative quality gates, and exports approved model-neutral records. The preparation and reconciliation commands make no provider calls.

The companion `edgeimci-azure-batch` command prepares and ingests the large Azure OpenAI generation batch. Its normalized `terminal_attempts.jsonl` feeds directly into `edgeimci-review prepare-primary`.

## Decision flow

```text
canonical generated candidates
        -> primary model review of every candidate
        -> stronger adjudication of high-risk, failed/uncertain, and audited passes
        -> disagreements and invalid results held
        -> quality gates by style
        -> approved_records.jsonl only when every gate passes
```

Deterministic failures are never automatically rescued. A primary failure remains held even if the adjudicator passes it. Missing provider results, malformed reviews, incomplete fact assessments, and inconsistent PASS decisions fail closed.

## Zero-call workflow

For a prepared, authorized generation schedule and its source-request manifest:

```bash
edgeimci-azure-batch prepare \
  --source-requests <source-requests.jsonl> \
  --schedule <schedule.json> \
  --output-dir experiments/generation/<batch-run-id> \
  --deployment <azure-global-batch-deployment>
```

After Azure returns the output and error JSONL files:

```bash
edgeimci-azure-batch ingest \
  --pipeline-dir experiments/generation/<batch-run-id> \
  --batch-output <output.jsonl> <error.jsonl> \
  --requested-at <recorded-submission-time> \
  --completed-at <recorded-completion-time>
```

Prepare the primary Azure/OpenAI Responses Batch JSONL:

```bash
edgeimci-review prepare-primary \
  experiments/generation/<batch-run-id>/terminal_attempts.jsonl \
  --output-dir experiments/review/<run-id> \
  --model <primary-batch-deployment>
```

Upload `primary_batch_input.jsonl` to an independently authorized Batch deployment. The file uses the documented `custom_id`, `POST`, `/v1/responses`, request-body format and strict Structured Outputs.

After retrieving the immutable provider output file:

```bash
edgeimci-review ingest-primary \
  --pipeline-dir experiments/review/<run-id> \
  --primary-output <downloaded-primary-output.jsonl> \
  --adjudicator-model <stronger-batch-deployment>
```

Submit the generated `adjudicator_batch_input.jsonl`, retrieve its output, then finalize:

```bash
edgeimci-review finalize \
  --pipeline-dir experiments/review/<run-id> \
  --adjudicator-output <downloaded-adjudicator-output.jsonl>
```

If no subjects were routed, omit `--adjudicator-output`.

## Outputs

- `subjects.jsonl`: immutable review inputs and canonical records.
- `primary_batch_input.jsonl`: all-candidate reviewer batch.
- `primary_reviews.jsonl`: normalized primary evidence.
- `adjudicator_batch_input.jsonl`: independently routed stronger review.
- `review_decisions.jsonl`: ACCEPT, HOLD, or EXCLUDE with reasons.
- `provisional_accepted_records.jsonl`: record-level passes before global gates.
- `approved_records.jsonl`: populated only when every global/style gate passes.
- `final_report.json`: counts, gates, token usage, and blocked/approved lifecycle.

The default configuration is deliberately non-executing at `configs/review/synthetic_language_review_v1.json`. Even clean review results remain provisional until a separate project-owner authorization enables automatic dataset promotion and pins actual deployment names, budgets, provider rate cards, and remote execution scope.

## Calibration

Prepare the frozen delegated-human calibration set without provider calls:

```bash
edgeimci-review-calibration prepare \
  --output-dir experiments/review/synthetic-language-review-calibration-v1 \
  --maximum-cases 64 \
  --model <exact-primary-batch-deployment>
```

After separately authorized asynchronous inference, score agreement and error rates:

```bash
edgeimci-review-calibration score \
  --calibration-dir experiments/review/synthetic-language-review-calibration-v1 \
  --primary-output <downloaded-primary-output.jsonl>
```

Calibration must pass before mass review. Primary-pass auditing is stratified by style at 10% with a configured minimum. `final_report.json` includes per-style quality, acceptance, usage, and estimated cost. Planning rates are execution gates, not billing evidence; reconcile them against immutable provider usage and a verified Azure rate card.
