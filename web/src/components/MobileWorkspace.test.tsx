import { Children, isValidElement, type ComponentProps, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { buildChecklist } from "../lib/checklist";
import type { CaptureJob, useVoiceCapture } from "../lib/useVoiceCapture";
import type { AssessmentProgress } from "../types";
import { MobileAssessmentHome, MobileAssessmentTabs, MobileDock, MobileHeader, type MobileView } from "./MobileWorkspace";

const checklist = buildChecklist({ patient_facts: { age_months: 24 } });
const sections = checklist.sections;
const focus: MobileView = { screen: "assessment", assessment: "ear", tab: "guidance" };
const progress: AssessmentProgress = {
  status: "INCOMPLETE", decision: "ASK", missing_fields: ["ear.ear_pain"],
  question: { field: "ear.ear_pain", text: "Does the child have ear pain?" }, blockers: ["Confirm the reported observation."],
};

function voiceMock(): ReturnType<typeof useVoiceCapture> {
  return {
    jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
    addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
    retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(), stageField: vi.fn(),
  };
}

function job(status: CaptureJob["status"], overrides: Partial<CaptureJob> = {}): CaptureJob {
  return {
    id: "clip-1", assessment: "ear", language: "yo", status, originalEncounter: {}, originalRevision: 0,
    reviewVersion: 0, changedFields: [], question: { field: "ear.ear_discharge_reported", text: "Original captured question" },
    trace: { id: "clip-1", timestamp: "2026-09-15T12:00:00Z", assessment: "ear", status: "candidate", source: {} },
    ...overrides,
  };
}

function dockProps(overrides: Partial<ComponentProps<typeof MobileDock>> = {}): ComponentProps<typeof MobileDock> {
  return { view: focus, sections, voice: voiceMock(), language: "en", consent: { audio: true, understanding: true },
    ready: true, onNavigate: vi.fn(), urgent: false, pendingCount: 0, ...overrides };
}

// These components are stateless: inspect their rendered button handlers without a second DOM library.
function buttons(node: ReactNode): ReactElement<ComponentProps<"button">>[] {
  return Children.toArray(node).flatMap((child) => {
    if (!isValidElement<{ children?: ReactNode }>(child)) return [];
    return child.type === "button" ? [child as ReactElement<ComponentProps<"button">>] : buttons(child.props.children);
  });
}

function click(button: ReactElement<ComponentProps<"button">> | undefined) {
  expect(button).toBeDefined();
  expect(button!.props.disabled).not.toBe(true);
  button!.props.onClick?.({} as Parameters<NonNullable<ComponentProps<"button">["onClick"]>>[0]);
}

describe("mobile assessment navigation", () => {
  it.each([
    ["list", "Assessment list"], ["assessment", "Ear problem"],
    ["results", "Clinical results"], ["settings", "Recording setup"],
  ] as const)("labels the %s view without duplicating the brand", (screen, title) => {
    const html = renderToStaticMarkup(<MobileHeader view={{ ...focus, screen }} sections={sections} onNavigate={vi.fn()} />);
    expect(html).toContain(`id="mobile-view-heading" tabindex="-1">${title}</h2>`);
    expect(html).not.toContain("brand");
    expect(html.includes('aria-label="Back to assessments"')).toBe(screen !== "list");
    // The disclaimer belongs in scrolling settings content, not fixed chrome.
    if (screen === "settings") expect(html).not.toContain("Research prototype.");
  });

  it("returns home explicitly from a focused assessment", () => {
    const onNavigate = vi.fn();
    click(buttons(MobileHeader({ view: focus, sections, onNavigate }))[0]);
    expect(onNavigate).toHaveBeenCalledWith({ screen: "list", assessment: null, tab: "guidance" });
  });

  it("renders all five actual assessments in order with full-row buttons", () => {
    const onNavigate = vi.fn();
    const props = { checklist, progress: undefined, captureStatuses: {}, pendingAssessments: [], onNavigate, setupReady: true };
    const tree = MobileAssessmentHome(props);
    const html = renderToStaticMarkup(tree);
    const rows = buttons(tree);
    expect(rows).toHaveLength(5);
    let previous = -1;
    sections.forEach((section, index) => {
      const labelIndex = html.indexOf(`<strong>${section.label}</strong>`);
      expect(labelIndex).toBeGreaterThan(previous);
      previous = labelIndex;
      expect(buttons(rows[index].props.children)).toHaveLength(0);
      click(rows[index]);
      expect(onNavigate).toHaveBeenLastCalledWith({ screen: "assessment", assessment: section.id, tab: "guidance" });
    });
    expect(html).toContain("24 months");
    expect(html).toContain("0 of 5 complete");
    expect(html).toContain("Research prototype.");
  });

  it("keeps capture status and pending work separate from authoritative assessment status", () => {
    const html = renderToStaticMarkup(<MobileAssessmentHome checklist={checklist} setupReady onNavigate={vi.fn()}
      progress={{ ear: { ...progress, status: "COMPLETE", decision: "COMPLETE" }, danger: { ...progress, status: "URGENT", decision: "URGENT" },
        fever: { ...progress, decision: "BLOCK" } }}
      captureStatuses={{ ear: "Captured", danger: "Reviewed", respiratory: "Captured" }} pendingAssessments={["ear", "danger", "respiratory"]} />);
    expect(html).toContain("1 of 5 complete");
    expect(html).toContain('aria-label="Assessment status: Awaiting confirmation"');
    expect(html).not.toContain('aria-label="Assessment status: Complete"');
    expect(html).toContain('aria-label="Assessment status: Urgent"');
    expect(html).toContain('aria-label="Assessment status: Blocked"');
    expect(html).toContain('aria-label="Assessment status: Not started"');
    expect(html).toContain("Capture: Captured / awaiting review");
    expect(html).toContain("Pending findings to address");
    expect(html).not.toContain("Assessment status: Needs review");
  });

  it("never invents age and offers an enabled setup route", () => {
    const onNavigate = vi.fn();
    const tree = MobileAssessmentHome({ checklist: buildChecklist(), progress: undefined, captureStatuses: {}, pendingAssessments: [], onNavigate, setupReady: false });
    const html = renderToStaticMarkup(tree);
    expect(html).toContain("<strong>Unknown</strong>");
    expect(html).not.toContain("24 months");
    const setup = buttons(tree).at(-1);
    expect(renderToStaticMarkup(setup!)).toContain("Configure recording");
    click(setup);
    expect(onNavigate).toHaveBeenCalledWith({ screen: "settings", assessment: null, tab: "guidance" });
  });
});

describe("focused mobile tabs", () => {
  const props = { view: focus, section: sections.find((section) => section.id === "ear"), progress, urgent: false, jobs: [], onNavigate: vi.fn() };

  it("shows the supplied shared age control on Assessment, never on Recordings", () => {
    const ageControl = <input aria-label="Shared age control" value="12." readOnly />;
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} ageControl={ageControl} />)).toContain("Shared age control");
    expect(renderToStaticMarkup(<MobileAssessmentTabs {...props} view={{ ...focus, tab: "findings" }} ageControl={ageControl} />)).not.toContain("Shared age control");
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
    expect(html).toContain('aria-pressed="true">Recordings');
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
    expect(renderToStaticMarkup(tree)).toContain('aria-label="2 pending captures"');
    const finished = renderToStaticMarkup(<MobileAssessmentTabs {...props} onNavigate={onNavigate} jobs={[job("accepted")]} />);
    expect(finished).not.toContain("pending captures");
    expect(finished).toContain('aria-pressed="true">Assessment');
    expect(onNavigate).not.toHaveBeenCalled();
    click(buttons(tree)[1]);
    expect(onNavigate).toHaveBeenCalledWith({ ...focus, tab: "findings" });
  });
});

