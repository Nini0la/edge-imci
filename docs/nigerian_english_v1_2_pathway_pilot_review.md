# EdgeIMCI Nigerian English v1.2 pathway-pilot review

> **Authority:** PROJECT_OWNER_DELEGATED_REVIEW · **Lifecycle:** COMPLETE · No additional calls, bulk generation, training, or clinical-use authorization.

The 24-parent pilot broadened Nigerian English v1.2 beyond the three matched validation encounters. It covered danger signs, respiratory assessment, diarrhoea/dehydration, fever/malaria/measles, ear assessment, integrated encounters, incomplete states, and contradictory source observations.

## Outcome

- Remote request starts: **24**
- Retries: **0**
- Generation-time deterministic passes: **23/24**
- Approved after strengthened validation and delegated semantic review: **19/24**
- Rejected semantic variants: **5/24**
- Annotation-only remediation: **1/24**
- Reserved exposure: **$0.72** (not billing evidence)
- Token usage: **37,164 input / 20,133 output**
- Recipe decision: REVISE_BEFORE_SCALE

## Newly exposed failures

- Diarrhoea-specific drinking status weakened into general ability to drink: **1**
- Known-negative ear-discharge history weakened into absence of reporting: **4**

These are semantic extraction-label failures, not stylistic preferences. In particular, knowing that a child can drink or breastfeed does not establish whether the child drinks normally, poorly, or eagerly/thirstily.

## Rejected cases

| Case | Stratum | Reason |
|---|---|---|
| hpg-028-diarrhoea-some-dehydration | diarrhoea_plan_b | DIARRHOEA_DRINKING_STATUS_DISTINCTION_LOST |
| hpg-061-ear-no-infection | ear_no_infection | KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT |
| hpg-065-ear-observed-pus-no-history | ear_observed_pus_negative_history | KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT |
| hpg-068-cross-four-pathways | integrated_all_pathways | KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT |
| hpg-069-cross-urgent-dehydration-ear | integrated_urgent_dependency | KNOWN_NEGATIVE_EAR_HISTORY_WEAKENED_TO_NONREPORT |

## Decision

The 19 faithful variants are retained as corpus candidates. The five semantic failures remain immutable rejected-attempt evidence. Nigerian English v1.2 should not be scaled further. Prompt v1.3 is prepared with explicit drinking-status and negative ear-history requirements, but it has not been remotely validated and no further calls are authorized.
