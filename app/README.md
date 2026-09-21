# EdgeIMCI prototype application

## Text-Only Intake Variant

The current interface on `variant/text-only-intake` requires a patient name and
age in completed months (2-59) before assessment. Patient name is local tab
metadata, never automatically added to the clinical schema or interpretation
requests. Text explicitly containing a name is still submitted as written: use
synthetic names and reports for this prototype, not identifying clinical data.

The three-panel interface retains tappable clinical controls, the text editor,
and deterministic results. There are no recording controls, microphone requests,
speech-language selectors, or provider branding. Main assessment text and inputs
are larger, with at least 48px action targets. Other clinical observations remain
nullable; required intake age cannot be cleared with Not assessed.

Use **Edit patient details** to correct intake later. Changes are validated and
re-evaluated before name and age are committed together. Failed or stale saves
leave the current patient unchanged; accepted clinical facts, pending reports,
and typed drafts are preserved. Resuming older assessments without a name
requires completing intake, with the saved age prefilled.

```bash
npm --prefix web ci
npm --prefix web run build
uv run --extra azure --extra modal-training python scripts/run_text_demo.py
```

The text launcher uses the authorized Azure resource and keeps its credential in
process memory, or uses an existing `EDGEIMCI_FRONTIER_API_KEY`. No speech key is
needed. `--port` and `--static-root` allow an isolated preview without overwriting
older builds. Browser tab storage is not a secure or durable patient-record store.

Previous checkpoints remain in Git: `9148a17e` is tappable/voice, and `24528e4b`
adds the text panel. The historical integration notes below describe those
earlier variants; they do not enable audio in this interface.

## Earlier Voice Variant

The implemented interaction decisions are recorded in
[`docs/voice_first_structured_controls_decisions.md`](../docs/voice_first_structured_controls_decisions.md):
voice and direct answers use the existing guide's canonical fields, with explicit
confirmation and no competing clinical form or requirements engine.

This worktree now contains the additive `variant/intron-text-panel` iteration,
based on the preserved tappable/voice checkpoint `9148a17e` on `variant/intron`.
The deterministic clinical engine remains in place. The demo uses **remote
Intron ASR and Azure OpenAI language understanding**, with local evidence review,
encounter state, workflow checks, clinical rules, and rendering. The native
whole-report API still uses the existing Modal extractor, but the restored middle
text panel uses the configured language-understanding provider, not that legacy
API. This is an
intentional demo bypass, not fully offline inference or the final architecture.

```text
assessment-scoped audio -> Intron -> original code-switched transcript
    -> LanguageUnderstandingProvider (Azure GPT-5.2 for the demo)
    -> report-only canonical evidence + optional English rendering + uncertainties
    -> worker review -> accepted encounter -> deterministic completeness / IMCI
```

English rendering is never authoritative and never replaces the original ASR
transcript. The canonical schema, validation, thresholds, clinical engine, and
clinical result rendering are not changed by the bypass. The external model
receives no clinical rule set and cannot return classification/action fields in
its schema-constrained evidence result.

### Run the demo

Run these commands from the `edge-imci-intron` worktree, not the original checkout:

```bash
npm --prefix web ci
npm --prefix web run build
uv run --extra azure --extra modal-training python scripts/run_intron_demo.py
```

Open `http://127.0.0.1:8000`. Configure `INTRON_API_KEY` in the owner-only `.env`
file (permissions `600`). The launcher uses the existing Azure CLI login to
retrieve a key for the explicitly authorized `openai-sota` resource in resource
group `synthetic-data-generation`; it holds that key only in process memory.
It does not print or persist it, rotate keys, or pass credentials in command
arguments. The selected deployment is `gpt-5.2` (inspected version `2025-12-11`).
The native full-report path separately requires the existing Modal deployment
and authentication. Modal is not called for scoped reports in frontier mode.

Alternatively, configure `EDGEIMCI_FRONTIER_API_KEY` in the environment or the
owner-only dotenv file and run:

```bash
uv run --extra azure --extra modal-training python -m app --language-understanding frontier --env-file .env
```

Without a frontier key the provider uses Azure CLI identity for the data plane;
this requires the appropriate Azure data-plane role. Management access alone
was insufficient in the live check. Optional `EDGEIMCI_FRONTIER_ENDPOINT` and
`EDGEIMCI_FRONTIER_MODEL` select another explicitly configured Azure deployment.
The dotenv loader reads only supported settings, never executes shell syntax,
and does not change the research generation/authorization configuration. Never
put credentials in a `VITE_*` variable or browser code.

