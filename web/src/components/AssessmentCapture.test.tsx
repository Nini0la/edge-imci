import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AssessmentCapture, CandidateReview } from "./AssessmentCapture";
import type { CaptureJob, useVoiceCapture } from "../lib/useVoiceCapture";
import type { AssessmentCandidate, AssessmentChange, AssessmentProgress } from "../types";

const progress: AssessmentProgress = {
  status: "INCOMPLETE", decision: "ASK", missing_fields: ["ear.ear_pain", "ear.ear_discharge_reported"],
  question: { field: "ear.ear_pain", text: "Does the child have ear pain?" }, blockers: [],
};
const candidate: AssessmentCandidate = { assessment: "ear", input_text: "Provider-normalized input", extraction_mode: "frontier", warnings: [],
  changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: null, value: false, conflict: false, outside_assessment: false }] };
const voice: ReturnType<typeof useVoiceCapture> = {
  jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
  addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
  retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(),
};
const props = { assessment: "ear" as const, encounter: {}, revision: 2, progress, urgent: false,
  voice, language: "yo" as const, consent: { audio: true, understanding: true }, reviewDisabled: false, ready: true, onDirty: vi.fn() };
function job(status: CaptureJob["status"], overrides: Partial<CaptureJob> = {}): CaptureJob {
  return { id: "clip-1", assessment: "ear", language: "yo", status, originalEncounter: {}, originalRevision: 1,
    reviewRevision: 2, reviewVersion: 1, changedFields: [], candidate,
    inputText: "No", question: { field: "ear.ear_pain", text: "Original question about pain" },
    trace: { id: "trace", timestamp: "2026-09-14T12:00:00Z", assessment: "ear", status: "candidate", source: {} }, ...overrides };
}

describe("inline capture presentation", () => {
  it("shows one server question, automatic processing instructions, and collapsed optional text fallback", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} />);
    expect(html).toContain("Does the child have ear pain?");
    expect(html).not.toContain("ear.ear_discharge_reported");
    expect(html).toContain("Record findings");
    expect(html).toContain("Stop to process automatically");
    expect(html).toContain("Recording does not complete an assessment");
    expect(html).toMatch(/<details class="capture-details typed-fallback"><summary>Type a finding instead/);
    expect(html).toContain("Process typed finding");
    expect(html).not.toContain("Transcribe audio");
    expect(html).not.toContain("Interpret section findings");
    expect(html).not.toContain("editable transcript");
  });

  it.each(["queued", "transcribing", "extracting", "preparing_review", "applying"] as const)("keeps recording available during %s and session acceptance", (status) => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} reviewDisabled voice={{ ...voice, jobs: [job(status)] }} />);
    expect(html).toContain("Processing /");
    expect(html).not.toMatch(/class="record-findings"[^>]*disabled/);
  });

  it.each(["permission", "recording", "stopping"] as const)("disables another section's microphone only while the mic is %s", (audioState) => {
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

  it("shows captured evidence without automatically opening review or applying it", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("captured")] }} />);
    expect(html).toContain("Captured / awaiting review");
    expect(html).toContain("Ear pain: <strong>false</strong>");
    expect(html).toContain("Not accepted");
    expect(html).toContain("Review captured findings");
    expect(html).not.toContain("Apply reviewed findings");
    expect(html).not.toMatch(/<details[^>]*open/);
  });

  it("keeps failed jobs retryable and accepted evidence independently retractable", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props}
      encounter={{ patient_facts: { age_months: 24, has_ear_problem: false }, ear: { ear_pain: true } }}
      voice={{ ...voice, jobs: [job("failed", { error: "Extraction unavailable" })] }} />);
    expect(html).toContain("Extraction unavailable");
    expect(html).toContain(">Retry</button>");
    expect(html).toContain(">Discard</button>");
    expect(html).toContain('aria-label="Reviewed observations"');
    expect(html).toContain("patient_facts.age_months");
    expect(html).toContain("ear.ear_pain");
    expect(html).toContain("Mark UNKNOWN (null)");
    expect(html).toContain("Review selected retractions");
    expect(html).not.toContain("Confirm selected retractions");
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

