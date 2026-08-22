# Product-level holistic golden semantic suite v1 — review package

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Generated review surface for the approved and frozen hackathon semantic suite.

**Status:** `FROZEN` — human/domain approved for the bounded hackathon scope; eligible for golden-language work, teacher bake-off, and product evaluation, but not training data.

**Cases:** 78. **Corpus role:** `HOLISTIC_PRODUCT_GOLDEN`.

**Pinned substrate:** `imci-major-sick-child-v1` / `imci-major-sick-child-holistic-completeness-v2` / `imci-major-sick-child-review-decisions-v1` / `imci-major-sick-child-oxygen-referral-disposition-v1` / `edge-imci-holistic-golden-scope-dispositions-v1` / `edge-imci-holistic-deterministic-oracle-v3`.

Every evaluable record is deterministically recomputed. Approval is pinned by `edge-imci-holistic-product-golden-approval-v1`; production clinical use remains unauthorized.

## Resolved product-scope disposition

- `HPG-GAP-REASSESS-001` — `RESOLVED_BY_PRODUCT_SCOPE`: Separate longitudinal Plan B/Plan C treatment-stage execution is outside holistic golden v1. The initial holistic semantic answer must include the source-backed dehydration classification, Plan B or Plan C, and the timed-reassessment instruction. A later full updated assessment may be submitted and evaluated afresh; EdgeIMCI v1 does not maintain treatment state, infer reassessment findings, or automatically repeat a rehydration plan.

## Case index

| Case | Expected state | Urgent | Final classifications | Coverage | Review decisions |
|---|---|---:|---|---|---|
| `hpg-001-all-negative` | COMPLETE | no | none | complete, low_severity, explicit_negative | MSC-CQ-SCOPE-001 |
| `hpg-002-danger-unable-to-drink-or-breastfeed` | COMPLETE | yes | VERY_SEVERE_DISEASE | complete, danger_sign, urgent | IP-CQ-001 |
| `hpg-003-danger-vomits-everything` | COMPLETE | yes | VERY_SEVERE_DISEASE | complete, danger_sign, urgent | IP-CQ-001 |
| `hpg-004-danger-had-convulsions` | COMPLETE | yes | VERY_SEVERE_DISEASE | complete, danger_sign, urgent | IP-CQ-001 |
| `hpg-005-danger-lethargic-or-unconscious` | COMPLETE | yes | VERY_SEVERE_DISEASE | complete, danger_sign, urgent | IP-CQ-001 |
| `hpg-006-danger-convulsing-now` | COMPLETE | yes | VERY_SEVERE_DISEASE | complete, danger_sign, urgent | IP-CQ-001 |
| `hpg-007-resp-age-2-rate-49` | COMPLETE | no | COUGH_OR_COLD | complete, respiratory, respiratory_boundary, age_2, rate_49 | IP-CQ-003 |
| `hpg-008-resp-age-2-rate-50` | COMPLETE | no | PNEUMONIA | complete, respiratory, respiratory_boundary, age_2, rate_50 | IP-CQ-003 |
| `hpg-009-resp-age-11-rate-50` | COMPLETE | no | PNEUMONIA | complete, respiratory, respiratory_boundary, age_11 | IP-CQ-003 |
| `hpg-010-resp-age-12-rate-39` | COMPLETE | no | COUGH_OR_COLD | complete, respiratory, respiratory_boundary, age_12, rate_39 | IP-CQ-003 |
| `hpg-011-resp-age-12-rate-40` | COMPLETE | no | PNEUMONIA | complete, respiratory, respiratory_boundary, age_12, rate_40 | IP-CQ-003 |
| `hpg-012-resp-age-59-rate-40` | COMPLETE | no | PNEUMONIA | complete, respiratory, respiratory_boundary, age_59 | IP-CQ-003 |
| `hpg-013-resp-chest-hiv-negative` | COMPLETE | no | PNEUMONIA | complete, respiratory, chest_indrawing, hiv_modifier_negative | IP-CQ-003 |
| `hpg-014-resp-chest-hiv-positive` | COMPLETE | no | PNEUMONIA | complete, respiratory, chest_indrawing, hiv_modifier_positive, referral | IP-CQ-003, MSC-CQ-RESP-002 |
| `hpg-015-resp-stridor` | COMPLETE | yes | SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE | complete, respiratory, severe_respiratory, urgent | IP-CQ-003 |
| `hpg-016-resp-oximeter-89-9` | COMPLETE | no | COUGH_OR_COLD | complete, respiratory, oxygen_boundary, urgent | IP-CQ-003 |
| `hpg-017-resp-oximeter-90` | COMPLETE | no | COUGH_OR_COLD | complete, respiratory, oxygen_boundary | IP-CQ-003 |
| `hpg-018-resp-prolonged-cough` | COMPLETE | no | COUGH_OR_COLD | complete, respiratory, prolonged_cough, referral | IP-CQ-003 |
| `hpg-019-resp-recurrent-wheeze` | COMPLETE | no | COUGH_OR_COLD | complete, respiratory, recurrent_wheeze, home_bronchodilator | IP-CQ-003 |
| `hpg-020-resp-post-bronchodilator-improved` | COMPLETE | no | COUGH_OR_COLD | complete, respiratory, bronchodilator_reassessment, complete_post_reassessment, improved | IP-CQ-003, MSC-CQ-RESP-001 |
| `hpg-021-resp-post-bronchodilator-fast` | COMPLETE | no | PNEUMONIA | complete, respiratory, bronchodilator_reassessment, complete_post_reassessment, persistent_fast_breathing | IP-CQ-003, MSC-CQ-RESP-001 |
| `hpg-022-resp-trial-outstanding` | INCOMPLETE | no | withheld | incomplete, respiratory, bronchodilator_reassessment | IP-CQ-003, MSC-CQ-RESP-001 |
| `hpg-023-resp-child-not-calm` | INCOMPLETE | no | withheld | incomplete, respiratory, invalid_evidence, contradiction | IP-CQ-003 |
| `hpg-024-resp-count-not-one-minute` | INCOMPLETE | no | withheld | incomplete, respiratory, invalid_evidence, contradiction | IP-CQ-003 |
| `hpg-025-resp-oximeter-missing-value` | INCOMPLETE | no | withheld | incomplete, respiratory, single_omission, measurement_missing | IP-CQ-003 |
| `hpg-026-resp-chest-hiv-unknown` | INCOMPLETE | no | withheld | incomplete, respiratory, single_omission, hiv_modifier_unknown | IP-CQ-003 |
| `hpg-027-diarrhoea-no-dehydration` | COMPLETE | no | NO_DEHYDRATION | complete, diarrhoea, no_dehydration | — |
| `hpg-028-diarrhoea-some-dehydration` | COMPLETE | no | SOME_DEHYDRATION | complete, diarrhoea, some_dehydration, plan_b, initial_treatment_stage | MSC-CQ-REASSESS-001 |
| `hpg-029-diarrhoea-severe-plan-c-under-24m` | COMPLETE | no | SEVERE_DEHYDRATION | complete, diarrhoea, severe_dehydration, plan_c, initial_treatment_stage | MSC-CQ-REASSESS-001 |
| `hpg-030-diarrhoea-severe-age-24-no-cholera` | COMPLETE | no | SEVERE_DEHYDRATION | complete, diarrhoea, severe_dehydration, cholera_context, age_boundary | MSC-CQ-DIARRHOEA-001, MSC-CQ-REASSESS-001 |
| `hpg-031-diarrhoea-severe-age-24-cholera` | COMPLETE | no | SEVERE_DEHYDRATION | complete, diarrhoea, severe_dehydration, cholera_action, local_protocol_generic | MSC-CQ-DIARRHOEA-001, MSC-CQ-REASSESS-001 |
| `hpg-032-diarrhoea-duration-13` | COMPLETE | no | NO_DEHYDRATION | complete, diarrhoea, duration_boundary, not_persistent | — |
| `hpg-033-diarrhoea-duration-14-persistent` | COMPLETE | no | NO_DEHYDRATION, PERSISTENT_DIARRHOEA | complete, diarrhoea, duration_boundary, persistent_diarrhoea | — |
| `hpg-034-diarrhoea-severe-persistent` | COMPLETE | yes | SOME_DEHYDRATION, SEVERE_PERSISTENT_DIARRHOEA | complete, diarrhoea, severe_persistent_diarrhoea, urgent | IP-CQ-004, MSC-CQ-REASSESS-001 |
| `hpg-035-diarrhoea-dysentery` | COMPLETE | no | NO_DEHYDRATION, DYSENTERY | complete, diarrhoea, dysentery | — |
| `hpg-036-diarrhoea-persistent-and-dysentery` | COMPLETE | no | NO_DEHYDRATION, PERSISTENT_DIARRHOEA, DYSENTERY | complete, diarrhoea, simultaneous_classifications, persistent_diarrhoea, dysentery | — |
| `hpg-037-diarrhoea-positive-drinking-reuse` | COMPLETE | yes | VERY_SEVERE_DISEASE, SEVERE_DEHYDRATION | complete, diarrhoea, cross_evidence_reuse, urgent | IP-CQ-001, IP-CQ-002 |
| `hpg-038-diarrhoea-negative-does-not-reuse` | INCOMPLETE | no | withheld | incomplete, diarrhoea, explicit_negative_omission_twin, single_omission | IP-CQ-002 |
| `hpg-039-diarrhoea-duration-unknown` | INCOMPLETE | no | withheld | incomplete, diarrhoea, single_omission | — |
| `hpg-040-diarrhoea-cholera-context-unknown` | INCOMPLETE | no | withheld | incomplete, diarrhoea, conditional_omission, cholera_context | MSC-CQ-DIARRHOEA-001, MSC-CQ-REASSESS-001 |
| `hpg-041-fever-high-positive` | COMPLETE | no | MALARIA | complete, fever, malaria, high_risk, test_positive | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-042-fever-high-negative` | COMPLETE | no | FEVER_NO_MALARIA | complete, fever, fever_no_malaria, high_risk, test_negative | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-043-fever-high-test-unavailable` | COMPLETE | no | MALARIA | complete, fever, malaria, test_unavailable | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-044-fever-low-obvious-cause` | COMPLETE | no | FEVER_NO_MALARIA | complete, fever, fever_no_malaria, low_risk, obvious_cause | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-045-fever-low-no-cause-positive` | COMPLETE | no | MALARIA | complete, fever, malaria, low_risk, test_positive | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-046-fever-no-risk` | COMPLETE | no | FEVER | complete, fever, no_malaria_risk | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-047-fever-temperature-38-4` | COMPLETE | no | FEVER_NO_MALARIA | complete, fever, temperature_boundary, no_high_fever_action | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-048-fever-temperature-38-5` | COMPLETE | no | FEVER_NO_MALARIA | complete, fever, temperature_boundary, high_fever_action | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-049-fever-duration-7` | COMPLETE | no | FEVER_NO_MALARIA | complete, fever, duration_boundary, not_prolonged | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-050-fever-duration-8-not-every-day` | COMPLETE | no | FEVER_NO_MALARIA | complete, fever, duration_boundary, not_prolonged | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-051-fever-duration-8-every-day` | COMPLETE | no | FEVER_NO_MALARIA | complete, fever, prolonged_fever, referral | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-052-fever-identified-bacterial-cause` | COMPLETE | no | FEVER_NO_MALARIA | complete, fever, generic_antibiotic_action, identified_bacterial_cause | MSC-CQ-FEVER-001, MSC-CQ-FEVER-002, MSC-CQ-FEVER-003 |
| `hpg-053-fever-measles` | COMPLETE | no | FEVER_NO_MALARIA, MEASLES | complete, fever, measles | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-054-fever-measles-eye` | COMPLETE | no | FEVER_NO_MALARIA, MEASLES_WITH_EYE_OR_MOUTH_COMPLICATIONS | complete, fever, measles_eye_or_mouth_complications | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-055-fever-severe-measles-cornea` | COMPLETE | yes | FEVER_NO_MALARIA, SEVERE_COMPLICATED_MEASLES | complete, fever, severe_complicated_measles, urgent | IP-CQ-004, MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-056-fever-severe-stiff-neck` | COMPLETE | yes | VERY_SEVERE_FEBRILE_DISEASE | complete, fever, very_severe_febrile_disease, urgent | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-057-fever-malaria-and-measles` | COMPLETE | no | MALARIA, MEASLES | complete, fever, simultaneous_classifications, malaria, measles | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-058-fever-measles-last-three-months` | COMPLETE | no | FEVER_NO_MALARIA, MEASLES | complete, fever, measles_history, measles | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-059-fever-malaria-risk-unknown` | INCOMPLETE | no | withheld | incomplete, fever, case_context_missing, single_omission | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-060-fever-test-result-unknown` | INCOMPLETE | no | withheld | incomplete, fever, single_omission, test_result_missing | MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-061-ear-no-infection` | COMPLETE | no | NO_EAR_INFECTION | complete, ear_problem, no_ear_infection | — |
| `hpg-062-ear-acute-pain` | COMPLETE | no | ACUTE_EAR_INFECTION | complete, ear_problem, acute_ear_infection, ear_pain | — |
| `hpg-063-ear-acute-discharge-13` | COMPLETE | no | ACUTE_EAR_INFECTION | complete, ear_problem, acute_ear_infection, duration_boundary | — |
| `hpg-064-ear-chronic-discharge-14` | COMPLETE | no | CHRONIC_EAR_INFECTION | complete, ear_problem, chronic_ear_infection, duration_boundary | — |
| `hpg-065-ear-observed-pus-no-history` | COMPLETE | no | ACUTE_EAR_INFECTION | complete, ear_problem, acute_ear_infection, observed_pus, negative_history | MSC-CQ-EAR-001 |
| `hpg-066-ear-mastoiditis` | COMPLETE | yes | MASTOIDITIS | complete, ear_problem, mastoiditis, urgent | — |
| `hpg-067-ear-duration-unknown` | INCOMPLETE | no | withheld | incomplete, ear_problem, single_omission | — |
| `hpg-068-cross-four-pathways` | COMPLETE | no | PNEUMONIA, NO_DEHYDRATION, DYSENTERY, MALARIA, MEASLES, ACUTE_EAR_INFECTION | complete, whole_encounter, simultaneous_classifications, integrated_action_plan, all_pathways | IP-CQ-003, MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-069-cross-urgent-dehydration-ear` | COMPLETE | yes | SEVERE_DEHYDRATION, MASTOIDITIS | complete, cross_pathway_action_dependency, urgent, deferred_routine_actions | IP-CQ-004 |
| `hpg-070-cross-multiple-urgent` | COMPLETE | yes | VERY_SEVERE_DISEASE, SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE, VERY_SEVERE_FEBRILE_DISEASE, MASTOIDITIS | complete, multiple_urgent, action_deduplication, integrated_action_plan | IP-CQ-001, IP-CQ-003, IP-CQ-004, MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-071-incomplete-entry-unknown` | INCOMPLETE | no | withheld | incomplete, explicit_negative_omission_twin, single_omission, grouped_missing_elements | MSC-CQ-SCOPE-001 |
| `hpg-072-incomplete-multiple-groups` | INCOMPLETE | no | withheld | incomplete, multiple_omissions, grouped_missing_elements | IP-CQ-003, MSC-CQ-SCOPE-001, MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-073-incomplete-known-urgent` | INCOMPLETE | yes | withheld | incomplete, urgent_incomplete, withhold_final_synthesis, grouped_missing_elements | IP-CQ-001, MSC-CQ-SCOPE-001 |
| `hpg-074-incomplete-internal-classification-withheld` | INCOMPLETE | no | withheld | incomplete, internal_classification, withhold_final_synthesis | IP-CQ-003, MSC-CQ-SCOPE-001 |
| `hpg-075-contradiction-drinking` | INCOMPLETE | no | withheld | incomplete, contradiction, cross_evidence | IP-CQ-002 |
| `hpg-076-complete-danger-plus-all-pathways` | COMPLETE | yes | VERY_SEVERE_DISEASE, SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE, NO_DEHYDRATION, VERY_SEVERE_FEBRILE_DISEASE, NO_EAR_INFECTION | complete, urgent, all_pathways, deferred_routine_actions, holistic_assessment_after_danger | IP-CQ-001, IP-CQ-003, IP-CQ-004, MSC-CQ-FEVER-001, MSC-CQ-FEVER-003 |
| `hpg-077-out-of-scope-age-1` | SCHEMA_REJECTION | — | — | out_of_scope, schema_rejection, age_boundary | MSC-CQ-SCOPE-001 |
| `hpg-078-out-of-scope-age-60` | SCHEMA_REJECTION | — | — | out_of_scope, schema_rejection, age_boundary | MSC-CQ-SCOPE-001 |

