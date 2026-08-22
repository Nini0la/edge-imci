# Product-level holistic golden suite — requirements v1

> **Authority:** `APPROVED_PRODUCT_POLICY` · **Lifecycle:** `CURRENT` · Construction and review contract; not a clinical-rule source.

**Status:** The 78-case suite has passed oracle-v3 technical/source verification, received explicit human/domain approval, and been hash-frozen under `edge-imci-holistic-product-golden-approval-v1`. This is hackathon-scope approval, not production clinical authorization.

**Artifacts:** `data/golden/holistic_product_v1/semantic_cases.jsonl`, its YAML mirror and manifest, plus `docs/product_holistic_golden_review_v1.md`.

## Relationship to the existing golden slice

The archived 14-case `LEGACY_SELECTED_V0_COMPONENT_REGRESSION` remains fixed under `data/archive/selected_v0/` for selected-v0 component regression and historical reproduction only.

It is not the product-level golden suite for holistic v2 behavior. It is mechanically ineligible for holistic generation, product evaluation, teacher selection, and training. Existing v1 cases that emit an early classification while assessment is incomplete must not be reused as affirmative v2 product targets. The new product suite uses `corpus_role=HOLISTIC_PRODUCT_GOLDEN` and pins the major-sick-child rule, policy, oracle, validator, and review-decision identifiers.

## Pinned prerequisites

The frozen suite pins approved versions of:

```text
clinical rule set
holistic completeness policy
whole-encounter schema
integrated action-synthesis oracle
clinical-question disposition set
source-literal oxygen-referral disposition
```

The pinned hackathon-scope substrate is `imci-major-sick-child-v1` with `imci-major-sick-child-holistic-completeness-v2`, `imci-major-sick-child-review-decisions-v1`, and `imci-major-sick-child-oxygen-referral-disposition-v1`. The recorded domain/policy gate is satisfied for construction and re-review of the holistic golden suite; production clinical authorization remains outside this approval.

## Required semantic families

The reviewed suite should include at least:

- a complete low-severity whole encounter;
- one complete encounter for each classification family;
- multiple simultaneous classifications across assessment areas;
- an integrated management plan with deduplicated shared actions;
- each identified cross-pathway treatment interaction;
- urgent/severe findings;
- exact age, duration, respiratory-rate, temperature, and ear-discharge boundaries;
- systematic single and multiple omissions;
- explicit negative versus omission twins;
- an incomplete encounter without a known urgent finding;
- an incomplete encounter with a known urgent finding;
- grouped missing-elements output;
- contradiction and ambiguity cases;
- bronchodilator intervention/reassessment;
- initial Plan B and Plan C actions with their timed-reassessment instructions;
- a complete post-reassessment encounter;
- malaria-risk and test-availability branches;
- measles with simultaneous respiratory/diarrhoea/ear classifications;
- out-of-scope cases that must not receive unsupported synthesis.

## Construction result

The frozen suite contains 78 cases, including 60 complete encounters and 18 incomplete or schema-rejected cases. Every encoded classification family appears in at least one review case. JSONL is canonical, YAML is the human-readable mirror, and each evaluable expected result is exactly recomputed from the pinned deterministic oracle.

`HPG-GAP-REASSESS-001` is resolved by `edge-imci-holistic-golden-scope-dispositions-v1`. Separate longitudinal Plan B/C treatment-stage execution is outside holistic golden v1. The suite covers the initial dehydration classification, Plan B/C action, and timed-reassessment instruction. A later full updated assessment may be submitted and evaluated afresh; v1 does not maintain treatment state, infer reassessment findings, or automatically repeat a plan. This product-scope disposition does not change the clinical rules or `MSC-CQ-REASSESS-001`.

## Target behavior

```text
COMPLETE
→ final integrated classifications and management synthesis

INCOMPLETE, no urgent finding
→ grouped missing elements
→ no final holistic synthesis

INCOMPLETE, known urgent finding
→ immediate source-backed urgent/pre-referral actions
→ explicit incomplete status and remaining assessment
→ no final holistic synthesis
```

## Review gates

Every semantic case must pass:

1. deterministic schema validation;
2. exact recomputation by the approved completeness and clinical oracle;
3. rule/action trace validation;
4. source-provenance review;
5. domain-expert semantic approval;
6. explicit confirmation that omitted findings remain unknown.

All six gates are complete for the hash recorded in `edge-imci-holistic-product-golden-approval-v1`. Language renderings may now be produced and reviewed under a separate rendering contract. The frozen semantic records remain ineligible for direct training. Teacher selection, prompt bake-offs, bulk generation, splits, and SFT remain later gated stages.