describe("explicit job review", () => {
  it("discloses changed acceptance context even when no proposed fields changed", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("review", { changedFields: [], candidate: { ...candidate, changes: [] } })] }} />);
    expect(html).toContain("Acceptance context changed since capture");
    expect(html).toContain("original captured question remains binding");
    expect(html).toContain("even if no proposed fields changed");
    expect(html).toContain("Original question about pain");
  });
  it("displays the immutable captured question and source separately from the next server question", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} progress={{ ...progress, question: { field: "ear.ear_discharge_reported", text: "New question about discharge" } }}
      voice={{ ...voice, jobs: [job("review")] }} />);
    expect(html).toContain("New question about discharge");
    expect(html).toContain("Question at capture");
    expect(html).toContain("Original question about pain");
    expect(html).toContain("Captured source (read-only)</strong><q>No</q>");
    expect(html).not.toContain("Provider-normalized input");
  });

  it("disables stale Apply and asks for review again against the latest revision", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} revision={3} voice={{ ...voice, jobs: [job("review")] }} />);
    expect(html).toContain("Accepted findings changed. Review again");
    expect(html).toContain(">Review again</button>");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Apply reviewed findings/);
    expect(html).toMatch(/<select[^>]*disabled/);
  });

  it("allows an ordinary proposal only through the final explicit Apply button", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("review")] }} />);
    expect(html).toContain('<option value="replace" selected="">');
    expect(html).toContain('<button type="button">Apply reviewed findings</button>');
    expect(html).toContain("Not yet accepted. Check every value");
  });

  it.each([{ value: null, previous: null, uncertain: true }, { conflict: true }, { outside_assessment: true },
    { review_changed: true, previous: false, value: false }, { review_changed: true, previous: null, value: null }] as Partial<AssessmentChange>[])("requires a fresh explicit choice for guarded rows: %j", (change) => {
    const guarded = { ...candidate, changes: [{ ...candidate.changes[0], ...change }] };
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("review", { candidate: guarded })] }} />);
    expect(html).toContain('<option value="" disabled="" selected="">Choose before applying');
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Apply reviewed findings/);
    if (change.review_changed) expect(html).toContain("Reconfirm your choice even if the latest value matches");
  });

  it.each(["keep", "replace", "unknown"] as const)("preserves an explicit %s choice", (resolution) => {
    const html = renderToStaticMarkup(<CandidateReview candidate={{ ...candidate, changes: [{ ...candidate.changes[0], review_changed: true }] }}
      resolutions={{ "ear.ear_pain": resolution }} busy={false} onResolve={vi.fn()} />);
    expect(html).toContain(`<option value="${resolution}" selected="">`);
  });

  it("keeps original ASR, optional correction, English rendering, and ambiguities distinct", () => {
    const detailed: AssessmentCandidate = { ...candidate, english_rendering: "Optional English wording", candidate_encounter: { ear: { ear_pain: null } },
      understanding: { provider: "azure_openai", model: "demo-model", request_id: "req-1", prompt_version: "v1", usage: { input_tokens: 42 } },
      uncertainties: [{ field: null, source_text: "Original ambiguous words", reason: "Unclear speaker" }],
      evidence_spans: [{ field: "ear.ear_pain", source_text: "Source words" }] };
    const html = renderToStaticMarkup(<AssessmentCapture {...props} voice={{ ...voice, jobs: [job("review", { candidate: detailed, inputText: "Worker edited words",
      transcript: { transcript: "Immutable ASR words", provider: "intron", model: null, duration_seconds: 3 } })] }} />);
    expect(html).toContain("Original ASR transcript (read-only)</strong><p class=\"trace-text\">Immutable ASR words");
    expect(html).toContain("Submitted input (read-only)</strong><p class=\"trace-text\">Worker edited words");
    expect(html).toMatch(/<details class="capture-details"><summary>Correct transcript if needed/);
    expect(html).toContain("Process corrected transcript");
    expect(html).toContain("Retrying/correcting this clip uses its original processing permission");
    expect(html).toContain("record another clip instead");
    expect(html).toContain("Optional English wording");
    expect(html).not.toContain("Provider-normalized input");
    expect(html).toContain("nonauthoritative");
    expect(html).toContain("azure_openai / demo-model");
    expect(html).toContain("Report-level uncertainty");
    expect(html).toContain("Unclear speaker");
    expect(html).not.toMatch(/<details[^>]*open/);
  });
});