To explicitly restore the previous scoped Qwen route, use
`--language-understanding native`. This native adapter is not the future
normalization-plus-local implementation; it simply preserves the existing path.

Language is deliberately not configured globally. Intron requires it on every
ASR request, and the health worker must select one for each recording: English
(`en`), Nigerian Pidgin-English (`pcm`), Yoruba-English (`yo`), Igbo-English
(`ig`), or Hausa-English (`ha`). The server rejects missing and unsupported
codes before audio is read or sent to Intron. This permits different clips and
benchmark cases to use different languages without restarting the application.

The intended provider is **Intron Sahara 2.5**. The public
[file upload](https://docs.voice.intron.io/docs/stt/file-upload) and
[file status](https://docs.voice.intron.io/docs/stt/file-status) APIs expose no
documented model-version selector or verifiable model version in the response.
The adapter therefore reports `provider="intron", model=null`; it does not invent
a version pin. Confirm endpoint-to-Sahara-2.5 mapping with Intron before recording
a version-qualified benchmark. LLM transcript corrections and diarization are
disabled; the API is used only for transcription, not clinical post-processing.

### Text-panel checkpoint

Desktop has three panels: the tappable assessment guide, a whole-report text
editor, and clinical results. On mobile, **Write text** or **Text report** opens
the same mounted editor without replacing the guide or interrupting voice work.

1. Type or paste findings and select **Interpret text**. This submits an explicit
   `full-note` capture through `/api/assessment/extract`; no follow-up question is
   attached and no ASR call is made.
2. Proposed answers appear in the existing guide, marked **From text**. Use those
   controls to inspect and correct findings, including conflicts with other drafts.
3. Return to the report and **Confirm findings**. Confirmation uses the existing
   deterministic review/accept endpoints and sparse-patches the accepted encounter.
   Omitted findings do not erase prior answers. The five clinical assessments and
   clinical rules are unchanged; `full-note` is only a capture/review scope.
4. **Generate IMCI recommendations** remains available. Unprocessed text and
   unconfirmed proposals still require review or discard before generation.

Clearing the text editor does not discard submitted reports, recordings, manual
edits, or accepted findings. Discarding a report affects only that report. The
original tappable-only version remains available from commit `9148a17e`.

### Assessment loop

1. Start on **Assessment**. Existing guide rows are now controls: Yes / No /
   Not assessed, schema enum choices, and numbers in explicit units. They work
   without dictation or remote-service consent. Mobile uses deployment-authorized
   processing: choose a language beside Speak, without a setup page or processing
   checkboxes. Desktop uses the same deployment authorization. Each clip freezes its language
   and authorization when recording starts.
2. Use **Record findings** beside the relevant assessment, then **Stop**. Continue
   scrolling or record the next section immediately. Stop automatically queues
   transcription and structuring; there is no separate Transcribe button.
3. The section shows Recording, Processing, then Captured. One microphone is used
   at a time, with up to two ASR/understanding pipelines processing concurrently.
   Additional clips queue. Clips in the same or different sections are retained
   independently and may finish out of order without moving the current view.
4. Voice suggestions populate those same guide controls, tagged **From recording**.
   Correct an answer by tapping it or entering a number; corrections are tagged
   **Your answer**. Shared fields use shared working values. Conflicting recordings
   never silently choose a winner, and arriving recordings do not overwrite worker
   edits. **Review on assessment** explicitly selects another report when needed.
    Original transcripts remain readable; engineering records are retained
    internally rather than exposed as JSON or conversion dumps.
5. **Confirm findings** explicitly applies the selected report/direct draft.
   Only acceptance is serialized, not capture or navigation. The pure
   `/api/assessment/review` operation prepares effective proposals against the
   latest accepted encounter without a model call. Original model evidence and
   worker corrections remain separate in the interaction trace. Changed context,
   edit versions, or conflicting pending evidence invalidate old confirmations.
   All existing schema, stale-previous, scope, and measurement guards still apply.
6. Accepted state is evaluated locally. Required follow-ups appear beside the
   section. Record short answers and repeat review as needed. A clip, transcript,
   or Captured status never constitutes clinical completeness.

`GET /api/assessment/schema` derives valid control types, options, declared bounds,
and display units from the unchanged canonical schema, limited to supported fields.
It does not define required-known observations. The existing guide supplies
instructions and display labels; the deterministic evaluator supplies missing
fields and completeness. In particular, the ability-to-drink row uses the existing
Able / Unable labels so its answers cannot invert the canonical inability field.
Unknown pathway entries initially show the entry question, not a wall of unknown
conditional checks. Yes reveals the applicable guide. Known or pending child
observations remain visible for explicit resolution if the entry changes to No.

Blank numeric input is not zero. Invalid input blocks confirmation and stays in
the working draft. Not assessed is an explicit null proposal; untouched fields
are omitted from direct updates. Same-value taps can reconfirm measurement
qualifiers. Direct answers use no ASR or language-model call, though the local API
must be reachable to validate and confirm them.

The v2 language-understanding prompt explicitly maps **not vomiting / no vomiting**
for the assessed child to `danger_signs.vomits_everything=false`, including the
equivalent Nigerian Pidgin report. Generic positive vomiting without the
"everything" qualifier remains unknown. English and Pidgin negative cases and
an English generic-positive control were verified with the live Azure provider;
this is not a general semantic-accuracy qualification or a local regex override.

The desktop workspace has two panels: a wide assessment guide with evidence
alongside its procedures, and classification/management. The dedicated phone
presentation below shares the same capture jobs and accepted state. Global
Stop/Cancel and accepted urgent guidance remain accessible while moving.

### Mobile presentation

The same app now has a dedicated phone layout rather than a compressed desktop
workspace. It selects mobile presentation at widths up to 900px. Use
`?layout=mobile` or `?layout=desktop` to explicitly preview either presentation.

- Home shows the existing five assessments, authoritative progress, and separate
  capture/dirty states. Age remains shared; no new clinical assessment is added.
- Selecting an assessment opens its Assessment and Recordings views. The bottom
  recording control always names the recording's actual assessment and language,
  including when the worker visits another screen while recording.
- Results is a separate screen. Language selection is inline with Speak; the
  mobile workflow assumes the configured processing authorization. Browser
  microphone permission still applies. Transcription/structuring starts
  automatically on Stop, followed by explicit evidence review and acceptance.
- There is one session, one capture queue, and one mounted editor per assessment.
  Navigation and viewport changes hide/reveal those same editors; they do not
  duplicate or remount them. Typed drafts, original questions, review choices,
  and background jobs remain intact. Desktop expansion state is retained too.
- Accepted urgent guidance, errors, and interruption notices remain global.
  Mobile uses the same quiet-result and final-plan gates as desktop. No clinical
  logic, provider behavior, or canonical schema differs by layout.

The mobile opening screen now starts with the five General Danger Signs, using
the same guide controls in a compact presentation, plus inline language selection,
a large **Speak** action, and **Continue**. Speak requires a selected language;
choosing one never starts recording automatically. Continue opens the symptom overview
without confirming drafts. The introductory recording is assessment-scoped,
not bound to a hidden age question. If its candidate includes age or other
observations beyond the visible five, **Review other findings** opens the full
review before those additional values can be confirmed.

Mobile numbers are value buttons: tap to open the same numeric input/keypad,
then Done to close it. Raw/invalid digits remain in the shared draft; Done and
blur never accept evidence. Age is kept in one stable scope editor, hidden on
the opening screen and available later in the overview/review. Its absence
still blocks final completeness exactly as before.

Mobile confirmation is a compact action with a red incomplete indicator derived
from accepted deterministic category progress, not model confidence or a guessed
clinical severity. Partial findings remain confirmable. Routine dock subtext,
the large Awaiting confirmation box, and mobile technical/JSON views are removed.
Human-readable source text, ambiguity, failures, and accepted urgent guidance
remain available; original diagnostic provenance is still retained internally.
The overview ends with **Show results**, which navigates only and does not accept
pending findings, rerun the model, or bypass final-result gates.

The mobile Recording setup page is removed. Both mobile and desktop authorization
are deployment assumptions requested by the owner, not stored claims of individual
consent. Neither layout has processing consent checkboxes. The overview's Assessment
options contains About processing, recording history, and Start new assessment.

Normal opening-screen fit was checked at 390x844 and 320x568. Scrolling remains
available for accessibility zoom, errors, or urgent guidance. A speed benefit
has not been established by these layout checks and still needs measurement.

To develop mobile while keeping a built desktop checkpoint running on port 8000:

```bash
npm --prefix web run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173/?layout=mobile` for the phone preview, or
`http://127.0.0.1:5173/?layout=desktop` for desktop comparison. Vite proxies API
requests to the existing server on port 8000, but does not replace `web/dist`.
The two origins have independent tab drafts; this is not cross-device encounter
synchronization. Resizing within the preview preserves that tab's session.

Physical-phone microphone testing needs an authenticated, HTTPS-accessible URL.
The loopback preview addresses are for the development machine, not a public
deployment. The browser checks use a simulated Chromium microphone and mock
speech/model responses with the real local review/evaluation endpoints.

Startup still evaluates the all-unknown encounter to obtain authoritative
requirements; this is not a clinical-engine defect. The old UI prematurely
rendered that initialization result. The new result panel stays neutral without
accepted observations (including restored history-only drafts), shows a compact
in-progress state for incomplete accepted findings, and shows the full routine
plan only when accepted evidence is complete and all new captures/edits have
been reviewed or discarded. Accepted urgent guidance is never hidden by these
presentation gates. No additional clinical classification/finalization rule is
introduced.

For a respiratory demonstration, provide age and general danger signs explicitly,
then report cough duration, rate, chest indrawing, wheezing/history, calm/full-minute
measurement validity, and oximeter availability, deliberately omitting stridor.
The section should remain incomplete and ask about stridor when calm. After that
answer, the section may complete; final holistic synthesis still requires all
applicable encounter assessments. Do not fill unrelated unknowns with negatives
just to finish a demonstration.

A new breathing count cannot inherit an older count's validity. When repeating
a measurement, explicitly report the rate, calm status, and full-minute counting
together. Reconfirmations may appear in the review even when their values match
accepted observations. Repairing an invalid count requires a repeated count,
not simply a later statement that the child is calm.

Known values can also be explicitly retracted to UNKNOWN in the section's accepted
evidence controls, without requiring successful ASR or model extraction. Extracted
nulls alone are omissions, not retractions. Candidate conflicts must be resolved
before acceptance. The old full-assessment text endpoints remain available for
native callers, but their large middle-column workflow is removed from this
voice interface. Section input and retractions are incremental, not whole-state
replacement.

### Boundaries and limitations

- Accepted findings and an interaction trace are saved in this tab's versioned
  `sessionStorage`. The trace retains recording IDs, ASR language/provider/model,
  raw transcript, edited input, optional English rendering, canonical candidates,
  warnings/uncertainties/source quotes, review choices, failures/rejections,
  before/after state, requested clarification, and deterministic result snapshots.
  Audio is not persisted. Historical results are never promoted to current
  guidance: accepted input is re-evaluated on reload. Clear encounter deletes
  the draft and history. Storage failure invalidates an older saved snapshot
  where possible and warns explicitly; full state remains in memory. This is
  not an encrypted clinical store, durable audit system, or multi-worker system.
  Use synthetic/de-identified demo data only.
- Reopening a tab with saved evidence now requires an explicit **Resume saved
  assessment** or **Start new assessment** choice. Saved answers are not populated
  into a fresh-looking intro by default. Resume re-evaluates the saved clinical
  input; starting new clears that tab's prior evidence/history only after
  confirmation and initializes every observation as unknown.
- The encounter-wide `decision=URGENT` interrupts ordinary questioning, but is
  not a section's clinical status. Section badges use only their own `status`.
  Global urgent guidance remains visible, and genuine urgency in another active
  pathway is retained when produced by the existing engine.
- Confirmed immediate-management actions appear in the clinical-result panel
  before the full assessment is complete, including while another recording is
  pending. They come directly from the accepted engine response. Final
  classifications and the complete plan remain withheld until their existing
  completeness/review gates pass; no diagnoses or treatments are inferred in UI.
- Desktop and mobile hide engineering output: raw JSON, schemas, field/rule IDs,
  conversion dumps, and processing traces. Readable transcripts, recording
  history, ambiguity review, and clinical explanations remain available. Original
  diagnostic records are retained internally, not deleted or shown as user output.
- A compact recording-progress strip remains visible after Stop, across collapsed
  assessments, scrolling, and mobile navigation. It follows actual transcription,
  structuring, review, and confirmation stages, with independent rows for parallel
  recordings. Ready for your review opens existing controls without accepting
  findings; failures link to recovery rather than leaving an endless spinner.
- The duplicated top management banner is removed. Urgent guidance is displayed
  once in the result panel; mobile has a small Urgent results navigation button.
- **Generate IMCI recommendations** is available at the bottom of the desktop
  guide and mobile overview. It runs a deterministic check on confirmed findings,
  including empty/incomplete encounters, and displays the engine's missing-check
  instructions when a final plan cannot yet be produced. It does not call ASR or
  a language model, mark unattempted sections complete, or auto-confirm drafts.
  Pending recordings/edits route back to review first. Failed checks remain
  retryable, and requested incomplete reports are tied to the evaluated revision.
- Audio and active capture jobs are memory-only. Leaving/reloading with unfinished
  captures or local edits triggers a browser warning. After reload, interrupted
  captures are identified visibly and remain a final-plan blocker until explicitly
  acknowledged; their unaccepted evidence is not applied or replayed automatically.
  Historical transcripts remain available for inspection. Clearing an encounter
  cancels its jobs and ignores late replies, including replies from an older
  patient/session. Retries retain the original source/question and processing
  permission. Failed acceptance receipts survive retry/discard.
- Intron receives audio; Azure receives scoped text plus assessment/question and
  accepted-state context. Modal receives native full-report text. Azure requests
  use `store=False`; provider-side policies still apply, and browser deletion
  does not delete provider data.
- Missing ASR credentials, failed transcription, or microphone denial leaves text
  input available. Extraction failure leaves accepted findings and urgent guidance
  intact. Azure is required for scoped language understanding, not for local
  acceptance/evaluation or the native full-report route. No silent fallback is
  used when the frontier provider fails.
- Stub mode supports the existing whole-report fixtures, not arbitrary scoped
  reports. Automated unit tests inject speech/understanding doubles; those tests
  alone are not accuracy benchmarks or live-provider evidence.
- Browser recording requires localhost or HTTPS. For non-local demos, put the
  server behind authenticated HTTPS and set `EDGEIMCI_ALLOWED_ORIGINS` to explicit
  comma-separated origins. The app rejects foreign browser origins/hosts and
  non-JSON requests to JSON endpoints, but is not an authenticated production
  service. Localhost and the documented Vite port 5173 are allowed by default.
- Client cancellation ignores late results and preserves accepted state; it does
  not cancel an already-submitted provider job or guarantee avoided billing.
- The frontier provider makes one bounded Responses call (45-second SDK timeout,
  6,000 output-token ceiling, SDK retries disabled). Invalid JSON, refusal,
  incomplete output, schema failure, missing/invented source quotes, or a known
  value carrying a field-specific uncertainty is rejected. No JSON repair or
  automatic retry occurs. A manual retry can incur another charge.
- Every non-null frontier observation needs a literal source quote, but a valid
  quote/schema is not proof that the model interpreted meaning correctly. Worker
  review remains mandatory. 'Vomiting' does not establish 'vomits everything';
  'since yesterday' does not become an exact day count. Field ambiguities remain
  null and create explicit review choices, including when old evidence exists.
- The existing Qwen extractor remains provisional and unreliable on some sparse
  English reports. It is deliberately bypassed for this milestone. Multilingual
  ASR support does not imply that any downstream local extractor is qualified.
- Clinical scope remains the existing 2-to-under-60-month initial assessment:
  danger signs, respiratory, diarrhoea, fever/measles, and ear. No nutrition/anaemia
  or longitudinal Plan B/C clinical implementation has been added.
- The clinical core is unchanged. Known pre-existing partial-evidence limitations
  include pathway-entry gating and measles activation requiring some additional
  observations even with positive rash/cough evidence. This variant does not
  claim to fix those semantics or provide universal early-urgency detection.
  Intake blockers prevent silent completion for findings under an absent entry;
  they do not invent a classification or referral. The contradiction-rendering
  crash was fixed so already-computed urgent actions remain renderable.

### Variant verification

```bash
uv run --extra dev --extra azure --extra modal-training python -m pytest tests/test_frontier_assessment.py tests/test_language_understanding.py tests/test_assessment_workflow.py tests/test_assessment_api.py tests/test_speech_provider.py tests/test_prototype_app.py tests/test_holistic_major_sick_child.py tests/test_structured_extraction_architecture.py
npm --prefix web test
npm --prefix web run build
```

Before variant edits, the isolated committed base had **554 passing and seven
failing Python tests**. Those seven fail in research matrix/registry and candidate
checks because `configs/generation/holistic_teacher_bakeoff_v1.json` does not match
its recorded registry digest. The original dirty checkout had the corresponding
uncommitted research changes and passed its larger suite. The variant deliberately
does not import that work or rewrite research provenance to hide the mismatch.

The optional bounded live smoke check below makes at most six scoped Azure calls
through the running server. It checks fixed synthetic proposals against expected
facts before simulating acceptance; that test harness is not an auto-accept path
in the application. It tests English/Yoruba-English transcripts, not audio:

```bash
python scripts/check_frontier_demo.py --live
```

Live verification completed during implementation:
- English and Yoruba-English reports plus contextual stridor answers produced
  matching canonical evidence and identical deterministic pneumonia outputs.
- 'The child is vomiting since yesterday' retained unknown danger-sign status and
  temporal ambiguity, without inventing a numeric duration.
- Synthetic English audio passed through Intron, GPT-5.2, checked review,
  incomplete status and stridor clarification, then deterministic final output.

These are small smoke checks, not multilingual clinical qualification. A real
Yoruba-English recording and physical-browser microphone/review checks remain
necessary before declaring the bilingual speech milestone complete.

### Demo recording checkpoint

Use the scripts' explicit synthetic cases as a recording plan: establish the
stated age/danger-sign/other-entry evidence, record the respiratory findings,
inspect raw transcript and candidate evidence, apply the reviewed findings,
show the stridor question, answer it, and show the deterministic result. Repeat
with a speaker-reviewed Yoruba-English recording. Do not fill omissions merely
to obtain a complete demo. Once these runs are stable, record the clean demo
before adding further architecture. No screen recording has been created by
these smoke checks.

### Deferred local work

The common boundary is `LanguageUnderstandingProvider.understand(...)`, returning
`CanonicalEvidenceCandidate`. After the demo is recorded:
1. Implement `NormalizationThenLocalExtractorProvider`: constrain normalization,
   feed its English text into the existing extractor, and return this same
   candidate contract. Compare against the bypass on the same saved transcripts;
   explicitly retest sparse-input and meaning-preservation failures.
2. Only after qualification, implement `DirectMultilingualLocalExtractorProvider`
   behind the same interface, with no English intermediate requirement.
3. Compare identical source recordings/transcripts for unsupported inferences,
   negation, quantities/durations, ambiguity, clarification, and deterministic
   IMCI agreement. Neither future provider nor a comparison framework is
   implemented in this milestone.

The following commands describe the preserved native workstation path.

## Native workstation run

Build the frontend once, then serve the API and static bundle together:

```bash
cd web
npm install
npm run build
cd ..
PYTHONPATH="src:." python -m app --language-understanding native
```

Open `http://127.0.0.1:8000`.

The native text extractor defaults to the selected Modal checkpoint. Deploy the
pinned function once, then start the workstation:

```bash
uv run --extra modal-training modal deploy \
  -m edge_imci.inference.modal_structured_extraction
uv run --extra modal-training python -m app --language-understanding native
```

The browser never receives Modal credentials. The backend accepts model output
only when the run ID, weights checksum, JSON parse, and model-facing schema all
match the selected candidate, then reruns the authoritative deterministic
adapter, evaluator, and approved response renderer locally.

## Frontend development

Run the Python service and Vite server in separate terminals from the repository
root:

```bash
uv run --extra azure --extra modal-training python scripts/run_intron_demo.py
```

```bash
cd web
npm install
npm run dev
```

Vite proxies `/api` requests to `http://127.0.0.1:8000`.

## Verification

```bash
PYTHONPATH="src:." python -m pytest tests/test_prototype_app.py
cd web
npm test
npm run build
```

Stub mode recognizes only the five frozen fixture submissions. Modal mode sends
free-form findings to the provisionally selected research checkpoint. Neither
mode is authorized for production clinical use.

Use `--extractor stub --language-understanding native` for deterministic offline
whole-report fixture development.
