import { Children, isValidElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AssessmentCapture, CandidateDetails, CaptureJobCard } from "./AssessmentCapture";
import type { CaptureJob, useVoiceCapture } from "../lib/useVoiceCapture";
import type { AssessmentCandidate, AssessmentProgress } from "../types";

const runtime = vi.hoisted(() => ({ current: null as { value: unknown } | null }));
vi.mock("react", async (importOriginal) => {
  const react = await importOriginal<typeof import("react")>();
  return { ...react, useState(initial: unknown) {
    const state = runtime.current;
    if (!state) return react.useState(initial);
    return [state.value, (next: unknown) => { state.value = next; }];
  } };
});

const progress: AssessmentProgress = {
  status: "INCOMPLETE", decision: "ASK", missing_fields: ["ear.ear_pain", "ear.ear_discharge_reported"],
  question: { field: "ear.ear_pain", text: "Does the child have ear pain?" }, blockers: [],
};
const candidate: AssessmentCandidate = { assessment: "ear", input_text: "Provider-normalized input", extraction_mode: "frontier", warnings: [],
  changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: null, value: false, conflict: false, outside_assessment: false }] };
const voice: ReturnType<typeof useVoiceCapture> = {
  jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
  addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
  retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(), stageField: vi.fn(),
};
const props = { assessment: "ear" as const, encounter: {}, revision: 2, progress, urgent: false,
  voice, reviewDisabled: false, ready: true, onDirty: vi.fn(), onReviewJob: vi.fn() };
function job(status: CaptureJob["status"], overrides: Partial<CaptureJob> = {}): CaptureJob {
  return { id: "clip-1", assessment: "ear", language: "yo", status, originalEncounter: {}, originalRevision: 1,
    reviewRevision: 2, reviewVersion: 1, changedFields: [], candidate, originalCandidate: candidate,
    inputText: "No", question: { field: "ear.ear_pain", text: "Original question about pain" },
    trace: { id: "trace", timestamp: "2026-09-14T12:00:00Z", assessment: "ear", status: "candidate", source: {} }, ...overrides };
}

