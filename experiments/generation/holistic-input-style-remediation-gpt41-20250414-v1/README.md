# EdgeIMCI input-language style remediation canary

> **Authority:** `PROJECT_OWNER_AUTHORIZED_CANARY` · **Lifecycle:** `EXECUTED_AND_REVIEWED`

Six target-blind GPT-4.1 attempts retested Nigerian English and noisy typed English v1.1 over the same three matched encounters. All six unique requests completed with zero retries; all passed the generation-time deterministic gate. Delegated semantic review approved five and rejected the Nigerian-English fever sample for `MALARIA_RISK_CONTEXT_SHIFT`.

Noisy typed English v1.1 is approved for further controlled generation. Nigerian English v1.1 remains `REVISE_BEFORE_SCALE`; v1.2 is prepared locally but unvalidated. See `docs/input_language_style_remediation_review_v1.md` and `data/canary/input_language_style_remediation_v1/`.

The conservative reservation is $0.18 and is not billing evidence. Additional remote calls, bulk generation, training, and production clinical use remain unauthorized.
