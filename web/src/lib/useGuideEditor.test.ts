import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AssessmentCandidate, AssessmentChange, AssessmentEvaluation, AssessmentId, ClinicalSchema, ClinicalValue, FieldDescriptor } from "../types";
import { extractAssessment, fetchClinicalSchema, prepareAssessmentReview, transcribeAudio } from "./api";
import type { createAudioCapture } from "./audio";
import { clinicalValue, pendingEvidenceVersion } from "./guideEvidence";
import type { useAssessmentSession } from "./useAssessmentSession";
import { useGuideEditor } from "./useGuideEditor";
import { createVoiceCapture, type useVoiceCapture } from "./useVoiceCapture";

// Dependency-aware version of the session tests' scheduler, including effect cleanup and async rerenders.
const hooks = vi.hoisted(() => ({ slots: [] as unknown[], cursor: 0, dirty: false,
  effects: [] as Array<() => void>, cleanups: new Map<number, () => void>() }));
vi.mock("react", () => ({
  useState(initial: unknown) {
    const index = hooks.cursor++;
    if (!(index in hooks.slots)) hooks.slots[index] = typeof initial === "function" ? initial() : initial;
    return [hooks.slots[index], (next: unknown) => {
      const value = typeof next === "function" ? next(hooks.slots[index]) : next;
      if (!Object.is(value, hooks.slots[index])) { hooks.slots[index] = value; hooks.dirty = true; }
    }];
  },
  useRef(initial: unknown) {
    const index = hooks.cursor++;
    if (!(index in hooks.slots)) hooks.slots[index] = { current: initial };
    return hooks.slots[index];
  },
  useEffect(effect: () => void | (() => void), dependencies?: unknown[]) {
    const index = hooks.cursor++;
    const previous = hooks.slots[index] as unknown[] | undefined;
    if (!dependencies || !previous || dependencies.length !== previous.length || dependencies.some((value, i) => !Object.is(value, previous[i]))) {
      hooks.slots[index] = dependencies;
      hooks.effects.push(() => {
        hooks.cleanups.get(index)?.();
        hooks.cleanups.delete(index);
        const cleanup = effect();
        if (cleanup) hooks.cleanups.set(index, cleanup);
      });
    }
  },
}));
vi.mock("./api", () => ({ fetchClinicalSchema: vi.fn(), transcribeAudio: vi.fn(), extractAssessment: vi.fn(), prepareAssessmentReview: vi.fn() }));

type Session = ReturnType<typeof useAssessmentSession>;
type Voice = ReturnType<typeof useVoiceCapture>;
type State = Parameters<Parameters<typeof createVoiceCapture>[0]["onChange"]>[0];
type Review = Awaited<ReturnType<typeof prepareAssessmentReview>>;
const pain: FieldDescriptor = { path: "ear.ear_pain", label: "Ear pain", kind: "boolean", nullable: true, assessments: ["ear"] };
const rate: FieldDescriptor = { path: "respiratory.respiratory_rate", label: "Respiratory rate", kind: "integer", nullable: true,
  minimum: 0, maximum: 200, unit: "breaths/min", assessments: ["respiratory"] };
const temperature: FieldDescriptor = { path: "fever.temperature_c", label: "Temperature", kind: "number", nullable: true, unit: "C", assessments: ["fever"] };
const skin: FieldDescriptor = { path: "diarrhoea.dehydration.skin_pinch", label: "Skin pinch", kind: "enum", nullable: true,
  options: [{ value: "NORMAL", label: "Normal" }, { value: "VERY_SLOWLY", label: "Very slowly" }], assessments: ["diarrhoea"] };
const shared: FieldDescriptor = { path: "danger_signs.lethargic_or_unconscious", label: "Lethargic or unconscious", kind: "boolean",
  nullable: true, assessments: ["danger", "diarrhoea"] };
const cough: FieldDescriptor = { path: "patient_facts.has_cough_or_difficult_breathing", label: "Cough or difficult breathing", kind: "boolean",
  nullable: true, assessments: ["respiratory"] };
