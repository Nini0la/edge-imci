import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import { useVoiceCapture, type CaptureJob } from "./lib/useVoiceCapture";
import { useGuideEditor } from "./lib/useGuideEditor";
import { useMobileLayout } from "./lib/layout";
import type { AnalysisResult, AssessmentEvaluation, AssessmentProgress, InteractionTrace } from "./types";

vi.mock("./lib/useAssessmentSession", () => ({ useAssessmentSession: vi.fn() }));
vi.mock("./lib/useVoiceCapture", () => ({ useVoiceCapture: vi.fn() }));
vi.mock("./lib/useGuideEditor", () => ({ useGuideEditor: vi.fn() }));
vi.mock("./lib/layout", () => ({ useMobileLayout: vi.fn() }));

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
    version: 1, encounter, patientName: "Synthetic Patient", attempted: [], revision: 1, hasData: true,
    evaluation: { ...accepted, analysis: { ...analysis, is_complete: false, state: "INCOMPLETE" } },
    busy: false, error: "", storageHint: "", ready: true, currentRevision: () => 1,
    snapshot: () => ({ encounter, revision: 1, evaluation: { ...accepted, analysis: { ...analysis, is_complete: false, state: "INCOMPLETE" } } }),
    interruptedCount: 0, acknowledgeInterrupted: vi.fn(),
    needsResumeDecision: false, resumeSaved: vi.fn().mockResolvedValue(false), updateIntake: vi.fn().mockResolvedValue(false),
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
  vi.mocked(useMobileLayout).mockReturnValue(false);
  vi.mocked(useAssessmentSession).mockReturnValue(session());
  vi.mocked(useVoiceCapture).mockReturnValue({
    jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
    addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
    retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(), stageField: vi.fn(),
  });
  vi.mocked(useGuideEditor).mockImplementation((session) => ({ schema: null, schemaError: "", workingEncounter: session.encounter,
    pendingFieldPaths: [], field: () => null, selectedJob: () => undefined, selectJob: vi.fn(), confirm: vi.fn().mockResolvedValue(undefined),
    reset: vi.fn(), retrySchema: vi.fn() }));
});

