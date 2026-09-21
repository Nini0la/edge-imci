import { afterEach, describe, expect, it, vi } from "vitest";
import { acceptAssessment, evaluateAssessment, extractAssessment, extractFindings, prepareAssessmentReview, transcribeAudio } from "./api";
import type { AssessmentCandidate } from "../types";

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("assessment API contract", () => {
  it("routes full notes through sparse assessment APIs without a follow-up or changing native extraction", async () => {
    const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response("{}")));
    vi.stubGlobal("fetch", fetch);
    const encounter = { ear: { ear_pain: false } };
    const candidate: AssessmentCandidate = { assessment: "full-note", input_text: "Report", extraction_mode: "frontier", warnings: [],
      changes: [{ field: "patient_facts.has_fever", label: "Fever", previous: null, value: true, conflict: false, outside_assessment: false }],
      candidate_encounter: { ear: { ear_pain: null } } };
    await extractAssessment("full-note", "Report", encounter, "ear.ear_pain");
    await prepareAssessmentReview("full-note", encounter, candidate.changes);
    await acceptAssessment(candidate, encounter, {}, ["fever"]);
    await extractFindings("Native report");
    expect(fetch.mock.calls.map(([url]) => url)).toEqual(["/api/assessment/extract", "/api/assessment/review", "/api/assessment/accept", "/api/extract"]);
    expect(fetch.mock.calls.map(([, options]) => JSON.parse(options.body))).toEqual([
      { assessment: "full-note", findings: "Report", encounter },
      { assessment: "full-note", encounter, changes: candidate.changes },
      { assessment: "full-note", encounter, changes: candidate.changes, resolutions: {}, confirmed: true, attempted: ["fever"] },
      { findings: "Native report" },
    ]);
    expect(encounter).toEqual({ ear: { ear_pain: false } });
  });

  it("prepares review with the latest encounter and original proposed rows, preserving changed and same-value rows", async () => {
    const encounter = { respiratory: { respiratory_rate: 42 }, ear: { ear_pain: null } };
    const changes = [
      { field: "respiratory.respiratory_rate", label: "Respiratory rate", previous: 42, value: 42, conflict: false, outside_assessment: false },
      { field: "ear.ear_pain", label: "Ear pain", previous: true, value: false, conflict: true, outside_assessment: true },
    ];
    const original = structuredClone({ encounter, changes });
    const review = { changes: [changes[0], { ...changes[1], previous: null, review_changed: true }], changed_fields: ["ear.ear_pain"] };
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(review)));
    vi.stubGlobal("fetch", fetch);
    expect(await prepareAssessmentReview("respiratory", encounter, changes)).toEqual(review);
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith("/api/assessment/review", expect.objectContaining({
      method: "POST", headers: { "Content-Type": "application/json" }, signal: expect.any(AbortSignal),
    }));
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ assessment: "respiratory", encounter, changes });
    expect({ encounter, changes }).toEqual(original);
  });

  it("forwards review cancellation and surfaces review errors without an accept request", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "Invalid review rows" }), { status: 400 }));
    vi.stubGlobal("fetch", fetch);
    await expect(prepareAssessmentReview("ear", {}, [])).rejects.toThrow("Invalid review rows");
    fetch.mockImplementation((_url, options: RequestInit) => new Promise((_resolve, reject) => {
      options.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }));
    const controller = new AbortController();
    const request = prepareAssessmentReview("ear", {}, [], controller.signal);
    const assertion = expect(request).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();
    await assertion;
    expect(fetch.mock.calls[1][1].signal.aborted).toBe(true);
    expect(fetch.mock.calls.map(([url]) => url)).toEqual(["/api/assessment/review", "/api/assessment/review"]);
  });

  it("rejects missing or unsupported languages without sending audio", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    for (const language of ["", "fr", undefined]) {
      await expect(transcribeAudio(new Blob(["audio"]), language as never)).rejects.toThrow("Select a language");
    }
    expect(fetch).not.toHaveBeenCalled();
  });
  it("sends raw audio and its MIME type, never credentials or JSON-wrapped audio", async () => {
    const payload = { transcript: "No ear pain", provider: "intron", model: null, duration_seconds: null };
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload)));
    vi.stubGlobal("fetch", fetch);
    const audio = new Blob(["audio"], { type: "audio/mp4" });
    expect(await transcribeAudio(audio, "yo")).toEqual(payload);
    expect(fetch).toHaveBeenCalledWith("/api/transcribe", expect.objectContaining({ body: audio, headers: { "Content-Type": "audio/mp4", "X-EdgeIMCI-ASR-Language": "yo" } }));
  });

  it("bounds transcription to 110 seconds", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_url, options: RequestInit) => new Promise((_resolve, reject) => {
      options.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    })));
    const response = transcribeAudio(new Blob(["audio"], { type: "audio/webm" }), "en");
    const assertion = expect(response).rejects.toThrow("timed out");
    await vi.advanceTimersByTimeAsync(110_000);
    await assertion;
  });

  it("forwards cancellation and safe server errors", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "Speech provider unavailable" }), { status: 503 }));
    vi.stubGlobal("fetch", fetch);
    await expect(transcribeAudio(new Blob(["audio"], { type: "audio/ogg" }), "ig")).rejects.toThrow("Speech provider unavailable");
    fetch.mockImplementation((_url, options: RequestInit) => new Promise((_resolve, reject) => {
      options.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }));
    const controller = new AbortController();
    const response = transcribeAudio(new Blob(["audio"], { type: "audio/ogg" }), "ha", controller.signal);
    const assertion = expect(response).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();
    await assertion;
  });

  it("passes stable question IDs and explicit resolutions without mutating the encounter", async () => {
    const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response("{}")));
    vi.stubGlobal("fetch", fetch);
    const encounter = { patient_facts: { age_months: 24 } };
    await evaluateAssessment();
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ attempted: [] });
    await extractAssessment("danger", "No", encounter, "danger_signs.convulsing_now");
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ assessment: "danger", findings: "No", encounter, question_field: "danger_signs.convulsing_now" });
    const candidate: AssessmentCandidate = { assessment: "danger", input_text: "No", extraction_mode: "modal", changes: [], warnings: [] };
    await acceptAssessment(candidate, encounter, { "danger_signs.convulsing_now": "unknown" }, ["danger"]);
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({ assessment: "danger", encounter, changes: [], resolutions: { "danger_signs.convulsing_now": "unknown" }, confirmed: true, attempted: ["danger"] });
    expect(encounter).toEqual({ patient_facts: { age_months: 24 } });
  });

  it("retains additive language metadata but accepts only reviewed changes, not report-only canonical data", async () => {
    const candidate: AssessmentCandidate = { assessment: "ear", input_text: "Provider normalized", extraction_mode: "frontier", warnings: [],
      changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: null, value: null, uncertain: true, conflict: false, outside_assessment: false }],
      candidate_encounter: { ear: { ear_pain: null } }, english_rendering: "Unclear ear pain",
      uncertainties: [{ field: "ear.ear_pain", source_text: "Original words", reason: "Ambiguous" }],
      evidence_spans: [], understanding: { provider: "azure_openai", model: "demo-model", request_id: "request-1", prompt_version: "v1", usage: { input_tokens: 10 } } };
    const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(candidate))));
    vi.stubGlobal("fetch", fetch);
    const encounter = { ear: { ear_pain: null } };
    expect(await extractAssessment("ear", "Worker edited words", encounter)).toEqual(candidate);
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ assessment: "ear", findings: "Worker edited words", encounter });
    await acceptAssessment(candidate, encounter, { "ear.ear_pain": "keep" }, ["ear"]);
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ assessment: "ear", encounter, changes: candidate.changes,
      resolutions: { "ear.ear_pain": "keep" }, confirmed: true, attempted: ["ear"] });
  });
});
