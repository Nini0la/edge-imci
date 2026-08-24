# Structured-extraction bulk T1 remediation review

> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `REMEDIATION_COMPLETE` · Bulk continuation released; training and production clinical use remain unauthorized.

The original 250-attempt T1 remains immutable. Its review found 14 semantic failures among 63 reviewed attempts, so continuation stopped. Prompt and validator remediation then used three successively narrower target-blind gates: 15 cases, five replacement cases, and three final replacement cases.

| Gate | Attempts | Semantic approved | Semantic rejected | Decision |
|---|---:|---:|---:|---|
| v1 | 15 | 10 | 5 | re-gate five cases |
| v2 | 5 | 2 | 3 | re-gate three cases |
| v3 | 3 | 3 | 0 | release latest prompt lineage |

Every prior failure remains rejected attempt evidence. No candidate was rewritten, and no semantic retry was hidden under the same prompt version. The released prompt set is pinned in `configs/generation/input_style_qualification_release_v2.json`.

The remediation covers unknown-to-negative invention, absence-of-report weakening, drinking/cough/rash polarity, initial-versus-recurrent wheeze, measurements and durations, bacterial-cause epistemic status, parent/nested fact conflation, and derived summaries such as “no dehydration.”

The next bulk package must exclude the exact 250 completed allocation slots—identified by parent, strategy and variant index—not old request hashes, because prompt hashes changed. It must schedule the remaining 1,892 slots only.
