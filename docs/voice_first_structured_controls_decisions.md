# Voice-First Structured Controls

> **Authority:** `APPROVED_PRODUCT_POLICY` | **Lifecycle:** `CURRENT` | **Canonicality:** Owner-agreed interaction and extraction decisions for `variant/intron`; not clinical rules.

Status: product decisions agreed with the project owner for `variant/intron`.
This is an interaction and extraction contract, not a change to the approved
clinical rules or a clinical-deployment authorization.

## Decisions

1. Voice-first does not mean voice-only. Dictation is the efficient way to report
   several findings; entry questions, follow-ups, corrections, and measurements
   may be entered directly when a tap or numeric value is more appropriate.
2. Make the existing assessment guide interactive. Do not add a parallel clinical
   form, schema, encounter, or completeness policy. Controls bind to the same
   canonical field paths already consumed by the deterministic engine.
3. Voice proposals populate those same guide controls. The original recording
   transcript, extracted candidate, English rendering, and source references are
   preserved separately from worker corrections and accepted evidence.
4. Controls are available without dictating first. Direct structured entry does
   not call ASR or a language model, and does not require consent to those remote
   services. Remote consent remains mandatory for actual provider processing.
5. Nullable booleans use explicit Yes / No / Not assessed choices. An unchecked
   checkbox must never mean absent. Untouched fields are not changes; an explicit
   Not assessed selection proposes UNKNOWN, not a negative observation. Selecting
   the same answer can explicitly reconfirm a measurement qualifier.
   Reuse existing guide-specific labels where polarity matters: the ability-to-
   drink row uses Able / Unable, mapped to the canonical inability field, rather
   than ambiguous Yes / No buttons beneath the opposite question.
6. Enumerated fields use their existing schema values with readable labels.
   Numeric fields use explicit canonical units and a numeric control. Blank is
   not zero, invalid input is not silently coerced, and no physiological threshold
   or new unit/temporal conversion is introduced by the UI.
7. JSON Schema describes valid values, not which observations must be known.
   Existing guide instructions/conditional structure remain the presentation
   source; deterministic missing fields, questions, validity, and completeness
   remain authoritative. Never hide a requested correction or discard recorded
   child findings merely because an entry answer is changed to No.
8. Shared observations have shared working values, not independent answers in
   different sections. Background clips must not overwrite worker edits. Multiple
   or conflicting proposals remain identifiable and are reviewed deliberately.
9. Review happens on the guide, in clinical controls, not in a wall of JSON or
   generic include/replace menus. Raw transcript, optional English rendering,
   source quotes, schema JSON, and provider/token metadata belong under Details.
10. Taps and voice proposals remain staged until explicit confirmation. Reuse
    the existing deterministic review/accept endpoints, serialized acceptance,
    stale-revision protection, uncertainty/conflict checks, and measurement
    episode guards. Do not auto-accept a voice report or infer missing values.
11. Captured and accepted progress are distinct. Show Awaiting confirmation when
    a recording or direct draft exists; do not imply that nothing happened or
    that the clinical assessment is complete. Accepted urgent guidance remains
    visible regardless of pending work or selected layout.
12. Desktop and mobile use the same controls, drafts, capture jobs, and clinical
    core. Navigation/rotation cannot discard edits or change the question a short
    recorded answer was addressing. The prior desktop checkpoint remains
    preserved while this interaction is tested in the preview.

## Explicit Negative Vomiting

The language-understanding contract must distinguish these cases:

| Source finding for the assessed child | `danger_signs.vomits_everything` |
| --- | --- |
| Not vomiting / no vomiting | `false` |
| Vomits everything | `true` |
| Vomiting, with no indication that everything is vomited | `null` |
| Not mentioned, ambiguous, or conflicting | `null` |

The negative case does not require the worker to say the word "everything".
Preserve subject and temporal qualifications; another person's finding, an
uncertain statement, or conflicting time-specific reports must not be turned
into a confident current observation. This is explicit language interpretation,
not a regex repair of model output or an IMCI classification rule.

## Implementation Boundaries

- Derive permitted control types/options/bounds from the existing model-facing
  schema, restricted to the application-supported fields. Units are display
  metadata, not an alternate clinical specification.
- Only touched direct values or actually extracted observations enter a proposed
  patch. Preserve UNKNOWN, false, zero, and same-valued reconfirmations distinctly.
- Preserve original voice evidence when a worker corrects or rejects it. A source
  quote supporting the original interpretation is not proof of a corrected value.
- Refresh review against the latest accepted encounter. Editing a working value
  invalidates prior confirmation; stale responses cannot restore old values.
- Keep asynchronous capture and the authoritative result-rendering gates. This
  iteration must not change classification, treatment, referral, or follow-up.

## Verification Checkpoint

Verify direct boolean/enum/numeric entry without provider calls; voice prefill
and correction on the same rows; explicit UNKNOWN; unknown/negative pathway
entries; hidden/shared findings; stale and overlapping captures; invalid numeric
input; measurement reconfirmation; mobile navigation and desktop preservation.
Test explicit negative vomiting in English and Nigerian Pidgin separately from
generic positive vomiting and silence. Injected tests prove contracts, not live
language accuracy; record live verification separately.
