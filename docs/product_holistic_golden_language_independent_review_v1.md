# Product holistic golden language calibration — independent language review v1

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Independent language and interaction review; cannot alter frozen clinical or semantic authority.

## Target hashes and verification

| Target | SHA-256 | Result |
|---|---|---|
| `data/golden/holistic_product_v1/language_calibration_v1.jsonl` | `4e05eae23aa7cc4a9371925035ee46564debf6bb004900fd37a4fefe606256b9` | VERIFIED |
| `data/golden/holistic_product_v1/semantic_cases.jsonl` | `9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f` | VERIFIED |

Both hashes match the values required by the review instructions. The calibration file contains exactly 16 records. No hash mismatch was detected.

## Subsequent disposition

Both minor findings were remediated before project-owner approval:

- `LGR-IR-001`: the `hpg-068` management plan was grouped by condition for readability;
- `LGR-IR-002`: the internal “mastoiditis pathway” reference was removed from `hpg-070`.

The remediated calibration was frozen at SHA-256 `b42659143270e8ef732593598fc3c7eeb6d9fb6805eaa03a0f93801d76c97fbb`. The controlled transition and bounded permissions are recorded in `product_holistic_golden_language_approval_v1.md`. This subsequent note does not alter the original review findings against the pinned pre-freeze hash.

## Reviewer identity and independence

- **Reviewer type:** Independent coding agent, distinct from the agent that authored the calibration drafts and the prior technical/editorial review.
- **Independence statement:** This review was performed by comparing each calibration record against the frozen semantic target and the approved product-policy documents. It does not reuse the prior technical review's findings or dispositions. The reviewer has no authority to modify frozen semantics, clinical rules, or approved decisions.
- **Limitation:** This is an automated language and interaction review against repository-authorized semantics. It is not a qualified PHC-worker field review and does not claim to be one.

## Method and authority boundary

### Required reading

The following files were read before reviewing any case:

1. `docs/README.md`
2. `docs/interaction_design_retrieval_assessment_bundles.md`
3. `docs/golden_language_rendering_contract_v1.md`
4. `docs/product_holistic_golden_approval_v1.md`
5. `data/golden/holistic_product_v1/manifest.json`
6. `data/golden/holistic_product_v1/semantic_cases.jsonl`
7. `configs/rendering/holistic_golden_language_record_v1.schema.json`
8. `data/golden/holistic_product_v1/language_calibration_manifest_v1.json`
9. `docs/product_holistic_golden_language_calibration_review_v1.md`
10. `docs/product_holistic_golden_language_technical_review_v1.md`

### Review method

For each of the 16 calibration records, the reviewer:

- verified the pinned semantic source hash and case linkage;
- compared the PHC-worker submission against the frozen structured input, checking that explicit negatives and unknowns were preserved;
- compared the EdgeIMCI response against the frozen semantic target for classifications, actions, deferred actions, missing elements, contradictions, and scope rejection;
- assessed interaction quality against the rendering contract and product policy;
- assessed PHC suitability for concise, actionable, natural frontline-worker language; and
- recorded any suspected semantic defect separately from language-only findings.

### Authority boundary

The frozen semantic cases decide classifications, actions, urgency, missing elements, contradictions, and scope rejection. This review may only disposition language and interaction quality. Any suspected clinical error in the frozen target was recorded as `POSSIBLE_SEMANTIC_DEFECT_REQUIRES_CHANGE_CONTROL`; none were found.

## Findings

### LGR-IR-001 — hpg-068 integrated response is long and lacks visual grouping

- **Severity:** MINOR
- **Affected case(s):** `hpg-068-cross-four-pathways`
- **Review dimension:** PHC suitability
- **Exact problematic wording:** The entire assistant response is presented as two dense paragraphs without headings, bullets, or pathway grouping.
- **Frozen semantic target or product-policy requirement involved:** The case has six simultaneous classifications and fourteen integrated actions. The rendering contract requires integrated-plan coherence and action deduplication; it also asks for concise, actionable, and low-memory-burden wording.
- **Why the wording fails:** A frontline worker reading the response must parse six classifications and fourteen actions from continuous prose. While every item is present, the lack of grouping increases memory burden and the risk that an action is missed.
- **Proposed language-only correction:** Retain all content but present it under pathway headings or a short bulleted plan, e.g.:
  - Pneumonia: oral amoxicillin 5 days, soothe throat/relieve cough, follow up in 3 days.
  - Diarrhoea: Plan A fluid/zinc/food; dysentery: ciprofloxacin 3 days.
  - Fever: first-line oral antimalarial, vitamin A; ear infection: antibiotic 5 days, paracetamol, dry ear by wicking.
  - Follow-up and return advice as applicable.
