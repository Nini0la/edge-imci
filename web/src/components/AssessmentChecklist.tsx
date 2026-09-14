import type { ReactNode } from "react";
import type { AnalysisResult, AssessmentId, AssessmentProgress } from "../types";
import { assessmentBadge } from "../lib/assessment";
import {
  buildChecklist,
  type AssessmentMethod,
  type ChecklistState,
} from "../lib/checklist";

interface AssessmentChecklistProps {
  encounter?: Record<string, unknown>;
  result?: AnalysisResult | null;
  progress?: Partial<Record<AssessmentId, AssessmentProgress>>;
  pendingAssessments?: AssessmentId[];
  captureStatuses?: Partial<Record<AssessmentId, string>>;
  guideStatus?: ReactNode;
  tools?: ReactNode;
  renderCapture?: (id: AssessmentId) => ReactNode;
}

const methodOrder: AssessmentMethod[] = ["ASK", "LOOK / LISTEN / FEEL", "MEASURE", "IF INDICATED"];

function stateLabel(state: ChecklistState): string {
  if (state === "urgent") return "Urgent";
  if (state === "unknown") return "Not documented";
  return "Recorded";
}

export function AssessmentChecklist({ encounter, result, progress, pendingAssessments = [], captureStatuses, guideStatus, tools, renderCapture }: AssessmentChecklistProps) {
  const checklist = buildChecklist(encounter, result);

  return (
    <aside className="panel checklist-panel" aria-label="IMCI assessment guide">
      <header className="checklist-header">
        <span className="eyebrow">WHO IMCI procedure</span>
        <h2>Assessment guide</h2>
        <p>Follow each prompt while assessing the child. Capture findings beside the procedure, then explicitly review and apply them.</p>
      </header>

      {guideStatus}

      <div className="assessment-scope">
        <span className="assessment-scope__label">First confirm</span>
        <span className="assessment-scope__instruction">{checklist.age.instruction}</span>
        <span className={`assessment-value assessment-value--${checklist.age.state}`}>
          {checklist.age.value}
        </span>
      </div>

      <div className="assessment-sections">
        {checklist.sections.map((section, sectionIndex) => {
          const id = section.id as AssessmentId;
          const badge = assessmentBadge(progress?.[id]);
          return (
          <details
            className={`assessment-section assessment-section--${section.state}`}
            key={section.id}
            open={section.id === "danger"}
          >
            <summary>
              <span className="assessment-section__number">{String(sectionIndex + 1).padStart(2, "0")}</span>
              <span className="assessment-section__heading">
                <strong>{section.label}</strong>
                <span>{section.prompt}</span>
                {(captureStatuses?.[id] || pendingAssessments.includes(id)) && <span className="assessment-capture-status">
                  {captureStatuses?.[id] ?? "Related findings awaiting review"}
                  {captureStatuses?.[id] === "Captured" && " / awaiting review"}
                  {captureStatuses?.[id] === "Reviewed" && pendingAssessments.includes(id) && " / related findings awaiting review"}
                </span>}
              </span>
              <span
                className={`assessment-section__state assessment-section__state--${badge.kind}`}
                aria-label={`Assessment status: ${badge.label}`}
              >
                <span className="assessment-section__status-dot" aria-hidden="true" />
                {badge.label}
              </span>
            </summary>

            <div className="assessment-section__body section-evidence-layout">
              <div className="assessment-procedure">
              {section.inactive && (
                <div className="assessment-inactive">
                  <strong>No further checks triggered</strong>
                  <span>The entry question was documented as absent.</span>
                </div>
              )}

              {!section.inactive && (
                <>
                  {section.guidance.map((guide) => (
                    <div
                      className={`assessment-guidance assessment-guidance--${guide.emphasis ?? "default"}`}
                      key={guide.title}
                    >
                      <strong>{guide.title}</strong>
                      {guide.lines.map((line) => <span key={line}>{line}</span>)}
                    </div>
                  ))}
                </>
              )}

              {methodOrder.map((method) => {
                const items = section.items.filter((item) => item.method === method);
                if (items.length === 0) return null;
                return (
                  <section className="assessment-method" key={method}>
                    <h3>{method}</h3>
                    <ol>
                      {items.map((item) => (
                        <li className={`assessment-item assessment-item--${item.state}`} key={item.id}>
                          <div className="assessment-item__instruction">
                            {item.instruction}
                            {item.conditional && (
                              <span className="assessment-item__conditional">Conditional if yes</span>
                            )}
                          </div>
                          {item.note && <div className="assessment-item__note">{item.note}</div>}
                          <div className="assessment-item__observation">
                            <span className="assessment-item__dot" aria-hidden="true" />
                            <span>{stateLabel(item.state)}</span>
                            <strong>{item.value}</strong>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </section>
                );
              })}

              <div className="assessment-source">WHO IMCI Chart Booklet, page {section.sourcePage}</div>
              </div>
              {renderCapture && <div className="assessment-evidence">{renderCapture(id)}</div>}
            </div>
          </details>
          );
        })}
      </div>

      <footer className="checklist-footer">
        <strong>Unknown is not absent.</strong> Verify every required observation before evaluation.
        {tools}
      </footer>
    </aside>
  );
}
