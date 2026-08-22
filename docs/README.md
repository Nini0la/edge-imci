# EdgeIMCI documentation authority index

> **Authority:** `DOCUMENT_CONTROL` · **Lifecycle:** `CURRENT` · **Canonicality:** Canonical index for the role and lifecycle of repository documentation.

This index prevents planning notes, historical experiments, review evidence, and approved policy from being treated as interchangeable. Authority describes what a document is allowed to decide; lifecycle describes whether it is current.

## Precedence and interpretation

1. The WHO IMCI source is the external clinical source. Human-approved review decisions resolve how the bounded hackathon representation handles recorded ambiguities.
2. Versioned canonical clinical and policy artifacts define what repository code executes. If an artifact conflicts with its clinical source or approved review decision, that is a defect requiring review—not permission to ignore the source.
3. Approved product-policy artifacts define EdgeIMCI interaction and scope choices but must not invent or override clinical logic.
4. Review and audit records explain, test, or approve artifacts; they do not silently modify them.
5. Implementation references describe schemas and software behavior.
6. Working plans guide future work and may change as evidence develops.
7. Exploratory notes contain hypotheses and options, not decisions.
8. Historical documents preserve reproducibility and must not control current product behavior.

When JSON and YAML represent the same artifact, the relationship is about editing and synchronization—not clinical authority. The designated canonical file is edited; the generated mirror is regenerated. In the current repository, canonical structured artifacts are JSON and their YAML files are generated mirrors.

## Authority vocabulary

| Label | Meaning |
|---|---|
| `NORMATIVE_CLINICAL_ARTIFACT` | Versioned machine-readable clinical or completeness logic used by deterministic code. |
| `APPROVED_DECISION_ARTIFACT` | Approved clinical-review or product-scope decision set. |
| `APPROVED_PRODUCT_POLICY` | Current product/interaction behavior that does not create clinical rules. |
| `REVIEW_RECORD` | Domain-review, source-map, crosscheck, audit, or golden-review evidence. |
| `IMPLEMENTATION_REFERENCE` | Schema, evaluator, or operational behavior documentation. |
| `WORKING_PLAN` | Current roadmap or experiment plan; revisable and non-clinical. |
| `EXPLORATORY_NOTES` | Hypotheses and options that are not approved decisions. |
| `REFERENCE` | Terminology or navigation aid. |
| `HISTORICAL_ARCHIVE` | Reproducibility record that is ineligible to govern current product work. |
| `DOCUMENT_CONTROL` | Repository documentation-governance metadata. |

Lifecycle values are `CURRENT`, `PROPOSED_FOR_REVIEW`, `FROZEN`, `SUPERSEDED`, and `ARCHIVED`.

## Canonical structured authority

| Canonical artifact | Generated mirror | Authority | Lifecycle |
|---|---|---|---|
| `data/rules/imci_major_sick_child_v1.json` | `.yaml` sibling | `NORMATIVE_CLINICAL_ARTIFACT` | `CURRENT` |
| `configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json` | `.yaml` sibling | `NORMATIVE_CLINICAL_ARTIFACT` | `CURRENT` |
| `configs/information_policy/imci_major_sick_child_review_decisions_v1.json` | `.yaml` sibling | `APPROVED_DECISION_ARTIFACT` | `CURRENT` |
| `configs/information_policy/imci_major_sick_child_oxygen_referral_disposition_v1.json` | `.yaml` sibling | `APPROVED_PRODUCT_POLICY` | `CURRENT` |
| `configs/golden/holistic_product_golden_scope_dispositions_v1.json` | `.yaml` sibling | `APPROVED_DECISION_ARTIFACT` | `CURRENT` |
| `configs/golden/holistic_product_golden_approval_v1.json` | `.yaml` sibling | `APPROVED_DECISION_ARTIFACT` | `CURRENT` |
| `data/golden/holistic_product_v1/semantic_cases.jsonl` | `semantic_cases.yaml` | `REVIEW_RECORD` | `FROZEN` |
| `configs/rendering/holistic_golden_language_record_v1.schema.json` | none | `IMPLEMENTATION_REFERENCE` | `CURRENT` |
| `configs/rendering/holistic_golden_language_approval_v1.json` | `.yaml` sibling | `APPROVED_DECISION_ARTIFACT` | `CURRENT` |
| `data/golden/holistic_product_v1/language_calibration_v1.jsonl` | `language_calibration_v1.yaml` | `REVIEW_RECORD` | `FROZEN` |
| `data/golden/holistic_product_v1/language_renderings_v1.jsonl` | `language_renderings_v1.yaml` | `REVIEW_RECORD` | `PROPOSED_FOR_REVIEW` |
| `data/archive/selected_v0/archive_manifest.json` | none | `HISTORICAL_ARCHIVE` | `ARCHIVED` |

