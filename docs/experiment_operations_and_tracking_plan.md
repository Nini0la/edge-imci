# EdgeIMCI Experiment Operations & Tracking Plan

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `CURRENT` · Maintained Markdown working version; the corresponding DOCX is its source snapshot.

*A lightweight operating system for reproducible, environment-aware experimental evidence*

**Status:** Working plan based on current campaign decisions; scope excludes the domain-expert clinical questionnaire.

> **Operating principle:** Running an experiment should automatically create its evidence. Capture raw usage and provenance at source; derive cost and comparative summaries later.

## 1. Scope and experiment taxonomy

The registry treats training, evaluation, generation and deployment work as experiments when each has a fixed configuration, inputs, outputs, metrics and reproducibility requirements.

- `TRAINING` - supervised fine-tuning and capacity/model-size comparisons.
- `CLINICAL_EVAL` - holistic classification, integrated management, completeness/withholding and urgent-incomplete evaluation.
- `SYNTHETIC_GENERATION` - teacher, prompt, variant and corpus-scale experiments.
- `MODEL_RUNTIME_QUALIFICATION` - fail-closed admission of an exact base model-runtime tuple on the intended deployment device, followed by paired post-training requalification.
- `EDGE_PROFILE` - latency, throughput, memory and deployability on target or proxy hardware.
- `COMPRESSION` - SVD or other checkpoint reduction methods, when justified.
- `ALIGNMENT` - preference or reinforcement-learning experiments, only if SFT error analysis supports them.
- `EXTERNAL_EVAL` - optional research evidence outside the hackathon critical path.

## 2. Execution environments

| Environment | Primary job | Model/provider | Telemetry that matters | Cost basis |
| --- | --- | --- | --- | --- |
| Local deterministic/dev | Rules, schemas, oracle/corpus work, smoke tests, small evals | No runtime model or local checkpoint | Versions, counts, validity, wall time, status | Effectively $0 incremental; record time only when useful |
| ASUS / intended target | Pre-training candidate admission and post-training deployment requalification | Exact checksum-pinned model-runtime tuple | Task quality, structured-output/retries/time-to-valid, neutral speed, cold start, process/system memory, swap, CPU and thermal behavior | Compute cost secondary; preserve qualification evidence |
| Modal | Primary GPU lab for SFT, checkpoint evals and selected self-hosted experiments | Qwen checkpoint; GPU/provider recorded | GPU type/time, wall time, config, checkpoint, metrics, artifacts | Billable runtime x versioned machine rate |
| External API | Teacher bake-offs and synthetic language generation | Teacher provider, model and snapshot | Tokens, requests, retries, latency, accept/reject and error codes | Raw usage x versioned API rate card |
| Hybrid Modal + API | Pipelines combining hosted generation with GPU validation/training | Teacher API + student/evaluator checkpoint | Both API and infrastructure telemetry, linked by run IDs | API usage + Modal runtime; report separately and combined |
| Official ADTC | Final controlled profiling/audit and submission evidence | Submitted artifact | Official profiler outputs plus artifact identity | Externally controlled / N/A unless charges arise |

## 3. Operational matrix

This is the scan-first campaign view. Speed and cost are recorded as observed values after execution; no single telemetry schema is forced onto every environment.

| Experiment | Where | Model/provider | Scientific result | Auto-captured execution data | Cost character |
| --- | --- | --- | --- | --- | --- |
| Deterministic corpus / oracle | Local | None | Artifact validity; coverage | Versions, counts, runtime | $0 incremental |
| Golden rendering bake-off | External API | 2-3 teacher candidates | Semantic acceptance; language quality | Prompt/model/usage/retries/latency | API usage |
| Bulk synthetic generation | API / Azure Batch | Chosen teacher | Acceptance; diversity; downstream utility | Tokens, attempts, errors, throughput | $/attempt and $/accepted example |
| Self-hosted generation alternative | Modal + vLLM | Open teacher | Acceptance; diversity | GPU/runtime/throughput | GPU-hours and $/accepted example |
| Candidate admission | ASUS | Untuned source/deployment artifact plus exact runtime | Pass/fail against frozen task and deployability thresholds | Repository/model/runtime/checksum identity, raw attempts, speed and sustained system telemetry | Mandatory before candidate-specific fine-tuning |
| Primary SFT | Modal | Qwen3-1.7B | Student clinical performance | GPU, config, data, checkpoint, runtime | $/run; $/1k examples |
| Clinical eval | Local / Modal | Base or trained checkpoint | Clinical metric suite | Checkpoint/eval versions; runtime | $0 local or Modal runtime |
| 4B / capacity branch | Modal | Qwen3-4B | Gain versus 1.7B | Same training/eval provenance | Higher GPU runtime; conditional |
| Qwen3.5 branch | Tinker | Supported Qwen3.5 model | Capacity/post-training result | Provider config, usage, checkpoint | Credits/usage; specialist branch |
| Preference / RL | Modal / specialist | Chosen checkpoint | Targeted error reduction | Reward/config/rollout/compute | Higher; only if justified |
| SVD / compression | Modal / local | Trained checkpoint | Quality-size-speed trade-off | Method/config/artifact/profile | Variable; optional |
| Post-training requalification | ASUS | Exact converted or quantized deployment artifact | Same frozen task and deployability gates; paired delta from admitted base | Full model/runtime/harness/device identity and raw before/after evidence | Mandatory before deployment selection |
| Quantization | Build environment + ASUS | Q8/Q6/Q4 only if triggered | Quality-runtime trade-off | Representation + matched profiles | Conditional optimization |
| Final profile | Official ADTC | Submitted GGUF | Official challenge evidence | Official output + artifact hash | N/A / externally controlled |
| Lundin external eval | Local / Modal | Selected checkpoint | Optional generalization evidence | Benchmark revision/scoring/runtime | Off critical path |

