# EdgeIMCI input-language style remediation review v1

> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `COMPLETE` · No additional remote calls, bulk generation, training, or clinical-use authorization.

Six GPT-4.1 v1.1 remediation attempts retested Nigerian English and noisy typed English over the same three matched encounters. All six passed the original deterministic gate; delegated semantic review approved five and rejected one newly identified malaria-risk context shift.

## Run outcome

- Remote request starts: **6**
- Retries: **0**
- Deterministic passes at generation time: **6/6**
- Approved corpus candidates after semantic review: **5/6**
- Reserved exposure: **$0.18** (not billing evidence)

| Recipe | Approved | Decision |
|---|---:|---|
| Nigerian English v1.1 | 2/3 | `REVISE_BEFORE_SCALE` |
| Noisy typed English v1.1 | 3/3 | `APPROVED_FOR_FURTHER_CONTROLLED_GENERATION` |

## Candidate decisions

| Style | Case | Decision | Reason |
|---|---|---|---|
| `NIGERIAN_ENGLISH` | `hpg-020-resp-post-bronchodilator-improved` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `KNOWN_NEGATIVE_REMEDIATION_PASSED`, `PHC_SUITABLE` |
| `NIGERIAN_ENGLISH` | `hpg-041-fever-high-positive` | `REJECTED` | `MALARIA_RISK_CONTEXT_SHIFT` |
| `NIGERIAN_ENGLISH` | `hpg-071-incomplete-entry-unknown` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `KNOWN_NEGATIVE_REMEDIATION_PASSED`, `UNKNOWN_PRESERVED`, `PHC_SUITABLE` |
| `NOISY_TYPED_ENGLISH` | `hpg-020-resp-post-bronchodilator-improved` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `DIRECT_NEGATION_PRESERVED`, `PHC_SUITABLE` |
| `NOISY_TYPED_ENGLISH` | `hpg-041-fever-high-positive` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `DIRECT_NEGATION_PRESERVED`, `EPISTEMIC_QUALIFIER_PRESERVED`, `PHC_SUITABLE` |
| `NOISY_TYPED_ENGLISH` | `hpg-071-incomplete-entry-unknown` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `DIRECT_NEGATION_PRESERVED`, `UNKNOWN_PRESERVED`, `PHC_SUITABLE` |

## Interpretation

The original known-negative defect is resolved in every v1.1 output: none uses absence-of-report wording or a double negative for ability to drink or breastfeed.

Noisy typed English v1.1 is approved for further controlled generation. Nigerian English v1.1 remains unapproved because the fever example recast the area's malaria-risk category as the child's individual risk. The new deterministic `MALARIA_RISK_CONTEXT_SHIFT` guard captures this failure.

Nigerian English v1.2 is prepared with explicit area/setting wording but has not been remotely validated. It must pass a separately authorized bounded gate before scale.
