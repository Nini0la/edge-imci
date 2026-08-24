# Experiment and edge-profiling guidance

This directory is the home for EdgeIMCI model experiments and their evidence. The primary learned-task question is whether a small instruct model can transform free-form findings from a supported whole sick-child encounter into the canonical model-facing encounter JSON without losing positives, negatives, UNKNOWN state, measurements, durations or qualifiers. The deterministic clinical pipeline—not the model—then owns completeness, classification, urgency, referral and action synthesis.

The current expanded substrate is `imci-major-sick-child-v1`, paired with `imci-major-sick-child-holistic-completeness-v2` and the approved hackathon decision set `imci-major-sick-child-review-decisions-v1`. Its scope is children aged `2 <= age_months < 60` across general danger signs, cough/difficult breathing, diarrhoea, fever including measles, and ear problem. This is complete only relative to that supported initial-encounter scope, not every IMCI activity. The 13 blocking clinical/policy questions are resolved for this bounded hackathon representation; this is not production clinical approval. Product-level golden-slice work may proceed after verification, while bulk generation and training remain not started.

Before the project begins running many SFT, RL, quantization, and edge-deployment variants, it now has two first-class pieces of infrastructure:

1. an **experiment registry** that records every model/training configuration and links it to its evaluation results; and
2. a **profiling registry** that stores the ASUS/ADTC edge evidence separately from model-quality results.

Candidate-specific fine-tuning also has a mandatory predecessor: exact model-runtime combinations are admitted on the ASUS Ubuntu deployment computer using a frozen repository checkout, reviewed model checksums, matched task and neutral-speed workloads, and sustained system/thermal profiling. The converted or quantized post-training artifact is then requalified with the same harness. See [`docs/target_device_model_runtime_qualification_plan.md`](../docs/target_device_model_runtime_qualification_plan.md).

The purpose is to make the state of the experimental program explicit and machine-readable. An experiment is discoverable from committed artifacts rather than reconstructed from conversation, filenames, or memory. The matrix is a research map, not a commitment to run every possible branch. The initial rows remain `PLANNED`; this infrastructure implementation did not execute any scientific work or declare the proposed holistic golden set approved.

## Implemented layout

The existing experiment-category directories remain useful for their run artifacts:

```text
experiments/
├── README.md
├── registry/
│   ├── experiment_matrix.json      # canonical machine-readable registry
│   ├── experiment_matrix.yaml      # generated human-readable mirror
│   ├── campaign_branches.json      # strategy branches, gates, and triggers
│   ├── run_index.json              # generated from validated common sidecars
│   ├── schemas/                    # versioned JSON Schemas
│   └── rate_cards/                 # verified production rate cards only
├── profiling/
│   └── adtc/
│       ├── runs/                   # immutable official reports plus sidecars
│       ├── summaries/              # computed aggregates by edge profile
│       └── comparisons/            # participant-versus-audit verdicts
├── qualification/
│   └── asus/                        # admission and paired post-training evidence
├── baselines/                           # untuned model run artifacts
├── sft/                                 # supervised fine-tuning artifacts
└── rl/                                  # later reward/RL artifacts
```

The registry is an index, not a replacement for the detailed artifacts in these directories.

The provider-neutral implementation lives under `src/edge_imci/experiments/`. It includes registry validation, canonical hashing and provenance, typed environment telemetry, atomic run tracking, decimal accounting, ADTC preservation checks, profile summaries, and a CLI. It imports no Modal, Azure, hosted-model, MLX, or ADTC SDK.

## 1. Experiment registry

`experiments/registry/experiment_matrix.json` is the canonical experiment matrix. Its YAML counterpart is generated from the JSON and deserializes to the same data. Do not edit the JSON and YAML independently.

Each experiment is one row/object. It records the scientific question and material factors separately from lifecycle, intended evidence, and immutable reproducibility references:

