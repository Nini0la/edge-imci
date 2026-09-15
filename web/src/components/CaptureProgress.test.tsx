import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { buildChecklist } from "../lib/checklist";
import type { CaptureJob } from "../lib/useVoiceCapture";
import { CaptureProgress } from "./CaptureProgress";

const sections = buildChecklist({}).sections;
function job(status: CaptureJob["status"], overrides: Partial<CaptureJob> = {}): CaptureJob {
  return { id: "private-recording-id", assessment: "danger", language: "pcm", status, originalEncounter: {}, originalRevision: 0,
    reviewVersion: 0, changedFields: [], trace: { id: "private-trace", assessment: "danger", timestamp: "today", status: "candidate", source: {} },
    ...overrides };
}

describe("recording progress", () => {
  it.each([
    ["queued", "Waiting to process your findings"],
    ["transcribing", "Turning your recording into text"],
    ["extracting", "Adding your findings to the assessment"],
    ["preparing_review", "Getting your findings ready for review"],
    ["applying", "Confirming your findings"],
  ] as const)("shows the actual %s stage, with movement but no premature review or fake percentage", (status, message) => {
    const onReview = vi.fn();
    const html = renderToStaticMarkup(<CaptureProgress jobs={[job(status)]} sections={sections} onReview={onReview} />);
    expect(html).toContain(message);
    expect(html).toContain("General danger signs");
    expect(html).toContain('data-busy="true"');
    expect(html).toMatch(/class="[^"]*\bcapture-progress__spinner\b/);
    for (const hidden of ["<button", "Ready for your review", "%", "private-", "<pre", "<code"]) expect(html).not.toContain(hidden);
    expect(onReview).not.toHaveBeenCalled();
  });

  it.each(["captured", "review"] as const)("distinguishes %s findings ready for review from confirmed evidence", (status) => {
    const html = renderToStaticMarkup(<CaptureProgress jobs={[job(status)]} sections={sections} onReview={vi.fn()} />);
    expect(html).toContain("Ready for your review");
    expect(html).toContain("Check the answers before confirming");
    expect(html).toContain('data-busy="false"');
    expect(html).toContain(">Review</button>");
    expect(html).not.toContain("capture-progress__spinner");
    expect(html).not.toContain("Assessment complete");
  });

  it.each(["failed", "captured", "review"] as const)("shows recoverable attention instead of a spinner or success for %s errors", (status) => {
    const html = renderToStaticMarkup(<CaptureProgress jobs={[job(status, { error: "private-service JSON error" })]} sections={sections} onReview={vi.fn()} />);
    expect(html).toContain("Your findings need attention");
    expect(html).toContain("Open to retry or review");
    expect(html).toContain(status === "failed" ? ">View recording</button>" : ">Review</button>");
    for (const hidden of ["capture-progress__spinner", "Ready for your review", "private-service", "JSON"]) expect(html).not.toContain(hidden);
  });

  it("tracks concurrent recordings independently without replacing ready or failed work with another job's stage", () => {
    const jobs = [job("transcribing"), job("extracting", { id: "two", assessment: "ear" }), job("queued", { id: "three", assessment: "fever" }),
      job("review", { id: "four", assessment: "respiratory" }), job("failed", { id: "five", assessment: "diarrhoea" })];
    const original = structuredClone(jobs);
    const html = renderToStaticMarkup(<CaptureProgress jobs={jobs} sections={sections} onReview={vi.fn()} />);
    expect(html.match(/class="capture-progress__item"/g)).toHaveLength(5);
    expect(html.match(/class="[^"]*\bcapture-progress__spinner\b/g)).toHaveLength(3);
    expect(html.match(/<button/g)).toHaveLength(2);
    for (const section of sections) expect(html).toContain(section.label);
    expect(jobs).toEqual(original);
  });

  it("keeps an empty announcement region without showing recording, accepted, discarded, or direct-entry work as processing", () => {
    const jobs = [job("recording"), job("accepted"), job("discarded"), job("captured", {
      originalCandidate: { assessment: "danger", input_text: "Direct entry", extraction_mode: "worker-review", changes: [], warnings: [] },
    })];
    const render = (jobs: CaptureJob[]) => renderToStaticMarkup(<CaptureProgress jobs={jobs} sections={sections} onReview={vi.fn()} />);
    expect(render(jobs)).toBe(render([]));
    expect(render([])).toBe('<section class="capture-progress" aria-label="Recording progress" aria-live="polite" aria-atomic="false"></section>');
  });
});
