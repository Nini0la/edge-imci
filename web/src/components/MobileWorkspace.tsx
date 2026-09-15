import { ArrowLeft, ChevronRight, ClipboardList, FileCheck2, Mic, Settings2, Square } from "lucide-react";
import type { ReactNode } from "react";
import { assessmentBadge } from "../lib/assessment";
import type { buildChecklist, ChecklistSection } from "../lib/checklist";
import type { CaptureJob, useVoiceCapture } from "../lib/useVoiceCapture";
import type { ASRLanguage, AssessmentId, AssessmentProgress } from "../types";

export interface MobileView {
  screen: "list" | "assessment" | "results" | "settings";
  assessment: AssessmentId | null;
  tab: "guidance" | "findings";
}

type Navigate = (view: MobileView) => void;
const homeView: MobileView = { screen: "list", assessment: null, tab: "guidance" };
const languageLabels: Record<ASRLanguage, string> = {
  en: "English", pcm: "Nigerian Pidgin-English", yo: "Yoruba-English", ig: "Igbo-English", ha: "Hausa-English",
};
const researchDisclaimer = "Research prototype. Not a production medical device or authorization for autonomous clinical use.";

export function MobileHeader({ view, sections, onNavigate }: {
  view: MobileView;
  sections: ChecklistSection[];
  onNavigate: Navigate;
}) {
  const title = view.screen === "assessment"
    ? sections.find((section) => section.id === view.assessment)?.label ?? "Assessment"
    : view.screen === "settings" ? "Recording setup"
      : view.screen === "results" ? "Clinical results" : "Assessment list";
  return <header className="mobile-only mobile-workspace-header">
    <div className="mobile-workspace-header__row">
      {view.screen !== "list" && <button type="button" className="mobile-back" aria-label="Back to assessments"
        onClick={() => onNavigate(homeView)}><ArrowLeft size={20} aria-hidden="true" /></button>}
      <h2 id="mobile-view-heading" tabIndex={-1}>{title}</h2>
    </div>
  </header>;
}

export function MobileAssessmentHome({ checklist, progress, captureStatuses, pendingAssessments, onNavigate, setupReady, ageControl }: {
  checklist: ReturnType<typeof buildChecklist>;
  progress: Partial<Record<AssessmentId, AssessmentProgress>> | undefined;
  captureStatuses: Partial<Record<AssessmentId, string>>;
  pendingAssessments: AssessmentId[];
  onNavigate: Navigate;
  setupReady: boolean;
  ageControl?: ReactNode;
}) {
  const complete = checklist.sections.filter((section) => progress?.[section.id as AssessmentId]?.status === "COMPLETE").length;
  return <div className="mobile-only mobile-assessment-home">
    <p className="mobile-workflow"><strong>Assess. Speak. Review.</strong> Record findings. Review before applying.</p>
    <div className="mobile-age">
      {ageControl ?? <><span aria-label={checklist.age.instruction}><strong>Age (completed months)</strong></span>
        <strong>{checklist.age.value}</strong></>}
    </div>
    <div className="mobile-list-heading">
      <h3>Assessments</h3><span>{complete} of {checklist.sections.length} complete</span>
    </div>
    <ol className="mobile-assessment-list">
      {checklist.sections.map((section, index) => {
        const id = section.id as AssessmentId;
        const pending = pendingAssessments.includes(id);
        const acceptedBadge = assessmentBadge(progress?.[id]);
        const badge = pending && acceptedBadge.kind !== "urgent" ? { label: "Awaiting confirmation", kind: "incomplete" } : acceptedBadge;
        return <li key={id}>
          <button type="button" className="mobile-assessment-row" data-pending={pending || undefined}
            onClick={() => onNavigate({ screen: "assessment", assessment: id, tab: "guidance" })}>
            <span className="mobile-assessment-row__number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
            <span className="mobile-assessment-row__body">
              <strong>{section.label}</strong>
              <span className={`mobile-assessment-badge mobile-assessment-badge--${badge.kind}`}
                aria-label={`Assessment status: ${badge.label}`}>{badge.label}</span>
              {captureStatuses[id] && <span className="mobile-capture-status">Capture: {captureStatuses[id]}
                {captureStatuses[id] === "Captured" && " / awaiting review"}</span>}
              {pending && <span className="mobile-pending-note">Pending findings to address</span>}
            </span>
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        </li>;
      })}
    </ol>
    {!setupReady && <div className="mobile-setup-prompt">
      <p>Before recording, choose a language and agree to both processing permissions.</p>
      <button type="button" onClick={() => onNavigate({ ...homeView, screen: "settings" })}>
        Configure recording <ChevronRight size={18} aria-hidden="true" />
      </button>
    </div>}
    <p className="mobile-home-note">Recording is not completion. Only reviewed, applied findings contribute to the assessment.</p>
    <p className="mobile-research-note">{researchDisclaimer}</p>
  </div>;
}

