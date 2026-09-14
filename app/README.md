# EdgeIMCI prototype application

## Intron voice variant

This worktree is the long-lived `variant/intron` app variant, based on
`feature/demo-workstation-integration`. The original assessment interface and
deterministic clinical engine remain in place. The scoped demo uses **remote
Intron ASR and Azure OpenAI language understanding**, with local evidence review,
encounter state, workflow checks, clinical rules, and rendering. The native
whole-report text route still uses the existing Modal extractor. This is an
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

### Assessment loop

1. Open **Guide** and choose **Add voice or text findings** inside an existing
   assessment section. Age remains the shared first check.
2. Read the network disclosure. Record a short report, stop, and review playback.
   Clips stop at 60 seconds and are limited to 5 MB. Click **Transcribe audio**.
3. The original transcript remains read-only. Correct the separate editable
   input if necessary, consent to language understanding, then **Interpret section
   findings**. Typed section reports use the same understanding provider.
4. Review every proposed observation. Explicitly resolve changes to known values
   and observations outside the selected section. Reject unsupported findings.
   The optional English rendering, source quotes, and full report-only canonical
   candidate are available in the expandable language-review details.
5. Apply reviewed evidence. Accepted state is validated and evaluated locally.
   The existing engine supplies missing requirements and urgent actions.
6. Answer the one displayed targeted question, then repeat review and acceptance.
   A clip or transcript never counts as clinical completeness.

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
before acceptance. Full-assessment text entry remains available, but confirmation
of a full report explicitly replaces the encounter; use section capture to merge
incremental findings.

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
