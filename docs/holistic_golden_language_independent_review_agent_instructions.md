# EdgeIMCI holistic golden language calibration — independent review agent instructions

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `SUPERSEDED` · This handoff was executed against its pinned pre-freeze hash and is retained as an audit record.

> **Do not execute this handoff again against the current calibration file.** Its recorded review-target hash is the pre-freeze language content. The resulting review is in `product_holistic_golden_language_independent_review_v1.md`; its two minor findings were remediated before the subsequent project-owner approval and controlled freeze recorded in `product_holistic_golden_language_approval_v1.md`.

## Assignment

Perform an independent, case-by-case language review of the 16-record EdgeIMCI holistic golden language calibration.

Do not generate dataset variants, teacher outputs, splits, training records, or model prompts. Do not edit the frozen semantic suite, clinical rules, completeness policy, approved decisions, language calibration, generator, schema, tests, or existing review records.

Your task is review and disposition only.

## Exact review target

Review this canonical file:

```text
data/golden/holistic_product_v1/language_calibration_v1.jsonl
```

Its required SHA-256 is:

```text
4e05eae23aa7cc4a9371925035ee46564debf6bb004900fd37a4fefe606256b9
```

It contains exactly 16 records and must remain pinned to frozen semantic SHA-256:

```text
9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f
```

If either hash differs, stop and report `REVIEW_TARGET_HASH_MISMATCH`. Do not review a moving or regenerated target.

## Required reading

Read these files before reviewing any case:

1. `docs/README.md` — authority and lifecycle rules.
2. `docs/interaction_design_retrieval_assessment_bundles.md` — current product interaction policy.
3. `docs/golden_language_rendering_contract_v1.md` — proposed language contract.
4. `docs/product_holistic_golden_approval_v1.md` — semantic approval and freeze boundary.
5. `data/golden/holistic_product_v1/manifest.json` — frozen semantic manifest.
6. `data/golden/holistic_product_v1/semantic_cases.jsonl` — exact semantic targets for the 16 linked case IDs.
7. `configs/rendering/holistic_golden_language_record_v1.schema.json` — language record contract.
8. `data/golden/holistic_product_v1/language_calibration_manifest_v1.json` — language lifecycle and permissions.
9. `docs/product_holistic_golden_language_calibration_review_v1.md` — readable case-by-case review surface.
10. `docs/product_holistic_golden_language_technical_review_v1.md` — prior same-agent technical/editorial findings and explicit limitations.

The earlier technical review is evidence, not a result you should copy. Independently compare each user submission and proposed response with the frozen target.

## Authority boundary

The frozen semantics decide:

- completeness and final-synthesis authorization;
- classifications;
- urgent, intermediate, deferred, and final actions;
- missing elements;
- contradictions;
- acquisition modes; and
- scope rejection.

The language layer may decide:

- wording and tone;
- organization and prioritization;
- whether related requests are expressed clearly as a group;
- whether the response sounds natural and useful to a PHC worker; and
- whether the free-form submission expresses the structured evidence without adding or hiding meaning.

If you suspect that a frozen classification or action is clinically wrong, record `POSSIBLE_SEMANTIC_DEFECT_REQUIRES_CHANGE_CONTROL`. Do not repair it by changing the proposed wording or substituting your own medical knowledge.

Do not introduce medical rules from general knowledge. Review only against repository-authorized semantics and sources.

## Required review dimensions

For every case, disposition all three dimensions separately.

### 1. Semantic faithfulness

Check both directions:

- Does the PHC-worker submission faithfully express the frozen structured input, including required explicit negatives and unknowns?
- Does the EdgeIMCI response express every frozen classification, action, urgency state, deferral, missing element, contradiction, or scope rejection without adding unsupported clinical content?

Use one of:

- `PASS`
- `FAIL`
- `POSSIBLE_SEMANTIC_DEFECT_REQUIRES_CHANGE_CONTROL`

Semantic faithfulness is a hard gate.

### 2. Interaction quality

Check whether the response:

- leads with urgent action when required;
- keeps referral distinct from urgent referral;
- withholds the completed answer when the assessment is incomplete;
- requests all and only the necessary missing observations;
- groups related acquisitions usefully;
- speaks directly to the PHC worker rather than to a dataset author;
- integrates simultaneous classifications and actions coherently; and
- avoids internal schema, enum, rule-ID, and pipeline language.