export function MobileAssessmentTabs({ view, section, progress, urgent, jobs, onNavigate, ageControl }: {
  view: MobileView;
  section: ChecklistSection | undefined;
  progress: AssessmentProgress | undefined;
  urgent: boolean;
  jobs: CaptureJob[];
  onNavigate: Navigate;
  ageControl?: ReactNode;
}) {
  if (view.screen !== "assessment" || !section || section.id !== view.assessment) return null;
  const pending = jobs.filter((job) => job.assessment === section.id && job.status !== "accepted" && job.status !== "discarded").length;
  return <div className="mobile-only mobile-assessment-focus">
    <div className="mobile-assessment-tabs" role="group" aria-label={`${section.label} view`}>
      <button type="button" aria-pressed={view.tab === "guidance"}
        onClick={() => onNavigate({ ...view, tab: "guidance" })}>Assessment</button>
      <button type="button" aria-pressed={view.tab === "findings"}
        onClick={() => onNavigate({ ...view, tab: "findings" })}>Recordings
        {pending > 0 && <span className="mobile-count" aria-label={`${pending} pending captures`}>{pending}</span>}
      </button>
    </div>
    {view.tab === "guidance" && <div className="mobile-guidance-context">
      {ageControl && <div className="mobile-age">{ageControl}</div>}
      {!urgent && progress?.decision === "ASK" && progress.question && <div className="mobile-next-observation">
        <strong>Next observation</strong><p>{progress.question.text}</p>
      </div>}
      {urgent && <p className="capture-warning">Ordinary questions are paused. Prioritize urgent actions. Further captures are your choice.</p>}
      {progress?.blockers.map((blocker, index) => <p className="capture-warning" key={index}>{blocker}</p>)}
    </div>}
  </div>;
}

export function MobileDock({ view, sections, voice, language, consent, ready, onNavigate, urgent, pendingCount }: {
  view: MobileView;
  sections: ChecklistSection[];
  voice: ReturnType<typeof useVoiceCapture>;
  language: ASRLanguage | "";
  consent: { audio: boolean; understanding: boolean };
  ready: boolean;
  onNavigate: Navigate;
  urgent: boolean;
  pendingCount: number;
}) {
  const active = voice.recordingId !== null || voice.audioState !== "idle";
  const owner = voice.jobs.find((job) => job.id === voice.recordingId);
  const ownerLabel = sections.find((section) => section.id === owner?.assessment)?.label ?? "Current capture";
  const selected = view.screen === "assessment" ? sections.find((section) => section.id === view.assessment) : undefined;
  const configured = Boolean(language && consent.audio && consent.understanding);
  const phase = voice.audioState === "permission" ? "Waiting for microphone permission"
    : voice.audioState === "stopping" ? "Finishing recording" : "Recording";
  return <footer className="mobile-only mobile-dock" data-capture-controls={active || Boolean(selected)} aria-label="Recording and workspace navigation">
    <div className="mobile-dock-status" role="status" aria-atomic="true">
      {urgent && <strong>Urgent guidance remains active. </strong>}
      {pendingCount > 0 ? `${pendingCount} pending capture${pendingCount === 1 ? "" : "s"} to address. Not yet accepted.`
        : "Only applied findings inform results."}
    </div>
    <div className="mobile-dock-recording">
      {active ? <>
        <p id="mobile-recording-context" className="mobile-recording-context" role="status">
          <strong>{phase}: {ownerLabel}</strong>
          <span>{owner?.language ? languageLabels[owner.language] : "Language unavailable"}</span>
        </p>
        <div className="mobile-dock-actions">
          <button type="button" className="mobile-record-button mobile-record-button--stop" aria-label="Stop recording"
            aria-describedby="mobile-recording-context" disabled={voice.audioState !== "recording"} onClick={voice.stop}>
            <Square size={20} aria-hidden="true" />Stop recording
          </button>
          <button type="button" className="mobile-cancel-button" aria-label="Cancel recording"
            aria-describedby="mobile-recording-context" onClick={voice.cancelRecording}>Cancel recording</button>
        </div>
      </> : selected ? <>
        <p id="mobile-recording-context" className="mobile-recording-context">
          <strong>Record for: {selected.label}</strong>
          <span>{!configured ? "Recording setup needed" : !ready ? "Waiting for encounter readiness"
            : `${language ? languageLabels[language] : ""} / 60 seconds maximum. Stop to process.`}</span>
        </p>
        {configured ? <button type="button" className="mobile-record-button" aria-label="Record findings"
          aria-describedby="mobile-recording-context capture-disclosure" disabled={!ready || !configured}
          onClick={() => {
            if (ready && configured && language && view.assessment) voice.startRecording(view.assessment, language, consent);
          }}><Mic size={22} aria-hidden="true" />Record findings</button>
          : <button type="button" className="mobile-record-button"
            onClick={() => onNavigate({ ...view, screen: "settings" })}><Settings2 size={20} aria-hidden="true" />Configure recording</button>}
      </> : null}
    </div>
    <nav className="mobile-dock-nav" aria-label="Mobile workspace">
      <button type="button" aria-label="Assessments" aria-current={view.screen === "list" || view.screen === "assessment" ? "page" : undefined}
        onClick={() => onNavigate(homeView)}><ClipboardList size={19} aria-hidden="true" /><span className="mobile-nav-label">Assessments</span><span className="mobile-nav-short" aria-hidden="true">List</span></button>
      <button type="button" aria-current={view.screen === "results" ? "page" : undefined}
        onClick={() => onNavigate({ ...view, screen: "results" })}><FileCheck2 size={19} aria-hidden="true" /><span>Results</span></button>
      <button type="button" aria-current={view.screen === "settings" ? "page" : undefined}
        onClick={() => onNavigate({ ...view, screen: "settings" })}><Settings2 size={19} aria-hidden="true" /><span>Setup</span></button>
    </nav>
  </footer>;
}
