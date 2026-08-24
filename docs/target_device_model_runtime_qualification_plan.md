# EdgeIMCI target-device model-runtime admission and qualification plan

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `CURRENT` · This gate precedes candidate-specific fine-tuning and is repeated after deployment conversion or quantization.

## Decision being made

EdgeIMCI does not admit a model name to fine-tuning. It admits an exact candidate model-runtime combination that has demonstrated adequate baseline task capability and acceptable operation on the intended ASUS Ubuntu deployment computer.

The qualification unit is the complete tuple:

```text
model repository + immutable revision + downloaded file hashes
+ tokenizer and chat-template identity
+ conversion/quantization identity, when applicable
+ runtime source/build/package identity
+ inference configuration
+ frozen evaluation repository commit
+ workload, prompts and scoring identities
+ ASUS hardware, firmware, OS, power and thermal state
```

A result for one tuple must not be generalized to another. Changing the weights, tokenizer, template, runtime build, quantization, context size, thread count, acceleration backend or material inference settings creates a new qualification unit.

## Two mandatory gates

### Gate A — pre-fine-tuning admission

Every candidate must run on the ASUS before training money or time is committed. The gate answers both questions:

1. Does the untuned candidate have enough baseline structured-extraction and instruction-following capability to be a credible fine-tuning parent?
2. Can its intended runtime representation execute acceptably on the deployment computer under representative and sustained load?

Only a candidate-runtime combination that passes the predeclared hard gates is eligible for fine-tuning. A candidate that cannot be made to run in the intended deployment runtime is not admitted merely because it can run in a different laboratory runtime.

### Gate B — post-fine-tuning requalification

The selected fine-tuned checkpoint must be converted or quantized as required for deployment, checksum-pinned, and rerun on the same ASUS with the same frozen evaluation repository, workloads, prompts, scoring policies and measurement methods. The report must pair the admitted base tuple with the post-training deployment tuple and identify every intentional delta.

Post-training results do not replace the baseline evidence. Both are retained to support a defensible before-and-after comparison and to expose quality loss introduced by conversion or quantization.

## Freeze package

Before the first measured run, create and review a version-controlled qualification package. It must contain:

- a full evaluation-repository commit SHA and repository URL;
- a candidate matrix with one immutable Hugging Face commit SHA per source repository;
- a pre-approved SHA-256 manifest for every downloaded or imported model, tokenizer and deployment-artifact file used by the runtime;
- the exact runtime identity, including source commit or immutable package/container identity and the executable or image digest;
- the complete inference configuration: template, system instruction, context size, batch size, thread counts, acceleration/offload settings, seed, sampling settings, stop strings and output-token cap;
- hashes for the workload, prompt sources, target schema, deterministic evaluator and scoring code;
- the retry policy and definition of a valid result;
- neutral benchmark prompt and generation token counts, warm-up policy, repetitions and aggregation policy;
- sustained-load duration, telemetry sample interval, cooling/reset rules and run order;
- hard admission thresholds and separately labelled ranking metrics; and
- the evidence-output location and retention policy.

An `UNRESOLVED` model, runtime, checksum, dataset, scorer or threshold keeps the experiment in `PLANNED`; it cannot silently default at execution time. Acceptance limits must be frozen before candidate outputs are inspected.

## ASUS preparation and immutable checkout

Use a dedicated Ubuntu user or run directory with sufficient disk space. Record the ASUS serial/model, CPU, GPU/NPU if used, RAM, storage, BIOS/firmware, Ubuntu kernel, drivers, power mode, governor and relevant environment variables. Disable unrelated scheduled work where practical and record anything that remains active.

Clone the harness rather than copying loose scripts:

```bash
git clone --no-checkout <evaluation-repository-url> edge-imci-evaluation
cd edge-imci-evaluation
git fetch --depth 1 origin <full-commit-sha>
git checkout --detach <full-commit-sha>
test "$(git rev-parse HEAD)" = "<full-commit-sha>"
test -z "$(git status --porcelain)"
uv sync --frozen
```

The checkout should remain read-only during qualification. Write evidence outside it so raw outputs do not make the harness dirty. Capture `git status`, the dependency lock hash, installed package inventory and runtime version output in each run bundle.

## Model acquisition and integrity

For a Hugging Face candidate, use `hf`, not an unpinned library download:

```bash
hf download <namespace/model> \
  --revision <full-hugging-face-commit-sha> \
  --local-dir <candidate-directory>

hf cache verify <namespace/model> \
  --revision <full-hugging-face-commit-sha> \
  --local-dir <candidate-directory> \
  --fail-on-missing-files \
  --fail-on-extra-files

(cd <candidate-directory> && sha256sum --check <reviewed-SHA256SUMS-file>)
```

The Hugging Face revision and SHA-256 file manifest serve different purposes and both are required. The revision identifies the upstream snapshot; the reviewed checksum manifest proves which bytes reached the ASUS. Do not generate the expected checksum manifest after the measured run and call that verification.

For an imported, converted or quantized artifact, record the parent checkpoint identity, conversion tool revision, command/configuration, output file list and SHA-256 values. Verify imported bytes against a reviewed manifest before inference. Keep model storage outside Git; retain the small checksum and provenance manifests in the evidence bundle.

## Matched qualification workload

Run all candidates through the repository's same representative structured-extraction workload. The task run must preserve, per case and per attempt:

