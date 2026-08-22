# Product holistic golden language calibration — technical/editorial review v1

> **Authority:** `REVIEW_RECORD` · **Lifecycle:** `CURRENT` · Same-agent technical/editorial review; not human/domain or PHC-worker approval.

## Disposition

`PASS_TECHNICAL_ALIGNMENT_READY_FOR_HUMAN_LANGUAGE_REVIEW`

All 16 calibration records are mechanically pinned to the frozen semantic suite and, after the remediations below, explicitly render their required classifications, actions, missing-element acquisitions, urgency, deferrals, contradictions, or scope rejection.

The reviewed calibration SHA-256 is:

```text
4e05eae23aa7cc4a9371925035ee46564debf6bb004900fd37a4fefe606256b9
```

The frozen semantic source remains:

```text
9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f
```

This disposition does not freeze the language layer and does not authorize generation, product evaluation, teacher bake-off, training, or production clinical use. The calibration manifest continues to permit only domain review and component validation.

## Review method

For each record, the review checked:

- the exact frozen case identifier, suite hash, and case logic signature;
- complete, incomplete, urgent-incomplete, contradiction, and schema-rejection behavior;
- every final classification and immediate/final action;
- acknowledgement of actions deferred by an urgent workflow;
- every missing observation and its acquisition mode;
- the distinction between referral and urgent referral;
- preservation of generic treatment wording where no drug or regimen is encoded;
- absence of internal rule/action identifiers in user-facing text; and
- whether the PHC-worker submission made required negative evidence explicit rather than relying on silence.

Deterministic lexical checks now fail regeneration when an expected classification, action, acquisition, deferral, or contradiction cue is absent. These checks are deliberately bounded and do not claim unrestricted natural-language entailment.

## Findings and remediation

### LGR-T-001 — Dataset-author guardrails leaked into PHC-facing responses

Affected cases: `hpg-014`, `hpg-016`, `hpg-031`, and `hpg-052`.

Phrases such as “do not label” and “do not invent” correctly described repository guardrails but did not sound like direct assistance to a PHC worker. They were replaced with actionable language that preserves the same boundary: non-urgent referral remains explicitly non-urgent, and generic treatment actions refer to the applicable protocol without supplying an invented drug or regimen.

**Status:** `REMEDIATED`

### LGR-T-002 — Incomplete-state responses exposed implementation language

Affected cases: `hpg-071`, `hpg-072`, `hpg-073`, and `hpg-075`.

Wording such as “management synthesis is withheld” was technically accurate but unnatural. The responses now state directly which findings are still needed, what must happen immediately, and why a complete set of classifications and actions cannot yet be given.

**Status:** `REMEDIATED`

### LGR-T-003 — Alignment metadata alone could conceal a textual omission

The first calibration version required exact structured alignment but did not mechanically verify that the prose contained every aligned concept. Bounded marker checks now cover all classifications, actions, acquisition requests, urgent deferrals, and contradictions represented by these 16 cases.

**Status:** `REMEDIATED`

### LGR-T-004 — Category shorthand obscured explicit negative evidence

Several PHC-worker submissions said only “no general danger signs,” while their frozen inputs contained five explicit negative findings. Because unknown must never become negative, the canonical calibration inputs now enumerate ability to drink or breastfeed, vomiting everything, convulsions during the illness, lethargy/unconsciousness, and convulsing now.

Later language variants may test trained-worker shorthand, but only under an explicit interpretation policy and never by silently treating an omitted category as negative.

**Status:** `REMEDIATED_FOR_CANONICAL_CALIBRATION`

## Per-case result

| Case | State | Technical alignment | Human language review |
|---|---|---|---|
| `hpg-001-all-negative` | Complete | Pass | Pending |
| `hpg-008-resp-age-2-rate-50` | Complete | Pass | Pending |
| `hpg-014-resp-chest-hiv-positive` | Complete, referral | Pass | Pending |
| `hpg-016-resp-oximeter-89-9` | Complete, referral | Pass | Pending |
| `hpg-020-resp-post-bronchodilator-improved` | Complete, post-reassessment | Pass | Pending |
| `hpg-028-diarrhoea-some-dehydration` | Complete, Plan B | Pass | Pending |
| `hpg-031-diarrhoea-severe-age-24-cholera` | Complete, Plan C/local protocol | Pass | Pending |
| `hpg-052-fever-identified-bacterial-cause` | Complete, generic antibiotic | Pass | Pending |
| `hpg-055-fever-severe-measles-cornea` | Complete, urgent | Pass | Pending |
| `hpg-068-cross-four-pathways` | Complete, integrated | Pass | Pending |
| `hpg-070-cross-multiple-urgent` | Complete, multiple urgent | Pass | Pending |
| `hpg-071-incomplete-entry-unknown` | Incomplete | Pass | Pending |
| `hpg-072-incomplete-multiple-groups` | Incomplete, batched acquisitions | Pass | Pending |
| `hpg-073-incomplete-known-urgent` | Incomplete, urgent | Pass | Pending |
| `hpg-075-contradiction-drinking` | Incomplete, contradiction | Pass | Pending |
| `hpg-077-out-of-scope-age-1` | Schema rejection | Pass | Pending |

The CSV companion contains the same 16 case dispositions.

## Remaining human-review gate

A human reviewer should now read `product_holistic_golden_language_calibration_review_v1.md` and disposition each case for:

1. semantic faithfulness in ordinary language;
2. clarity and action prioritization;
3. naturalness for the intended PHC-worker interaction;
4. usefulness and burden of the complete-case input wording;
5. clarity of grouped acquisitions and acquisition modes; and
6. overall EdgeIMCI voice.

Particular attention should be given to `hpg-068` because it tests a long integrated management response, and `hpg-070` because its wording must faithfully carry the frozen mastoiditis action set without suggesting a different semantic decision. If either review exposes a genuine semantic problem, that must enter semantic change control rather than being silently repaired in the language layer.

## Independence limitation

The same coding agent authored and performed this technical/editorial review. The review is useful for deterministic alignment and editorial cleanup, but it is not independent evidence of clinical correctness, PHC usability, or preferred product voice.