## Detailed case review

### hpg-001-all-negative

**Why:** Complete low-severity encounter with every pathway explicitly absent.

**Coverage:** `complete`, `low_severity`, `explicit_negative`

**Applicable approved decisions:** `MSC-CQ-SCOPE-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "always_required + unknown_semantics",
    "details": [
      "All always-required observations are supplied explicitly; negative pathway-entry findings make those pathways not applicable."
    ],
    "fields": [
      "patient_facts.age_months",
      "danger_signs.unable_to_drink_or_breastfeed",
      "danger_signs.vomits_everything",
      "danger_signs.had_convulsions",
      "danger_signs.lethargic_or_unconscious",
      "danger_signs.convulsing_now",
      "patient_facts.has_cough_or_difficult_breathing",
      "patient_facts.has_diarrhoea",
      "patient_facts.has_fever",
      "patient_facts.has_ear_problem"
    ],
    "provenance_id": "HC-EXPLICIT-NEGATIVE-PATHWAY-EXCLUSION",
    "provenance_type": "COMPLETENESS_REQUIREMENT"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-001-all-negative",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** none

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** none

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-002-danger-unable-to-drink-or-breastfeed

**Why:** Complete encounter with unable_to_drink_or_breastfeed as the known general danger sign.

**Coverage:** `complete`, `danger_sign`, `urgent`

**Applicable approved decisions:** `IP-CQ-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": true,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-002-danger-unable-to-drink-or-breastfeed",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`

**Final classifications:** `VERY_SEVERE_DISEASE`

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-UNABLE-TO-DRINK`

**Source provenance:**

- `IMCI-MSC-GDS-UNABLE-TO-DRINK` — General danger signs; PDF page 5; printed page 1 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-003-danger-vomits-everything

**Why:** Complete encounter with vomits_everything as the known general danger sign.

**Coverage:** `complete`, `danger_sign`, `urgent`

**Applicable approved decisions:** `IP-CQ-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": true
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-003-danger-vomits-everything",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`

**Final classifications:** `VERY_SEVERE_DISEASE`

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-VOMITS-EVERYTHING`

**Source provenance:**

- `IMCI-MSC-GDS-VOMITS-EVERYTHING` — General danger signs; PDF page 5; printed page 1 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-004-danger-had-convulsions

**Why:** Complete encounter with had_convulsions as the known general danger sign.

**Coverage:** `complete`, `danger_sign`, `urgent`

**Applicable approved decisions:** `IP-CQ-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": true,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-004-danger-had-convulsions",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`

**Final classifications:** `VERY_SEVERE_DISEASE`

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-CONVULSIONS-HISTORY`

**Source provenance:**

- `IMCI-MSC-GDS-CONVULSIONS-HISTORY` — General danger signs; PDF page 5; printed page 1 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-005-danger-lethargic-or-unconscious

**Why:** Complete encounter with lethargic_or_unconscious as the known general danger sign.

**Coverage:** `complete`, `danger_sign`, `urgent`

**Applicable approved decisions:** `IP-CQ-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": true,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-005-danger-lethargic-or-unconscious",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`

