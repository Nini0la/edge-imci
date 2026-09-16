# EdgeIMCI ADTC submission and ASUS profiling handoff v1

> **Authority:** `PROJECT_EXECUTION_HANDOFF` · **Lifecycle:** `CURRENT` · Current only for reproducing or auditing the frozen Gate 1 candidate; it does not authorize Gate 2 model selection, training, TEST access, or submission.

## Objective

Produce the exact offline GGUF artifact, ASUS participant profile, official ADTC evidence and public submission package for the already selected EdgeIMCI fine-tune.

The canonical ADTC submission repository already exists:

```text
https://github.com/Nini0la/edgeIMCI-adtc-2026-submission
```

Do not create a replacement submission repository or submit the main EdgeIMCI research repository URL.

The work starts from the canonical designation:

```text
configs/deployment/qwen3_0_6b_provisional_product_candidate_v1.json
```

That file, not a model-family name or an old planning document, is the source of truth for the selected checkpoint.

## Selected source checkpoint

| Field | Pinned value |
| --- | --- |
| Candidate ID | `qwen3-0.6b-sft-selected-seed-20260824` |
| Base model | `Qwen/Qwen3-0.6B` |
| Base Hugging Face revision | `c1899de289a04d12100db370d81485cdf75e47ca` |
| Training run ID | `251039a3-4adc-4e74-8c30-069eb8aca6de` |
| Calibration cell | `qwen3-0.6b-sft-calibration-v1--016--dde3f482d8` |
| Modal volume | `edge-imci-finetune-artifacts` |
| Remote run path | `251039a3-4adc-4e74-8c30-069eb8aca6de` |
| Merged checkpoint path | `251039a3-4adc-4e74-8c30-069eb8aca6de/merged` |
| Remote manifest SHA-256 | `0e57732f7f216136af1a4ba894ae6c57debf148effd34ce3c235da7978cbd254` |
| Merged `model.safetensors` SHA-256 | `86bb2507e5e7d04ad35c6c933923b902d21652bd04c401055a97a0d4485fd76a` |
| Training configuration SHA-256 | `dde3f482d880151df14626ae9767711ce016d242c135b6b49a899ddf6d61ae1b` |
| Training recipe | LoRA, 3 epochs, learning rate `0.0002`, seed `20260824` |

The retained TEST report records 97.20% exact-record and decision equivalence, 99.89% field accuracy and 100% schema validity. It also records six preregistered clinical-threshold failures. The artifact is therefore a project-owner-designated **provisional product and submission placeholder**, not a production-clinical authorization. Preserve that wording in the technical report.

## Non-goals and protected boundaries

- Do not run a new model search, hyperparameter sweep or fine-tune.
- Do not replace the selected run with the seed control or first smoke run.
- Do not reopen or reuse the permanently closed reserved TEST authorization.
- Do not claim that GGUF conversion or quantization is lossless until checked.
- Do not claim ASUS evidence is an official audit result; it is participant evidence unless the organizers run audit mode.
- Do not modify an official `submission.json` after the profiler creates it.
- Do not publish model weights, personal contact details or a submission repository until the project owner has approved the public values and destination.

## Completion definition

This handoff is complete only when all of the following exist:

1. the selected merged checkpoint has been exported and its pinned hashes verified;
2. conversion provenance pins the exact `llama.cpp` source commit, commands and tool identities;
3. at least one exact GGUF derivative is checksum-pinned and validated with `llama.cpp`;
4. the final quantization/representation is selected using retained target-device evidence;
5. the exact final GGUF passes a complete official ADTC participant run on the ASUS;
6. the untouched official `submission.json` and GGUF bytes are registered by SHA-256 in an EdgeIMCI run sidecar;
7. the public submission package passes a clean-room download and offline-inference test; and
8. the final package contains approved metadata, exactly two domain prompts, an idempotent download script and a factual `REPORT.md`.

## Phase 1 — verify repository and designation

Record a clean, immutable repository commit for the conversion/profile work. The present worktree contains active uncommitted work, so do not describe it as a clean frozen harness until that work has been reviewed and committed.

Run the existing designation checks before touching the remote artifact:

```bash
uv run pytest -q \
  tests/test_provisional_product_candidate.py \
  tests/test_modal_app_extractor.py \
  tests/test_experiment_profiling.py

uv run python -m edge_imci.experiments.cli validate-registry
```

Read these inputs:

- `configs/deployment/qwen3_0_6b_provisional_product_candidate_v1.json`
- `experiments/training/matrices/qwen3-0.6b-sft-calibration-v1/selection.json`
- `experiments/training/qwen3-0.6b-structured-extraction-sft-v1-modal/qwen3-0.6b-sft-calibration-v1--016--dde3f482d8/edgeimci_run.json`
- `experiments/evaluation/qwen3-0.6b-one-shot-test-v1/aggregate_report_final_v2.json`
- `experiments/README.md`, section `ASUS/ADTC profiling registry`

