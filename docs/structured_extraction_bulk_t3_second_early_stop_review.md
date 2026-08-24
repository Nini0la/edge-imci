# Structured-extraction campaign: second T3 early-stop review

> **Authority:** project-owner delegated execution and semantic review · **Lifecycle:** `IMMUTABLE_CAMPAIGN_REVIEW`  
> **Decision:** remediation complete; exact-slot continuation released  
> **Training:** not authorized by this review

The v6 continuation was stopped after 104 completed attempts. Its 88 deterministic passes and 16 deterministic rejections were preserved as immutable campaign evidence. Review of all 16 rejections found 11 real semantic defects and five conservative annotation/validator outcomes.

The repeatable defects were narrow: loss of the *identified in this assessment* qualifier in one Nigerian Pidgin fever case, weakening of known-negative caregiver ear-discharge history in noisy typed English, and fabrication of an ear-discharge-history statement when that field was absent in telegraphic notes.

The prompts were remediated without changing the frozen semantic sources. A ten-case boundary gate then tested the exact failure boundaries. All ten outputs were semantically faithful. Eight passed the deterministic guards directly; two were manually approved as annotation-only overrides because the prose preserved the facts but used written-out numbers or a combined evidence span.

The released prompt set is recorded in `configs/generation/input_style_qualification_release_v5.json`. The next run must exclude the exact 684 completed campaign slots from v1, v3, v4, v5, and v6. It may schedule only the remaining 1,458 slots. Existing accepted and rejected attempts remain evidence and must not be regenerated or silently rewritten.
