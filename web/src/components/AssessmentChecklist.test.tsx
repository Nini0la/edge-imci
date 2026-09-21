import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AssessmentChecklist } from "./AssessmentChecklist";
import { buildChecklist } from "../lib/checklist";
import type { AssessmentProgress } from "../types";

describe("AssessmentChecklist", () => {
  it("never promotes locally documented sections to complete before server evaluation", () => {
    const html = renderToStaticMarkup(<AssessmentChecklist encounter={{ patient_facts: { has_cough_or_difficult_breathing: false } }} />);
    expect(html).not.toContain("Assessment status: Complete");
    expect(html.match(/Assessment status: Not started/g)).toHaveLength(5);
  });

  it("keeps clinical server status separate from capture status", () => {
    const complete: AssessmentProgress = { status: "COMPLETE", decision: "COMPLETE", question: null, blockers: [], missing_fields: [] };
    const props = { encounter: {}, progress: { danger: complete } };
    expect(renderToStaticMarkup(<AssessmentChecklist {...props} />)).toContain("Assessment status: Complete");
    const pending = renderToStaticMarkup(<AssessmentChecklist {...props} pendingAssessments={["danger"]} captureStatuses={{ danger: "Captured" }} />);
    expect(pending).toContain("Assessment status: Awaiting confirmation");
    expect(pending).not.toContain("Assessment status: Complete");
    expect(pending).toContain("Captured / awaiting review");
    expect(pending).not.toContain("Assessment status: Needs review");
  });

  it.each([false, true])("badges only the urgent source path despite global urgent decisions, pending=%s", (pending) => {
    const urgent: AssessmentProgress = { status: "URGENT", decision: "URGENT", question: null, blockers: [], missing_fields: [] };
    const html = renderToStaticMarkup(<AssessmentChecklist
      progress={{ danger: urgent, respiratory: { ...urgent, status: "NOT_STARTED" }, diarrhoea: { ...urgent, status: "INCOMPLETE" },
        fever: { ...urgent, status: "COMPLETE" }, ear: { ...urgent, status: "COMPLETE" } }}
      pendingAssessments={pending ? ["danger", "ear"] : []} />);
    expect(Array.from(html.matchAll(/aria-label="Assessment status: ([^"]+)"/g), (match) => match[1])).toEqual([
      "Urgent", "Not started", "Needs info", "Complete", pending ? "Awaiting confirmation" : "Complete",
    ]);
    expect(html.match(/assessment-section__state--urgent/g)).toHaveLength(1);
  });

  it("places procedure and evidence side by side and never opens sections for completed background jobs", () => {
    const html = renderToStaticMarkup(<AssessmentChecklist encounter={{}} captureStatuses={{ ear: "Captured", fever: "Reviewed" }}
      renderCapture={(id) => <section>Evidence for {id}</section>} tools={<details><summary>Tools</summary></details>} />);
    expect(html.match(/class="assessment-section__body section-evidence-layout"/g)).toHaveLength(5);
    expect(html.match(/class="assessment-procedure"/g)).toHaveLength(5);
    expect(html.match(/class="assessment-evidence"/g)).toHaveLength(5);
    expect(html.match(/<details[^>]*open=""/g)).toHaveLength(1);
    expect(html).toMatch(/<footer class="checklist-footer">.*<summary>Tools/);
  });

  it("marks sections affected by another capture without inventing a clinical status", () => {
    const html = renderToStaticMarkup(<AssessmentChecklist pendingAssessments={["respiratory"]} />);
    expect(html).toContain("Related findings awaiting review");
    expect(html.match(/Assessment status: Not started/g)).toHaveLength(4);
    expect(html).toContain("Assessment status: Awaiting confirmation");
    const reviewed = renderToStaticMarkup(<AssessmentChecklist pendingAssessments={["ear"]} captureStatuses={{ ear: "Reviewed" }} />);
    expect(reviewed).toContain("Reviewed / related findings awaiting review");
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

  it("renders canonical field controls in existing observations and age scope", () => {
    const renderField = vi.fn((_assessment: string, path: string) => <button>{path}</button>);
    const html = renderToStaticMarkup(<AssessmentChecklist renderField={renderField} />);
    expect(renderField).toHaveBeenCalledWith("danger", "patient_facts.age_months");
    expect(renderField).toHaveBeenCalledWith("respiratory", "patient_facts.has_cough_or_difficult_breathing");
    expect(renderField).not.toHaveBeenCalledWith("respiratory", "respiratory.respiratory_rate");
    expect(html).toContain('<div class="assessment-item__observation"><button>patient_facts.has_cough_or_difficult_breathing</button></div>');
    expect(html).not.toContain("assessment-item__dot");
    expect(html).not.toContain("<form");
    expect(renderField.mock.calls.filter(([, path]) => path === "patient_facts.age_months")).toHaveLength(1);
    expect(html).toMatch(/<div class="assessment-scope">.*<button>patient_facts.age_months<\/button><\/div>/);
  });

  it.each([false, true])("renders age only when explicitly requested, showAge=%s", (showAge) => {
    const encounter = { patient_facts: { age_months: 24 } };
    const renderField = vi.fn((_assessment: string, path: string) => <button>{path}</button>);
    const html = renderToStaticMarkup(<AssessmentChecklist encounter={encounter}
      workingEncounter={{ patient_facts: { age_months: 36 } }} pendingFieldPaths={["patient_facts.age_months"]}
      showAge={showAge} renderField={renderField} ageReview={<button>Confirm age</button>} />);
    expect(html.includes('class="assessment-scope"')).toBe(showAge);
    expect(html.includes("Confirm age")).toBe(showAge);
    expect(renderField.mock.calls.filter(([, path]) => path === "patient_facts.age_months")).toHaveLength(showAge ? 1 : 0);
    expect(renderField).toHaveBeenCalledWith("danger", "danger_signs.convulsing_now");
    expect(html.match(/class="assessment-section__body/g)).toHaveLength(5);
    expect(encounter.patient_facts.age_months).toBe(24);
  });

  it.each([false, true])("renders five canonical short danger labels beside full instructions, retaining read-only annotations: interactive=%s", (interactive) => {
    const encounter = { danger_signs: { unable_to_drink_or_breastfeed: false, convulsing_now: true } };
    const original = structuredClone(encounter);
    const renderField = vi.fn((_assessment: string, path: string) => <button>{path}</button>);
    const html = renderToStaticMarkup(<AssessmentChecklist encounter={encounter} renderField={interactive ? renderField : undefined}
      mobileView={{ screen: "assessment", assessment: "danger", tab: "guidance", intro: true }} />);
    const items = buildChecklist(encounter).sections[0].items;
    expect(items).toHaveLength(5);
    expect(html.match(/class="danger-compact-label"/g)).toHaveLength(5);
    for (const item of items) expect(html).toContain(`<span class="danger-compact-label">${item.label}</span><span class="assessment-full-instruction">${item.instruction}</span>`);
    if (interactive) {
      expect(renderField).toHaveBeenCalledWith("danger", "danger_signs.unable_to_drink_or_breastfeed", { yes: "Unable", no: "Able" });
      expect(renderField.mock.calls.filter(([assessment, path]) => assessment === "danger" && path.startsWith("danger_signs."))).toHaveLength(5);
      expect(html).not.toContain("assessment-item__dot");
    } else {
      expect(html).toContain("assessment-item__dot");
      expect(html).toContain("<strong>Able</strong>");
      expect(html).toContain("<strong>Present</strong>");
      expect(html).toContain("<strong>Unknown</strong>");
      expect(html).not.toMatch(/<input|<button|role="radiogroup"/);
    }
    expect(encounter).toEqual(original);
  });

  it("previews positive rows without changing accepted server status", () => {
    const complete: AssessmentProgress = { status: "COMPLETE", decision: "COMPLETE", question: null, blockers: [], missing_fields: [] };
    const html = renderToStaticMarkup(
      <AssessmentChecklist
        encounter={{ patient_facts: { has_cough_or_difficult_breathing: false } }}
        workingEncounter={{ patient_facts: { has_cough_or_difficult_breathing: true } }}
        progress={{ respiratory: complete }}
        renderField={(_assessment, path) => <button>{path}</button>}
      />,
    );
    const respiratory = html.split('class="assessment-section__number">02</span>')[1].split("</details>")[0];
    expect(respiratory).toContain("respiratory.respiratory_rate");
    expect(respiratory).toContain('aria-label="Assessment status: Complete"');
    expect(respiratory).not.toContain("No further checks triggered");
  });

  it("retains accepted children cleared in a negative preview and forwards pending paths", () => {
    const renderField = vi.fn((_assessment: string, path: string) => <button>{path}</button>);
    renderToStaticMarkup(
      <AssessmentChecklist
        encounter={{ patient_facts: { has_ear_problem: true }, ear: { ear_pain: false } }}
        workingEncounter={{ patient_facts: { has_ear_problem: false }, ear: { ear_pain: null } }}
        pendingFieldPaths={["ear.pus_draining_from_ear"]}
        requiredFieldPaths={["ear.ear_discharge_duration_days"]}
        renderField={renderField}
      />,
    );
    expect(renderField).toHaveBeenCalledWith("ear", "ear.ear_pain");
    expect(renderField).toHaveBeenCalledWith("ear", "ear.pus_draining_from_ear");
    expect(renderField).not.toHaveBeenCalledWith("ear", "ear.ear_discharge_duration_days");
  });

  it("forwards required paths and renders section review inside the existing procedure", () => {
    const renderField = vi.fn((_assessment: string, path: string) => <button>{path}</button>);
    const renderSectionReview = vi.fn((assessment: string) => <footer>Review {assessment}</footer>);
    const html = renderToStaticMarkup(
      <AssessmentChecklist
        workingEncounter={{ patient_facts: { has_cough_or_difficult_breathing: true } }}
        requiredFieldPaths={["respiratory.post_bronchodilator_child_calm"]}
        renderField={renderField}
        renderSectionReview={renderSectionReview}
        renderCapture={(assessment) => <section>Capture {assessment}</section>}
      />,
    );
    expect(renderField).toHaveBeenCalledWith("respiratory", "respiratory.post_bronchodilator_child_calm", { yes: "Calm", no: "Not calm" });
    expect(renderField).toHaveBeenCalledWith("danger", "danger_signs.unable_to_drink_or_breastfeed", { yes: "Unable", no: "Able" });
    expect(renderSectionReview).toHaveBeenCalledTimes(5);
    expect(html).toContain('page 2</div><footer>Review respiratory</footer></div><div class="assessment-evidence"><section>Capture respiratory</section></div>');
    expect(html.match(/class="assessment-section__body section-evidence-layout"/g)).toHaveLength(5);
    expect(html.match(/class="assessment-procedure"/g)).toHaveLength(5);
  });

  it("does not use working values for ordinary annotations", () => {
    const html = renderToStaticMarkup(
      <AssessmentChecklist
        encounter={{ patient_facts: { age_months: 18 }, danger_signs: { convulsing_now: false } }}
        workingEncounter={{ patient_facts: { age_months: 30 }, danger_signs: { convulsing_now: true } }}
      />,
    );
    expect(html).toContain("18 months");
    expect(html).not.toContain("30 months");
    expect(html).not.toContain("<strong>Present</strong>");
  });

  it("preserves mobile chrome, section opening, and capture parents with interactive fields", () => {
    const props = {
      renderField: (_assessment: string, path: string) => <button>{path}</button>,
      renderCapture: (assessment: string) => <section>Capture {assessment}</section>,
      renderSectionReview: (assessment: string) => <footer>Review {assessment}</footer>,
      mobileHome: <nav>Assessment home</nav>,
      mobileFocus: <nav>Assessment tabs</nav>,
      guideStatus: <p>Guide status</p>,
      tools: <button>Tools</button>,
      ageReview: <button>Review age</button>,
    };
    const desktop = renderToStaticMarkup(<AssessmentChecklist {...props} />);
    const mobile = renderToStaticMarkup(<AssessmentChecklist {...props} mobileView={{ screen: "assessment", assessment: "ear", tab: "findings" }} />);
    expect(desktop.match(/data-assessment="[^"]+" open=""/g)).toEqual(['data-assessment="danger" open=""']);
    expect(mobile.match(/data-assessment="[^"]+" open=""/g)).toEqual(['data-assessment="ear" open=""']);
    for (const html of [desktop, mobile]) {
      expect(html).toContain('<p>Guide status</p><div class="assessment-scope">');
      expect(html).toContain('<button>patient_facts.age_months</button><button>Review age</button></div><div class="mobile-only mobile-home"><nav>Assessment home</nav></div>');
      expect(html.match(/<button>patient_facts.age_months<\/button>/g)).toHaveLength(1);
      expect(html).toContain('<div class="mobile-only mobile-focus-header"><nav>Assessment tabs</nav></div><div class="assessment-sections">');
      expect(html.match(/class="assessment-evidence"/g)).toHaveLength(5);
      expect(html.match(/<footer>Review [^<]+<\/footer><\/div><div class="assessment-evidence">/g)).toHaveLength(5);
      expect(html).toContain('<button>Tools</button></footer></aside>');
    }
  });
});
