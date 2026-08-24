# EdgeIMCI Synthetic Data Generation Experiment Plan

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `CURRENT` · Maintained Markdown working version; the corresponding DOCX is its source snapshot.

*Whole-encounter rendering, controlled bake-offs and a two-speed route to scale*

**Status:** Working plan; time and cost figures are planning estimates until measured.

> **Core design:** One complete canonical child encounter is the semantic unit. The teacher renders only coherent, realistic PHC-worker input. The primary student target is exported deterministically from the same frozen encounter into the versioned model-facing JSON contract.

## 1. Generation unit and responsibility boundary

A whole-encounter teacher request contains only the source findings the teacher is allowed to express—for example age, danger-sign observations, respiratory, diarrhoea, fever/measles and ear findings. Expected classifications, actions, completeness state and assistant wording remain hidden. The encounter is not split into independently generated IMCI pathway fragments.

| Component | Responsibility |
| --- | --- |
| Frozen semantic source | Defines the canonical encounter observations, explicit negatives and UNKNOWN state. |
| Teacher model | Converts the approved semantics into realistic PHC-worker language within the boundary fixed by the selected rendering strategy. |
| Validator | Checks semantic fidelity, required content and detectable rendering failures; returns pass/fail plus error codes. |
| Deterministic target exporter | Projects the frozen source into model-facing encounter JSON; it does not copy oracle outputs or provenance. |
| Deterministic clinical pipeline | Consumes validated encounter state and owns completeness, classifications, urgency, referral and actions. |
| Student evaluation | Measures structured extraction and downstream decision equivalence; validator acceptance remains an intermediate data-quality proxy. |

*The controlled teacher lane remains narrow: it returns only a PHC-worker submission plus fact-evidence annotations. Existing variant records may continue to preserve the frozen assistant response and alignment for language/reference audit, but canonical extraction SFT records attach the deterministic model-facing JSON projection as the primary target. The teacher never generates that target. In every design, the complete encounter remains the semantic unit.*

## 2. Experiment definition and campaign

Experiment/run = one fixed generation configuration. Request = one semantic encounter processed within that run. Change one principal factor at a time where possible.

| Stage | What varies | Decision/output |
| --- | --- | --- |
| 1. Teacher / prompt bake-off | 2-3 teachers x 1-2 prompt/rendering strategies on the same 50-100-case slice | Choose a stable, high-fidelity rendering recipe |
| 2. Variant-count experiment | 1 vs 2 vs 4 renderings per semantic encounter | Measure diversity gain against cost and duplication |
| 3. Fast controlled corpus | Generate about 500-1,000 accepted PHC submissions and pair each with its deterministic JSON target | Start extraction SFT-v1 quickly |
| 4. Dataset-scale generation | Approximately 1k to 3k to 10k, possibly 20k/30k | Support learning-curve and larger-data experiments |
| 5. Quality/diversity refinement | Prompt or renderer changes only if early data show mode collapse, awkward language or systematic rejections | Correct observed failure modes |

**A reasonably complete campaign may contain roughly 10-14 generation runs; the critical path is smaller:** 4-6 bake-off runs, one fast corpus run, inspection, then scale only when justified.

## 3. Prompt and generation provenance

Store prompts once in version control and reference them from generated records by ID, version and immutable hash. Do not duplicate full prompt text into every item.

| Group | Required provenance |
| --- | --- |
| Run/config | `generation_run_id`; `teacher_provider`; `teacher_model`; `teacher_snapshot`; `prompt_id`; `prompt_version`; `prompt_hash`; `sampling_config`; `variants_per_case`; `validator_version` |
| Item identity | `semantic_case_id`; `variant_id`; `attempt_id`; parent generation run |
| Validation | `validation_pass`; `validation_error_codes`; rejected reason; reviewer override if any |
| Usage | `input_tokens`; `output_tokens`; cached tokens if applicable; latency; retry count; provider request ID; raw cost/usage response |
| Data/code | semantic-set version/hash; renderer code git commit; output artifact/hash; timestamps and status |

Before language variants are generated at scale, assign the parent semantic encounter with `edge-imci-parent-semantic-split-v1`. Every attempt and accepted paraphrase inherits that `TRAIN`, `VALIDATION` or `TEST` partition. Never split rows or variants independently. Cases 77 and 78 remain out-of-scope TEST parents; the small out-of-scope training slice must use separate reviewed parent encounters.

## 4. Acceptance, quality and cost metrics