const schema: ClinicalSchema = { schema_id: "test-schema", schema_sha256: "test-sha",
  fields: Object.fromEntries([pain, rate, temperature, skin, shared, cough].map((descriptor) => [descriptor.path, descriptor])) };

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function row(field: string, value: ClinicalValue, previous: ClinicalValue = null): AssessmentChange {
  return { field, label: field, value, previous, conflict: previous !== null && previous !== value, outside_assessment: false };
}
function proposal(assessment: AssessmentId, changes: AssessmentChange[]): AssessmentCandidate {
  return { assessment, changes, input_text: "Recorded observations", extraction_mode: "test", warnings: [] };
}
function evaluation(encounter: Record<string, unknown>): AssessmentEvaluation {
  const progress = { status: "INCOMPLETE" as const, decision: "ASK" as const, missing_fields: [], question: null, blockers: [] };
  return { encounter, assessments: { danger: progress, respiratory: progress, diarrhoea: progress, fever: progress, ear: progress },
    analysis: { input_text: "", extraction_mode: "test", matched_case_id: null, structured_encounter: encounter, structured_view: [],
      schema_valid: true, extraction_warnings: [], is_complete: false, missing_elements: {}, contradictions: [], is_urgent: false,
      classifications: [], urgent_actions: [], final_actions: [], deferred_actions: [], rendered_response: "Incomplete",
      decision_trace: [], pipeline_trace: [], error: null, outside_supported_scope: false, state: "INCOMPLETE" } };
}

function setup(encounter: Record<string, unknown> = {}) {
  let state: State = { jobs: [], recordingId: null, audioState: "idle", error: "" };
  const session: Session = { version: 1, encounter: structuredClone(encounter), attempted: [], revision: 10, interactions: [],
    evaluation: evaluation(encounter), hasData: true, busy: false, ready: true, error: "", storageHint: "", interruptedCount: 0,
    currentRevision: () => session.revision,
    snapshot: () => ({ encounter: session.encounter, revision: session.revision, evaluation: session.evaluation, interactions: session.interactions }),
    recordInteraction: vi.fn((trace) => { session.interactions = [...session.interactions.filter((entry) => entry.id !== trace.id), structuredClone(trace)]; }),
    accept: vi.fn(async (candidate, resolutions, revision, trace) => {
      if (session.busy || revision !== session.revision) return false;
      const next = structuredClone(session.encounter);
      for (const change of candidate.changes) {
        if (resolutions[change.field] === "keep") continue;
        const parts = change.field.split(".");
        let node = next;
        for (const part of parts.slice(0, -1)) node = (node[part] ??= {}) as Record<string, unknown>;
        node[parts.at(-1)!] = resolutions[change.field] === "unknown" ? null : change.value;
      }
      commit(next);
      if (trace) session.recordInteraction({ ...trace, candidate, resolutions, status: "accepted", pending: false, result: session.evaluation! });
      return true;
    }),
    refresh: vi.fn(async () => true), evaluate: vi.fn(async () => true), reset: vi.fn(), rejectPending: vi.fn(), acknowledgeInterrupted: vi.fn() };
  function commit(next: Record<string, unknown>) {
    session.encounter = structuredClone(next); session.revision += 1; session.evaluation = evaluation(session.encounter); hooks.dirty = true;
  }
  let callbacks!: Parameters<typeof createAudioCapture>[0];
  const microphone = { record: vi.fn(async () => { callbacks.state("permission"); callbacks.state("recording"); }),
    stop: vi.fn(() => { callbacks.state("stopping"); callbacks.state("idle"); callbacks.audio(new Blob(["fake audio"])); }),
    cancel: vi.fn(() => { callbacks.state("idle"); }) };
  const capture = createVoiceCapture({ getSession: () => session, onChange: (next) => { state = next; hooks.dirty = true; },
    transcribe: transcribeAudio, extract: extractAssessment, prepare: prepareAssessmentReview,
    audioFactory: (events) => { callbacks = events; return microphone; } });
  const prepare = vi.spyOn(capture, "prepareReview");
  const stage = vi.spyOn(capture, "stageField");
  const accept = vi.spyOn(capture, "accept");
  let editor!: ReturnType<typeof useGuideEditor>;
  function render() {
    let passes = 0;
    do {
      if (++passes > 30) throw new Error("Hook render did not settle");
      hooks.cursor = 0; hooks.dirty = false;
      const voice: Voice = { ...state, ...capture, clear: () => capture.clear() };
      editor = useGuideEditor({ ...session }, voice);
      for (const effect of hooks.effects.splice(0)) effect();
    } while (hooks.dirty);
    return editor;
  }
  async function flush() { for (let i = 0; i < 12; i += 1) { await Promise.resolve(); render(); } return editor; }
  async function record(candidate: AssessmentCandidate) {
    vi.mocked(extractAssessment).mockResolvedValueOnce(candidate);
    capture.startRecording(candidate.assessment, "yo", { audio: true, understanding: true });
    const id = state.recordingId!;
    render(); capture.stop(); render(); await flush();
    return id;
  }
  render();
  return { session, capture, prepare, stage, accept, microphone, render, flush, record, commit,
    job: (id: string) => state.jobs.find((job) => job.id === id)!, state: () => state };
}

