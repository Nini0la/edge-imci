import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAssessmentSession } from "./useAssessmentSession";
import { acceptAssessment, evaluateAssessment } from "./api";
import { draftKey, parseDraft } from "./assessment";
import type { AssessmentCandidate, AssessmentEvaluation, InteractionTrace } from "../types";

// Minimal hook scheduler: exercise async session logic without adding a DOM dependency.
const hooks = vi.hoisted(() => ({ slots: [] as unknown[], cursor: 0, effects: [] as Array<() => unknown> }));
vi.mock("react", () => ({
  useState(initial: unknown) {
    const index = hooks.cursor++;
    if (!(index in hooks.slots)) hooks.slots[index] = typeof initial === "function" ? initial() : initial;
    return [hooks.slots[index], (next: unknown) => {
      hooks.slots[index] = typeof next === "function" ? next(hooks.slots[index]) : next;
    }];
  },
  useRef(initial: unknown) {
    const index = hooks.cursor++;
    if (!(index in hooks.slots)) hooks.slots[index] = { current: initial };
    return hooks.slots[index];
  },
  useEffect(effect: () => unknown) {
    const index = hooks.cursor++;
    if (!(index in hooks.slots)) { hooks.slots[index] = true; hooks.effects.push(effect); }
  },
}));
vi.mock("./api", () => ({ acceptAssessment: vi.fn(), evaluateAssessment: vi.fn() }));

function render() { hooks.cursor = 0; return useAssessmentSession(); }
function mount() {
  const session = render();
  const cleanups = hooks.effects.splice(0).map((effect) => effect());
  return { session, unmount: () => cleanups.forEach((cleanup) => { if (typeof cleanup === "function") cleanup(); }) };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const encounter = { ear: { ear_pain: true } };
const progress = { status: "INCOMPLETE" as const, decision: "ASK" as const, missing_fields: [], question: null, blockers: [] };
const evaluation: AssessmentEvaluation = { encounter,
  analysis: { input_text: "", extraction_mode: "test", matched_case_id: null, structured_encounter: encounter, structured_view: [],
    schema_valid: true, extraction_warnings: [], is_complete: false, missing_elements: {}, contradictions: [], is_urgent: false,
    classifications: [], urgent_actions: [], final_actions: [], deferred_actions: [], rendered_response: "Incomplete",
    decision_trace: [], pipeline_trace: [], error: null, outside_supported_scope: false, state: "INCOMPLETE" },
  assessments: { danger: progress, respiratory: progress, diarrhoea: progress, fever: progress, ear: progress } };
const candidate: AssessmentCandidate = { assessment: "ear", input_text: "Normalized input", extraction_mode: "frontier", warnings: [],
  changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: null, value: true, conflict: false, outside_assessment: false }] };
const trace: InteractionTrace = { id: "interpretation-1", timestamp: "2026-09-13T12:00:00Z", assessment: "ear", status: "candidate",
  source: { recording_id: "recording-1", raw_asr_transcript: "Raw words", submitted_text: "Worker edited words", language: "yo" }, candidate };
const storage = new Map<string, string>();
const setItem = vi.fn((key: string, value: string) => { storage.set(key, value); });

beforeEach(() => {
  hooks.slots = []; hooks.cursor = 0; hooks.effects = [];
  storage.clear(); vi.clearAllMocks(); setItem.mockReset();
  setItem.mockImplementation((key, value) => { storage.set(key, value); });
  vi.stubGlobal("sessionStorage", { getItem: (key: string) => storage.get(key) ?? null, setItem, removeItem: (key: string) => storage.delete(key) });
  vi.mocked(evaluateAssessment).mockResolvedValue(evaluation);
});
afterEach(() => { vi.unstubAllGlobals(); });