## Phase 2 — export and verify the selected merged checkpoint

Retrieve the complete selected run from Modal into a staging directory outside Git:

```bash
uv run --extra modal-training modal volume get \
  edge-imci-finetune-artifacts \
  251039a3-4adc-4e74-8c30-069eb8aca6de \
  <staging-directory>/
```

Locate `remote_run_manifest.json` and `merged/model.safetensors`. Verify:

```bash
sha256sum <staging-directory>/remote_run_manifest.json
sha256sum <staging-directory>/merged/model.safetensors
```

The expected values are the two hashes in the selected-checkpoint table. Also verify every file listed in the remote manifest against its recorded SHA-256 and size. Stop if any byte differs. Preserve the exported manifest unchanged.

The Hugging Face base identity remains relevant conversion provenance even though the fine-tuned merged artifact comes from Modal. Do not redownload the base model and accidentally convert it instead of the merged checkpoint.

## Phase 3 — pin `llama.cpp`, convert and derive deployment representations

Clone `llama.cpp`, select and record a full commit SHA, build the conversion/quantization tools, and retain:

- repository URL and commit;
- compiler, CMake and build flags;
- converter and quantizer command lines;
- input merged-checkpoint hashes;
- output filenames, byte sizes and SHA-256 values; and
- tokenizer/chat-template files consumed by conversion.

Convert the merged Hugging Face directory to an unquantized GGUF control first. Then derive only the small set of representations worth testing on the ASUS—for example F16, Q8_0 and Q4_K_M when supported by the pinned toolchain. These are deployment representations of the same selected fine-tune, not a reopening of model selection.

Do not assume the smallest file is the best ADTC submission. Accuracy is weighted most heavily by the published profiler score, while throughput, memory and thermal behavior also matter. Retain every derivative's checksum and the parent/control relationship.

For each derivative:

1. confirm the file is valid GGUF and inspect its metadata;
2. run a direct `llama.cpp` smoke inference using the Qwen chat template with thinking disabled;
3. check strict JSON parsing and the EdgeIMCI model-facing schema;
4. run the approved non-TEST conversion/regression workload; and
5. record any difference from the merged checkpoint output.

If no deployment-regression workload is currently authorized, use version-controlled TRAIN/VALIDATION smoke material or obtain a new explicit evaluation authorization. Do not silently reuse the closed reserved TEST set.

## Phase 4 — ASUS representation selection and profiling

Use the ASUS running Ubuntu. Record exact CPU, RAM, storage, OS/kernel, BIOS/firmware, `llama.cpp` commit/build, thread count, context, batch settings, governor/power state and temperature sensors.

Run short profiler smoke tests with `--skip-accuracy` only to eliminate invalid or clearly inferior GGUF derivatives. Select the final representation using the declared quality-preservation, throughput, memory and thermal criteria. Once selected, freeze its filename and SHA-256; all final evidence must refer to those exact bytes.

For supplemental EdgeIMCI profiling, retain cold start, task latency/time-to-valid, process and whole-system memory, swap, CPU utilization, temperature and throttling. Store supplemental telemetry separately from the official report.

## Phase 5 — complete the existing ADTC submission repository

Clone the existing EdgeIMCI submission repository on the ASUS and pin the starting commit:

```bash
git clone \
  https://github.com/Nini0la/edgeIMCI-adtc-2026-submission.git \
  edgeIMCI-adtc-2026-submission

cd edgeIMCI-adtc-2026-submission
git rev-parse HEAD
git status --porcelain
```

Use this repository for the final public package:

```text
https://github.com/Nini0la/edgeIMCI-adtc-2026-submission
```

It should remain aligned with the current official upstream template:

```text
https://github.com/Africa-Deep-Tech-Foundation/adtc-2026-submission-template
```

Record both the existing submission-repository commit and the official template commit used for comparison. Do not overwrite repository-specific work by blindly replacing it with a fresh template. Review and merge only required template changes. The public repository must contain:

```text
metadata.json
download_model.sh
REPORT.md
.gitignore
model/                 # ignored; populated by download_model.sh
```

Requirements from the current official template:

- the repository is public at evaluation time;
- the weight is a GGUF file and runs through `llama.cpp`;
- inference works fully offline after the download step;
- `metadata.json` has no placeholders and uses domain `healthcare_medical`;
- `test_prompts` contains exactly two approved domain prompts;
- `_runtime.model_path` exactly matches the downloaded GGUF location;
- `download_model.sh` is idempotent and needs no credentials;
- model weights are not committed to Git; and
- `REPORT.md` factually covers the problem, African context, design, quantization choice, constraints and measured benchmarks.

