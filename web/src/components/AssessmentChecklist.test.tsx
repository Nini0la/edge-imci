import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AssessmentChecklist } from "./AssessmentChecklist";

describe("AssessmentChecklist", () => {
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
