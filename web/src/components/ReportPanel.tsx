import type { ReactNode } from "react";
import { FilePenLine } from "lucide-react";
import type { ChecklistSection } from "../lib/checklist";
import type { useVoiceCapture } from "../lib/useVoiceCapture";
import type { AssessmentId } from "../types";
import { CaptureJobCard } from "./AssessmentCapture";

export function ReportPanel({ text, onChange, onInterpret, onClear, ready, voice, review, sections, onReviewSection, onReviewJob, reviewDisabled }: {
  text: string;
  onChange: (text: string) => void;
  onInterpret: () => void;
  onClear: () => void;
  ready: boolean;
  voice: ReturnType<typeof useVoiceCapture>;
  review: ReactNode;
  sections: ChecklistSection[];
  onReviewSection: (assessment: AssessmentId) => void;
  onReviewJob: (id: string) => void;
  reviewDisabled: boolean;
}) {
  const reports = voice.jobs.filter((job) => job.assessment === "full-note" && job.status !== "discarded");
  return <section className="report-panel" aria-label="Text assessment report">
    <header className="pane-header">
      <p className="panel-index">Text report</p><h1 id="report-heading" tabIndex={-1}>Write assessment findings</h1>
      <p>Type or paste findings from one or several assessments. You can also tap answers directly in the assessment guide.</p>
    </header>
    <div className="report-body">
      <label htmlFor="assessment-report">Assessment findings</label>
      <textarea id="assessment-report" value={text} maxLength={8000} rows={10}
        placeholder="Describe your assessment findings. Leave unassessed observations out."
        onChange={(event) => onChange(event.target.value)} aria-describedby="report-help" />
       <p id="report-help">Interpretation proposes answers on the guide. Check or correct them, then confirm. Existing confirmed findings are kept unless you explicitly change them. Do not include patient names in submitted text.</p>
      <div className="report-actions">
        <button type="button" className="interpret-report" disabled={!ready || !text.trim()} onClick={onInterpret}>
          <FilePenLine size={18} aria-hidden="true" />Interpret text
        </button>
        {text && <button type="button" className="clear-report" onClick={onClear}>Clear text</button>}
      </div>
      {!ready && <p role="status">Waiting for the assessment to be ready.</p>}
      {sections.length > 0 && <div className="report-review-sections">
        <h2>Review findings in the guide</h2>
        <div className="assessment-review-links">{sections.map((section) => <button type="button" className="assessment-review-link"
          key={section.id} onClick={() => onReviewSection(section.id)}>{section.label}</button>)}</div>
      </div>}
      {review}
      <div className="report-jobs">{reports.map((job) => <CaptureJobCard key={job.id} job={job} voice={voice}
        reviewDisabled={reviewDisabled} onReviewJob={onReviewJob} showDebug={false} />)}</div>
    </div>
  </section>;
}
