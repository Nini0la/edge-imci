# Holistic teacher bake-off review protocol v1

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `PROPOSED_FOR_REVIEW` · Human-readable companion to the canonical selection policy.

## Purpose and boundary

This protocol defines how generated PHC-worker language candidates will be reviewed and how evidence will be ordered for a project-owner choice. It is an experiment and interaction policy, not an IMCI clinical rule. It does not authorize model calls, corpus promotion, bulk generation or training.

The reviewer sees only an opaque review-item ID, the structured encounter findings and the candidate PHC-worker submission. The review surface hides teacher identity, model, prompt strategy, canonical assistant response, semantic alignment and target-side provenance. This reduces configuration preference and prevents the frozen answer from shaping review of the input language.

## Per-candidate rubric

Every deterministically passing candidate is reviewed for:

| Dimension | Values | Meaning |
|---|---|---|
| Semantic faithfulness | `PASS`, `FAIL`, `UNSURE` | Whether the submission preserves the source meaning without adding or changing facts. |
| Fact completeness | `PASS`, `FAIL`, `UNSURE` | Whether all known source observations needed in the complete encounter are represented. |
| Unknown preservation | `PASS`, `FAIL`, `NOT_APPLICABLE`, `UNSURE` | Whether unknown information remains unknown rather than becoming negative. |
| Target leakage | `NONE`, `SUSPECTED`, `PRESENT` | Whether classification, action or urgency wording has leaked into the worker submission. |
| Answer-shaped language | `NONE`, `SUSPECTED`, `PRESENT` | Whether the case has been unnaturally written to make the intended answer obvious. |
| Naturalness | 1–5 | Quality of the submission as coherent human language. |
| PHC suitability | 1–5 | Plausibility and usefulness as frontline PHC-worker case communication. |

Score anchors for both 1–5 scales are: `1` unusable, `2` major problems, `3` acceptable for the bounded hackathon, `4` strong, and `5` exemplary. These anchors are project interaction criteria, not clinical-source claims.

## Coherent dispositions

`APPROVE` requires semantic and completeness passes, unknown preservation pass or not applicable, no leakage, no answer-shaped phrasing, scores of at least 3, and no error codes.

An uncertain judgment or suspected leakage requires `ESCALATE`. Any failed required dimension, present leakage, score below 3 or recorded error code requires `REJECT`. Code validates this relationship so a contradictory review record cannot enter the comparison summary.

## Configuration eligibility

A teacher/strategy configuration becomes eligible for project-owner selection only after:

- all scheduled calls have reached a terminal execution state;
- no uncertain request remains unreconciled;
- every deterministic pass has the required human review;
- no review escalation remains open;
- the project owner records that the observed human acceptance is sufficient;
- systematic-corruption review is recorded as `NONE`;
- usage and cost evidence is complete; and
- no approved item contains target leakage.

V1 does not invent a numerical systematic-corruption threshold or minimum acceptable approval rate before evidence exists. Those two judgments must be explicitly recorded rather than silently inferred.

## Comparison order and winner decision

Eligible configurations are compared in this order:

1. higher human approval rate;
2. lower semantic or unknown-preservation rejection rate;
3. lower target-leakage rate;
4. higher mean PHC suitability;
5. higher mean naturalness;
6. higher deterministic pass rate;
7. lower cost per human-approved item; and
8. lower p95 latency.

The summary never selects a winner automatically. The project owner records the final configuration decision, and ties require explicit review.

## Canonical artifacts

- `configs/generation/holistic_teacher_bakeoff_selection_policy_v1.json` — canonical proposed policy.
- `configs/generation/holistic_teacher_bakeoff_selection_policy_v1.yaml` — generated mirror.
- `configs/generation/holistic_language_variant_review_v1.schema.json` — review-record schema.
- `src/edge_imci/generation/holistic_bakeoff.py` — review validation and evidence summarization.