beforeEach(() => {
  hooks.slots = []; hooks.cursor = 0; hooks.dirty = false; hooks.effects = []; hooks.cleanups.clear();
  vi.resetAllMocks();
  vi.stubGlobal("fetch", vi.fn(() => { throw new Error("Unexpected network call"); }));
  vi.mocked(fetchClinicalSchema).mockResolvedValue(schema);
  vi.mocked(transcribeAudio).mockResolvedValue({ transcript: "Recorded observations", provider: "intron", model: null, duration_seconds: 1 });
  vi.mocked(extractAssessment).mockRejectedValue(new Error("No fake extraction queued"));
  vi.mocked(prepareAssessmentReview).mockImplementation(async (_assessment, encounter, changes) => {
    const rows = changes.map((change) => {
      const previous = clinicalValue(encounter, change.field);
      return { ...change, previous, conflict: previous !== null && previous !== change.value, review_changed: previous !== change.previous };
    });
    return { changes: rows, changed_fields: rows.filter((change) => change.review_changed).map((change) => change.field) };
  });
});
afterEach(() => {
  for (const cleanup of hooks.cleanups.values()) cleanup();
  expect(fetch).not.toHaveBeenCalled();
  vi.restoreAllMocks(); vi.unstubAllGlobals();
});

describe("guide schema and control props", () => {
  it("only exposes schema fields and preserves descriptors, sparse unknowns, and accepted false or zero", async () => {
    const h = setup({ ear: { ear_pain: false }, respiratory: { respiratory_rate: 0 } });
    expect(h.render().field("ear", pain.path)).toBeNull();
    expect(h.render().field("ear", "invented.field")).toBeNull();
    await h.flush();
    for (const descriptor of [pain, rate, temperature, skin]) {
      expect(h.render().field(descriptor.assessments[0], descriptor.path)).toMatchObject({ descriptor, source: "accepted", pending: false,
        requiresChoice: false, disabled: false, raw: undefined, error: undefined, onChange: expect.any(Function) });
    }
    expect(h.render().field("ear", pain.path)!.value).toBe(false);
    expect(h.render().field("respiratory", rate.path)!.value).toBe(0);
    expect(h.render().field("fever", temperature.path)!.value).toBeNull();
    expect(h.render().field("diarrhoea", skin.path)!.value).toBeNull();
    expect(h.render().field("ear", "invented.field")).toBeNull();
    expect(h.stage).not.toHaveBeenCalled();
    expect(h.render().workingEncounter).toEqual(h.session.encounter);
    expect(h.render().workingEncounter).not.toBe(h.session.encounter);
    h.session.ready = false;
    expect(h.render().field("ear", pain.path)!.disabled).toBe(true);
  });

  it("surfaces schema errors, retries with cleanup, and ignores a late schema result after unmount", async () => {
    vi.mocked(fetchClinicalSchema).mockRejectedValueOnce(new Error("Schema unavailable"));
    const h = setup(); await h.flush();
    expect(h.render().schemaError).toBe("Schema unavailable");
    expect(h.render().field("ear", pain.path)).toBeNull();
    const request = deferred<ClinicalSchema>();
    vi.mocked(fetchClinicalSchema).mockReturnValueOnce(request.promise);
    const firstSignal = vi.mocked(fetchClinicalSchema).mock.calls[0][0]!;
    h.render().retrySchema(); h.render();
    expect(firstSignal.aborted).toBe(true);
    expect(h.render().schemaError).toBe("");
    const signal = vi.mocked(fetchClinicalSchema).mock.calls[1][0]!;
    for (const cleanup of hooks.cleanups.values()) cleanup();
    hooks.cleanups.clear();
    expect(signal.aborted).toBe(true);
    hooks.dirty = false;
    request.resolve(schema); await request.promise; await Promise.resolve();
    expect(hooks.dirty).toBe(false);
    expect(h.stage).not.toHaveBeenCalled();
  });
});