describe("global mobile recording dock", () => {
  it("records for the focused assessment with the root-controlled settings", () => {
    const props = dockProps();
    const tree = MobileDock(props);
    const html = renderToStaticMarkup(tree);
    expect(html).toContain("Record for: Ear problem");
    click(buttons(tree).find((button) => button.props["aria-label"] === "Record findings"));
    expect(props.voice.startRecording).toHaveBeenCalledWith("ear", "en", { audio: true, understanding: true });
  });

  it.each([
    { consent: { audio: false, understanding: true } },
    { consent: { audio: true, understanding: false } },
    { language: "" as const },
  ])("replaces unconfigured recording with an actionable setup CTA: %j", (overrides) => {
    const props = dockProps(overrides);
    const tree = MobileDock(props);
    const html = renderToStaticMarkup(tree);
    expect(html).not.toContain('aria-label="Record findings"');
    expect(html).toContain("Configure recording");
    click(buttons(tree)[0]);
    expect(props.onNavigate).toHaveBeenCalledWith({ ...focus, screen: "settings" });
    expect(props.voice.startRecording).not.toHaveBeenCalled();
  });

  it("requires encounter readiness even with language and both consents", () => {
    const props = dockProps({ ready: false });
    const record = buttons(MobileDock(props)).find((button) => button.props["aria-label"] === "Record findings");
    expect(record?.props.disabled).toBe(true);
    expect(renderToStaticMarkup(<MobileDock {...props} />)).toContain("Waiting for encounter readiness");
    record?.props.onClick?.({} as Parameters<NonNullable<ComponentProps<"button">["onClick"]>>[0]);
    expect(props.voice.startRecording).not.toHaveBeenCalled();
  });

  it.each(["queued", "transcribing", "extracting", "captured", "preparing_review", "review", "applying", "failed"] as const)(
    "does not block recording for background %s jobs", (status) => {
      const props = dockProps();
      props.voice.jobs = [job(status)];
      const tree = MobileDock(props);
      click(buttons(tree).find((button) => button.props["aria-label"] === "Record findings"));
      expect(props.voice.startRecording).toHaveBeenCalledOnce();
    });

  it.each(["list", "assessment", "results", "settings"] as const)("retains the real mic owner and controls on %s", (screen) => {
    const props = dockProps({ view: { screen, assessment: "fever", tab: "guidance" }, urgent: true, pendingCount: 2 });
    props.voice = { ...props.voice, jobs: [job("recording")], audioState: "recording", recordingId: "clip-1" };
    const tree = MobileDock(props);
    const html = renderToStaticMarkup(tree);
    expect(html).toContain("Recording: Ear problem");
    expect(html).toContain("Yoruba-English");
    expect(html).not.toContain("<span>English</span>");
    expect(html).not.toContain("Record for: Fever");
    expect(html).not.toContain('aria-label="Record findings"');
    expect(html).toContain("2 pending captures to address. Not yet accepted.");
    expect(html).toContain("Urgent guidance remains active.");
    const actions = buttons(tree);
    click(actions.find((button) => button.props["aria-label"] === "Stop recording"));
    click(actions.find((button) => button.props["aria-label"] === "Cancel recording"));
    expect(props.voice.stop).toHaveBeenCalledOnce();
    expect(props.voice.cancelRecording).toHaveBeenCalledOnce();
    actions.slice(-3).forEach(click);
    expect(props.onNavigate).toHaveBeenCalledTimes(3);
    expect(props.onNavigate).toHaveBeenNthCalledWith(1, { screen: "list", assessment: null, tab: "guidance" });
    expect(props.onNavigate).toHaveBeenNthCalledWith(2, { ...props.view, screen: "results" });
    expect(props.onNavigate).toHaveBeenNthCalledWith(3, { ...props.view, screen: "settings" });
  });

  it.each(["permission", "stopping"] as const)("disables Stop during %s but keeps Cancel and navigation enabled", (audioState) => {
    const props = dockProps();
    props.voice = { ...props.voice, jobs: [job("recording")], audioState, recordingId: "clip-1" };
    const actions = buttons(MobileDock(props));
    expect(actions[0].props["aria-label"]).toBe("Stop recording");
    expect(actions[0].props.disabled).toBe(true);
    actions.slice(1).forEach(click);
    expect(props.voice.cancelRecording).toHaveBeenCalledOnce();
    expect(props.onNavigate).toHaveBeenCalledTimes(3);
  });

  it.each(["list", "results", "settings"] as const)("never starts a new capture from idle %s", (screen) => {
    const props = dockProps({ view: { ...focus, screen } });
    const html = renderToStaticMarkup(<MobileDock {...props} />);
    expect(html).not.toContain('aria-label="Record findings"');
    expect(buttons(MobileDock(props))).toHaveLength(3);
    expect(html).toContain('aria-current="page"');
    expect(props.onNavigate).not.toHaveBeenCalled();
  });
});
