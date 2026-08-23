# Full language review — case-by-case report on product_holistic_golden_language_review_v1.md

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `SUPERSEDED` · Pre-format review evidence retained for audit; it cannot alter frozen semantics.
>
> 78 records reviewed: 16 frozen style anchors + 62 draft records.  
> Frozen semantic source hash: `9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f` (VERIFIED).
> Reviewed language-renderings hash: `9840b57e5e7b21193d7d5596de7cf1b574285fae280c5f8365cafd3d637f7dbe` (PINNED AFTER REVIEW).

## Subsequent disposition

The project owner accepted the recommendation to standardize canonical outputs for post-training. `LGR-FR-001` and `LGR-FR-002` are addressed by the versioned `edge-imci-response-grammar-v1` policy: all complete, urgent-complete, incomplete, urgent-incomplete, and out-of-scope responses use deterministic state-specific headings and bullets, and `hpg-001` no longer uses “these pathways.”

The reviewed artifact above remains preserved as pre-format evidence. The reformatted 78-case layer receives a new hash and returns to review; this report does not approve or freeze that subsequent artifact.

## Method

Each record was checked against its frozen semantic case across all nine review dimensions. An automated cross-check compared every review record's state, urgency, classifications, actions, deferred actions, and missing elements against the structured semantic target. Formatting consistency between frozen and draft records was also checked. All automated findings were then manually reviewed to distinguish true defects from false positives.

---

## Summary

| Dimension | Pass | Fail | Notes |
|---|---|---|---|
| Semantic faithfulness | 78 | 0 | All records match frozen semantics |
| Natural PHC-worker input language | 78 | 0 | All submissions use natural clinical phrasing |
| Clear EdgeIMCI responses | 76 | 2 | Two formatting inconsistency findings |
| Urgent actions appearing first | 78 | 0 | All urgent cases lead with URGENT: prefix |
| Urgent vs non-urgent referral distinction | 78 | 0 | Correctly distinguished throughout |
| Missing-information requests | 78 | 0 | Properly grouped, unknown-not-negative stated |
| Complete integrated treatment plans | 78 | 0 | All actions from semantics are present |
| Absence of internal identifiers | 77 | 1 | One borderline case (hpg-001) |
| No invented clinical details | 78 | 0 | Nothing invented beyond frozen semantics |

**Overall: PASS with minor formatting notes.**

---

## Findings

### LGR-FR-001 — Formatting inconsistency between frozen and draft records

- **Severity:** MINOR
- **Affected records:** 49 draft records use `Management:` header + bullet lists; 15 frozen records use prose paragraphs without headers
- **Description:** The 62 draft records predominantly use a structured format (`Classification:` / `Management:` / bullet list), while the 16 frozen style anchors predominantly use continuous prose. This is a stylistic split, not a semantic defect. Both styles are readable and clinically correct.
- **Recommendation:** Before freezing the full 78-record language layer, decide on one house style. The structured format (headers + bullets) is more scannable for a frontline worker under time pressure. If you choose that style, the 15 frozen prose records (hpg-001, hpg-008, hpg-014, hpg-016, hpg-020, hpg-028, hpg-031, hpg-052, hpg-055, hpg-070, hpg-071, hpg-073, hpg-075, hpg-077, and one more) would need reformatting. If you keep the prose style for single-pathway cases and use structured format only for multi-pathway cases, document that rule.
- **Status:** OPEN — style decision needed before language freeze

### LGR-FR-002 — "these pathways" in hpg-001 response

- **Severity:** MINOR (borderline — acceptable for hackathon scope)
- **Affected record:** `hpg-001-all-negative`
- **Exact wording:** "no management action is indicated by these pathways"
- **Description:** "These pathways" refers to the IMCI clinical assessment areas (respiratory, diarrhoea, fever, ear). A PHC worker would understand this as the clinical assessment domains, not as internal schema language. It is borderline because "pathways" is also the internal term for the assessment pipeline stages. However, in context it reads naturally — "nothing in the assessment pathways requires action."
- **Recommendation:** If you want to be strict, change to "no management action is indicated." If you're comfortable with it, leave it — it's natural enough for hackathon scope.
- **Status:** OPEN — minor optional edit

