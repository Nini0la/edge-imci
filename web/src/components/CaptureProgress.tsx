import { AlertCircle, ClipboardCheck, LoaderCircle } from "lucide-react";
import type { ChecklistSection } from "../lib/checklist";
import type { CaptureJob } from "../lib/useVoiceCapture";

const messages: Partial<Record<CaptureJob["status"], string>> = {
  queued: "Waiting to process your findings",
  transcribing: "Turning your recording into text",
  extracting: "Adding your findings to the assessment",
  preparing_review: "Getting your findings ready for review",
  captured: "Ready for your review",
  review: "Ready for your review",
  applying: "Confirming your findings",
  failed: "Could not process your findings",
};

export function CaptureProgress({ jobs, sections, onReview }: {
  jobs: CaptureJob[];
  sections: ChecklistSection[];
  onReview: (id: string) => void;
}) {
  const pending = jobs.filter((job) => messages[job.status] && job.originalCandidate?.extraction_mode !== "worker-review");
  // Keep the live region mounted so new work and stage changes are announced.
  return <section className="capture-progress" aria-label="Recording progress" aria-live="polite" aria-atomic="false">
    {pending.map((job) => {
      const busy = ["queued", "transcribing", "extracting", "preparing_review", "applying"].includes(job.status);
      const failed = job.status === "failed" || (!busy && Boolean(job.error));
      const Icon = busy ? LoaderCircle : failed ? AlertCircle : ClipboardCheck;
      return <div className="capture-progress__item" key={job.id} data-stage={job.status} data-busy={busy} data-attention={failed}>
        <Icon className={busy ? "capture-progress__spinner" : undefined} size={18} aria-hidden="true" />
        <div className="capture-progress__text">
          <strong>{failed ? "Your findings need attention" : messages[job.status]}</strong>
          <span>{job.assessment === "full-note" ? "Full assessment report" : sections.find((section) => section.id === job.assessment)?.label ?? "Assessment"}
            {busy ? " / Please wait" : failed ? " / Open to retry or review" : " / Check the answers before confirming"}</span>
        </div>
        {!busy && <button type="button" onClick={() => onReview(job.id)}>{job.status === "failed" ? job.assessment === "full-note" ? "View report" : "View recording" : "Review"}</button>}
      </div>;
    })}
  </section>;
}
