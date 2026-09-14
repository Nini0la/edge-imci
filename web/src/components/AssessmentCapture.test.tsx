import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AssessmentCapture, CandidateReview, CaptureInput } from "./AssessmentCapture";
import type { AssessmentCandidate, AssessmentProgress } from "../types";

const progress: AssessmentProgress = {
  status: "INCOMPLETE", decision: "ASK", missing_fields: ["ear.ear_pain", "ear.ear_discharge_reported"],
  question: { field: "ear.ear_pain", text: "Does the child have ear pain?" }, blockers: [],
};
const props = {
  assessment: "ear" as const, encounter: {}, revision: 2, progress, urgent: false, disabled: false,
  onBusy: vi.fn(), onPending: vi.fn(), onAccept: vi.fn().mockResolvedValue(true),
  onRecordInteraction: vi.fn(),
};

describe("inline assessment capture", () => {
  it("offers independent accepted-field retraction when there is no extraction candidate or extraction has failed", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} serviceError="Extraction unavailable"
      encounter={{ patient_facts: { age_months: 24, has_ear_problem: false }, ear: { ear_pain: true } }} />);
    expect(html).toContain("Extraction unavailable");
    expect(html).toContain('aria-label="Review accepted evidence"');
    expect(html).toContain("patient_facts.age_months");
    expect(html).toContain("ear.ear_pain");
    expect(html).toContain("Mark UNKNOWN (null)");
    expect(html).toContain("Confirm selected retractions to UNKNOWN");
    expect(html).not.toContain("Review proposed findings");
  });

  it("shows only the server's next question and discloses both providers", () => {
    const html = renderToStaticMarkup(<AssessmentCapture {...props} />);
    expect(html).toContain("Does the child have ear pain?");
    expect(html).not.toContain("ear.ear_discharge_reported");
    expect(html).toContain("Audio is sent to Intron");
    expect(html).toContain("configured language-understanding service (Azure OpenAI in demo mode)");
    expect(html).toContain("External Azure receives the transcript and current canonical encounter");
    expect(html).toContain("I agree to send this section text/transcript");
    expect(html).not.toContain("Modal");
    expect(html).not.toContain("chat");
    expect(html).toContain("Select for each transcription request");
    for (const language of ["en", "pcm", "yo", "ig", "ha"]) expect(html).toContain(`value="${language}"`);
    expect(html).toContain("Research/demo only");
    expect(html).toContain("Recording does not complete an assessment");
  });

  it("keeps raw ASR, edited input, normalized provider input, and optional English independent", () => {
    const candidate: AssessmentCandidate = {
      assessment: "ear", input_text: "Provider-normalized input", extraction_mode: "frontier", warnings: [], changes: [],
      english_rendering: "Optional English wording", candidate_encounter: { ear: { ear_pain: null } },
      understanding: { provider: "azure_openai", model: "demo-model", request_id: "req-1", prompt_version: "v1", usage: { input_tokens: 42 } },
      uncertainties: [{ field: null, source_text: "Original ambiguous words", reason: "Unclear speaker" }],
      evidence_spans: [{ field: "ear.ear_pain", source_text: "Source words" }],
    };
    const html = renderToStaticMarkup(<><CaptureInput assessment="ear" rawTranscript="Immutable ASR words" text="Worker edited words" disabled={false} onChange={vi.fn()} />
      <CandidateReview candidate={candidate} resolutions={{}} busy={false} onResolve={vi.fn()} /></>);
    expect(html).toMatch(/<textarea[^>]*id="capture-raw-ear"[^>]*readOnly[^>]*>Immutable ASR words<\/textarea>/);
    expect(html).toMatch(/<textarea[^>]*id="capture-text-ear"[^>]*>Worker edited words<\/textarea>/);
    expect(html).toContain("Optional English wording");
    expect(html).not.toContain("Provider-normalized input");
    expect(html).toContain("nonauthoritative");
    expect(html).toContain("azure_openai / demo-model");
    expect(html).toContain("Report-level uncertainty");
    expect(html).toContain("Unclear speaker");
    expect(html).toMatch(/<details[^>]*><summary>Language review/);
    expect(html).not.toMatch(/<details[^>]*open/);
  });

  it("does not default uncertain null-to-null rows to inclusion or false", () => {
    const candidate: AssessmentCandidate = { assessment: "ear", input_text: "Unsure", extraction_mode: "frontier", warnings: [],
      changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: null, value: null, uncertain: true, conflict: false, outside_assessment: false }] };
    const html = renderToStaticMarkup(<CandidateReview candidate={candidate} resolutions={{}} busy={false} onResolve={vi.fn()} />);
    expect(html).toContain("Ambiguous / unknown, not a negative finding");
    expect(html).toMatch(/<option value="" disabled="" selected="">Choose before applying/);
    expect(html).not.toContain("Proposed: false");
    expect(html).toContain("keep explicitly reaffirms the accepted value");
    expect(html).toContain("No English rendering supplied");
  });

  it("pauses questioning for urgent or blocked assessments without hiding errors or text fallback", () => {
    const urgent = renderToStaticMarkup(<AssessmentCapture {...props} urgent serviceError="Service unavailable" />);
    expect(urgent).not.toContain("Does the child have ear pain?");
    expect(urgent).toContain("Ordinary questions are paused");
    expect(urgent).toContain("Service unavailable");
    const blocked = renderToStaticMarkup(<AssessmentCapture {...props} disabled progress={{ ...progress, decision: "BLOCK", blockers: ["Verify child age"] }} />);
    expect(blocked).not.toContain("Does the child have ear pain?");
    expect(blocked).toContain("Verify child age");
    expect(blocked).toMatch(/<textarea[^>]*id="capture-text-ear"/);
    expect(blocked).not.toMatch(/<textarea[^>]*disabled/);
  });
});