describe("manual guide confirmation", () => {
  it.each([
    [pain, false, false], [rate, "42", 42], [temperature, "37.5", 37.5], [skin, "VERY_SLOWLY", "VERY_SLOWLY"],
    [rate, "", null], [pain, null, null],
  ] satisfies Array<[FieldDescriptor, ClinicalValue, ClinicalValue]>)("stages %j input %j locally and prepares plus accepts in one confirm action", async (descriptor, input, value) => {
    const h = setup(); await h.flush();
    const assessment = descriptor.assessments[0];
    h.render().field(assessment, descriptor.path)!.onChange(input);
    await h.flush();
    const id = h.render().selectedJob(assessment)!.id;
    expect(h.render().field(assessment, descriptor.path)).toMatchObject({ value, acceptedValue: null, source: "worker", pending: true });
    expect(h.session.encounter).toEqual({});
    expect(h.session.revision).toBe(10);
    expect(h.prepare).not.toHaveBeenCalled();
    expect(h.session.accept).not.toHaveBeenCalled();
    expect(transcribeAudio).not.toHaveBeenCalled();
    expect(extractAssessment).not.toHaveBeenCalled();
    expect(h.microphone.record).not.toHaveBeenCalled();
    const pendingEvidence = pendingEvidenceVersion(h.state().jobs, [descriptor.path], h.session.encounter);
    await h.render().confirm(assessment); await h.flush();
    expect(h.prepare).toHaveBeenCalledExactlyOnceWith(id);
    expect(h.accept).toHaveBeenCalledExactlyOnceWith(id, { [descriptor.path]: value === null ? "unknown" : "replace" },
      { revision: 10, editVersion: 1, pendingEvidence });
    expect(h.session.accept).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ changes: [expect.objectContaining({ field: descriptor.path, value })] }),
      { [descriptor.path]: value === null ? "unknown" : "replace" }, 10, expect.objectContaining({ original_candidate: { assessment,
        input_text: "Worker-entered structured observations", extraction_mode: "worker-review", changes: [], warnings: [] },
        worker_edits: { [descriptor.path]: expect.objectContaining({ value }) } }));
    expect(h.job(id).status).toBe("accepted");
    expect(clinicalValue(h.session.encounter, descriptor.path)).toBe(value);
    expect(h.render().field(assessment, descriptor.path)).toMatchObject({ value, source: "accepted", pending: false });
  });

  it("retains same-value manual reconfirmation instead of treating it as an empty draft", async () => {
    const h = setup({ respiratory: { respiratory_rate: 42 } }); await h.flush();
    h.render().field("respiratory", rate.path)!.onChange("42"); h.render();
    await h.render().confirm("respiratory"); await h.flush();
    expect(h.session.accept).toHaveBeenCalledOnce();
    expect(h.session.interactions.at(-1)).toMatchObject({ status: "accepted", worker_edits: { [rate.path]: { value: 42, raw: "42", previous: 42 } } });
    expect(h.state().jobs[0].changedFields).toEqual([]);
  });

  it("preserves invalid numeric text and accepted projection, blocking both prepare and accept", async () => {
    const h = setup({ respiratory: { respiratory_rate: 42 } }); await h.flush();
    h.render().field("respiratory", rate.path)!.onChange("12x"); await h.flush();
    expect(h.render().field("respiratory", rate.path)).toMatchObject({ value: undefined, raw: "12x", error: expect.any(String), source: "worker", pending: true });
    expect(h.render().workingEncounter).toEqual({ respiratory: { respiratory_rate: 42 } });
    await h.render().confirm("respiratory"); await h.flush();
    expect(h.prepare).not.toHaveBeenCalled();
    expect(h.session.accept).not.toHaveBeenCalled();
    h.render().field("respiratory", rate.path)!.onChange("43"); h.render();
    await h.render().confirm("respiratory"); await h.flush();
    expect(h.session.accept).toHaveBeenCalledOnce();
    expect(h.session.encounter).toEqual({ respiratory: { respiratory_rate: 43 } });
  });

  it("refreshes a stale context without accepting it until another explicit confirm", async () => {
    const h = setup(); await h.flush();
    h.render().field("ear", pain.path)!.onChange(true); h.render();
    h.commit({ respiratory: { respiratory_rate: 42 } }); h.render();
    await h.render().confirm("ear"); await h.flush();
    expect(h.prepare).toHaveBeenCalledOnce();
    expect(h.render().selectedJob("ear")).toMatchObject({ status: "review", reviewRevision: 11, workerEdits: { [pain.path]: { value: true } } });
    expect(h.session.accept).not.toHaveBeenCalled();
    await h.render().confirm("ear"); await h.flush();
    expect(h.session.accept).toHaveBeenCalledOnce();
    expect(h.session.encounter).toEqual({ respiratory: { respiratory_rate: 42 }, ear: { ear_pain: true } });
  });

  it("requires a new tap after re-review changes the accepted value, preserving the worker draft", async () => {
    const h = setup(); await h.flush();
    h.render().field("ear", pain.path)!.onChange(true); h.render();
    h.commit({ ear: { ear_pain: false } }); h.render();
    await h.render().confirm("ear"); await h.flush();
    expect(h.render().field("ear", pain.path)).toMatchObject({ value: true, acceptedValue: false, requiresChoice: true, source: "worker" });
    await h.render().confirm("ear");
    expect(h.session.accept).not.toHaveBeenCalled();
    h.render().field("ear", pain.path)!.onChange(true); h.render();
    await h.render().confirm("ear"); await h.flush();
    expect(h.session.accept).toHaveBeenCalledOnce();
    expect(h.session.encounter).toEqual({ ear: { ear_pain: true } });
  });

  it("aborts edits during a pending confirm's prepare and ignores late results", async () => {
    const h = setup(); await h.flush();
    h.render().field("ear", pain.path)!.onChange(true); h.render();
    const review = deferred<Review>();
    vi.mocked(prepareAssessmentReview).mockReturnValueOnce(review.promise);
    const confirming = h.render().confirm("ear"); h.render();
    expect(h.render().selectedJob("ear")!.status).toBe("preparing_review");
    h.render().field("ear", pain.path)!.onChange(false); h.render();
    expect(vi.mocked(prepareAssessmentReview).mock.calls[0][3]!.aborted).toBe(true);
    review.resolve({ changes: [row(pain.path, true)], changed_fields: [] }); await confirming; await h.flush();
    expect(h.session.accept).not.toHaveBeenCalled();
    expect(h.render().field("ear", pain.path)).toMatchObject({ value: false, source: "worker", pending: true });
    await h.render().confirm("ear"); await h.flush();
    expect(h.session.encounter).toEqual({ ear: { ear_pain: false } });
  });

  it("does not accept a pending confirmation when the encounter changes before prepare returns", async () => {
    const h = setup(); await h.flush();
    h.render().field("ear", pain.path)!.onChange(true); h.render();
    const review = deferred<Review>(); vi.mocked(prepareAssessmentReview).mockReturnValueOnce(review.promise);
    const confirming = h.render().confirm("ear"); h.render();
    h.commit({ ear: { ear_pain: false } }); h.render();
    review.resolve({ changes: [row(pain.path, true)], changed_fields: [] }); await confirming; await h.flush();
    expect(h.session.accept).not.toHaveBeenCalled();
    expect(h.render().selectedJob("ear")).toMatchObject({ status: "captured", error: expect.stringContaining("changed during review") });
    expect(h.session.encounter).toEqual({ ear: { ear_pain: false } });
  });

  it("does not let an aborted confirm accept a newer edit that was subsequently prepared for viewing", async () => {
    const h = setup(); await h.flush();
    h.render().field("ear", pain.path)!.onChange(true); h.render();
    const id = h.render().selectedJob("ear")!.id;
    const oldReview = deferred<Review>(); vi.mocked(prepareAssessmentReview).mockReturnValueOnce(oldReview.promise);
    const oldConfirm = h.render().confirm("ear"); h.render();
    h.render().field("ear", pain.path)!.onChange(false); h.render();
    expect(vi.mocked(prepareAssessmentReview).mock.calls[0][3]!.aborted).toBe(true);
    h.render().selectJob(id); await h.flush();
    expect(h.job(id)).toMatchObject({ status: "review", editVersion: 2, reviewEditVersion: 2 });
    expect(h.session.accept).not.toHaveBeenCalled();
    oldReview.resolve({ changes: [row(pain.path, true)], changed_fields: [] }); await oldConfirm; await h.flush();
    expect(h.session.accept).not.toHaveBeenCalled();
    expect(h.session.encounter).toEqual({});
    await h.render().confirm("ear"); await h.flush();
    expect(h.session.accept).toHaveBeenCalledOnce();
    expect(h.session.encounter).toEqual({ ear: { ear_pain: false } });
  });

  it("does not accept when another recording arrives during preparation without changing the confirmed job's edit or accepted revision", async () => {
    const h = setup(); await h.flush();
    const first = await h.record(proposal("danger", [row(shared.path, true)]));
    h.render().field("danger", shared.path)!.onChange(true); h.render();
    const editVersion = h.job(first).editVersion;
    const revision = h.session.revision;
    const pendingEvidence = pendingEvidenceVersion(h.state().jobs, [shared.path], h.session.encounter);
    const review = deferred<Review>(); vi.mocked(prepareAssessmentReview).mockReturnValueOnce(review.promise);
    const confirming = h.render().confirm("danger"); h.render();
    expect(h.job(first).status).toBe("preparing_review");
    const second = await h.record(proposal("danger", [row(shared.path, false)]));
    expect(h.job(second).status).toBe("captured");
    expect(h.job(first).editVersion).toBe(editVersion);
    expect(h.session.revision).toBe(revision);
    expect(pendingEvidenceVersion(h.state().jobs, [shared.path], h.session.encounter)).not.toBe(pendingEvidence);
    review.resolve({ changes: [row(shared.path, true)], changed_fields: [] }); await confirming; await h.flush();
    expect(h.job(first)).toMatchObject({ status: "review", editVersion, reviewRevision: revision });
    expect(h.accept).not.toHaveBeenCalled();
    expect(h.session.accept).not.toHaveBeenCalled();
    expect(h.session.encounter).toEqual({});
    expect(h.job(second).originalCandidate!.changes[0].value).toBe(false);
  });
});