**Final classifications:** `VERY_SEVERE_DISEASE`

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-LETHARGIC-OR-UNCONSCIOUS`

**Source provenance:**

- `IMCI-MSC-GDS-LETHARGIC-OR-UNCONSCIOUS` — General danger signs; PDF page 5; printed page 1 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-006-danger-convulsing-now

**Why:** Complete encounter with convulsing_now as the known general danger sign.

**Coverage:** `complete`, `danger_sign`, `urgent`

**Applicable approved decisions:** `IP-CQ-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": true,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-006-danger-convulsing-now",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`

**Final classifications:** `VERY_SEVERE_DISEASE`

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_DIAZEPAM_IF_CONVULSING_NOW`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_DIAZEPAM_IF_CONVULSING_NOW`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-CONVULSING-NOW`

**Source provenance:**

- `IMCI-MSC-GDS-CONVULSING-NOW` — General danger signs; PDF page 5; printed page 1 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-007-resp-age-2-rate-49

**Why:** Complete respiratory semantic case: age-2-rate-49.

**Coverage:** `complete`, `respiratory`, `respiratory_boundary`, `age_2`, `rate_49`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-007-resp-age-2-rate-49",
  "fever": null,
  "patient_facts": {
    "age_months": 2,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 49,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `COUGH_OR_COLD`

**Final classifications:** `COUGH_OR_COLD`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-COUGH-OR-COLD`

**Source provenance:**

- `IMCI-MSC-RESP-COUGH-OR-COLD` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-008-resp-age-2-rate-50

**Why:** Complete respiratory semantic case: age-2-rate-50.

**Coverage:** `complete`, `respiratory`, `respiratory_boundary`, `age_2`, `rate_50`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-008-resp-age-2-rate-50",
  "fever": null,
  "patient_facts": {
    "age_months": 2,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 50,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** `PNEUMONIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS`, `GIVE_ORAL_AMOXICILLIN_5_DAYS`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-2-12M`, `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-2-12M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-009-resp-age-11-rate-50

**Why:** Complete respiratory semantic case: age-11-rate-50.

**Coverage:** `complete`, `respiratory`, `respiratory_boundary`, `age_11`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-009-resp-age-11-rate-50",
  "fever": null,
  "patient_facts": {
    "age_months": 11,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 50,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** `PNEUMONIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS`, `GIVE_ORAL_AMOXICILLIN_5_DAYS`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-2-12M`, `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-2-12M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-010-resp-age-12-rate-39

**Why:** Complete respiratory semantic case: age-12-rate-39.

**Coverage:** `complete`, `respiratory`, `respiratory_boundary`, `age_12`, `rate_39`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-010-resp-age-12-rate-39",
  "fever": null,
  "patient_facts": {
    "age_months": 12,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 39,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `COUGH_OR_COLD`

**Final classifications:** `COUGH_OR_COLD`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-COUGH-OR-COLD`

**Source provenance:**

- `IMCI-MSC-RESP-COUGH-OR-COLD` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-011-resp-age-12-rate-40

**Why:** Complete respiratory semantic case: age-12-rate-40.

**Coverage:** `complete`, `respiratory`, `respiratory_boundary`, `age_12`, `rate_40`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-011-resp-age-12-rate-40",
  "fever": null,
  "patient_facts": {
    "age_months": 12,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 40,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** `PNEUMONIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS`, `GIVE_ORAL_AMOXICILLIN_5_DAYS`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-12-60M`, `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-12-60M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-012-resp-age-59-rate-40

**Why:** Complete respiratory semantic case: age-59-rate-40.

**Coverage:** `complete`, `respiratory`, `respiratory_boundary`, `age_59`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-012-resp-age-59-rate-40",
  "fever": null,
  "patient_facts": {
    "age_months": 59,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 40,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** `PNEUMONIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS`, `GIVE_ORAL_AMOXICILLIN_5_DAYS`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-12-60M`, `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-12-60M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-013-resp-chest-hiv-negative

**Why:** Complete respiratory semantic case: chest-hiv-negative.

**Coverage:** `complete`, `respiratory`, `chest_indrawing`, `hiv_modifier_negative`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-013-resp-chest-hiv-negative",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": true,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": false,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** `PNEUMONIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS`, `GIVE_ORAL_AMOXICILLIN_5_DAYS`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-PNEUMONIA-CHEST-INDRAWING`

**Source provenance:**

- `IMCI-MSC-RESP-PNEUMONIA-CHEST-INDRAWING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-014-resp-chest-hiv-positive

**Why:** Complete respiratory semantic case: chest-hiv-positive.

**Coverage:** `complete`, `respiratory`, `chest_indrawing`, `hiv_modifier_positive`, `referral`

**Applicable approved decisions:** `IP-CQ-003`, `MSC-CQ-RESP-002`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-014-resp-chest-hiv-positive",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": true,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": true,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** `PNEUMONIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `GIVE_FIRST_DOSE_AMOXICILLIN_AND_REFER`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-PNEUMONIA-CHEST-INDRAWING`, `IMCI-MSC-RESP-HIV-CHEST-INDRAWING`

**Source provenance:**

- `IMCI-MSC-RESP-PNEUMONIA-CHEST-INDRAWING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-HIV-CHEST-INDRAWING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-015-resp-stridor

**Why:** Complete respiratory semantic case: stridor.

**Coverage:** `complete`, `respiratory`, `severe_respiratory`, `urgent`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-015-resp-stridor",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": true,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE`

**Final classifications:** `SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE`

**Urgent actions:** `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-SEVERE-STRIDOR`

**Source provenance:**

- `IMCI-MSC-RESP-SEVERE-STRIDOR` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-016-resp-oximeter-89-9

**Why:** Complete respiratory semantic case: oximeter-89-9.

**Coverage:** `complete`, `respiratory`, `oxygen_boundary`, `urgent`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** `imci-major-sick-child-oxygen-referral-disposition-v1`

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-016-resp-oximeter-89-9",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": 89.9,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": true,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `COUGH_OR_COLD`

**Final classifications:** `COUGH_OR_COLD`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `REFER_FOR_OXYGEN_SATURATION_BELOW_90`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-COUGH-OR-COLD`, `IMCI-MSC-RESP-OXYGEN-SATURATION`

**Source provenance:**

- `IMCI-MSC-RESP-COUGH-OR-COLD` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-OXYGEN-SATURATION` — Cough or difficult breathing footnote; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-017-resp-oximeter-90

**Why:** Complete respiratory semantic case: oximeter-90.

**Coverage:** `complete`, `respiratory`, `oxygen_boundary`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-017-resp-oximeter-90",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": 90.0,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": true,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `COUGH_OR_COLD`

**Final classifications:** `COUGH_OR_COLD`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-COUGH-OR-COLD`

**Source provenance:**

- `IMCI-MSC-RESP-COUGH-OR-COLD` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-018-resp-prolonged-cough

**Why:** Complete respiratory semantic case: prolonged-cough.

**Coverage:** `complete`, `respiratory`, `prolonged_cough`, `referral`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-018-resp-prolonged-cough",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 15,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `COUGH_OR_COLD`

**Final classifications:** `COUGH_OR_COLD`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `REFER_FOR_TB_OR_ASTHMA_ASSESSMENT`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-COUGH-OR-COLD`, `IMCI-MSC-RESP-PROLONGED-OR-RECURRENT`

**Source provenance:**

- `IMCI-MSC-RESP-COUGH-OR-COLD` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PROLONGED-OR-RECURRENT` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-019-resp-recurrent-wheeze

**Why:** Complete respiratory semantic case: recurrent-wheeze.

**Coverage:** `complete`, `respiratory`, `recurrent_wheeze`, `home_bronchodilator`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-019-resp-recurrent-wheeze",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": true,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": true
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `COUGH_OR_COLD`

**Final classifications:** `COUGH_OR_COLD`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_INHALED_BRONCHODILATOR_5_DAYS`, `REFER_FOR_TB_OR_ASTHMA_ASSESSMENT`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-COUGH-OR-COLD`, `IMCI-MSC-RESP-WHEEZE-HOME-TREATMENT`, `IMCI-MSC-RESP-PROLONGED-OR-RECURRENT`

**Source provenance:**

- `IMCI-MSC-RESP-COUGH-OR-COLD` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-WHEEZE-HOME-TREATMENT` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PROLONGED-OR-RECURRENT` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-020-resp-post-bronchodilator-improved

**Why:** Complete respiratory semantic case: post-bronchodilator-improved.

**Coverage:** `complete`, `respiratory`, `bronchodilator_reassessment`, `complete_post_reassessment`, `improved`

**Applicable approved decisions:** `IP-CQ-003`, `MSC-CQ-RESP-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-020-resp-post-bronchodilator-improved",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": true,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": true,
    "post_bronchodilator_chest_indrawing": false,
    "post_bronchodilator_child_calm": true,
    "post_bronchodilator_respiratory_rate": 35,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 45,
    "stridor_when_calm": false,
    "wheezing": true
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `COUGH_OR_COLD`

**Final classifications:** `COUGH_OR_COLD`

**Urgent actions:** none

**Intermediate actions:** `GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL`, `REASSESS_BREATHING_AFTER_BRONCHODILATOR`

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_INHALED_BRONCHODILATOR_5_DAYS`, `GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL`, `REASSESS_BREATHING_AFTER_BRONCHODILATOR`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-12-60M`, `IMCI-MSC-RESP-WHEEZE-BRONCHODILATOR-REASSESS`, `IMCI-MSC-RESP-COUGH-OR-COLD`, `IMCI-MSC-RESP-WHEEZE-HOME-TREATMENT`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-12-60M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-WHEEZE-BRONCHODILATOR-REASSESS` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-COUGH-OR-COLD` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-WHEEZE-HOME-TREATMENT` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-021-resp-post-bronchodilator-fast

**Why:** Complete respiratory semantic case: post-bronchodilator-fast.

**Coverage:** `complete`, `respiratory`, `bronchodilator_reassessment`, `complete_post_reassessment`, `persistent_fast_breathing`

**Applicable approved decisions:** `IP-CQ-003`, `MSC-CQ-RESP-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-021-resp-post-bronchodilator-fast",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": true,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": true,
    "post_bronchodilator_chest_indrawing": false,
    "post_bronchodilator_child_calm": true,
    "post_bronchodilator_respiratory_rate": 42,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 45,
    "stridor_when_calm": false,
    "wheezing": true
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** `PNEUMONIA`

**Urgent actions:** none

**Intermediate actions:** `GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL`, `REASSESS_BREATHING_AFTER_BRONCHODILATOR`

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS`, `GIVE_INHALED_BRONCHODILATOR_5_DAYS`, `GIVE_ORAL_AMOXICILLIN_5_DAYS`, `GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL`, `REASSESS_BREATHING_AFTER_BRONCHODILATOR`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-12-60M`, `IMCI-MSC-RESP-WHEEZE-BRONCHODILATOR-REASSESS`, `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING`, `IMCI-MSC-RESP-WHEEZE-HOME-TREATMENT`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-12-60M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-WHEEZE-BRONCHODILATOR-REASSESS` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-WHEEZE-HOME-TREATMENT` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-022-resp-trial-outstanding

**Why:** Incomplete respiratory semantic case: trial-outstanding.

**Coverage:** `incomplete`, `respiratory`, `bronchodilator_reassessment`

**Applicable approved decisions:** `IP-CQ-003`, `MSC-CQ-RESP-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[2]",
    "fields": [
      "respiratory.bronchodilator_trial_completed",
      "respiratory.post_bronchodilator_breaths_counted_one_minute",
      "respiratory.post_bronchodilator_chest_indrawing",
      "respiratory.post_bronchodilator_child_calm",
      "respiratory.post_bronchodilator_respiratory_rate"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-03",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "respiratory.wheezing_with_fast_breathing_or_chest_indrawing": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-022-resp-trial-outstanding",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 45,
    "stridor_when_calm": false,
    "wheezing": true
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** `GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL`, `REASSESS_BREATHING_AFTER_BRONCHODILATOR`

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "respiratory": [
    "respiratory.bronchodilator_trial_completed",
    "respiratory.post_bronchodilator_breaths_counted_one_minute",
    "respiratory.post_bronchodilator_chest_indrawing",
    "respiratory.post_bronchodilator_child_calm",
    "respiratory.post_bronchodilator_respiratory_rate"
  ]
}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-12-60M`, `IMCI-MSC-RESP-WHEEZE-BRONCHODILATOR-REASSESS`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-12-60M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-WHEEZE-BRONCHODILATOR-REASSESS` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-023-resp-child-not-calm

**Why:** Incomplete respiratory semantic case: child-not-calm.

**Coverage:** `incomplete`, `respiratory`, `invalid_evidence`, `contradiction`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "invalid_evidence_blocks_completion",
    "details": [
      "respiratory observations are invalid because the child was not calm"
    ],
    "fields": [],
    "provenance_id": "HC-INVALID-EVIDENCE",
    "provenance_type": "EVIDENCE_VALIDITY_REQUIREMENT"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-023-resp-child-not-calm",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": false,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{}
```

**Contradictions:** respiratory observations are invalid because the child was not calm

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-024-resp-count-not-one-minute

**Why:** Incomplete respiratory semantic case: count-not-one-minute.

**Coverage:** `incomplete`, `respiratory`, `invalid_evidence`, `contradiction`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "invalid_evidence_blocks_completion",
    "details": [
      "respiratory rate is invalid because breaths were not counted for one minute"
    ],
    "fields": [],
    "provenance_id": "HC-INVALID-EVIDENCE",
    "provenance_type": "EVIDENCE_VALIDITY_REQUIREMENT"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-024-resp-count-not-one-minute",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": false,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{}
```

**Contradictions:** respiratory rate is invalid because breaths were not counted for one minute

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-025-resp-oximeter-missing-value

**Why:** Incomplete respiratory semantic case: oximeter-missing-value.

**Coverage:** `incomplete`, `respiratory`, `single_omission`, `measurement_missing`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[1]",
    "fields": [
      "respiratory.oxygen_saturation_percent"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-02",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "respiratory.pulse_oximeter_available": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-025-resp-oximeter-missing-value",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": true,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** `COUGH_OR_COLD`

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "respiratory": [
    "respiratory.oxygen_saturation_percent"
  ]
}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-COUGH-OR-COLD`

**Source provenance:**

- `IMCI-MSC-RESP-COUGH-OR-COLD` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-026-resp-chest-hiv-unknown

**Why:** Incomplete respiratory semantic case: chest-hiv-unknown.

**Coverage:** `incomplete`, `respiratory`, `single_omission`, `hiv_modifier_unknown`

**Applicable approved decisions:** `IP-CQ-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[3]",
    "fields": [
      "respiratory.hiv_exposed_or_infected"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-04",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "respiratory.effective_chest_indrawing": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-026-resp-chest-hiv-unknown",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": true,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "respiratory": [
    "respiratory.hiv_exposed_or_infected"
  ]
}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-PNEUMONIA-CHEST-INDRAWING`

**Source provenance:**

- `IMCI-MSC-RESP-PNEUMONIA-CHEST-INDRAWING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-027-diarrhoea-no-dehydration

**Why:** Complete diarrhoea semantic case: no-dehydration.

**Coverage:** `complete`, `diarrhoea`, `no_dehydration`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-027-diarrhoea-no-dehydration",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `NO_DEHYDRATION`

**Final classifications:** `NO_DEHYDRATION`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_A`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-028-diarrhoea-some-dehydration

**Why:** Complete diarrhoea semantic case: some-dehydration.

**Coverage:** `complete`, `diarrhoea`, `some_dehydration`, `plan_b`, `initial_treatment_stage`

**Applicable approved decisions:** `MSC-CQ-REASSESS-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": true,
      "skin_pinch": "NORMAL",
      "sunken_eyes": true
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-028-diarrhoea-some-dehydration",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `SOME_DEHYDRATION`

**Final classifications:** `SOME_DEHYDRATION`

**Urgent actions:** none

**Intermediate actions:** `GIVE_FLUID_ZINC_AND_FOOD_PLAN_B`, `REASSESS_DEHYDRATION_AFTER_PLAN_B`

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_B`, `REASSESS_DEHYDRATION_AFTER_PLAN_B`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-SOME-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-SOME-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-029-diarrhoea-severe-plan-c-under-24m

**Why:** Complete diarrhoea semantic case: severe-plan-c-under-24m.

**Coverage:** `complete`, `diarrhoea`, `severe_dehydration`, `plan_c`, `initial_treatment_stage`

**Applicable approved decisions:** `MSC-CQ-REASSESS-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "POORLY",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": true
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-029-diarrhoea-severe-plan-c-under-24m",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `SEVERE_DEHYDRATION`

**Final classifications:** `SEVERE_DEHYDRATION`

**Urgent actions:** none

**Intermediate actions:** `GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C`, `REASSESS_DEHYDRATION_AFTER_PLAN_C`

**Deferred actions:** none

**Final actions:** `GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C`, `REASSESS_DEHYDRATION_AFTER_PLAN_C`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-030-diarrhoea-severe-age-24-no-cholera

**Why:** Complete diarrhoea semantic case: severe-age-24-no-cholera.

**Coverage:** `complete`, `diarrhoea`, `severe_dehydration`, `cholera_context`, `age_boundary`

**Applicable approved decisions:** `MSC-CQ-DIARRHOEA-001`, `MSC-CQ-REASSESS-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": false,
    "dehydration": {
      "drinking_status": "POORLY",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": true
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-030-diarrhoea-severe-age-24-no-cholera",
  "fever": null,
  "patient_facts": {
    "age_months": 24,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `SEVERE_DEHYDRATION`

**Final classifications:** `SEVERE_DEHYDRATION`

**Urgent actions:** none

**Intermediate actions:** `GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C`, `REASSESS_DEHYDRATION_AFTER_PLAN_C`

**Deferred actions:** none

**Final actions:** `GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C`, `REASSESS_DEHYDRATION_AFTER_PLAN_C`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-031-diarrhoea-severe-age-24-cholera

**Why:** Complete diarrhoea semantic case: severe-age-24-cholera.

**Coverage:** `complete`, `diarrhoea`, `severe_dehydration`, `cholera_action`, `local_protocol_generic`

**Applicable approved decisions:** `MSC-CQ-DIARRHOEA-001`, `MSC-CQ-REASSESS-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": true,
    "dehydration": {
      "drinking_status": "POORLY",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": true
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-031-diarrhoea-severe-age-24-cholera",
  "fever": null,
  "patient_facts": {
    "age_months": 24,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `SEVERE_DEHYDRATION`

**Final classifications:** `SEVERE_DEHYDRATION`

**Urgent actions:** none

**Intermediate actions:** `GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C`, `REASSESS_DEHYDRATION_AFTER_PLAN_C`

**Deferred actions:** none

**Final actions:** `GIVE_CHOLERA_ANTIBIOTIC_PER_LOCAL_PROTOCOL`, `GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C`, `REASSESS_DEHYDRATION_AFTER_PLAN_C`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION`, `IMCI-MSC-DIARRHOEA-CHOLERA-CONTEXT`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76
- `IMCI-MSC-DIARRHOEA-CHOLERA-CONTEXT` — Diarrhoea - severe dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-032-diarrhoea-duration-13

**Why:** Complete diarrhoea semantic case: duration-13.

**Coverage:** `complete`, `diarrhoea`, `duration_boundary`, `not_persistent`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 13,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-032-diarrhoea-duration-13",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `NO_DEHYDRATION`

**Final classifications:** `NO_DEHYDRATION`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_A`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-033-diarrhoea-duration-14-persistent

**Why:** Complete diarrhoea semantic case: duration-14-persistent.

**Coverage:** `complete`, `diarrhoea`, `duration_boundary`, `persistent_diarrhoea`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 14,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-033-diarrhoea-duration-14-persistent",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `NO_DEHYDRATION`, `PERSISTENT_DIARRHOEA`

**Final classifications:** `NO_DEHYDRATION`, `PERSISTENT_DIARRHOEA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_FEEDING_FOR_PERSISTENT_DIARRHOEA`, `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_A`, `GIVE_MULTIVITAMINS_MINERALS_ZINC_14_DAYS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`, `IMCI-MSC-DIARRHOEA-PERSISTENT`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76
- `IMCI-MSC-DIARRHOEA-PERSISTENT` — Diarrhoea - persistent diarrhoea; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-034-diarrhoea-severe-persistent

**Why:** Complete diarrhoea semantic case: severe-persistent.

**Coverage:** `complete`, `diarrhoea`, `severe_persistent_diarrhoea`, `urgent`

**Applicable approved decisions:** `IP-CQ-004`, `MSC-CQ-REASSESS-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": true,
      "skin_pinch": "NORMAL",
      "sunken_eyes": true
    },
    "duration_days": 14,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-034-diarrhoea-severe-persistent",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `SOME_DEHYDRATION`, `SEVERE_PERSISTENT_DIARRHOEA`

**Final classifications:** `SOME_DEHYDRATION`, `SEVERE_PERSISTENT_DIARRHOEA`

**Urgent actions:** `REFER_TO_HOSPITAL`

**Intermediate actions:** `GIVE_FLUID_ZINC_AND_FOOD_PLAN_B`, `REASSESS_DEHYDRATION_AFTER_PLAN_B`, `TREAT_DEHYDRATION_BEFORE_REFERRAL`

**Deferred actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_B`, `REASSESS_DEHYDRATION_AFTER_PLAN_B`

**Final actions:** `REFER_TO_HOSPITAL`, `TREAT_DEHYDRATION_BEFORE_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-SOME-DEHYDRATION`, `IMCI-MSC-DIARRHOEA-SEVERE-PERSISTENT`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-SOME-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76
- `IMCI-MSC-DIARRHOEA-SEVERE-PERSISTENT` — Diarrhoea - persistent diarrhoea; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-035-diarrhoea-dysentery

**Why:** Complete diarrhoea semantic case: dysentery.

**Coverage:** `complete`, `diarrhoea`, `dysentery`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": true,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-035-diarrhoea-dysentery",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `NO_DEHYDRATION`, `DYSENTERY`

**Final classifications:** `NO_DEHYDRATION`, `DYSENTERY`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_CIPROFLOXACIN_3_DAYS`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_A`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`, `IMCI-MSC-DIARRHOEA-DYSENTERY`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76
- `IMCI-MSC-DIARRHOEA-DYSENTERY` — Diarrhoea - blood in stool; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-036-diarrhoea-persistent-and-dysentery

**Why:** Complete diarrhoea semantic case: persistent-and-dysentery.

**Coverage:** `complete`, `diarrhoea`, `simultaneous_classifications`, `persistent_diarrhoea`, `dysentery`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": true,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 14,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-036-diarrhoea-persistent-and-dysentery",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `NO_DEHYDRATION`, `PERSISTENT_DIARRHOEA`, `DYSENTERY`

**Final classifications:** `NO_DEHYDRATION`, `PERSISTENT_DIARRHOEA`, `DYSENTERY`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_FEEDING_FOR_PERSISTENT_DIARRHOEA`, `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS`, `FOLLOW_UP_5_DAYS`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_CIPROFLOXACIN_3_DAYS`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_A`, `GIVE_MULTIVITAMINS_MINERALS_ZINC_14_DAYS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`, `IMCI-MSC-DIARRHOEA-PERSISTENT`, `IMCI-MSC-DIARRHOEA-DYSENTERY`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76
- `IMCI-MSC-DIARRHOEA-PERSISTENT` — Diarrhoea - persistent diarrhoea; PDF page 7; printed page 3 of 76
- `IMCI-MSC-DIARRHOEA-DYSENTERY` — Diarrhoea - blood in stool; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-037-diarrhoea-positive-drinking-reuse

**Why:** Clinically confirmed inability to drink is reused one-way in dehydration assessment.

**Coverage:** `complete`, `diarrhoea`, `cross_evidence_reuse`, `urgent`

**Applicable approved decisions:** `IP-CQ-001`, `IP-CQ-002`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": true,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": null,
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": true
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-037-diarrhoea-positive-drinking-reuse",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`, `SEVERE_DEHYDRATION`

**Final classifications:** `VERY_SEVERE_DISEASE`, `SEVERE_DEHYDRATION`

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `CONTINUE_BREASTFEEDING`, `FREQUENT_ORS_SIPS_DURING_REFERRAL`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `CONTINUE_BREASTFEEDING`, `FREQUENT_ORS_SIPS_DURING_REFERRAL`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-UNABLE-TO-DRINK`, `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-GDS-UNABLE-TO-DRINK` — General danger signs; PDF page 5; printed page 1 of 76
- `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-038-diarrhoea-negative-does-not-reuse

**Why:** A negative danger-sign answer does not fill diarrhoea drinking status.

**Coverage:** `incomplete`, `diarrhoea`, `explicit_negative_omission_twin`, `single_omission`

**Applicable approved decisions:** `IP-CQ-002`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[4]",
    "fields": [
      "diarrhoea.dehydration.drinking_status"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-05",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "patient_facts.has_diarrhoea": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": null,
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-038-diarrhoea-negative-does-not-reuse",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "diarrhoea": [
    "diarrhoea.dehydration.drinking_status"
  ]
}
```

**Contradictions:** none

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-039-diarrhoea-duration-unknown

**Why:** Known diarrhoea pathway with duration omitted remains incomplete.

**Coverage:** `incomplete`, `diarrhoea`, `single_omission`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[4]",
    "fields": [
      "diarrhoea.duration_days"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-05",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "patient_facts.has_diarrhoea": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": null,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-039-diarrhoea-duration-unknown",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** `NO_DEHYDRATION`

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "diarrhoea": [
    "diarrhoea.duration_days"
  ]
}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-040-diarrhoea-cholera-context-unknown

**Why:** Severe dehydration at 24 months requires cholera-area context.

**Coverage:** `incomplete`, `diarrhoea`, `conditional_omission`, `cholera_context`

**Applicable approved decisions:** `MSC-CQ-DIARRHOEA-001`, `MSC-CQ-REASSESS-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[5]",
    "fields": [
      "diarrhoea.cholera_in_area"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-06",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "age_months": {
        "gte": 24
      },
      "classification": "SEVERE_DEHYDRATION"
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "POORLY",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": true
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-040-diarrhoea-cholera-context-unknown",
  "fever": null,
  "patient_facts": {
    "age_months": 24,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** `SEVERE_DEHYDRATION`

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** `GIVE_FLUID_FOR_SEVERE_DEHYDRATION_PLAN_C`, `REASSESS_DEHYDRATION_AFTER_PLAN_C`

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "diarrhoea": [
    "diarrhoea.cholera_in_area"
  ]
}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-041-fever-high-positive

**Why:** Complete fever/measles semantic case: high-positive.

**Coverage:** `complete`, `fever`, `malaria`, `high_risk`, `test_positive`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-041-fever-high-positive",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "POSITIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `MALARIA`

**Final classifications:** `MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_FIRST_LINE_ORAL_ANTIMALARIAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-MALARIA`

**Source provenance:**

- `IMCI-MSC-FEVER-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-042-fever-high-negative

**Why:** Complete fever/measles semantic case: high-negative.

**Coverage:** `complete`, `fever`, `fever_no_malaria`, `high_risk`, `test_negative`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-042-fever-high-negative",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`

**Final classifications:** `FEVER_NO_MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-043-fever-high-test-unavailable

**Why:** Complete fever/measles semantic case: high-test-unavailable.

**Coverage:** `complete`, `fever`, `malaria`, `test_unavailable`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-043-fever-high-test-unavailable",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": false,
    "malaria_test_result": null,
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `MALARIA`

**Final classifications:** `MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_FIRST_LINE_ORAL_ANTIMALARIAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-MALARIA`

**Source provenance:**

- `IMCI-MSC-FEVER-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-044-fever-low-obvious-cause

**Why:** Complete fever/measles semantic case: low-obvious-cause.

**Coverage:** `complete`, `fever`, `fever_no_malaria`, `low_risk`, `obvious_cause`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-044-fever-low-obvious-cause",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "LOW",
    "malaria_test_available": null,
    "malaria_test_result": null,
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": true,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`

**Final classifications:** `FEVER_NO_MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-045-fever-low-no-cause-positive

**Why:** Complete fever/measles semantic case: low-no-cause-positive.

**Coverage:** `complete`, `fever`, `malaria`, `low_risk`, `test_positive`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-045-fever-low-no-cause-positive",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "LOW",
    "malaria_test_available": true,
    "malaria_test_result": "POSITIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `MALARIA`

**Final classifications:** `MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_FIRST_LINE_ORAL_ANTIMALARIAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-MALARIA`

**Source provenance:**

- `IMCI-MSC-FEVER-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-046-fever-no-risk

**Why:** Complete fever/measles semantic case: no-risk.

**Coverage:** `complete`, `fever`, `no_malaria_risk`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-046-fever-no-risk",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "NONE_NO_TRAVEL",
    "malaria_test_available": null,
    "malaria_test_result": null,
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER`

**Final classifications:** `FEVER`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_2_DAYS_IF_FEVER_PERSISTS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA-RISK`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA-RISK` — Fever - no malaria risk and no travel; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-047-fever-temperature-38-4

**Why:** Complete fever/measles semantic case: temperature-38-4.

**Coverage:** `complete`, `fever`, `temperature_boundary`, `no_high_fever_action`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-047-fever-temperature-38-4",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.4
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`

**Final classifications:** `FEVER_NO_MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-048-fever-temperature-38-5

**Why:** Complete fever/measles semantic case: temperature-38-5.

**Coverage:** `complete`, `fever`, `temperature_boundary`, `high_fever_action`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-048-fever-temperature-38-5",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.5
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`

**Final classifications:** `FEVER_NO_MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_PARACETAMOL_FOR_HIGH_FEVER`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`, `IMCI-MSC-FEVER-HIGH-TEMPERATURE`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-FEVER-HIGH-TEMPERATURE` — Fever; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-049-fever-duration-7

**Why:** Complete fever/measles semantic case: duration-7.

**Coverage:** `complete`, `fever`, `duration_boundary`, `not_prolonged`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-049-fever-duration-7",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 7,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`

**Final classifications:** `FEVER_NO_MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-050-fever-duration-8-not-every-day

**Why:** Complete fever/measles semantic case: duration-8-not-every-day.

**Coverage:** `complete`, `fever`, `duration_boundary`, `not_prolonged`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-050-fever-duration-8-not-every-day",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 8,
    "fever_present_every_day": false,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`

**Final classifications:** `FEVER_NO_MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-051-fever-duration-8-every-day

**Why:** Complete fever/measles semantic case: duration-8-every-day.

**Coverage:** `complete`, `fever`, `prolonged_fever`, `referral`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-051-fever-duration-8-every-day",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 8,
    "fever_present_every_day": true,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`

**Final classifications:** `FEVER_NO_MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `REFER_PROLONGED_FEVER_FOR_ASSESSMENT`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`, `IMCI-MSC-FEVER-PROLONGED`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-FEVER-PROLONGED` — Fever; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-052-fever-identified-bacterial-cause

**Why:** Complete fever/measles semantic case: identified-bacterial-cause.

**Coverage:** `complete`, `fever`, `generic_antibiotic_action`, `identified_bacterial_cause`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-002`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-052-fever-identified-bacterial-cause",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": true,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`

**Final classifications:** `FEVER_NO_MALARIA`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_APPROPRIATE_ANTIBIOTIC_FOR_IDENTIFIED_BACTERIAL_CAUSE`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`, `IMCI-MSC-FEVER-IDENTIFIED-BACTERIAL-CAUSE`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-FEVER-IDENTIFIED-BACTERIAL-CAUSE` — Fever; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-053-fever-measles

**Why:** Complete fever/measles semantic case: measles.

**Coverage:** `complete`, `fever`, `measles`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-053-fever-measles",
  "fever": {
    "clouding_of_cornea": false,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": true,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": true,
    "measles_within_last_3_months": false,
    "mouth_ulcers": false,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": false,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`, `MEASLES`

**Final classifications:** `FEVER_NO_MALARIA`, `MEASLES`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_VITAMIN_A_TREATMENT`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`, `IMCI-MSC-MEASLES`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-MEASLES` — Measles; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-054-fever-measles-eye

**Why:** Complete fever/measles semantic case: measles-eye.

**Coverage:** `complete`, `fever`, `measles_eye_or_mouth_complications`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-054-fever-measles-eye",
  "fever": {
    "clouding_of_cornea": false,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": true,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": false,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": true,
    "red_eyes": true,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`, `MEASLES_WITH_EYE_OR_MOUTH_COMPLICATIONS`

**Final classifications:** `FEVER_NO_MALARIA`, `MEASLES_WITH_EYE_OR_MOUTH_COMPLICATIONS`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `APPLY_TETRACYCLINE_EYE_OINTMENT`, `FOLLOW_UP_3_DAYS`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_VITAMIN_A_TREATMENT`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`, `IMCI-MSC-MEASLES-EYE-OR-MOUTH-COMPLICATIONS`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-MEASLES-EYE-OR-MOUTH-COMPLICATIONS` — Measles; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-055-fever-severe-measles-cornea

**Why:** Complete fever/measles semantic case: severe-measles-cornea.

**Coverage:** `complete`, `fever`, `severe_complicated_measles`, `urgent`

**Applicable approved decisions:** `IP-CQ-004`, `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-055-fever-severe-measles-cornea",
  "fever": {
    "clouding_of_cornea": true,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": true,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": false,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": false,
    "red_eyes": true,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `FEVER_NO_MALARIA`, `SEVERE_COMPLICATED_MEASLES`

**Final classifications:** `FEVER_NO_MALARIA`, `SEVERE_COMPLICATED_MEASLES`

**Urgent actions:** `APPLY_TETRACYCLINE_EYE_OINTMENT`, `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_VITAMIN_A_TREATMENT`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`

**Final actions:** `APPLY_TETRACYCLINE_EYE_OINTMENT`, `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_VITAMIN_A_TREATMENT`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`, `IMCI-MSC-MEASLES-SEVERE-COMPLICATED`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-MEASLES-SEVERE-COMPLICATED` — Measles; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-056-fever-severe-stiff-neck

**Why:** Complete fever/measles semantic case: severe-stiff-neck.

**Coverage:** `complete`, `fever`, `very_severe_febrile_disease`, `urgent`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-056-fever-severe-stiff-neck",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": true,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_FEBRILE_DISEASE`

**Final classifications:** `VERY_SEVERE_FEBRILE_DISEASE`

**Urgent actions:** `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-VERY-SEVERE`

**Source provenance:**

- `IMCI-MSC-FEVER-VERY-SEVERE` — Fever; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-057-fever-malaria-and-measles

**Why:** Complete fever/measles semantic case: malaria-and-measles.

**Coverage:** `complete`, `fever`, `simultaneous_classifications`, `malaria`, `measles`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-057-fever-malaria-and-measles",
  "fever": {
    "clouding_of_cornea": false,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": true,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "POSITIVE",
    "measles_cough": true,
    "measles_within_last_3_months": false,
    "mouth_ulcers": false,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": false,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.5
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `MALARIA`, `MEASLES`

**Final classifications:** `MALARIA`, `MEASLES`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_FIRST_LINE_ORAL_ANTIMALARIAL`, `GIVE_PARACETAMOL_FOR_HIGH_FEVER`, `GIVE_VITAMIN_A_TREATMENT`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-MALARIA`, `IMCI-MSC-MEASLES`, `IMCI-MSC-FEVER-HIGH-TEMPERATURE`

**Source provenance:**

- `IMCI-MSC-FEVER-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-MEASLES` — Measles; PDF page 8; printed page 4 of 76
- `IMCI-MSC-FEVER-HIGH-TEMPERATURE` — Fever; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-058-fever-measles-last-three-months

**Why:** Complete fever/measles semantic case: measles-last-three-months.

**Coverage:** `complete`, `fever`, `measles_history`, `measles`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-058-fever-measles-last-three-months",
  "fever": {
    "clouding_of_cornea": false,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": true,
    "mouth_ulcers": false,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": false,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `FEVER_NO_MALARIA`, `MEASLES`

**Final classifications:** `FEVER_NO_MALARIA`, `MEASLES`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `GIVE_VITAMIN_A_TREATMENT`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-FEVER-NO-MALARIA`, `IMCI-MSC-MEASLES`

**Source provenance:**

- `IMCI-MSC-FEVER-NO-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-MEASLES` — Measles; PDF page 8; printed page 4 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-059-fever-malaria-risk-unknown

**Why:** Applicable fever assessment with malaria-area risk context omitted.

**Coverage:** `incomplete`, `fever`, `case_context_missing`, `single_omission`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[6]",
    "fields": [
      "fever.malaria_risk"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-07",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "patient_facts.has_fever": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-059-fever-malaria-risk-unknown",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": null,
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "fever": [
    "fever.malaria_risk"
  ]
}
```

**Contradictions:** none

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-060-fever-test-result-unknown

**Why:** Available required malaria test without a result remains incomplete.

**Coverage:** `incomplete`, `fever`, `single_omission`, `test_result_missing`

**Applicable approved decisions:** `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[9]",
    "fields": [
      "fever.malaria_test_result"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-10",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "fever.malaria_test_available": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-060-fever-test-result-unknown",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": null,
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": true
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "fever": [
    "fever.malaria_test_result"
  ]
}
```

**Contradictions:** none

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-061-ear-no-infection

**Why:** Complete ear semantic case: no-infection.

**Coverage:** `complete`, `ear_problem`, `no_ear_infection`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": false,
    "ear_pain": false,
    "pus_draining_from_ear": false,
    "tender_swelling_behind_ear": false
  },
  "encounter_id": "hpg-061-ear-no-infection",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": true,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `NO_EAR_INFECTION`

**Final classifications:** `NO_EAR_INFECTION`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `NO_EAR_TREATMENT`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-EAR-NO-INFECTION`

**Source provenance:**

- `IMCI-MSC-EAR-NO-INFECTION` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-062-ear-acute-pain

**Why:** Complete ear semantic case: acute-pain.

**Coverage:** `complete`, `ear_problem`, `acute_ear_infection`, `ear_pain`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": false,
    "ear_pain": true,
    "pus_draining_from_ear": false,
    "tender_swelling_behind_ear": false
  },
  "encounter_id": "hpg-062-ear-acute-pain",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": true,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `ACUTE_EAR_INFECTION`

**Final classifications:** `ACUTE_EAR_INFECTION`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `DRY_EAR_BY_WICKING`, `FOLLOW_UP_5_DAYS`, `GIVE_ANTIBIOTIC_5_DAYS`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-EAR-ACUTE-INFECTION`

**Source provenance:**

- `IMCI-MSC-EAR-ACUTE-INFECTION` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-063-ear-acute-discharge-13

**Why:** Complete ear semantic case: acute-discharge-13.

**Coverage:** `complete`, `ear_problem`, `acute_ear_infection`, `duration_boundary`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": {
    "ear_discharge_duration_days": 13,
    "ear_discharge_reported": true,
    "ear_pain": false,
    "pus_draining_from_ear": true,
    "tender_swelling_behind_ear": false
  },
  "encounter_id": "hpg-063-ear-acute-discharge-13",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": true,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `ACUTE_EAR_INFECTION`

**Final classifications:** `ACUTE_EAR_INFECTION`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `DRY_EAR_BY_WICKING`, `FOLLOW_UP_5_DAYS`, `GIVE_ANTIBIOTIC_5_DAYS`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-EAR-ACUTE-INFECTION`

**Source provenance:**

- `IMCI-MSC-EAR-ACUTE-INFECTION` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-064-ear-chronic-discharge-14

**Why:** Complete ear semantic case: chronic-discharge-14.

**Coverage:** `complete`, `ear_problem`, `chronic_ear_infection`, `duration_boundary`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": {
    "ear_discharge_duration_days": 14,
    "ear_discharge_reported": true,
    "ear_pain": false,
    "pus_draining_from_ear": true,
    "tender_swelling_behind_ear": false
  },
  "encounter_id": "hpg-064-ear-chronic-discharge-14",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": true,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `CHRONIC_EAR_INFECTION`

**Final classifications:** `CHRONIC_EAR_INFECTION`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `DRY_EAR_BY_WICKING`, `FOLLOW_UP_5_DAYS`, `GIVE_TOPICAL_QUINOLONE_EARDROPS_14_DAYS`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-EAR-CHRONIC-INFECTION`

**Source provenance:**

- `IMCI-MSC-EAR-CHRONIC-INFECTION` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-065-ear-observed-pus-no-history

**Why:** Complete ear semantic case: observed-pus-no-history.

**Coverage:** `complete`, `ear_problem`, `acute_ear_infection`, `observed_pus`, `negative_history`

**Applicable approved decisions:** `MSC-CQ-EAR-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": false,
    "ear_pain": false,
    "pus_draining_from_ear": true,
    "tender_swelling_behind_ear": false
  },
  "encounter_id": "hpg-065-ear-observed-pus-no-history",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": true,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `ACUTE_EAR_INFECTION`

**Final classifications:** `ACUTE_EAR_INFECTION`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `DRY_EAR_BY_WICKING`, `FOLLOW_UP_5_DAYS`, `GIVE_ANTIBIOTIC_5_DAYS`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-EAR-ACUTE-INFECTION`

**Source provenance:**

- `IMCI-MSC-EAR-ACUTE-INFECTION` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-066-ear-mastoiditis

**Why:** Complete ear semantic case: mastoiditis.

**Coverage:** `complete`, `ear_problem`, `mastoiditis`, `urgent`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": false,
    "ear_pain": false,
    "pus_draining_from_ear": false,
    "tender_swelling_behind_ear": true
  },
  "encounter_id": "hpg-066-ear-mastoiditis",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": true,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `MASTOIDITIS`

**Final classifications:** `MASTOIDITIS`

**Urgent actions:** `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-EAR-MASTOIDITIS`

**Source provenance:**

- `IMCI-MSC-EAR-MASTOIDITIS` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-067-ear-duration-unknown

**Why:** Reported ear discharge requires its duration.

**Coverage:** `incomplete`, `ear_problem`, `single_omission`

**Applicable approved decisions:** none

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[13]",
    "fields": [
      "ear.ear_discharge_duration_days"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-14",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "ear.ear_discharge_reported": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": true,
    "ear_pain": false,
    "pus_draining_from_ear": true,
    "tender_swelling_behind_ear": false
  },
  "encounter_id": "hpg-067-ear-duration-unknown",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": true,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "ear_problem": [
    "ear.ear_discharge_duration_days"
  ]
}
```

**Contradictions:** none

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-068-cross-four-pathways

**Why:** Complete whole encounter with simultaneous respiratory, diarrhoea, malaria/measles, and ear classifications.

**Coverage:** `complete`, `whole_encounter`, `simultaneous_classifications`, `integrated_action_plan`, `all_pathways`

**Applicable approved decisions:** `IP-CQ-003`, `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": true,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": false,
    "ear_pain": true,
    "pus_draining_from_ear": false,
    "tender_swelling_behind_ear": false
  },
  "encounter_id": "hpg-068-cross-four-pathways",
  "fever": {
    "clouding_of_cornea": false,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": true,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "POSITIVE",
    "measles_cough": true,
    "measles_within_last_3_months": false,
    "mouth_ulcers": false,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": false,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": true,
    "has_ear_problem": true,
    "has_fever": true
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 42,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`, `NO_DEHYDRATION`, `DYSENTERY`, `MALARIA`, `MEASLES`, `ACUTE_EAR_INFECTION`

**Final classifications:** `PNEUMONIA`, `NO_DEHYDRATION`, `DYSENTERY`, `MALARIA`, `MEASLES`, `ACUTE_EAR_INFECTION`

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `DRY_EAR_BY_WICKING`, `FOLLOW_UP_3_DAYS`, `FOLLOW_UP_3_DAYS_IF_FEVER_PERSISTS`, `FOLLOW_UP_5_DAYS`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_ANTIBIOTIC_5_DAYS`, `GIVE_CIPROFLOXACIN_3_DAYS`, `GIVE_FIRST_LINE_ORAL_ANTIMALARIAL`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_A`, `GIVE_ORAL_AMOXICILLIN_5_DAYS`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`, `GIVE_VITAMIN_A_TREATMENT`, `SOOTHE_THROAT_AND_RELIEVE_COUGH`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-12-60M`, `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING`, `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`, `IMCI-MSC-DIARRHOEA-DYSENTERY`, `IMCI-MSC-FEVER-MALARIA`, `IMCI-MSC-MEASLES`, `IMCI-MSC-EAR-ACUTE-INFECTION`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-12-60M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76
- `IMCI-MSC-DIARRHOEA-DYSENTERY` — Diarrhoea - blood in stool; PDF page 7; printed page 3 of 76
- `IMCI-MSC-FEVER-MALARIA` — Fever - high or low malaria risk; PDF page 8; printed page 4 of 76
- `IMCI-MSC-MEASLES` — Measles; PDF page 8; printed page 4 of 76
- `IMCI-MSC-EAR-ACUTE-INFECTION` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-069-cross-urgent-dehydration-ear

**Why:** Mastoiditis changes simultaneous severe-dehydration management to referral transfer actions.

**Coverage:** `complete`, `cross_pathway_action_dependency`, `urgent`, `deferred_routine_actions`

**Applicable approved decisions:** `IP-CQ-004`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "POORLY",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": true
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": false,
    "ear_pain": false,
    "pus_draining_from_ear": false,
    "tender_swelling_behind_ear": true
  },
  "encounter_id": "hpg-069-cross-urgent-dehydration-ear",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": true,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `SEVERE_DEHYDRATION`, `MASTOIDITIS`

**Final classifications:** `SEVERE_DEHYDRATION`, `MASTOIDITIS`

**Urgent actions:** `CONTINUE_BREASTFEEDING`, `FREQUENT_ORS_SIPS_DURING_REFERRAL`, `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `CONTINUE_BREASTFEEDING`, `FREQUENT_ORS_SIPS_DURING_REFERRAL`, `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION`, `IMCI-MSC-EAR-MASTOIDITIS`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-SEVERE-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76
- `IMCI-MSC-EAR-MASTOIDITIS` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-070-cross-multiple-urgent

**Why:** Multiple severe findings deduplicate shared urgent actions while retaining traces.

**Coverage:** `complete`, `multiple_urgent`, `action_deduplication`, `integrated_action_plan`

**Applicable approved decisions:** `IP-CQ-001`, `IP-CQ-003`, `IP-CQ-004`, `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": true,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": false,
    "ear_pain": false,
    "pus_draining_from_ear": false,
    "tender_swelling_behind_ear": true
  },
  "encounter_id": "hpg-070-cross-multiple-urgent",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": true,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": true,
    "has_fever": true
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": true,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`, `SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE`, `VERY_SEVERE_FEBRILE_DISEASE`, `MASTOIDITIS`

**Final classifications:** `VERY_SEVERE_DISEASE`, `SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE`, `VERY_SEVERE_FEBRILE_DISEASE`, `MASTOIDITIS`

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_DIAZEPAM_IF_CONVULSING_NOW`, `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_DIAZEPAM_IF_CONVULSING_NOW`, `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT`, `GIVE_PARACETAMOL_FOR_EAR_PAIN`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-CONVULSING-NOW`, `IMCI-MSC-RESP-SEVERE-DANGER-SIGN`, `IMCI-MSC-FEVER-VERY-SEVERE`, `IMCI-MSC-EAR-MASTOIDITIS`

**Source provenance:**

- `IMCI-MSC-GDS-CONVULSING-NOW` — General danger signs; PDF page 5; printed page 1 of 76
- `IMCI-MSC-RESP-SEVERE-DANGER-SIGN` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-FEVER-VERY-SEVERE` — Fever; PDF page 8; printed page 4 of 76
- `IMCI-MSC-EAR-MASTOIDITIS` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-071-incomplete-entry-unknown

**Why:** One omitted pathway-entry answer remains UNKNOWN and blocks holistic synthesis.

**Coverage:** `incomplete`, `explicit_negative_omission_twin`, `single_omission`, `grouped_missing_elements`

**Applicable approved decisions:** `MSC-CQ-SCOPE-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "always_required",
    "fields": [
      "patient_facts.has_diarrhoea"
    ],
    "provenance_id": "HC-REQ-ALWAYS",
    "provenance_type": "COMPLETENESS_REQUIREMENT"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-071-incomplete-entry-unknown",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": null,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "supported_encounter": [
    "patient_facts.has_diarrhoea"
  ]
}
```

**Contradictions:** none

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-072-incomplete-multiple-groups

**Why:** Multiple omissions are grouped by supported assessment.

**Coverage:** `incomplete`, `multiple_omissions`, `grouped_missing_elements`

**Applicable approved decisions:** `IP-CQ-003`, `MSC-CQ-SCOPE-001`, `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "always_required",
    "fields": [
      "danger_signs.vomits_everything",
      "patient_facts.has_ear_problem"
    ],
    "provenance_id": "HC-REQ-ALWAYS",
    "provenance_type": "COMPLETENESS_REQUIREMENT"
  },
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[0]",
    "fields": [
      "respiratory.respiratory_rate"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-01",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "patient_facts.has_cough_or_difficult_breathing": true
    }
  },
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "conditional_requirements[6]",
    "fields": [
      "fever.malaria_risk"
    ],
    "provenance_id": "HC-REQ-CONDITIONAL-07",
    "provenance_type": "COMPLETENESS_REQUIREMENT",
    "trigger": {
      "patient_facts.has_fever": true
    }
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": null
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-072-incomplete-multiple-groups",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": null,
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": null,
    "has_fever": true
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": null,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** none

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "fever": [
    "fever.malaria_risk"
  ],
  "general_danger_signs": [
    "danger_signs.vomits_everything"
  ],
  "respiratory": [
    "respiratory.respiratory_rate"
  ],
  "supported_encounter": [
    "patient_facts.has_ear_problem"
  ]
}
```

**Contradictions:** none

**Fired rules:** none

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-073-incomplete-known-urgent

**Why:** Known convulsion triggers immediate urgent actions while missing assessment blocks final synthesis.

**Coverage:** `incomplete`, `urgent_incomplete`, `withhold_final_synthesis`, `grouped_missing_elements`

**Applicable approved decisions:** `IP-CQ-001`, `MSC-CQ-SCOPE-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "always_required",
    "fields": [
      "danger_signs.vomits_everything",
      "patient_facts.age_months",
      "patient_facts.has_cough_or_difficult_breathing",
      "patient_facts.has_diarrhoea",
      "patient_facts.has_ear_problem",
      "patient_facts.has_fever"
    ],
    "provenance_id": "HC-REQ-ALWAYS",
    "provenance_type": "COMPLETENESS_REQUIREMENT"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": true,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": null
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-073-incomplete-known-urgent",
  "fever": null,
  "patient_facts": {
    "age_months": null,
    "has_cough_or_difficult_breathing": null,
    "has_diarrhoea": null,
    "has_ear_problem": null,
    "has_fever": null
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`

**Final classifications:** withheld

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_DIAZEPAM_IF_CONVULSING_NOW`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "general_danger_signs": [
    "danger_signs.vomits_everything"
  ],
  "supported_encounter": [
    "patient_facts.age_months",
    "patient_facts.has_cough_or_difficult_breathing",
    "patient_facts.has_diarrhoea",
    "patient_facts.has_ear_problem",
    "patient_facts.has_fever"
  ]
}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-CONVULSING-NOW`

**Source provenance:**

- `IMCI-MSC-GDS-CONVULSING-NOW` — General danger signs; PDF page 5; printed page 1 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-074-incomplete-internal-classification-withheld

**Why:** A known pneumonia classification remains internal when another encounter entry is unknown.

**Coverage:** `incomplete`, `internal_classification`, `withhold_final_synthesis`

**Applicable approved decisions:** `IP-CQ-003`, `MSC-CQ-SCOPE-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "always_required",
    "fields": [
      "patient_facts.has_ear_problem"
    ],
    "provenance_id": "HC-REQ-ALWAYS",
    "provenance_type": "COMPLETENESS_REQUIREMENT"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-074-incomplete-internal-classification-withheld",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": null,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 45,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** `PNEUMONIA`

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{
  "supported_encounter": [
    "patient_facts.has_ear_problem"
  ]
}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-RESP-FAST-BREATHING-12-60M`, `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING`

**Source provenance:**

- `IMCI-MSC-RESP-FAST-BREATHING-12-60M` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-RESP-PNEUMONIA-FAST-BREATHING` — Cough or difficult breathing; PDF page 6; printed page 2 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-075-contradiction-drinking

