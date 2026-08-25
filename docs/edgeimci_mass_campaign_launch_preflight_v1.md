# EdgeIMCI mass synthetic-data campaign launch preflight v1

> **Authority:** `PROJECT_OWNER_DELEGATED_PREFLIGHT` · **Date:** 2026-08-24 · **Lifecycle:** `BLOCKED_NOT_AUTHORIZED` · No paid job, automatic dataset promotion, fine-tuning, or production clinical use is authorized.

## Launch decision

Do not submit generation or review jobs yet. The six-style 10,000-attempt campaign is deterministically allocated and its zero-call preparation path is tested, but both regular-English prompts need a new synchronous canary and the unattended reviewer needs model calibration against the prepared human-reviewed set.

## Regular-English canaries

Historical synchronous evidence does not qualify either regular-English style:

| Style | Evidence | Result | Disposition |
| --- | --- | --- | --- |
| Natural conversational English v2.1 | 4 targeted GPT-4.1 attempts, rechecked with current deterministic guards | 1 pass; evidence-span, fact-set, connector, ear-history, and fact-conflation failures | Blocked |
| Clinical/concise standard English v2 | 2 delegated human-reviewed samples | 1 semantic pass; 1 semantic failure caused by changing `OR` to `AND` | Blocked |

Candidate prompts v2.2 and v2.1 strengthen unknown omission, logical connectors, provenance/state separation, and exact evidence spans. A 14-request package covering seven representative cases per style is prepared at `experiments/generation/edge-imci-regular-english-canary-v1/`. It has not been submitted.

Canary release gates are at least 90% deterministic acceptance per style, zero semantic failures, and harness inspection of only three examples per style. The historical evidence and the small inspected sample are not a substitute for this new canary.

## Reviewer calibration

`experiments/review/synthetic-language-review-calibration-v1/` contains a zero-call primary Batch package for 64 existing delegated human-reviewed cases:

| Label/style | Count |
| --- | ---: |
| Human semantic PASS | 35 |
| Human semantic FAIL | 29 |
| Nigerian English | 14 |
| Nigerian Pidgin | 18 |
| Noisy typed English | 18 |
| Telegraphic PHC notes | 14 |

No reviewer inference has run, so measured agreement, false acceptance, and false rejection are pending. The calibration scorer is fail-closed and requires:

- completion rate at least 99.5%;
- agreement at least 90%;
- false acceptance at most 2%;
- false rejection at most 10%;
- high-risk false acceptance exactly 0%.

The reviewer prompt now treats candidate text as untrusted data, defines style and error-code anchors, pins risk to deterministic routing, and requires finding/code consistency. The output cap is 5,000 tokens to avoid truncating complete multi-pathway reviews.

## Proposed campaign

| Style | Attempts | Share | Estimated generation cost | Estimated review cost |
| --- | ---: | ---: | ---: | ---: |
| Natural conversational English | 2,000 | 20% | $11.00 | $8.95 |
| Standard clinical English | 2,000 | 20% | $11.00 | $8.95 |
| Nigerian English | 1,500 | 15% | $8.25 | $6.71 |
| Nigerian Pidgin | 1,500 | 15% | $8.25 | $6.71 |
| Noisy typed English | 1,500 | 15% | $8.25 | $6.71 |
| Telegraphic PHC notes | 1,500 | 15% | $8.25 | $6.71 |
| **Total** | **10,000** | **100%** | **$55.00** | **$44.75** |

Generation assumes 1,500 input and 1,000 output tokens per attempt at planning Batch rates of $1.00/M input and $4.00/M output. Review assumes 2,500 input and 1,800 output tokens, primary review of every deterministic candidate, and 30% adjudication planning coverage. Primary planning rates are $0.20/M input and $0.80/M output; adjudicator planning rates are $0.50/M input and $4.00/M output. These are conservative planning assumptions, not verified Azure billing rates. Reforecast from actual canary/calibration usage and a verified region/deployment rate card before authorization.

The planned review cost is $44.75, within the required $40-$75 envelope and below the hard $75 review gate. If observed failure/high-risk routing projects adjudication above that ceiling, adjudication preparation stops for explicit budget reconciliation rather than silently reducing required coverage.

## Review flow

1. Ingest every returned generation item and run existing deterministic schema, evidence, leakage, and semantic guards.
2. Send every parseable candidate to the primary asynchronous Batch reviewer.
3. Independently adjudicate every primary failure or uncertainty, every high-risk case, and a deterministic stratified 10% pass audit with at least 10 audited passes per observed style.
4. Exclude deterministic failures; hold semantic failures, uncertainty, invalid/missing results, and reviewer disagreements outside the approved output.
5. Produce generation yield and token reports plus final per-style deterministic pass, reviewer verdict, adjudication, acceptance, critical-error, token, and estimated-cost reports.
6. Keep `approved_records.jsonl` empty because automatic promotion remains unauthorized. Clean records are only provisional.

## Required Azure configuration

The following exact project-specific values are unresolved and must be pinned before any paid submission:

- Azure OpenAI resource or Foundry project HTTPS endpoint, normalized to the v1 Responses endpoint;
- authentication mode: Entra ID or an API-key environment-variable name, with no secret stored in artifacts;
- existing synchronous GPT-4.1 `2025-04-14` deployment for the 14-request regular-English canary;
- Global Batch GPT-4.1 `2025-04-14` deployment name for generation;
- Global Batch deployment name for the primary reviewer, intended model GPT-4.1 mini `2025-04-14` or an explicitly approved equivalent supporting strict Responses structured output;
- separate stronger Global Batch adjudicator deployment name supporting the same strict output contract;
- region-specific Batch token/file quota sufficient for 10,000 generation requests and the downstream review batches;
- verified Batch rate card, effective date, region, and currency.

Deployment names in request bodies must be Azure deployment names, not generic model names.

## Remaining blockers

- Explicit authorization and a small budget for the 14 synchronous regular-English canary.
- Passing canary metrics and limited owner/harness sample inspection.
- Exact primary reviewer deployment and paid execution authorization for the 64-case calibration Batch.
- Passing measured calibration gates; prompt/gate revision and rerun if any gate fails.
- Exact generation and adjudicator deployment names, endpoint/auth mode, quota confirmation, and verified rate card.
- Regenerated cost forecast from canary and calibration token usage.
- Explicit project-owner authorization for the paid 10,000-request generation job and downstream review jobs.

## Prepared commands

Rebuild the regular-English canary package without remote calls:

```bash
edgeimci-mass-campaign --regular-english-canary \
  --output-dir experiments/generation/edge-imci-regular-english-canary-v1
```

Rebuild the historical calibration package without remote calls:

```bash
edgeimci-review-calibration prepare \
  --output-dir experiments/review/synthetic-language-review-calibration-v1 \
  --maximum-cases 64 \
  --model <exact-primary-review-batch-deployment>
```

After separately authorized Batch inference, score immutable calibration output:

```bash
edgeimci-review-calibration score \
  --calibration-dir experiments/review/synthetic-language-review-calibration-v1 \
  --primary-output <downloaded-primary-output.jsonl>
```

The blocked local 10,000-request source package is staged at `experiments/generation/edge-imci-six-style-azure-batch-mass-v1/`. Rebuild it without remote calls with:

```bash
edgeimci-mass-campaign \
  --output-dir experiments/generation/edge-imci-six-style-azure-batch-mass-v1
```

Do not convert its unauthorized schedule template into a submission schedule or call `edgeimci-azure-batch prepare` until all launch gates and explicit paid-job authorization pass.