describe("guide-first workspace", () => {
  it.each([false, true].flatMap((mobile) => [
    { patientName: undefined, encounter }, { patientName: "", encounter }, { patientName: "   ", encounter },
    { patientName: "x".repeat(201), encounter },
    ...[null, 1, 60, 24.5, "24"].map((age) => ({ patientName: "Synthetic Patient", encounter: { patient_facts: { age_months: age } } })),
    { patientName: "Synthetic Patient", encounter: {} },
  ].map((details) => ({ mobile, ...details }))))("gates invalid intake before all workspace content: %j", ({ mobile, ...details }) => {
    vi.mocked(useMobileLayout).mockReturnValue(mobile);
    const active = session({ ...details, evaluation: accepted });
    vi.mocked(useAssessmentSession).mockReturnValue(active);
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Patient intake</h1>");
    expect(html).toContain("Start assessment</button>");
    for (const hidden of ["clinical-workspace", "mobile-dock", "Clinical synthesis ready", "Generate IMCI recommendations", "Interpret text"])
      expect(html).not.toContain(hidden);
    expect(useVoiceCapture).toHaveBeenCalledWith(active, false);
    expect(active.updateIntake).not.toHaveBeenCalled();
  });

  it.each([2, 59])("shows accepted age %s only in the patient summary, not an ordinary age editor", (age) => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter: { patient_facts: { age_months: age } } }));
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain('aria-label="Patient details"');
    expect(html).toContain("Synthetic Patient");
    expect(html).toContain(`Age: ${age} months`);
    expect(html).toContain("Edit patient details</button>");
    expect(html).not.toContain('class="assessment-scope"');
    expect(html).not.toContain('id="patient-age"');
    expect(html).toContain("Assessment in progress");
  });

  it.each([false, true].flatMap((mobile) => ["intake-only", "incomplete", "busy"].map((state) => ({ mobile, state }))))(
    "offers generation for $state evidence with mobile=$mobile, disabling only while busy", ({ mobile, state }) => {
      vi.mocked(useMobileLayout).mockReturnValue(mobile);
      vi.mocked(useAssessmentSession).mockReturnValue(session({ ready: true, busy: state === "busy",
        encounter, evaluation: { ...accepted,
          analysis: { ...analysis, is_complete: false, state: "INCOMPLETE" } } }));
      const html = renderToStaticMarkup(<App />);
      const action = html.match(/<button[^>]*class="generate-assessment"[^>]*>[\s\S]*?<\/button>/g);
      expect(action).toHaveLength(1);
      expect(action![0].includes('disabled=""')).toBe(state === "busy");
      expect(action![0]).toContain(state === "busy" ? "Checking assessment..." : "Generate IMCI recommendations");
      expect(html).not.toContain("Show results");
      if (!mobile) expect(html.indexOf('class="assessment-submit"')).toBeGreaterThan(html.indexOf(">Clear encounter</button>"));
    });

  it("shows only the saved-assessment choice before the normal workspace, even if old output is supplied", () => {
    const saved = session({ needsResumeDecision: true, encounter, ready: true, hasData: true, interactions: [trace],
      interruptedCount: 1, evaluation: { ...accepted, analysis: { ...analysis, is_urgent: true, urgent_actions: ["Old urgent action"] } } });
    vi.mocked(useAssessmentSession).mockReturnValue(saved);
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain('<main class="resume-assessment" aria-labelledby="resume-assessment-title">');
    expect(html).toContain('id="resume-assessment-title">Saved assessment</h1>');
    expect(html).toContain("Resume saved assessment</button>");
    expect(html).toContain("Start new assessment</button>");
    expect(html.match(/<button/g)).toHaveLength(2);
    for (const hidden of ["clinical-workspace", "assessment-scope", "mobile-dock", "Interaction trace", "Old urgent action",
      "Clinical synthesis ready", "Acknowledge interrupted captures", 'role="radiogroup"', "Clear encounter"]) expect(html).not.toContain(hidden);
    expect(useVoiceCapture).toHaveBeenCalledWith(saved, false);
    expect(useGuideEditor).toHaveBeenCalledWith(saved, vi.mocked(useVoiceCapture).mock.results[0].value);
    expect(saved.resumeSaved).not.toHaveBeenCalled();
    expect(saved.refresh).not.toHaveBeenCalled();
    expect(saved.reset).not.toHaveBeenCalled();
  });

  it("has three responsive panels with one central text report between the guide and results", () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain('class="clinical-workspace clinical-workspace--three-panel" data-active-panel="assessment"');
    const nav = html.slice(html.indexOf("<nav"), html.indexOf("</nav>"));
    expect(nav.match(/<button/g)).toHaveLength(3);
    expect(nav).toContain("Assessment");
    expect(nav).toContain("Text report");
    expect(nav).toContain("Result");
    expect(html.match(/aria-label="IMCI assessment guide"/g)).toHaveLength(1);
    expect(html.match(/aria-label="Text assessment report"/g)).toHaveLength(1);
    expect(html.match(/aria-label="Clinical result"/g)).toHaveLength(1);
    expect(html.indexOf('class="report-panel"')).toBeGreaterThan(html.indexOf('class="panel checklist-panel"'));
    expect(html.indexOf('class="report-panel"')).toBeLessThan(html.indexOf('class="output-panel"'));
    expect(html).toContain("Write assessment findings");
    expect(html).toContain("Interpret text");
    expect(nav).not.toContain("Findings");
    expect(html).not.toContain("findings-panel");
    expect(html).not.toContain("Describe the completed assessment");
    expect(html).not.toContain("Interpret findings");
    expect(html).not.toContain("Demonstration input");
    expect(html).not.toContain("chat");
    expect(html).toContain('class="assessment-section__body section-evidence-layout"');
    expect(html).toContain('class="checklist-footer"');
    expect(html).toContain('>Clear encounter</button>');
    expect(html).not.toContain('>Start new assessment</button>');
    expect(html).toMatch(/<details class="interaction-history"><summary>Assessment history \(0\)/);
    expect(html).not.toContain('class="app-frame app-frame--mobile"');
    expect(html).toContain('class="mobile-only mobile-workspace-header" data-mobile-intro="true"');
    const main = html.slice(html.indexOf("<main"), html.indexOf(">", html.indexOf("<main")));
    expect(main).not.toMatch(/data-mobile-|data-show-age/);
    expect(html.match(/data-assessment="[^"]+" open=""/g)).toEqual(['data-assessment="danger" open=""']);
    expect(html).not.toContain('class="assessment-scope"');
  });

  it.each([false, true])("exposes text-only processing and no speech controls with mobile=%s", (mobile) => {
    vi.mocked(useMobileLayout).mockReturnValue(mobile);
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("About processing");
    expect(html).toContain("Submitted text and clinical context go to the language-understanding service");
    expect(html).toContain("The intake name is not included automatically");
    expect(html).toContain("Assessment history (0)");
    for (const removed of ['type="checkbox"', '<select', "Intron", "microphone", 'aria-label="Speak"', 'id="mobile-speech-language"', 'id="capture-language"', "record-findings", "capture-toolbar"])
      expect(html).not.toContain(removed);
    expect(useVoiceCapture).toHaveBeenCalledWith(expect.anything(), false);
    expect(vi.mocked(useVoiceCapture).mock.results[0].value.startRecording).not.toHaveBeenCalled();
  });
});