**Why:** Unable drinking status contradicts a clinically established negative general danger sign.

**Coverage:** `incomplete`, `contradiction`, `cross_evidence`

**Applicable approved decisions:** `IP-CQ-002`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "contradictions_block_completion",
    "details": [
      "UNABLE observed drinking conflicts with a negative general danger sign"
    ],
    "fields": [],
    "provenance_id": "HC-CONTRADICTION-BLOCKS-COMPLETION",
    "provenance_type": "EVIDENCE_VALIDITY_REQUIREMENT"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "UNABLE",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": null,
  "encounter_id": "hpg-075-contradiction-drinking",
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": true,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `False` / `False`

**Urgent action required:** `False`

**Internal classifications:** `NO_DEHYDRATION`

**Final classifications:** withheld

**Urgent actions:** none

**Intermediate actions:** none

**Deferred actions:** none

**Final actions:** withheld

**Grouped missing elements:**

```json
{}
```

**Contradictions:** UNABLE observed drinking conflicts with a negative general danger sign

**Fired rules:** `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`

**Source provenance:**

- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-076-complete-danger-plus-all-pathways

**Why:** Urgent finding leads while the complete holistic assessment retains all simultaneous classifications and defers routine actions.

**Coverage:** `complete`, `urgent`, `all_pathways`, `deferred_routine_actions`, `holistic_assessment_after_danger`