```json
{
  "experiment_id": "qwen3-1.7b-sft-v1-modal",
  "definition_version": "1.0.0",
  "experiment_type": "TRAINING",
  "priority": "CORE",
  "status": "PLANNED",
  "hypothesis": "Whole-encounter supervised fine-tuning improves the 1.7B model.",
  "decision_question": "Does SFT-v1 produce a viable first EdgeIMCI checkpoint?",
  "branch_id": "qwen3-1.7b-sft-v1",
  "prerequisites": ["Validated fast controlled corpus"],
  "branch_trigger": null,
  "material_configuration": {
    "model_family": "Qwen3-1.7B",
    "training_stage": "SFT_V1",
    "preferred_environment": "MODAL"
  },
  "reproducibility": {
    "required_reference_kinds": ["CONFIG", "MODEL", "DATASET"],
    "references": [],
    "unresolved_inputs": [
      "base checkpoint revision",
      "approved training dataset and mixture",
      "training recipe",
      "Modal image/config"
    ]
  },
  "evidence": [
    {
      "evidence_id": "training_metrics",
      "evidence_class": "SCIENTIFIC",
      "applicability": "APPLICABLE",
      "artifact_ref": null
    }
  ],
  "run_ids": []
}
```

Evidence uses repository-relative artifact paths after validated evidence exists. For declared applicable evidence, `artifact_ref: null` means applicable but not yet available. `applicability: NOT_APPLICABLE` is distinct, cannot carry an artifact reference, and is never inferred from `null`.

### Field meanings

| Field | Meaning |
| --- | --- |
| `experiment_id` | Unique, stable identifier for this exact scientific protocol and material configuration. |
| `definition_version` | Schema-level revision of the definition; it does not authorize reuse for a material change. |
| `experiment_type` | One of the fixed operations taxonomy values. |
| `priority` | Research importance: `CORE`, `CONDITIONAL`, or `OPTIONAL`. This is independent of lifecycle state. |
| `status` | Lifecycle: `PLANNED`, `READY`, `RUNNING`, `COMPLETE`, `SUPERSEDED`, or `FAILED`. |
| `hypothesis` / `decision_question` | The claim being tested and decision the evidence must support. |
| `branch_id` / `branch_trigger` | Link to campaign strategy without turning an unresolved branch into a pseudo-experiment. |
| `material_configuration` | Known fixed scientific factors; unresolved values remain explicit while `PLANNED`. |
| `reproducibility` | Required reference kinds, resolved immutable references, and unresolved inputs. |
| `evidence` | Separate scientific, execution, profile, and external evidence with explicit applicability. |
| `run_ids` | Zero or more immutable execution attempts associated with this definition. |

Add fields when needed to identify an experiment unambiguously, but keep detailed per-case results, prompts, runtime metadata, and hardware measurements in their own artifacts. The matrix should remain compact enough to scan and automate against.

Primary model metrics are schema validity, whole-record exact match, field accuracy, positive/negative/UNKNOWN preservation, measurements, durations, qualifiers and intervention-state accuracy. The predicted encounter is also passed through the same deterministic engine for downstream classification, completeness, management, referral and separately visible urgent-action equivalence. Lundin remains a complementary external competence/generalization benchmark and must not be merged with EdgeIMCI product metrics into a single accuracy number.

The canonical dataset policy is `configs/training/structured_extraction_dataset_policy_v1.json`. Splits are assigned to parent semantic encounters, never individual paraphrases. Cases 77 and 78 are reserved out-of-scope TEST parents; the separate `oos-extract-young-respiratory-001` and `oos-extract-older-fever-001` parents are forced to TRAIN and await reviewed language. Longitudinal Plan B/C reassessment state remains corpus-ineligible, generic acquisition mode is not invented as a v1 label, and contradiction state remains a deterministic derived output.

### Secondary and component evaluation

The older narrow evaluation machinery remains useful for:

- strict structured diagnostics;
- narrow v0 regression testing;
- progressive acquisition and multi-turn behavior;
- the existing 14-case component golden suite; and
- controlled semantic-to-language conversion checks.

These are secondary/component/regression evaluations under the current product framing. Preserve their historical artifacts and continue running them where relevant, but do not treat them as substitutes for structured-extraction evaluation and downstream deterministic decision equivalence. Progressive one-question-at-a-time interaction is a fallback and research mode rather than the primary product axis.

### Priority and lifecycle

`priority` distinguishes near-term importance from the broader research map:

| Priority | Meaning |
| --- | --- |
| `CORE` | Critical-path evidence for the first credible holistic model and hackathon submission. |
| `CONDITIONAL` | Run only when earlier evidence, available time, or a clear comparison justifies it. |
| `OPTIONAL` | Useful exploratory evidence that must not appear to be a submission prerequisite. |

`status` records what has happened:

