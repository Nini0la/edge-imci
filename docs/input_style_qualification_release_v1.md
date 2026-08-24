# EdgeIMCI input-style qualification release v1

> **Authority:** `PROJECT_OWNER_DELEGATED_EXECUTION_AND_REVIEW` · **Lifecycle:** `FROZEN_FOR_GUARDED_BULK` · Prompt release only; training and production clinical use remain unauthorized.

| Style | Exact prompt | Semantic result | Qualification method |
|---|---|---:|---|
| NIGERIAN_ENGLISH | `1.3.1` / `ecc08d6cdb55…` | 24/24 | FULL_MATCHED_PARENT_GATE |
| NIGERIAN_PIDGIN | `1.2.1` / `10faa1298477…` | 24/24 | FULL_BASE_GATE_PLUS_TARGETED_PROMPT_DELTA_GATES |
| NOISY_TYPED_ENGLISH | `1.2.1` / `d95f127ddd49…` | 23/24 | TARGETED_GATE_PLUS_DISJOINT_SUPPLEMENT_TO_FULL_24 |
| TELEGRAPHIC_PHC_NOTE | `1.1.0` / `96a5096aa248…` | 24/24 | FULL_MATCHED_PARENT_GATE |

Only candidates that pass deterministic validation and subsequent corpus review may be promoted. Annotation-only overrides above qualify the recipe, not the rejected attempt record itself. All failed, rejected, and transport-failed attempts remain immutable evidence.

The exact prompt paths and full hashes are canonical in `configs/generation/input_style_qualification_release_v1.json`.
