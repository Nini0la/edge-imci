# EdgeIMCI grammar-normalized golden language — re-review agent instructions

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `CURRENT` · Review-only handoff for the grammar-normalized 78-case language layer.

## Assignment

Perform an independent, case-by-case re-review of the grammar-normalized EdgeIMCI product-level golden language layer.

Do not edit the clinical rules, completeness policy, deterministic evaluator, frozen semantic suite, frozen 16-case calibration, response grammar, generator, language records, manifests, schemas, tests, or existing review records. Do not generate variants, teacher outputs, datasets, splits, or training records.

Create only these two deliverables:

1. `docs/product_holistic_golden_language_format_re_review_v1.md`
2. `docs/product_holistic_golden_language_format_re_review_v1.csv`

## Exact review targets

Verify these SHA-256 hashes before reviewing:

| Artifact | Required SHA-256 |
|---|---|
| `data/golden/holistic_product_v1/language_renderings_v1.jsonl` | `713d223436c7b1b2daf10006d7e239ae1d7681dc6cccb771cea7d906a2bf2d94` |
| `data/golden/holistic_product_v1/semantic_cases.jsonl` | `9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f` |
| `configs/rendering/edgeimci_response_grammar_v1.json` | `9ce4aa8de062dbdcd0c3a2cbca72a4ec72ca7e828f29c2a24b8721a887f8d6fc` |
| `data/golden/holistic_product_v1/language_calibration_v1.jsonl` | `b42659143270e8ef732593598fc3c7eeb6d9fb6805eaa03a0f93801d76c97fbb` |

If any hash differs, stop and report `REVIEW_TARGET_HASH_MISMATCH`. Do not review a moving target.

The language file must contain exactly 78 records, all with `status=DRAFT_FOR_HUMAN_REVIEW`. The frozen calibration must remain unchanged; it is historical input evidence, not the current full-layer review target.

## Required reading

Read these files before reviewing cases:

1. `docs/README.md`
2. `docs/golden_language_rendering_contract_v1.md`
3. `docs/edgeimci_response_grammar_v1.md`
4. `configs/rendering/edgeimci_response_grammar_v1.json`
5. `docs/product_holistic_golden_approval_v1.md`
6. `data/golden/holistic_product_v1/manifest.json`
7. `data/golden/holistic_product_v1/semantic_cases.jsonl`
8. `data/golden/holistic_product_v1/language_manifest_v1.json`
9. `data/golden/holistic_product_v1/language_renderings_v1.jsonl`
10. `docs/product_holistic_golden_language_review_v1.md`
11. `docs/product_holistic_golden_language_review_v1_report.md`

The pre-format report is historical evidence. Independently verify the new target rather than copying its result.

## Authority boundary

The frozen semantics decide observations, completeness, classifications, actions, urgency, missing elements, contradictions, acquisition modes, deferrals, and scope rejection. The response grammar decides only headings, section order, bullet delimiters, and state-dependent presentation.

Do not introduce medical knowledge. If the frozen semantic target appears wrong, record `POSSIBLE_SEMANTIC_DEFECT_REQUIRES_CHANGE_CONTROL`; do not repair it in language.

## Required checks for every case

Review all 78 records for:

1. exact semantic faithfulness;
2. every classification represented once and without alteration;
3. every immediate/final action represented once and without alteration;
4. urgent actions first and exact `URGENT:` leading behavior;
5. correct urgent versus non-urgent referral wording;
6. every missing element and contradiction represented;
7. correct acquisition language and mode;
8. no invention, omission, or unknown-to-negative conversion;
9. natural PHC-worker submission language;
10. clear, scannable EdgeIMCI response;
11. exact response-grammar state selection;
12. exact heading casing and section order;
13. `Classifications:` used for all complete cases, including one classification;
14. bullet formatting for classifications, actions, and information requests;
15. no internal rule, action, schema, or pipeline identifiers; and
16. preservation of the frozen calibration user submission for each of the 16 linked anchor cases.

Pay particular attention to:

- `hpg-001`, which must use the structured no-classification/no-action template and must not say “these pathways”;
- the 16 format-remediated anchor-linked records;
- urgent complete and urgent incomplete section order;
- post-bronchodilator actions rendered in the correct completed/reassessed tense;
- generic antibiotic and local-protocol actions that must not gain invented details;
- deferral sections in urgent cases; and
- out-of-scope cases, which must not synthesize classifications or management.

## Required Markdown report

The Markdown deliverable must include:

- all four verified target hashes;
- reviewer identity/type and independence statement;
- method and authority boundary;
- disposition counts by review dimension;
- one row for every case;
- every finding with severity, affected cases, exact wording, governing semantic or grammar requirement, rationale, proposed language-only correction, and status;
- confirmation that all 16 anchor user submissions were preserved;
- confirmation that all 78 records use the correct state template;
- confirmation that clinical semantics were not changed;
- remaining limitations, including absence of qualified PHC-worker field validation; and
- one overall recommendation from the allowed set below.

## Required CSV columns

The CSV must contain exactly one row per case and these columns:

```text
golden_case_id,semantic_faithfulness,grammar_conformance,interaction_quality,phc_suitability,anchor_user_preserved,finding_ids,case_recommendation,notes
```

## Allowed dispositions

Per case:

- `READY`
- `READY_AFTER_MINOR_REMEDIATION`
- `NOT_READY`
- `POSSIBLE_SEMANTIC_DEFECT_REQUIRES_CHANGE_CONTROL`

Overall:

- `READY_FOR_PROJECT_OWNER_LANGUAGE_APPROVAL`
- `READY_AFTER_LANGUAGE_REMEDIATION`
- `NOT_READY_FOR_LANGUAGE_APPROVAL`
- `POSSIBLE_SEMANTIC_DEFECT_REQUIRES_CHANGE_CONTROL`

Do not mark the corpus frozen or authorize teacher bake-off, variant generation, training, or production use. Those require a separate project-owner approval and versioned freeze after this review.
