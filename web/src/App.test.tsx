import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { FullAssessmentReview } from "./App";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import type { AnalysisResult, AssessmentEvaluation, AssessmentProgress, ExtractionPreview } from "./types";

vi.mock("./lib/useAssessmentSession", () => ({ useAssessmentSession: vi.fn() }));

const analysis: AnalysisResult = {
  input_text: "", extraction_mode: "test", matched_case_id: null, structured_encounter: {},
  structured_view: [], schema_valid: true, extraction_warnings: [], is_complete: true,
  missing_elements: {}, contradictions: [], is_urgent: false, classifications: ["Routine classification"],
  urgent_actions: [], final_actions: ["Routine management"], deferred_actions: [],
  rendered_response: "Routine classification and routine management", decision_trace: [], pipeline_trace: [],
  error: null, outside_supported_scope: false, state: "COMPLETE",
};
const preview: ExtractionPreview = {
  input_text: "Age outside scope", extraction_mode: "test", matched_case_id: null,
  structured_encounter: { patient_facts: { age_months: 1 } }, structured_view: [],
  schema_valid: false, extraction_warnings: [], pipeline_trace: [], error: null,
  outside_supported_scope: true, state: "OUT_OF_SCOPE",
};
const completeProgress: AssessmentProgress = { status: "COMPLETE", decision: "COMPLETE", missing_fields: [], question: null, blockers: [] };
const completeAssessments: AssessmentEvaluation["assessments"] = {
  danger: completeProgress, respiratory: completeProgress, diarrhoea: completeProgress, fever: completeProgress, ear: completeProgress,
};

function session(overrides: Partial<ReturnType<typeof useAssessmentSession>> = {}): ReturnType<typeof useAssessmentSession> {
  return {
    version: 1, encounter: {}, attempted: [], revision: 1, evaluation: null, hasData: false,
    busy: false, error: "", storageHint: "", ready: false, currentRevision: () => 1,
    refresh: vi.fn().mockResolvedValue(true), reset: vi.fn(), evaluate: vi.fn().mockResolvedValue(true),
    accept: vi.fn().mockResolvedValue(true), ...overrides,
    interactions: overrides.interactions ?? [], recordInteraction: vi.fn(), rejectPending: vi.fn(),
  };
}

beforeEach(() => { vi.stubGlobal("navigator", { platform: "Linux" }); });
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

describe("global encounter safeguards", () => {
  it("keeps startup errors, storage warnings, and retry outside all mobile-switched panes", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ error: "Server unavailable", storageHint: "Tab storage unavailable" }));
    const html = renderToStaticMarkup(<App />);
    const global = html.slice(0, html.indexOf("<main"));
    expect(global).toContain("Server unavailable");
    expect(global).toContain("Tab storage unavailable");
    expect(global).toContain("Interpret is unavailable until the server evaluates accepted findings");
    expect(global).toContain("Retry accepted assessment evaluation");
    expect(html).toMatch(/class="analyze-button"[^>]*disabled/);
  });

  it("withholds routine synthesis on any BLOCK without mutating the result or hiding urgent actions", () => {
    const assessments: AssessmentEvaluation["assessments"] = {
      ...completeAssessments, ear: { ...completeProgress, decision: "BLOCK", blockers: ["Review the ear entry and findings"] },
    };
    const result = { ...analysis, is_urgent: true, urgent_actions: ["Authoritative urgent transfer action"] };
    const accepted = { encounter: {}, analysis: result, assessments };
    const before = JSON.stringify(accepted);
    vi.mocked(useAssessmentSession).mockReturnValue(session({ evaluation: accepted, ready: true, hasData: true }));
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Progress blocked; resolve evidence issues before using final synthesis.");
    expect(html).toContain("Review the ear entry and findings");
    expect(html.slice(0, html.indexOf("<main"))).toContain("Authoritative urgent transfer action");
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain(analysis.rendered_response);
    expect(JSON.stringify(accepted)).toBe(before);
  });

  it("still renders accepted routine results when the server has no blockers", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session({ evaluation: { encounter: {}, analysis, assessments: completeAssessments }, ready: true }));
    expect(renderToStaticMarkup(<App />)).toContain("Clinical synthesis ready");
  });

  it("preserves the Modal full-note path and a local, non-chat trace", () => {
    vi.mocked(useAssessmentSession).mockReturnValue(session());
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain("Findings are sent to Modal for interpretation");
    expect(html).toContain("Interaction trace (0)");
    expect(html).toContain("No audio is saved");
    expect(html).toContain("never current clinical guidance");
    expect(html).not.toContain("chat");
  });
});

describe("full-report scope review", () => {
  it("never offers acceptance for an out-of-scope preview, even if diagnostic evaluation fails", () => {
    const html = renderToStaticMarkup(<FullAssessmentReview preview={preview} scopeResult={null} disabled={false} onConfirm={vi.fn()} />);
    expect(html).toContain("Outside supported scope");
    expect(html).toContain("applicable approved age-specific pathway");
    expect(html).toContain("accepted encounter and any urgent guidance are unchanged");
    expect(html).not.toContain("Interpretation is correct");
    expect(html).not.toContain("<button");
  });

  it("displays the existing outside-scope response separately, never as accepted synthesis", () => {
    const scopeResult = { ...analysis, outside_supported_scope: true, state: "OUT_OF_SCOPE" as const, rendered_response: "Use the applicable approved age-specific pathway from the server." };
    const html = renderToStaticMarkup(<FullAssessmentReview preview={preview} scopeResult={scopeResult} disabled={false} onConfirm={vi.fn()} />);
    expect(html).toContain(scopeResult.rendered_response);
    expect(html).not.toContain("Clinical synthesis ready");
    expect(html).not.toContain("Interpretation is correct");
  });

  it("also blocks invalid previews while retaining the normal confirmation flow for valid reports", () => {
    const invalid = { ...preview, outside_supported_scope: false, state: "ERROR" as const };
    expect(renderToStaticMarkup(<FullAssessmentReview preview={invalid} scopeResult={null} disabled={false} onConfirm={vi.fn()} />)).not.toContain("Interpretation is correct");
    const valid = { ...invalid, schema_valid: true, state: "READY_FOR_REVIEW" as const };
    expect(renderToStaticMarkup(<FullAssessmentReview preview={valid} scopeResult={null} disabled={false} onConfirm={vi.fn()} />)).toContain("Interpretation is correct");
  });
});