**Applicable approved decisions:** `IP-CQ-001`, `IP-CQ-003`, `IP-CQ-004`, `MSC-CQ-FEVER-001`, `MSC-CQ-FEVER-003`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": true
  },
  "diarrhoea": {
    "blood_in_stool": false,
    "cholera_in_area": null,
    "dehydration": {
      "drinking_status": "NORMAL",
      "restless_or_irritable": false,
      "skin_pinch": "NORMAL",
      "sunken_eyes": false
    },
    "duration_days": 3,
    "post_rehydration": null,
    "rehydration_stage": null
  },
  "ear": {
    "ear_discharge_duration_days": null,
    "ear_discharge_reported": false,
    "ear_pain": false,
    "pus_draining_from_ear": false,
    "tender_swelling_behind_ear": false
  },
  "encounter_id": "hpg-076-complete-danger-plus-all-pathways",
  "fever": {
    "clouding_of_cornea": null,
    "fever_duration_days": 2,
    "fever_present_every_day": null,
    "generalized_rash": false,
    "identified_bacterial_cause_present": false,
    "malaria_risk": "HIGH",
    "malaria_test_available": true,
    "malaria_test_result": "NEGATIVE",
    "measles_cough": false,
    "measles_within_last_3_months": false,
    "mouth_ulcers": null,
    "mouth_ulcers_deep_or_extensive": null,
    "obvious_cause_of_fever_present": false,
    "pus_draining_from_eye": null,
    "red_eyes": false,
    "runny_nose": false,
    "stiff_neck": false,
    "temperature_c": 38.0
  },
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": true,
    "has_ear_problem": true,
    "has_fever": true
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  },
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Complete / final synthesis authorized:** `True` / `True`

