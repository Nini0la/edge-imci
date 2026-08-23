# Product holistic golden language format re-review v1

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · **Review target:** grammar-normalized 78-case product-level golden language layer.

## Review identity and independence

This review was performed by the primary EdgeIMCI coding agent that also implemented the deterministic response-grammar normalization. It is a complete case-by-case technical and editorial re-review, but it is **not independent evidence** and it is **not qualified PHC-worker field validation**. Project-owner approval and external/domain usability review remain separate gates.

## Verified targets

The following SHA-256 hashes were verified before review:

| Artifact | Verified SHA-256 |
|---|---|
| `data/golden/holistic_product_v1/language_renderings_v1.jsonl` | `713d223436c7b1b2daf10006d7e239ae1d7681dc6cccb771cea7d906a2bf2d94` |
| `data/golden/holistic_product_v1/semantic_cases.jsonl` | `9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f` |
| `configs/rendering/edgeimci_response_grammar_v1.json` | `9ce4aa8de062dbdcd0c3a2cbca72a4ec72ca7e828f29c2a24b8721a887f8d6fc` |
| `data/golden/holistic_product_v1/language_calibration_v1.jsonl` | `b42659143270e8ef732593598fc3c7eeb6d9fb6805eaa03a0f93801d76c97fbb` |

The target contains exactly 78 records, and all 78 have `status=DRAFT_FOR_HUMAN_REVIEW`.

## Method and authority boundary

The review combined:

1. mechanical verification of target hashes, record count, statuses, state templates, headings, delimiters, urgent prefixes, semantic alignment, and anchor-user preservation;
2. a manual read of every user submission and assistant response against its frozen semantic case and alignment record;
3. comparison with the frozen 16-case calibration where an anchor link exists; and
4. focused validation with `uv run pytest -q tests/test_holistic_golden_language_full.py` (`16 passed`).

The frozen semantic suite is authoritative for observations, completeness, classifications, actions, urgency, missing elements, contradictions, acquisition modes, deferrals, and scope rejection. The response grammar is authoritative for the presentation states, headings, section order, and delimiters. This review introduces no clinical knowledge and makes no clinical-semantic changes.

## Disposition summary

| Dimension | Result |
|---|---|
| Semantic faithfulness | 78 pass; 0 fail |
| Classification/action membership | 78 pass; 0 fail |
| Correct state-template selection | 78 pass; 0 fail |
| Exact grammar and language conformance | 77 pass; 1 needs language remediation |
| Urgent leading prefix | 15 of 15 urgent cases pass |
| Frozen anchor user submissions | 16 of 16 preserved exactly |
| No invented clinical content | 78 pass; 0 fail |
| Interaction/PHC readiness | 36 ready; 42 ready after minor case-level language remediation |
| Possible semantic defects | 0 |

All 78 records use the correct state template. The one grammar-conformance failure is lexical leakage inside the correct template, not incorrect state selection.

## Findings

### LGR-GR-001 — deterministic action order does not consistently reflect workflow priority

- **Severity:** `MAJOR` at corpus level because the defect is systematic and would teach an unreliable response order; each affected case requires only language/presentation remediation.
- **Status:** `OPEN`.
- **Affected cases (38):** `hpg-006`, `hpg-007`, `hpg-008`, `hpg-009`, `hpg-010`, `hpg-011`, `hpg-012`, `hpg-013`, `hpg-016`, `hpg-017`, `hpg-018`, `hpg-019`, `hpg-020`, `hpg-021`, `hpg-027`, `hpg-028`, `hpg-032`, `hpg-033`, `hpg-034`, `hpg-035`, `hpg-036`, `hpg-041`, `hpg-043`, `hpg-045`, `hpg-048`, `hpg-051`, `hpg-052`, `hpg-053`, `hpg-054`, `hpg-057`, `hpg-058`, `hpg-062`, `hpg-063`, `hpg-064`, `hpg-065`, `hpg-068`, `hpg-070`, and `hpg-073`.
- **Exact examples:** `hpg-008` presents caregiver advice and follow-up before oral amoxicillin. `hpg-034` says to refer before treating dehydration prior to referral. `hpg-070` and `hpg-073` place rapid completion of assessment before diazepam for active convulsions. `hpg-068` flattens fourteen actions so that advice and follow-up precede medicines.
- **Governing requirement:** `docs/golden_language_rendering_contract_v1.md` requires immediate actions before supporting detail and an integrated, coherent answer. The frozen semantics determine action membership but do not require identifier order.
- **Rationale:** Stable delimiters alone are insufficient for post-training if clinically important actions appear after counselling or follow-up. The current renderer effectively preserves identifier-derived ordering rather than workflow priority.
- **Proposed language-only correction:** add a versioned deterministic action-priority policy to the response grammar/renderer. Preserve every semantic action exactly, while ordering active stabilization and immediate treatment first, required pre-referral care before referral, other treatment/support next, and routine counselling/return/follow-up last. For multi-pathway cases, use deterministic grouping or at minimum this same priority order.

