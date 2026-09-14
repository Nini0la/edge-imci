import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AssessmentChecklist } from "./AssessmentChecklist";
import type { AssessmentProgress } from "../types";

describe("AssessmentChecklist", () => {
  it("never promotes locally documented sections to complete before server evaluation", () => {
    const html = renderToStaticMarkup(<AssessmentChecklist encounter={{ patient_facts: { has_cough_or_difficult_breathing: false } }} />);
    expect(html).not.toContain("Assessment status: Complete");
    expect(html.match(/Assessment status: Not started/g)).toHaveLength(5);
  });

  it("uses server status rather than local checklist completeness and marks candidates pending", () => {
    const complete: AssessmentProgress = { status: "COMPLETE", decision: "COMPLETE", question: null, blockers: [], missing_fields: [] };
    const props = { encounter: {}, progress: { danger: complete } };
    expect(renderToStaticMarkup(<AssessmentChecklist {...props} />)).toContain("Assessment status: Complete");
    const pending = renderToStaticMarkup(<AssessmentChecklist {...props} pendingAssessments={["danger"]} />);
    expect(pending).not.toContain("Assessment status: Complete");
    expect(pending).toContain("Assessment status: Needs review");
  });

  it("shows the documented entry answer when a negative answer ends a section", () => {
    const html = renderToStaticMarkup(
      <AssessmentChecklist
        encounter={{ patient_facts: { has_cough_or_difficult_breathing: false } }}
      />,
    );

    expect(html).toContain("No further checks triggered");
    expect(html).toContain("Ask whether the child has cough or difficult breathing.");
    expect(html).toContain("Recorded");
    expect(html).toContain("Absent");
  });

  it("shows conditional follow-ups when the entry answer is unknown", () => {
    const html = renderToStaticMarkup(
      <AssessmentChecklist
        encounter={{ patient_facts: { has_diarrhoea: null }, diarrhoea: null }}
      />,
    );

    expect(html).toContain("Ask whether the child has diarrhoea.");
    expect(html).toContain("If yes, ask for how long.");
    expect(html).toContain("Ask whether there is blood in the stool.");
    expect(html).toContain("Conditional if yes");
  });
});
