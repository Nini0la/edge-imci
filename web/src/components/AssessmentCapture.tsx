import { useEffect, useRef, useState } from "react";
import { extractAssessment, transcribeAudio } from "../lib/api";
import { affectedAssessments, createRequestGate, unresolvedChanges, workerRetraction } from "../lib/assessment";
import { acceptedSectionFields } from "../lib/checklist";
import { createAudioCapture, type AudioState } from "../lib/audio";
import type { ASRLanguage, AssessmentCandidate, AssessmentId, AssessmentProgress, InteractionTrace, Resolutions, Resolution } from "../types";

interface AssessmentCaptureProps {
  assessment: AssessmentId;
  encounter: Record<string, unknown>;
  revision: number;
  progress?: AssessmentProgress;
  urgent: boolean;
  disabled: boolean;
  serviceError?: string;
  onBusy: (busy: boolean) => void;
  onPending: (pending: AssessmentId[]) => void;
  onAccept: (candidate: AssessmentCandidate, resolutions: Resolutions, revision: number, interaction?: InteractionTrace) => Promise<boolean>;
  onRecordInteraction: (interaction: InteractionTrace) => void;
}

function valueLabel(value: unknown) {
  return value === null || value === undefined ? "Unknown (null)" : JSON.stringify(value);
}

export function CaptureInput({ assessment, rawTranscript, text, disabled, onChange }: {
  assessment: AssessmentId; rawTranscript?: string; text: string; disabled: boolean; onChange: (text: string) => void;
}) {
  return <>
    {rawTranscript !== undefined && <>
      <label htmlFor={`capture-raw-${assessment}`}>Original ASR transcript (read-only)</label>
      <textarea id={`capture-raw-${assessment}`} value={rawTranscript} readOnly rows={3} />
    </>}
    <label htmlFor={`capture-text-${assessment}`}>Section findings / editable transcript</label>
    <textarea id={`capture-text-${assessment}`} value={text} rows={4} disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      placeholder="Describe one or several observed findings. You can always type instead of recording." />
  </>;
}

