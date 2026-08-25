# Qwen3-0.6B base-control methodology correction v1

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT_CORRECTION` · This corrects interpretation of historical evidence; any TEST reuse requires a separate explicit authorization.

## Finding

The closed `edge-imci-qwen3-0.6b-reserved-test-v1` run did not provide the
untuned Qwen3-0.6B control with the EdgeIMCI model-facing encounter JSON Schema
or an example output. All candidates received the dataset's short system
instruction, which names the project-specific schema but does not define it.
The selected fine-tuned model had already seen 1,239 TRAIN demonstrations of
that exact contract.

The base control's 0% JSON parse and schema-valid rates therefore do not measure
its extraction capability under a schema-informed prompt. The closed run still
supports the selected checkpoint's absolute TEST metrics, but its paired
selected-versus-base differences must not be presented as an unbiased estimate
of the benefit caused by fine-tuning.

## Corrected Treatment

A new comparison must be separately versioned and preregistered. Its untuned
`BASE_CONTROL` candidate must use `SCHEMA_INFORMED_BASE_CONTROL_V1`, which puts
the complete pinned JSON Schema and a pinned, schema-valid non-TEST example
output in the system prompt. Fine-tuned candidates retain the original dataset
system instruction so their inference treatment remains aligned with training.

The policy must set `generation.identical_for_all_candidates` to `false` and
pin the schema, example-output, and assembled-prompt SHA-256 values. The runner
rejects any policy that applies this treatment to a fine-tuned candidate or
whose prompt evidence differs from the preregistered hashes.

The old TEST authorization remains permanently closed. The project owner has
separately authorized exactly one post-hoc schema-informed base-control use in
[`qwen3_0_6b_posthoc_schema_informed_base_control_v1.json`](../configs/evaluation/qwen3_0_6b_posthoc_schema_informed_base_control_v1.json).
That authorization does not alter the historical policy or report, rerun a
fine-tuned candidate, or make the already observed TEST partition untouched
again. Its result must remain labelled post hoc and cannot establish a new
TEST pass/fail claim.

## Authorized Post-Hoc Outcome

The one authorized use completed on 2026-08-24 and is closed with
`use_count=1`. The schema-informed base control received the complete pinned
JSON Schema and pinned valid example output, but still produced 0% JSON parse,
schema-valid, exact-match, and decision-equivalence rates on all 143 records.
The preserved selected fine-tune remained at 97.20% exact-match and decision
equivalence, 99.89% field accuracy, and 100% JSON parse and schema-valid rates.

This post-hoc diagnostic directly addresses the identified prompt-treatment
defect and did not improve the base result. It strengthens the evidence that
the untuned 0.6B model did not perform this contract under the tested
schema-informed prompt, but it remains post hoc and is not a replacement for a
new untouched held-out comparison.

Aggregate-only report:
[`aggregate_report.json`](../experiments/evaluation/qwen3-0.6b-posthoc-base-control-v1/aggregate_report.json)
(`report_sha256=59c6a839fb73bf42a5d50975ced347af8d6c0d96f55dfbe2d0ea7e9267dae8a6`).