- **Status:** OPEN

### LGR-IR-002 — hpg-070 contains residual pathway-reference language

- **Severity:** MINOR
- **Affected case(s):** `hpg-070-cross-multiple-urgent`
- **Review dimension:** PHC suitability
- **Exact problematic wording:** "give paracetamol for ear pain as indicated by the mastoiditis pathway"
- **Frozen semantic target or product-policy requirement involved:** The rendering contract prohibits exposing internal schema, enum, rule-ID, and pipeline language to the PHC worker. The action itself (`GIVE_PARACETAMOL_FOR_EAR_PAIN`) is a source-backed action.
- **Why the wording fails:** "the mastoiditis pathway" is an internal classification label, not a phrase a PHC worker needs to hear. It does not add clinical meaning and slightly weakens the natural frontline voice.
- **Proposed language-only correction:** "give paracetamol for ear pain"
- **Status:** OPEN

## Per-case disposition table

| Case | State | Semantic faithfulness | Interaction quality | PHC suitability | Finding IDs | Case recommendation |
|---|---|---|---|---|---|---|
| `hpg-001-all-negative` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-008-resp-age-2-rate-50` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-014-resp-chest-hiv-positive` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-016-resp-oximeter-89-9` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-020-resp-post-bronchodilator-improved` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-028-diarrhoea-some-dehydration` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-031-diarrhoea-severe-age-24-cholera` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-052-fever-identified-bacterial-cause` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-055-fever-severe-measles-cornea` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-068-cross-four-pathways` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | LGR-IR-001 | READY_AFTER_MINOR_REMEDIATION |
| `hpg-070-cross-multiple-urgent` | COMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | LGR-IR-002 | READY_AFTER_MINOR_REMEDIATION |
| `hpg-071-incomplete-entry-unknown` | INCOMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-072-incomplete-multiple-groups` | INCOMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-073-incomplete-known-urgent` | INCOMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-075-contradiction-drinking` | INCOMPLETE | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |
| `hpg-077-out-of-scope-age-1` | SCHEMA_REJECTION | PASS | PASS | PASS_FOR_HACKATHON_CALIBRATION | — | READY |

## Totals by disposition and severity

### Disposition counts

| Dimension | PASS / PASS_FOR_HACKATHON_CALIBRATION | FAIL / FAIL_NEEDS_LANGUAGE_REMEDIATION | POSSIBLE_SEMANTIC_DEFECT |
|---|---|---|---|
| Semantic faithfulness | 16 | 0 | 0 |
| Interaction quality | 16 | 0 | — |
| PHC suitability | 16 | 0 | — |

### Severity counts

| Severity | Count |
|---|---|
| BLOCKING | 0 |
| MAJOR | 0 |
| MINOR | 2 |

### Case recommendation counts

| Recommendation | Count |
|---|---|
| READY | 14 |
| READY_AFTER_MINOR_REMEDIATION | 2 |
| NOT_READY | 0 |

## Remaining limitations

1. This review is an independent automated language review against frozen repository semantics. It is not a qualified PHC-worker field validation.
2. The two MINOR findings are polish and grouping suggestions; they do not indicate semantic error or unsafe clinical wording.
3. No possible semantic defects were identified. All 16 records remain aligned with the frozen semantic-suite hash.
4. The calibration manifest still blocks training, product evaluation, teacher bake-off, and production clinical use until the language layer receives its own approval/freeze step.

## Overall recommendation

`READY_AFTER_LANGUAGE_REMEDIATION`

The frozen semantics remain sound across all 16 cases. All records pass semantic faithfulness and interaction quality. Two MINOR language polish items should be addressed before the language layer is approved for human language sign-off: visual grouping for `hpg-068` and removal of the internal pathway reference in `hpg-070`. Once those are remediated, the calibration is ready for human language approval.