## 4. Scientific versus operational metrics

Scientific metrics answer whether a change improved the model or dataset. Operational metrics answer what it took to produce that evidence. Both belong to a run, but they should remain distinguishable.

| Class | Scientific metrics | Operational/accounting metrics |
| --- | --- | --- |
| Synthetic generation | Acceptance, semantic error codes, diversity, downstream student performance | Attempts, tokens, latency, retries, throughput, raw API usage |
| Training | Loss/learning curves and post-training clinical performance | GPU type/time, wall time, examples, checkpoint size, provider usage |
| Clinical evaluation | Classification, management, completeness/withholding, urgent-incomplete metrics | Checkpoint/eval identity, denominator, runtime, hardware |
| Target-device qualification | Quality, instruction following, first-attempt and eventual structured validity, retries, decision equivalence | Time to valid result, prompt/generation tok/s, cold start, process and whole-system memory, swap, CPU, temperature, throttling, model/runtime/harness identity |

## 5. Automatic provenance and run artifacts

> **Minimum rule:** Every runner writes a sidecar record at start and finalizes it on success or failure. Provider adapters add environment-specific telemetry; fields that do not apply remain absent.

| Group | Fields |
| --- | --- |
| Identity | `run_id`, `experiment_id`, `experiment_type`, `parent_run_id`, `status` |
| Model | `model_provider`, `model_id`, `revision/snapshot`, `checkpoint_id`, `checkpoint_hash` |
| Execution | `execution_provider`, `environment`, `hardware`, `started_at`, `finished_at`, `wall_time` |
| Inputs | `dataset_id/version/hash`, split, `prompt_id/version/hash`, `config_id/hash` |
| Code | `git_commit`, `dirty_worktree` flag, runner version, dependency/container identity |
| Usage | examples, requests, tokens, GPU-seconds, retries, raw provider usage |
| Outputs | metrics, error codes, artifact paths/hashes, logs and exception state |
| Accounting | `rate_card_id/date`, derived `actual_cost_usd`, estimation flag |

```text
EXPERIMENT CONFIG
        |
ONE RUNNER ENTRY POINT
        |
WORK + PROVIDER-SPECIFIC TELEMETRY
        |
RUN.JSON + CONFIG + METRICS + ARTIFACT HASHES
        |
REGISTRY / COMPARATIVE REPORTS
```

## 6. Environment-aware cost accounting

- Raw usage is evidence; dollar cost is derived. Preserve token counts, request counts, GPU-seconds and machine type even when a provider does not expose cost directly.
- Use a versioned rate card with currency, effective date, region/deployment and pricing mode. Recalculation must not overwrite the historical rate-card reference.
- For API generation report cost per attempt and cost per accepted example. For Modal report cost per run and, where helpful, per 1,000 training examples. For local and edge work prioritize runtime/performance evidence over nominal electricity cost.
- For hybrid runs retain component costs separately and provide a combined total. Mark forecasts as estimates until reconciled with provider usage or invoices.

## 7. Branch rules

### Quantization

Qualify the base candidate in the intended runtime representation before fine-tuning. After fine-tuning, convert or quantize as required and rerun the same ASUS qualification. When multiple Q8/Q6/Q4 artifacts are compared, treat each as a distinct checksum-pinned model-runtime tuple and measure the matched quality, reliability, size, speed, memory and thermal trade-off. Do not deploy a quantized artifact on the strength of training-time or non-target-device evidence.

### Candidate admission

No candidate-specific fine-tuning starts until the exact parent model-runtime combination has passed the frozen ASUS admission policy. Missing checksums, runtime identity, thresholds or required measurements make the result incomplete. Ranking can select among passing combinations but cannot override a failed hard gate. See [the target-device qualification plan](target_device_model_runtime_qualification_plan.md).

### Lundin

Remove it from required hackathon evidence. Treat it as optional external research evaluation if time permits; do not let it block holistic clinical evaluation, edge profiling or submission.

## 8. Immediate implementation checklist

- Define a small run schema with common identity/provenance fields and typed environment-specific extensions.
- Wrap generation, training, evaluation and profiling entry points so run records are automatic.
- Freeze and validate a target-device qualification lock containing the repository commit, candidate source revisions, reviewed SHA-256 manifests, runtime/configuration identities, workloads, measurement design and admission thresholds.
- Run the admission study on the ASUS before fine-tuning and retain raw task, neutral-benchmark and sustained-profile evidence for every candidate tuple.
- Version prompts, configs, datasets, checkpoints, eval suites and rate cards; store immutable hashes.
- Create a registry view that joins scientific metrics, execution telemetry and derived cost without manual re-entry.
- Run one end-to-end dry run in each active environment before the campaign expands.
