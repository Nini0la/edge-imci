# EdgeIMCI input-language style canary review v1

> **Authority:** `PROJECT_OWNER_DELEGATED_HACKATHON_REVIEW` · **Lifecycle:** `COMPLETE` · This is not expert linguistic certification or authorization for bulk generation/training.

The 12 immutable Azure attempts were incorrectly recorded as `SCHEMA_INVALID` because the candidate schema's closed strategy enumeration still named only the older prompt strategies. No attempt was retried. Raw JSON responses were revalidated under the corrected schema, while the original attempt evidence remained unchanged.

## Outcome

- Approved corpus candidates: **9**
- Rejected candidates: **3**
- Remote request starts: **12**
- Retries: **0**

| Style | Approved | Recipe decision |
|---|---:|---|
| `NIGERIAN_ENGLISH` | 2/3 | `REVISE_BEFORE_SCALE` |
| `NIGERIAN_PIDGIN` | 3/3 | `APPROVED_FOR_FURTHER_CONTROLLED_GENERATION` |
| `NOISY_TYPED_ENGLISH` | 1/3 | `REVISE_BEFORE_SCALE` |
| `TELEGRAPHIC_PHC_NOTE` | 3/3 | `APPROVED_FOR_FURTHER_CONTROLLED_GENERATION` |

## Candidate decisions

| Style | Case | Decision | Reason codes |
|---|---|---|---|
| `NIGERIAN_ENGLISH` | `hpg-020-resp-post-bronchodilator-improved` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `PHC_SUITABLE` |
| `NIGERIAN_ENGLISH` | `hpg-041-fever-high-positive` | `REJECTED` | `NEGATIVE_EVIDENCE_WEAKENED_OR_DOUBLE_NEGATED` |
| `NIGERIAN_ENGLISH` | `hpg-071-incomplete-entry-unknown` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `UNKNOWN_PRESERVED`, `PHC_SUITABLE` |
| `NIGERIAN_PIDGIN` | `hpg-020-resp-post-bronchodilator-improved` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `PHC_SUITABLE`, `HACKATHON_PIDGIN_REVIEW_PASSED` |
| `NIGERIAN_PIDGIN` | `hpg-041-fever-high-positive` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `PHC_SUITABLE`, `HACKATHON_PIDGIN_REVIEW_PASSED`, `EVIDENCE_SPAN_ANNOTATION_REPAIRED` |
| `NIGERIAN_PIDGIN` | `hpg-071-incomplete-entry-unknown` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `UNKNOWN_PRESERVED`, `PHC_SUITABLE`, `HACKATHON_PIDGIN_REVIEW_PASSED` |
| `NOISY_TYPED_ENGLISH` | `hpg-020-resp-post-bronchodilator-improved` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `PHC_SUITABLE` |
| `NOISY_TYPED_ENGLISH` | `hpg-041-fever-high-positive` | `REJECTED` | `NEGATIVE_EVIDENCE_WEAKENED_OR_DOUBLE_NEGATED` |
| `NOISY_TYPED_ENGLISH` | `hpg-071-incomplete-entry-unknown` | `REJECTED` | `NEGATIVE_EVIDENCE_WEAKENED_OR_DOUBLE_NEGATED` |
| `TELEGRAPHIC_PHC_NOTE` | `hpg-020-resp-post-bronchodilator-improved` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `PHC_SUITABLE` |
| `TELEGRAPHIC_PHC_NOTE` | `hpg-041-fever-high-positive` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `PHC_SUITABLE` |
| `TELEGRAPHIC_PHC_NOTE` | `hpg-071-incomplete-entry-unknown` | `APPROVED_CORPUS_CANDIDATE` | `SEMANTICALLY_FAITHFUL`, `UNKNOWN_PRESERVED`, `PHC_SUITABLE` |

## Interpretation

Nigerian Pidgin and telegraphic PHC-note recipes passed all three matched semantic probes and may proceed to further controlled generation. The Pidgin decision is a project-level hackathon suitability review, not broad sociolinguistic certification.

Nigerian English and noisy typed English require prompt remediation before scale. The rejected phrasing weakened a known negative into absence of a report or represented it with a double negative; either could train UNKNOWN/negative confusion.

All approved language variants are paired with deterministic model-facing JSON targets. Their frozen downstream assistant responses remain preserved in language records but are absent from extraction SFT records and messages.
