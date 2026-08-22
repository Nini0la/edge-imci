# Product-level holistic golden semantic approval v1

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Records the bounded hackathon approval and controlled freeze; it is not a clinical-rule source.

## Decision

The project domain owner approves the 78-case `edge-imci-holistic-product-golden-v1` semantic suite as the product-level golden semantic target for the current EdgeIMCI hackathon scope.

This approval authorizes the suite for:

- golden-language rendering and review;
- product evaluation;
- teacher and prompt bake-offs; and
- deterministic component validation and domain review.

It does not authorize:

- using the 78 golden semantic records themselves as training examples;
- production clinical deployment or autonomous clinical use;
- expanding the encoded clinical scope; or
- changing clinical expectations through language rendering.

The canonical machine-readable decision is `configs/golden/holistic_product_golden_approval_v1.json`; its YAML sibling is generated for human readability.

## Approval basis

The approval follows the oracle-v3 technical/source verification in `docs/product_holistic_golden_domain_re_review_v2.md`, which recorded all 78 cases as `PASS_SOURCE_ALIGNED` and recommended `READY_FOR_HUMAN_DOMAIN_APPROVAL`. That review also records its same-agent independence limitation; the project domain owner supplied the subsequent human/domain disposition.

The following substrate remains pinned:

| Role | Identifier |
|---|---|
| Clinical rules | `imci-major-sick-child-v1` |
| Holistic completeness policy | `imci-major-sick-child-holistic-completeness-v2` |
| Approved review decisions | `imci-major-sick-child-review-decisions-v1` |
| Oxygen referral disposition | `imci-major-sick-child-oxygen-referral-disposition-v1` |
| Golden scope dispositions | `edge-imci-holistic-golden-scope-dispositions-v1` |
| Deterministic oracle | `edge-imci-holistic-deterministic-oracle-v3` |

## Hash-preserving freeze transition

| Stage | SHA-256 |
|---|---|
| Reviewed oracle-v3 semantic records | `e8c538ac7a82b8faae7b7e36644eb3c44751c88380621e87625d1f703c5a70a1` |
| Frozen v4 record envelope | `9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f` |

The two hashes differ because the controlled freeze changed lifecycle metadata only:

- record status became `FROZEN`;
- review flags became `HUMAN_DOMAIN_APPROVED` and `SEMANTICS_FROZEN`;
- the approval identifier was pinned; and
- record, generator, and validator lifecycle identifiers advanced to v4.

No input case, expected completeness state, missing element, classification, action, trace, or clinical provenance changed during this transition.

## Freeze and change control

The frozen JSONL is the canonical semantic record; YAML is its generated mirror. Every eligible use must verify the frozen SHA-256 and artifact pins.

Language renderings may select wording, organization, tone, and turn structure, but they must not alter the frozen semantic target. A wording problem belongs in the language layer. A discovered semantic defect requires a new versioned remediation, deterministic regeneration, review, approval, and freeze; it must never be patched silently in place.

The archived selected-v0 14-case slice remains historical/component-regression material and must not be substituted for this product-level suite.

## Next gate

The next gate is approval of the golden-language rendering contract and a small calibration set, followed by reviewed language renderings for all 78 frozen semantic cases. Bulk variant generation and SFT remain blocked until the language layer and generation recipe pass their own review gates.
