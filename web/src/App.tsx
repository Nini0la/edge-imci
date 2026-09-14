import { useEffect, useState } from "react";
import { ClipboardCheck, LockKeyhole, Mic, ShieldCheck } from "lucide-react";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
import { AssessmentCapture } from "./components/AssessmentCapture";
import { ResultPanel } from "./components/ResultPanel";
import { InteractionHistory } from "./components/InteractionHistory";
import { affectedAssessments, assessmentIds, hasMeaningfulEvidence } from "./lib/assessment";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import { useVoiceCapture, type CaptureJob } from "./lib/useVoiceCapture";
import type { ASRLanguage, AssessmentId } from "./types";

export default function App() {
  const session = useAssessmentSession();
  const voice = useVoiceCapture(session);
  const [activePanel, setActivePanel] = useState<"assessment" | "result">("assessment");
  const [language, setLanguage] = useState<ASRLanguage | "">("");
  const [audioConsent, setAudioConsent] = useState(false);
  const [understandingConsent, setUnderstandingConsent] = useState(false);
  const [captureResetKey, setCaptureResetKey] = useState(0);
  const [dirtySections, setDirtySections] = useState<Partial<Record<AssessmentId, boolean>>>({});
  const dirtyAssessments = assessmentIds.filter((id) => dirtySections[id]);
  const hasDirty = dirtyAssessments.length > 0;
  const interrupted = session.interruptedCount > 0;
  const result = session.evaluation?.analysis;
  const meaningful = hasMeaningfulEvidence(session.encounter);
  const urgent = Boolean(result?.is_urgent || Object.values(session.evaluation?.assessments ?? {})
    .some((item) => item.status === "URGENT" || item.decision === "URGENT"));
  const progressBlocked = Object.values(session.evaluation?.assessments ?? {}).some((item) => item.decision === "BLOCK");
  const pendingJobs = voice.jobs.filter((job) => job.status !== "accepted" && job.status !== "discarded");
  const pendingAssessments = [...new Set([...dirtyAssessments, ...pendingJobs.flatMap((job) => affectedAssessments(job.assessment,
    [...job.changedFields, ...(job.candidate?.changes.map((change) => change.field) ?? [])]))])];
  const captureStatuses: Partial<Record<AssessmentId, string>> = {};
  for (const id of assessmentIds) {
    const jobs: CaptureJob[] = voice.jobs.filter((job) => job.assessment === id && job.status !== "discarded");
    if (dirtySections[id]) captureStatuses[id] = "Unprocessed edits";
    else if (jobs.some((job) => job.id === voice.recordingId)) captureStatuses[id] = "Recording";
    else if (jobs.some((job) => ["queued", "transcribing", "extracting", "preparing_review", "applying"].includes(job.status))) captureStatuses[id] = "Processing";
    else if (jobs.some((job) => job.status === "failed")) captureStatuses[id] = "Capture failed";
    else if (jobs.some((job) => job.status === "captured" || job.status === "review")) captureStatuses[id] = "Captured";
    else if (jobs.some((job) => job.status === "accepted")) captureStatuses[id] = "Reviewed";
  }
  const recording = voice.jobs.find((job) => job.id === voice.recordingId);
  const finalReady = meaningful && result?.is_complete && !pendingJobs.length && !hasDirty && !interrupted && !progressBlocked;

  useEffect(() => {
    if (!hasDirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [hasDirty]);

  function clearAssessment() {
    if (!window.confirm("Clear this encounter, all unaccepted findings, audio, interaction history, and the saved tab draft? This cannot be undone.")) return;
    voice.clear();
    session.reset();
    setDirtySections({});
    // Only explicit encounter clearing resets local editors, never an accepted revision.
    setCaptureResetKey((previous) => previous + 1);
    setAudioConsent(false);
    setUnderstandingConsent(false);
    setActivePanel("assessment");
  }

  return <div className="app-frame">
    <header className="site-header">
      <a className="brand" href="/" aria-label="EdgeIMCI home">
        <span className="brand-symbol"><img src="/edge-imci-mark.svg" alt="" aria-hidden="true" /></span>
        <span>Edge<strong>IMCI</strong></span>
      </a>
      <div className="header-context"><span>Initial sick-child assessment</span><span>Ages 2–59 months</span></div>
      <div className="header-trust"><LockKeyhole aria-hidden="true" size={14} /> Intron voice demo</div>
    </header>

    <nav className="mobile-panel-nav" aria-label="Application panels">
      {(["assessment", "result"] as const).map((panel) => <button className={activePanel === panel ? "active" : ""}
        type="button" key={panel} aria-pressed={activePanel === panel} onClick={() => setActivePanel(panel)}>
        {panel === "assessment" ? "Assessment" : "Result"}
        {panel === "result" && urgent && <span className="urgent-dot" />}
      </button>)}
    </nav>

    {urgent && <section className="workspace-urgent" aria-label="Accepted urgent guidance" role="alert">
      <strong>Urgent: prioritize immediate care. Do not delay referral.</strong>
      <ul>{result?.urgent_actions.map((action, index) => <li key={index}>{action}</li>)}</ul>
    </section>}

    {voice.audioState !== "idle" && <section className="recording-banner" aria-label="Active recording">
      <Mic aria-hidden="true" size={18} />
      <span role="status"><strong>{voice.audioState === "permission" ? "Waiting for microphone permission"
        : voice.audioState === "stopping" ? "Finishing recording" : "Recording"}</strong>{recording && ` / ${recording.assessment} / ${recording.language}`}</span>
      <button type="button" disabled={voice.audioState !== "recording"} onClick={voice.stop}>Stop</button>
      <button type="button" onClick={voice.cancelRecording}>Cancel</button>
    </section>}

    {(!session.ready || session.storageHint || session.error || voice.error || interrupted || (meaningful && (progressBlocked || result?.error))) &&
      <section className="workspace-notices" aria-label="Encounter service and safety notices">
        {interrupted && <div role="status">
          <p><strong>{session.interruptedCount} capture(s) interrupted and not applied.</strong> Audio jobs are not resumed after reload; only metadata remains in the interaction trace. Inspect the trace and record the findings again as needed.</p>
          <button type="button" onClick={session.acknowledgeInterrupted}>Acknowledge interrupted captures</button>
        </div>}
        {!session.ready && <p role="status">{session.busy ? "Checking accepted findings with the server. Completion is not yet verified."
          : "Accepted findings have not been evaluated by the server. Retry evaluation below."}</p>}
        {session.storageHint && <p role="status">{session.storageHint}</p>}
        {session.error && <p role="alert">{session.error}</p>}
        {voice.error && <p role="alert">{voice.error}</p>}
        {meaningful && result?.error && <p role="alert">{result.error}</p>}
        {(session.error || !session.ready) && <button type="button" disabled={session.busy} onClick={() => void session.refresh()}>Retry accepted assessment evaluation</button>}
        {meaningful && progressBlocked && <p role="alert"><strong>Progress blocked; resolve evidence issues before using final synthesis.</strong> Routine classifications and management are withheld. Accepted urgent actions remain active.</p>}
      </section>}

    <main className="clinical-workspace clinical-workspace--two-panel" data-active-panel={activePanel}>
      <AssessmentChecklist key={captureResetKey} encounter={session.encounter} result={result} progress={session.evaluation?.assessments}
        pendingAssessments={pendingAssessments} captureStatuses={captureStatuses}
        guideStatus={<section className="capture-toolbar" aria-label="Encounter recording settings">
          <p id="capture-disclosure">Research/demo only. Use synthetic data only; no identifying details. Audio is sent to Intron for transcription. Text/transcripts and the current canonical encounter are sent to the configured language-understanding service (external Azure OpenAI in demo mode). Audio stays in memory; transcripts, results, and interaction traces are retained in this tab.</p>
          <div className="capture-settings">
            <label className="capture-language" htmlFor="capture-language">Recording language
              <select id="capture-language" value={language} onChange={(event) => setLanguage(event.target.value as ASRLanguage | "")}>
                <option value="" disabled>Select language</option>
                <option value="en">English</option><option value="pcm">Nigerian Pidgin-English</option>
                <option value="yo">Yoruba-English</option><option value="ig">Igbo-English</option><option value="ha">Hausa-English</option>
              </select>
            </label>
            <label className="capture-consent"><input type="checkbox" checked={audioConsent} onChange={(event) => setAudioConsent(event.target.checked)} />I agree to send audio to Intron.</label>
            <label className="capture-consent"><input type="checkbox" checked={understandingConsent} onChange={(event) => setUnderstandingConsent(event.target.checked)} />I agree to send text/transcripts and the encounter to the language-understanding service, and retain traces in this tab.</label>
          </div>
          <p className="capture-meta">Choose a language and both consents before recording. Stopping processes the clip in the background; nothing is accepted until you review and apply it. Settings apply to new clips only.</p>
        </section>}
        renderCapture={(assessment) => <AssessmentCapture assessment={assessment} encounter={session.encounter}
          revision={session.revision} progress={session.evaluation?.assessments[assessment]} urgent={urgent}
          voice={voice} language={language} consent={{ audio: audioConsent, understanding: understandingConsent }}
          ready={session.ready} onDirty={setDirtySections} reviewDisabled={!session.ready || session.busy} />}
        tools={<>
          <InteractionHistory interactions={session.interactions} />
          <button className="guide-clear" type="button" onClick={clearAssessment}>Clear encounter</button>
          <p>AI only structures documented findings. After your explicit review, the deterministic engine produces classifications and management guidance.</p>
        </>}
      />

      <section className="output-panel" aria-label="Clinical result">
        <header className="pane-header result-pane-header">
          <div><p className="panel-index">Clinical result</p><h1>Classification and management</h1></div>
          <span className="deterministic-label"><ShieldCheck aria-hidden="true" size={14} /> Deterministic</span>
        </header>
        <div className="result-scroll">
          {!meaningful ? <section className="compact-empty-result">
            <ClipboardCheck aria-hidden="true" size={27} /><h2>Ready when you are</h2>
            <p>Follow the assessment guide. Record findings beside each section, then review what was captured.</p>
            <p>Clinical results appear here after findings are accepted.</p>
          </section> : finalReady && result ? <ResultPanel result={result} /> :
            <section className="quiet-result" aria-live="polite">
              <h2>{progressBlocked ? "Review evidence issues" : interrupted ? "Acknowledge interrupted captures before final plan"
                : result?.is_complete && hasDirty ? "Process or discard unprocessed edits before final plan" : result?.is_complete && pendingJobs.length
                ? "Review captured findings before final plan" : "Assessment in progress"}</h2>
              <p>{progressBlocked ? "Resolve the blockers shown in the assessment sections. Final synthesis is withheld."
                : interrupted ? "Review the interruption notice above. Acknowledgement does not accept or recover interrupted findings."
                  : result?.is_complete && hasDirty ? "Typed findings, transcript corrections, or selected retractions still need your attention in the assessment sections."
                : result?.is_complete && pendingJobs.length ? "The accepted assessment is complete. New captures still need review or discard."
                  : "Continue with the next observations in each assessment section. Only accepted findings contribute to the result."}</p>
              {urgent && <p>Accepted urgent guidance remains active above. Do not delay immediate care.</p>}
            </section>}
        </div>
      </section>
    </main>

    <footer className="site-footer">
      <p><strong>Research prototype.</strong> Not a production medical device or authorization for autonomous clinical use.</p>
      <p>Unchecked findings remain unknown; they are never inferred absent.</p>
    </footer>
  </div>;
}