describe("session provenance and clinical authority", () => {
  it("records intermediate snapshots without revision changes; accepts only after the current request succeeds", async () => {
    mount(); await Promise.resolve();
    let session = render();
    const revision = session.revision;
    session.recordInteraction(trace);
    session = render();
    expect(session.revision).toBe(revision);
    expect(session.interactions).toHaveLength(1);
    const request = deferred<AssessmentEvaluation>();
    vi.mocked(acceptAssessment).mockReturnValue(request.promise);
    const accepting = session.accept(candidate, {}, revision, trace);
    session = render();
    expect(session.revision).toBe(revision);
    expect(session.interactions[0]).toMatchObject({ status: "candidate", pending: true });
    expect(session.interactions[0].result).toBeUndefined();
    request.resolve(evaluation);
    expect(await accepting).toBe(true);
    session = render();
    expect(session.revision).toBe(revision + 1);
    expect(session.interactions).toHaveLength(1);
    expect(session.interactions[0]).toMatchObject({ status: "accepted", pending: false, result: evaluation, source: trace.source, before_encounter: encounter });
    expect(JSON.parse(storage.get(draftKey)!).interactions[0].status).toBe("accepted");
    expect(session.encounter).toEqual(encounter);
    expect(session.encounter).not.toHaveProperty("interactions");
  });

  it("retains failed acceptance and rejected candidates without changing clinical revision", async () => {
    mount(); await Promise.resolve();
    let session = render();
    const revision = session.revision;
    vi.mocked(acceptAssessment).mockRejectedValue(new Error("Accept timed out"));
    expect(await session.accept(candidate, {}, revision, trace)).toBe(false);
    session = render();
    expect(session.revision).toBe(revision);
    expect(session.interactions[0]).toMatchObject({ status: "failed", error: "Accept timed out", candidate });
    session.recordInteraction({ ...trace, id: "another-candidate" });
    render().rejectPending("Worker switched assessments");
    session = render();
    expect(session.interactions.map((item) => item.status)).toEqual(["failed", "rejected"]);
    expect(session.revision).toBe(revision);
    expect(session.encounter).toEqual(encounter);
  });

  it("refuses stale or unresolved acceptance without adding an accepted trace or calling the API", async () => {
    mount(); await Promise.resolve();
    const session = render();
    const uncertain = { ...candidate, changes: [{ ...candidate.changes[0], previous: null, value: null, uncertain: true }] };
    expect(await session.accept(uncertain, {}, session.revision, trace)).toBe(false);
    expect(await session.accept(candidate, {}, session.revision - 1, trace)).toBe(false);
    expect(acceptAssessment).not.toHaveBeenCalled();
    expect(render().interactions).toEqual([]);
  });

  it("restores historical outputs only as trace data and re-evaluates the accepted encounter", async () => {
    const historical = { ...evaluation, encounter: { ear: { ear_pain: false } }, analysis: { ...evaluation.analysis, is_complete: true } };
    storage.set(draftKey, JSON.stringify({ version: 1, encounter, attempted: ["ear"], revision: 7,
      interactions: [{ ...trace, status: "accepted", result: historical }] }));
    const request = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValue(request.promise);
    const { session } = mount();
    expect(session.evaluation).toBeNull();
    expect(session.ready).toBe(false);
    expect(session.interactions[0].result).toEqual(historical);
    expect(evaluateAssessment).toHaveBeenCalledWith(encounter, ["ear"], expect.any(AbortSignal));
    request.resolve(evaluation); await request.promise;
    expect(render().evaluation).toEqual(evaluation);
    expect(render().evaluation).not.toEqual(historical);
  });

  it("clears all history on reset and ignores late acceptance without recreating storage", async () => {
    mount(); await Promise.resolve();
    let session = render();
    const request = deferred<AssessmentEvaluation>();
    vi.mocked(acceptAssessment).mockReturnValue(request.promise);
    const accepting = session.accept(candidate, {}, session.revision, trace);
    render().reset();
    const revisionAfterReset = render().revision;
    request.resolve(evaluation);
    expect(await accepting).toBe(false);
    session = render();
    expect(session.interactions).toEqual([]);
    expect(session.revision).toBeGreaterThanOrEqual(revisionAfterReset);
    expect(storage.has(draftKey)).toBe(false);
    expect(session.hasData).toBe(false);
  });

  it("warns on overflow without dropping history and does not record a failed event on unmount", async () => {
    const { unmount } = mount(); await Promise.resolve();
    setItem.mockImplementation(() => { throw new Error("QuotaExceededError"); });
    render().recordInteraction(trace);
    let session = render();
    expect(session.storageHint).toContain("Tab storage is full or unavailable");
    expect(session.interactions).toEqual([trace]);
    const revision = session.revision;
    const request = deferred<AssessmentEvaluation>();
    vi.mocked(acceptAssessment).mockReturnValue(request.promise);
    const accepting = session.accept(candidate, {}, revision, trace);
    unmount();
    request.reject(new Error("Aborted"));
    expect(await accepting).toBe(false);
    session = render();
    expect(session.revision).toBe(revision);
    expect(session.interactions[0].status).toBe("candidate");
  });

  it("removes the previous accepted snapshot when saving newer accepted evidence fails, so reload cannot restore it", async () => {
    const oldEncounter = { ear: { ear_pain: false } };
    const oldTrace = { ...trace, id: "older-accepted", status: "accepted" as const };
    storage.set(draftKey, JSON.stringify({ version: 1, encounter: oldEncounter, attempted: ["ear"], revision: 7, interactions: [oldTrace] }));
    vi.mocked(evaluateAssessment).mockResolvedValue({ ...evaluation, encounter: oldEncounter });
    const { unmount } = mount(); await Promise.resolve();
    expect(parseDraft(storage.get(draftKey)!)?.encounter).toEqual(oldEncounter);
    setItem.mockImplementation(() => { throw new Error("QuotaExceededError"); });
    vi.mocked(acceptAssessment).mockResolvedValue(evaluation);
    const session = render();
    expect(await session.accept(candidate, {}, session.revision, trace)).toBe(true);
    const current = render();
    expect(current.encounter).toEqual(encounter);
    expect(current.interactions).toHaveLength(2);
    expect(current.interactions[0]).toEqual(oldTrace);
    expect(current.interactions[1]).toMatchObject({ id: trace.id, status: "accepted", source: trace.source, result: evaluation });
    expect(current.storageHint).toContain("older saved draft was removed");
    expect(current.storageHint).toContain("reload will lose them");
    expect(parseDraft(storage.get(draftKey) ?? null)).toBeNull();

    unmount();
    hooks.slots = []; hooks.cursor = 0; hooks.effects = [];
    vi.mocked(evaluateAssessment).mockClear().mockResolvedValue({ ...evaluation, encounter: {} });
    const reloaded = mount().session;
    expect(reloaded.encounter).toEqual({});
    expect(reloaded.hasData).toBe(false);
    expect(reloaded.interactions).toEqual([]);
    expect(evaluateAssessment).toHaveBeenCalledWith(undefined, [], expect.any(AbortSignal));
    await Promise.resolve();
  });

  it("explicitly warns against reload when the stale snapshot cannot be invalidated", async () => {
    mount(); await Promise.resolve();
    render().recordInteraction({ ...trace, status: "accepted", result: evaluation });
    const previousSnapshot = storage.get(draftKey);
    setItem.mockImplementation(() => { throw new Error("QuotaExceededError"); });
    vi.spyOn(sessionStorage, "removeItem").mockImplementation(() => { throw new Error("SecurityError"); });
    render().recordInteraction({ ...trace, id: "newer-evidence" });
    const session = render();
    expect(session.interactions).toHaveLength(2);
    expect(storage.get(draftKey)).toBe(previousSnapshot);
    expect(session.storageHint).toContain("older saved draft could not be removed");
    expect(session.storageHint).toContain("Safe restoration cannot be guaranteed");
    expect(session.storageHint).toContain("close this tab");
    expect(session.storageHint).toContain("do not reload");
  });

  it("traces full-note replacement and worker retraction without attaching old recording provenance", async () => {
    mount(); await Promise.resolve();
    let session = render();
    session.recordInteraction({ ...trace, status: "accepted", result: evaluation });
    const full: InteractionTrace = { id: "full-1", timestamp: "today", assessment: "full-note", status: "candidate", source: { submitted_text: "Complete new note" }, before_encounter: encounter };
    expect(await session.evaluate({}, ["ear"], full)).toBe(true);
    session = render();
    vi.mocked(acceptAssessment).mockResolvedValue(evaluation);
    const retract = { ...candidate, input_text: "Worker-requested retraction", extraction_mode: "worker-review", changes: [{ ...candidate.changes[0], value: null, conflict: true }] };
    expect(await session.accept(retract, { "ear.ear_pain": "unknown" }, session.revision)).toBe(true);
    session = render();
    expect(session.interactions).toHaveLength(3);
    expect(session.interactions.map((item) => item.status)).toEqual(["accepted", "accepted", "accepted"]);
    expect(session.interactions[1].source).toEqual(full.source);
    expect(session.interactions[2].source).toEqual({ submitted_text: "Worker-requested retraction" });
    expect(session.interactions[2].resolutions).toEqual({ "ear.ear_pain": "unknown" });
  });
});
