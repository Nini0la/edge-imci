import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ASRLanguage, AssessmentCandidate, AssessmentChange, AssessmentEvaluation, AssessmentId, Transcription } from "../types";
import type { extractAssessment, prepareAssessmentReview, transcribeAudio } from "./api";
import type { createAudioCapture } from "./audio";
import type { useAssessmentSession } from "./useAssessmentSession";
import { createVoiceCapture } from "./useVoiceCapture";

type Session = ReturnType<typeof useAssessmentSession>;
type State = Parameters<Parameters<typeof createVoiceCapture>[0]["onChange"]>[0];
type Review = Awaited<ReturnType<typeof prepareAssessmentReview>>;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

// Public recording/text methods are void; drain their short async processing chain.
async function flush() { for (let i = 0; i < 8; i += 1) await Promise.resolve(); }

function row(field = "ear.ear_pain", value: unknown = true, previous: unknown = null): AssessmentChange {
  return { field, label: field, value, previous, conflict: false, outside_assessment: false };
}

function candidate(assessment: AssessmentId = "ear", changes = [row()], input_text = "Finding"): AssessmentCandidate {
  return { assessment, input_text, changes, extraction_mode: "test", warnings: [] };
}

function transcript(text = "Spoken finding"): Transcription {
  return { transcript: text, provider: "intron", model: null, duration_seconds: 1 };
}

function evaluation(encounter: Record<string, unknown>): AssessmentEvaluation {
  const progress = { status: "INCOMPLETE" as const, decision: "ASK" as const, missing_fields: [], blockers: [], question: null };
  return {
    encounter,
    analysis: { input_text: "", extraction_mode: "test", matched_case_id: null, structured_encounter: encounter, structured_view: [],
      schema_valid: true, extraction_warnings: [], is_complete: false, missing_elements: {}, contradictions: [], is_urgent: false,
      classifications: [], urgent_actions: [], final_actions: [], deferred_actions: [], rendered_response: "Incomplete",
      decision_trace: [], pipeline_trace: [], error: null, outside_supported_scope: false, state: "INCOMPLETE" },
    assessments: { danger: { ...progress }, respiratory: { ...progress }, diarrhoea: { ...progress }, fever: { ...progress },
      ear: { ...progress, question: { field: "ear.ear_pain", text: "Does the child have ear pain?" } } },
  };
}

