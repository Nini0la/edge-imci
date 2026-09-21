import { useState, type ReactNode } from "react";
import type { MobileView } from "./MobileWorkspace";
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
  mobileView?: MobileView;
  mobileHome?: ReactNode;
  mobileFocus?: ReactNode;
  renderField?: (assessment: AssessmentId, field: string, labels?: { yes: string; no: string }) => ReactNode;
  renderSectionReview?: (assessment: AssessmentId) => ReactNode;
  workingEncounter?: Record<string, unknown>;
  pendingFieldPaths?: string[];
  requiredFieldPaths?: string[];
  ageReview?: ReactNode;
  showAge?: boolean;
}

const methodOrder: AssessmentMethod[] = ["ASK", "LOOK / LISTEN / FEEL", "MEASURE", "IF INDICATED"];

function stateLabel(state: ChecklistState): string {
  if (state === "urgent") return "Urgent";
  if (state === "unknown") return "Not documented";
  return "Recorded";
}

export function AssessmentChecklist({
  encounter, result, progress, pendingAssessments = [], captureStatuses, guideStatus, tools,
  renderCapture, mobileView, mobileHome, mobileFocus, renderField, renderSectionReview,
  workingEncounter, pendingFieldPaths, requiredFieldPaths, ageReview, showAge = true,
}: AssessmentChecklistProps) {
  const accepted = buildChecklist(encounter, result);
  const acceptedFields = renderField ? buildChecklist(encounter, result, { interactive: true }) : accepted;
  const acceptedItems = new Map(acceptedFields.sections.flatMap((section) => section.items.map((item) => [item.id, item] as const)));
  const checklist = buildChecklist(workingEncounter ?? encounter, result, {
    interactive: !!renderField,
    pendingFields: [
      ...(pendingFieldPaths ?? []),
      // Retain accepted observations even when a proposal clears or closes their branch.
      ...Array.from(acceptedItems.values()).filter((item) => item.state !== "unknown").map((item) => item.id),
    ],
    requiredFields: requiredFieldPaths,
  });
  const [desktopOpen, setDesktopOpen] = useState<Partial<Record<AssessmentId, boolean>>>({ danger: true });

  return (
    <aside className="panel checklist-panel" aria-label="IMCI assessment guide">
      <header className="checklist-header">
        <span className="eyebrow">WHO IMCI procedure</span>
        <h2>Assessment guide</h2>
        <p>Follow each prompt while assessing the child. Capture findings beside the procedure, then explicitly review and apply them.</p>
      </header>

      {guideStatus}

       {showAge && <div className="assessment-scope">
        <span className="assessment-scope__label">First confirm</span>
        <span className="assessment-scope__instruction">{checklist.age.instruction}</span>
        {renderField ? renderField("danger", "patient_facts.age_months") : (
          <span className={`assessment-value assessment-value--${accepted.age.state}`}>
            {accepted.age.value}
          </span>
        )}
        {ageReview}
       </div>}

      <div className="mobile-only mobile-home">{mobileHome}</div>

      <div className="mobile-only mobile-focus-header">{mobileFocus}</div>

      <div className="assessment-sections">
        {checklist.sections.map((section, sectionIndex) => {
          const id = section.id as AssessmentId;
           const acceptedBadge = assessmentBadge(progress?.[id]);
           const badge = pendingAssessments.includes(id) && acceptedBadge.kind !== "urgent"
             ? { label: "Awaiting confirmation", kind: "incomplete" } : acceptedBadge;
          return (
          <details
            className={`assessment-section assessment-section--${accepted.sections[sectionIndex].state}`}
             key={section.id}
             data-assessment={id}
             open={mobileView ? mobileView.screen === "assessment" && mobileView.assessment === id : desktopOpen[id] ?? false}
             onToggle={(event) => {
               if (!mobileView) {
                 const open = event.currentTarget.open;
                 setDesktopOpen((previous) => previous[id] === open ? previous : { ...previous, [id]: open });
               }
             }}
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
                  <strong>{accepted.sections[sectionIndex].inactive ? "No further checks triggered" : "No further checks if this answer is confirmed"}</strong>
                  <span>{accepted.sections[sectionIndex].inactive ? "The entry question was documented as absent." : "The No answer is pending confirmation. Retained findings still need review."}</span>
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
                      {items.map((item) => {
                        const annotation = acceptedItems.get(item.id);
                        return (
                        <li className={`assessment-item assessment-item--${annotation?.state ?? "unknown"}`} key={item.id}>
                          <div className="assessment-item__instruction">
                            {id === "danger" && <span className="danger-compact-label">{item.label}</span>}
                            <span className="assessment-full-instruction">{item.instruction}</span>
                            {item.conditional && (
                              <span className="assessment-item__conditional">Conditional if yes</span>
                            )}
                          </div>
                          {item.note && <div className="assessment-item__note">{item.note}</div>}
                          <div className="assessment-item__observation">
                            {renderField ? (item.booleanLabels ? renderField(id, item.id, item.booleanLabels) : renderField(id, item.id)) : (
                              <>
                                <span className="assessment-item__dot" aria-hidden="true" />
                                <span>{stateLabel(annotation?.state ?? "unknown")}</span>
                                <strong>{annotation?.value ?? "Unknown"}</strong>
                              </>
                            )}
                          </div>
                        </li>
                        );
                      })}
                    </ol>
                  </section>
                );
              })}

              <div className="assessment-source">WHO IMCI Chart Booklet, page {section.sourcePage}</div>
              {renderSectionReview?.(id)}
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