| Status | Meaning |
| --- | --- |
| `PLANNED` | Defined, but prerequisites or scheduling are not complete. |
| `READY` | Inputs, approvals, and execution configuration are available. |
| `RUNNING` | Execution is currently in progress. |
| `COMPLETE` | Required artifacts for the experiment's declared scope exist and passed validation. |
| `SUPERSEDED` | Retained historically but replaced by a newer experiment; never silently repurposed. |
| `FAILED` | Attempted but did not complete successfully; detailed evidence records the failure. |

Changing lifecycle status must not mutate an experiment into a different model, checkpoint, recipe, dataset, or precision. Those changes require a new `experiment_id`.

### Registry rules

- Create the matrix row when an experiment is planned, not only after every run is complete.
- Use a stable, unique `experiment_id`; do not reuse an ID for a materially different checkpoint, dataset mixture, training recipe, or precision.
- Before a row becomes `READY`, its fields or linked versioned configuration must resolve the exact checkpoint revision, dataset version and mixture, training recipe, conversion settings, and deployed precision. A human-readable model name alone is not reproducible identity.
- Fill evaluation references only after the referenced artifacts exist and have passed their relevant checks.
- Keep applicable but unavailable evidence references as `null`. Declare non-applicability explicitly; never use placeholder paths or fabricated scores.
- Keep structured extraction, downstream decision equivalence, urgent-action equivalence, Lundin, and any secondary/component results separate. Do not collapse incompatible benchmarks into one score.
- Treat JSON as canonical. Regenerate YAML after every JSON change and verify semantic equality.
- Prefer append-only history. If an experiment is superseded, record that state explicitly rather than silently turning its row into another experiment.
- Validate `priority` and `status` against their fixed enumerations.

### Current experiment strategy

The matrix should show the research landscape without implying that every row will be executed. The current approximate prioritization is:

**Core / critical path**

- Qwen3-1.7B base structured-extraction baseline;
- ASUS admission of the exact untuned candidate model-runtime combination;
- the first Qwen3-1.7B extraction SFT;
- post-SFT structured extraction and downstream decision-equivalence evaluation;
- same-ASUS requalification of the exact converted or quantized deployment artifact; and
- ADTC profiling of the exact deployment representation.

Qwen3-4B may serve as a larger capacity anchor when that comparison is affordable and useful.

**Useful if inexpensive**

- Qwen3-0.6B as a lower-capacity bound;
- additional quantizations of Qwen3-1.7B for edge trade-offs; and
- further SFT variants only when preceding evidence motivates them.

Lundin is an optional external branch and remains off the critical path.

**Conditional / optional branches**

- Qwen3.5-2B challenger;
- Qwen3.5-4B or Tinker-based work;
- RL or preference optimization;
- SVD experiments;
- additional compression; and
- extensive hyperparameter sweeps.

None of these conditional branches is required before the first hackathon submission. They should not consume critical-path time without evidence that they address a measured limitation.

The following remains a conceptual scan view. The implemented registry records the currently instantiated definitions as `PLANNED`; neither this view nor those rows claim that an evaluation has run:

| Model | Training | Precision | Priority | Status | Structured extraction | Decision equivalence | Urgent-action equivalence | Lundin | Edge profile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-1.7B | base | deployment candidate TBD | `CORE` | `PLANNED` | applicable | applicable | applicable | applicable | applicable |
| Qwen3-1.7B | sft-v1 | deployment candidate TBD | `CORE` | `PLANNED` | applicable | applicable | applicable | applicable | applicable |
| Qwen3-4B | base comparison | Q4_K_M candidate | `CONDITIONAL` | `PLANNED` | conditional | conditional | conditional | conditional | conditional |
| Qwen3-0.6B | base lower bound | deployment candidate TBD | `OPTIONAL` | `PLANNED` | optional | optional | optional | optional | optional |

The cells above describe intended applicability and priority only. They are not result claims or fabricated artifact references.

### Hackathon and production-oriented separation

The bounded model contribution is structured interpretation:

```text
free-form whole-encounter PHC findings
        ↓
EdgeIMCI structured extractor
        ↓
model-facing encounter JSON
```

The end-to-end EdgeIMCI architecture uses that learned output as deterministic clinical input:

```text
free-form PHC findings
        ↓
structured extraction
        ↓
validated deterministic IMCI engine
        ↓
classifications and actions
        ↓
LLM presentation or explanation
```

The model is not trained to invent or directly predict downstream classifications, actions or urgency. Those results are nevertheless evaluated end to end by running the predicted state through the same deterministic engine used for the gold state.