Host the final GGUF at a stable public location, preferably a dedicated public Hugging Face model repository/revision or release. Pin the uploaded file by commit/revision and SHA-256. The download script should verify the expected SHA-256 and fail closed before returning success.

Public model hosting, contact details, pushes to the existing public submission repository and the final Devpost submission are external actions. Confirm the project owner's intended accounts, team ID, submitter details, prompts, model license and publication authorization before performing them.

## Phase 6 — pin and run the official profiler

Use the official profiler repository:

```text
https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler
```

Pin a full profiler commit and its bundled report-schema revision. Install/build `llama-bench` from the pinned `llama.cpp` toolchain and ensure it is on `PATH`.

Run an iteration smoke:

```bash
bash download_model.sh

adtc-profiler run \
  --submission <path-to-edgeIMCI-adtc-2026-submission> \
  --mode participant \
  --output <new-run-directory>/submission.json \
  --skip-accuracy
```

Then run the final complete participant profile without `--skip-accuracy`:

```bash
adtc-profiler run \
  --submission <path-to-edgeIMCI-adtc-2026-submission> \
  --mode participant \
  --output <new-run-directory>/submission.json
```

Do not edit the generated JSON. Validate it against the pinned official schema:

```bash
uv run python -m edge_imci.experiments.cli validate-adtc \
  <new-run-directory>/submission.json \
  <pinned-profiler-checkout>/src/adtc_profiler/schema/adtc-profiler.schema.json
```

Register the untouched report and exact GGUF in an `OFFICIAL_ADTC` EdgeIMCI sidecar under:

```text
experiments/profiling/adtc/runs/<run-id>/
```

The sidecar must record:

- experiment `selected-artifact-official-adtc-v1`;
- selected source training run and source weights hash;
- final GGUF hash and size;
- conversion and quantization identities;
- profiler and report-schema commits;
- ASUS/environment identity;
- full command and accuracy configuration; and
- artifact roles `OFFICIAL_ADTC_REPORT` and `DEPLOYED_MODEL`.

Repeat final profiling only as a predeclared reproducibility check, never to discard an inconvenient valid run. Each invocation gets a distinct immutable directory.

## Phase 7 — clean-room submission check

Before publication/submission, test from a fresh checkout or disposable directory:

1. clone `https://github.com/Nini0la/edgeIMCI-adtc-2026-submission` into a fresh directory;
2. run `bash download_model.sh` with no credentials;
3. verify the downloaded GGUF checksum;
4. disable outbound network access;
5. run `llama.cpp` inference and an ADTC profiler smoke;
6. confirm exactly two public prompts and no placeholder metadata;
7. confirm no model weights, private data, TEST records, secrets or personal information beyond approved submitter fields are committed; and
8. confirm `REPORT.md` metrics match the retained ASUS report and identify them as participant/development measurements.

The organizer's audit run is external evidence. When an audit report is supplied, preserve it unchanged and run:

```bash
adtc-profiler compare submission.json audit.json --output verdict.json
```

## Final project updates

After the exact GGUF and official participant report are valid:

- add their hashes and provenance to the two selected registry experiments;
- regenerate `experiments/registry/experiment_matrix.yaml`;
- validate the registry and ADTC sidecars;
- create a profile summary only from comparable runs;
- update the provisional designation through an explicit project-owner decision rather than silently changing its constraints; and
- keep the six clinical-threshold failures and lack of production-clinical authorization visible.

## Agent instruction

Use this exact prompt when handing the task to another agent:

> Execute `docs/adtc_submission_and_asus_profiling_handoff_v1.md`. Start from the canonical selected candidate in `configs/deployment/qwen3_0_6b_provisional_product_candidate_v1.json`: training run `251039a3-4adc-4e74-8c30-069eb8aca6de`, merged weights SHA-256 `86bb2507e5e7d04ad35c6c933923b902d21652bd04c401055a97a0d4485fd76a`. The canonical public submission repository is `https://github.com/Nini0la/edgeIMCI-adtc-2026-submission`; do not create another one. Do not perform model selection or fine-tuning and do not reopen the closed reserved TEST. Export and verify the selected merged checkpoint, pin `llama.cpp`, convert/quantize with full provenance, qualify the exact GGUF on the ASUS, run the pinned official ADTC profiler, preserve immutable evidence, and complete a clean-room check of the existing submission repository. Pause for project-owner input before public model hosting, personal metadata, pushes to the public repository or Devpost submission.
