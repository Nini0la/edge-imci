# EdgeIMCI Nigerian English v1.2 canary review

> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `COMPLETE` · No additional remote calls, bulk generation, training, or clinical-use authorization.

The bounded Nigerian English v1.2 validation used the same three matched semantic encounters as the earlier style canaries. The strengthened prompt preserved area-level malaria risk, explicit negatives, UNKNOWN state, and pre/post-bronchodilator findings.

## Outcome

- Remote request starts: **3**
- Retries: **0**
- Generation-time deterministic passes: **2/3**
- Approved corpus candidates after annotation remediation and semantic review: **3/3**
- Reserved exposure: **$0.09** (not billing evidence)
- Recipe decision: `APPROVED_FOR_FURTHER_CONTROLLED_GENERATION`

The respiratory response was generation-time rejected only because three `fact_evidence` values were not exact substrings of its semantically faithful submission. The immutable attempt remains rejected. A separate review artifact corrects only those evidence-span pointers; it does not alter the generated PHC language or clinical meaning.

## Candidate decisions

| Case | Immutable status | Review decision | Notes |
|---|---|---|---|
| `hpg-020-resp-post-bronchodilator-improved` | `DETERMINISTIC_REJECTED` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `EVIDENCE_ANNOTATION_REMEDIATED`, `PRE_POST_INTERVENTION_STATE_PRESERVED`, `PHC_SUITABLE` |
| `hpg-041-fever-high-positive` | `PENDING_HUMAN_REVIEW` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `AREA_LEVEL_MALARIA_RISK_PRESERVED`, `EPISTEMIC_QUALIFIER_PRESERVED`, `PHC_SUITABLE` |
| `hpg-071-incomplete-entry-unknown` | `PENDING_HUMAN_REVIEW` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `UNKNOWN_PRESERVED`, `PHC_SUITABLE` |

## Interpretation

Nigerian English v1.2 is suitable for further controlled, review-gated generation at the current hackathon scope. This is not expert linguistic certification, authorization for bulk generation or training, or production clinical validation.
