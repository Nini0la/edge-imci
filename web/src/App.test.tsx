import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import { useVoiceCapture, type CaptureJob } from "./lib/useVoiceCapture";
import type { AnalysisResult, AssessmentEvaluation, AssessmentProgress, InteractionTrace } from "./types";

vi.mock("./lib/useAssessmentSession", () => ({ useAssessmentSession: vi.fn() }));
vi.mock("./lib/useVoiceCapture", () => ({ useVoiceCapture: vi.fn() }));

const analysis: AnalysisResult = {
  input_text: "", extraction_mode: "test", matched_case_id: null, structured_encounter: {},
  structured_view: [], schema_valid: true, extraction_warnings: [], is_complete: true,
  missing_elements: {}, contradictions: [], is_urgent: false, classifications: ["Routine classification"],
  urgent_actions: [], final_actions: ["Routine management"], deferred_actions: [],
  rendered_response: "Routine classification and routine management", decision_trace: [], pipeline_trace: [],
  error: null, outside_supported_scope: false, state: "COMPLETE",
};
const completeProgress: AssessmentProgress = { status: "COMPLETE", decision: "COMPLETE", missing_fields: [], question: null, blockers: [] };
const completeAssessments: AssessmentEvaluation["assessments"] = {
  danger: completeProgress, respiratory: completeProgress, diarrhoea: completeProgress, fever: completeProgress, ear: completeProgress,
};
const encounter = { patient_facts: { age_months: 24 } };
const accepted = { encounter, analysis, assessments: completeAssessments };
const trace: InteractionTrace = { id: "trace", timestamp: "2026-09-14T12:00:00Z", assessment: "ear", status: "failed", source: { submitted_text: "Unaccepted words" } };

function session(overrides: Partial<ReturnType<typeof useAssessmentSession>> = {}): ReturnType<typeof useAssessmentSession> {
  return {
    version: 1, encounter: {}, attempted: [], revision: 1, evaluation: null, hasData: false,
    busy: false, error: "", storageHint: "", ready: false, currentRevision: () => 1,
    snapshot: () => ({ encounter: {}, revision: 1, evaluation: null }),
    interruptedCount: 0, acknowledgeInterrupted: vi.fn(),
    refresh: vi.fn().mockResolvedValue(true), reset: vi.fn(), evaluate: vi.fn().mockResolvedValue(true),
    accept: vi.fn().mockResolvedValue(true), interactions: [], recordInteraction: vi.fn(), rejectPending: vi.fn(), ...overrides,
  };
}

function job(status: CaptureJob["status"], overrides: Partial<CaptureJob> = {}): CaptureJob {
  return { id: "ear-clip", assessment: "ear", language: "yo", status, originalEncounter: {}, originalRevision: 1,
    reviewVersion: 0, changedFields: [], trace, ...overrides };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAssessmentSession).mockReturnValue(session());
  vi.mocked(useVoiceCapture).mockReturnValue({
    jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
    addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
    retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(),
  });
});

describe("guide-first workspace", () => {
  it("has two responsive panels, defaults to Assessment, and removes the central full-note workflow", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain('class="clinical-workspace clinical-workspace--two-panel" data-active-panel="assessment"');
    const nav = html.slice(html.indexOf("<nav"), html.indexOf("</nav>"));
    expect(nav.match(/<button/g)).toHaveLength(2);
    expect(nav).toContain("Assessment");
    expect(nav).toContain("Result");
    expect(nav).not.toContain("Findings");
    expect(html).not.toContain("findings-panel");
    expect(html).not.toContain("Describe the completed assessment");
    expect(html).not.toContain("Interpret findings");
    expect(html).not.toContain("Demonstration input");
    expect(html).not.toContain("chat");
    expect(html).toContain('class="assessment-section__body section-evidence-layout"');
    expect(html).toContain('class="checklist-footer"');
    expect(html).toMatch(/<details class="interaction-history"><summary>Interaction trace \(0\)/);
  });

  it("discloses both external services and requires both explicit consents and a language", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Audio is sent to Intron");
    expect(html).toContain("external Azure OpenAI in demo mode");
    expect(html).toContain("Settings apply to new clips only");
    expect(html.match(/type="checkbox"/g)).toHaveLength(2);
    expect(html).not.toContain('checked=""');
    expect(html).toContain('<option value="" disabled="" selected="">Select language');
    for (const language of ["en", "pcm", "yo", "ig", "ha"]) expect(html).toContain(`value="${language}"`);
    expect(html.match(/class="record-findings"[^>]*disabled/g)).toHaveLength(5);
  });

  it("keeps Stop and Cancel outside the mobile-switched panes", () => {
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job("recording")], recordingId: "ear-clip", audioState: "recording" });
    const html = renderToStaticMarkup(<App />);
    const global = html.slice(0, html.indexOf("<main"));
    expect(global).toContain('aria-label="Active recording"');
    expect(global).toContain("ear / yo");
    expect(global).toContain(">Stop</button>");
    expect(global).toContain(">Cancel</button>");
  });
});

