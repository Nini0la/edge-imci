import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ASRLanguage, AssessmentCandidate, AssessmentChange, AssessmentEvaluation, AssessmentId, CaptureScope, FieldDescriptor, Transcription } from "../types";
import type { extractAssessment, prepareAssessmentReview, transcribeAudio } from "./api";
import type { createAudioCapture } from "./audio";
import type { useAssessmentSession } from "./useAssessmentSession";
import { createVoiceCapture } from "./useVoiceCapture";
import { effectiveChanges, guideResolutions, pendingEvidenceVersion } from "./guideEvidence";

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

function candidate(assessment: CaptureScope = "ear", changes = [row()], input_text = "Finding"): AssessmentCandidate {
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

function setup(encounter: Record<string, unknown> = {}, audioEnabled?: boolean) {
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
    needsResumeDecision: false, resumeSaved: vi.fn().mockResolvedValue(false),
    currentRevision: () => session.revision,
    interruptedCount: 0, acknowledgeInterrupted: vi.fn(),
    snapshot: () => ({ encounter: session.encounter, revision: session.revision, evaluation: session.evaluation, interactions: session.interactions }),
    recordInteraction, accept, refresh: vi.fn(async () => true), evaluate: vi.fn(async () => true), rejectPending: vi.fn(),
    updateIntake: vi.fn(async () => true),
    reset: vi.fn(() => { commit({}); session.interactions = []; session.busy = false; }),
  };
  function commit(next: Record<string, unknown>) {
    session.encounter = structuredClone(next);
    session.revision += 1;
    session.evaluation = evaluation(session.encounter);
  }
  const capture = createVoiceCapture({ getSession: () => session, onChange: (next) => { state = next; }, transcribe, extract, prepare, audioFactory, audioEnabled });
  const latest = () => state.jobs[state.jobs.length - 1];
  function record(assessment: AssessmentId = "ear", language: ASRLanguage = "yo") {
    capture.startRecording(assessment, language, { audio: true, understanding: true });
    const id = latest().id;
    capture.stop();
    return id;
  }
  function text(assessment: CaptureScope = "ear", input = "Typed finding") {
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
  it("never constructs or accesses a microphone when audio is disabled, including cleanup", () => {
    const getUserMedia = vi.fn();
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
    const h = setup({}, false);
    h.capture.startRecording("ear", "en", { audio: true, understanding: true });
    h.capture.startRecording("ear", "en", { audio: false, understanding: false });
    h.capture.stop();
    h.capture.cancelRecording();
    h.capture.clear();
    h.capture.clear(false);
    expect(h.state()).toEqual({ jobs: [], recordingId: null, audioState: "idle", error: "" });
    expect(h.audioFactory).not.toHaveBeenCalled();
    expect(h.microphone.record).not.toHaveBeenCalled();
    expect(h.microphone.stop).not.toHaveBeenCalled();
    expect(h.microphone.cancel).not.toHaveBeenCalled();
    expect(getUserMedia).not.toHaveBeenCalled();
    expect(h.transcribe).not.toHaveBeenCalled();
    expect(h.recordInteraction).not.toHaveBeenCalled();
  });

  it("rejects an audio-only retry in malformed state without ASR, and recovers with text", async () => {
    const h = setup({}, false);
    const id = await h.captured();
    // Simulate a malformed audio-only job reaching the reusable queue's retry path.
    Object.assign(h.job(id), { inputText: undefined, audio: h.audio, language: "en" });
    h.capture.retry(id);
    await flush();
    const failed = h.latest().id;
    expect(h.job(failed)).toMatchObject({ status: "failed", error: "Audio capture is disabled. Type a finding instead." });
    expect(h.transcribe).not.toHaveBeenCalled();
    expect(h.extract).toHaveBeenCalledOnce();
    h.capture.retry(failed, "Corrected typed finding");
    h.extracts[1].resolve(candidate()); await flush();
    expect(h.latest()).toMatchObject({ status: "captured", inputText: "Corrected typed finding" });
    expect(h.audioFactory).not.toHaveBeenCalled();
    expect(h.transcribe).not.toHaveBeenCalled();
  });

  it("keeps text readiness, retries, review, acceptance and discard working without audio", async () => {
    const h = setup({}, false);
    h.session.evaluation = null;
    expect(h.capture.addText("full-note", "Keep draft", true)).toBe(false);
    expect(h.capture.stageField("ear", pain, false)).toBeUndefined();
    expect(h.state().jobs).toEqual([]);
    h.session.evaluation = evaluation({});
    expect(h.capture.addText("full-note", "No consent", false)).toBe(false);
    expect(h.capture.addText("full-note", "   ", true)).toBe(false);
    const failed = h.text("full-note");
    h.extracts[0].reject(new Error("Extraction unavailable")); await flush();
    h.capture.retry(failed, "  No ear pain  ");
    const id = h.latest().id;
    h.extracts[1].resolve(candidate("full-note", [row(pain.path, false)])); await flush();
    expect(h.job(id)).toMatchObject({ status: "captured", inputText: "No ear pain" });
    expect(h.prepare).not.toHaveBeenCalled();
    expect(h.accept).not.toHaveBeenCalled();
    await h.reviewed(id);
    const accepting = h.capture.accept(id, {});
    h.applies[0].resolve(true); await accepting;
    expect(h.session.encounter).toEqual({ ear: { ear_pain: false } });
    expect(h.job(id).status).toBe("accepted");
    const discarded = h.text();
    h.capture.discard(discarded);
    expect(h.extract.mock.calls[2][4]!.aborted).toBe(true);
    h.extracts[2].resolve(candidate()); await flush();
    expect(h.job(discarded).status).toBe("discarded");
    const reset = h.text();
    h.capture.clear(false);
    expect(h.extract.mock.calls[3][4]!.aborted).toBe(true);
    const history = structuredClone(h.session.interactions);
    h.extracts[3].resolve(candidate()); await flush();
    expect(h.session.interactions).toEqual(history);
    expect(h.capture.stageField("ear", pain, true, reset)).toBeUndefined();
    expect(h.audioFactory).not.toHaveBeenCalled();
    expect(h.transcribe).not.toHaveBeenCalled();
  });

  it("freezes full-note context, strips supplied questions even on retry, and refuses full-note voice", async () => {
    const h = setup({ ear: { ear_pain: false } });
    const context = { encounter: structuredClone(h.session.encounter), revision: 10,
      question: { field: "ear.ear_pain", text: "Ear pain?" } };
    h.capture.startRecording("full-note" as AssessmentId, "en", { audio: true, understanding: true });
    expect(h.microphone.record).not.toHaveBeenCalled();
    expect(h.capture.addText("full-note", "  Report  ", true, context)).toBe(true);
    const id = h.latest().id;
    (context.encounter.ear as Record<string, unknown>).ear_pain = true;
    h.commit({ patient_facts: { has_fever: true } });
    expect(h.extract).toHaveBeenCalledExactlyOnceWith("full-note", "Report", { ear: { ear_pain: false } }, undefined, expect.any(AbortSignal));
    expect(h.job(id)).toMatchObject({ originalRevision: 10, originalEncounter: { ear: { ear_pain: false } }, question: undefined });
    expect(h.job(id).trace.source.question).toBeUndefined();
    h.extracts[0].reject(new Error("Retry report")); await flush();
    h.capture.retry(id, "Corrected report");
    expect(h.latest().assessment).toBe("full-note");
    expect(h.extract).toHaveBeenLastCalledWith("full-note", "Corrected report", { ear: { ear_pain: false } }, undefined, expect.any(AbortSignal));
    h.extracts[1].resolve(candidate("full-note")); await flush();
    expect(h.latest().status).toBe("captured");
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.transcribe).not.toHaveBeenCalled();
  });

  it("interleaves a report and section capture and merges only explicitly confirmed rows", async () => {
    const h = setup({ patient_facts: { age_months: 24 } });
    const report = h.text("full-note");
    const ear = h.text("ear");
    h.extracts[1].resolve(candidate()); await flush();
    await h.reviewed(ear);
    await h.capture.accept(ear, {});
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.job(ear).error).toContain("full report");
    h.extracts[0].resolve({ ...candidate("full-note", [row("patient_facts.has_fever", true)]), candidate_encounter: { ear: { ear_pain: null } } }); await flush();
    await h.reviewed(report);
    const first = h.capture.accept(ear, {}); h.applies[0].resolve(true); await first;
    await h.capture.accept(report, {});
    expect(h.accept).toHaveBeenCalledOnce();
    await h.reviewed(report);
    const second = h.capture.accept(report, {}); h.applies[1].resolve(true); await second;
    expect(h.session.encounter).toEqual({ patient_facts: { age_months: 24, has_fever: true }, ear: { ear_pain: true } });
    expect(h.state().jobs.map((job) => job.status)).toEqual(["accepted", "accepted"]);
  });

  it.each(["discard", "reset"] as const)("ignores a late full-note reply after %s", async (action) => {
    const h = setup(); const id = h.text("full-note");
    if (action === "discard") h.capture.discard(id);
    else { h.capture.clear(); h.session.reset(); }
    expect(h.extract.mock.calls[0][4]!.aborted).toBe(true);
    const history = structuredClone(h.session.interactions);
    h.extracts[0].resolve(candidate("full-note")); await flush();
    expect(h.session.interactions).toEqual(history);
    expect(h.session.encounter).toEqual({});
    expect(h.accept).not.toHaveBeenCalled();
    if (action === "discard") expect(h.job(id).status).toBe("discarded");
    else expect(h.state().jobs).toEqual([]);
  });

  it.each(["review", "accept"] as const)("ignores a late full-note %s after reset", async (stage) => {
    const h = setup(); const id = await h.captured(candidate("full-note"));
    let pending: Promise<unknown>;
    if (stage === "review") pending = h.capture.prepareReview(id);
    else { await h.reviewed(id); pending = h.capture.accept(id, {}); }
    h.capture.clear(); h.session.reset();
    if (stage === "review") {
      expect(h.prepare.mock.calls[0][3]!.aborted).toBe(true);
      h.reviews[0].resolve({ changes: [row()], changed_fields: [] });
    } else h.applies[0].resolve(true);
    await pending; await flush();
    expect(h.state().jobs).toEqual([]);
    expect(h.session.interactions).toEqual([]);
    expect(h.session.encounter).toEqual({});
  });

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
    expect(h.prepare.mock.calls[1][2]).toEqual(original.changes);
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
    expect(h.accept).toHaveBeenCalledWith(h.job(id).candidate, resolutions, 11, {
      ...h.job(id).trace, original_candidate: h.job(id).originalCandidate, worker_edits: h.job(id).workerEdits,
    });
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
      let pending: Promise<unknown> | undefined;
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

