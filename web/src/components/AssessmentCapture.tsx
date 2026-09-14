import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { Mic, Square } from "lucide-react";
import { unresolvedChanges } from "../lib/assessment";
import { acceptedSectionFields } from "../lib/checklist";
import type { CaptureContext, CaptureJob, useVoiceCapture } from "../lib/useVoiceCapture";
import type { ASRLanguage, AssessmentCandidate, AssessmentId, AssessmentProgress, Resolutions, Resolution } from "../types";

interface AssessmentCaptureProps {
  assessment: AssessmentId;
  encounter: Record<string, unknown>;
  revision: number;
  progress?: AssessmentProgress;
  urgent: boolean;
  voice: ReturnType<typeof useVoiceCapture>;
  language: ASRLanguage | "";
  consent: { audio: boolean; understanding: boolean };
  reviewDisabled: boolean;
  ready: boolean;
  onDirty: Dispatch<SetStateAction<Partial<Record<AssessmentId, boolean>>>>;
}

function valueLabel(value: unknown) {
  return value === null || value === undefined ? "Unknown (null)" : JSON.stringify(value);
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
        {change.review_changed && <p className="capture-warning">Accepted evidence changed since this capture. Reconfirm your choice even if the latest value matches the proposal or is unknown.</p>}
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

function JobReview({ job, revision, disabled, voice }: {
  job: CaptureJob; revision: number; disabled: boolean; voice: AssessmentCaptureProps["voice"];
}) {
  const [resolutions, setResolutions] = useState<Resolutions>({});
  const candidate = job.candidate!;
  const stale = job.reviewRevision !== revision;
  const unresolved = unresolvedChanges(candidate.changes, resolutions);
  const applying = job.status === "applying";
  return <div className="capture-review">
    <CandidateReview candidate={candidate} resolutions={resolutions} busy={disabled || stale || applying}
      onResolve={(field, choice) => setResolutions((previous) => ({ ...previous, [field]: choice }))} />
    {stale && <p className="capture-warning" role="status">Accepted findings changed. Review again against the latest encounter before applying.</p>}
    {job.reviewRevision !== undefined && job.originalRevision !== job.reviewRevision && <p className="capture-warning">Acceptance context changed since capture. The original captured question remains binding. Review these findings against the latest accepted encounter before explicitly applying, even if no proposed fields changed.</p>}
    {!candidate.changes.length && <p>No new evidence was extracted. Existing accepted values will NOT become unknown. Record a correction, explicitly retract uncertain accepted evidence below, or acknowledge that there is no new evidence.</p>}
    {unresolved.length > 0 && <p className="capture-warning" role="status">{unresolved.length} unresolved choice(s). Nothing can be applied until these are reviewed.</p>}
    <div className="capture-actions">
      {stale && <button type="button" disabled={disabled || applying} onClick={() => void voice.prepareReview(job.id)}>Review again</button>}
      <button type="button" disabled={disabled || stale || applying || unresolved.length > 0} onClick={() => {
        if (!candidate.changes.length && !window.confirm("Acknowledge that this report supplied no new evidence? Accepted findings will not change. If an accepted value is uncertain, explicitly retract it instead.")) return;
        void voice.accept(job.id, resolutions);
      }}>{applying ? "Applying reviewed findings..." : candidate.changes.length ? "Apply reviewed findings" : "Acknowledge no new evidence"}</button>
    </div>
  </div>;
}

const jobStatus: Record<CaptureJob["status"], string> = {
  recording: "Recording", queued: "Processing / queued", transcribing: "Processing / transcribing",
  extracting: "Processing / structuring findings", captured: "Captured / awaiting review",
  preparing_review: "Processing / preparing review", review: "Captured / review before applying",
  applying: "Processing / applying reviewed findings", accepted: "Reviewed", failed: "Capture failed", discarded: "Discarded",
};

function CaptureJobCard({ job, revision, reviewDisabled, voice, onDirty }: {
  job: CaptureJob; revision: number; reviewDisabled: boolean; voice: AssessmentCaptureProps["voice"];
  onDirty: Dispatch<SetStateAction<Record<string, boolean>>>;
}) {
  const sourceText = job.inputText ?? job.transcript?.transcript ?? "";
  const [correctedText, setCorrectedText] = useState<string | null>(null);
  const reviewing = job.status === "review" || job.status === "applying";
  const canRetry = ["captured", "review", "failed"].includes(job.status);
  const correctionDirty = canRetry && correctedText !== null && correctedText !== sourceText;
  const retryableInput = Boolean(job.inputText?.trim() || (job.audio?.size && job.language));
  useEffect(() => {
    onDirty((previous) => previous[job.id] === correctionDirty ? previous : { ...previous, [job.id]: correctionDirty });
  }, [job.id, correctionDirty, onDirty]);
  useEffect(() => () => {
    onDirty((previous) => { const next = { ...previous }; delete next[job.id]; return next; });
  }, [job.id, onDirty]);
  return <article className={`capture-job capture-job--${job.status}`} aria-label={`Capture ${job.id}`}>
    <header className="capture-job-heading"><strong role="status">{jobStatus[job.status]}</strong>
      <span>{job.language ?? "Text / worker review"}</span></header>
    {job.question && job.status !== "accepted" && <div className="capture-source-question"><strong>Question at capture</strong><p>{job.question.text}</p><code>{job.question.field}</code></div>}
    {reviewing && sourceText && <p className="capture-source-text"><strong>Captured source (read-only)</strong><q>{sourceText}</q></p>}
    {job.error && <p className="capture-error" role="alert">{job.error}</p>}
    {correctionDirty && <p className="capture-warning" role="status">Transcript has unprocessed edits. Process the correction or cancel it before applying this review.</p>}
    {job.status === "accepted" && <p className="capture-meta">{job.changedFields.length
      ? `Reviewed changes: ${job.changedFields.map((field) => job.candidate?.changes.find((change) => change.field === field)?.label ?? field).join(", ")}.`
      : "Reviewed; no accepted values changed."} Current observations are shown below.</p>}
    {job.status === "captured" && <>
      {!!job.candidate?.changes.length && <ul className="captured-findings">{job.candidate.changes.map((change) => <li key={change.field}>
        {change.label}: <strong>{valueLabel(change.value)}</strong> <span>Not accepted</span>
      </li>)}</ul>}
      <button type="button" disabled={reviewDisabled || correctionDirty} onClick={() => void voice.prepareReview(job.id)}>Review captured findings</button>
    </>}
    {reviewing && job.candidate && <JobReview key={`${job.id}:${job.reviewVersion}`} job={job} revision={revision} disabled={reviewDisabled || correctionDirty} voice={voice} />}
    {(job.transcript || job.inputText !== undefined) && <details className="capture-details">
      <summary>Transcript / source details (read-only)</summary>
      {job.transcript && <><strong>Original ASR transcript (read-only)</strong><p className="trace-text">{job.transcript.transcript}</p></>}
      {job.inputText !== undefined && <><strong>Submitted input (read-only)</strong><p className="trace-text">{job.inputText}</p></>}
    </details>}
    {canRetry && sourceText && <details className="capture-details">
      <summary>Correct transcript if needed</summary>
      <p>Optional. You can record another clip instead. Processing a correction requires a new review; accepted findings stay unchanged.</p>
      <p>Retrying/correcting this clip uses its original processing permission. Editing alone sends nothing.</p>
      <label htmlFor={`correct-transcript-${job.id}`}>Corrected transcript</label>
      <textarea id={`correct-transcript-${job.id}`} rows={3} value={correctedText ?? sourceText} onChange={(event) => setCorrectedText(event.target.value)} />
      <div className="capture-actions">
        <button type="button" disabled={!(correctedText ?? sourceText).trim()} onClick={() => voice.retry(job.id, correctedText ?? sourceText)}>Process corrected transcript</button>
        {correctedText !== null && <button type="button" onClick={() => setCorrectedText(null)}>Cancel correction</button>}
      </div>
    </details>}
    {job.status !== "accepted" && job.status !== "recording" && job.status !== "applying" && <div className="capture-actions">
      {job.status === "failed" && (retryableInput
        ? <button type="button" disabled={correctionDirty} onClick={() => voice.retry(job.id)}>Retry</button>
        : <p className="capture-meta">No usable recording or text remains. Record again or type a finding instead.</p>)}
      <button type="button" onClick={() => voice.discard(job.id)}>Discard</button>
    </div>}
  </article>;
}

export function AssessmentCapture({ assessment, encounter, revision, progress, urgent, voice, language, consent, reviewDisabled, ready, onDirty }: AssessmentCaptureProps) {
  // Undefined means untouched; null means typing began before a valid question existed.
  const [draft, setDraft] = useState<{ text: string; context?: CaptureContext | null }>({ text: "" });
  const [retractions, setRetractions] = useState<string[]>([]);
  const [dirtyCorrections, setDirtyCorrections] = useState<Record<string, boolean>>({});
  const jobs = voice.jobs.filter((job) => job.assessment === assessment && job.status !== "discarded");
  const ownsMic = jobs.some((job) => job.id === voice.recordingId);
  const acceptedFields = acceptedSectionFields(encounter, assessment);
  const selectedRetractions = retractions.filter((field) => acceptedFields.some((change) => change.field === field));
  const dirty = Boolean(draft.text.trim() || selectedRetractions.length || Object.values(dirtyCorrections).some(Boolean));
  useEffect(() => {
    onDirty((previous) => previous[assessment] === dirty ? previous : { ...previous, [assessment]: dirty });
  }, [assessment, dirty, onDirty]);
  useEffect(() => () => {
    onDirty((previous) => { const next = { ...previous }; delete next[assessment]; return next; });
  }, [assessment, onDirty]);
  return <section className="assessment-capture" aria-label={`${assessment} findings capture`}>
    <h3>Capture findings</h3>
    {!urgent && progress?.decision === "ASK" && progress.question && <div className="capture-question">
      <strong>Next observation</strong><p>{progress.question.text}</p>
    </div>}
    {urgent && <p className="capture-warning">Ordinary questions are paused. Prioritize urgent actions. Further captures are your choice.</p>}
    {progress?.blockers.map((blocker, index) => <p className="capture-warning" key={index}>{blocker}</p>)}
    <div className="capture-actions">
      {ownsMic ? <>
        <button type="button" disabled={voice.audioState !== "recording"} onClick={voice.stop}><Square aria-hidden="true" size={15} />Stop</button>
        <button type="button" onClick={voice.cancelRecording}>Cancel recording</button>
      </> : <button type="button" className="record-findings" aria-describedby="capture-disclosure"
        disabled={voice.audioState !== "idle" || !language || !consent.audio || !consent.understanding}
        onClick={() => { if (language) voice.startRecording(assessment, language, consent); }}><Mic aria-hidden="true" size={16} />Record findings</button>}
    </div>
    <p className="capture-meta">{ownsMic ? voice.audioState === "permission" ? "Waiting for microphone permission."
      : voice.audioState === "stopping" ? "Finishing recording..." : "Recording. Stop when finished."
      : "Stop to process automatically. Continue to any section while processing."} Maximum 60 seconds / 5 MB.</p>
    <p className="capture-meta">Recording does not complete an assessment. Record another clip to add or correct a finding without typing.</p>
    <div className="capture-jobs">{jobs.map((job) => <CaptureJobCard key={job.id} job={job} revision={revision} reviewDisabled={reviewDisabled} voice={voice} onDirty={setDirtyCorrections} />)}</div>

    <section className="accepted-observations" aria-label="Reviewed observations">
      <h4>Reviewed observations</h4>
      {acceptedFields.length ? <dl>{acceptedFields.map((change) => <div key={change.field}>
        <dt>{change.label}</dt><dd>{valueLabel(change.previous)}</dd>
      </div>)}</dl> : <p className="capture-meta">No accepted observations yet.</p>}
      {acceptedFields.length > 0 && <details className="capture-details">
        <summary>Mark accepted findings unknown</summary>
        <p>Uncertain about a recorded value? Select it to prepare a separate retraction for review. Nothing changes until you explicitly resolve and apply it.</p>
        {acceptedFields.map((change) => <label className="capture-retraction" key={change.field}>
          <input type="checkbox" checked={selectedRetractions.includes(change.field)} onChange={(event) => setRetractions((previous) => event.target.checked
            ? [...previous, change.field] : previous.filter((field) => field !== change.field))} />
          <span><strong>{change.label}</strong>: {valueLabel(change.previous)}<code>{change.field}</code>Mark UNKNOWN (null)</span>
        </label>)}
        <button type="button" disabled={!ready || !selectedRetractions.length} onClick={() => {
          if (!ready) return;
          voice.retract(assessment, selectedRetractions); setRetractions([]);
        }}>Review selected retractions</button>
      </details>}
    </section>
    <details className="capture-details typed-fallback">
      <summary>Type a finding instead</summary>
      <p>Optional fallback if the microphone or ASR fails. Language understanding still needs connectivity, followed by explicit review.</p>
      {draft.context?.question && <div className="capture-source-question"><strong>Question when typing began</strong><p>{draft.context.question.text}</p><code>{draft.context.question.field}</code></div>}
      {draft.context && draft.context.revision !== revision && <p className="capture-warning">Accepted findings changed while you were typing. This draft keeps its original question and encounter context; it will not answer the new question.</p>}
      {draft.context === null && <p className="capture-meta">Typing began before the encounter was ready. This draft will use the latest accepted encounter without binding to a newly appearing question.</p>}
      <label htmlFor={`capture-text-${assessment}`}>Typed finding for this section</label>
      <textarea id={`capture-text-${assessment}`} rows={3} value={draft.text} onChange={(event) => setDraft({ text: event.target.value,
        context: draft.context !== undefined ? draft.context : ready ? { encounter: structuredClone(encounter), revision,
          question: !urgent && progress?.decision === "ASK" && progress.question ? { ...progress.question } : undefined } : null })} />
      {!consent.understanding && <p className="capture-meta">Agree to language-understanding processing in the recording settings first.</p>}
      <div className="capture-actions">
        <button type="button" disabled={!ready || !draft.text.trim() || !consent.understanding} onClick={() => {
          if (!ready) return;
          const context = draft.context ?? { encounter: structuredClone(encounter), revision, question: undefined };
          if (voice.addText(assessment, draft.text, consent.understanding, context)) setDraft({ text: "" });
        }}>Process typed finding</button>
        {draft.context !== undefined && <button type="button" onClick={() => setDraft({ text: "" })}>Clear typed finding</button>}
      </div>
    </details>
  </section>;
}