describe("quiet accepted results", () => {
  it("withholds the final plan until interrupted captures are acknowledged, without hiding accepted urgency", () => {
    const restored = session({ encounter, ready: true, interruptedCount: 2, evaluation: { ...accepted,
      analysis: { ...analysis, is_urgent: true, urgent_actions: ["Authoritative urgent transfer action"] } } });
    vi.mocked(useAssessmentSession).mockReturnValue(restored);
    const html = renderToStaticMarkup(<App />);
    const global = html.slice(0, html.indexOf("<main"));
    expect(global).toContain("2 capture(s) interrupted and not applied");
    expect(global).toContain("Audio jobs are not resumed after reload");
    expect(global).toContain("Acknowledge interrupted captures");
    expect(global).toContain("Authoritative urgent transfer action");
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain(analysis.rendered_response);
    vi.mocked(useAssessmentSession).mockReturnValue({ ...restored, interruptedCount: 0 });
    expect(renderToStaticMarkup(<App />)).toContain("Clinical synthesis ready");
  });

  it("shows the interruption notice even with no meaningful accepted evidence", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ interruptedCount: 1 }));
    const html = renderToStaticMarkup(<App />);
    expect(html.slice(0, html.indexOf("<main"))).toContain("1 capture(s) interrupted and not applied");
    expect(html).toContain("Ready when you are");
  });

  it.each([{}, { patient_facts: { age_months: null }, ear: { ear_pain: null } }])("stays neutral for empty or all-null accepted evidence", (empty) => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter: empty, hasData: true, ready: true,
      evaluation: { ...accepted, encounter: empty, analysis: { ...analysis, state: "INCOMPLETE", is_complete: false,
        rendered_response: "Information needed: all fields" } } }));
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Ready when you are");
    expect(html).not.toContain("Assessment incomplete");
    expect(html).not.toContain("Information needed");
    expect(html).not.toContain("Assessment in progress");
  });

  it("does not treat trace-only drafts or unaccepted captures as clinical evidence", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ hasData: true, ready: true, interactions: [trace], evaluation: { ...accepted, encounter: {} } }));
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job("captured")] });
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Ready when you are");
    expect(html).toContain("Interaction trace (1)");
    expect(html).not.toContain("Clinical synthesis ready");
  });

  it.each([{ patient_facts: { has_ear_problem: false } }, { ear: { ear_discharge_duration_days: 0 } }])("counts known false and zero values, showing only a compact partial note", (known) => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter: known, ready: true,
      evaluation: { ...accepted, encounter: known, analysis: { ...analysis, is_complete: false, state: "INCOMPLETE", rendered_response: "Information needed: remaining fields" } } }));
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Assessment in progress");
    expect(html).toContain("next observations in each assessment section");
    expect(html).not.toContain("Ready when you are");
    expect(html).not.toContain("Assessment incomplete");
    expect(html).not.toContain("Information needed");
    expect(html).not.toContain("Clinical synthesis ready");
  });

  it("renders final synthesis only for accepted complete evidence with no pending jobs", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, evaluation: accepted, ready: true }));
    expect(renderToStaticMarkup(<App />)).toContain("Clinical synthesis ready");
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job("accepted"), job("discarded", { id: "old" })] });
    expect(renderToStaticMarkup(<App />)).toContain("Clinical synthesis ready");
  });

  it.each<CaptureJob["status"]>(["recording", "queued", "transcribing", "extracting", "captured", "preparing_review", "review", "applying", "failed"])("withholds final synthesis while a job is %s", (status) => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, evaluation: accepted, ready: true }));
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job(status)] });
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Review captured findings before final plan");
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain(analysis.rendered_response);
  });

  it("retains accepted urgent guidance globally while an unrelated section processes", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, ready: true, evaluation: { ...accepted,
      analysis: { ...analysis, is_complete: false, is_urgent: true, state: "URGENT_INCOMPLETE", urgent_actions: ["Authoritative urgent transfer action"] } } }));
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job("transcribing")] });
    const html = renderToStaticMarkup(<App />);
    expect(html.slice(0, html.indexOf("<main"))).toContain("Authoritative urgent transfer action");
    expect(html).toContain("Processing / transcribing");
    expect(html).not.toContain(analysis.rendered_response);
  });

  it("withholds routine synthesis on BLOCK without changing engine values or hiding urgent actions", () => {
    const evaluation = { ...accepted, assessments: { ...completeAssessments,
      ear: { ...completeProgress, decision: "BLOCK" as const, blockers: ["Review the ear entry and findings"] } },
      analysis: { ...analysis, is_urgent: true, urgent_actions: ["Authoritative urgent transfer action"] } };
    const before = JSON.stringify(evaluation);
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, evaluation, ready: true }));
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Progress blocked; resolve evidence issues before using final synthesis.");
    expect(html).toContain("Review the ear entry and findings");
    expect(html.slice(0, html.indexOf("<main"))).toContain("Authoritative urgent transfer action");
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain(analysis.rendered_response);
    expect(JSON.stringify(evaluation)).toBe(before);
  });

  it("keeps startup errors, storage warnings, and retry global without hiding background jobs", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ error: "Server unavailable", storageHint: "Tab storage unavailable" }));
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job("extracting")], error: "Microphone unavailable" });
    const html = renderToStaticMarkup(<App />);
    const global = html.slice(0, html.indexOf("<main"));
    for (const message of ["Server unavailable", "Tab storage unavailable", "Microphone unavailable", "Retry accepted assessment evaluation"]) expect(global).toContain(message);
    expect(html).toContain("Processing / structuring findings");
    expect(html).toContain("Ready when you are");
  });
});
