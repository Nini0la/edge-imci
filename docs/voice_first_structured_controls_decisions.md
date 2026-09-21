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
   services. Remote processing must be authorized: the app uses the owner's
   configured deployment preauthorization on both mobile and desktop.
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

## Mobile Simplification Checkpoint

The current mobile/control implementation was preserved in commit `29372e32`
before the project owner approved this mobile-only simplification:

- Open directly on the existing five General Danger Signs rows, with concise
  labels and a large Speak action. Aim to fit those rows without scrolling in
  normal phone viewports; retain scrolling for zoom, errors, or urgent guidance.
- Continue leads to the main assessment overview. Age remains UNKNOWN until
  explicitly supplied; collecting it later does not relax completeness or scope.
- Use Speak instead of Record findings on mobile. Remove routine instructional
  subtext from the dock. Keep active recording identity, language, recoverable
  errors, provider consent, and accepted urgent guidance available.
- Replace permanently exposed numeric textboxes with a value button that opens
  the existing numeric input/keypad. Closing it only stages the value; it does
  not accept evidence. Keep partial/invalid raw input and explicit UNKNOWN.
- Confirmation is a compact action, not an Awaiting confirmation panel. An
  incomplete indicator is red, based on deterministic accepted assessment
  progress, distinct from clinical urgency. Partial findings remain confirmable.
- Do not render JSON, schemas, provider/token metadata, or internal field IDs in
  the mobile workflow. Retain diagnostic provenance internally. Human-readable
  transcripts, ambiguity, and correction feedback remain available when needed.
- Put a conspicuous Show results action at the bottom of the overview. It opens
  the existing results view; it neither reruns the language model nor silently
  confirms drafts. Final-output safety gates remain unchanged.
- Reuse shared danger-sign observations downstream only through existing canonical
  fields and approved engine behavior. No inferred negatives or duplicated state.
- A speed advantage is a hypothesis to measure, not a claim established by this
  layout change. Desktop presentation and clinical logic are outside this pass.

## Reopening and Urgency Corrections

- Do not silently resume a saved encounter into the first-screen layout. Offer
  Resume or Start new before showing any saved selections. Resume requires fresh
  deterministic evaluation; Start new explicitly clears the prior tab draft.
- Separate global workflow interruption from per-assessment status. An urgent
  encounter must not label every category urgent. Badge urgency comes from the
  category's own engine-derived status, while the global urgent-care banner and
  existing clinical cross-pathway dependencies remain authoritative.
- Regression tests must cover false-valued saved evidence, resume/reset races,
  and nonurgent category statuses paired with a global urgent decision. Earlier
  tests covered persistence and urgency independently but missed these combined
  presentation cases.

## Inline Mobile Speech Controls

The owner subsequently removed the mobile Recording setup page and per-encounter
processing checkboxes. The mobile deployment assumes authorization to send audio
to Intron and text/encounter context to the configured understanding provider.
This is deployment policy, not evidence that an individual checked a consent box;
privacy obligations for real clinical deployment remain outside this demo UI.

- Language is chosen explicitly beside Speak, beneath the danger-sign rows. No
  default language is silently sent, and selecting a language does not record.
- Speak and language form one control group, with no large empty region between
  the assessment and the speaking action. The active clip keeps its original
  language; changes after Stop affect only subsequent recordings.
- Mobile answer buttons are enlarged and separated enough to contain their text.
  Browser microphone permission, readiness, confirmation, uncertainty handling,
  and deterministic clinical validation are unchanged.
- About processing, recording history, and Start new assessment remain reachable
  under Assessment options on the overview, without an intervening setup page.
- At this checkpoint desktop retained its separate opt-in; the subsequent shared
  deployment authorization decision below supersedes that distinction.

## Shared Deployment Authorization

The owner subsequently confirmed that the same pre-authorized use case applies
to desktop. Both layouts now use deployment authorization for audio and language
understanding, with no per-encounter processing consent checkboxes. This supersedes
the earlier desktop opt-in distinction above. Language remains explicit, browser
microphone permission still applies, and confirmation of clinical evidence is
unchanged. About processing remains available without blocking the workflow; the
application does not claim that an individual checked or signed consent.

## User Results and Recording Details

- Confirmed urgent actions must appear in the clinical-result panel and remain
  reachable from mobile assessment screens. Do not wait for age or the remaining assessment to
  show the engine's immediate-management actions. Pending recordings and edits
  do not remove accepted urgent guidance or become accepted evidence themselves.