### LGR-FR-003 — hpg-068 frozen record already uses structured format

- **Severity:** INFORMATION
- **Affected record:** `hpg-068-cross-four-pathways`
- **Description:** This is the one frozen record that already uses the `Management:` header + bullet list format (with pathway-grouped bullets). This is actually the best-formatted record in the entire suite for a frontline worker — it groups actions by pathway, making six classifications and fourteen actions scannable. This could serve as the template if you adopt the structured format as house style.
- **Status:** Noted — potential style template

---

## Case-by-case review

### General danger signs (hpg-002 through hpg-006)

| Case | Semantic | Input language | Response clarity | Urgent first | Referral distinction | Missing info | Integrated plan | No internal IDs | No invention | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| hpg-002 | PASS | PASS | PASS | PASS | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-003 | PASS | PASS | PASS | PASS | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-004 | PASS | PASS | PASS | PASS | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-005 | PASS | PASS | PASS | PASS | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-006 | PASS | PASS | PASS | PASS | N/A | N/A | PASS | PASS | PASS | READY |

All five danger-sign cases correctly lead with "URGENT: Act now and do not delay referral." hpg-006 correctly adds diazepam for active convulsions. All list the same pre-referral package (complete assessment quickly, give pre-referral treatment, keep warm, prevent low blood sugar, arrange urgent referral). No issues.

### Respiratory — cough/difficult breathing (hpg-007 through hpg-026)

| Case | Semantic | Input language | Response clarity | Urgent first | Referral distinction | Missing info | Integrated plan | No internal IDs | No invention | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| hpg-007 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-008 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-009 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-010 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-011 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-012 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-013 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-014 | PASS | PASS | PASS | N/A | PASS | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-015 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-016 | PASS | PASS | PASS | N/A | PASS | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-017 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-018 | PASS | PASS | PASS | N/A | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-019 | PASS | PASS | PASS | N/A | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-020 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-021 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-022 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |
| hpg-023 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |
| hpg-024 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |
| hpg-025 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |
| hpg-026 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |

Key observations:
- **hpg-014** (HIV-positive, chest indrawing): Correctly says "This finding alone calls for referral, not urgent referral" — the non-urgent referral distinction is explicit and clear.
- **hpg-015** (stridor): Correctly classified as severe pneumonia, urgent referral. Two actions only (first dose antibiotic + urgent referral) — matches semantics.
- **hpg-016** (SpO2 89.9%): Correctly says "Refer the child because the oxygen saturation is below 90%. This finding alone calls for referral, not urgent referral." Non-urgent referral reason stated.
- **hpg-017** (SpO2 90.0%): Correctly classified as cough or cold with no referral — 90% is the threshold, and at exactly 90% there is no referral. Matches semantics.
- **hpg-020** (post-bronchodilator improved): Correctly acknowledges completed trial and uses post-treatment findings. The semantic action `GIVE_RAPID_ACTING_INHALED_BRONCHODILATOR_TRIAL` is acknowledged in past tense — this is correct behavior, not a missing action.
- **hpg-021** (post-bronchodilator fast): Correctly lists both the trial/reassessment actions and the pneumonia treatment. All seven semantic actions present.
- **hpg-022 through hpg-026** (incomplete respiratory): All correctly state they cannot provide final classifications, list specific missing checks. hpg-023 and hpg-024 correctly flag conflicting/invalid findings (child not calm, count not one minute).

### Diarrhoea (hpg-027 through hpg-040)

| Case | Semantic | Input language | Response clarity | Urgent first | Referral distinction | Missing info | Integrated plan | No internal IDs | No invention | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| hpg-027 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-028 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-029 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-030 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-031 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-032 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-033 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-034 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-035 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-036 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-037 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-038 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |
| hpg-039 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |
| hpg-040 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |

Key observations:
- **hpg-034** (severe persistent diarrhoea): Correctly urgent. Says "Refer the child to hospital" and "Treat dehydration before referral unless another severe classification prevents this." Deferred actions correctly noted. Matches semantics.
- **hpg-037** (unable to drink + severe dehydration): Correctly urgent with both very severe disease and severe dehydration. Includes ORS sips and continue breastfeeding during referral — matches semantics.
- **hpg-038** (drinking response not observed): Correctly incomplete. Asks to "Offer fluid and observe whether the child drinks normally, eagerly or thirstily, poorly, or is unable to drink." Specific and actionable.
- **hpg-039** (duration unknown): Correctly incomplete. Asks for duration in days.
- **hpg-040** (cholera context unknown): Correctly incomplete. Asks to confirm cholera presence in area.

### Fever (hpg-041 through hpg-060)

| Case | Semantic | Input language | Response clarity | Urgent first | Referral distinction | Missing info | Integrated plan | No internal IDs | No invention | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| hpg-041 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-042 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-043 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-044 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-045 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-046 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-047 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-048 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-049 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-050 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-051 | PASS | PASS | PASS | N/A | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-052 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-053 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-054 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-055 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-056 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-057 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-058 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-059 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |
| hpg-060 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |

Key observations:
- **hpg-043** (test unavailable, high-risk): Correctly classifies as malaria and gives antimalarial — in high-risk areas with no test, treat as malaria. Matches semantics.
- **hpg-046** (no malaria risk): Correctly classifies as "Fever" (not "Fever—no malaria") with 2-day follow-up. Matches semantics — the "no malaria" suffix only applies when malaria risk exists.
- **hpg-048** (38.5°C): Correctly adds paracetamol for high fever (≥38.5°C). hpg-047 (38.4°C) correctly does not. Matches semantics.
- **hpg-051** (8 days, every day): Correctly adds "Refer for assessment of prolonged fever." hpg-050 (8 days, not every day) correctly does not. Matches semantics.
- **hpg-055** (severe complicated measles): Correctly urgent. Pre-referral actions (vitamin A, antibiotic, tetracycline eye ointment) listed before deferral note. Matches semantics.
- **hpg-056** (stiff neck): Correctly urgent with very severe febrile disease. First dose antibiotic + first dose severe malaria treatment + prevent low blood sugar + urgent referral. Matches semantics.

### Ear problems (hpg-061 through hpg-067)

| Case | Semantic | Input language | Response clarity | Urgent first | Referral distinction | Missing info | Integrated plan | No internal IDs | No invention | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| hpg-061 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-062 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-063 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-064 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-065 | PASS | PASS | PASS | N/A | N/A | N/A | PASS | PASS | PASS | READY |
| hpg-066 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-067 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |

Key observations:
- **hpg-061** (no ear infection): Correctly says "No ear treatment is indicated." Matches semantics.
- **hpg-063** (discharge 13 days) vs **hpg-064** (discharge 14 days): 13 days = acute, 14 days = chronic. hpg-064 correctly uses topical quinolone eardrops for 14 days instead of oral antibiotic. Matches semantics.
- **hpg-065** (observed pus, no caregiver history): Correctly classified as acute ear infection based on observed pus. Matches semantics.
- **hpg-066** (mastoiditis): Correctly urgent with urgent referral. Matches semantics.

### Cross-pathway and edge cases (hpg-068 through hpg-078)

| Case | Semantic | Input language | Response clarity | Urgent first | Referral distinction | Missing info | Integrated plan | No internal IDs | No invention | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| hpg-068 | PASS | PASS | PASS (structured) | N/A | N/A | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-069 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-070 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY (frozen) |
| hpg-071 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY (frozen) |
| hpg-072 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY (frozen) |
| hpg-073 | PASS | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | READY (frozen) |
| hpg-074 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY |
| hpg-075 | PASS | PASS | PASS | N/A | N/A | PASS | N/A | PASS | PASS | READY (frozen) |
| hpg-076 | PASS | PASS | PASS | PASS | PASS | N/A | PASS | PASS | PASS | READY |
| hpg-077 | PASS | PASS | PASS | N/A | N/A | N/A | N/A | PASS | PASS | READY (frozen) |
| hpg-078 | PASS | PASS | PASS | N/A | N/A | N/A | N/A | PASS | PASS | READY |

