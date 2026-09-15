import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AssessmentCapture, CandidateDetails } from "./AssessmentCapture";
import type { CaptureJob, useVoiceCapture } from "../lib/useVoiceCapture";
import type { AssessmentCandidate, AssessmentProgress } from "../types";

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
  voice, language: "yo" as const, consent: { audio: true, understanding: true }, reviewDisabled: false, ready: true, onDirty: vi.fn(), onReviewJob: vi.fn() };
function job(status: CaptureJob["status"], overrides: Partial<CaptureJob> = {}): CaptureJob {
  return { id: "clip-1", assessment: "ear", language: "yo", status, originalEncounter: {}, originalRevision: 1,
    reviewRevision: 2, reviewVersion: 1, changedFields: [], candidate, originalCandidate: candidate,
    inputText: "No", question: { field: "ear.ear_pain", text: "Original question about pain" },
    trace: { id: "trace", timestamp: "2026-09-14T12:00:00Z", assessment: "ear", status: "candidate", source: {} }, ...overrides };
}

describe("inline capture presentation", () => {
  it("shows the server question, automatic processing instructions, and collapsed text fallback", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} />);
    expect(html).toContain("Does the child have ear pain?");
    expect(html).not.toContain("ear.ear_discharge_reported");
    expect(html).toContain("Record findings");
    expect(html).toContain("Stop to process automatically");
    expect(html).toContain("Recording does not complete an assessment");
    expect(html).toMatch(/<details class="capture-details typed-fallback"><summary>Type a finding instead/);
    expect(html).toContain("Process typed finding");
    expect(html).not.toContain("Transcribe audio");
  });

  it.each(["queued", "transcribing", "extracting", "preparing_review", "applying"] as const)("keeps recording available during %s and session acceptance", (status) => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} reviewDisabled voice={{ ...voice, jobs: [job(status)] }} />);
    expect(html).toContain("Processing /");
    expect(html).not.toMatch(/class="record-findings"[^>]*disabled/);
  });

  it.each(["permission", "recording", "stopping"] as const)("disables another section's microphone while the mic is %s", (audioState) => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, audioState, recordingId: "other" }} />);
    expect(html).toMatch(/class="record-findings"[^>]*disabled/);
  });

  it.each([{ audio: false, understanding: true }, { audio: true, understanding: false }])("requires both consents before recording", (consent) => {
    expect(renderToStaticMarkup(<AssessmentCapture {...props} consent={consent} />)).toMatch(/class="record-findings"[^>]*disabled/);
  });

  it("requires a language and switches the active section control to Stop", () => {
    expect(renderToStaticMarkup(<AssessmentCapture {...props} language="" />)).toMatch(/class="record-findings"[^>]*disabled/);
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("recording")], recordingId: "clip-1", audioState: "recording" }} />);
    expect(html).toContain("Stop</button>");
    expect(html).toContain("Cancel recording");
    expect(html).not.toContain("Record findings");
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

  it("recommends recording again instead of retrying an empty failed capture", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("failed", { inputText: undefined, audio: undefined })] }} />);
    expect(html).not.toContain(">Retry</button>");
    expect(html).toContain("Record again or type a finding instead");
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

  it("pauses targeted questioning for urgent or blocked assessments without hiding fallback", () => {
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
});
