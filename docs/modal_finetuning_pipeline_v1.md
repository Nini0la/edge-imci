# EdgeIMCI Modal fine-tuning pipeline v1

> **Authority:** `IMPLEMENTED_PIPELINE` · **Lifecycle:** `CURRENT` · This is research training infrastructure, not clinical or deployment authorization.

The first pipeline fine-tunes the immutable Hugging Face revision
`Qwen/Qwen3-0.6B@c1899de289a04d12100db370d81485cdf75e47ca` with LoRA on one
Modal A10G. It learns only free-form PHC findings to model-facing encounter
JSON. The deterministic clinical engine remains outside the model.

## Guardrails

- `structured_extraction_sft_release_v1.json` is a new scoped release; it does
  not rewrite the historical corpus review that prohibited training at export
  time.
- SHA-256 checks pin the release, corpus manifest, and chat-message dataset.
- All variants of a semantic parent remain in one partition.
- The runner validates all 1,497 records and their target schema, then returns
  only 1,239 TRAIN and 115 VALIDATION records to the trainer.
- The 143 TEST records are checked for split integrity but never returned to
  tokenization, training, validation, or the eight-example generation smoke.
- Sequence truncation is forbidden. The observed maximum is 1,026 tokens under
  the pinned tokenizer, below the configured 1,536-token limit.
- Loss is masked over the system/user prompt and applied only to the assistant
  JSON response.
- Qwen thinking is disabled consistently in training and validation inference.
- Training authorization does not authorize deployment or production clinical
  use. Formal ASUS admission and post-training requalification remain separate.

## Commands

Install the local Modal client and run the fail-closed preflight:

```bash
uv sync --extra dev --extra modal-training
uv run --extra modal-training modal run \
  -m edge_imci.training.modal_finetune --dry-run
```

Launch a named run:

```bash
uv run --extra modal-training modal run \
  -m edge_imci.training.modal_finetune \
  --run-name qwen3-0.6b-lora-v1-YYYYMMDD
```

The local entrypoint creates an `edgeimci_run.json` sidecar before invoking
paid compute and finalizes it on success or failure. Modal stores checkpoints
under the returned run UUID on the `edge-imci-finetune-artifacts` Volume. The
base-model cache persists separately on `edge-imci-hf-cache`.

Retrieve a complete run when needed:

```bash
uv run --extra modal-training modal volume get \
  edge-imci-finetune-artifacts RUN_UUID local-output-directory/
```

For routine handoff, retrieve `metrics.json`, `preflight.json`,
`remote_run_manifest.json`, and the compact `adapter/`; the merged checkpoint
can remain on Modal until conversion or evaluation needs it.

Run an interactive inference against the persisted merged checkpoint:

```bash
uv run --extra modal-training modal run \
  -m edge_imci.inference.modal_structured_extraction \
  --text "The child is 18 months old ..."
```

The inference receipt includes the raw response, strict JSON parse/schema
status, deterministic downstream evaluation, latency, and token throughput.
It defaults to a novel demonstration written outside the campaign corpus and
does not access the TEST partition.

## First run

- Run ID: `4b9c196e-d3f7-4e45-a591-f8bf32932a9b`
- Status: `SUCCEEDED`
- GPU: NVIDIA A10G
- Trainable parameters: 10,092,544 / 606,142,464 (1.665%)
- Training: 234 optimizer steps, three epochs, 677.0 seconds
- Final/best validation loss: 0.0002333
- Peak allocated GPU memory: 9,156,529,664 bytes
- Validation-generation smoke: 8/8 JSON parsed, 8/8 schema valid, 8/8 exact
- Persisted remote artifacts: 55 files, 1,539,179,595 bytes

The smoke result is a pipeline check, not a final model-quality claim. The
full TEST partition remains untouched for the matched structured-extraction
and downstream decision-equivalence evaluation.
