# EdgeIMCI response grammar v1

> **Authority:** `APPROVED_PRODUCT_POLICY` · **Lifecycle:** `CURRENT` · Project-owner-approved interaction format for golden-language remediation and later post-training; not a clinical-rule source.

## Decision

Canonical EdgeIMCI responses use a stable, state-dependent grammar. The purpose is to make urgent behavior predictable, reduce irrelevant stylistic variation for small-model post-training, improve frontline scanning, and make deterministic evaluation easier.

The canonical machine-readable policy is `configs/rendering/edgeimci_response_grammar_v1.json`. Its YAML sibling is generated. Exact delimiters in that artifact outrank illustrative prose in this document.

## Stable states and delimiters

| State | Required leading structure |
|---|---|
| Complete | `Classifications:` → `Management:` |
| Urgent complete | `URGENT:` → `Classifications:` → `Immediate management:` |
| Incomplete | `ASSESSMENT INCOMPLETE` → optional conflicts → `Information needed:` |
| Urgent incomplete | `URGENT:` → `Immediate management:` → `ASSESSMENT INCOMPLETE` → optional conflicts → `Information still needed:` |
| Out of scope | `OUTSIDE SUPPORTED SCOPE` |

Classifications, actions, and acquisition requests use `- ` bullets. `Classifications:` is always plural, even for one classification. An encoded urgent state always begins with the exact `URGENT:` prefix. Optional sections appear only when their corresponding semantic content exists.

## Deterministic presentation order

The grammar also separates the semantic evaluator's stable identifier order from the order shown to a PHC worker. This is an interaction/UX policy, not an IMCI clinical rule. It never adds, removes, suppresses, or changes an encoded action or observation request.

For management actions, the canonical renderer uses these priority bands while preserving semantic source order within a band:

1. active stabilization that cannot wait, currently diazepam for a child convulsing now;
2. an action whose own encoded wording requires completion before referral, currently treating dehydration before referral;
3. remaining assessment, treatment, support, reassessment, and referral actions;
4. caregiver counselling; and
5. scheduled follow-up.

This means treatment and operational actions appear before routine advice or follow-up, and “before referral” actions appear before the corresponding referral. It does not turn non-urgent referral into urgent referral.

Information requests follow the encoded assessment workflow: general danger signs, age/scope, respiratory, diarrhoea, fever, then ear assessment. The bronchodilator sequence is rendered as trial completion, calm-state confirmation, full-minute respiratory counting/rate, then chest-indrawing reassessment. Equal-priority items retain their source order.

## Complete response

```text
Classifications:
- Pneumonia
- No dehydration

Management:
- Give oral amoxicillin for 5 days.
- Give fluid, zinc, and food according to Plan A.
```

A complete case with no triggered classification or action still uses both sections:

```text
Classifications:
- None of the currently supported classifications is triggered.

Management:
- No management action is indicated by the supported assessment.
```

## Urgent complete response

```text
URGENT: Act now and do not delay referral.

Classifications:
- Very severe disease

Immediate management:
- Give the indicated pre-referral treatment immediately.
- Arrange urgent referral.
```

When the frozen semantics defer routine actions, a `Deferred routine care:` section follows the immediate management. It must not compete with or precede urgent actions.

## Incomplete response

```text
ASSESSMENT INCOMPLETE

Information needed:
- Ask whether the child has diarrhoea.
- Count the respiratory rate for one full minute while the child is calm.

I cannot provide the final classifications and complete management plan until these findings are supplied.
```

Contradictory or invalid evidence adds `Conflicting or invalid findings:` before the information requests.

## Urgent incomplete response

```text
URGENT: Act now and do not delay referral.

Immediate management:
- Give diazepam if the child is convulsing now.
- Arrange urgent referral.

ASSESSMENT INCOMPLETE

Information still needed:
- Complete the remaining required checks.

Complete these checks rapidly, but do not delay referral. The final holistic classifications and complete management plan remain pending.
```

## Scope rejection

```text
OUTSIDE SUPPORTED SCOPE

This encounter is outside the supported EdgeIMCI major sick-child scope. Use the applicable approved age-specific pathway.
```

## Change-control boundary

This format decision does not alter observations, classifications, actions, urgency, missing elements, contradictions, acquisition modes, or source provenance. The frozen 16-case calibration remains immutable historical evidence. Its user submissions are retained in the complete layer, while its assistant responses may be reformatted under this grammar.

All 78 reformatted full-layer records returned to review status under this policy. That review, language remediation, project-owner approval, and controlled hash freeze are now complete. The separate full-language approval artifact authorizes controlled variant work, teacher bake-off, and product evaluation. Training and production clinical use remain blocked.
