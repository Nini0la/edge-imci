import { Children, isValidElement, type ComponentProps, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { buildChecklist } from "../lib/checklist";
import type { CaptureJob } from "../lib/useVoiceCapture";
import type { AssessmentProgress } from "../types";
import { AssessmentChecklist } from "./AssessmentChecklist";
import { ClinicalFieldControl } from "./ClinicalFieldControl";
import { MobileAssessmentHome, MobileAssessmentTabs, MobileDock, MobileHeader, type MobileView } from "./MobileWorkspace";

const checklist = buildChecklist({ patient_facts: { age_months: 24 } });
const sections = checklist.sections;
const focus: MobileView = { screen: "assessment", assessment: "ear", tab: "guidance" };
const intro: MobileView = { screen: "assessment", assessment: "danger", tab: "guidance", intro: true };
const assessmentAction = <button type="button">Generate IMCI recommendations</button>;
const progress: AssessmentProgress = {
  status: "INCOMPLETE", decision: "ASK", missing_fields: ["ear.ear_pain"],
  question: { field: "ear.ear_pain", text: "Does the child have ear pain?" }, blockers: ["Confirm the reported observation."],
};

function job(status: CaptureJob["status"], overrides: Partial<CaptureJob> = {}): CaptureJob {
  return {
    id: "clip-1", assessment: "ear", language: "yo", status, originalEncounter: {}, originalRevision: 0,
    reviewVersion: 0, changedFields: [], question: { field: "ear.ear_discharge_reported", text: "Original captured question" },
    trace: { id: "clip-1", timestamp: "2026-09-15T12:00:00Z", assessment: "ear", status: "candidate", source: {} },
    ...overrides,
  };
}

function dockProps(overrides: Partial<ComponentProps<typeof MobileDock>> = {}): ComponentProps<typeof MobileDock> {
  return { view: intro, onNavigate: vi.fn(), ...overrides };
}

// These components are stateless: inspect their handlers without a second DOM library.
function elements<T extends "button" | "select">(node: ReactNode, tag: T): ReactElement<ComponentProps<T>>[] {
  return Children.toArray(node).flatMap((child) => {
    if (!isValidElement<{ children?: ReactNode }>(child)) return [];
    return child.type === tag ? [child as ReactElement<ComponentProps<T>>] : elements(child.props.children, tag);
  });
}
const buttons = (node: ReactNode) => elements(node, "button");

function click(button: ReactElement<ComponentProps<"button">> | undefined) {
  expect(button).toBeDefined();
  expect(button!.props.disabled).not.toBe(true);
  button!.props.onClick?.({} as Parameters<NonNullable<ComponentProps<"button">["onClick"]>>[0]);
}

describe("mobile assessment navigation", () => {
  it.each([
    ["list", "Assessment list"], ["assessment", "Ear problem"],
    ["results", "Clinical results"], ["report", "Text report"],
  ] as const)("labels the %s view without duplicating the brand", (screen, title) => {
    const html = renderToStaticMarkup(<MobileHeader view={{ ...focus, screen }} sections={sections} onNavigate={vi.fn()} />);
    expect(html).toContain(`id="mobile-view-heading" tabindex="-1">${title}</h2>`);
    expect(html).not.toContain("brand");
    expect(html.includes('aria-label="Back to assessments"')).toBe(screen !== "list");
    expect(html).not.toContain("Recording setup");
  });

  it("returns home explicitly from a focused assessment", () => {
    const onNavigate = vi.fn();
    click(buttons(MobileHeader({ view: focus, sections, onNavigate }))[0]);
    expect(onNavigate).toHaveBeenCalledWith({ screen: "list", assessment: null, tab: "guidance" });
  });

  it.each([intro, focus, { ...focus, tab: "findings" as const },
    { ...focus, screen: "list" as const }, { ...focus, screen: "results" as const }])(
    "offers only an urgent results link outside results on $screen/$tab", (view) => {
      const onNavigate = vi.fn();
      for (const urgent of [undefined, false, true]) {
        const tree = MobileHeader({ view, sections, onNavigate, urgent });
        const links = buttons(tree).filter((button) => button.props["aria-label"] === "View urgent guidance");
        expect(links).toHaveLength(urgent && view.screen !== "results" ? 1 : 0);
        expect(renderToStaticMarkup(tree)).not.toMatch(/workspace-urgent|Immediate management|role="alert"/);
        expect(onNavigate).not.toHaveBeenCalled();
        if (links.length) {
          click(links[0]);
          expect(onNavigate).toHaveBeenCalledExactlyOnceWith({ ...view, screen: "results" });
        }
      }
    });

  it("renders all five actual assessments in order with full-row buttons", () => {
    const onNavigate = vi.fn();
    const props = { checklist, progress: undefined, captureStatuses: {}, pendingAssessments: [], onNavigate, assessmentAction };
    const tree = MobileAssessmentHome(props);
    const html = renderToStaticMarkup(tree);
    const rows = buttons(tree);
    expect(rows).toHaveLength(6);
    let previous = -1;
    sections.forEach((section, index) => {
      const labelIndex = html.indexOf(`<strong>${section.label}</strong>`);
      expect(labelIndex).toBeGreaterThan(previous);
      previous = labelIndex;
      expect(buttons(rows[index].props.children)).toHaveLength(0);
      click(rows[index]);
      expect(onNavigate).toHaveBeenLastCalledWith({ screen: "assessment", assessment: section.id, tab: "guidance" });
    });
    expect(html).not.toContain("24 months");
    expect(html).toContain("0 of 5 complete");
    expect(html).not.toContain("Research prototype.");
    expect(html).not.toContain("Assess. Speak. Review.");
    expect(html).not.toContain("Recording is not completion");
    expect(html.indexOf("Generate IMCI recommendations")).toBeGreaterThan(html.indexOf("</ol>"));
    expect(html).not.toContain("Show results");
    expect(onNavigate).toHaveBeenCalledTimes(5);
  });

  it("keeps capture status and pending work separate from authoritative assessment status", () => {
    const html = renderToStaticMarkup(<MobileAssessmentHome checklist={checklist} onNavigate={vi.fn()} assessmentAction={assessmentAction}
      progress={{ ear: { ...progress, status: "COMPLETE", decision: "COMPLETE" }, danger: { ...progress, status: "URGENT", decision: "URGENT" },
        fever: { ...progress, decision: "BLOCK" } }}
      captureStatuses={{ ear: "Captured", danger: "Reviewed", respiratory: "Captured" }} pendingAssessments={["ear", "danger", "respiratory"]} />);
    expect(html).toContain("1 of 5 complete");
    expect(html).toContain('aria-label="Assessment status: Awaiting confirmation"');
    expect(html).not.toContain('aria-label="Assessment status: Complete"');
    expect(html).toContain('aria-label="Assessment status: Urgent"');
    expect(html).toContain('aria-label="Assessment status: Blocked"');
    expect(html).toContain('aria-label="Assessment status: Not started"');
    expect(html).not.toContain("Capture: Captured / awaiting review");
    expect(html).not.toContain("Pending findings to address");
    expect(html).not.toContain("Assessment status: Needs review");
  });

  it("preserves all five authoritative assessment states", () => {
    const html = renderToStaticMarkup(<MobileAssessmentHome checklist={checklist} onNavigate={vi.fn()} assessmentAction={assessmentAction}
      progress={{ danger: { ...progress, status: "URGENT", decision: "URGENT" }, respiratory: { ...progress, status: "COMPLETE", decision: "COMPLETE" },
        diarrhoea: progress, fever: { ...progress, decision: "BLOCK" } }} captureStatuses={{}} pendingAssessments={[]} />);
    for (const label of ["Urgent", "Complete", "Needs info", "Blocked", "Not started"]) {
      expect(html).toContain(`aria-label="Assessment status: ${label}"`);
    }
  });

  it.each([false, true])("badges only the urgent source path despite global urgent decisions, pending=%s", (pending) => {
    const urgent: AssessmentProgress = { status: "URGENT", decision: "URGENT", question: null, blockers: [], missing_fields: [] };
    const html = renderToStaticMarkup(<MobileAssessmentHome checklist={checklist} onNavigate={vi.fn()} assessmentAction={assessmentAction}
      progress={{ danger: urgent, respiratory: { ...urgent, status: "NOT_STARTED" }, diarrhoea: { ...urgent, status: "INCOMPLETE" },
        fever: { ...urgent, status: "COMPLETE" }, ear: { ...urgent, status: "COMPLETE" } }}
      captureStatuses={{}} pendingAssessments={pending ? ["danger", "ear"] : []} />);
    expect(Array.from(html.matchAll(/aria-label="Assessment status: ([^"]+)"/g), (match) => match[1])).toEqual([
      "Urgent", "Not started", "Needs info", "Complete", pending ? "Awaiting confirmation" : "Complete",
    ]);
    expect(html.match(/mobile-assessment-badge--urgent/g)).toHaveLength(1);
    expect(html).toContain("2 of 5 complete");
  });

  it("does not infer completion from five answered danger signs without age", () => {
    const answered = buildChecklist({ danger_signs: Object.fromEntries(sections[0].items.map((item) => [item.id.split(".")[1], false])) });
    const html = renderToStaticMarkup(<MobileAssessmentHome checklist={answered} onNavigate={vi.fn()} assessmentAction={assessmentAction}
      progress={undefined} captureStatuses={{}} pendingAssessments={[]} />);
    expect(html).toContain("0 of 5 complete");
    expect(html).not.toContain('aria-label="Assessment status: Complete"');
  });

  it("leaves age to the shared scope and delegates the final action to its supplied handler, not navigation", () => {
    const onNavigate = vi.fn();
    const generate = vi.fn();
    const action = <button type="button" onClick={generate}>Generate IMCI recommendations</button>;
    const tree = MobileAssessmentHome({ checklist: buildChecklist(), progress: undefined, captureStatuses: {}, pendingAssessments: [], onNavigate,
      assessmentAction: action });
    const html = renderToStaticMarkup(tree);
    expect(html).not.toContain("mobile-age");
    expect(html).not.toContain("<input");
    expect(html).not.toContain("24 months");
    const results = buttons(tree).at(-1);
    expect(results!.props.onClick).toBe(generate);
    expect(renderToStaticMarkup(results!)).toContain("Generate IMCI recommendations");
    click(results);
    expect(generate).toHaveBeenCalledOnce();
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("keeps optional overview tools after the list and before prominent results", () => {
    const html = renderToStaticMarkup(<MobileAssessmentHome checklist={checklist} progress={undefined}
      captureStatuses={{}} pendingAssessments={[]} onNavigate={vi.fn()} assessmentAction={assessmentAction}
      tools={<details><summary>Assessment tools</summary><button>New assessment</button><p>History and About</p></details>} />);
    expect(html.indexOf("<details>")).toBeGreaterThan(html.indexOf("</ol>"));
    expect(html.indexOf("Generate IMCI recommendations")).toBeGreaterThan(html.indexOf("</details>"));
    expect(html).not.toContain('open=""');
  });

  it("has no intro setup button", () => {
    const onNavigate = vi.fn();
    const header = MobileHeader({ view: intro, sections, onNavigate });
    expect(renderToStaticMarkup(header)).toContain("General danger signs");
    expect(buttons(header)).toHaveLength(0);
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("uses the five real checklist danger labels and one set of existing controls per row", () => {
    const danger = sections.find((section) => section.id === "danger")!;
    const onChange = vi.fn();
    const renderField = vi.fn((assessment: string, field: string, booleanLabels?: { yes: string; no: string }) => {
      const item = danger.items.find((item) => item.id === field);
      if (assessment !== "danger" || !item) return null;
      return <ClinicalFieldControl descriptor={{ path: field, label: item.label, kind: "boolean", nullable: true, assessments: ["danger"] }}
        value={null} acceptedValue={null} source="accepted" pending={false} onChange={onChange} booleanLabels={booleanLabels} />;
    });
    const html = renderToStaticMarkup(<AssessmentChecklist mobileView={intro} renderField={renderField} />);
    expect(danger.items).toHaveLength(5);
    const dangerMarkup = html.match(/<details[^>]*data-assessment="danger"[\s\S]*?<\/details>/)?.[0] ?? "";
    expect(dangerMarkup).toContain('open=""');
    const compactLabels = Array.from(dangerMarkup.matchAll(/class="danger-compact-label"[^>]*>([^<]+)<\/span>/g), (match) => match[1]);
    expect(compactLabels).toEqual(danger.items.map((item) => item.label));
    for (const item of danger.items) {
      expect(renderField.mock.calls.filter(([assessment, field]) => assessment === "danger" && field === item.id)).toHaveLength(1);
    }
    expect(html.match(/role="radio"/g)).toHaveLength(15);
    expect(html.match(/aria-checked="true" data-unknown="true"/g)).toHaveLength(5);
    expect(dangerMarkup).toContain(">Unable</button>");
    expect(dangerMarkup).toContain(">Able</button>");
    expect(dangerMarkup.match(/>Not assessed<\/button>/g)).toHaveLength(5);
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe("focused mobile tabs", () => {
  const props = { view: focus, section: sections.find((section) => section.id === "ear"), progress, urgent: false, jobs: [], onNavigate: vi.fn() };

  it("leaves age to the single shared scope", () => {
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} />)).not.toContain("<input");
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} view={{ ...focus, tab: "findings" }} />)).not.toContain("<input");
  });

  it.each(["recording", "queued", "transcribing", "extracting", "failed", "captured", "preparing_review", "review", "applying", "accepted", "discarded"] as const)("leaves intro %s feedback to global CaptureProgress without navigating", (status) => {
    const onNavigate = vi.fn();
    expect(MobileAssessmentTabs({ ...props, view: intro, section: sections[0], onNavigate,
      jobs: [job(status, { assessment: "danger" }), job("failed"), job("queued")] })).toBeNull();
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("keeps reports reachable through ordinary tabs without restoring generic intro feedback", () => {
    const onNavigate = vi.fn();
    const tree = MobileAssessmentTabs({ ...props, view: { ...intro, tab: "findings" }, section: sections[0], onNavigate,
      jobs: [job("failed", { assessment: "danger" }), job("queued", { id: "next", assessment: "danger" })] });
    const html = renderToStaticMarkup(tree);
    expect(html).toContain('aria-pressed="true">Reports');
    expect(html).toContain('aria-label="2 pending reports"');
    expect(html).not.toMatch(/mobile-intro-feedback|Recording failed|Processing\.\.\./);
    expect(onNavigate).not.toHaveBeenCalled();
    click(buttons(tree)[0]);
    expect(onNavigate).toHaveBeenCalledExactlyOnceWith(intro);
  });

  it("only activates intro for danger guidance", () => {
    expect(MobileAssessmentTabs({ ...props, view: intro, section: sections[0] })).toBeNull();
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} view={{ ...focus, intro: true }} />)).toContain("mobile-assessment-tabs");
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} view={{ ...intro, intro: false }} section={sections[0]} />)).toContain("mobile-assessment-tabs");
  });

  it("keeps the backend question and blockers on Guidance, not the source question", () => {
    const html = renderToStaticMarkup(<MobileAssessmentTabs {...props} jobs={[job("captured")]} />);
    expect(html).toContain("Next observation");
    expect(html).toContain("Does the child have ear pain?");
    expect(html).toContain("Confirm the reported observation.");
    expect(html).not.toContain("Original captured question");
    expect(html).not.toContain("ear.ear_pain");
    expect(html).toContain('aria-pressed="true">Assessment');
  });

  it("leaves Findings questions to the existing capture subtree", () => {
    const html = renderToStaticMarkup(<MobileAssessmentTabs {...props} view={{ ...focus, tab: "findings" }} jobs={[job("review")]} />);
    expect(html).not.toContain("Does the child have ear pain?");
    expect(html).not.toContain("Original captured question");
    expect(html).not.toContain("Confirm the reported observation.");
    expect(html).toContain('aria-pressed="true">Reports');
  });

  it("suppresses ordinary questions when urgent but retains blockers", () => {
    const html = renderToStaticMarkup(<MobileAssessmentTabs {...props} urgent />);
    expect(html).not.toContain("Next observation");
    expect(html).not.toContain("Does the child have ear pain?");
    expect(html).toContain("Prioritize urgent actions");
    expect(html).toContain("Confirm the reported observation.");
  });

  it("renders no question for another assessment or non-assessment screen", () => {
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} section={sections[0]} />)).toBe("");
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} section={undefined} />)).toBe("");
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} view={{ ...focus, screen: "results" }} />)).toBe("");
  });

  it("counts only local pending captures and never navigates when jobs finish", () => {
    const onNavigate = vi.fn();
    const jobs = [job("captured"), job("failed", { id: "failed" }), job("accepted", { id: "accepted" }),
      job("discarded", { id: "discarded" }), job("queued", { id: "other", assessment: "fever" })];
    const tree = MobileAssessmentTabs({ ...props, jobs, onNavigate });
    expect(renderToStaticMarkup(tree)).toContain('aria-label="2 pending reports"');
    const finished = renderToStaticMarkup(<MobileAssessmentTabs {...props} onNavigate={onNavigate} jobs={[job("accepted")]} />);
    expect(finished).not.toContain("pending reports");
    expect(finished).toContain('aria-pressed="true">Assessment');
    expect(onNavigate).not.toHaveBeenCalled();
    click(buttons(tree)[1]);
    expect(onNavigate).toHaveBeenCalledWith({ ...focus, tab: "findings" });
  });
});

