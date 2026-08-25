# Registry-driven experiment matrix v1

> **Authority:** `IMPLEMENTED_PIPELINE` · **Lifecycle:** `CURRENT` · This controls research execution planning, not clinical or deployment authorization.

The experiment registry remains the authority for *what* may be investigated.
The matrix compiler is the deterministic planning layer for *which controlled
runs* implement one registered training experiment. Compilation does not launch
compute, mutate the registry, or authorize use of the held-out TEST partition.

## First calibration matrix

`configs/training/qwen3_0_6b_sft_calibration_matrix_v1.json` expands the pinned
Qwen3-0.6B LoRA recipe across:

- epochs: 1, 2, 3, and 5;
- learning rates: 1e-4, 2e-4, and 3e-4;
- seeds: 3407 and 20260824.

This produces 24 cells. The completed 3-epoch, 2e-4, seed-3407 run is reused,
leaving 23 prospective runs. Estimates use the observed first-run GPU duration,
separate fixed/training time, and a 15% contingency. They are resource estimates,
not provider billing claims.

Compile the plan locally:

```bash
uv run edgeimci-experiments compile-matrix \
  configs/training/qwen3_0_6b_sft_calibration_matrix_v1.json \
  --output experiments/training/matrices/qwen3-0.6b-sft-calibration-v1.plan.json
```

The compiler fails closed on unknown override paths, unregistered reused runs,
budget overruns, unpinned base models, missing gate evidence, and any matrix that
does not explicitly prohibit TEST use.

Materialize the 23 prospective cell configs without launching them:

```bash
uv run edgeimci-experiments materialize-matrix \
  experiments/training/matrices/qwen3-0.6b-sft-calibration-v1.plan.json \
  --output-dir experiments/training/matrices/qwen3-0.6b-sft-calibration-v1/configs
```

The Modal runner accepts any of these repository-contained, preflighted configs
through `--config-path`. The run name should be the compiled `cell_id`, preserving
the plan-to-run association in the tracked command and config snapshot.

## Launch boundary

Every new cell is launch-authorized under the capped automatic-evidence policy
in `qwen3_0_6b_sft_calibration_authorization_v1.json`. The matched evaluator is pinned by
`configs/evaluation/structured_extraction_checkpoint_policy_v1.json`; it scores
all 115 VALIDATION examples globally and by language style, with hard safety
gates for structured output, urgent actions, and referral behavior. Routine
Codex review of examples and datasets is disabled: execution emits machine-readable
receipts and aggregate comparisons only. TEST remains untouched during selection;
it is reserved for the final promoted candidate.

## Completed execution

The authorized sweep completed all 23 prospective cells; together with the
reused baseline, all 24 matrix cells now have matched 115-example VALIDATION
evidence. Eight cells passed every automatic promotion gate. The deterministic
leaderboard selected cell `qwen3-0.6b-sft-calibration-v1--016--dde3f482d8`
(run `251039a3-4adc-4e74-8c30-069eb8aca6de`): 3 epochs, learning rate 2e-4,
and seed 20260824. Its six pinned aggregate ranking metrics are all 1.0.

This is a validation-stage selection, not a clinical, TEST, or deployment
authorization. Three failed canary attempts are retained as infrastructure
evidence; the fail-closed launcher prevented fan-out until the canary passed.
No individual example or generated response was used for routine Codex review.
