import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { Mic, Square } from "lucide-react";
import type { CaptureContext, CaptureJob, useVoiceCapture } from "../lib/useVoiceCapture";
import type { ASRLanguage, AssessmentCandidate, AssessmentId, AssessmentProgress } from "../types";

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
  onReviewJob: (id: string) => void;
  showDebug?: boolean;
}

/** Read-only source evidence, kept separate from answers corrected on the guide. */
export function CandidateDetails({ candidate, showDebug = true, showReport = true }: { candidate: AssessmentCandidate; showDebug?: boolean; showReport?: boolean }) {
  return <>
    {showReport && <><strong>{showDebug ? "Original submitted report (read-only)" : "Original report"}</strong><p className="trace-text">{candidate.input_text}</p></>}
    {showDebug && <><p>Optional English rendering is nonauthoritative. It is not the original transcript, editable input, or accepted clinical evidence.</p>
      {candidate.english_rendering != null ? <><strong>English rendering</strong><p className="trace-text">{candidate.english_rendering}</p></>
        : <p>No English rendering supplied.</p>}</>}
    {!!candidate.warnings.length && (showDebug ? <ul className="capture-warning">{candidate.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
      : <p className="capture-warning">Please review the report and confirm the findings on the assessment.</p>)}
    {!!candidate.uncertainties?.length && <><strong>Reported ambiguities</strong><ul>{candidate.uncertainties.map((item, index) => <li key={index}>
      {showDebug && <><code>{item.field ?? "Report-level uncertainty"}</code>: </>}{item.reason} <q>{item.source_text}</q>
    </li>)}</ul></>}
    {showDebug && !!candidate.evidence_spans?.length && <ul>{candidate.evidence_spans.map((span, index) => <li key={index}><code>{span.field}</code>: <q>{span.source_text}</q></li>)}</ul>}
    {showDebug && <><strong>Original candidate (not the accepted encounter)</strong><pre>{JSON.stringify(candidate, null, 2)}</pre></>}
  </>;
}

const jobStatus: Record<CaptureJob["status"], string> = {
  recording: "Recording", queued: "Processing / queued", transcribing: "Processing / transcribing",
  extracting: "Processing / structuring findings", captured: "Captured / awaiting confirmation",
  preparing_review: "Processing / preparing review", review: "Awaiting confirmation",
  applying: "Processing / confirming findings", accepted: "Reviewed", failed: "Capture failed", discarded: "Discarded",
};

function CaptureJobCard({ job, reviewDisabled, voice, onReviewJob, showDebug = true }: {
  job: CaptureJob; reviewDisabled: boolean; voice: AssessmentCaptureProps["voice"]; onReviewJob: (id: string) => void; showDebug?: boolean;
}) {
  const retryableInput = Boolean(job.inputText?.trim() || (job.audio?.size && job.language));
  const report = job.transcript?.transcript ?? job.inputText ?? job.originalCandidate?.input_text;
  return <article className={`capture-job capture-job--${job.status}`} aria-label={showDebug ? `Capture ${job.id}` : "Recording"}>
    <header className="capture-job-heading"><strong role="status">{jobStatus[job.status]}</strong>
      <span>{job.language ?? "Text / worker review"}</span></header>
    {job.error && <p className="capture-error" role="alert">{job.error}</p>}
    {job.status === "accepted" && <p className="capture-meta">{job.changedFields.length
      ? showDebug ? `Reviewed changes: ${job.changedFields.map((field) => job.candidate?.changes.find((change) => change.field === field)?.label ?? field).join(", ")}.` : "Findings reviewed."
      : "Reviewed; no accepted values changed."} Confirmed observations are shown on the assessment.</p>}
    {["captured", "review", "preparing_review"].includes(job.status) && <>
      <p className="capture-meta">Findings populate the assessment controls. Correct answers there or record another clip; the original source stays unchanged.</p>
      <button type="button" disabled={reviewDisabled} onClick={() => onReviewJob(job.id)}>Review on assessment</button>
    </>}
    {(job.transcript || job.inputText !== undefined || job.originalCandidate || job.question) && <details className="capture-details">
      <summary>{showDebug ? "Details: original source (read-only)" : "Transcript"}</summary>
      {job.question && <><strong>Question at capture</strong><p>{job.question.text}</p>{showDebug && <code>{job.question.field}</code>}</>}
      {showDebug ? <>
        {job.transcript && <><strong>Original ASR transcript (read-only)</strong><p className="trace-text">{job.transcript.transcript}</p></>}
        {job.inputText !== undefined && <><strong>Submitted input (read-only)</strong><p className="trace-text">{job.inputText}</p></>}
      </> : report !== undefined && <p className="trace-text">{report}</p>}
      {job.originalCandidate && <CandidateDetails candidate={job.originalCandidate} showDebug={showDebug} showReport={showDebug} />}
    </details>}
    {job.status !== "accepted" && job.status !== "recording" && job.status !== "applying" && <div className="capture-actions">
      {job.status === "failed" && (retryableInput
        ? <button type="button" onClick={() => voice.retry(job.id)}>Retry</button>
        : <p className="capture-meta">No usable recording or text remains. Record again or type a finding instead.</p>)}
      <button type="button" onClick={() => voice.discard(job.id)}>Discard</button>
    </div>}
  </article>;
}

export function AssessmentCapture({ assessment, encounter, revision, progress, urgent, voice, language, consent, reviewDisabled, ready, onDirty, onReviewJob, showDebug = true }: AssessmentCaptureProps) {
  // Undefined means untouched; null means typing began before a valid question existed.
  const [draft, setDraft] = useState<{ text: string; context?: CaptureContext | null }>({ text: "" });
  const jobs = voice.jobs.filter((job) => job.assessment === assessment && job.status !== "discarded");
  const ownsMic = jobs.some((job) => job.id === voice.recordingId);
  const dirty = Boolean(draft.text.trim());
  useEffect(() => {
    onDirty((previous) => previous[assessment] === dirty ? previous : { ...previous, [assessment]: dirty });
  }, [assessment, dirty, onDirty]);
  useEffect(() => () => {
    onDirty((previous) => { const next = { ...previous }; delete next[assessment]; return next; });
  }, [assessment, onDirty]);
  return <section className="assessment-capture" aria-label={`${assessment} findings capture`}>
    <h3>{showDebug ? "Capture findings" : "Recordings"}</h3>
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
    <p className="capture-meta">Recording does not complete an assessment. Review or correct the answers on the assessment, then confirm findings.</p>
    <div className="capture-jobs">{jobs.map((job) => <CaptureJobCard key={job.id} job={job} reviewDisabled={reviewDisabled} voice={voice} onReviewJob={onReviewJob} showDebug={showDebug} />)}</div>

    <details className="capture-details typed-fallback">
      <summary>Type a finding instead</summary>
      <p>Optional fallback if the microphone or ASR fails. Language understanding still needs connectivity, followed by explicit review.</p>
      {draft.context?.question && <div className="capture-source-question"><strong>Question when typing began</strong><p>{draft.context.question.text}</p>{showDebug && <code>{draft.context.question.field}</code>}</div>}
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