**Urgent action required:** `True`

**Internal classifications:** `VERY_SEVERE_DISEASE`, `SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE`, `NO_DEHYDRATION`, `VERY_SEVERE_FEBRILE_DISEASE`, `NO_EAR_INFECTION`

**Final classifications:** `VERY_SEVERE_DISEASE`, `SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE`, `NO_DEHYDRATION`, `VERY_SEVERE_FEBRILE_DISEASE`, `NO_EAR_INFECTION`

**Urgent actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Intermediate actions:** none

**Deferred actions:** `ADVISE_WHEN_TO_RETURN_IMMEDIATELY`, `FOLLOW_UP_5_DAYS_IF_NOT_IMPROVING`, `GIVE_FLUID_ZINC_AND_FOOD_PLAN_A`, `NO_EAR_TREATMENT`

**Final actions:** `COMPLETE_ASSESSMENT_QUICKLY`, `GIVE_FIRST_DOSE_APPROPRIATE_ANTIBIOTIC`, `GIVE_FIRST_DOSE_SEVERE_MALARIA_TREATMENT`, `GIVE_PRE_REFERRAL_TREATMENT_IMMEDIATELY`, `KEEP_WARM`, `PREVENT_LOW_BLOOD_SUGAR`, `URGENT_REFERRAL`