- The immediate-management panel uses only the accepted evaluation's urgent
  actions. It does not infer classifications, treatments, or missing findings.
  Final classifications and the complete plan still require a valid, complete,
  in-scope assessment with no outstanding review, interruption, or evidence
  blocker. An urgent workflow decision must not hide an underlying blocker.
- Both desktop and mobile are user interfaces, not engineering consoles. Do not
  render raw candidates, JSON, control schemas, field/rule IDs, provider metadata,
  English conversion dumps, or processing traces. Preserve the underlying source
  records for engineering diagnostics without adding a user-facing debug switch.
- Keep a concise, read-only transcript and recording history for source review,
  with ambiguities and actionable answer choices. Avoid repeating the same report
  as transcript, submitted input, and raw candidate. Technical provider warnings
  become a plain-language review reminder; original warnings remain stored.

## Recording Progress and Single Results View

- Show processing status outside collapsible assessments and scrolling content,
  on desktop and mobile. Use actual capture stages, not a fake percentage or
  timer: queued, turning the recording into text, adding findings to the
  assessment, preparing review, and confirming the worker's findings.
- Keep Ready for your review distinct from accepted evidence. Review opens the
  existing assessment controls; it never confirms findings. Failures show an
  attention message with a route to the existing retry/review controls, not an
  endless spinner or raw provider error in the status strip.
- Parallel recordings retain independent statuses and assessment labels. Accepted,
  cancelled, discarded, or reset recordings leave the strip. Direct structured
  answers do not pretend to be recordings undergoing remote processing.
- Remove the duplicated top management banner. Clinical guidance lives once in
  the results panel, including accepted urgent actions while new work is pending.
  On mobile, a small Urgent results navigation button keeps that guidance
  reachable without repeating the assessment or management above the workspace.
- Processing animation respects reduced-motion preferences; stage changes are
  announced through a persistent live region. No clinical rules or acceptance
  behavior change.

## Explicit Assessment Generation

- Restore a prominent Generate IMCI recommendations action at the bottom of the
  desktop guide and mobile overview. On mobile this replaces the former Show
  results button; Results navigation elsewhere remains navigation only.
- This action checks confirmed findings with the deterministic assessment service,
  not ASR or a language model. It checks the entire supported encounter, including
  sections not yet attempted, without marking those sections assessed.
- Empty and incomplete assessments may be submitted for this check. Show the
  engine's readable missing-information response after a successful check, rather
  than leaving the worker with a generic Assessment in progress message. Final
  classifications and complete management remain withheld until truly complete.
- Pending recordings, direct-answer edits, typed drafts, interrupted captures, and
  evidence blockers do not get silently accepted or ignored. Explain the pending
  review and offer routes back to the relevant assessment controls first.
- Bind explicitly requested incomplete reports to the successful evaluation's
  revision. Loading, failed requests, newer accepted findings, and encounter reset
  must not expose an old report as the newly generated recommendation. Preserve
  accepted urgent actions independently while routine results remain gated.

## Additive Text-Panel Checkpoint

The tappable/voice checkpoint remains `9148a17e` on `variant/intron`. The additive
text-panel iteration is developed separately on `variant/intron-text-panel`.

- Restore the desktop middle panel as a whole-assessment text editor, alongside
  the existing tappable guide and clinical results. Do not restore the old
  replace-the-entire-encounter confirmation behavior or remove voice capture.
- On mobile, Write text and Text report navigation open the same mounted editor;
  changing layouts or navigating does not clear its draft or other working answers.
- Interpret text uses the configured understanding provider through the existing
  assessment extraction endpoint, with explicit `full-note` capture scope and no
  follow-up question. It does not switch back to native whole-note extraction.
- `full-note` is an input/review scope, not a sixth clinical assessment. Schema
  field ownership, clinical progress, and attempted assessments remain the five
  existing supported assessments. Age alone does not mark all sections attempted.
- Report proposals populate the existing guide controls with From text provenance.
  Corrections attach to that report while preserving its original text/candidate.
  Confirming the report atomically applies only explicitly reviewed observations;
  omitted findings never clear unrelated accepted evidence.
- Voice, text, and direct edits coexist. Conflicts, stale revisions, uncertainty,
  and measurement-episode guards apply equally to whole-report confirmation.
  A full report still being interpreted blocks confirmation until its potential
  overlap is known. There is no automatic acceptance of extracted findings.
- Unprocessed report text and unconfirmed report jobs keep recommendation
  generation gated. Clear text affects only the editor draft; discarding a report
  affects only that job. Reset cancels all encounter work and ignores late replies.
- No engineering JSON, schemas, or provider internals are reintroduced into the
  worker interface. Readable original reports and shared progress remain available.