The frozen holistic golden suite is the approved semantic target for the bounded hackathon scope. Its approval artifact authorizes specified research uses but explicitly excludes direct training and production clinical use.

## Markdown document register

| Document | Authority | Lifecycle | Relationship |
|---|---|---|---|
| `README.md` | `DOCUMENT_CONTROL` | `CURRENT` | This documentation index. |
| `glossary.md` | `REFERENCE` | `CURRENT` | Terminology aid only. |
| `clinical_questions.md` | `REVIEW_RECORD` | `CURRENT` | Question/disposition index; canonical answers live in approved decision artifacts. |
| `major_sick_child_expansion_map_v1.md` | `REVIEW_RECORD` | `CURRENT` | Source-derived engineering map; read with the approved decision set. |
| `major_sick_child_domain_review_v1.md` | `REVIEW_RECORD` | `CURRENT` | Hackathon-scope domain-review record. |
| `system_level_clinical_audit_v2.md` | `REVIEW_RECORD` | `SUPERSEDED` | Pre-oracle-v3 substrate audit retained for history. |
| `product_holistic_golden_suite_requirements_v1.md` | `APPROVED_PRODUCT_POLICY` | `CURRENT` | Approved construction/review contract for product semantics. |
| `product_holistic_golden_review_v1.md` | `REVIEW_RECORD` | `CURRENT` | Generated review surface for the approved and frozen semantics. |
| `product_holistic_golden_approval_v1.md` | `REVIEW_RECORD` | `CURRENT` | Human-readable approval, hash transition, permissions, and freeze/change-control record. |
| `golden_language_rendering_contract_v1.md` | `APPROVED_PRODUCT_POLICY` | `CURRENT` | Approved bounded-hackathon language contract and frozen 16-case style calibration boundary. |
| `product_holistic_golden_language_calibration_review_v1.md` | `REVIEW_RECORD` | `CURRENT` | Generated review surface for the project-owner-approved and frozen 16-case calibration. |
| `product_holistic_golden_language_technical_review_v1.md` | `REVIEW_RECORD` | `CURRENT` | Same-agent technical/editorial verification used as an approval input; preserves its independence limitation. |
| `product_holistic_golden_language_independent_review_v1.md` | `REVIEW_RECORD` | `CURRENT` | Independent coding-agent review of the pinned pre-freeze calibration; its two minor findings were remediated before approval. |
| `product_holistic_golden_language_approval_v1.md` | `REVIEW_RECORD` | `CURRENT` | Project-owner language approval, controlled freeze, permissions, and explicit validation limitations. |
| `product_holistic_golden_language_review_v1.md` | `REVIEW_RECORD` | `PROPOSED_FOR_REVIEW` | Generated review surface for all 78 language records; 62 new renderings remain pending. |
| `holistic_golden_language_independent_review_agent_instructions.md` | `WORKING_PLAN` | `SUPERSEDED` | Executed pre-freeze independent-review handoff retained for audit history. |
| `holistic_golden_domain_review_agent_instructions.md` | `WORKING_PLAN` | `SUPERSEDED` | Original review-only protocol retained for audit history. |
| `product_holistic_golden_domain_review_v1.md` | `REVIEW_RECORD` | `SUPERSEDED` | Technical/source review of the pre-remediation corpus hash; records four findings and no approval. |
| `holistic_golden_remediation_re_review_agent_instructions.md` | `WORKING_PLAN` | `SUPERSEDED` | Completed oracle-v2 re-review protocol retained for history. |
| `product_holistic_golden_domain_re_review_v1.md` | `REVIEW_RECORD` | `SUPERSEDED` | Independent review of corpus hash `bba39ee0...`; records the three respiratory findings remediated in v3. |
| `holistic_golden_respiratory_remediation_re_review_agent_instructions.md` | `WORKING_PLAN` | `SUPERSEDED` | Completed oracle-v3 verification protocol retained for audit history. |
| `product_holistic_golden_domain_re_review_v2.md` | `REVIEW_RECORD` | `CURRENT` | Same-agent technical/source verification of oracle-v3 used as the basis for explicit human/domain approval; retains its independence limitation. |
| `interaction_design_retrieval_assessment_bundles.md` | `APPROVED_PRODUCT_POLICY` | `CURRENT` | Current interaction framing; cannot override clinical artifacts. |
| `experiment_operations_and_tracking_plan.md` | `WORKING_PLAN` | `CURRENT` | Maintained Markdown working version; corresponding DOCX is its source snapshot. |
| `experimental_campaign_map.md` | `WORKING_PLAN` | `CURRENT` | Maintained Markdown working version; corresponding DOCX is its source snapshot. |
| `synthetic_data_generation_experiment_plan.md` | `WORKING_PLAN` | `CURRENT` | Maintained Markdown working version; corresponding DOCX is its source snapshot. |
| `synthetic_data_generation_experiment_notes.md` | `EXPLORATORY_NOTES` | `CURRENT` | Generation hypotheses and options; never a clinical or product decision. |
| `information_policy_proposal.md` | `REVIEW_RECORD` | `ARCHIVED` | Selected-v0 design record. |
| `information_policy_v1.md` | `IMPLEMENTATION_REFERENCE` | `ARCHIVED` | Selected-v0 deterministic policy reference. |
| `trajectory_schema.md` | `IMPLEMENTATION_REFERENCE` | `ARCHIVED` | Selected-v0 trajectory/reference-rendering schema. |
| `golden_slice_review_v1.md` | `HISTORICAL_ARCHIVE` | `ARCHIVED` | Selected-v0 14-case review package. |
| `rendering_contract_v1.md` | `HISTORICAL_ARCHIVE` | `ARCHIVED` | Selected-v0 rendering contract. |
| `rendering_bakeoff_review_v1.md` | `HISTORICAL_ARCHIVE` | `ARCHIVED` | Selected-v0 historical experiment review. |
| `system_level_clinical_audit_v0.md` | `HISTORICAL_ARCHIVE` | `ARCHIVED` | Selected-v0 audit. |
| `cases_crosscheck.md` | `HISTORICAL_ARCHIVE` | `ARCHIVED` | Selected-v0 case crosscheck. |
| `rules_crosscheck.md` | `HISTORICAL_ARCHIVE` | `ARCHIVED` | Selected-v0 rule crosscheck. |