describe("voice proposals in guide fields", () => {
  it.each(["conflict", "outside_assessment", "uncertain", "review_changed", "unknown"] as const)("requires an explicit tap for a %s row, not just confirm", async (flag) => {
    const accepted = flag === "conflict" || flag === "review_changed" ? false : null;
    const h = setup({ ear: { ear_pain: accepted } }); await h.flush();
    const change = row(pain.path, flag === "uncertain" || flag === "unknown" ? null : true, flag === "review_changed" ? null : accepted);
    if (flag !== "unknown") change[flag] = true;
    const id = await h.record(proposal("ear", [change]));
    expect(h.job(id).status).toBe("review");
    expect(h.render().field("ear", pain.path)).toMatchObject({ value: change.value, source: "voice", pending: true, requiresChoice: true });
    expect(h.job(id).workerEdits).toBeUndefined();
    await h.render().confirm("ear");
    expect(h.session.accept).not.toHaveBeenCalled();
    h.render().field("ear", pain.path)!.onChange(change.value as ClinicalValue); h.render();
    await h.render().confirm("ear"); await h.flush();
    expect(h.session.accept).toHaveBeenCalledOnce();
    expect(h.session.interactions.at(-1)).toMatchObject({ resolutions: { [pain.path]: change.value === null ? "unknown" : "replace" } });
    expect(transcribeAudio).toHaveBeenCalledOnce();
    expect(extractAssessment).toHaveBeenCalledOnce();
  });

  it("clears effective model uncertainty on a known worker correction but retains original evidence", async () => {
    const h = setup(); await h.flush();
    const original = { ...proposal("ear", [{ ...row(pain.path, null), uncertain: true }]),
      uncertainties: [{ field: pain.path, source_text: "Maybe", reason: "Unclear answer" }], evidence_spans: [{ field: pain.path, source_text: "Maybe" }] };
    const before = structuredClone(original);
    const id = await h.record(original);
    expect(h.render().workingEncounter).toEqual({ ear: { ear_pain: null } });
    expect(h.session.encounter).toEqual({});
    h.render().field("ear", pain.path)!.onChange(true); h.render();
    expect(h.job(id).candidate!.changes[0]).toMatchObject({ value: true, uncertain: false });
    await h.render().confirm("ear"); await h.flush();
    expect(original).toEqual(before);
    expect(h.session.interactions.at(-1)).toMatchObject({ original_candidate: before, worker_edits: { [pain.path]: { value: true } },
      source: { raw_asr_transcript: "Recorded observations" } });
  });

  it("keeps a confirmed answer only after an explicit keep tap, preserving the rejected proposal", async () => {
    const h = setup({ ear: { ear_pain: false } }); await h.flush();
    const id = await h.record(proposal("ear", [row(pain.path, true, false)]));
    h.render().field("ear", pain.path)!.onKeep!(); h.render();
    expect(h.render().field("ear", pain.path)).toMatchObject({ value: false, source: "kept", pending: true });
    await h.render().confirm("ear"); await h.flush();
    expect(h.session.encounter).toEqual({ ear: { ear_pain: false } });
    expect(h.job(id).originalCandidate!.changes[0].value).toBe(true);
    expect(h.session.interactions.at(-1)).toMatchObject({ resolutions: { [pain.path]: "keep" }, worker_edits: { [pain.path]: { keep: true } } });
  });

  it("shows one canonical worker value across danger and diarrhoea without later captures clobbering it", async () => {
    const h = setup(); await h.flush();
    h.render().field("danger", shared.path)!.onChange(false); h.render();
    const manualId = h.render().selectedJob("danger")!.id;
    await h.record(proposal("diarrhoea", [row(shared.path, true)]));
    for (const assessment of ["danger", "diarrhoea"] as const) {
      expect(h.render().field(assessment, shared.path)).toMatchObject({ value: false, source: "worker", jobId: manualId });
    }
    h.render().field("diarrhoea", shared.path)!.onChange(true); h.render();
    expect(h.stage).toHaveBeenLastCalledWith("danger", shared, true, manualId, false);
    expect(h.render().field("danger", shared.path)!.value).toBe(true);
    expect(h.state().jobs).toHaveLength(2);
    expect(h.session.encounter).toEqual({});
  });

  it("exposes conflicting captures consistently rather than choosing the last writer, and accepts only after a field tap", async () => {
    const h = setup(); await h.flush();
    const first = await h.record(proposal("danger", [row(shared.path, true)]));
    const second = await h.record(proposal("diarrhoea", [row(shared.path, false)]));
    for (const assessment of ["danger", "diarrhoea"] as const) {
      expect(h.render().field(assessment, shared.path)).toMatchObject({ value: null, source: "conflict", requiresChoice: true, error: expect.stringContaining("disagree") });
    }
    expect(h.render().workingEncounter).toEqual({});
    await h.render().confirm("danger"); await h.flush();
    expect(h.session.accept).not.toHaveBeenCalled();
    h.render().field("diarrhoea", shared.path)!.onChange(false); h.render();
    expect(h.render().field("danger", shared.path)).toMatchObject({ value: false, source: "worker" });
    await h.render().confirm("danger"); await h.flush();
    expect(h.session.accept).toHaveBeenCalledOnce();
    expect(h.job(first).status).toBe("accepted");
    expect(h.job(second).originalCandidate!.changes[0].value).toBe(false);
  });

  it("requires a field tap for contradictory same-assessment recordings even after explicitly selecting either source", async () => {
    const h = setup(); await h.flush();
    const first = await h.record(proposal("danger", [row(shared.path, true)]));
    const second = await h.record(proposal("danger", [row(shared.path, false)]));
    expect(h.render().selectedJob("danger")!.id).toBe(first);
    expect(h.job(second).status).toBe("captured");
    await h.render().confirm("danger");
    expect(h.accept).not.toHaveBeenCalled();
    for (const id of [second, first]) {
      h.render().selectJob(id); await h.flush();
      expect(h.render().selectedJob("danger")!.id).toBe(id);
      for (const assessment of ["danger", "diarrhoea"] as const) {
        expect(h.render().field(assessment, shared.path)).toMatchObject({ jobId: id, source: "conflict", value: null, requiresChoice: true });
      }
      expect(h.job(id).workerEdits).toBeUndefined();
      await h.render().confirm("danger");
      expect(h.accept).not.toHaveBeenCalled();
    }
    expect(h.stage).not.toHaveBeenCalled();
    h.render().field("danger", shared.path)!.onChange(true); h.render();
    expect(h.render().field("danger", shared.path)).toMatchObject({ jobId: first, value: true, source: "worker", requiresChoice: false });
    await h.render().confirm("danger"); await h.flush();
    expect(h.session.accept).toHaveBeenCalledOnce();
    expect(h.job(first).status).toBe("accepted");
    expect(h.job(second).workerEdits).toBeUndefined();
    expect(h.job(second)).toMatchObject({ status: "review",
      originalCandidate: { changes: [expect.objectContaining({ field: shared.path, value: false })] }, trace: { pending: true } });
    expect(h.render().pendingFieldPaths).toContain(shared.path);
    expect(h.session.encounter).toEqual({ danger_signs: { lethargic_or_unconscious: true } });
    await h.render().confirm("danger");
    expect(h.session.accept).toHaveBeenCalledOnce();
  });

  it("prefills disjoint fields from unselected same-assessment recordings without switching the selected source", async () => {
    const h = setup(); await h.flush();
    const first = await h.record(proposal("respiratory", [row(rate.path, 42)]));
    const second = await h.record(proposal("respiratory", [row(cough.path, false)]));
    expect(h.render().selectedJob("respiratory")!.id).toBe(first);
    expect(h.render().field("respiratory", rate.path)).toMatchObject({ jobId: first, value: 42, source: "voice", pending: true });
    expect(h.render().field("respiratory", cough.path)).toMatchObject({ jobId: second, value: false, source: "voice", pending: true, requiresChoice: false });
    expect(h.render().pendingFieldPaths).toEqual(expect.arrayContaining([rate.path, cough.path]));
    expect(h.render().workingEncounter).toEqual({ respiratory: { respiratory_rate: 42 }, patient_facts: { has_cough_or_difficult_breathing: false } });
    h.render().selectJob(second); await h.flush();
    expect(h.render().selectedJob("respiratory")!.id).toBe(second);
    expect(h.render().field("respiratory", rate.path)).toMatchObject({ jobId: first, value: 42, source: "voice", pending: true });
    expect(h.session.encounter).toEqual({});
    expect(h.accept).not.toHaveBeenCalled();
  });

  it("retains hidden-branch pending rows without inventing branch facts or silently accepting uncertain measurements", async () => {
    const h = setup({ patient_facts: { has_cough_or_difficult_breathing: false } }); await h.flush();
    const original = { ...proposal("respiratory", [{ ...row(rate.path, null), uncertain: true }]),
      candidate_encounter: { patient_facts: { has_cough_or_difficult_breathing: true }, respiratory: { respiratory_rate: 99 } } };
    const id = await h.record(original);
    expect(h.render().pendingFieldPaths).toContain(rate.path);
    expect(h.render().workingEncounter).toEqual({ patient_facts: { has_cough_or_difficult_breathing: false }, respiratory: { respiratory_rate: null } });
    expect(h.render().field("respiratory", cough.path)).toMatchObject({ value: false, source: "accepted", pending: false });
    await h.render().confirm("respiratory");
    expect(h.session.accept).not.toHaveBeenCalled();
    expect(h.job(id).originalCandidate).toEqual(original);
    expect(h.session.encounter).toEqual({ patient_facts: { has_cough_or_difficult_breathing: false } });
  });
});
