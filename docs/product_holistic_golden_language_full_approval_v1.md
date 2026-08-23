# Product holistic golden language full-layer approval v1

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Records project-owner approval and the controlled freeze of the complete 78-case golden language layer for the bounded hackathon.

## Decision

The project owner approves the remediated complete EdgeIMCI golden language layer and authorizes its controlled freeze.

This approval covers all 78 canonical conversations and is pinned to the unchanged frozen product-level semantic suite. It authorizes controlled language-variant work, teacher bake-off, and product evaluation. It does not authorize direct use of these records as training data, unreviewed bulk corpus generation, production clinical use, or claims of qualified PHC-worker field validation.

## Approval basis

The approved layer passed:

- complete case-by-case semantic and language re-review at reviewed hash `78d4a503eecf603ad69dd1d26edb1fa7cd258c310ece95bdfb892688158dd665`;
- deterministic remediation of `LGR-GR-001` through `LGR-GR-004`;
- documentation remediation `LGR-GR-DOC-001`;
- exact verification that only the 42 identified assistant responses changed during remediation;
- exact preservation of all 78 user submissions and semantic alignment objects; and
- project-owner review and explicit approval on 2026-08-23.

The technical/editorial re-review and remediation verification were performed by the same coding agent that implemented the renderer changes. This limitation is recorded. The explicit project-owner disposition is the human approval authority for this bounded hackathon freeze.

## Controlled hash transition

| Stage | SHA-256 |
|---|---|
| Pre-remediation reviewed language | `713d223436c7b1b2daf10006d7e239ae1d7681dc6cccb771cea7d906a2bf2d94` |
| Approved remediated language content | `78d4a503eecf603ad69dd1d26edb1fa7cd258c310ece95bdfb892688158dd665` |
| Frozen 78-record artifact | `9b9c1b67a73c2e5763f5507bc55e618d28149bdee6c7c4329ecc8a868e3860a0` |
| Frozen semantic source | `9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f` |
| Approved response grammar | `1fd793607f077cd4d44a9cf73349803d32ef1e69e3aab82d00fe0bda330f4873` |

The content hash changes at freeze because lifecycle and review metadata move from pending/draft to project-owner-approved/frozen. Conversation content and semantic alignments do not change during this transition.

The canonical machine-readable approval is `configs/rendering/holistic_golden_full_language_approval_v1.json`; its YAML sibling is generated.

## Authorized uses

| Use | Authorized |
|---|---|
| Domain review | Yes |
| Component validation | Yes |
| Controlled holistic language-variant work | Yes |
| Product evaluation | Yes |
| Teacher/prompt bake-off | Yes |
| Direct training use | No |
| Production clinical use | No |

## Next gate

The next stage is controlled language-variant design and teacher/prompt bake-off against this exact frozen canonical layer. Before any resulting records become training data, their generation policy, provenance, quality gates, dataset assembly, splits, and training eligibility must be separately reviewed and versioned.