- case and prompt identities;
- exact rendered prompt/messages sent to the runtime;
- raw model text, parsed object and validation errors;
- task-quality and instruction-following results;
- schema validity, whole-record exact match and field accuracy;
- positive precision/recall, negative accuracy, UNKNOWN preservation, measurement, duration and qualifier accuracy;
- downstream completeness, classification, urgency, urgent-action, referral and management equivalence;
- retry reason and attempt number;
- first-attempt validity, eventual validity within the fixed retry cap, and retries consumed; and
- wall time to first response, each attempt and the first valid result.

`time_to_valid_result` is a user-facing end-to-end measure: it includes failed attempts and retry overhead. Report it alongside first-attempt validity so retries cannot conceal brittle structured output. A generation that parses but fails the model-facing schema is not valid.

The qualification set must be representative and evaluation-eligible. Training examples may be used for a smoke test but cannot stand in for held-out admission evidence. All candidates receive identical ordering or a predeclared counterbalanced ordering; no candidate-specific prompt repairs are allowed inside a matched comparison.

## Neutral inference benchmark

Keep neutral speed measurement separate from task quality. Use fixed prompt-token and requested generation-token workloads, fixed context and batch settings, and report at least:

- prompt-processing tokens/second;
- generation tokens/second;
- time to first token;
- total request latency; and
- actual prompt/generated token counts and early-stop state.

Record warm-ups and individual repetitions, then report median and a declared tail percentile. Do not compare runs with different token counts, early stopping, templates or runtime settings as though they were matched.

## Cold start and sustained system profile

Measure a true cold start separately from warm inference. State exactly what was cold: process, runtime/model cache and, if deliberately controlled, filesystem page cache. Do not clear system caches without explicit authorization and a documented method.

During sustained representative load, sample and retain:

- model/runtime process RSS and peak RSS;
- whole-system used and available memory;
- swap used, swap-in and swap-out activity;
- per-process and whole-system CPU utilization;
- accelerator utilization and memory, when applicable;
- temperatures for all available relevant sensors;
- CPU frequency and explicit thermal-throttling indicators;
- power mode/governor and, where available, power draw; and
- OOM, runtime, kernel and throttling events.

Use the official ADTC profiler when its pinned revision and report schema are available and suitable. Preserve the official report bytes untouched and register their SHA-256 value. Supplemental Linux telemetry may fill gaps, but must be stored as a separate, clearly identified artifact rather than inserted into an official ADTC report.

Run enough sustained load to reach thermal steady state or the predeclared duration. Use the same cooling/reset condition and power state for each candidate. Randomize or counterbalance candidate order where possible so ambient temperature and cache state do not systematically favor one combination.

## Evidence bundle

Each measured qualification unit produces an immutable run bundle containing:

```text
qualification/<qualification-id>/<combination-id>/<run-id>/
  qualification-lock.json
  environment.json
  repository-provenance.json
  model-source-manifest.json
  SHA256SUMS
  runtime-identity.json
  inference-config.json
  task/
    attempts.jsonl
    raw-outputs.jsonl
    metrics.json
  neutral-benchmark/
    repetitions.jsonl
    summary.json
  profile/
    telemetry.jsonl
    summary.json
    official-adtc-report.json       # only when produced by ADTC
  decision.json
  edgeimci_run.json
```

The common run sidecar must link and hash the consumed model, frozen inputs and produced evidence. Evidence is append-only after finalization. Any corrected rerun receives a new run ID and records why the earlier run is excluded; raw failed evidence is not overwritten.

## Admission decision

The versioned decision record must evaluate every predeclared hard gate. At minimum, it should cover:

- baseline task-quality floor;
- instruction following and first-attempt structured-output floor;
- valid-within-retry-cap floor and retry ceiling;
- time-to-valid-result ceiling;
- prompt/generation performance floor or latency ceiling;
- successful cold start;
- peak process and whole-system memory headroom;
- no OOM and acceptable swap behavior;
- acceptable sustained temperature and thermal-throttling behavior; and
- completion of the sustained-load run without runtime failure.

Threshold values are project decisions and remain unresolved until frozen in the qualification package. The harness must not invent them. Missing required evidence is `NOT_QUALIFIED`, not a pass. The decision states one of:

- `ADMITTED_FOR_FINE_TUNING` — all hard gates pass;
- `NOT_ADMITTED` — one or more hard gates fail; or
- `INCOMPLETE` — required evidence or a frozen threshold is absent.

Ranking metrics may choose among combinations that pass, but may not compensate for a failed safety, integrity or deployability gate. The admitted combination becomes the parent identity for the training run.

## Paired post-training report

The final comparison pairs Gate A and Gate B using the same frozen harness commit and reports:

- base source and deployable artifact hashes;
- fine-tuned checkpoint and final deployable artifact hashes;
- conversion/quantization provenance;
- identical-case quality deltas, including regressions;
- structured-output, retries and time-to-valid deltas;
- neutral speed, cold-start, memory, swap, CPU and thermal deltas; and
- pass/fail results against the deployment qualification thresholds.

If a necessary toolchain update prevents use of the original runtime, preserve the original Gate A result and run an additional base-artifact control under the new runtime. This separates training effects from runtime/toolchain effects.

## Required campaign sequence

```text
ASUS boots Ubuntu
→ clones the pinned evaluation repository
→ acquires checksum-pinned candidate artifacts
→ qualifies matched candidate model-runtime combinations
→ admits only viable combinations to fine-tuning
→ fine-tunes the admitted parent
→ converts or quantizes the resulting checkpoint
→ requalifies the deployment artifact on the same ASUS
→ retains the paired before-and-after evidence
```

This is a target-device admission and qualification study, not a model leaderboard. Its conclusion applies only to the exact model-runtime-device tuple supported by the retained evidence.