describe("quiet accepted results", () => {
  it.each([{ ready: false }, { busy: true }, { error: "Latest check failed" }])(
    "withholds an old complete evaluation when the session is not result-ready: %j", (gate) => {
      vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, ready: true, evaluation: accepted, ...gate }));
      const html = renderToStaticMarkup(<App />);
      expect(html).not.toContain("Clinical synthesis ready");
      expect(html).not.toContain(analysis.rendered_response);
    });

  it.each([false, true].flatMap((mobile) => [false, true].map((pending) => ({ mobile, pending }))))(
    "shows confirmed danger-sign management after intake before overall completion, mobile=$mobile pending=$pending",
    ({ mobile, pending }) => {
      vi.mocked(useMobileLayout).mockReturnValue(mobile);
      const dangerEncounter = { ...encounter, danger_signs: { unable_to_drink_or_breastfeed: true, vomits_everything: true,
        had_convulsions: false, lethargic_or_unconscious: false, convulsing_now: false } };
      const urgentActions = ["Complete the remaining assessment quickly.", "Give the indicated pre-referral treatment immediately.",
        "Keep the child warm.", "Prevent low blood sugar.", "Arrange urgent referral."];
      const evaluation = { ...accepted, encounter: dangerEncounter, analysis: { ...analysis, is_complete: false, is_urgent: true,
        state: "URGENT_INCOMPLETE" as const, classifications: [], final_actions: [], urgent_actions: urgentActions,
        missing_elements: { ear: ["ear_pain"] } } };
      const original = structuredClone(evaluation);
      vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter: dangerEncounter, ready: true, evaluation }));
      vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: pending ? [job("transcribing")] : [] });
      const html = renderToStaticMarkup(<App />);
      const right = html.slice(html.indexOf('<section class="output-panel"'));
      for (const text of ["Urgent findings confirmed", "Immediate management", "Assessment incomplete", ...urgentActions]) expect(right).toContain(text);
      for (const action of urgentActions) expect(html.split(action)).toHaveLength(2);
      expect(html).not.toContain("workspace-urgent");
      for (const hidden of ["Clinical synthesis ready", "Routine classification", "Routine management", "diazepam", "Very severe disease"]) expect(right).not.toContain(hidden);
      expect(right.includes("New findings are awaiting review")).toBe(pending);
      expect(evaluation).toEqual(original);
    });

  it.each(["contradiction", "blocker", "pending", "interrupted"])(
    "keeps accepted urgent actions visible without leaking a complete plan through a %s gate", (gate) => {
      const evaluation = { ...accepted, analysis: { ...analysis, is_urgent: true, state: "URGENT_COMPLETE" as const,
        urgent_actions: ["Accepted immediate action"], contradictions: gate === "contradiction" ? ["Resolve conflicting observations"] : [] },
        assessments: { ...completeAssessments, danger: { ...completeProgress, status: "URGENT" as const, decision: "URGENT" as const,
          blockers: gate === "blocker" ? ["Resolve conflicting observations"] : [] } } };
      vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, ready: true, evaluation, interruptedCount: gate === "interrupted" ? 1 : 0 }));
      vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: gate === "pending" ? [job("review")] : [] });
      const html = renderToStaticMarkup(<App />);
      const right = html.slice(html.indexOf('<section class="output-panel"'));
      expect(right).toContain("Accepted immediate action");
      expect(html.split("Accepted immediate action")).toHaveLength(2);
      expect(html.slice(0, html.indexOf("<main"))).not.toContain("Accepted immediate action");
      expect(html).not.toContain("workspace-urgent");
      expect(right).not.toContain(analysis.rendered_response);
      expect(right).not.toContain("Clinical synthesis ready");
    });

  it.each([
    { schema_valid: false }, { error: "Evaluation failed", state: "ERROR" as const },
    { outside_supported_scope: true, state: "OUT_OF_SCOPE" as const },
  ])("does not expose guidance from invalid, failed, or out-of-scope evaluation %j", (invalid) => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, ready: true, evaluation: { ...accepted,
      analysis: { ...analysis, is_urgent: true, urgent_actions: ["Invalid evaluation action"], ...invalid } } }));
    const html = renderToStaticMarkup(<App />);
    const right = html.slice(html.indexOf('<section class="output-panel"'));
    for (const hidden of ["Invalid evaluation action", "Immediate management", analysis.rendered_response]) expect(right).not.toContain(hidden);
  });

  it("withholds the final plan until interrupted captures are acknowledged, without hiding accepted urgency", () => {
    const restored = session({ encounter, ready: true, interruptedCount: 2, evaluation: { ...accepted,
      analysis: { ...analysis, is_urgent: true, urgent_actions: ["Authoritative urgent transfer action"] } } });
    vi.mocked(useAssessmentSession).mockReturnValue(restored);
    const html = renderToStaticMarkup(<App />);
    const global = html.slice(0, html.indexOf("<main"));
    expect(global).toContain("2 report(s) interrupted and not applied");
    expect(global).toContain("Check the assessment history");
    expect(global).toContain("Acknowledge interrupted captures");
    expect(global).not.toContain("Authoritative urgent transfer action");
    expect(html.slice(html.indexOf('<section class="output-panel"'))).toContain("Authoritative urgent transfer action");
    expect(html.split("Authoritative urgent transfer action")).toHaveLength(2);
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain(analysis.rendered_response);
    vi.mocked(useAssessmentSession).mockReturnValue({ ...restored, interruptedCount: 0 });
    expect(renderToStaticMarkup(<App />)).toContain("Clinical synthesis ready");
  });

  it("shows the interruption notice after intake even without other accepted findings", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ interruptedCount: 1 }));
    const html = renderToStaticMarkup(<App />);
    expect(html.slice(0, html.indexOf("<main"))).toContain("1 report(s) interrupted and not applied");
    expect(html).toContain("Acknowledge interrupted captures before final plan");
  });

  it.each([{}, { patient_facts: { age_months: null }, ear: { ear_pain: null } }])("requires intake for empty or all-null accepted evidence", (empty) => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter: empty, hasData: true, ready: true,
      evaluation: { ...accepted, encounter: empty, analysis: { ...analysis, state: "INCOMPLETE", is_complete: false,
        rendered_response: "Information needed: all fields" } } }));
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Patient intake</h1>");
    expect(html).not.toContain("clinical-workspace");
    expect(html).not.toContain("Assessment incomplete");
    expect(html).not.toContain("Information needed");
    expect(html).not.toContain("Assessment in progress");
  });

  it("does not treat trace-only drafts or unaccepted captures as clinical evidence", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter: {}, hasData: true, ready: true, interactions: [trace], evaluation: { ...accepted, encounter: {} } }));
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job("captured")] });
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Patient intake</h1>");
    expect(html).not.toContain("Assessment history (1)");
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain('aria-label="Immediate management"');
  });

  it.each([{ patient_facts: { age_months: 24, has_ear_problem: false } }, { ...encounter, ear: { ear_discharge_duration_days: 0 } }])("counts known false and zero values after intake, showing only a compact partial note", (known) => {
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

  it("hides desktop engineering output while preserving readable history and original provenance", () => {
    const result = { ...analysis,
      pipeline_trace: [{ kind: "LEARNED" as const, label: "Original processing step", detail: "Original processing detail" }],
      decision_trace: [{ rule_id: "original-rule", pathway: "Ear", classification: "Routine classification", findings: [["Pain", "Absent"] as [string, string]], rule_description: "Accepted rationale" }],
    };
    const evaluation = { ...accepted, analysis: result };
    const original = structuredClone({ evaluation, trace });
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, evaluation, ready: true, interactions: [trace] }));
    const html = renderToStaticMarkup(<App />);
    for (const text of ["Clinical synthesis ready", "Assessment history (1)", "Unaccepted words", "Accepted rationale"]) expect(html).toContain(text);
    for (const text of ["Interaction trace", "<pre", "<code", "JSON", "original-rule", "Processing trace", "Original processing detail"]) expect(html).not.toContain(text);
    expect({ evaluation, trace }).toEqual(original);
  });

  it.each<CaptureJob["status"]>(["recording", "queued", "transcribing", "extracting", "captured", "preparing_review", "review", "applying", "failed"])("withholds final synthesis while a job is %s", (status) => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, evaluation: accepted, ready: true }));
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job(status)] });
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Review captured findings before final plan");
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain(analysis.rendered_response);
  });

  it("keeps accepted urgent guidance only in results while unrelated processing remains global", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ encounter, ready: true, evaluation: { ...accepted,
      analysis: { ...analysis, is_complete: false, is_urgent: true, state: "URGENT_INCOMPLETE", urgent_actions: ["Authoritative urgent transfer action"] } } }));
    vi.mocked(useVoiceCapture).mockReturnValue({ ...useVoiceCapture(session()), jobs: [job("extracting")] });
    const html = renderToStaticMarkup(<App />);
    const global = html.slice(0, html.indexOf("<main"));
    expect(global).not.toContain("Authoritative urgent transfer action");
    expect(global).toContain('aria-label="Assessment progress"');
    expect(global).toContain("Adding your findings to the assessment");
    expect(html.slice(html.indexOf('<section class="output-panel"'))).toContain("Authoritative urgent transfer action");
    expect(html.split("Authoritative urgent transfer action")).toHaveLength(2);
    expect(html).not.toContain("workspace-urgent");
    expect(html).toContain("Processing / structuring findings");
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
    expect(html.slice(0, html.indexOf("<main"))).not.toContain("Authoritative urgent transfer action");
    expect(html.slice(html.indexOf('<section class="output-panel"'))).toContain("Authoritative urgent transfer action");
    expect(html.split("Authoritative urgent transfer action")).toHaveLength(2);
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain(analysis.rendered_response);
    expect(JSON.stringify(evaluation)).toBe(before);
  });

  it("keeps setup errors and storage warnings on intake without exposing the workspace", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ ready: false, error: "Server unavailable", storageHint: "Tab storage unavailable" }));
    const html = renderToStaticMarkup(<App />);
    for (const message of ["Server unavailable", "Tab storage unavailable", "Retry assessment setup", "Patient intake</h1>"]) expect(html).toContain(message);
    expect(html).not.toContain("clinical-workspace");
  });
});
