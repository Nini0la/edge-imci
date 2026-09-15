import { useEffect, useRef, useState } from "react";
import { ClipboardCheck, LockKeyhole, Mic, ShieldCheck } from "lucide-react";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
import { AssessmentCapture, CandidateDetails } from "./components/AssessmentCapture";
import { ClinicalFieldControl } from "./components/ClinicalFieldControl";
import { ResultPanel } from "./components/ResultPanel";
import { InteractionHistory } from "./components/InteractionHistory";
import { MobileAssessmentHome, MobileAssessmentTabs, MobileDock, MobileHeader, type MobileView } from "./components/MobileWorkspace";
import { affectedAssessments, assessmentIds, hasMeaningfulEvidence, unresolvedChanges } from "./lib/assessment";
import { clinicalValue, effectiveChanges, guideResolutions } from "./lib/guideEvidence";
import { useGuideEditor } from "./lib/useGuideEditor";
import { buildChecklist } from "./lib/checklist";
import { useMobileLayout } from "./lib/layout";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import { useVoiceCapture, type CaptureJob } from "./lib/useVoiceCapture";
import type { ASRLanguage, AssessmentId } from "./types";

export default function App() {
  const session = useAssessmentSession();
  const voice = useVoiceCapture(session);
  const guide = useGuideEditor(session, voice);
  const [activePanel, setActivePanel] = useState<"assessment" | "result">("assessment");
  const [language, setLanguage] = useState<ASRLanguage | "">("");
  const [audioConsent, setAudioConsent] = useState(false);
  const [understandingConsent, setUnderstandingConsent] = useState(false);
  const [captureResetKey, setCaptureResetKey] = useState(0);
  const [dirtySections, setDirtySections] = useState<Partial<Record<AssessmentId, boolean>>>({});
  const mobile = useMobileLayout();
  const [mobileView, setMobileView] = useState<MobileView>({ screen: "list", assessment: null, tab: "guidance" });
  const lastFocus = useRef<{ node: HTMLElement; dock: boolean } | null>(null);
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
    [...job.changedFields, ...effectiveChanges(job).map((change) => change.field)]))])];
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
  const checklist = buildChecklist(session.encounter, result);
  const selectedSection = checklist.sections.find((section) => section.id === mobileView.assessment);
  const setupReady = Boolean(language && audioConsent && understandingConsent);
  const requiredFieldPaths = [...new Set(Object.values(session.evaluation?.assessments ?? {})
    .flatMap((progress) => [...progress.missing_fields, ...(progress.question ? [progress.question.field] : [])]))];
  const agePending = guide.pendingFieldPaths.includes("patient_facts.age_months");
  const ageUnknown = (session.encounter.patient_facts as { age_months?: number | null } | undefined)?.age_months == null;

  function renderField(assessment: AssessmentId, path: string, labels?: { yes: string; no: string }) {
    const field = guide.field(assessment, path);
    const owner = voice.jobs.find((job) => job.id === field?.jobId);
    return <div data-guide-field={path}>{field ? <ClinicalFieldControl {...field} booleanLabels={labels} />
      : <p className="capture-meta">{guide.schema ? "Control unavailable. Confirmed evidence remains unchanged."
        : "Controls unavailable until assessment metadata loads. Confirmed evidence remains unchanged."}</p>}
      {owner && owner.assessment !== assessment && path !== "patient_facts.age_months" && <button type="button" className="guide-clear"
        onClick={() => reviewJob(owner.id)}>Review with {checklist.sections.find((section) => section.id === owner.assessment)?.label}</button>}
    </div>;
  }

  function reviewJob(id: string) {
    const job = voice.jobs.find((item) => item.id === id);
    if (!job) return;
    guide.selectJob(id);
    if (mobile) setMobileView({ screen: "assessment", assessment: job.assessment, tab: "guidance" });
    else {
      const section = document.querySelector<HTMLDetailsElement>(`details[data-assessment="${job.assessment}"]`);
      if (section) {
        section.open = true;
        section.querySelector<HTMLElement>("summary")?.focus();
        section.scrollIntoView?.({ block: "start", behavior: "smooth" });
      }
    }
  }

  function renderSectionReview(assessment: AssessmentId) {
    const job = guide.selectedJob(assessment);
    if (!job) return null;
    const jobs = pendingJobs.filter((item) => item.assessment === assessment && item.originalCandidate
      && ["captured", "review", "preparing_review", "applying"].includes(item.status));
    const currentReview = job.status === "review" && (job.reviewEditVersion ?? 0) === (job.editVersion ?? 0);
    const changes = currentReview ? job.candidate?.changes ?? [] : effectiveChanges(job);
    const choices = guideResolutions(job);
    const unresolved = changes.filter((row) => {
      const shown = guide.field(assessment, row.field);
      const proposed = choices[row.field] === "keep" ? clinicalValue(session.encounter, row.field) : row.value;
      return unresolvedChanges([row], choices).length > 0 || shown?.source === "conflict"
        || (shown?.pending && shown.jobId !== job.id && shown.value !== proposed);
    });
    const stale = (job.reviewRevision ?? job.originalRevision) !== session.revision;
    const invalid = Object.values(job.workerEdits ?? {}).some((edit) => edit.error);
    const disabled = !session.ready || session.busy || !guide.schema || invalid
      || job.status === "preparing_review" || job.status === "applying";
    return <section className="guide-review" aria-label={`${assessment} findings review`}>
      <h3>Awaiting confirmation</h3>
      {jobs.length > 1 && <>
        <div className="capture-actions">{jobs.map((item, index) => <button type="button" key={item.id}
          aria-pressed={item.id === job.id} disabled={job.status === "applying"}
          onClick={() => guide.selectJob(item.id)}>{item.originalCandidate?.extraction_mode === "worker-review"
            ? "Review worker answers" : `Review recording ${index + 1}`}</button>)}</div>
        <p className="capture-meta">Other drafts are retained when you switch sources. Confirm each separately.</p>
      </>}
      <p>{changes.length ? `${changes.length} observation(s) staged. Check the answers on the assessment before confirming.`
        : "No new evidence extracted. Confirming acknowledges this report without changing accepted findings."}</p>
      {stale && <p className="capture-warning" role="status">Accepted findings changed. Refresh review first, then check the answers again before confirming.</p>}
      {unresolved.length > 0 && <div className="capture-warning" role="status">
        <p>Choose answers above or keep confirmed answers for {unresolved.length} flagged observation(s).</p>
        <div className="capture-actions">{unresolved.map((change) => <button key={change.field} type="button" onClick={() => {
          const target = guide.schema?.fields[change.field]?.assessments;
          const origin = target?.includes(assessment) ? assessment : target?.[0] ?? assessment;
          if (mobile) setMobileView({ screen: "assessment", assessment: origin, tab: "guidance" });
          const section = document.querySelector<HTMLDetailsElement>(`details[data-assessment="${origin}"]`);
          if (section && !mobile) section.open = true;
          requestAnimationFrame(() => {
            const field = document.querySelector<HTMLElement>(`${change.field === "patient_facts.age_months"
              ? mobile ? ".mobile-assessment-focus" : ".assessment-scope" : `details[data-assessment="${origin}"]`} [data-guide-field="${change.field}"]`);
            field?.querySelector<HTMLElement>("input, button")?.focus();
            field?.scrollIntoView?.({ block: "center", behavior: "smooth" });
          });
        }}>{change.label}</button>)}</div>
      </div>}
      {invalid && <p className="capture-warning" role="alert">Correct invalid answers on the assessment before confirming.</p>}
      {job.error && <p className="capture-error" role="alert">{job.error} Check the answers and retry confirmation.</p>}
      {!!job.originalCandidate?.warnings.length && <p className="capture-warning">This report has warnings. Check Details and the flagged answers.</p>}
      {!!job.originalCandidate?.uncertainties?.length && <p className="capture-warning">Some source findings are ambiguous. Choose the observed answers; source details remain unchanged.</p>}
      <button type="button" disabled={disabled} onClick={() => {
        if (disabled) return;
        if (!stale && !changes.length && !window.confirm("Acknowledge that this report supplied no new evidence? Accepted findings will not change. If an accepted value is uncertain, choose Not assessed on the assessment instead.")) return;
        void guide.confirm(assessment);
      }}>{job.status === "preparing_review" ? "Preparing review..." : job.status === "applying" ? "Confirming findings..."
        : stale ? "Refresh review" : "Confirm findings"}</button>
      {job.originalCandidate && <details className="capture-details"><summary>Details: original report and review</summary>
        {job.question && <><strong>Question at capture</strong><p>{job.question.text}</p><code>{job.question.field}</code></>}
        {job.transcript && <><strong>Original ASR transcript (read-only)</strong><p className="trace-text">{job.transcript.transcript}</p></>}
        <CandidateDetails candidate={job.originalCandidate} />
        <strong>Review metadata</strong><pre>{JSON.stringify({ changes, workerEdits: job.workerEdits }, null, 2)}</pre>
        <strong>Control schema</strong><pre>{JSON.stringify(guide.schema, null, 2)}</pre>
      </details>}
    </section>;
  }

  const ageOwner = voice.jobs.find((job) => job.id === guide.field("danger", "patient_facts.age_months")?.jobId)?.assessment ?? "danger";
  const ageControl = <>{renderField("danger", "patient_facts.age_months")}
    {agePending && !(mobileView.screen === "assessment" && mobileView.assessment === ageOwner) && <button type="button" className="guide-clear"
      onClick={() => setMobileView({ screen: "assessment", assessment: ageOwner, tab: "guidance" })}>
      Review age with {checklist.sections.find((section) => section.id === ageOwner)?.label}</button>}</>;

  useEffect(() => {
    // Explicit mobile navigation moves the view; background job updates never do.
    if (!mobile) return;
    document.getElementById("mobile-view-heading")?.focus({ preventScroll: true });
    document.querySelector(mobileView.screen === "results" ? ".output-panel" : ".checklist-panel")?.scrollTo({ top: 0 });
  }, [mobileView]);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const active = document.activeElement;
    const previous = lastFocus.current;
    const removed = active === document.body && previous
      && (!previous.node.isConnected || previous.node.matches(":disabled"));
    if (removed || (active instanceof HTMLElement && !active.getClientRects().length)) {
      const dockTarget = mobile && previous?.dock
        ? document.querySelector<HTMLElement>(voice.audioState === "idle"
          ? '.mobile-dock .mobile-record-button:not(:disabled)'
          : '.mobile-dock [aria-label="Stop recording"]:not(:disabled), .mobile-dock [aria-label="Cancel recording"]')
        : null;
      const target = mobile ? dockTarget ?? document.getElementById("mobile-view-heading") : document.querySelector<HTMLElement>(".brand");
      target?.focus({ preventScroll: true });
    }
  }, [mobile, voice.audioState]);

  useEffect(() => {
    if (!hasDirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [hasDirty]);

  function clearAssessment() {
    if (!window.confirm("Clear this encounter, all unaccepted findings, audio, interaction history, and the saved tab draft? This cannot be undone.")) return;
    voice.clear();
    guide.reset();
    session.reset();
    setDirtySections({});
    // Only explicit encounter clearing resets local editors, never an accepted revision.
    setCaptureResetKey((previous) => previous + 1);
    setAudioConsent(false);
    setUnderstandingConsent(false);
    setActivePanel("assessment");
    setMobileView({ screen: "list", assessment: null, tab: "guidance" });
  }

  return <div className={mobile ? "app-frame app-frame--mobile" : "app-frame"}
    onFocusCapture={(event) => { lastFocus.current = { node: event.target, dock: Boolean(event.target.closest(".mobile-dock")) }; }}>
    <header className="site-header">
      <a className="brand" href="/" aria-label="EdgeIMCI home">
        <span className="brand-symbol"><img src="/edge-imci-mark.svg" alt="" aria-hidden="true" /></span>
        <span>Edge<strong>IMCI</strong></span>
      </a>
      <div className="header-context"><span>Initial sick-child assessment</span><span>Ages 2–59 months</span></div>
      <div className="header-trust"><LockKeyhole aria-hidden="true" size={14} /> Intron voice demo</div>
    </header>

    <MobileHeader view={mobileView} sections={checklist.sections} onNavigate={setMobileView} />

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

    {(!guide.schema || guide.schemaError || !session.ready || session.storageHint || session.error || voice.error || interrupted || (meaningful && (progressBlocked || result?.error))) &&
      <section className="workspace-notices" aria-label="Encounter service and safety notices">
        {guide.schemaError ? <div role="alert"><p>Assessment controls could not load: {guide.schemaError}</p>
          <button type="button" onClick={guide.retrySchema}>Retry controls</button></div>
          : !guide.schema && <p role="status">Loading assessment controls...</p>}
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

    <main className="clinical-workspace clinical-workspace--two-panel" data-active-panel={activePanel}
      data-mobile-screen={mobile ? mobileView.screen : undefined}
      data-mobile-assessment={mobile ? mobileView.assessment ?? undefined : undefined}
      data-mobile-tab={mobile ? mobileView.tab : undefined}>
      <AssessmentChecklist key={captureResetKey} encounter={session.encounter} result={result} progress={session.evaluation?.assessments}
        workingEncounter={guide.workingEncounter} renderField={renderField} renderSectionReview={renderSectionReview}
        pendingFieldPaths={guide.pendingFieldPaths} requiredFieldPaths={requiredFieldPaths}
        pendingAssessments={pendingAssessments} captureStatuses={captureStatuses}
        mobileView={mobile ? mobileView : undefined}
        mobileHome={mobile && <MobileAssessmentHome checklist={checklist} progress={session.evaluation?.assessments}
          captureStatuses={captureStatuses} pendingAssessments={pendingAssessments} onNavigate={setMobileView} setupReady={setupReady} ageControl={ageControl} />}
        mobileFocus={mobile && <MobileAssessmentTabs view={mobileView} section={selectedSection}
          progress={mobileView.assessment ? session.evaluation?.assessments[mobileView.assessment] : undefined}
          urgent={urgent} jobs={voice.jobs} onNavigate={setMobileView} ageControl={(ageUnknown || agePending) ? ageControl : undefined} />}
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
          {mobile && <p className="mobile-research-note">Research prototype. Not a production medical device or authorization for autonomous clinical use.</p>}
          {mobile && <button className="guide-clear" type="button" onClick={() => setMobileView({ ...mobileView,
            screen: mobileView.assessment ? "assessment" : "list" })}>Continue assessment</button>}
        </section>}
        renderCapture={(assessment) => <AssessmentCapture assessment={assessment} encounter={session.encounter}
          revision={session.revision} progress={session.evaluation?.assessments[assessment]} urgent={urgent}
          voice={voice} language={language} consent={{ audio: audioConsent, understanding: understandingConsent }}
          ready={session.ready} onDirty={setDirtySections} reviewDisabled={!session.ready || session.busy || !guide.schema} onReviewJob={reviewJob} />}
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
                  : result?.is_complete && hasDirty ? "Typed findings still need processing or clearing in the assessment sections."
                : result?.is_complete && pendingJobs.length ? "The accepted assessment is complete. New captures still need review or discard."
                  : "Continue with the next observations in each assessment section. Only accepted findings contribute to the result."}</p>
              {urgent && <p>Accepted urgent guidance remains active above. Do not delay immediate care.</p>}
            </section>}
        </div>
      </section>
    </main>

    <MobileDock view={mobileView} sections={checklist.sections} voice={voice} language={language}
      consent={{ audio: audioConsent, understanding: understandingConsent }} ready={session.ready}
      onNavigate={setMobileView} urgent={urgent} pendingCount={pendingJobs.length} />

    <footer className="site-footer">
      <p><strong>Research prototype.</strong> Not a production medical device or authorization for autonomous clinical use.</p>
      <p>Unchecked findings remain unknown; they are never inferred absent.</p>
    </footer>
  </div>;
}