Use `PASS` or `FAIL`.

### 3. PHC suitability

Assess whether the wording is concise, understandable, actionable, and plausible for the intended frontline-worker interaction. Identify unnecessary verbosity, ambiguous instructions, awkward phrasing, or excessive memory burden.

This is a language/usability judgment, not production field validation. Do not describe it as PHC-worker validation unless an actual qualified PHC reviewer performed it.

Use:

- `PASS_FOR_HACKATHON_CALIBRATION`
- `FAIL_NEEDS_LANGUAGE_REMEDIATION`
- `REQUIRES_QUALIFIED_PHC_REVIEW`

## Required case-specific attention

Pay particular attention to:

- `hpg-001`: whether a no-classification/no-action result is clear without sounding like broad medical reassurance.
- `hpg-014` and `hpg-016`: whether non-urgent referral is unmistakable without burying the referral action.
- `hpg-020`: whether completed bronchodilator treatment and post-treatment classification are temporally clear.
- `hpg-028` and `hpg-031`: whether initial Plan B/C management and later reassessment remain distinct without inventing longitudinal state.
- `hpg-031` and `hpg-052`: whether generic protocol wording avoids fabricated drugs or regimens while remaining actionable.
- `hpg-055`: whether urgent referral and pre-referral treatment lead while deferred routine actions do not compete.
- `hpg-068`: whether the integrated multi-pathway plan is coherent rather than a difficult-to-use list.
- `hpg-070`: whether the multiple urgent actions are prioritized and deduplicated, and whether any concern is a language issue or a possible frozen-semantic issue.
- `hpg-071` and `hpg-072`: whether unknown observations are requested precisely and efficiently.
- `hpg-073`: whether urgent action is immediate while rapid completion of the remaining assessment is still clear.
- `hpg-075`: whether the contradiction is resolved through clinician reassessment rather than guessing.
- `hpg-077`: whether the scope rejection avoids unsupported clinical synthesis.

## Finding format

Every finding must include:

- finding ID, such as `LGR-IR-001`;
- severity: `BLOCKING`, `MAJOR`, or `MINOR`;
- affected case ID(s);
- review dimension;
- exact problematic wording;
- the frozen semantic target or product-policy requirement involved;
- why the wording fails;
- a proposed language-only correction, unless semantic change control is required; and
- status `OPEN`.

Do not edit the target calibration while reviewing it.

## Required deliverables

Create only these two files:

```text
docs/product_holistic_golden_language_independent_review_v1.md
docs/product_holistic_golden_language_independent_review_v1.csv
```

The Markdown review must include:

1. exact target hashes and verification result;
2. reviewer identity/type and independence statement;
3. method and authority boundary;
4. every finding;
5. a 16-row per-case disposition table;
6. totals by disposition and severity;
7. remaining limitations; and
8. exactly one overall recommendation:
   - `READY_FOR_HUMAN_LANGUAGE_APPROVAL`
   - `READY_AFTER_LANGUAGE_REMEDIATION`
   - `NOT_READY_POSSIBLE_SEMANTIC_DEFECT`

The CSV must contain one row per case with these columns:

```text
golden_case_id,semantic_faithfulness,interaction_quality,phc_suitability,finding_ids,case_recommendation,notes
```

## Recommendation rules

Use `READY_FOR_HUMAN_LANGUAGE_APPROVAL` only if:

- all 16 cases pass semantic faithfulness;
- all 16 cases pass interaction quality;
- no blocking or major language finding remains open;
- no possible semantic defect is recorded; and
- any PHC-suitability limitation is clearly scoped rather than misrepresented as completed field validation.

Use `READY_AFTER_LANGUAGE_REMEDIATION` when the frozen semantics remain sound but one or more language changes are required.

Use `NOT_READY_POSSIBLE_SEMANTIC_DEFECT` when any case appears to require a change to frozen clinical expectations rather than wording alone.

## Prohibited actions

Do not:

- approve or freeze the language layer;
- modify either reviewed hash;
- modify existing files;
- create replacement renderings;
- use archived selected-v0 renderings as current product authority;
- browse for or introduce new medical guidance;
- generate variants or training data;
- run a teacher bake-off; or
- commit or push unless the project owner separately instructs you to do so.
