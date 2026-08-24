# ASUS structured-extraction smoke fixture v1

This frozen fixture provides a quick, realistic check of whether an exact model-runtime combination can perform the EdgeIMCI learned task:

```text
free-form PHC findings -> model-facing encounter JSON
```

It tests application behavior and time to valid structured state. It does **not** replace the official ADTC neutral benchmark, a representative held-out qualification suite, sustained-load testing, or the predeclared admission thresholds in [`docs/target_device_model_runtime_qualification_plan.md`](../../../docs/target_device_model_runtime_qualification_plan.md).

## Contents

- [`prompt.md`](prompt.md): human-readable prompt and expected result.
- [`system_prompt.txt`](system_prompt.txt): exact system-message bytes.
- [`user_prompt.txt`](user_prompt.txt): exact user-message bytes.
- [`expected_target.json`](expected_target.json): canonical gold target.
- [`run_config.json`](run_config.json): matched sampling and evidence requirements.
- [`fixture_manifest.json`](fixture_manifest.json): identities and SHA-256 pins.
- [`score_output.py`](score_output.py): deterministic response scorer.

## Scope and provenance

- Source semantic case: `hpg-017-resp-oximeter-90`.
- Source approved language example: `extract__hpg-017-resp-oximeter-90__phc-nigerian-english-v1__v0004`.
- Parent partition: `TRAIN`.
- Target schema: `edge-imci-model-facing-encounter-v1`.
- Purpose: `APPLICATION_TASK_SMOKE_ONLY`.

Because this is a TRAIN-parent example, use it to verify installation, prompting, output format and rough speed. Do not cite it as held-out evidence that a candidate has passed ASUS admission.

## Matched run procedure

1. Pin and record the exact model, artifact, tokenizer/chat template, runtime and configuration.
2. Start from the same declared cold or warm condition for every candidate.
3. Disable Qwen thinking mode through the runtime's documented chat-template mechanism; do not append model-specific wording to only one candidate's prompt.
4. Use the exact messages and settings in this directory.
5. Save the response bytes without stripping Markdown or extracting a JSON substring.
6. Capture all timing, token-count and memory fields listed in `run_config.json`.
7. Score the unmodified response.

Example:

```bash
uv run python \
  experiments/qualification/asus-structured-extraction-smoke-v1/score_output.py \
  /path/to/raw-model-output.txt
```

Exit status `0` means exact structured match and downstream decision equivalence. Status `1` means parseable but non-exact or decision-divergent output. Status `2` means the raw response is not exactly one valid JSON object.

## Interpretation

Record both quality and runtime behavior:

- first-attempt parse and schema validity;
- exact structured match and field-level metrics;
- UNKNOWN, measurement, duration and qualifier preservation;
- deterministic decision and urgent-action equivalence;
- prompt-processing and generation tokens per second;
- time to first token and total time to valid result;
- cold-start time, RSS and whole-system memory; and
- the unmodified raw output, including failures.

One successful response proves only that the runtime is wired correctly and can solve this case. Formal candidate admission requires the frozen representative held-out workload and thresholds described in the qualification plan.
