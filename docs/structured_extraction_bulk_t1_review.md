# Structured-extraction bulk T1 review

> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `REMEDIATION_REQUIRED` · Combined review of 250 immutable attempts; T2, training and production clinical use are not released.

T1 produced 227 raw deterministic passes and 23 raw rejections. Review covered every rejection plus 10 deterministic passes per style (63 unique attempts total). Fourteen reviewed attempts contained semantic defects; 12 raw rejections were annotation-only overrides.

| Style | Attempts | Raw pass | Reviewed | Semantic defects | Annotation overrides |
|---|---:|---:|---:|---:|---:|
| phc-nigerian-english-v1 | 62 | 55 | 17 | 3 | 5 |
| phc-nigerian-pidgin-v1 | 63 | 58 | 15 | 4 | 2 |
| phc-noisy-typed-english-v1 | 63 | 59 | 14 | 3 | 1 |
| phc-telegraphic-note-v1 | 62 | 55 | 17 | 4 | 4 |

## Decision

T2 is blocked. Prompt and deterministic-polarity remediation must pass a targeted gate before a new exact-slot continuation can be prepared. The 250 T1 attempts remain immutable and will not be regenerated.

## Blocking findings

- Positive cough/difficult-breathing polarity reversal escaped deterministic validation.
- Unable-to-drink polarity reversal escaped deterministic validation.
- Initial wheezing was lost into a recurrent-wheeze negative.
- Null nested ear/fever facts were invented systematically in affected styles.
- Complex cases showed fact omission and one rash polarity reversal.
