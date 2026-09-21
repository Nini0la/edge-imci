import { useEffect, useRef, useState } from "react";
import { ClipboardCheck, LockKeyhole, Mic, ShieldCheck } from "lucide-react";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
import { AssessmentCapture } from "./components/AssessmentCapture";
import { CaptureProgress } from "./components/CaptureProgress";
import { ClinicalFieldControl } from "./components/ClinicalFieldControl";
import { ResultPanel } from "./components/ResultPanel";
import { ReportPanel } from "./components/ReportPanel";
import { InteractionHistory } from "./components/InteractionHistory";
import { MobileAssessmentHome, MobileAssessmentTabs, MobileDock, MobileHeader, type MobileView } from "./components/MobileWorkspace";
import { affectedAssessments, assessmentIds, hasMeaningfulEvidence, unresolvedChanges } from "./lib/assessment";
import { clinicalValue, effectiveChanges, guideResolutions } from "./lib/guideEvidence";
import { useGuideEditor } from "./lib/useGuideEditor";
import { buildChecklist } from "./lib/checklist";
import { useMobileLayout } from "./lib/layout";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import { useVoiceCapture, type CaptureContext, type CaptureJob } from "./lib/useVoiceCapture";
import type { ASRLanguage, AssessmentId, CaptureScope } from "./types";