**Grouped missing elements:**

```json
{}
```

**Contradictions:** none

**Fired rules:** `IMCI-MSC-GDS-VOMITS-EVERYTHING`, `IMCI-MSC-RESP-SEVERE-DANGER-SIGN`, `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION`, `IMCI-MSC-FEVER-VERY-SEVERE`, `IMCI-MSC-EAR-NO-INFECTION`

**Source provenance:**

- `IMCI-MSC-GDS-VOMITS-EVERYTHING` — General danger signs; PDF page 5; printed page 1 of 76
- `IMCI-MSC-RESP-SEVERE-DANGER-SIGN` — Cough or difficult breathing; PDF page 6; printed page 2 of 76
- `IMCI-MSC-DIARRHOEA-NO-DEHYDRATION` — Diarrhoea - dehydration; PDF page 7; printed page 3 of 76
- `IMCI-MSC-FEVER-VERY-SEVERE` — Fever; PDF page 8; printed page 4 of 76
- `IMCI-MSC-EAR-NO-INFECTION` — Ear problem; PDF page 9; printed page 5 of 76

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-077-out-of-scope-age-1

**Why:** Young infant is outside the supported major sick-child schema.

**Coverage:** `out_of_scope`, `schema_rejection`, `age_boundary`

**Applicable approved decisions:** `MSC-CQ-SCOPE-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "population.age_months",
    "fields": [
      "patient_facts.age_months"
    ],
    "provenance_id": "HC-SCOPE-AGE-2-59",
    "provenance_type": "SCOPE_BOUNDARY"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-077-out-of-scope-age-1",
  "fever": null,
  "patient_facts": {
    "age_months": 1,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Expected result:** `SCHEMA_REJECTION`

**Expected error:** age_months must be at least 2 and less than 60

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance

### hpg-078-out-of-scope-age-60

**Why:** Child aged 60 months is outside the supported major sick-child schema.

**Coverage:** `out_of_scope`, `schema_rejection`, `age_boundary`

**Applicable approved decisions:** `MSC-CQ-SCOPE-001`

**Applicable product-policy dispositions:** none

**Non-firing requirement / scope provenance:**

```json
[
  {
    "artifact_id": "imci-major-sick-child-holistic-completeness-v2",
    "artifact_path": "configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json",
    "artifact_section": "population.age_months",
    "fields": [
      "patient_facts.age_months"
    ],
    "provenance_id": "HC-SCOPE-AGE-2-59",
    "provenance_type": "SCOPE_BOUNDARY"
  }
]
```

**Structured input:**

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "encounter_id": "hpg-078-out-of-scope-age-60",
  "fever": null,
  "patient_facts": {
    "age_months": 60,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null,
  "schema_version": "edge-imci-major-sick-child-encounter-v1"
}
```

**Expected result:** `SCHEMA_REJECTION`

**Expected error:** age_months must be at least 2 and less than 60

**Source provenance:**

- No clinical rule fired; review against the pinned scope/completeness policy.

**Review:** [ ] input facts  [ ] completeness/withholding  [ ] classifications  [ ] actions  [ ] trace/provenance


## Review instructions

Treat these semantic targets as immutable. If a genuine semantic defect is discovered, open change control and create a new reviewed version rather than silently editing the frozen suite.

Golden-language rendering and controlled teacher/prompt evaluation are now authorized. Bulk synthetic generation and training remain separate gated stages.