function setup(encounter: Record<string, unknown> = {}) {
  let state: State = { jobs: [], recordingId: null, audioState: "idle", error: "" };
  let audioCallbacks!: Parameters<typeof createAudioCapture>[0];
  const audio = new Blob(["synthetic audio"], { type: "audio/webm" });
  const microphone = {
    record: vi.fn(async () => { audioCallbacks.state("permission"); audioCallbacks.state("recording"); }),
    stop: vi.fn(() => { audioCallbacks.state("stopping"); audioCallbacks.state("idle"); audioCallbacks.audio(audio); }),
    cancel: vi.fn(() => { audioCallbacks.state("idle"); }),
  };
  const audioFactory = vi.fn<typeof createAudioCapture>((callbacks) => { audioCallbacks = callbacks; return microphone; });
  const asr: ReturnType<typeof deferred<Transcription>>[] = [];
  const extracts: ReturnType<typeof deferred<AssessmentCandidate>>[] = [];
  const reviews: ReturnType<typeof deferred<Review>>[] = [];
  const applies: ReturnType<typeof deferred<boolean>>[] = [];
  const transcribe = vi.fn<typeof transcribeAudio>(() => { const request = deferred<Transcription>(); asr.push(request); return request.promise; });
  const extract = vi.fn<typeof extractAssessment>(() => { const request = deferred<AssessmentCandidate>(); extracts.push(request); return request.promise; });
  const prepare = vi.fn<typeof prepareAssessmentReview>(() => { const request = deferred<Review>(); reviews.push(request); return request.promise; });
  const recordInteraction = vi.fn<Session["recordInteraction"]>((trace) => {
    session.interactions = [...session.interactions.filter((entry) => entry.id !== trace.id), structuredClone(trace)];
  });
  const accept = vi.fn<Session["accept"]>(async (proposal, resolutions, revision, trace) => {
    if (session.busy || revision !== session.revision) return false;
    const epoch = session.revision;
    session.busy = true;
    const request = deferred<boolean>();
    applies.push(request);
    const accepted = await request.promise;
    if (epoch !== session.revision) return false;
    session.busy = false;
    if (!accepted) {
      if (trace) recordInteraction({ ...trace, candidate: proposal, resolutions, status: "failed", pending: false, error: "Synthetic acceptance failure" });
      return false;
    }
    // Simulate the backend's row-wise merge, never the report-only candidate encounter.
    const next = structuredClone(session.encounter);
    for (const change of proposal.changes) {
      if (resolutions[change.field] === "keep") continue;
      const [section, field] = change.field.split(".");
      const fields = (next[section] ??= {}) as Record<string, unknown>;
      fields[field] = resolutions[change.field] === "unknown" ? null : change.value;
    }
    commit(next);
    if (trace) recordInteraction({ ...trace, candidate: proposal, resolutions, status: "accepted", pending: false, result: session.evaluation! });
    return true;
  });
  const session: Session = {
    version: 1, encounter: structuredClone(encounter), attempted: [], revision: 10, interactions: [],
    evaluation: evaluation(structuredClone(encounter)), hasData: true, busy: false, error: "", storageHint: "", ready: true,
    currentRevision: () => session.revision,
    interruptedCount: 0, acknowledgeInterrupted: vi.fn(),
    snapshot: () => ({ encounter: session.encounter, revision: session.revision, evaluation: session.evaluation, interactions: session.interactions }),
    recordInteraction, accept, refresh: vi.fn(async () => true), evaluate: vi.fn(async () => true), rejectPending: vi.fn(),
    reset: vi.fn(() => { commit({}); session.interactions = []; session.busy = false; }),
  };
  function commit(next: Record<string, unknown>) {
    session.encounter = structuredClone(next);
    session.revision += 1;
    session.evaluation = evaluation(session.encounter);
  }
  const capture = createVoiceCapture({ getSession: () => session, onChange: (next) => { state = next; }, transcribe, extract, prepare, audioFactory });
  const latest = () => state.jobs[state.jobs.length - 1];
  function record(assessment: AssessmentId = "ear", language: ASRLanguage = "yo") {
    capture.startRecording(assessment, language, { audio: true, understanding: true });
    const id = latest().id;
    capture.stop();
    return id;
  }
  function text(assessment: AssessmentId = "ear", input = "Typed finding") {
    capture.addText(assessment, input, true);
    return latest().id;
  }
  async function captured(proposal = candidate()) {
    const id = text(proposal.assessment, proposal.input_text);
    extracts[extracts.length - 1].resolve(proposal);
    await flush();
    return id;
  }
  async function reviewed(id: string, changes = state.jobs.find((job) => job.id === id)!.originalCandidate!.changes, changed_fields: string[] = []) {
    const pending = capture.prepareReview(id);
    reviews[reviews.length - 1].resolve({ changes, changed_fields });
    await pending;
  }
  return { capture, session, commit, record, text, captured, reviewed, latest, state: () => state,
    job: (id: string) => state.jobs.find((job) => job.id === id)!, callbacks: () => audioCallbacks,
    audio, audioFactory, microphone, transcribe, extract, prepare, accept, recordInteraction, asr, extracts, reviews, applies };
}

beforeEach(() => { vi.stubGlobal("fetch", vi.fn(() => { throw new Error("Unexpected network call"); })); });
afterEach(() => { vi.unstubAllGlobals(); });