Key observations:
- **hpg-068** (four pathways): Best-formatted record in the suite. Groups actions by pathway under bullet headings. All six classifications and fourteen actions present. Matches semantics.
- **hpg-069** (severe dehydration + mastoiditis): Correctly urgent. Includes ORS sips and continue breastfeeding for dehydration, plus antibiotic and paracetamol for mastoiditis, plus urgent referral. Matches semantics.
- **hpg-070** (multiple urgent): Correctly urgent. Diazepam first (active convulsions), then antibiotic, severe malaria treatment, paracetamol, pre-referral treatment, keep warm, prevent low blood sugar, complete assessment quickly, urgent referral. All nine semantic actions present. Matches semantics.
- **hpg-073** (incomplete known urgent): Correctly leads with urgent treatment (diazepam, pre-referral, prevent low blood sugar, keep warm, urgent referral) before requesting remaining assessment. Matches semantics.
- **hpg-074** (incomplete, ear missing): Correctly incomplete. Only asks for ear problem status — the respiratory assessment is complete but the encounter cannot be finalized without ear assessment. Matches semantics.
- **hpg-075** (contradiction): Correctly identifies the conflict between "able to drink" (danger signs) and "unable to drink" (diarrhoea). Says "Do not choose one result or issue a final classification yet." Matches semantics.
- **hpg-076** (danger sign + all pathways): Correctly urgent. Five classifications including "No dehydration" and "No ear infection" — negative classifications are correctly included. Deferred actions noted. Matches semantics.
- **hpg-077** (age 1 month): Correctly rejected. Says "outside the supported EdgeIMCI major sick-child scope, which starts at 2 completed months." Directs to young-infant pathway. Matches semantics.
- **hpg-078** (age 60 months): Correctly rejected. Same scope statement, directs to age-specific pathway. Matches semantics.

---

## Cross-cutting observations

### Formatting split (LGR-FR-001)

The most visible issue is the formatting split between frozen and draft records:

- **Frozen records (16):** 15 use continuous prose, 1 uses structured format (hpg-068)
- **Draft records (62):** 49 use `Management:` header + bullets, 13 use prose (the 12 incomplete records + hpg-078)

The 13 draft records without `Management:` headers are all INCOMPLETE or SCHEMA_REJECTION cases — they don't have management plans to list, so the header would be inappropriate. This is actually consistent behavior: structured format when there are actions to list, prose when there aren't.

The real split is: frozen COMPLETE records use prose, draft COMPLETE records use structured format. That's the inconsistency to resolve.

### "Pathway" language (LGR-FR-002)

Only one record uses "pathways" in the response — hpg-001. It's borderline acceptable but could be cleaned up.

### Deferred actions

All records with deferred actions (hpg-034, hpg-055, hpg-076) correctly include deferral language: "Routine home-care counselling and scheduled follow-up are deferred so they do not delay or compete with the urgent referral workflow." This is consistent and clear.

### Unknown-not-negative principle

All incomplete records correctly state or imply that an unmentioned answer cannot be treated as "no." hpg-071 states it explicitly: "An unmentioned answer cannot be treated as no." Others embed it in the request structure (e.g., "Ask the caregiver whether..." rather than "Confirm if...").

### Urgent action ordering

All urgent cases lead with "URGENT:" prefix. In hpg-073 (incomplete known urgent), the urgent treatment is given before the remaining assessment request — correct priority. In hpg-070, diazepam is mentioned first because the child is actively convulsing — correct clinical priority.

---

## Overall recommendation

**PASS.** All 78 records are semantically faithful to the frozen semantic suite. No clinical content was invented, dropped, or altered. No internal identifiers or engineering language are exposed (one borderline case in hpg-001). Urgent actions consistently appear first. Non-urgent and urgent referrals are correctly distinguished. Missing-information requests are properly grouped and actionable.

The only open items are:
1. **Formatting consistency** — decide on one house style before freezing the full language layer (LGR-FR-001)
2. **"these pathways"** in hpg-001 — optional minor edit (LGR-FR-002)

Neither blocks hackathon use. Both should be resolved before the language layer is frozen for training.