- Acceptance rate and semantic error rate by teacher, prompt and variant policy.
- Error-code distribution, retry rate, duplicate/near-duplicate rate and language-diversity indicators.
- Mean and p95 latency, accepted examples per hour, tokens per accepted example and attempts per accepted example.
- Cost per attempt and cost per accepted example, derived from raw usage and a versioned rate card.
- Student structured-extraction and downstream decision-equivalence performance by generation recipe—the final arbiter when validator metrics and training utility disagree.

## 5. Two-speed execution strategy

```text
CLINICAL APPROVAL + HOLISTIC GOLDEN SEMANTIC SET
                    |
50-100 CASE TEACHER / PROMPT BAKE-OFF
                    |
STABLE RECIPE + HIGH ACCEPTANCE + NO SYSTEMATIC CORRUPTION
          /-----------------------------------\
FAST STANDARD API: ~500-1,000          LARGE AZURE BATCH
          |                              10k / 20k / 30k
ASUS CANDIDATE MODEL-RUNTIME ADMISSION      |
          |                                 |
ADMITTED PARENT                             |
          |                                 |
QWEN3-1.7B EXTRACTION SFT-v1 ON MODAL      |
          |                               ARRIVES LATER
EXTRACTION + DECISION-EQUIVALENCE EVAL <--- NEXT TRAINING EXPERIMENTS
```

### Phase A - fast lane

Use the standard API for approximately 500-1,000 validated examples so SFT can start as soon as the dataset is authorized and a candidate parent has passed ASUS model-runtime admission, without waiting for asynchronous scale.

### Phase B - scale lane

Once the recipe is demonstrably stable, submit a much larger Azure Batch job. Modal fine-tuning, evaluation and error analysis continue while the batch is processing, so its elapsed time is hidden behind useful work.

*When the large corpus arrives, preserve two routes where affordable: continue SFT-v1 for the pragmatic strongest model, and train a matched checkpoint from the same base for the scientific dataset-scale comparison.*

## 6. Planning time ranges

> **Estimate notice:** These are working ranges, not provider SLAs. Concurrency, quota, output length, validator speed and acceptance/retry rate can materially change them. Reforecast after the first approximately 100 requests.

| Accepted target / bake-off | API generation estimate | Planning window including validation + retries |
| --- | ---: | ---: |
| 100-case experiment | ~5-15 min | ~15-30 min |
| 500 | ~15-40 min | ~30-60 min |
| 1,000 | ~30-60 min | ~1-2 h |
| 3,000 | ~1-3 h | ~2-4 h |
| 10,000 | ~4-8 h | ~5-10 h |
| 30,000 | ~12-24 h | ~15-30 h |

*Forecast replacement metrics:* `accepted_examples_per_hour`; `mean_request_latency`; `p95_request_latency`; `retry_rate`; `tokens_per_accepted_example`; `cost_per_accepted_example`.

## 7. Cost and accounting model

Do not hard-code provider prices into the experiment record. Retain actual input/output token counts, request mode, deployment/region and provider usage response; calculate dollars through a versioned rate card.

| Measure | Accounting concept |
| --- | --- |
| Attempt cost | (input tokens x input rate) + (output tokens x output rate) + any applicable service components |
| Accepted-example cost | Total generation + validation/retry cost / accepted examples |
| Batch planning placeholder | Standard-mode estimate x documented batch discount assumption; label assumption, rate-card date and region |
| Reconciliation | Replace estimate with actual provider usage/invoice data while preserving both estimate and actual |

*Optional planning assumption from the current discussion: begin forecasting with approximately 1,500 input and 700 output tokens per whole encounter, then replace these values with observed means after 50-100 requests. This is a placeholder, not a specification.*

## 8. Gates and next actions

- Use the frozen holistic semantic and language layers as the source for the first bake-off; pin the controlled-variant contract, prompts, schemas and validator.
- Keep teacher selection, immutable model snapshots, remote-call authorization, sampling settings and a budget/credit ceiling as explicit run gates.
- Run teacher/prompt comparisons on identical cases; review both validator outcomes and language quality.
- Select a recipe only after stable acceptance, no systematic semantic corruption and sensible cost/throughput.
- Pair accepted language with deterministic model-facing targets and approve the dataset/split.
- Before fine-tuning, run the frozen target-device admission study and select only from candidate model-runtime combinations that pass on the ASUS.
- Start extraction SFT-v1 on Modal only with the admitted parent identity recorded in the training provenance.
- Keep non-null Plan B/C longitudinal reassessment records corpus-ineligible until an approved evaluator exists; do not let this defer ordinary initial-encounter generation.
- Submit the large Azure Batch lane in parallel; do not block fine-tuning or evaluation on its completion. The independent ASUS admission gate still applies.
- Reforecast time and cost after approximately 100 requests and retain the measured forecast in the run registry.