### LGR-GR-002 — acquisition requests are not consistently ordered as an executable assessment sequence

- **Severity:** `MINOR`.
- **Status:** `OPEN`.
- **Affected cases:** `hpg-022-resp-trial-outstanding`, `hpg-072-incomplete-multiple-groups`.
- **Exact wording/behavior:** `hpg-022` requests the bronchodilator trial, counting, chest-indrawing check, calm-state confirmation, and respiratory rate in a non-executable order. `hpg-072` requests danger-sign, fever-context, ear, and respiratory information in lexicographic rather than established workflow order.
- **Governing requirement:** the rendering contract requires concise, coherent, operational next steps; the approved information policy uses deterministic scheduling.
- **Rationale:** Every required acquisition is present, but ordering should help the worker carry out the assessment rather than mirror internal identifiers.
- **Proposed language-only correction:** define a deterministic pathway/acquisition sequence. Within respiratory reassessment, request trial completion, calm-state confirmation, full-minute counting/rate, and chest-indrawing reassessment in executable order. Across pathways, retain the established assessment order.

### LGR-GR-003 — non-urgent referral distinction is insufficiently explicit

- **Severity:** `MINOR`.
- **Status:** `OPEN`.
- **Affected case:** `hpg-014-resp-chest-hiv-positive`.
- **Exact wording:** “Give the first dose of amoxicillin, then refer the child.”
- **Governing requirement:** the approved clinical decision distinguishes this `refer` branch from `refer urgently`; the review instructions require correct urgent versus non-urgent referral wording.
- **Rationale:** The current sentence does not falsely say “urgent,” but the explicit qualifier in the frozen calibration was intentionally designed to prevent that interpretation.
- **Proposed language-only correction:** restore the anchor clarification: “This finding alone calls for referral, not urgent referral.” Preserve the existing first-dose action and non-urgent referral semantics.

### LGR-GR-004 — internal enum-like wording leaks into caregiver/worker-facing language

- **Severity:** `MAJOR` as a hard language-quality gate; correction is language-only.
- **Status:** `OPEN`.
- **Affected case:** `hpg-075-contradiction-drinking`.
- **Exact wording:** “UNABLE observed drinking conflicts with a negative general danger sign.”
- **Governing requirement:** the response grammar forbids internal rule, action, schema, or pipeline identifiers; the rendering contract requires natural PHC-worker-facing language.
- **Rationale:** `UNABLE` is enum-like implementation language and “negative general danger sign” is opaque and unnatural.
- **Proposed language-only correction:** use the frozen natural rendering: “The general danger-sign assessment says the child can drink or breastfeed, but the diarrhoea assessment records the child as unable to drink.”

### LGR-GR-DOC-001 — rendering-contract status note is stale

- **Severity:** `MINOR` documentation finding.
- **Status:** `OPEN`.
- **Affected artifact:** `docs/golden_language_rendering_contract_v1.md`.
- **Exact wording:** “the complete 78-case golden language layer is not yet authored, reviewed, or frozen.”
- **Governing requirement:** documentation should describe current lifecycle state accurately.
- **Rationale:** The complete layer is now authored and reviewed; it remains unapproved and unfrozen pending remediation and project-owner approval.
- **Proposed correction:** update the status sentence after the language remediation, without changing the contract's clinical or rendering requirements.

