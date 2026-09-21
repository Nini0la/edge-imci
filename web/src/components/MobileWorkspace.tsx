import { ArrowLeft, ChevronRight, ClipboardList, FileCheck2, FilePenLine } from "lucide-react";
import type { ReactNode } from "react";
import { assessmentBadge } from "../lib/assessment";
import type { buildChecklist, ChecklistSection } from "../lib/checklist";
import type { CaptureJob } from "../lib/useVoiceCapture";
import type { AssessmentId, AssessmentProgress } from "../types";

export interface MobileView {
  screen: "list" | "assessment" | "report" | "results";
  assessment: AssessmentId | null;
  tab: "guidance" | "findings";
  intro?: boolean;
}

type Navigate = (view: MobileView) => void;
const homeView: MobileView = { screen: "list", assessment: null, tab: "guidance" };
function isIntro(view: MobileView) {
  return view.intro && view.screen === "assessment" && view.assessment === "danger" && view.tab === "guidance";
}

export function MobileHeader({ view, sections, onNavigate, urgent = false }: {
  view: MobileView;
  sections: ChecklistSection[];
  onNavigate: Navigate;
  urgent?: boolean;
}) {
  const intro = isIntro(view);
  const title = view.screen === "assessment"
    ? sections.find((section) => section.id === view.assessment)?.label ?? "Assessment"
    : view.screen === "results" ? "Clinical results" : view.screen === "report" ? "Text report" : "Assessment list";
  return <header className="mobile-only mobile-workspace-header" data-mobile-intro={intro || undefined}>
    <div className="mobile-workspace-header__row">
      {view.screen !== "list" && !intro && <button type="button" className="mobile-back" aria-label="Back to assessments"
        onClick={() => onNavigate(homeView)}><ArrowLeft size={20} aria-hidden="true" /></button>}
      <h2 id="mobile-view-heading" tabIndex={-1}>{title}</h2>
      {urgent && view.screen !== "results" && <button type="button" className="mobile-urgent-results" aria-label="View urgent guidance"
        onClick={() => onNavigate({ ...view, screen: "results" })}>Urgent results</button>}
    </div>
  </header>;
}

export function MobileAssessmentHome({ checklist, progress, captureStatuses, pendingAssessments, onNavigate, tools, assessmentAction }: {
  checklist: ReturnType<typeof buildChecklist>;
  progress: Partial<Record<AssessmentId, AssessmentProgress>> | undefined;
  captureStatuses: Partial<Record<AssessmentId, string>>;
  pendingAssessments: AssessmentId[];
  onNavigate: Navigate;
  tools?: ReactNode;
  assessmentAction: ReactNode;
}) {
  const complete = checklist.sections.filter((section) => progress?.[section.id as AssessmentId]?.status === "COMPLETE").length;
  return <div className="mobile-only mobile-assessment-home">
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
              {captureStatuses[id] && !["Captured", "Reviewed"].includes(captureStatuses[id]!) && <span className="mobile-capture-status">{captureStatuses[id]}</span>}
            </span>
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        </li>;
      })}
    </ol>
    {tools}
    {assessmentAction}
  </div>;
}

export function MobileAssessmentTabs({ view, section, progress, urgent, jobs, onNavigate }: {
  view: MobileView;
  section: ChecklistSection | undefined;
  progress: AssessmentProgress | undefined;
  urgent: boolean;
  jobs: CaptureJob[];
  onNavigate: Navigate;
}) {
  if (view.screen !== "assessment" || !section || section.id !== view.assessment) return null;
  if (isIntro(view)) return null;
  const selectedJobs = jobs.filter((job) => job.assessment === section.id);
  const pending = selectedJobs.filter((job) => job.status !== "accepted" && job.status !== "discarded").length;
  return <div className="mobile-only mobile-assessment-focus">
    <div className="mobile-assessment-tabs" role="group" aria-label={`${section.label} view`}>
      <button type="button" aria-pressed={view.tab === "guidance"}
        onClick={() => onNavigate({ ...view, tab: "guidance" })}>Assessment</button>
      <button type="button" aria-pressed={view.tab === "findings"}
        onClick={() => onNavigate({ ...view, tab: "findings" })}>Reports
        {pending > 0 && <span className="mobile-count" aria-label={`${pending} pending reports`}>{pending}</span>}
      </button>
    </div>
    {view.tab === "guidance" && <div className="mobile-guidance-context">
      {!urgent && progress?.decision === "ASK" && progress.question && <div className="mobile-next-observation">
        <strong>Next observation</strong><p>{progress.question.text}</p>
      </div>}
      {urgent && <p className="capture-warning">Ordinary questions are paused. Prioritize urgent actions. You may still add findings.</p>}
      {progress?.blockers.map((blocker, index) => <p className="capture-warning" key={index}>{blocker}</p>)}
    </div>}
  </div>;
}

export function MobileDock({ view, onNavigate, confirmation }: {
  view: MobileView;
  onNavigate: Navigate;
  confirmation?: ReactNode;
}) {
  const intro = isIntro(view);
  return <footer className="mobile-only mobile-dock" data-mobile-intro={intro || undefined} aria-label="Workspace navigation">
    {intro ? <div className="mobile-intro-actions">
      {confirmation}
      <button type="button" className="mobile-write-report" onClick={() => onNavigate({ ...homeView, screen: "report" })}>Write text</button>
      <button type="button" className="mobile-continue" onClick={() => onNavigate(homeView)}>
        Continue<ChevronRight size={18} aria-hidden="true" />
      </button>
    </div> : <nav className="mobile-dock-nav" aria-label="Mobile workspace">
      <button type="button" aria-current={view.screen === "list" || view.screen === "assessment" ? "page" : undefined}
        onClick={() => onNavigate(homeView)}><ClipboardList size={19} aria-hidden="true" /><span>Assessment</span></button>
      <button type="button" aria-current={view.screen === "report" ? "page" : undefined}
        onClick={() => onNavigate({ ...homeView, screen: "report" })}><FilePenLine size={19} aria-hidden="true" /><span>Text report</span></button>
      <button type="button" aria-current={view.screen === "results" ? "page" : undefined}
        onClick={() => onNavigate({ ...view, screen: "results" })}><FileCheck2 size={19} aria-hidden="true" /><span>Results</span></button>
    </nav>}
  </footer>;
}
