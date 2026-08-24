# Holistic teacher canary — GPT-4.1 `2025-04-14`

This directory contains the immutable, zero-call step-4 package for generation run `holistic-teacher-canary-gpt41-20250414-v1`.

Current state: `VALIDATED_NOT_STARTED`.

- Six frozen semantic cases are selected by `edge-imci-holistic-teacher-canary-selection-v1`.
- Each case is scheduled under the concise and natural prompt strategies.
- The schedule therefore contains exactly 12 requests.
- Azure deployment `gpt-4.1`, model `gpt-4.1`, snapshot `2025-04-14`, temperature `0.7`, and 2,000 maximum output tokens are pinned.
- The execution ceiling is 12 started attempts and USD 1.00.
- The conservative reservation is USD 0.02 per attempt and USD 0.24 in total; it is not billing evidence.
- Provider response storage and SDK automatic retries are disabled.
- Ambiguous provider outcomes require reconciliation.

Canonical JSON files are authoritative; YAML siblings are generated readability mirrors.

No request receipt, provider response, generated candidate, usage record, review record, or charge exists in this directory. Those artifacts may be created only when execution starts in a later explicit step.

When execution is authorized, `python -m edge_imci.generation.holistic_canary_execute`
runs the simple gate, then the complex all-pathway gate, then the remaining units.
Each attempt directory preserves `requested.json` before network I/O and a separate
`terminal.json` after a provider response. `run_state.json` is derived resumable
state; it is not billing evidence. A lone requested receipt blocks automatic retry.
