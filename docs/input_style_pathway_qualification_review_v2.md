# EdgeIMCI input-style pathway qualification v2 review

> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `COMPLETE` · Review of 96 immutable Azure GPT-4.1 attempts; no training or production-clinical authorization.

## Outcome

| Style | Approved | Rejected | Annotation overrides | Decision |
|---|---:|---:|---:|---|
| NIGERIAN_ENGLISH | 24/24 | 0 | 2 | QUALIFIED |
| NIGERIAN_PIDGIN | 21/24 | 3 | 4 | REMEDIATE_AND_REQUALIFY |
| NOISY_TYPED_ENGLISH | 21/24 | 3 | 1 | REMEDIATE_AND_REQUALIFY |
| TELEGRAPHIC_PHC_NOTE | 20/24 | 4 | 1 | REMEDIATE_AND_REQUALIFY |

Nigerian English v1.3.1 qualifies. The other three recipes require prompt remediation and a fresh matched-parent qualification; their v2 attempts remain useful immutable evidence but are not released into a bulk contract.

## Semantic rejections

- `NIGERIAN_PIDGIN` / `hpg-028-diarrhoea-some-dehydration` — Diarrhoea-specific eager/thirsty drinking status was omitted.
- `NIGERIAN_PIDGIN` / `hpg-046-fever-no-risk` — Wording for the negative lethargy/unconsciousness finding can mean the child is not conscious.
- `NIGERIAN_PIDGIN` / `hpg-075-contradiction-drinking` — The general known-negative drinking danger sign was inverted and the separate diarrhoea-specific drinking status of UNABLE was not preserved.
- `NOISY_TYPED_ENGLISH` / `hpg-028-diarrhoea-some-dehydration` — Diarrhoea-specific eager/thirsty drinking status was omitted.
- `NOISY_TYPED_ENGLISH` / `hpg-061-ear-no-infection` — Known-negative caregiver ear-discharge history was weakened to absence of a report.
- `NOISY_TYPED_ENGLISH` / `hpg-069-cross-urgent-dehydration-ear` — Known-negative caregiver ear-discharge history was weakened to absence of a report.
- `TELEGRAPHIC_PHC_NOTE` / `hpg-014-resp-chest-hiv-positive` — Known-negative danger sign was rendered as the risky double negative 'not unable'.
- `TELEGRAPHIC_PHC_NOTE` / `hpg-016-resp-oximeter-89-9` — Known-negative danger sign was rendered as the risky double negative 'not unable'.
- `TELEGRAPHIC_PHC_NOTE` / `hpg-031-diarrhoea-severe-age-24-cholera` — Known-negative danger sign was rendered as the risky double negative 'not unable'.
- `TELEGRAPHIC_PHC_NOTE` / `hpg-065-ear-observed-pus-no-history` — Known-negative caregiver ear-discharge history was weakened to absence of a report.

## Annotation-only overrides

These submissions are semantically approved, while their original deterministic terminal status is preserved.

- `NIGERIAN_ENGLISH` / `hpg-027-diarrhoea-no-dehydration` — EVIDENCE_SPAN_MISSING
- `NIGERIAN_ENGLISH` / `hpg-055-fever-severe-measles-cornea` — EVIDENCE_SPAN_MISSING
- `NIGERIAN_PIDGIN` / `hpg-021-resp-post-bronchodilator-fast` — EVIDENCE_SPAN_MISSING
- `NIGERIAN_PIDGIN` / `hpg-027-diarrhoea-no-dehydration` — EVIDENCE_SPAN_MISSING, DIARRHOEA_DRINKING_STATUS_DISTINCTION_LOST
- `NIGERIAN_PIDGIN` / `hpg-055-fever-severe-measles-cornea` — EVIDENCE_SPAN_MISSING
- `NIGERIAN_PIDGIN` / `hpg-068-cross-four-pathways` — EVIDENCE_SPAN_MISSING
- `NOISY_TYPED_ENGLISH` / `hpg-075-contradiction-drinking` — DIARRHOEA_DRINKING_STATUS_DISTINCTION_LOST
- `TELEGRAPHIC_PHC_NOTE` / `hpg-069-cross-urgent-dehydration-ear` — EVIDENCE_SPAN_MISSING