## Case-by-case disposition

| Case | Semantic | Grammar | Interaction/PHC | Anchor user | Findings | Recommendation |
|---|---|---|---|---|---|---|
| hpg-001-all-negative | PASS | PASS | PASS | YES | — | READY |
| hpg-002-danger-unable-to-drink-or-breastfeed | PASS | PASS | PASS | N/A | — | READY |
| hpg-003-danger-vomits-everything | PASS | PASS | PASS | N/A | — | READY |
| hpg-004-danger-had-convulsions | PASS | PASS | PASS | N/A | — | READY |
| hpg-005-danger-lethargic-or-unconscious | PASS | PASS | PASS | N/A | — | READY |
| hpg-006-danger-convulsing-now | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-007-resp-age-2-rate-49 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-008-resp-age-2-rate-50 | PASS | PASS | REMEDIATE | YES | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-009-resp-age-11-rate-50 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-010-resp-age-12-rate-39 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-011-resp-age-12-rate-40 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-012-resp-age-59-rate-40 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-013-resp-chest-hiv-negative | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-014-resp-chest-hiv-positive | PASS | PASS | REMEDIATE | YES | LGR-GR-003 | READY_AFTER_MINOR_REMEDIATION |
| hpg-015-resp-stridor | PASS | PASS | PASS | N/A | — | READY |
| hpg-016-resp-oximeter-89-9 | PASS | PASS | REMEDIATE | YES | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-017-resp-oximeter-90 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-018-resp-prolonged-cough | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-019-resp-recurrent-wheeze | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-020-resp-post-bronchodilator-improved | PASS | PASS | REMEDIATE | YES | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-021-resp-post-bronchodilator-fast | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-022-resp-trial-outstanding | PASS | PASS | REMEDIATE | N/A | LGR-GR-002 | READY_AFTER_MINOR_REMEDIATION |
| hpg-023-resp-child-not-calm | PASS | PASS | PASS | N/A | — | READY |
| hpg-024-resp-count-not-one-minute | PASS | PASS | PASS | N/A | — | READY |
| hpg-025-resp-oximeter-missing-value | PASS | PASS | PASS | N/A | — | READY |
| hpg-026-resp-chest-hiv-unknown | PASS | PASS | PASS | N/A | — | READY |
| hpg-027-diarrhoea-no-dehydration | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-028-diarrhoea-some-dehydration | PASS | PASS | REMEDIATE | YES | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-029-diarrhoea-severe-plan-c-under-24m | PASS | PASS | PASS | N/A | — | READY |
| hpg-030-diarrhoea-severe-age-24-no-cholera | PASS | PASS | PASS | N/A | — | READY |
| hpg-031-diarrhoea-severe-age-24-cholera | PASS | PASS | PASS | YES | — | READY |
| hpg-032-diarrhoea-duration-13 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-033-diarrhoea-duration-14-persistent | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-034-diarrhoea-severe-persistent | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-035-diarrhoea-dysentery | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-036-diarrhoea-persistent-and-dysentery | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-037-diarrhoea-positive-drinking-reuse | PASS | PASS | PASS | N/A | — | READY |
| hpg-038-diarrhoea-negative-does-not-reuse | PASS | PASS | PASS | N/A | — | READY |
| hpg-039-diarrhoea-duration-unknown | PASS | PASS | PASS | N/A | — | READY |
| hpg-040-diarrhoea-cholera-context-unknown | PASS | PASS | PASS | N/A | — | READY |
| hpg-041-fever-high-positive | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-042-fever-high-negative | PASS | PASS | PASS | N/A | — | READY |
| hpg-043-fever-high-test-unavailable | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-044-fever-low-obvious-cause | PASS | PASS | PASS | N/A | — | READY |
| hpg-045-fever-low-no-cause-positive | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-046-fever-no-risk | PASS | PASS | PASS | N/A | — | READY |
| hpg-047-fever-temperature-38-4 | PASS | PASS | PASS | N/A | — | READY |
| hpg-048-fever-temperature-38-5 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-049-fever-duration-7 | PASS | PASS | PASS | N/A | — | READY |
| hpg-050-fever-duration-8-not-every-day | PASS | PASS | PASS | N/A | — | READY |
| hpg-051-fever-duration-8-every-day | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-052-fever-identified-bacterial-cause | PASS | PASS | REMEDIATE | YES | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-053-fever-measles | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-054-fever-measles-eye | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-055-fever-severe-measles-cornea | PASS | PASS | PASS | YES | — | READY |
| hpg-056-fever-severe-stiff-neck | PASS | PASS | PASS | N/A | — | READY |
| hpg-057-fever-malaria-and-measles | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-058-fever-measles-last-three-months | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-059-fever-malaria-risk-unknown | PASS | PASS | PASS | N/A | — | READY |
| hpg-060-fever-test-result-unknown | PASS | PASS | PASS | N/A | — | READY |
| hpg-061-ear-no-infection | PASS | PASS | PASS | N/A | — | READY |
| hpg-062-ear-acute-pain | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-063-ear-acute-discharge-13 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-064-ear-chronic-discharge-14 | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-065-ear-observed-pus-no-history | PASS | PASS | REMEDIATE | N/A | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-066-ear-mastoiditis | PASS | PASS | PASS | N/A | — | READY |
| hpg-067-ear-duration-unknown | PASS | PASS | PASS | N/A | — | READY |
| hpg-068-cross-four-pathways | PASS | PASS | REMEDIATE | YES | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-069-cross-urgent-dehydration-ear | PASS | PASS | PASS | N/A | — | READY |
| hpg-070-cross-multiple-urgent | PASS | PASS | REMEDIATE | YES | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-071-incomplete-entry-unknown | PASS | PASS | PASS | YES | — | READY |
| hpg-072-incomplete-multiple-groups | PASS | PASS | REMEDIATE | YES | LGR-GR-002 | READY_AFTER_MINOR_REMEDIATION |
| hpg-073-incomplete-known-urgent | PASS | PASS | REMEDIATE | YES | LGR-GR-001 | READY_AFTER_MINOR_REMEDIATION |
| hpg-074-incomplete-internal-classification-withheld | PASS | PASS | PASS | N/A | — | READY |
| hpg-075-contradiction-drinking | PASS | FAIL | REMEDIATE | YES | LGR-GR-004 | READY_AFTER_MINOR_REMEDIATION |
| hpg-076-complete-danger-plus-all-pathways | PASS | PASS | PASS | N/A | — | READY |
| hpg-077-out-of-scope-age-1 | PASS | PASS | PASS | YES | — | READY |
| hpg-078-out-of-scope-age-60 | PASS | PASS | PASS | N/A | — | READY |