const pain: FieldDescriptor = { path: "ear.ear_pain", label: "Ear pain", kind: "boolean", nullable: true, assessments: ["ear"] };
const rate: FieldDescriptor = { path: "respiratory.respiratory_rate", label: "Respiratory rate", kind: "integer", nullable: true,
  minimum: 0, maximum: 200, unit: "breaths/min", assessments: ["respiratory"] };
const age: FieldDescriptor = { path: "patient_facts.age_months", label: "Age", kind: "integer", nullable: true,
  minimum: 0, maximum: 59, unit: "months", assessments: ["respiratory"] };

describe("direct structured field staging", () => {
  it.each([false, 0])("preserves structured %j through review and acceptance without audio", async (input) => {
    const h = setup({}, false);
    const descriptor = input === false ? pain : rate;
    const assessment = descriptor.assessments[0];
    const id = h.capture.stageField(assessment, descriptor, input)!;
    expect(h.job(id).workerEdits![descriptor.path]).toMatchObject({ value: input });
    expect(h.extract).not.toHaveBeenCalled();
    await h.reviewed(id, effectiveChanges(h.job(id)));
    const accepting = h.capture.accept(id, guideResolutions(h.job(id)));
    h.applies[0].resolve(true); await accepting;
    expect(h.job(id)).toMatchObject({ status: "accepted", candidate: { changes: [expect.objectContaining({ value: input })] } });
    expect(h.session.encounter).toEqual(input === false ? { ear: { ear_pain: false } } : { respiratory: { respiratory_rate: 0 } });
    expect(h.audioFactory).not.toHaveBeenCalled();
    expect(h.transcribe).not.toHaveBeenCalled();
  });

  it.each([null, "", "  ", 0, "1", "60", "2.5", "12x", false])("rejects required intake age %j while preserving raw input", async (input) => {
    const h = setup({ patient_facts: { age_months: 24 } }, false);
    const id = h.capture.stageField("respiratory", age, "24")!;
    await h.reviewed(id, effectiveChanges(h.job(id)));
    // Identity is read at edit time, not frozen when the queue or job is created.
    h.session.patientName = "Test Child";
    h.prepare.mockClear();
    h.capture.stageField("respiratory", age, input, id);
    const edit = h.job(id).workerEdits![age.path];
    expect(edit.error).toBe("Enter age in completed months from 2 to 59.");
    expect(edit.raw).toBe(input === null ? undefined : String(input));
    expect(edit.value).toBeUndefined();
    expect(guideResolutions(h.job(id))).toEqual({});
    await h.capture.prepareReview(id);
    await h.capture.accept(id, { [age.path]: "unknown" });
    expect(h.prepare).not.toHaveBeenCalled();
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.session.encounter).toEqual({ patient_facts: { age_months: 24 } });
    h.capture.stageField("respiratory", age, "2", id);
    expect(h.job(id).workerEdits![age.path]).toMatchObject({ raw: "2", value: 2 });
    expect(h.job(id).workerEdits![age.path].error).toBeUndefined();
    await h.reviewed(id, effectiveChanges(h.job(id)));
    const accepting = h.capture.accept(id, guideResolutions(h.job(id)));
    h.applies[0].resolve(true); await accepting;
    expect(h.session.encounter).toEqual({ patient_facts: { age_months: 2 } });
  });

  it("keeps valid intake ages and other nullable fields unchanged", () => {
    const h = setup({}, false);
    h.session.patientName = "Test Child";
    for (const input of [2, "59"]) {
      const id = h.capture.stageField("respiratory", age, input)!;
      expect(h.job(id).workerEdits![age.path]).toMatchObject({ value: Number(input) });
      expect(h.job(id).workerEdits![age.path].error).toBeUndefined();
    }
    for (const input of [null, ""]) {
      const id = h.capture.stageField("respiratory", rate, input)!;
      expect(h.job(id).workerEdits![rate.path]).toMatchObject({ value: null });
      expect(h.job(id).workerEdits![rate.path].error).toBeUndefined();
    }
  });

  it.each([undefined, "", "   "])("retains nullable legacy age without a valid identity (%j)", (patientName) => {
    const h = setup();
    h.session.patientName = patientName;
    for (const input of [null, "", 0]) {
      const id = h.capture.stageField("respiratory", age, input)!;
      expect(h.job(id).workerEdits![age.path]).toMatchObject({ value: input === 0 ? 0 : null });
      expect(h.job(id).workerEdits![age.path].error).toBeUndefined();
    }
  });

  it("only edits existing full-note jobs and never recreates them from stale controls", async () => {
    const h = setup();
    expect(h.capture.stageField("full-note", pain, true)).toBeUndefined();
    expect(h.capture.stageField("fever", pain, true)).toBeUndefined();
    expect(h.state().jobs).toEqual([]);
    const original = candidate("full-note");
    Object.freeze(original.changes[0]); Object.freeze(original.changes); Object.freeze(original);
    const id = await h.captured(original);
    expect(h.capture.stageField("full-note", pain, false, id)).toBe(id);
    expect(h.job(id).originalCandidate).toBe(original);
    expect(original.changes[0].value).toBe(true);
    expect(h.job(id).candidate!.changes[0].value).toBe(false);
    h.capture.discard(id);
    expect(h.capture.stageField("full-note", pain, true, id)).toBeUndefined();
    expect(h.capture.stageField("ear", pain, true, id)).toBeUndefined();
    expect(h.state().jobs).toHaveLength(1);
    h.capture.clear();
    expect(h.capture.stageField("ear", pain, true, id)).toBeUndefined();
    expect(h.state().jobs).toEqual([]);
  });

  it.each(["arrival", "discard"] as const)("rejects a stale pending-evidence fingerprint after %s even before React can rerender", async (event) => {
    const h = setup();
    const field = "danger_signs.lethargic_or_unconscious";
    const id = await h.captured(candidate("danger", [row(field, true)]));
    await h.reviewed(id);
    const other = event === "discard" ? await h.captured(candidate("danger", [row(field, false)])) : undefined;
    // Hold the immutable jobs snapshot a rendered hook would still have while the controller receives new events.
    const renderedJobs = h.state().jobs;
    const expected = { revision: h.session.revision, editVersion: h.job(id).editVersion ?? 0,
      pendingEvidence: pendingEvidenceVersion(renderedJobs, [field], h.session.encounter) };
    if (event === "arrival") await h.captured(candidate("danger", [row(field, false)]));
    else h.capture.discard(other!);
    expect(h.session.revision).toBe(expected.revision);
    expect(h.job(id).editVersion ?? 0).toBe(expected.editVersion);
    expect(pendingEvidenceVersion(renderedJobs, [field], h.session.encounter)).toBe(expected.pendingEvidence);
    expect(pendingEvidenceVersion(h.state().jobs, [field], h.session.encounter)).not.toBe(expected.pendingEvidence);
    await h.capture.accept(id, {}, expected);
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.job(id)).toMatchObject({ status: "review", error: expect.stringContaining("pending evidence") });
    expect(h.session.encounter).toEqual({});
  });

  it("accepts a matching fingerprint through preparation and re-review metadata changes", async () => {
    const h = setup();
    const id = await h.captured();
    const expected = { revision: h.session.revision, editVersion: 0,
      pendingEvidence: pendingEvidenceVersion(h.state().jobs, [pain.path], h.session.encounter) };
    await h.reviewed(id);
    await h.reviewed(id, [{ ...row(), review_changed: false }]);
    expect(h.job(id)).toMatchObject({ reviewVersion: 2, reviewRevision: expected.revision, reviewEditVersion: 0 });
    expect(pendingEvidenceVersion(h.state().jobs, [pain.path], h.session.encounter)).toBe(expected.pendingEvidence);
    const accepting = h.capture.accept(id, {}, expected);
    expect(h.accept).toHaveBeenCalledOnce();
    h.applies[0].resolve(true); await accepting;
    expect(h.job(id).status).toBe("accepted");
    expect(h.session.encounter).toEqual({ ear: { ear_pain: true } });
  });

  it("stages without remote consents, ASR, extraction, recording, or changes to accepted evidence", async () => {
    const h = setup();
    h.capture.addText("ear", "Not consented", false);
    const id = h.capture.stageField("ear", pain, false)!;
    expect(id).toBeTruthy();
    expect(h.job(id)).toMatchObject({ status: "captured", originalRevision: 10, question: undefined,
      originalCandidate: { extraction_mode: "worker-review", changes: [] },
      workerEdits: { [pain.path]: { value: false, previous: null, revision: 10 } }, editVersion: 1 });
    expect(h.job(id).trace.source).toEqual({ submitted_text: "Worker-entered structured observations" });
    expect(h.transcribe).not.toHaveBeenCalled();
    expect(h.extract).not.toHaveBeenCalled();
    expect(h.microphone.record).not.toHaveBeenCalled();
    expect(h.prepare).not.toHaveBeenCalled();
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.session.encounter).toEqual({});
    expect(h.session.revision).toBe(10);
    await h.reviewed(id, effectiveChanges(h.job(id)));
    const accepting = h.capture.accept(id, guideResolutions(h.job(id)));
    h.applies[0].resolve(true); await accepting;
    expect(h.session.encounter).toEqual({ ear: { ear_pain: false } });
    expect(h.session.interactions[0]).toMatchObject({ status: "accepted", original_candidate: { changes: [] },
      worker_edits: { [pain.path]: { value: false } }, resolutions: { [pain.path]: "replace" } });
    expect(fetch).not.toHaveBeenCalled();
  });

  it.each(["12x", "-", "1.5", "201"])("preserves invalid numeric text %j and blocks preparation and acceptance until corrected", async (raw) => {
    const h = setup({ respiratory: { respiratory_rate: 42 } });
    const id = h.capture.stageField("respiratory", rate, "42")!;
    await h.reviewed(id, effectiveChanges(h.job(id)));
    h.prepare.mockClear();
    expect(h.capture.stageField("respiratory", rate, raw, id)).toBe(id);
    expect(h.job(id).workerEdits![rate.path]).toMatchObject({ raw, error: expect.any(String) });
    expect(h.job(id).workerEdits![rate.path].value).toBeUndefined();
    expect(h.job(id)).toMatchObject({ status: "captured", editVersion: 2, reviewEditVersion: 1 });
    await h.capture.prepareReview(id);
    await h.capture.accept(id, { [rate.path]: "replace" });
    expect(h.prepare).not.toHaveBeenCalled();
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.session.encounter).toEqual({ respiratory: { respiratory_rate: 42 } });
    h.capture.stageField("respiratory", rate, "43", id);
    await h.reviewed(id, effectiveChanges(h.job(id)));
    expect(h.job(id).workerEdits![rate.path]).toMatchObject({ raw: "43", value: 43 });
    expect(h.job(id).workerEdits![rate.path].error).toBeUndefined();
    expect(h.job(id)).toMatchObject({ editVersion: 3, reviewEditVersion: 3, reviewVersion: 2 });
  });

  it.each([null, "", "42"])("retains manual unknown or same-value reconfirmation %j through an accepted receipt", async (input) => {
    const h = setup({ respiratory: { respiratory_rate: 42 } });
    const id = h.capture.stageField("respiratory", rate, input)!;
    const value = input === "42" ? 42 : null;
    expect(h.job(id).candidate!.changes).toHaveLength(1);
    expect(h.job(id).candidate!.changes[0]).toMatchObject({ field: rate.path, previous: 42, value, worker_entered: true });
    await h.reviewed(id, effectiveChanges(h.job(id)));
    const resolutions = guideResolutions(h.job(id));
    expect(resolutions).toEqual({ [rate.path]: value === null ? "unknown" : "replace" });
    const accepting = h.capture.accept(id, resolutions);
    h.applies[0].resolve(true); await accepting;
    expect(h.session.interactions[0]).toMatchObject({ status: "accepted", worker_edits: { [rate.path]: { value } },
      candidate: { changes: [expect.objectContaining({ field: rate.path, value })] }, resolutions });
    expect(h.job(id).changedFields).toEqual(value === null ? [rate.path] : []);
  });

  it("retains immutable ASR quotes and original uncertainty when a worker corrects null to known", async () => {
    const h = setup();
    const id = h.record();
    h.asr[0].resolve(transcript("Maybe ear pain")); await flush();
    const original = { ...candidate("ear", [{ ...row(pain.path, null), uncertain: true }], "Maybe ear pain"),
      uncertainties: [{ field: pain.path, source_text: "Maybe ear pain", reason: "Unclear" }],
      evidence_spans: [{ field: pain.path, source_text: "Maybe ear pain" }] };
    h.extracts[0].resolve(original); await flush();
    const before = structuredClone(original);
    const source = structuredClone(h.job(id).trace.source);
    Object.freeze(original.changes[0]); Object.freeze(original.changes); Object.freeze(original);
    h.capture.stageField("ear", pain, true, id);
    expect(h.job(id).candidate!.changes[0]).toMatchObject({ value: true, uncertain: false, worker_entered: true });
    await h.reviewed(id, effectiveChanges(h.job(id)));
    const accepting = h.capture.accept(id, guideResolutions(h.job(id)));
    h.applies[0].resolve(true); await accepting;
    expect(original).toEqual(before);
    expect(h.job(id).originalCandidate).toEqual(before);
    expect(h.session.interactions[0]).toMatchObject({ status: "accepted", source, original_candidate: before,
      worker_edits: { [pain.path]: { value: true } }, candidate: { uncertainties: before.uncertainties, evidence_spans: before.evidence_spans,
        changes: [expect.objectContaining({ value: true, uncertain: false })] } });
    expect(h.transcribe).toHaveBeenCalledOnce();
    expect(h.extract).toHaveBeenCalledOnce();
  });

  it("keeps worker edits across re-review but invalidates old versions and choices against changed evidence", async () => {
    const h = setup();
    const id = h.capture.stageField("ear", pain, true)!;
    await h.reviewed(id, effectiveChanges(h.job(id)));
    const edit = structuredClone(h.job(id).workerEdits);
    h.commit({ ear: { ear_pain: false } });
    await h.capture.accept(id, guideResolutions(h.job(id)));
    expect(h.accept).not.toHaveBeenCalled();
    const rows = effectiveChanges(h.job(id)).map((change) => ({ ...change, previous: false, conflict: true, review_changed: true }));
    await h.reviewed(id, rows, [pain.path]);
    expect(h.prepare.mock.calls[1][2]).toEqual(effectiveChanges(h.job(id)));
    expect(h.job(id)).toMatchObject({ workerEdits: edit, reviewVersion: 2, reviewRevision: 11 });
    expect(guideResolutions(h.job(id))).toEqual({});
    await h.capture.accept(id, guideResolutions(h.job(id)));
    expect(h.accept).not.toHaveBeenCalled();
    h.capture.stageField("ear", pain, true, id);
    expect(h.job(id)).toMatchObject({ status: "captured", editVersion: 2, reviewEditVersion: 1 });
    await h.capture.accept(id, { [pain.path]: "replace" });
    expect(h.accept).not.toHaveBeenCalled();
    await h.reviewed(id, rows, [pain.path]);
    expect(guideResolutions(h.job(id))).toEqual({ [pain.path]: "replace" });
  });

  it("aborts preparation when edited and ignores its late reply without cancelling a newer review", async () => {
    const h = setup();
    const id = h.capture.stageField("ear", pain, true)!;
    const first = h.capture.prepareReview(id);
    const oldRows = h.prepare.mock.calls[0][2];
    h.capture.stageField("ear", pain, false, id);
    expect(h.prepare.mock.calls[0][3]!.aborted).toBe(true);
    const second = h.capture.prepareReview(id);
    const currentRows = h.prepare.mock.calls[1][2];
    h.reviews[0].resolve({ changes: oldRows, changed_fields: [] }); await first;
    expect(h.job(id)).toMatchObject({ status: "preparing_review", editVersion: 2, reviewVersion: 0 });
    expect(h.prepare.mock.calls[1][3]!.aborted).toBe(false);
    h.capture.stageField("ear", pain, null, id);
    expect(h.prepare.mock.calls[1][3]!.aborted).toBe(true);
    h.reviews[1].resolve({ changes: currentRows, changed_fields: [] }); await second;
    expect(h.job(id)).toMatchObject({ status: "captured", editVersion: 3, reviewVersion: 0,
      candidate: { changes: [expect.objectContaining({ value: null })] } });
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.session.encounter).toEqual({});
  });
});
