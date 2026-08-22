# Product holistic golden language calibration approval v1

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Records project-owner language approval for the bounded hackathon; not a clinical-rule source or PHC field-validation record.

## Decision

The project owner approves the 16-case holistic golden language calibration and its interaction style for the bounded EdgeIMCI hackathon scope.

This approval authorizes:

- use of the 16 cases as frozen style anchors;
- authoring the remaining 62 canonical golden language renderings;
- deterministic component validation; and
- bounded product-language evaluation.

It does not authorize:

- teacher or prompt bake-offs before the complete 78-case language layer is reviewed;
- bulk variant generation;
- using the calibration records as training data;
- production clinical use; or
- describing the language as qualified PHC-worker field validation.

## Approval basis and limitation

The approval follows the same-agent technical/editorial review in `product_holistic_golden_language_technical_review_v1.md`, which closed four language-layer findings and recorded `PASS_TECHNICAL_ALIGNMENT_READY_FOR_HUMAN_LANGUAGE_REVIEW`.

An independent coding-agent language review in `product_holistic_golden_language_independent_review_v1.md` then passed semantic faithfulness and interaction quality for all 16 cases and identified two minor PHC-language improvements. `LGR-IR-001` was resolved by grouping the dense multi-pathway management plan, and `LGR-IR-002` was resolved by removing an internal pathway reference. The project owner then supplied the explicit language disposition.

The independent review is repository-based automated review, not qualified PHC-worker field validation. The approval is sufficient to move the bounded hackathon workflow forward, but it is not production clinical authorization or field usability evidence.

## Controlled freeze transition

| Stage | SHA-256 |
|---|---|
| Reviewed 16-case calibration | `4e05eae23aa7cc4a9371925035ee46564debf6bb004900fd37a4fefe606256b9` |
| Frozen 16-case calibration | `b42659143270e8ef732593598fc3c7eeb6d9fb6805eaa03a0f93801d76c97fbb` |
| Frozen semantic source | `9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f` |

The calibration hash changed because the two documented minor language remediations were applied and lifecycle/review metadata moved from pending to approved/frozen. The PHC-worker submissions and semantic alignment targets did not change. No clinical classification, action, urgency state, missing element, contradiction, or scope disposition changed.

The canonical machine-readable decision is `configs/rendering/holistic_golden_language_approval_v1.json`; its YAML sibling is generated.

## Next gate

The approved style may now be applied to the remaining 62 frozen semantic cases. The resulting complete 78-case language layer must receive its own review and freeze before teacher selection or synthetic variant generation begins.