## Anchor and template confirmations

All 16 linked anchor user submissions are byte-for-byte preserved in the current full layer: `hpg-001`, `hpg-008`, `hpg-014`, `hpg-016`, `hpg-020`, `hpg-028`, `hpg-031`, `hpg-052`, `hpg-055`, `hpg-068`, `hpg-070`, `hpg-071`, `hpg-072`, `hpg-073`, `hpg-075`, and `hpg-077`.

All 78 records select the correct response state template. All complete cases use `Classifications:` even for a single classification. All 15 urgent records begin with the exact `URGENT:` behavior required by the grammar. The incomplete and schema-rejection cases do not invent classifications or management.

## Remaining limitations

- The reviewer is not independent of the grammar-normalization implementation.
- No qualified PHC worker has field-tested the wording, scanability, or task execution order.
- The action-order and acquisition-order findings require deterministic policy changes and regeneration before approval.
- The corpus remains `DRAFT_FOR_HUMAN_REVIEW`; this review does not freeze it.
- This review does not authorize teacher bake-off, variant generation, dataset assembly, training, evaluation claims, or production use.

## Overall recommendation

`READY_AFTER_LANGUAGE_REMEDIATION`

The 78-case layer is semantically faithful and structurally stable, but it should not receive project-owner language approval or a versioned freeze until `LGR-GR-001` through `LGR-GR-004` are remediated and the affected cases are rechecked. `LGR-GR-DOC-001` should be corrected when the lifecycle documentation is updated. No clinical-semantic change is required by this review.