## 2. ASUS/ADTC profiling registry

Hardware performance is a different dimension from clinical/model quality. Do not put token rates, RAM, first-token latency, or other profiler measurements directly in the experiment matrix. The matrix should point to a structured edge-profile summary instead.

The [ADTC 2026 challenge page](https://adtc-2026.devpost.com/) defines the target as an x86-64 laptop with an Intel Core i5 10th–12th generation or AMD Ryzen 5 3000–5000 CPU, 8 GB DDR4 RAM, integrated graphics only, a 256 GB SSD, and Ubuntu 22.04 LTS. The ASUS development machine is a **participant-laptop proxy** unless its recorded specifications match that profile; an ASUS result is not itself an official audit result.

The [official ADTC profiler repository](https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler) is the source of truth for the profiling contract. It profiles local GGUF models through `llama.cpp`, requires `llama-bench` on `PATH`, and emits schema-validated JSON. Pin the profiler version and source commit used for every EdgeIMCI run because the tool and schema may change during the competition.

Conceptually:

```text
EXPERIMENT MATRIX
       |
       |-- model and training configuration
       |-- structured-extraction evaluation
       |-- downstream decision-equivalence evaluation
       |-- urgent-action equivalence
       |-- Lundin external evaluation result
       |-- secondary/component evidence, when applicable
       `-- edge_profile ----------------------.
                                                |
                                                v
                                      ASUS / ADTC PROFILE
                                      - generation tok/s
                                      - first-token latency
                                      - peak and steady RSS
                                      - CPU utilization and thermals
                                      - environment and model metadata
                                      - accuracy entries
                                      - reproducibility metadata
```

Earlier planning identified these candidate profiling configurations:

```text
asus-qwen3-0.6b-fp16
asus-qwen3-0.6b-q8
asus-qwen3-1.7b-q8
asus-qwen3-1.7b-q6
asus-qwen3-4b-q4_k_m
```

These names describe configurations, not results or obligations to run every profile. Select them according to the current priority strategy and evidence from earlier stages. A trained checkpoint should include its training identifier so that it cannot be confused with the untuned base model, for example `asus-qwen3-1.7b-sft-v2-q8-v1`.

### Official report contract

The profiler's bundled [JSON Schema](https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler/blob/main/src/adtc_profiler/schema/adtc-profiler.schema.json) is strict: its objects use `additionalProperties: false`. Preserve the generated `submission.json` unchanged. Do **not** insert EdgeIMCI-only fields such as `profile_id`, `experiment_id`, `run_id`, timestamp, notes, or custom averages into that file.

The official report contains these top-level blocks:

| Official block | Relevant contents |
| --- | --- |
| `schema_version`, `profiler_version` | Versions of the report contract and profiler. |
| `submission` | Team, domain, language, test prompts, model runtime, quantization, parameter estimate, and packaging claims. EdgeIMCI's domain is `healthcare_medical`. |
| `environment` | `measured_on`, CPU model, installed RAM, GPU description, and operating system. `measured_on` is either `participant_laptop` or `audit_cloud_vm`. |
| `throughput` | Required generation tokens/second and first-token latency, plus prompt-token and generated-token counts. |
| `memory` | Required peak and steady-state resident memory in MB, with optional peak virtual memory. |
| `accuracy` | Zero or more benchmark records containing benchmark, dataset version, language, sample count, score, and optional metric. |
| `cpu_thermal` | Required p99 CPU utilization and throttling flag, plus nullable peak core temperature. |
| `reproducibility` | Git commit SHA, Docker image digest, and random seed. |
| `model_info` | GGUF-derived parameter count, context length, architecture, claimed parameter estimate, and parameter-match check. |

Use the official JSON paths in summaries, including:

```text
throughput.tokens_per_second_generation
throughput.first_token_latency_ms
memory.peak_rss_mb
memory.steady_state_rss_mb
memory.peak_vms_mb
cpu_thermal.cpu_percent_p99
cpu_thermal.core_temp_c_peak
cpu_thermal.throttled
model_info.context_length
```

The current profiler does **not** emit a prompt-tokens-per-second field or a distinct model-memory field. Do not invent either as an ADTC measurement. The profiler currently runs CPU-only `llama-bench` with a 512-token prompt and 128 generated tokens by default. Its `first_token_latency_ms` is an estimate derived from the prompt-processing rate for the whole prompt, rather than an independently timed application request. Preserve that distinction in reports and presentations.

### Submission input and profiler commands

The profiler expects a submission directory containing `metadata.json` and the GGUF model referenced by `_runtime.model_path`. All public metadata fields are required, extra public fields are rejected, and `test_prompts` must contain exactly two prompts. Use the profiler's `examples/demo-submission/` directory and canonical schema when building EdgeIMCI's submission package.

Install a pinned revision rather than silently following a moving `main` branch. The operational prerequisites are Python and `llama-bench` from `llama.cpp` on `PATH`.

Run the local participant profile with:

```bash
adtc-profiler run \
  --submission /path/to/edgeimci-submission \
  --mode participant \
  --output submission.json
```

`--skip-accuracy` is appropriate only for quick iteration. A final candidate report must come from a complete run because accuracy contributes 50% of the published score. The current CLI defaults to seed 42, `arc_easy`, and an accuracy limit of 50 for participant-side runs; record any overrides. The real audit uses hidden validation data.

Audit mode belongs to the evaluation environment. When an official audit report becomes available, compare it with the participant report and retain the verdict:

```bash
adtc-profiler compare submission.json audit.json --output verdict.json
```

The current comparison contract flags deviations beyond ±15% for peak/steady RSS and ±25% for generation throughput/first-token latency; deviations above 50%, zero or missing values, mismatched team IDs, incorrect environments, or schema violations fail comparison.

### Individual profile runs

Store every generated report as an immutable artifact together with an EdgeIMCI sidecar:

```text
experiments/profiling/adtc/runs/
└── asus-qwen3-1.7b-q8-v1-20260820T120000Z-01/
    ├── submission.json       # untouched, schema-valid profiler output
    └── edgeimci_run.json     # EdgeIMCI identity and provenance
```

The sidecar owns the fields that do not belong in the official schema:

```json
{
  "schema_version": "1.0.0",
  "profile_id": "asus-qwen3-1.7b-q8-v1",
  "run_id": "asus-qwen3-1.7b-q8-v1-20260820T120000Z-01",
  "experiment_id": "qwen3-1.7b-base-q8",
  "report_path": "experiments/profiling/adtc/runs/asus-qwen3-1.7b-q8-v1-20260820T120000Z-01/submission.json",
  "report_sha256": "...",
  "model_artifact_sha256": "...",
  "run_timestamp": "2026-08-20T12:00:00Z",
  "profiler_source_revision": "...",
  "command": [
    "adtc-profiler",
    "run",
    "--submission",
    "/path/to/edgeimci-submission",
    "--mode",
    "participant",
    "--output",
    "submission.json"
  ],
  "accuracy_skipped": false,
  "notes": ""
}
```

The ellipses above are documentation placeholders, not valid completed evidence. Populate digests and the pinned profiler source revision before registering the run. The official report contains submitter contact details, so use only contact information approved for publication before committing it to this repository.

### Immutability and summaries

Never overwrite an individual run because a later run looks cleaner. Each invocation gets a new `run_id` and directory. Failed or anomalous runs should remain available with their status and notes when they are useful evidence. A failed invocation that produces no schema-valid `submission.json` must be recorded as failed in an EdgeIMCI sidecar; never manufacture an official report to fill the gap.

A separate summary artifact should reference the included run IDs and compute aggregates such as:

- run count;
- arithmetic mean and median for generation tokens/second, first-token latency, peak RSS, and steady-state RSS;
- minimum and maximum, or another stated dispersion measure; and
- the aggregation timestamp and method/version.

Only aggregate comparable runs: same exact GGUF digest, profiler/schema revision, participant machine and OS state, runtime settings, accuracy configuration, and workload. Do not average participant and audit measurements together. The experiment matrix's `edge_profile` should normally refer to this stable summary/profile ID, not to whichever raw run happened most recently. Summaries may be regenerated when new immutable runs are deliberately admitted, but their input run IDs, official report digests, exclusions, and aggregation method must remain explicit. This prevents one unusual run from silently replacing the underlying evidence.

### ADTC scoring context

The published leaderboard formula weights accuracy at 50%, generation-throughput performance at 30%, and memory efficiency at 20%, then applies a 10-point thermal penalty when throttling occurs or temperature exceeds 85°C. The current published reference throughput is 15 generation tokens/second, and memory efficiency is measured against a 7 GB budget. An out-of-memory or sandbox crash disqualifies the submission. These competition constants are externally controlled and may change; record the rules date/version used for any derived score rather than baking the constants into raw evidence.

## 3. Workflow for each experiment

Agents and contributors should use the following sequence:

1. **Register the configuration.** Add a unique row for the exact model, checkpoint/training state, and precision; set unavailable applicable references to `null`.
2. **Mark priority and lifecycle.** Record whether the experiment is `CORE`, `CONDITIONAL`, or `OPTIONAL`, and its current status.
3. **Produce the relevant model artifact.** Preserve exact checkpoint, dataset, training-recipe, and conversion provenance. A base-model evaluation does not require a training artifact.
4. **Run applicable product evaluations.** Evaluate schema validity, exact/field extraction, UNKNOWN preservation, and downstream decision/urgent-action equivalence when the experiment is intended to answer those questions.
5. **Run relevant component regressions.** Preserve narrow v0, structured diagnostic, 14-case golden, acquisition, or multi-turn checks when they provide useful regression evidence.
6. **Run Lundin when appropriate.** Keep the named external revision and scoring policy separate from EdgeIMCI product metrics.
7. **Profile the deployable representation when relevant.** Run the exact GGUF checkpoint and quantization with a pinned official profiler revision.
8. **Preserve immutable raw evidence.** Keep detailed evaluation artifacts and every untouched official profiling report with its EdgeIMCI sidecar.
9. **Link results, do not copy them.** Update the matrix only with stable references to completed, validated artifacts; never paste scores or hardware measurements into a row.
10. **Regenerate and validate the registry.** Produce YAML deterministically from canonical JSON, check semantic equality, validate priority/status values, resolve every non-null reference, enforce unique IDs, and ensure each profile summary names existing immutable runs.

Not every planned experiment must immediately run every evaluation. Applicability should be explicit in the eventual registry schema; lack of applicability must not be represented by a fabricated path or score.

## 4. Separation of concerns

Keep the following boundaries intact:

- The **experiment matrix** answers: What configurations exist, and where is their evidence?
- An **evaluation artifact** answers: How did this configuration perform on one named product, component, regression, or external benchmark under one versioned policy?
- A **raw profiling artifact** answers: What happened in one edge-performance invocation?
- A **profile summary** answers: What aggregate edge performance was observed across a declared set of comparable runs?

This structure lets humans review the program as a matrix while allowing scripts and agents to fill missing cells, validate provenance, compare variants, and compute edge Pareto trade-offs without depending on conversational context.

## 5. Implemented registry and tracker

The versioned schemas are:

- `schemas/experiment.schema.json` for the canonical experiment matrix;
- `schemas/campaign_branch.schema.json` for evidence-triggered strategy branches;
- `schemas/run.schema.json` for common `edgeimci_run.json` sidecars;
- `schemas/rate_card.schema.json` for verified, versioned unit rates; and
- `schemas/profile_summary.schema.json` for declared comparable-run aggregates.

Owned structural objects reject extra fields. Scientific metric maps, sanitized provider payloads, and similarly intentional extension points remain open. Runtime validation adds cross-record rules that JSON Schema alone cannot enforce: unique identities, explicit applicability, `READY` reproducibility closure, safe repository paths, immutable local hashes or remote revisions, branch links, environment-adapter matching, terminal-run immutability, and consistent experiment-definition digests across repeated runs.

The common lifecycle is deliberately small:

```python
from edge_imci.experiments import ExperimentRegistry, RunTracker

registry = ExperimentRegistry()
tracker = RunTracker(registry)

with tracker.start(
    experiment_id="a-ready-experiment-id",
    output_dir="experiments/sft/a-new-immutable-run",
    config={"config_id": "recipe", "version": "1.0.0", "data": recipe},
    execution=typed_execution_metadata,
    models=model_references,
    datasets=dataset_references,
    prompts=prompt_references,
) as run:
    # Perform model/provider setup inside this boundary so failures are durable.
    run.record_scientific_metrics(scientific_summary)
    run.record_validation(validation_summary)
    run.record_usage(
        usage_id="provider-usage-1",
        source="named-provider",
        metrics=raw_usage,
        raw_payload=provider_payload,
    )
    run.add_artifact(result_path, artifact_id="detailed-results", role="EVALUATION_RESULT")
```

`start()` validates that the experiment is execution-eligible (`READY`, already `RUNNING`, or `COMPLETE` when an exact repeat is required), snapshots and canonically hashes config, captures sanitized Git/runtime provenance, and atomically writes `RUNNING` before control enters the body. Normal exit finalizes `SUCCEEDED`; exceptions and interruptions finalize `FAILED` or `INTERRUPTED` and are re-raised. Every retry or exact repeat receives a new output directory and `run_id`. A terminal sidecar cannot be reused. Billing reconciliation is the sole explicit mutation channel: it appends a new accounting record and audit event without deleting the original estimate or raw usage.

Environment telemetry is a discriminated contract. `LOCAL_DEV`, `TARGET_HARDWARE`, `MODAL`, `EXTERNAL_API`, `HYBRID`, `OFFICIAL_ADTC`, and `MANAGED_TRAINING` each permit only their matching extension. `execution_provider`, hosted `api_provider`, and model publisher/source identities remain separate. Non-applicable fields are absent, not `null`.

### Commands

Install the project, then use either the console command shown below or `python -m edge_imci.experiments.cli`:

```bash
edgeimci-experiments validate-registry
edgeimci-experiments sync-yaml
edgeimci-experiments validate-run experiments/path/to/run/edgeimci_run.json
edgeimci-experiments build-index experiments --output experiments/registry/run_index.json
edgeimci-experiments derive-cost raw_usage.json verified_rate_card.json \
  --calculation-id calculation-v1 --output derived_cost.json
edgeimci-experiments validate-adtc submission.json /path/to/pinned/adtc-profiler.schema.json
edgeimci-experiments summarize-profiles run-a/edgeimci_run.json run-b/edgeimci_run.json \
  --schema /path/to/pinned/adtc-profiler.schema.json \
  --summary-id asus-selected-artifact-v1 \
  --output experiments/profiling/adtc/summaries/asus-selected-artifact-v1.json
```

`run_index.json` is derived only from validated files named `edgeimci_run.json`. Historical `run.json` and `strict_run.json` artifacts are not rewritten or retroactively promoted to the common schema.

Canonical configuration hashing uses UTF-8 JSON with sorted keys, compact separators, and one trailing newline. Local prompts, datasets, checkpoints, configs, validation artifacts, and output artifacts are hashed from bytes wherever applicable. A remote-only model uses its immutable provider revision/snapshot; the tracker does not fabricate a local file hash.

### Accounting and profile summaries

Raw usage remains in the run. Cost calculations refer to a named rate card and use decimal arithmetic; estimates, actual evidence, and reconciliations are separate records. API calculations can report cost per attempt and accepted example; training calculations can report cost per run and per 1,000 examples. Hybrid totals enumerate component calculation IDs and reject duplicate components.

Official `submission.json` bytes remain outside the EdgeIMCI schema and are validated against a caller-supplied schema from the pinned profiler revision. The common sidecar stores EdgeIMCI provenance and hashes the official report plus exact deployed artifact. Profile summaries take explicit sidecar IDs, record every inclusion/exclusion, and aggregate only a single comparison fingerprint: exact model digest, profiler/schema revision, measurement designation, environment, runtime settings, workload, and accuracy configuration. Participant-laptop and audit-cloud measurements cannot share a fingerprint and are therefore never averaged together.

## 6. Current gate

All initial experiment definitions remain `PLANNED` because the proposed holistic product golden suite is still awaiting domain approval. The tracker refuses to start those rows. A contributor may move a definition to `READY` only after all declared material references resolve to immutable local hashes or remote revisions and `unresolved_inputs` is empty. This is an execution gate, not a clinical-approval mechanism.

The empty committed run index and empty profiling directories are infrastructure placeholders, not evidence. No production rate card is committed; tests use fictional cards only. The existing baseline and rendering-bake-off artifacts remain unchanged historical evidence.

## Sources and change control

This guidance was checked against the following primary sources on 20 August 2026:

- [Africa Deep Tech Challenge 2026 overview, requirements, hardware profile, and scoring](https://adtc-2026.devpost.com/)
- [Official ADTC profiler repository and CLI documentation](https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler)
- [Canonical ADTC profiler JSON Schema](https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler/blob/main/src/adtc_profiler/schema/adtc-profiler.schema.json)
- [Current throughput implementation](https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler/blob/main/src/adtc_profiler/throughput.py)

Recheck these sources before final profiling and submission. If they conflict with this guide, the current competition rules and the profiler schema pinned for the run take precedence; update this document and record the change.