describe("inline capture presentation", () => {
  it.each([
    { ready: false, text: "No ear pain", queued: true },
    { ready: true, text: " \n ", queued: true },
    { ready: true, text: "No ear pain", queued: false },
    { ready: true, text: "No ear pain", queued: true },
  ])("gates text submission and clears only queued drafts: %j", ({ ready, text, queued }) => {
    const draft = { text, context: null };
    const state = { value: draft as unknown };
    const addText = vi.fn().mockReturnValue(queued);
    let submit: (() => void) | undefined;
    function Capture() {
      runtime.current = state;
      try {
        const tree = AssessmentCapture({ ...props, ready, voice: { ...voice, addText }, showDebug: false });
        function visit(node: ReactNode) {
          Children.forEach(node, (child) => {
            if (!isValidElement<{ children?: ReactNode; disabled?: boolean; onClick?: () => void }>(child)) return;
            if (child.type === "button" && child.props.children === "Process typed finding") {
              expect(child.props.disabled).toBe(!ready || !text.trim());
              submit = child.props.onClick;
            }
            visit(child.props.children);
          });
        }
        visit(tree);
        return tree;
      } finally { runtime.current = null; }
    }
    const html = renderToStaticMarkup(<Capture />);
    expect(html).not.toMatch(/<textarea[^>]*disabled/);
    submit!();
    if (ready && text.trim()) {
      expect(addText).toHaveBeenCalledExactlyOnceWith("ear", text, true, { encounter: {}, revision: 2, question: undefined });
    } else expect(addText).not.toHaveBeenCalled();
    expect(state.value).toEqual(ready && text.trim() && queued ? { text: "" } : draft);
    expect(voice.startRecording).not.toHaveBeenCalled();
  });

  it.each([false, true])("preserves the explicit review gate=%s without accepting a report", (reviewDisabled) => {
    const onReviewJob = vi.fn();
    const tree = CaptureJobCard({ job: job("review"), reviewDisabled, voice, onReviewJob, showDebug: false });
    let review: { disabled?: boolean; onClick?: () => void } | undefined;
    function visit(node: ReactNode) {
      Children.forEach(node, (child) => {
        if (!isValidElement<{ children?: ReactNode; disabled?: boolean; onClick?: () => void }>(child)) return;
        if (child.type === "button" && child.props.children === "Review on assessment") review = child.props;
        visit(child.props.children);
      });
    }
    visit(tree);
    expect(review?.disabled).toBe(reviewDisabled);
    expect(onReviewJob).not.toHaveBeenCalled();
    if (!reviewDisabled) {
      review?.onClick?.();
      expect(onReviewJob).toHaveBeenCalledExactlyOnceWith("clip-1");
    }
    expect(voice.accept).not.toHaveBeenCalled();
  });

  it("shows the server question and primary text entry without audio or language controls", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} />);
    expect(html).toContain("Does the child have ear pain?");
    expect(html).not.toContain("ear.ear_discharge_reported");
    expect(html).toContain("Section findings");
    expect(html).toContain("Type a finding");
    expect(html).toContain("then confirm findings");
    expect(html).not.toMatch(/<details|<select|<audio|microphone|Record findings|ASR|fallback/i);
    expect(html).toContain("Process typed finding");
    expect(html).not.toContain("Transcribe audio");
  });

  it.each(["queued", "transcribing", "extracting", "preparing_review", "applying"] as const)("keeps text entry available during %s and session acceptance", (status) => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} reviewDisabled voice={{ ...voice, jobs: [job(status)] }} />);
    expect(html).toContain("Processing");
    expect(html).toContain("Reports");
    expect(html).not.toMatch(/<textarea[^>]*disabled/);
  });

  it.each(["permission", "recording", "stopping"] as const)("never exposes legacy audio controls while internal state is %s", (audioState) => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, audioState, recordingId: "other" }} />);
    expect(html).not.toMatch(/<select|<audio|microphone|record-findings|Cancel recording|Stop<\/button>/i);
    expect(html).not.toMatch(/<textarea[^>]*disabled/);
  });

  it.each(["captured", "review", "preparing_review"] as const)("routes %s evidence to assessment controls without a parallel form", (status) => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job(status)] }} />);
    expect(html).toContain("Findings populate the assessment controls");
    expect(html).toContain("Review on assessment");
    expect(html).not.toContain("Apply reviewed findings");
    expect(html).not.toContain("<select");
    expect(html).not.toMatch(/<details[^>]*open/);
  });

  it("keeps failed jobs retryable without a duplicate retraction form", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} encounter={{ ear: { ear_pain: true } }}
      voice={{ ...voice, jobs: [job("failed", { error: "Extraction unavailable" })] }} />);
    expect(html).toContain("Extraction unavailable");
    expect(html).toContain(">Retry</button>");
    expect(html).toContain(">Discard</button>");
    expect(html).not.toContain('type="checkbox"');
    expect(html).not.toContain("Review selected retractions");
  });

  it("recommends new text instead of retrying an empty failed report", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("failed", { inputText: undefined, audio: undefined })] }} />);
    expect(html).not.toContain(">Retry</button>");
    expect(html).toContain("Type a finding to try again");
    expect(html).toContain(">Discard</button>");
  });

  it("filters jobs by section, hides discarded jobs, and retains a reviewed summary", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("accepted", { changedFields: ["ear.ear_pain"] }),
      job("discarded", { id: "discarded-clip" }), job("extracting", { id: "other-section", assessment: "fever" })] }} />);
    expect(html).toContain("Reviewed changes: Ear pain");
    expect(html).not.toContain("discarded-clip");
    expect(html).not.toContain("other-section");
    expect(html).not.toContain("Correct transcript if needed");
  });

  it("pauses targeted questioning for urgent or blocked assessments without hiding text entry", () => {
    const urgent = renderToStaticMarkup(<AssessmentCapture {...props} urgent />);
    expect(urgent).not.toContain("Does the child have ear pain?");
    expect(urgent).toContain("Ordinary questions are paused");
    const blocked = renderToStaticMarkup(<AssessmentCapture {...props} reviewDisabled progress={{ ...progress, decision: "BLOCK", blockers: ["Verify child age"] }} />);
    expect(blocked).not.toContain("Does the child have ear pain?");
    expect(blocked).toContain("Verify child age");
    expect(blocked).toMatch(/<textarea[^>]*id="capture-text-ear"/);
    expect(blocked).not.toMatch(/<textarea[^>]*disabled/);
  });
});