describe("text-only mobile dock", () => {
  it.each<MobileView>([intro, focus, { screen: "report", assessment: null, tab: "guidance" }])(
    "opens text from $screen with navigation only, without microphone or draft actions", (view) => {
      const props = dockProps({ view });
      const tree = MobileDock(props);
      const link = buttons(tree).find((button) => renderToStaticMarkup(button).includes(view.intro ? "Write text" : "Text report"));
      expect(link!.props["aria-current"]).toBe(view.screen === "report" ? "page" : undefined);
      expect(props.onNavigate).not.toHaveBeenCalled();
      click(link);
      expect(props.onNavigate).toHaveBeenCalledExactlyOnceWith({ screen: "report", assessment: null, tab: "guidance" });
    });

  it.each([intro, focus, { ...intro, tab: "findings" as const },
    { ...focus, screen: "list" as const }, { ...focus, screen: "results" as const }])("has no setup UX on $screen/$tab", (view) => {
    const props = dockProps({ view });
    const html = renderToStaticMarkup(<><MobileHeader view={view} sections={sections} onNavigate={props.onNavigate} /><MobileDock {...props} /></>);
    expect(html).not.toMatch(/setup|recording|speech|speak|microphone|language|intron|<select|<audio|type="checkbox"/i);
  });

  it("shows only text and Continue on intro without automatic navigation", () => {
    const props = dockProps();
    const tree = MobileDock(props);
    const html = renderToStaticMarkup(tree);
    expect(html).toContain('data-mobile-intro="true"');
    expect(html).not.toContain("mobile-dock-nav");
    expect(html).not.toContain("Only applied");
    expect(html).not.toContain("60 seconds");
    expect(html).not.toContain("Record findings");
    expect(buttons(tree)).toHaveLength(2);
    expect(html).toContain("Write text");
    expect(html).toContain("Continue");
    expect(props.onNavigate).not.toHaveBeenCalled();
  });

  it.each([false, true])("Continue only opens overview, with optional confirmation: %s", (withConfirmation) => {
    const confirm = vi.fn();
    const props = dockProps({ confirmation: withConfirmation
      ? <div className="mobile-confirmation"><button type="button" onClick={confirm}>Confirm answers</button></div> : undefined });
    const tree = MobileDock(props);
    expect(renderToStaticMarkup(tree).includes("Confirm answers")).toBe(withConfirmation);
    click(buttons(tree).find((button) => button.props.className === "mobile-continue"));
    expect(props.onNavigate).toHaveBeenCalledExactlyOnceWith({ screen: "list", assessment: null, tab: "guidance" });
    expect(confirm).not.toHaveBeenCalled();
    const dock = MobileDock({ ...props, view: { screen: "list", assessment: null, tab: "guidance" } });
    click(buttons(dock).at(-1));
    expect(props.onNavigate).toHaveBeenLastCalledWith({ screen: "results", assessment: null, tab: "guidance" });
    expect(confirm).not.toHaveBeenCalled();
    if (withConfirmation) {
      click(buttons(tree).find((button) => button.props.children === "Confirm answers"));
      expect(confirm).toHaveBeenCalledOnce();
    }
  });

  it("only hides navigation and shows confirmation during active intro", () => {
    for (const view of [{ ...intro, tab: "findings" as const }, { ...intro, screen: "list" as const }, { ...focus, intro: true }, { ...intro, intro: false }]) {
      const html = renderToStaticMarkup(<MobileDock {...dockProps({ view, confirmation: <span>Intro confirmation</span> })} />);
      expect(html).toContain("mobile-dock-nav");
      expect(html).not.toContain("Intro confirmation");
      expect(html).not.toContain("mobile-continue");
    }
  });

  it.each(["list", "assessment", "report", "results"] as const)("keeps all navigation available on %s without audio controls", (screen) => {
    const props = dockProps({ view: { screen, assessment: "fever", tab: "guidance" } });
    const tree = MobileDock(props);
    const html = renderToStaticMarkup(tree);
    expect(html).toContain('aria-label="Workspace navigation"');
    expect(html).not.toMatch(/recording|speech|speak|microphone|language|intron|<select|<audio/i);
    const actions = buttons(tree);
    expect(actions).toHaveLength(3);
    ["Assessment", "Text report", "Results"].forEach((label, index) => expect(renderToStaticMarkup(actions[index])).toContain(`<span>${label}</span>`));
    expect(actions.map((action) => action.props["aria-current"])).toEqual([
      screen === "list" || screen === "assessment" ? "page" : undefined,
      screen === "report" ? "page" : undefined,
      screen === "results" ? "page" : undefined,
    ]);
    expect(props.onNavigate).not.toHaveBeenCalled();
    actions.forEach(click);
    expect(props.onNavigate).toHaveBeenCalledTimes(3);
    expect(props.onNavigate).toHaveBeenNthCalledWith(1, { screen: "list", assessment: null, tab: "guidance" });
    expect(props.onNavigate).toHaveBeenNthCalledWith(2, { screen: "report", assessment: null, tab: "guidance" });
    expect(props.onNavigate).toHaveBeenNthCalledWith(3, { ...props.view, screen: "results" });
  });

});