describe("voice capture controller", () => {
  it("keeps typed drafts bound to their editing context, not the later question", async () => {
    const h = setup();
    const context = { encounter: structuredClone(h.session.encounter), revision: h.session.revision,
      question: h.session.evaluation!.assessments.ear.question! };
    h.commit({ ear: { ear_pain: true } });
    h.session.evaluation!.assessments.ear.question = { field: "ear.tender_swelling_behind_ear", text: "Is there swelling?" };
    expect(h.capture.addText("ear", "Yes", true, context)).toBe(true);
    expect(h.extract.mock.calls[0]).toEqual(["ear", "Yes", {}, "ear.ear_pain", expect.any(AbortSignal)]);
    expect(h.latest().originalRevision).toBe(context.revision);
    expect(h.latest().question).toEqual(context.question);
    h.extracts[0].resolve(candidate()); await flush();
    const unbound = { encounter: h.session.encounter, revision: h.session.revision };
    expect(h.capture.addText("ear", "A report begun before initialization", true, unbound)).toBe(true);
    expect(h.extract.mock.calls[1][3]).toBeUndefined();
  });

  it("reports enqueue failure so a pre-evaluation typed draft is not cleared", () => {
    const h = setup(); h.session.evaluation = null;
    expect(h.capture.addText("ear", "Keep my draft", true)).toBe(false);
    expect(h.state().jobs).toHaveLength(0);
    expect(h.extract).not.toHaveBeenCalled();
  });

  it("preserves failed acceptance receipts when applying again or discarding", async () => {
    const h = setup(); const id = await h.captured(); await h.reviewed(id);
    const first = h.capture.accept(id, {}); h.applies[0].resolve(false); await first;
    const failed = structuredClone(h.session.interactions[0]);
    expect(h.job(id).trace).toMatchObject({ status: "failed", error: "Synthetic acceptance failure" });
    const second = h.capture.accept(id, {}); h.applies[1].resolve(true); await second;
    expect(h.session.interactions).toHaveLength(2);
    expect(h.session.interactions[0]).toEqual(failed);
    expect(h.session.interactions[1].status).toBe("accepted");
    expect(h.session.interactions[1].id).not.toBe(failed.id);
    const another = await h.captured(); await h.reviewed(another);
    const applying = h.capture.accept(another, {}); h.applies[2].resolve(false); await applying;
    const receipt = structuredClone(h.session.interactions.at(-1));
    h.capture.discard(another);
    expect(h.session.interactions.at(-1)).toEqual(receipt);
  });

  it("automatically transcribes then extracts on Stop, but never prepares or accepts automatically", async () => {
    const h = setup();
    h.capture.startRecording("ear", "yo", { audio: true, understanding: true });
    const id = h.latest().id;
    expect(h.state()).toMatchObject({ recordingId: id, audioState: "recording" });
    expect(h.transcribe).not.toHaveBeenCalled();
    h.capture.stop();
    expect(h.state()).toMatchObject({ recordingId: null, audioState: "idle" });
    expect(h.job(id).status).toBe("transcribing");
    expect(h.transcribe).toHaveBeenCalledWith(h.audio, "yo", expect.any(AbortSignal));
    expect(h.extract).not.toHaveBeenCalled();
    h.asr[0].resolve(transcript("No ear pain")); await flush();
    expect(h.job(id).status).toBe("extracting");
    expect(h.extract).toHaveBeenCalledWith("ear", "No ear pain", {}, "ear.ear_pain", expect.any(AbortSignal));
    h.extracts[0].resolve(candidate("ear", [row("ear.ear_pain", false)])); await flush();
    expect(h.job(id)).toMatchObject({ status: "captured", transcript: transcript("No ear pain"), originalRevision: 10 });
    expect(h.session.interactions[0]).toMatchObject({ id, status: "candidate", pending: true,
      source: { recording_id: id, language: "yo", raw_asr_transcript: "No ear pain", submitted_text: "No ear pain", asr_provider: "intron" } });
    expect(h.prepare).not.toHaveBeenCalled();
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.session.encounter).toEqual({});
    expect(h.session.revision).toBe(10);
  });

  it("processes different sections in parallel and preserves both out-of-order replies", async () => {
    const h = setup();
    const ear = h.record("ear", "ig");
    const fever = h.record("fever", "ha");
    expect(h.transcribe).toHaveBeenCalledTimes(2);
    h.asr[1].resolve(transcript("Fever today")); await flush();
    h.asr[0].resolve(transcript("No ear pain")); await flush();
    expect(h.extract.mock.calls.map(([assessment, text]) => [assessment, text])).toEqual([["fever", "Fever today"], ["ear", "No ear pain"]]);
    const earCandidate = candidate("ear", [row("ear.ear_pain", false)]);
    const feverCandidate = candidate("fever", [row("patient_facts.has_fever", true)]);
    h.extracts[1].resolve(earCandidate); await flush();
    expect(h.job(fever).status).toBe("extracting");
    h.extracts[0].resolve(feverCandidate); await flush();
    expect(h.state().jobs.map((job) => [job.id, job.status, job.candidate])).toEqual([[ear, "captured", earCandidate], [fever, "captured", feverCandidate]]);
    expect(h.job(ear).trace.source.raw_asr_transcript).toBe("No ear pain");
    expect(h.job(fever).trace.source.language).toBe("ha");
  });

  it("queues the third job at a bound of two and frees a slot after either ASR or extraction failure", async () => {
    for (const stage of ["asr", "extract"] as const) {
      const h = setup();
      const first = h.record("ear");
      const second = h.record("fever");
      const third = h.record("respiratory");
      expect(h.transcribe).toHaveBeenCalledTimes(2);
      expect(h.job(third).status).toBe("queued");
      if (stage === "asr") h.asr[0].reject(new Error("ASR unavailable"));
      else {
        h.asr[0].resolve(transcript()); await flush();
        expect(h.transcribe).toHaveBeenCalledTimes(2);
        h.extracts[0].reject(new Error("Extraction unavailable"));
      }
      await flush();
      expect(h.job(first).status).toBe("failed");
      expect(h.session.interactions.find((entry) => entry.id === first)).toMatchObject({ status: "failed", pending: false });
      expect(h.transcribe).toHaveBeenCalledTimes(3);
      expect(h.job(second).status).toBe("transcribing");
      expect(h.job(third).status).toBe("transcribing");
      h.asr[2].resolve(transcript("Breathing finding")); await flush();
      h.extracts[h.extracts.length - 1].resolve(candidate("respiratory", [row("respiratory.respiratory_rate", 45)])); await flush();
      expect(h.job(third).status).toBe("captured");
      expect(h.accept).not.toHaveBeenCalled();
    }
  });

  it("keeps multiple clips in the same assessment as separate jobs and history entries", async () => {
    const h = setup();
    const first = h.record();
    const second = h.record();
    expect(first).not.toBe(second);
    h.asr[0].resolve(transcript("Ear pain")); h.asr[1].resolve(transcript("Discharge for two days")); await flush();
    h.extracts[1].resolve(candidate("ear", [row("ear.discharge_duration_days", 2)])); await flush();
    h.extracts[0].resolve(candidate()); await flush();
    expect(h.state().jobs.map((job) => [job.id, job.status, job.inputText])).toEqual([
      [first, "captured", "Ear pain"], [second, "captured", "Discharge for two days"],
    ]);
    expect(h.session.interactions).toHaveLength(2);
    expect(h.session.interactions.map((entry) => entry.source.recording_id).sort()).toEqual([first, second].sort());
  });

  it("snapshots question, language, state and revision at Record start and retains replies across accepted revisions", async () => {
    const h = setup({ ear: { ear_pain: null }, patient_facts: { age_months: 24 } });
    const original = structuredClone(h.session.encounter);
    const question = { ...h.session.evaluation!.assessments.ear.question! };
    h.capture.startRecording("ear", "pcm", { audio: true, understanding: true });
    const id = h.latest().id;
    (h.session.encounter.patient_facts as Record<string, unknown>).age_months = 30;
    h.session.evaluation!.assessments.ear.question!.text = "A different question";
    h.commit({ ear: { ear_pain: true } });
    h.capture.stop();
    h.asr[0].resolve(transcript("No")); await flush();
    expect(h.transcribe).toHaveBeenCalledWith(h.audio, "pcm", expect.any(AbortSignal));
    expect(h.extract).toHaveBeenCalledWith("ear", "No", original, question.field, expect.any(AbortSignal));
    h.commit({ ear: { ear_pain: true }, patient_facts: { has_fever: true } });
    const proposal = candidate("ear", [row("ear.ear_pain", false)]);
    h.extracts[0].resolve(proposal); await flush();
    expect(h.job(id)).toMatchObject({ status: "captured", originalEncounter: original, originalRevision: 10, question, language: "pcm", originalCandidate: proposal });
    expect(h.job(id).trace).toMatchObject({ before_encounter: original, capture_context: { encounter: original, revision: 10 }, source: { question, language: "pcm" } });
    expect(h.session.currentRevision()).toBe(12);
    expect(h.accept).not.toHaveBeenCalled();
  });

  it("prepares against the latest snapshot using ORIGINAL rows and proposals, with a new reviewVersion for old UI choices", async () => {
    const h = setup();
    const original = candidate("ear", [row("ear.ear_pain", true), row("ear.discharge_duration_days", 2)]);
    const id = await h.captured(original);
    h.commit({ ear: { ear_pain: false } });
    const firstRows = [{ ...original.changes[0], previous: false, conflict: true, review_changed: true }, original.changes[1]];
    await h.reviewed(id, firstRows, ["ear.ear_pain"]);
    expect(h.prepare).toHaveBeenNthCalledWith(1, "ear", h.session.encounter, original.changes, expect.any(AbortSignal));
    expect(h.job(id)).toMatchObject({ status: "review", reviewRevision: 11, reviewVersion: 1, changedFields: ["ear.ear_pain"] });
    h.commit({ ear: { ear_pain: null, discharge_duration_days: 2 } });
    const pending = h.capture.prepareReview(id);
    expect(h.job(id).status).toBe("preparing_review");
    await h.capture.accept(id, { "ear.ear_pain": "replace" });
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.prepare).toHaveBeenNthCalledWith(2, "ear", h.session.encounter, original.changes, expect.any(AbortSignal));
    expect(h.prepare.mock.calls[1][2]).toBe(original.changes);
    const newRows = original.changes.map((change) => ({ ...change, review_changed: true }));
    h.reviews[1].resolve({ changes: newRows, changed_fields: ["ear.discharge_duration_days"] }); await pending;
    expect(h.job(id)).toMatchObject({ status: "review", reviewRevision: 12, reviewVersion: 2,
      changedFields: ["ear.discharge_duration_days"], candidate: { changes: newRows }, originalCandidate: original });
    expect(original.changes[0]).toEqual(row("ear.ear_pain", true));
    await h.capture.accept(id, {});
    expect(h.accept).not.toHaveBeenCalled();
  });

  it("rejects review replies that race a revision change, and recovers from review failure", async () => {
    const h = setup();
    const id = await h.captured();
    const pending = h.capture.prepareReview(id);
    h.commit({ patient_facts: { has_fever: true } });
    h.reviews[0].resolve({ changes: [row()], changed_fields: [] }); await pending;
    expect(h.job(id)).toMatchObject({ status: "captured", reviewVersion: 0, error: expect.stringContaining("changed during review") });
    await h.capture.accept(id, {});
    expect(h.accept).not.toHaveBeenCalled();
    const retry = h.capture.prepareReview(id);
    h.reviews[1].reject(new Error("Review unavailable")); await retry;
    expect(h.job(id)).toMatchObject({ status: "captured", error: "Review unavailable" });
    await h.reviewed(id);
    expect(h.job(id)).toMatchObject({ status: "review", reviewRevision: 11, reviewVersion: 1, error: undefined });
  });

  it("accepts only a current review with every required explicit resolution and permits a failed apply to retry", async () => {
    const h = setup();
    const changes = [{ ...row(), conflict: true }, { ...row("ear.discharge_duration_days", null), uncertain: true },
      { ...row("patient_facts.has_fever", true), outside_assessment: true }];
    const id = await h.captured(candidate("ear", changes));
    await h.capture.accept(id, {});
    expect(h.accept).not.toHaveBeenCalled();
    await h.reviewed(id);
    await h.capture.accept(id, {});
    await h.capture.accept(id, { "ear.ear_pain": "replace", "ear.discharge_duration_days": "unknown" });
    expect(h.accept).not.toHaveBeenCalled();
    const resolutions = { "ear.ear_pain": "replace", "ear.discharge_duration_days": "unknown", "patient_facts.has_fever": "keep" } as const;
    h.commit({ patient_facts: { has_fever: false } });
    await h.capture.accept(id, resolutions);
    expect(h.accept).not.toHaveBeenCalled();
    await h.reviewed(id);
    const failed = h.capture.accept(id, resolutions);
    expect(h.accept).toHaveBeenCalledWith(h.job(id).candidate, resolutions, 11, h.job(id).trace);
    h.applies[0].resolve(false); await failed;
    expect(h.job(id)).toMatchObject({ status: "review", error: expect.stringContaining("not applied") });
    const retry = h.capture.accept(id, resolutions);
    h.applies[1].resolve(true); await retry;
    expect(h.job(id)).toMatchObject({ status: "accepted", audio: undefined });
    expect(h.session.encounter).toEqual({ patient_facts: { has_fever: false }, ear: { ear_pain: true, discharge_duration_days: null } });
  });

  it("applies disjoint captures from the same old revision without losing already accepted fields", async () => {
    const h = setup();
    const ear = await h.captured({ ...candidate(), candidate_encounter: { ear: { ear_pain: true }, patient_facts: { has_fever: null } } });
    const fever = await h.captured({ ...candidate("fever", [row("patient_facts.has_fever", true)]), candidate_encounter: { ear: { ear_pain: null } } });
    expect(h.job(ear).originalRevision).toBe(h.job(fever).originalRevision);
    await h.reviewed(ear);
    await h.reviewed(fever);
    const first = h.capture.accept(ear, {});
    h.applies[0].resolve(true); await first;
    await h.capture.accept(fever, {});
    expect(h.accept).toHaveBeenCalledTimes(1);
    await h.reviewed(fever);
    expect(h.prepare.mock.calls[2][1]).toEqual({ ear: { ear_pain: true } });
    const second = h.capture.accept(fever, {});
    h.applies[1].resolve(true); await second;
    expect(h.session.encounter).toEqual({ ear: { ear_pain: true }, patient_facts: { has_fever: true } });
    expect(h.job(ear).changedFields).toEqual(["ear.ear_pain"]);
    expect(h.job(fever).changedFields).toEqual(["patient_facts.has_fever"]);
    expect(h.session.interactions.map((entry) => entry.status)).toEqual(["accepted", "accepted"]);
  });

  it("requires a fresh explicit choice for overlapping review_changed rows even when accepted or proposed values are null", async () => {
    const h = setup({ ear: { ear_pain: true } });
    const id = await h.captured(candidate("ear", [row("ear.ear_pain", false, true), row("ear.discharge_duration_days", null)]));
    const retraction = await h.captured(candidate("ear", [{ ...row("ear.ear_pain", null, true), conflict: true }]));
    await h.reviewed(retraction);
    const applied = h.capture.accept(retraction, { "ear.ear_pain": "unknown" });
    h.applies[0].resolve(true); await applied;
    const rows = [{ ...row("ear.ear_pain", false, null), review_changed: true }, row("ear.discharge_duration_days", null)];
    await h.reviewed(id, rows, ["ear.ear_pain"]);
    await h.capture.accept(id, {});
    await h.capture.accept(id, { "ear.ear_pain": "replace" });
    expect(h.accept).toHaveBeenCalledTimes(1);
    expect(h.session.encounter).toEqual({ ear: { ear_pain: null } });
    const accepting = h.capture.accept(id, { "ear.ear_pain": "replace", "ear.discharge_duration_days": "keep" });
    h.applies[1].resolve(true); await accepting;
    expect(h.session.encounter).toEqual({ ear: { ear_pain: false } });
  });

  it("keeps the microphone and processing available while another reviewed update makes the session busy", async () => {
    const h = setup();
    const first = await h.captured();
    const second = await h.captured(candidate("fever", [row("patient_facts.has_fever", true)]));
    await h.reviewed(first); await h.reviewed(second);
    const accepting = h.capture.accept(first, {});
    expect(h.session.busy).toBe(true);
    await h.capture.accept(second, {});
    expect(h.accept).toHaveBeenCalledTimes(1);
    expect(h.job(second).error).toContain("Another reviewed update");
    const third = h.record("respiratory");
    h.asr[0].resolve(transcript("Breathing finding")); await flush();
    h.extracts[2].resolve(candidate("respiratory", [row("respiratory.respiratory_rate", 45)])); await flush();
    expect(h.job(third).status).toBe("captured");
    expect(h.job(first).status).toBe("applying");
    h.applies[0].resolve(true); await accepting;
    expect(h.job(first).status).toBe("accepted");
    expect(h.job(third).status).toBe("captured");
  });

  it("aborts on reset and ignores late ASR, extraction, review and session acceptance without writing history", async () => {
    for (const stage of ["asr", "extract", "review", "accept"] as const) {
      const h = setup();
      const id = h.record();
      let pending: Promise<void> | undefined;
      if (stage !== "asr") { h.asr[0].resolve(transcript()); await flush(); }
      if (stage === "review" || stage === "accept") { h.extracts[0].resolve(candidate()); await flush(); }
      if (stage === "review") pending = h.capture.prepareReview(id);
      if (stage === "accept") { await h.reviewed(id); pending = h.capture.accept(id, {}); }
      const signal = stage === "asr" ? h.transcribe.mock.calls[0][2]
        : stage === "extract" ? h.extract.mock.calls[0][4] : stage === "review" ? h.prepare.mock.calls[0][3] : undefined;
      h.capture.clear(); h.session.reset();
      if (signal) expect(signal.aborted).toBe(true);
      expect(h.microphone.cancel).toHaveBeenCalledOnce();
      expect(h.state()).toEqual({ jobs: [], recordingId: null, audioState: "idle", error: "" });
      // Start new work before the old reply: its finally must not free a new slot.
      h.record("ear"); h.record("fever"); const queued = h.record("respiratory");
      const newJobs = h.state().jobs;
      const history = structuredClone(h.session.interactions);
      h.recordInteraction.mockClear();
      if (stage === "asr") h.asr[0].resolve(transcript("Late speech"));
      if (stage === "extract") h.extracts[0].resolve(candidate());
      if (stage === "review") h.reviews[0].resolve({ changes: [row()], changed_fields: [] });
      if (stage === "accept") h.applies[0].resolve(true);
      await pending; await flush();
      expect(h.state().jobs).toEqual(newJobs);
      expect(h.recordInteraction).not.toHaveBeenCalled();
      expect(h.session.interactions).toEqual(history);
      expect(h.session.encounter).toEqual({});
      if (stage === "asr") expect(h.extract).not.toHaveBeenCalled();
      expect(h.job(queued).status).toBe("queued");
      expect(h.state().jobs.filter((job) => job.status === "transcribing")).toHaveLength(2);
    }
  });

  it("discards only the selected job and ignores its late reply without cancelling another capture", async () => {
    const h = setup();
    const discarded = h.record();
    const retained = h.record("fever");
    h.capture.discard(discarded);
    expect(h.transcribe.mock.calls[0][2]?.aborted).toBe(true);
    expect(h.transcribe.mock.calls[1][2]?.aborted).toBe(false);
    const writes = h.recordInteraction.mock.calls.length;
    h.asr[0].resolve(transcript("Discarded words")); await flush();
    expect(h.recordInteraction).toHaveBeenCalledTimes(writes);
    expect(h.extract).not.toHaveBeenCalled();
    h.asr[1].resolve(transcript("Fever today")); await flush();
    h.extracts[0].resolve(candidate("fever", [row("patient_facts.has_fever", true)])); await flush();
    expect(h.job(discarded)).toMatchObject({ status: "discarded", audio: undefined });
    expect(h.job(retained).status).toBe("captured");
    expect(h.session.interactions.find((entry) => entry.id === discarded)).toMatchObject({ status: "rejected", pending: false });
    expect(h.microphone.cancel).not.toHaveBeenCalled();
  });

  it("requires both consents and a supported language, and recovers on a later Record after permission failure", async () => {
    const h = setup();
    for (const [language, consent] of [
      ["en", { audio: false, understanding: true }], ["en", { audio: true, understanding: false }],
      ["", { audio: true, understanding: true }], ["fr", { audio: true, understanding: true }],
    ] as const) h.capture.startRecording("ear", language as ASRLanguage, consent);
    expect(h.microphone.record).not.toHaveBeenCalled();
    expect(h.state().jobs).toEqual([]);
    expect(h.state().error).toContain("consent to both");
    h.capture.addText("ear", "Typed finding", false);
    h.capture.addText("ear", "   ", true);
    expect(h.extract).not.toHaveBeenCalled();
    h.microphone.record.mockImplementationOnce(async () => {
      h.callbacks().state("permission"); h.callbacks().state("idle"); h.callbacks().error("Microphone access failed");
    });
    h.capture.startRecording("ear", "en", { audio: true, understanding: true }); await flush();
    const failed = h.latest().id;
    expect(h.job(failed)).toMatchObject({ status: "failed", error: "Microphone access failed" });
    expect(h.state()).toMatchObject({ recordingId: null, audioState: "idle" });
    const recovered = h.record("ear", "ha");
    h.asr[0].resolve(transcript()); await flush(); h.extracts[0].resolve(candidate()); await flush();
    expect(h.job(recovered).status).toBe("captured");
    expect(h.state().error).toBe("");
    expect(h.session.interactions.find((entry) => entry.id === failed)).toMatchObject({ status: "failed", pending: false });
  });

  it("retries with a new identity and clean candidate/review state without mixing typed and audio provenance", async () => {
    const h = setup();
    const audioId = h.record("ear", "yo");
    h.asr[0].resolve(transcript("Raw ear words")); await flush();
    h.extracts[0].resolve(candidate()); await flush();
    await h.reviewed(audioId);
    const typedId = h.text("fever", "  Typed fever words  ");
    h.extracts[1].reject(new Error("Extraction failed")); await flush();
    h.capture.retry(audioId, "  Corrected ear words  ");
    const corrected = h.latest().id;
    expect(corrected).not.toBe(audioId);
    expect(h.job(corrected)).toMatchObject({ status: "extracting", inputText: "Corrected ear words", originalCandidate: undefined,
      candidate: undefined, reviewRevision: undefined, reviewVersion: 0, changedFields: [], error: undefined });
    expect(h.job(corrected).trace.source).toEqual({ ...h.job(audioId).trace.source, submitted_text: "Corrected ear words" });
    expect(h.job(corrected).trace.source.recording_id).toBe(audioId);
    expect(h.job(corrected).trace.capture_context).toEqual(h.job(audioId).trace.capture_context);
    h.capture.retry(typedId, "Corrected typed fever");
    const typedRetry = h.latest().id;
    expect(h.job(typedRetry).trace.source).toEqual({ submitted_text: "Corrected typed fever" });
    expect(h.job(typedRetry).audio).toBeUndefined();
    expect(h.job(typedRetry).transcript).toBeUndefined();
    expect(h.transcribe).toHaveBeenCalledOnce();
    expect(h.extract.mock.calls.slice(2).map(([assessment, text]) => [assessment, text])).toEqual([
      ["ear", "Corrected ear words"], ["fever", "Corrected typed fever"],
    ]);
    h.extracts[3].resolve(candidate("fever", [row("patient_facts.has_fever", true)]));
    h.extracts[2].resolve(candidate("ear", [row("ear.ear_pain", false)])); await flush();
    expect(h.job(corrected).status).toBe("captured");
    expect(h.job(typedRetry).status).toBe("captured");
    expect(h.session.interactions.find((entry) => entry.id === typedId)).toMatchObject({ status: "failed", error: "Extraction failed" });
    expect(h.job(audioId).trace.source.raw_asr_transcript).toBe("Raw ear words");
    const failedAudio = h.record("ear", "ig");
    h.asr[1].reject(new Error("ASR unavailable")); await flush();
    h.capture.retry(failedAudio);
    const audioRetry = h.latest().id;
    expect(h.transcribe).toHaveBeenLastCalledWith(h.audio, "ig", expect.any(AbortSignal));
    expect(h.job(audioRetry).trace.source).toMatchObject({ recording_id: failedAudio, language: "ig" });
    expect(h.job(audioRetry).trace.source.submitted_text).toBeUndefined();
    expect(h.job(audioRetry).trace.source.raw_asr_transcript).toBeUndefined();
    h.asr[2].resolve(transcript("New ASR words")); await flush();
    expect(h.extract).toHaveBeenLastCalledWith("ear", "New ASR words", {}, "ear.ear_pain", expect.any(AbortSignal));
    h.extracts[4].resolve(candidate()); await flush();
    expect(h.job(audioRetry).status).toBe("captured");
    expect(h.session.interactions.find((entry) => entry.id === failedAudio)).toMatchObject({ status: "failed", error: "ASR unavailable" });
    expect(h.accept).not.toHaveBeenCalled();
  });

  it("retains same-value measurement reconfirmation rows through capture, review and explicit apply", async () => {
    const h = setup({ respiratory: { respiratory_rate: 42 } });
    const measurement = row("respiratory.respiratory_rate", 42, 42);
    const id = await h.captured(candidate("respiratory", [measurement], "Measured again: 42 breaths per minute"));
    expect(h.job(id).candidate!.changes).toEqual([measurement]);
    await h.reviewed(id);
    expect(h.prepare.mock.calls[0][2]).toEqual([measurement]);
    expect(h.job(id).candidate!.changes).toEqual([measurement]);
    expect(h.accept).not.toHaveBeenCalled();
    const accepting = h.capture.accept(id, {});
    h.applies[0].resolve(true); await accepting;
    expect(h.accept.mock.calls[0][0].changes).toEqual([measurement]);
    expect(h.job(id)).toMatchObject({ status: "accepted", changedFields: [] });
    expect(h.session.interactions[0]).toMatchObject({ status: "accepted", candidate: { changes: [measurement] } });
    expect(h.session.encounter).toEqual({ respiratory: { respiratory_rate: 42 } });
  });

  it("fails empty ASR and mismatched assessment replies without presenting or accepting a candidate", async () => {
    const h = setup();
    const empty = h.record();
    h.asr[0].resolve(transcript(" \n ")); await flush();
    expect(h.job(empty)).toMatchObject({ status: "failed", error: expect.stringContaining("No usable speech") });
    expect(h.extract).not.toHaveBeenCalled();
    const wrong = h.text();
    h.extracts[0].resolve(candidate("fever", [row("patient_facts.has_fever", true)])); await flush();
    expect(h.job(wrong)).toMatchObject({ status: "failed", error: expect.stringContaining("wrong assessment") });
    expect(h.job(wrong).candidate).toBeUndefined();
    expect(h.prepare).not.toHaveBeenCalled();
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.session.encounter).toEqual({});
  });
});