describe("read-only source details", () => {
  it("preserves historical source words even when they mention a former provider", () => {
    const report = "Intron was mentioned in the original report.";
    const capture = job("accepted", { inputText: report, transcript: undefined });
    const before = JSON.stringify(capture);
    const html = renderToStaticMarkup(<AssessmentCapture {...props} showDebug={false} voice={{ ...voice, jobs: [capture] }} />);
    expect(html).toContain(report);
    expect(JSON.stringify(capture)).toBe(before);
  });

  it("places the immutable captured question under Details, separate from the next server question", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} progress={{ ...progress, question: { field: "ear.ear_discharge_reported", text: "New question about discharge" } }}
      voice={{ ...voice, jobs: [job("review")] }} />);
    expect(html).toContain("New question about discharge");
    expect(html).toContain("Original question about pain");
    expect(html).toContain('Submitted input (read-only)</strong><p class="trace-text">No</p>');
    expect(html.indexOf("Question at capture")).toBeGreaterThan(html.indexOf("Details: original source (read-only)"));
  });

  it("keeps original ASR, English rendering, and ambiguities immutable and secondary", () => {
    const detailed: AssessmentCandidate = { ...candidate, english_rendering: "Optional English wording", candidate_encounter: { ear: { ear_pain: null } },
      understanding: { provider: "azure_openai", model: "demo-model", request_id: "req-1", prompt_version: "v1", usage: { input_tokens: 42 } },
      uncertainties: [{ field: null, source_text: "Original ambiguous words", reason: "Unclear speaker" }],
      evidence_spans: [{ field: "ear.ear_pain", source_text: "Source words" }] };
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("review", { originalCandidate: detailed,
      transcript: { transcript: "Immutable ASR words", provider: "intron", model: null, duration_seconds: 3 } })] }} />);
    expect(html).toContain('Original ASR transcript (read-only)</strong><p class="trace-text">Immutable ASR words');
    expect(html).not.toContain("Correct transcript if needed");
    expect(html).not.toContain("Process corrected transcript");
    for (const text of ["Optional English wording", "Provider-normalized input", "nonauthoritative", "azure_openai", "Report-level uncertainty", "Unclear speaker"]) {
      expect(html).toContain(text);
    }
    expect(html).not.toMatch(/<details[^>]*open/);
  });

  it("renders only read-only content for candidate details", () => {
    const html = renderToStaticMarkup(<CandidateDetails candidate={candidate} />);
    expect(html).toContain("Original candidate (not the accepted encounter)");
    expect(html).not.toMatch(/<(input|select|textarea|button)/);
  });

  it.each(["captured", "accepted", "failed"] as const)("omits technical markup from nondebug %s reports, not just their visible surface", (status) => {
    const detailed: AssessmentCandidate = { ...candidate, input_text: "Original spoken words",
      warnings: ["Check the reported duration", 'JSON schema mismatch: {"ear.ear_pain": null} from azure_openai'], english_rendering: "Optional English words",
      candidate_encounter: { ear: { ear_pain: false } },
      understanding: { provider: "azure_openai", model: "private-model", request_id: "private-request", prompt_version: "v1", usage: { input_tokens: 42 } },
      uncertainties: [{ field: "ear.ear_pain", source_text: "Maybe pain", reason: "The answer was unclear" }],
      evidence_spans: [{ field: "ear.ear_pain", source_text: "Original source words" }],
    };
    const capture = job(status, { originalCandidate: detailed, inputText: "Original spoken words", changedFields: ["unknown.internal_field"],
      error: status === "failed" ? "Intron ASR recording could not be processed" : undefined,
      transcript: { transcript: "Original spoken words", provider: "intron", model: null, duration_seconds: 3 },
    });
    const before = JSON.stringify(capture);
    const html = renderToStaticMarkup(<AssessmentCapture {...props} showDebug={false} voice={{ ...voice, jobs: [capture] }} />);
    for (const text of ["<pre", "<code", "JSON", "schema", "ear.ear_pain", "unknown.internal_field", "candidate_encounter", "extraction_mode", "azure_openai", "private-model", "private-request", "input_tokens", "clip-1", "Optional English words", "Check the reported duration", "Original source words", "Submitted input", "Original submitted report", "Intron", "intron", "ASR", "Recording", "<select", "<audio"]) {
      expect(html).not.toContain(text);
    }
    for (const text of ["Reports", "<summary>Original report</summary>", "Original spoken words", "Original question about pain", "Please review the report and confirm the findings on the assessment.", "The answer was unclear", "Maybe pain", "Type a finding", "Process typed finding", "Section findings"]) {
      expect(html).toContain(text);
    }
    expect(html.match(/Original spoken words/g)).toHaveLength(1);
    expect(html).not.toMatch(/<details[^>]*open/);
    if (status === "failed") {
      expect(html).toContain('role="alert">Could not process these findings.');
      expect(html).toContain(">Retry</button>");
      expect(html).toContain(">Discard</button>");
    }
    if (status === "accepted") expect(html).toContain("Findings reviewed.");
    expect(JSON.stringify(capture)).toBe(before);
    const desktop = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [capture] }} />);
    expect(desktop).toBe(renderToStaticMarkup(<AssessmentCapture {...props} showDebug voice={{ ...voice, jobs: [capture] }} />));
    expect(desktop).toContain("<pre>");
    expect(desktop).toContain("private-model");
  });

  it("omits absent English and candidate internals from standalone mobile details", () => {
    const html = renderToStaticMarkup(<CandidateDetails candidate={candidate} showDebug={false} />);
    expect(html).toContain("Provider-normalized input");
    expect(html).not.toContain("English");
    expect(html).not.toContain("<pre");
    expect(html).not.toContain("Original candidate");
    expect(html).not.toContain("ear.ear_pain");
    expect(html).not.toContain("Please review the report");
  });

  it.each(["transcript", "typed", "candidate"] as const)("shows only the original %s report without normalized duplicates", (source) => {
    const capture = job("review", {
      inputText: source === "candidate" ? undefined : "Original typed words",
      transcript: source === "transcript" ? { transcript: "Original spoken words", provider: "intron", model: null, duration_seconds: 3 } : undefined,
    });
    const before = JSON.stringify(capture);
    const html = renderToStaticMarkup(<AssessmentCapture {...props} showDebug={false} voice={{ ...voice, jobs: [capture] }} />);
    const expected = source === "transcript" ? "Original spoken words" : source === "typed" ? "Original typed words" : candidate.input_text;
    expect(html.match(/<p class="trace-text">/g)).toHaveLength(1);
    expect(html).toContain(expected);
    if (source !== "candidate") expect(html).not.toContain(candidate.input_text);
    expect(JSON.stringify(capture)).toBe(before);
  });

  it("keeps standalone nondebug review needs without raw warnings or conversions", () => {
    const detailed: AssessmentCandidate = { ...candidate, warnings: ['JSON schema: {"ear.ear_pain": null}'],
      english_rendering: "Verbose English conversion", evidence_spans: [{ field: "ear.ear_pain", source_text: "Evidence dump" }],
      uncertainties: [{ field: "ear.ear_pain", reason: "Please clarify the answer", source_text: "Possibly" }] };
    const before = JSON.stringify(detailed);
    const html = renderToStaticMarkup(<CandidateDetails candidate={detailed} showDebug={false} />);
    for (const text of [candidate.input_text, "Please review the report", "Please clarify the answer", "Possibly"]) expect(html).toContain(text);
    for (const text of ["JSON", "schema", "ear.ear_pain", "Verbose English conversion", "Evidence dump"]) expect(html).not.toContain(text);
    expect(JSON.stringify(detailed)).toBe(before);
  });

  it("keeps the mobile typed question frozen and human-only through layout and revision changes", () => {
    const state = { value: { text: "" } as unknown };
    let current = { ...props, showDebug: false };
    let change: ((event: { target: { value: string } }) => void) | undefined;
    let submit: (() => void) | undefined;
    function Capture() {
      runtime.current = state;
      try {
        const tree = AssessmentCapture(current);
        function visit(node: ReactNode) {
          Children.forEach(node, (child) => {
            if (!isValidElement<{ children?: ReactNode; onChange?: typeof change; onClick?: typeof submit }>(child)) return;
            if (child.type === "textarea") change = child.props.onChange;
            if (child.type === "button" && child.props.children === "Process typed finding") submit = child.props.onClick;
            visit(child.props.children);
          });
        }
        visit(tree);
        return tree;
      } finally { runtime.current = null; }
    }
    renderToStaticMarkup(<Capture />);
    change!({ target: { value: "No ear pain" } });
    current = { ...current, revision: 3, progress: { ...progress, question: { field: "ear.ear_discharge_reported", text: "Is there discharge?" } } };
    const mobile = renderToStaticMarkup(<Capture />);
    expect(mobile).toContain("Question when typing began");
    expect(mobile).toContain("Does the child have ear pain?");
    expect(mobile).toContain("Is there discharge?");
    expect(mobile).toContain("Accepted findings changed while you were typing");
    expect(mobile).not.toContain("<code");
    expect(mobile).not.toContain("ear.ear_pain");
    current = { ...current, showDebug: true };
    expect(renderToStaticMarkup(<Capture />)).toContain("<code>ear.ear_pain</code>");
    current = { ...current, showDebug: false };
    expect(renderToStaticMarkup(<Capture />)).toBe(mobile);
    submit!();
    expect(voice.addText).toHaveBeenLastCalledWith("ear", "No ear pain", true, { encounter: {}, revision: 2, question: progress.question });
    expect(renderToStaticMarkup(<Capture />)).not.toContain("Question when typing began");
  });
});