export function CandidateReview({ candidate, resolutions, busy, onResolve }: {
  candidate: AssessmentCandidate; resolutions: Resolutions; busy: boolean; onResolve: (field: string, resolution: Resolution) => void;
}) {
  return <>
    <h4>Review proposed findings</h4>
    <p>Not yet accepted. Check every value. Reject any unsupported finding. Choosing unknown explicitly retracts the accepted value to null.</p>
    <p className="capture-meta">Language understanding: {candidate.understanding
      ? `${candidate.understanding.provider}${candidate.understanding.model ? ` / ${candidate.understanding.model}` : ""}`
      : candidate.extraction_mode}</p>
    {candidate.warnings.length > 0 && <ul className="capture-warning">{candidate.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}
    {!!candidate.uncertainties?.length && <div className="capture-warning">
      <strong>Reported ambiguities</strong>
      <ul>{candidate.uncertainties.map((item, index) => <li key={index}>
        <code>{item.field ?? "Report-level uncertainty"}</code>: {item.reason} <q>{item.source_text}</q>
      </li>)}</ul>
    </div>}
    <details className="capture-details">
      <summary>Language review and report-only extraction</summary>
      <p>Optional English rendering is nonauthoritative. It is not the original transcript, editable input, or accepted clinical evidence.</p>
      {candidate.english_rendering != null ? <div><strong>English rendering</strong><p className="trace-text">{candidate.english_rendering}</p></div>
        : <p>No English rendering supplied.</p>}
      {!!candidate.evidence_spans?.length && <ul>{candidate.evidence_spans.map((span, index) => <li key={index}><code>{span.field}</code>: <q>{span.source_text}</q></li>)}</ul>}
      {candidate.candidate_encounter && <><strong>Report-only canonical candidate (not the merged encounter)</strong><pre>{JSON.stringify(candidate.candidate_encounter, null, 2)}</pre></>}
      {candidate.understanding && <><strong>Provider metadata</strong><pre>{JSON.stringify(candidate.understanding, null, 2)}</pre></>}
    </details>
    {candidate.changes.map((change) => {
      const required = unresolvedChanges([change], {}).length > 0;
      return <div className="capture-change" key={change.field}>
        <strong>{change.label}</strong><code>{change.field}</code>
        <p><span>Accepted: {valueLabel(change.previous)}</span><span>Proposed: {valueLabel(change.value)}</span></p>
        {(change.uncertain || change.value === null) && <p className="capture-warning">Ambiguous / unknown, not a negative finding. Explicit resolution required, even if the accepted value is already unknown. Include or retract sets null; keep explicitly reaffirms the accepted value.</p>}
        {change.conflict && <p className="capture-warning">Conflict with an accepted finding. Choose a resolution.</p>}
        {change.outside_assessment && <p className="capture-warning">Outside this assessment. Explicit inclusion or rejection required.</p>}
        <label>Review choice for {change.label}
          <select value={resolutions[change.field] ?? (required ? "" : "replace")} disabled={busy}
            onChange={(event) => onResolve(change.field, event.target.value as Resolution)}>
            {required && <option value="" disabled>Choose before applying</option>}
            <option value="replace">Include / replace with proposed value</option>
            <option value="keep">Reject / keep accepted value (explicitly reaffirm)</option>
            <option value="unknown">Retract / mark unknown (null)</option>
          </select>
        </label>
      </div>;
    })}
  </>;
}

export function AssessmentCapture({ assessment, encounter, revision, progress, urgent, disabled, serviceError, onBusy, onPending, onAccept, onRecordInteraction }: AssessmentCaptureProps) {
  const [text, setText] = useState("");
  const [candidate, setCandidate] = useState<AssessmentCandidate | null>(null);
  const [resolutions, setResolutions] = useState<Resolutions>({});
  const [retractions, setRetractions] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const [textConsent, setTextConsent] = useState(false);
  const [asrSource, setAsrSource] = useState<InteractionTrace["source"]>({});
  const recordingId = useRef<string | undefined>(undefined);
  const interaction = useRef<InteractionTrace | null>(null);
  const [language, setLanguage] = useState<ASRLanguage | "">("");
  const [audioState, setAudioState] = useState<AudioState>("idle");
  const [audio, setAudio] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState("");
  const [operation, setOperation] = useState<"transcribing" | "interpreting" | "applying" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [gate] = useState(createRequestGate);
  const currentRevision = useRef(revision);
  currentRevision.current = revision;
  const [microphone] = useState(() => createAudioCapture({ state: setAudioState, audio: setAudio, error: setError }));
  const busy = audioState !== "idle" || operation !== null;
  const pending = Boolean(text.trim() || candidate || audio || busy || retractions.length);
  const acceptedFields = acceptedSectionFields(encounter, assessment);

  useEffect(() => { onBusy(busy); }, [busy, onBusy]);
  useEffect(() => {
    onPending(pending ? affectedAssessments(assessment, [...(candidate?.changes.map((change) => change.field) ?? []), ...retractions]) : []);
  }, [pending, assessment, candidate, retractions, onPending]);
  useEffect(() => () => { gate.cancel(); microphone.cancel(); }, [gate, microphone]);
  useEffect(() => {
    if (!audio) { setAudioUrl(""); return; }
    const url = URL.createObjectURL(audio);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [audio]);

  function rejectInteraction(reason: string) {
    const entry = interaction.current;
    if (entry && (entry.status === "candidate" || entry.status === "transcribed")) {
      onRecordInteraction({ ...entry, resolutions, pending: false, status: "rejected", error: reason });
    }
    interaction.current = null;
  }

  function record(entry: InteractionTrace) {
    interaction.current = entry;
    onRecordInteraction(entry);
  }

  function editText(value: string) {
    rejectInteraction("Editable input changed; prior interpretation was not accepted.");
    gate.cancel();
    setOperation(null);
    setText(value);
    setCandidate(null);
    setResolutions({});
    setError("");
    setNotice("");
  }

  function cancel() {
    rejectInteraction("Capture cancelled by worker; accepted findings unchanged.");
    gate.cancel();
    microphone.cancel();
    setAudio(null);
    setOperation(null);
    setCandidate(null);
    setResolutions({});
    setRetractions([]);
    setError("");
    setNotice("Capture cancelled. Typed findings and accepted observations are unchanged.");
  }

  async function transcribe() {
    if (!audio || !consent || !language || busy || disabled) return;
    const request = gate.begin(revision);
    rejectInteraction("Superseded by a new transcription request.");
    const trace: InteractionTrace = { id: crypto.randomUUID(), timestamp: new Date().toISOString(), assessment,
      status: "candidate", pending: true, source: { recording_id: recordingId.current, language, asr_provider: "intron" }, before_encounter: encounter };
    record(trace);
    setLanguage("");
    setOperation("transcribing");
    setCandidate(null);
    setResolutions({});
    setError("");
    try {
      const response = await transcribeAudio(audio, trace.source.language!, request.signal);
      if (!request.isCurrent(currentRevision.current)) return;
      setText(response.transcript);
      const source = { ...trace.source, raw_asr_transcript: response.transcript, asr_provider: response.provider, asr_model: response.model };
      setAsrSource(source);
      record({ ...trace, source, status: "transcribed", pending: false });
      setNotice("Transcribed by Intron. Edit the transcript, then interpret and review before applying.");
    } catch (failure) {
      if (request.isCurrent(currentRevision.current)) {
        const message = failure instanceof Error ? failure.message : "Transcription failed. You can type findings below.";
        setError(message); record({ ...trace, status: "failed", pending: false, error: message });
      }
    } finally {
      if (request.isCurrent(currentRevision.current)) setOperation(null);
    }
  }

  async function interpret() {
    if (!text.trim() || !textConsent || busy || disabled) return;
    const request = gate.begin(revision);
    rejectInteraction("Superseded by an interpretation request; original transcription retained here.");
    const trace: InteractionTrace = { id: crypto.randomUUID(), timestamp: new Date().toISOString(), assessment,
      status: "candidate", pending: true, source: { ...asrSource, submitted_text: text,
        question: !urgent && progress?.decision === "ASK" ? progress.question ?? undefined : undefined }, before_encounter: encounter };
    record(trace);
    setOperation("interpreting");
    setCandidate(null);
    setResolutions({});
    setError("");
    setNotice("");
    try {
      const response = await extractAssessment(assessment, text, encounter,
        trace.source.question?.field, request.signal);
      if (!request.isCurrent(currentRevision.current)) return;
      if (response.assessment !== assessment) throw new Error("The interpretation returned the wrong assessment. Please retry.");
      setCandidate(response);
      record({ ...trace, status: "candidate", pending: false, candidate: response });
    } catch (failure) {
      if (request.isCurrent(currentRevision.current)) {
        const message = failure instanceof Error ? failure.message : "Interpretation failed. Accepted findings are unchanged.";
        setError(message); record({ ...trace, status: "failed", pending: false, error: message });
      }
    } finally {
      if (request.isCurrent(currentRevision.current)) setOperation(null);
    }
  }

  async function apply() {
    if (!candidate || busy || disabled || retractions.length || unresolvedChanges(candidate.changes, resolutions).length) return;
    if (!candidate.changes.length && !window.confirm("Acknowledge that this report supplied no new evidence? Accepted findings will not change. If an accepted value is uncertain, cancel and explicitly retract it below instead.")) return;
    setOperation("applying");
    // The parent remounts capture on an accepted revision, discarding audio and the old candidate.
    const trace = interaction.current?.status === "failed" ? { ...interaction.current, id: crypto.randomUUID(), timestamp: new Date().toISOString() } : interaction.current ?? undefined;
    if (!await onAccept(candidate, resolutions, revision, trace)) {
      if (trace) interaction.current = { ...trace, status: "failed" };
      setOperation(null);
    }
  }

  async function retract() {
    if (busy || disabled || !retractions.length) return;
    const changes = acceptedFields.filter((field) => retractions.includes(field.field));
    if (!window.confirm(`Mark these accepted findings UNKNOWN (null): ${changes.map((change) => change.label).join(", ")}? This explicitly retracts evidence and re-evaluates the encounter. Any other unaccepted section report or audio will be discarded on success.`)) return;
    gate.cancel();
    rejectInteraction("Discarded in favor of explicit worker retraction.");
    setCandidate(null);
    setResolutions({});
    setOperation("applying");
    setError("");
    const choices: Resolutions = Object.fromEntries(changes.map((change) => [change.field, "unknown"]));
    if (!await onAccept(workerRetraction(assessment, changes), choices, revision)) setOperation(null);
  }

  const unresolved = candidate ? unresolvedChanges(candidate.changes, resolutions) : [];
  return (
    <section className="assessment-capture" aria-label={`${assessment} findings capture`}>
      <h3>Record or type this assessment</h3>
      {!urgent && progress?.decision === "ASK" && progress.question && (
        <div className="capture-question" aria-live="polite">
          <strong>Next observation</strong><p>{progress.question.text}</p>
        </div>
      )}
      {progress?.decision === "COMPLETE" && !urgent && <p>Accepted assessment complete. You may add or correct findings.</p>}
      {urgent && <p className="capture-warning">Ordinary questions are paused. Prioritize urgent actions. Further captures are your choice.</p>}
      {progress?.blockers.map((blocker, index) => <p className="capture-warning" key={index}>{blocker}</p>)}
      <p className="capture-privacy" id={`privacy-${assessment}`}>
        Research/demo only. Audio is sent to Intron for transcription. Section text/transcripts and the current canonical encounter are sent to the configured language-understanding service (Azure OpenAI in demo mode).
        External Azure receives the transcript and current canonical encounter in demo mode. Use synthetic data only; no identifying details.
        Browser audio is kept in memory, never saved. Accepted findings and local interaction traces containing transcripts and results are saved in this tab only, including rejected and failed requests.
      </p>
      <label htmlFor={`capture-language-${assessment}`}>
        Recording language
        <select id={`capture-language-${assessment}`} value={language} disabled={busy}
          onChange={(event) => setLanguage(event.target.value as ASRLanguage | "")}>
          <option value="" disabled>Select for each transcription request</option>
          <option value="en">English</option>
          <option value="pcm">Nigerian Pidgin-English</option>
          <option value="yo">Yoruba-English</option>
          <option value="ig">Igbo-English</option>
          <option value="ha">Hausa-English</option>
        </select>
      </label>
      <label className="capture-consent">
        <input type="checkbox" checked={consent} disabled={busy} onChange={(event) => setConsent(event.target.checked)} />
        I understand and agree to send audio to Intron.
      </label>
      <div className="capture-actions">
        <button type="button" disabled={disabled || busy || !consent || !language} aria-describedby={`privacy-${assessment}`} onClick={() => {
          rejectInteraction("New recording started; prior capture not accepted."); recordingId.current = crypto.randomUUID();
          setAudio(null); setCandidate(null); setResolutions({}); setError(""); setNotice(""); void microphone.record();
        }}>Record</button>
        <button type="button" disabled={audioState !== "recording"} onClick={microphone.stop}>Stop</button>
        <button type="button" disabled={operation === "applying" || (!busy && !audio && !candidate && !retractions.length)} onClick={cancel}>Cancel</button>
      </div>
      <p className="capture-meta" role="status">
        {audioState === "permission" ? "Waiting for microphone permission. Cancel also discards a late permission grant."
          : audioState === "recording" ? "Recording. Automatically stops at 60 seconds; maximum 5 MB."
            : audioState === "stopping" ? "Finishing recording..." : "Maximum 60 seconds / 5 MB. Recording does not complete an assessment."}
      </p>
      {audioUrl && <div className="capture-playback">
        <audio controls src={audioUrl} preload="metadata" aria-label="Review recorded assessment" />
        <div className="capture-actions">
          <button type="button" disabled={disabled || busy || !consent || !language} onClick={() => {
            if (!text.trim() || window.confirm("Replace the editable text with a new transcript?")) void transcribe();
          }}>Transcribe audio</button>
          <button type="button" disabled={busy} onClick={() => setAudio(null)}>Discard audio</button>
        </div>
      </div>}
      <CaptureInput assessment={assessment} rawTranscript={asrSource.raw_asr_transcript} text={text}
        disabled={audioState !== "idle" || operation === "applying"} onChange={editText} />
      <label className="capture-consent">
        <input type="checkbox" checked={textConsent} disabled={busy} onChange={(event) => setTextConsent(event.target.checked)} />
        I agree to send this section text/transcript and the current canonical encounter to the configured language-understanding service (external Azure OpenAI in demo mode), and retain transcripts/results in this tab. Synthetic data only.
      </label>
      <button type="button" disabled={disabled || busy || !text.trim() || !textConsent} onClick={() => void interpret()}>Interpret section findings</button>
      {operation && <p role="status">{operation === "transcribing" ? "Transcribing with Intron (up to 110 seconds)..." : operation === "interpreting" ? "Interpreting findings with the configured language-understanding service..." : "Applying reviewed findings and evaluating..."}</p>}
      {error && <p className="capture-error" role="alert">{error}</p>}
      {serviceError && <p className="capture-error" role="alert">{serviceError}</p>}
      {notice && <p role="status">{notice}</p>}
      {candidate && <div className="capture-review">
        <CandidateReview candidate={candidate} resolutions={resolutions} busy={busy} onResolve={(field, choice) => {
          const next = { ...resolutions, [field]: choice };
          setResolutions(next);
          if (interaction.current && interaction.current.status === "candidate") record({ ...interaction.current, resolutions: next });
        }} />
        {!candidate.changes.length && <p>No new evidence was extracted. Existing accepted values will NOT become unknown. Revise the report, explicitly retract uncertain accepted evidence below, or acknowledge that there is no new evidence.</p>}
        {unresolved.length > 0 && <p className="capture-warning" role="status">{unresolved.length} unresolved choice(s). Nothing can be applied until these are reviewed.</p>}
        {retractions.length > 0 && <p className="capture-warning">Review the selected retractions below, or unselect them before applying this interpretation.</p>}
        <button type="button" disabled={disabled || busy || retractions.length > 0 || unresolved.length > 0} onClick={() => void apply()}>{candidate.changes.length ? "Apply reviewed findings" : "Acknowledge no new evidence"}</button>
      </div>}
      <section className="capture-review" aria-label="Review accepted evidence">
        <h4>Review accepted evidence</h4>
        <p>Uncertain about a recorded value? Explicitly mark it UNKNOWN here, even if interpretation failed or returned no changes. This does not infer a replacement from your text.</p>
        {acceptedFields.length ? acceptedFields.map((change) => <label className="capture-retraction" key={change.field}>
          <input type="checkbox" checked={retractions.includes(change.field)} disabled={disabled || busy}
            onChange={(event) => setRetractions((previous) => event.target.checked ? [...previous, change.field] : previous.filter((field) => field !== change.field))} />
          <span><strong>{change.label}</strong>: {valueLabel(change.previous)}<code>{change.field}</code>Mark UNKNOWN (null)</span>
        </label>) : <p>No known accepted fields in this section to retract.</p>}
        {acceptedFields.length > 0 && <button type="button" disabled={disabled || busy || !retractions.length} onClick={() => void retract()}>Confirm selected retractions to UNKNOWN</button>}
      </section>
    </section>
  );
}