## Non-Markdown companions

| Files | Role |
|---|---|
| `EdgeIMCI - Experiment Operations and Tracking Plan.docx` | Original user-authored/source snapshot for the maintained Markdown working plan. |
| `EdgeIMCI - Experimental Campaign Map.docx` | Original user-authored/source snapshot for the maintained Markdown working plan. |
| `EdgeIMCI - Synthetic Data Generation Experiment Plan.docx` | Original user-authored/source snapshot for the maintained Markdown working plan. |
| `cases_crosscheck.csv`, `rules_crosscheck.csv`, `rules_crosscheck.pdf` | Generated/companion selected-v0 historical review material. |
| `product_holistic_golden_domain_review_v1.csv` | Per-case companion to the superseded pre-remediation technical/source review. |
| `product_holistic_golden_domain_re_review_v1.csv` | Per-case companion to the superseded oracle-v2 independent review. |
| `product_holistic_golden_domain_re_review_v2.csv` | Current 78-row companion to the oracle-v3 technical/source verification. |
| `product_holistic_golden_language_technical_review_v1.csv` | Current 16-row companion to the language calibration technical/editorial review. |
| `product_holistic_golden_language_independent_review_v1.csv` | Current 16-row companion to the independent pre-freeze language review. |

Changes to document authority, lifecycle, canonicality, or supersession must update this index in the same commit.
