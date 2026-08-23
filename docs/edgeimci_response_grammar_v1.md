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

All 78 reformatted full-layer records return to review status. Teacher selection, variant generation, training, and production clinical use remain blocked until the complete formatted layer receives its own review, project-owner approval, and hash freeze.