export default function App() {
  const session = useAssessmentSession();
  const voice = useVoiceCapture(session);
  const guide = useGuideEditor(session, voice);
  const [activePanel, setActivePanel] = useState<"assessment" | "report" | "result">("assessment");
  const [reportDraft, setReportDraft] = useState<{ text: string; context?: CaptureContext }>({ text: "" });
  const [assessmentRequested, setAssessmentRequested] = useState(false);
  const [generatedRevision, setGeneratedRevision] = useState<number | null>(null);
  const [language, setLanguage] = useState<ASRLanguage | "">("");
  const [captureResetKey, setCaptureResetKey] = useState(0);
  const [dirtySections, setDirtySections] = useState<Partial<Record<AssessmentId, boolean>>>({});
  const mobile = useMobileLayout();
  const [mobileView, setMobileView] = useState<MobileView>({ screen: "assessment", assessment: "danger", tab: "guidance", intro: true });
  const previousMobileView = useRef(mobileView);
  const dangerIntro = mobile && mobileView.intro && mobileView.screen === "assessment"
    && mobileView.assessment === "danger" && mobileView.tab === "guidance";
  const lastFocus = useRef<{ node: HTMLElement; dock: boolean } | null>(null);
  const dirtyAssessments = assessmentIds.filter((id) => dirtySections[id]);
  const hasReportDraft = Boolean(reportDraft.text.trim());
  const hasDirty = dirtyAssessments.length > 0 || hasReportDraft;
  const interrupted = session.interruptedCount > 0;
  const result = session.evaluation?.analysis;
  const meaningful = hasMeaningfulEvidence(session.encounter);
  const urgent = Boolean(result?.is_urgent || Object.values(session.evaluation?.assessments ?? {})
    .some((item) => item.status === "URGENT" || item.decision === "URGENT"));
  const progressBlocked = Boolean(result?.contradictions.length || Object.values(session.evaluation?.assessments ?? {})
    .some((item) => item.decision === "BLOCK" || item.blockers.length));
  // Immediate actions are safe before final synthesis, but only from accepted engine output.
  const immediateActions = meaningful && result?.is_urgent && result.schema_valid && !result.error && !result.outside_supported_scope
    ? result.urgent_actions : [];
  const pendingJobs = voice.jobs.filter((job) => job.status !== "accepted" && job.status !== "discarded");
  const pendingAssessments = [...new Set([...(hasReportDraft ? assessmentIds : []), ...dirtyAssessments, ...pendingJobs.flatMap((job) => affectedAssessments(job.assessment,
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
  const resultReady = session.ready && !session.busy && !session.error && result?.schema_valid && !result.error && !result.outside_supported_scope
    && !pendingJobs.length && !hasDirty && !interrupted && !progressBlocked;
  const finalReady = meaningful && resultReady && result?.is_complete;
  const requestedIncomplete = resultReady && generatedRevision === session.revision
    && (result?.state === "INCOMPLETE" || result?.state === "URGENT_INCOMPLETE");
  const requestNeedsReview = assessmentRequested && (pendingJobs.length > 0 || hasDirty);
  const checklist = buildChecklist(session.encounter, result);
  const selectedSection = checklist.sections.find((section) => section.id === mobileView.assessment);
  // Both layouts use deployment-authorized processing, not per-encounter consent boxes.
  const processingAuthorization = { audio: true, understanding: true };
  const canProcessSpeech = Boolean(language && processingAuthorization.audio && processingAuthorization.understanding);
  const requiredFieldPaths = [...new Set(Object.values(session.evaluation?.assessments ?? {})
    .flatMap((progress) => [...progress.missing_fields, ...(progress.question ? [progress.question.field] : [])]))];
  const agePending = guide.pendingFieldPaths.includes("patient_facts.age_months");
  const ageUnknown = (session.encounter.patient_facts as { age_months?: number | null } | undefined)?.age_months == null;

  function renderField(assessment: AssessmentId, path: string, labels?: { yes: string; no: string }) {
    const field = guide.field(assessment, path);
    const owner = voice.jobs.find((job) => job.id === field?.jobId);
    return <div data-guide-field={path}>{field ? <ClinicalFieldControl {...field} booleanLabels={labels} compact={mobile} />
      : <p className="capture-meta">{guide.schema ? "Control unavailable. Confirmed evidence remains unchanged."
        : "Controls unavailable until assessment metadata loads. Confirmed evidence remains unchanged."}</p>}
      {owner && owner.assessment !== assessment && path !== "patient_facts.age_months" && <button type="button" className="guide-clear"
        onClick={() => reviewJob(owner.id)}>Review with {owner.assessment === "full-note" ? "text report" : checklist.sections.find((section) => section.id === owner.assessment)?.label}</button>}
    </div>;
  }

  function openAssessment(assessment: AssessmentId, tab: "guidance" | "findings" = "guidance") {
    setActivePanel("assessment");
    if (mobile) setMobileView({ screen: "assessment", assessment, tab });
    else {
      const section = document.querySelector<HTMLDetailsElement>(`details[data-assessment="${assessment}"]`);
      if (section) {
        section.open = true;
        section.querySelector<HTMLElement>("summary")?.focus();
        section.scrollIntoView?.({ block: "start", behavior: "smooth" });
      }
    }
  }

  function reviewJob(id: string) {
    const job = voice.jobs.find((item) => item.id === id);
    if (!job) return;
    guide.selectJob(id);
    if (job.assessment === "full-note") openReport();
    else openAssessment(job.assessment, job.status === "failed" ? "findings" : "guidance");
  }

  function openReport() {
    setActivePanel("report");
    if (mobile) setMobileView({ screen: "report", assessment: null, tab: "guidance" });
    else document.getElementById("report-heading")?.focus({ preventScroll: true });
  }

  async function generateRecommendations() {
    if (session.busy) return;
    setAssessmentRequested(true);
    setGeneratedRevision(null);
    setActivePanel("result");
    if (mobile) setMobileView({ ...mobileView, screen: "results" });
    document.querySelector<HTMLElement>(".result-scroll")?.scrollTo?.({ top: 0 });
    if (pendingJobs.length || hasDirty || interrupted || progressBlocked) return;
    const revision = session.currentRevision();
    if (await session.refresh() && session.currentRevision() === revision + 1) setGeneratedRevision(revision + 1);
  }

  function renderSectionReview(assessment: CaptureScope, placement: "section" | "intro" | "age" = "section") {
    if (dangerIntro && assessment === "danger" && placement === "section") return null;
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
      || job.status === "preparing_review" || job.status === "applying"
      || pendingJobs.some((pending) => pending.assessment === "full-note" && ["queued", "extracting"].includes(pending.status));
    const extraIntroFields = placement === "intro" && changes.some((row) => !row.field.startsWith("danger_signs."));
    const progress = assessment === "full-note" ? undefined : session.evaluation?.assessments[assessment];
    const completeness = progress?.status === "URGENT" ? "urgent" : progress?.status === "COMPLETE" ? "complete" : "incomplete";
    return <section className={mobile ? "guide-review mobile-confirmation" : "guide-review"}
      data-completeness={mobile ? completeness : undefined} aria-label={`${assessment} findings review`}>
      {!mobile && <h3>{assessment === "full-note" ? "Confirm text findings" : "Awaiting confirmation"}</h3>}
      {jobs.length > 1 && <>
        <div className="capture-actions">{jobs.map((item, index) => <button type="button" key={item.id}
          aria-pressed={item.id === job.id} disabled={job.status === "applying"}
          onClick={() => guide.selectJob(item.id)}>{item.originalCandidate?.extraction_mode === "worker-review"
            ? "Review worker answers" : `Review ${item.language ? "recording" : "text report"} ${index + 1}`}</button>)}</div>
        {!mobile && <p className="capture-meta">Other drafts are retained when you switch sources. Confirm each separately.</p>}
      </>}
      {!mobile && <p>{changes.length ? `${changes.length} observation(s) staged. Check the answers on the assessment before confirming.`
        : "No new evidence extracted. Confirming acknowledges this report without changing accepted findings."}</p>}
      {stale && <p className="capture-warning" role="status">{mobile ? "Answers changed. Refresh review." : "Accepted findings changed. Refresh review first, then check the answers again before confirming."}</p>}
      {unresolved.length > 0 && <div className="capture-warning" role="status">
        <p>{mobile ? `${unresolved.length} answer(s) need review.` : `Choose answers above or keep confirmed answers for ${unresolved.length} flagged observation(s).`}</p>
        <div className="capture-actions">{unresolved.map((change) => <button key={change.field} type="button" onClick={() => {
          const target = guide.schema?.fields[change.field]?.assessments;
          const origin = assessment !== "full-note" && target?.includes(assessment) ? assessment : target?.[0] ?? "danger";
          setActivePanel("assessment");
          if (mobile) setMobileView({ screen: "assessment", assessment: origin, tab: "guidance", intro: false });
          const section = document.querySelector<HTMLDetailsElement>(`details[data-assessment="${origin}"]`);
          if (section && !mobile) section.open = true;
          requestAnimationFrame(() => {
            const field = document.querySelector<HTMLElement>(`${change.field === "patient_facts.age_months"
              ? ".assessment-scope" : `details[data-assessment="${origin}"]`} [data-guide-field="${change.field}"]`);
            field?.querySelector<HTMLElement>("input, button")?.focus();
            field?.scrollIntoView?.({ block: "center", behavior: "smooth" });
          });
        }}>{change.label}</button>)}</div>
      </div>}
      {invalid && <p className="capture-warning" role="alert">Correct invalid answers on the assessment before confirming.</p>}
      {job.error && <p className="capture-error" role="alert">{job.error} Check the answers and retry confirmation.</p>}
      {!mobile && !!job.originalCandidate?.warnings.length && <p className="capture-warning">Check the proposed answers against your report before confirming.</p>}
      {!!job.originalCandidate?.uncertainties?.length && <p className="capture-warning">Some source findings are ambiguous. Choose the observed answers; source details remain unchanged.</p>}
      <button type="button" className={mobile ? "mobile-confirm-button" : undefined} disabled={disabled}
        aria-describedby={mobile ? `confirmation-progress-${assessment}-${placement}` : undefined} onClick={() => {
        if (disabled) return;
        if (extraIntroFields) {
          setMobileView({ screen: "assessment", assessment: "danger", tab: "guidance", intro: false });
          return;
        }
        if (!stale && !changes.length && !window.confirm("Acknowledge that this report supplied no new evidence? Accepted findings will not change. If an accepted value is uncertain, choose Not assessed on the assessment instead.")) return;
        void guide.confirm(assessment);
      }}>{job.status === "preparing_review" ? "Preparing review..." : job.status === "applying" ? "Confirming findings..."
        : extraIntroFields ? "Review other findings" : stale ? "Refresh review" : placement === "age" ? "Confirm age" : "Confirm findings"}</button>
      {mobile && <span className="mobile-sr-only" id={`confirmation-progress-${assessment}-${placement}`}>
        {completeness === "incomplete" ? "Assessment incomplete. Partial findings can be confirmed." : completeness === "urgent" ? "Accepted urgent guidance remains active." : "Accepted assessment complete."}
      </span>}
    </section>;
  }

  const ageOwner = voice.jobs.find((job) => job.id === guide.field("danger", "patient_facts.age_months")?.jobId)?.assessment ?? "danger";
  const fullReport = guide.selectedJob("full-note");
  const reportChanges = fullReport ? effectiveChanges(fullReport) : [];
  const ageJob = guide.selectedJob(ageOwner);
  const ageOnlyDraft = ageJob && effectiveChanges(ageJob).length > 0
    && effectiveChanges(ageJob).every((row) => row.field === "patient_facts.age_months");
  const ageReview = mobile && mobileView.screen === "list" && agePending
    ? ageOnlyDraft ? renderSectionReview(ageOwner, "age") : <button type="button" className="guide-clear"
      onClick={() => ageOwner === "full-note" ? openReport() : setMobileView({ screen: "assessment", assessment: ageOwner, tab: "guidance", intro: false })}>
      Review age with {ageOwner === "full-note" ? "text report" : checklist.sections.find((section) => section.id === ageOwner)?.label}</button> : null;

  useEffect(() => {
    // A hot-reloaded client may still hold the removed setup screen in memory.
    if (mobile && !["list", "assessment", "report", "results"].includes(mobileView.screen)) {
      setMobileView({ ...mobileView, screen: mobileView.assessment ? "assessment" : "list" });
    }
  }, [mobile, mobileView.screen, mobileView.assessment]);

  useEffect(() => {
    // Explicit mobile navigation moves the view; background job updates never do.
    if (previousMobileView.current === mobileView) return;
    previousMobileView.current = mobileView;
    if (!mobile) return;
    document.getElementById("mobile-view-heading")?.focus({ preventScroll: true });
    document.querySelector(mobileView.screen === "results" ? ".output-panel" : mobileView.screen === "report" ? ".report-panel" : ".checklist-panel")?.scrollTo({ top: 0 });
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
    if (!window.confirm(mobile || session.needsResumeDecision
      ? "Start a new assessment? This clears the saved answers, pending captures, and history in this tab."
      : "Clear this encounter, all unaccepted findings, audio, interaction history, and the saved tab draft? This cannot be undone.")) return;
    voice.clear();
    guide.reset();
    session.reset();
    setDirtySections({});
    setReportDraft({ text: "" });
    setAssessmentRequested(false);
    setGeneratedRevision(null);
    // Only explicit encounter clearing resets local editors, never an accepted revision.
    setCaptureResetKey((previous) => previous + 1);
    setActivePanel("assessment");
    setMobileView({ screen: "assessment", assessment: "danger", tab: "guidance", intro: true });
  }

  const assessmentAction = <div className="assessment-submit">
    <button type="button" className="generate-assessment" disabled={session.busy} onClick={() => void generateRecommendations()}>
      <ClipboardCheck size={20} aria-hidden="true" />{session.busy ? "Checking assessment..." : "Generate IMCI recommendations"}
    </button>
    <p>Checks confirmed findings and shows what is still missing.</p>
  </div>;

  if (session.needsResumeDecision) return <div className={mobile ? "app-frame app-frame--mobile" : "app-frame"}>
    <header className="site-header"><span className="brand">Edge<strong>IMCI</strong></span></header>
    <main className="resume-assessment" aria-labelledby="resume-assessment-title">
      <h1 id="resume-assessment-title">Saved assessment</h1>
      <p>This tab has a previous assessment. Choose whether to continue it or start with all observations unassessed.</p>
      <button type="button" onClick={() => void session.resumeSaved()}>Resume saved assessment</button>
      <button type="button" className="resume-assessment__new" onClick={clearAssessment}>Start new assessment</button>
    </main>
  </div>;

  return <div className={mobile ? "app-frame app-frame--mobile" : "app-frame"} data-mobile-intro={dangerIntro || undefined}
    onFocusCapture={(event) => { lastFocus.current = { node: event.target, dock: Boolean(event.target.closest(".mobile-dock")) }; }}>
    <header className="site-header">
      <a className="brand" href="/" aria-label="EdgeIMCI home">
        <span className="brand-symbol"><img src="/edge-imci-mark.svg" alt="" aria-hidden="true" /></span>
        <span>Edge<strong>IMCI</strong></span>
      </a>
      <div className="header-context"><span>Initial sick-child assessment</span><span>Ages 2–59 months</span></div>
      <div className="header-trust"><LockKeyhole aria-hidden="true" size={14} /> Intron voice demo</div>
    </header>

    <MobileHeader view={mobileView} sections={checklist.sections} onNavigate={setMobileView} urgent={urgent} />

    <nav className="mobile-panel-nav" aria-label="Application panels">
      {(["assessment", "report", "result"] as const).map((panel) => <button className={activePanel === panel ? "active" : ""}
        type="button" key={panel} aria-pressed={activePanel === panel} onClick={() => setActivePanel(panel)}>
        {panel === "assessment" ? "Assessment" : panel === "report" ? "Text report" : "Result"}
        {panel === "result" && urgent && <span className="urgent-dot" />}
      </button>)}
    </nav>

    {voice.audioState !== "idle" && <section className="recording-banner" aria-label="Active recording">
      <Mic aria-hidden="true" size={18} />
      <span role="status"><strong>{voice.audioState === "permission" ? "Waiting for microphone permission"
        : voice.audioState === "stopping" ? "Finishing recording" : "Recording"}</strong>{recording && ` / ${recording.assessment} / ${recording.language}`}</span>
      <button type="button" disabled={voice.audioState !== "recording"} onClick={voice.stop}>Stop</button>
      <button type="button" onClick={voice.cancelRecording}>Cancel</button>
    </section>}

    <CaptureProgress jobs={voice.jobs} sections={checklist.sections} onReview={reviewJob} />

    {(!guide.schema || guide.schemaError || !session.ready || session.storageHint || session.error || voice.error || interrupted || (meaningful && (progressBlocked || result?.error))) &&
      <section className="workspace-notices" aria-label="Encounter service and safety notices">
        {guide.schemaError ? <div role="alert"><p>Assessment controls could not load: {guide.schemaError}</p>
          <button type="button" onClick={guide.retrySchema}>Retry controls</button></div>
          : !guide.schema && <p role="status">Loading assessment controls...</p>}
        {interrupted && <div role="status">
          <p><strong>{session.interruptedCount} capture(s) interrupted and not applied.</strong> Audio jobs are not resumed after reload. Check the recording history and record the findings again as needed.</p>
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

    <main className="clinical-workspace clinical-workspace--three-panel" data-active-panel={activePanel}
      data-mobile-screen={mobile ? mobileView.screen : undefined}
      data-mobile-assessment={mobile ? mobileView.assessment ?? undefined : undefined}
      data-mobile-tab={mobile ? mobileView.tab : undefined}
      data-mobile-intro={dangerIntro || undefined}
      data-show-age={mobile && !dangerIntro && (mobileView.screen === "list"
        || (mobileView.screen === "assessment" && (ageUnknown || agePending))) || undefined}>
      <AssessmentChecklist key={captureResetKey} encounter={session.encounter} result={result} progress={session.evaluation?.assessments}
        workingEncounter={guide.workingEncounter} renderField={renderField} renderSectionReview={renderSectionReview}
        pendingFieldPaths={guide.pendingFieldPaths} requiredFieldPaths={requiredFieldPaths}
        pendingAssessments={pendingAssessments} captureStatuses={captureStatuses}
        ageReview={ageReview}
        mobileView={mobile ? mobileView : undefined}
        mobileHome={mobile && <MobileAssessmentHome checklist={checklist} progress={session.evaluation?.assessments}
          captureStatuses={captureStatuses} pendingAssessments={pendingAssessments} onNavigate={setMobileView}
          assessmentAction={assessmentAction}
          tools={<details className="mobile-assessment-options"><summary>Assessment options</summary>
            <details><summary>About processing</summary><p id="capture-disclosure">This mobile demo uses pre-authorized processing: audio goes to Intron and transcripts/encounter context go to the language-understanding service. Clinical rules remain local. Use synthetic data only.</p></details>
            <InteractionHistory interactions={session.interactions} showDebug={false} />
            <button type="button" className="guide-clear" onClick={clearAssessment}>Start new assessment</button>
          </details>} />}
        mobileFocus={mobile && <MobileAssessmentTabs view={mobileView} section={selectedSection}
          progress={mobileView.assessment ? session.evaluation?.assessments[mobileView.assessment] : undefined}
          urgent={urgent} jobs={voice.jobs} onNavigate={setMobileView} />}
        guideStatus={!mobile && <section className="capture-toolbar" aria-label="Encounter recording settings">
          <div className="capture-settings">
            <label className="capture-language" htmlFor="capture-language">Recording language
              <select id="capture-language" value={language} onChange={(event) => setLanguage(event.target.value as ASRLanguage | "")}>
                <option value="" disabled>Select language</option>
                <option value="en">English</option><option value="pcm">Nigerian Pidgin-English</option>
                <option value="yo">Yoruba-English</option><option value="ig">Igbo-English</option><option value="ha">Hausa-English</option>
              </select>
            </label>
          </div>
          <details className="processing-disclosure"><summary>About processing</summary>
            <p id="capture-disclosure">This demo uses deployment-authorized processing: audio goes to Intron and transcripts/encounter context go to the language-understanding service. Clinical rules remain local. Use synthetic data only. Audio stays in memory; transcripts and interaction history remain in this tab.</p>
          </details>
        </section>}
        renderCapture={(assessment) => <AssessmentCapture assessment={assessment} encounter={session.encounter}
          revision={session.revision} progress={session.evaluation?.assessments[assessment]} urgent={urgent}
          voice={voice} language={language} consent={processingAuthorization}
          ready={session.ready} onDirty={setDirtySections} reviewDisabled={!session.ready || session.busy || !guide.schema} onReviewJob={reviewJob} showDebug={false} />}
        tools={!mobile && <>
          <InteractionHistory interactions={session.interactions} showDebug={false} />
          <button className="guide-clear" type="button" onClick={clearAssessment}>Clear encounter</button>
          <p>AI only structures documented findings. After your explicit review, the deterministic engine produces classifications and management guidance.</p>
          {assessmentAction}
        </>}
      />

      <ReportPanel text={reportDraft.text} ready={session.ready} voice={voice}
        onChange={(text) => setReportDraft((previous) => ({ text, context: previous.context ?? (session.ready ? { ...session.snapshot(), question: undefined } : undefined) }))}
        onClear={() => setReportDraft({ text: "" })}
        onInterpret={() => {
          if (session.ready && voice.addText("full-note", reportDraft.text, processingAuthorization.understanding,
            reportDraft.context ?? { ...session.snapshot(), question: undefined })) setReportDraft({ text: "" });
        }}
        review={renderSectionReview("full-note")}
        sections={checklist.sections.filter((section) => reportChanges
          .some((row) => row.field === "patient_facts.age_months" ? section.id === "danger" : guide.schema?.fields[row.field]?.assessments.includes(section.id)))}
        onReviewSection={openAssessment} onReviewJob={reviewJob} reviewDisabled={!session.ready || session.busy || !guide.schema} />

      <section className="output-panel" aria-label="Clinical result">
        <header className="pane-header result-pane-header">
          <div><p className="panel-index">Clinical result</p><h1>Classification and management</h1></div>
          <span className="deterministic-label"><ShieldCheck aria-hidden="true" size={14} /> Deterministic</span>
        </header>
        <div className="result-scroll">
          {(finalReady || requestedIncomplete) && result ? <ResultPanel result={result} showDebug={false} />
          : !meaningful && !assessmentRequested ? <section className="compact-empty-result">
            <ClipboardCheck aria-hidden="true" size={27} /><h2>Ready when you are</h2>
            <p>Follow the assessment guide. Record findings beside each section, then review what was captured.</p>
            <p>Clinical results appear here after findings are accepted.</p>
          </section> :
            <section className="quiet-result" aria-live="polite">
              {immediateActions.length > 0 && <section className="immediate-management" aria-label="Immediate management">
                <h2>Urgent findings confirmed</h2>
                <p>Based on confirmed findings. Do not delay referral.</p>
                <h3>Immediate management</h3>
                <ul>{immediateActions.map((action, index) => <li key={index}>{action}</li>)}</ul>
              </section>}
              <h2>{assessmentRequested && session.busy ? "Checking assessment..." : assessmentRequested && session.error ? "Could not check the assessment"
                : progressBlocked ? "Review evidence issues" : interrupted ? "Acknowledge interrupted captures before final plan"
                : requestNeedsReview ? "Review findings before generating recommendations"
                : result?.is_complete && hasDirty ? "Process or discard unprocessed edits before final plan" : result?.is_complete && pendingJobs.length
                ? "Review captured findings before final plan" : immediateActions.length ? "Assessment incomplete" : "Assessment in progress"}</h2>
              <p>{assessmentRequested && session.busy ? "Checking your confirmed findings for IMCI recommendations and missing information."
                : assessmentRequested && session.error ? "The assessment check failed. Your confirmed findings have not changed. Try again when the service is available."
                : progressBlocked ? "Resolve the blockers shown in the assessment sections. Final synthesis is withheld."
                : interrupted ? "Review the interruption notice above. Acknowledgement does not accept or recover interrupted findings."
                : requestNeedsReview ? "Recordings and edited answers must be confirmed or discarded first. Only confirmed findings are used."
                  : result?.is_complete && hasDirty ? "Typed findings still need processing or clearing in the assessment sections."
                 : result?.is_complete && pendingJobs.length ? "The accepted assessment is complete. New captures still need review or discard."
                  : immediateActions.length ? "Final classifications and the complete management plan remain pending until the required findings are confirmed. Immediate care must not wait for the remaining assessment."
                   : "Continue with the next observations in each assessment section. Only accepted findings contribute to the result."}</p>
              {immediateActions.length > 0 && (pendingJobs.length > 0 || hasDirty) && <p>New findings are awaiting review. They have not changed the guidance above.</p>}
              {assessmentRequested && session.error && <button type="button" className="assessment-review-link" disabled={session.busy}
                onClick={() => void generateRecommendations()}>Retry assessment</button>}
              {assessmentRequested && !session.busy && (requestNeedsReview || progressBlocked) && <div className="assessment-review-links">
                {[...new Set([...(hasReportDraft ? ["full-note" as const] : []), ...dirtyAssessments, ...pendingJobs.map((job) => job.assessment),
                  ...assessmentIds.filter((id) => session.evaluation?.assessments[id].blockers.length)])].map((id) => <button type="button"
                    className="assessment-review-link" key={id} onClick={() => {
                      const job = pendingJobs.find((item) => item.assessment === id);
                      if (job) reviewJob(job.id);
                      else if (id === "full-note") openReport();
                      else openAssessment(id, dirtySections[id] ? "findings" : "guidance");
                    }}>Review {id === "full-note" ? "text report" : checklist.sections.find((section) => section.id === id)?.label}</button>)}
              </div>}
            </section>}
        </div>
      </section>
    </main>

    <MobileDock view={mobileView} sections={checklist.sections} voice={voice} language={language}
      onLanguageChange={setLanguage} ready={session.ready}
      onNavigate={setMobileView} urgent={urgent} pendingCount={pendingJobs.length}
      confirmation={dangerIntro ? renderSectionReview("danger", "intro") : undefined}
      onSpeak={() => {
        if (!mobileView.assessment || !language || !canProcessSpeech || !session.ready) return;
        if (dangerIntro) voice.startRecording("danger", language, processingAuthorization, { ...session.snapshot(), question: undefined });
        else voice.startRecording(mobileView.assessment, language, processingAuthorization);
      }} />

    <footer className="site-footer">
      <p><strong>Research prototype.</strong> Not a production medical device or authorization for autonomous clinical use.</p>
      <p>Unchecked findings remain unknown; they are never inferred absent.</p>
    </footer>
  </div>;
}
