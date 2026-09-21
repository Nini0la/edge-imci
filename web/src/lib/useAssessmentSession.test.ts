import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAssessmentSession } from "./useAssessmentSession";
import { acceptAssessment, evaluateAssessment } from "./api";
import { draftKey, parseDraft } from "./assessment";
import type { AssessmentCandidate, AssessmentEvaluation, AssessmentId, InteractionTrace, Resolutions } from "../types";

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

describe("local patient intake", () => {
  const name = "Synthetic Intake Patient";
  const template = { patient_facts: { age_months: null, has_cough_or_difficult_breathing: null },
    danger_signs: { convulsing_now: null }, respiratory: { respiratory_rate: null, child_calm: null, breaths_counted_one_minute: null } };
  const withAge = (age_months: number | null) => ({ ...structuredClone(template), patient_facts: { ...template.patient_facts, age_months } });
  const resultFor = (encounter: Record<string, unknown>): AssessmentEvaluation => ({ ...evaluation, encounter: structuredClone(encounter),
    analysis: { ...evaluation.analysis, input_text: "Worker-reviewed assessment evidence", extraction_mode: "reviewed-assessment-evidence",
      structured_encounter: structuredClone(encounter) } });

  beforeEach(() => {
    vi.mocked(evaluateAssessment).mockImplementation(async (encounter = template) => resultFor(encounter));
  });

  it.each([2, 59])("initializes intake at age %s only after evaluation and keeps identity out of clinical channels", async (age) => {
    const { session } = mount();
    await Promise.resolve();
    expect(render()).toMatchObject({ ready: true, hasData: false, attempted: [] });
    expect(render().patientName).toBeUndefined();
    const before = render().snapshot();
    const pending = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValueOnce(pending.promise);
    const updating = session.updateIntake(`  ${name}  `, age, render().revision);
    expect(render().snapshot()).toEqual(before);
    expect(render().patientName).toBeUndefined();
    expect(storage.has(draftKey)).toBe(false);
    expect(evaluateAssessment).toHaveBeenLastCalledWith(withAge(age), [], expect.any(AbortSignal));
    const canonical = resultFor(withAge(age));
    pending.resolve(canonical);
    expect(await updating).toBe(true);
    expect(render()).toMatchObject({ patientName: name, encounter: canonical.encounter, evaluation: canonical, revision: before.revision + 1,
      hasData: true, busy: false, attempted: [], interactions: [] });
    expect(render().evaluation).toBe(canonical);
    expect(parseDraft(storage.get(draftKey)!)).toEqual({ version: 1, patientName: name, encounter: canonical.encounter,
      revision: before.revision + 1, attempted: [], interactions: [] });
    expect(JSON.stringify(render().snapshot())).not.toContain(name);
    expect(JSON.stringify(vi.mocked(evaluateAssessment).mock.calls)).not.toContain(name);
    expect(acceptAssessment).not.toHaveBeenCalled();
    expect(setItem).toHaveBeenCalledOnce();
  });

  it.each([false, true])("updates age 11 to 12 from CURRENT input preserving attempts, history and respiratory evidence, known=%s", async (known) => {
    const { session: retained } = mount(); await Promise.resolve();
    expect(await retained.updateIntake(name, 11, render().revision)).toBe(true);
    const clinical = { ...withAge(11), ear: { ear_pain: false, ear_discharge_duration_days: 0 },
      respiratory: known ? { respiratory_rate: 45, child_calm: false, breaths_counted_one_minute: true } : template.respiratory,
      danger_signs: { convulsing_now: false }, diarrhoea: { dehydration: { sunken_eyes: true } } };
    expect(await render().evaluate(clinical, ["danger", "ear"])).toBe(true);
    render().recordInteraction({ ...trace, status: "accepted", before_encounter: clinical, result: resultFor(clinical) });
    const before = render();
    const snapshot = structuredClone(before.snapshot());
    const pending = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValueOnce(pending.promise);
    const updating = retained.updateIntake(" Renamed Synthetic Patient ", 12, before.revision);
    const expected = { ...clinical, patient_facts: { ...clinical.patient_facts, age_months: 12 } };
    const sent = vi.mocked(evaluateAssessment).mock.lastCall![0]!;
    expect(sent).toEqual(expected);
    expect(sent).not.toBe(before.encounter);
    expect(sent.diarrhoea).not.toBe(before.encounter.diarrhoea);
    expect(sent.respiratory).toEqual(clinical.respiratory);
    expect(render().snapshot()).toEqual(snapshot);
    expect(render().patientName).toBe(name);
    // History arriving during evaluation must not be overwritten by a captured draft.
    render().recordInteraction({ ...trace, id: "during-intake", status: "failed" });
    pending.resolve(resultFor(expected));
    expect(await updating).toBe(true);
    expect(before.snapshot().encounter).toEqual(expected);
    expect(snapshot.encounter).toEqual(clinical);
    expect(render()).toMatchObject({ patientName: "Renamed Synthetic Patient", attempted: before.attempted, revision: before.revision + 1 });
    expect(render().interactions).toEqual([...before.interactions, { ...trace, id: "during-intake", status: "failed" }]);
    expect(render().evaluation?.analysis.is_complete).toBe(false);
    expect(await retained.refresh()).toBe(true);
    expect(evaluateAssessment).toHaveBeenLastCalledWith(expected, before.attempted, expect.any(AbortSignal));
    expect(render()).toMatchObject({ patientName: "Renamed Synthetic Patient", encounter: expected, hasData: true });
    expect(JSON.stringify(render().snapshot())).not.toContain("Renamed Synthetic Patient");
  });

  it.each([undefined, "  Legacy Synthetic Patient  ", 42])("resumes legacy clinical age with name metadata %j for prefill", async (patientName) => {
    storage.set(draftKey, JSON.stringify({ version: 1, patientName, encounter: withAge(11), attempted: ["ear"], revision: 7 }));
    const { session } = mount();
    expect(session.patientName).toBeUndefined();
    expect(await session.updateIntake(name, 12, 0)).toBe(false);
    expect(evaluateAssessment).not.toHaveBeenCalled();
    expect(await session.resumeSaved()).toBe(true);
    expect(render().patientName).toBe(typeof patientName === "string" ? patientName.trim() : undefined);
    expect(render().encounter).toEqual(withAge(11));
    expect(await session.updateIntake(name, 12, render().revision)).toBe(true);
    expect(parseDraft(storage.get(draftKey)!)).toMatchObject({ version: 1, patientName: name, encounter: withAge(12), attempted: ["ear"] });
  });

  it("gates an identity-only draft, allows completing its intake, and removes identity on reset", async () => {
    storage.set(draftKey, JSON.stringify({ version: 1, patientName: name, encounter: {}, attempted: [], revision: 7 }));
    const { session } = mount();
    expect(session.needsResumeDecision).toBe(true);
    expect(await session.refresh()).toBe(false);
    expect(await session.resumeSaved()).toBe(true);
    expect(render()).toMatchObject({ patientName: name, ready: true, hasData: true });
    expect(await session.updateIntake(name, 11, render().revision)).toBe(true);
    session.reset(); await Promise.resolve();
    expect(render().patientName).toBeUndefined();
    expect(render()).toMatchObject({ hasData: false, encounter: template });
    expect(storage.has(draftKey)).toBe(false);
  });

  it.each([
    ["", 11], [" \n\t ", 11], ["n".repeat(201), 11], [null, 11], [name, null], [name, "11"],
    [name, 1], [name, 60], [name, 11.5], [name, NaN], [name, Infinity],
  ])("rejects invalid intake name=%j age=%j without touching accepted data", async (invalidName, age) => {
    mount(); await Promise.resolve();
    const before = render().snapshot();
    expect(await render().updateIntake(invalidName as string, age as number, before.revision)).toBe(false);
    expect(render().snapshot()).toEqual(before);
    expect(render().patientName).toBeUndefined();
    expect(evaluateAssessment).toHaveBeenCalledOnce();
    expect(setItem).not.toHaveBeenCalled();
  });

  it("requires a ready template, a current revision, and a single in-flight invocation", async () => {
    const initial = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValueOnce(initial.promise);
    const { session } = mount();
    expect(await session.updateIntake(name, 11, 0)).toBe(false);
    initial.reject(new Error("No template")); await initial.promise.catch(() => {});
    expect(await session.updateIntake(name, 11, 0)).toBe(false);
    expect(await session.refresh()).toBe(true);
    const revision = render().revision;
    expect(await session.updateIntake(name, 11, revision - 1)).toBe(false);
    const pending = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValueOnce(pending.promise);
    const first = session.updateIntake(name, 11, revision);
    expect(await session.updateIntake("Duplicate", 12, revision)).toBe(false);
    expect(await render().refresh()).toBe(false);
    expect(evaluateAssessment).toHaveBeenCalledTimes(3);
    pending.resolve(resultFor(withAge(11)));
    expect(await first).toBe(true);
    expect(await session.updateIntake("Stale", 12, revision)).toBe(false);
    expect(render().patientName).toBe(name);
  });

  it.each(["network", "schema", "error", "state", "age"])("does not commit metadata or clinical changes on %s failure", async (failure) => {
    mount(); await Promise.resolve();
    await render().updateIntake(name, 11, render().revision);
    render().recordInteraction({ ...trace, status: "accepted" });
    const before = render().snapshot();
    const saved = storage.get(draftKey);
    if (failure === "network") vi.mocked(evaluateAssessment).mockRejectedValueOnce(new Error("Synthetic failure"));
    else {
      const invalid = resultFor(withAge(failure === "age" ? null : 12));
      if (failure === "schema") invalid.analysis.schema_valid = false;
      if (failure === "error") invalid.analysis.error = "Synthetic invalid result";
      if (failure === "state") invalid.analysis.state = "ERROR";
      vi.mocked(evaluateAssessment).mockResolvedValueOnce(invalid);
    }
    expect(await render().updateIntake("Uncommitted Synthetic Name", 12, before.revision)).toBe(false);
    expect(render().snapshot()).toEqual(before);
    expect(render().patientName).toBe(name);
    expect(render().busy).toBe(false);
    expect(render().error).not.toBe("");
    expect(storage.get(draftKey)).toBe(saved);
  });

  it.each(["resolve", "reject"].flatMap((outcome) => [false, true].map((freshFirst) => ({ outcome, freshFirst }))))(
    "ignores late intake $outcome after reset, fresh evaluation finished=$freshFirst", async ({ outcome, freshFirst }) => {
    mount(); await Promise.resolve();
    await render().updateIntake(name, 11, render().revision);
    const old = deferred<AssessmentEvaluation>();
    const fresh = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValueOnce(old.promise).mockReturnValueOnce(fresh.promise);
    const updating = render().updateIntake("Late Synthetic Name", 12, render().revision);
    const signal = vi.mocked(evaluateAssessment).mock.lastCall![2]!;
    render().reset();
    if (freshFirst) { fresh.resolve(resultFor(template)); await fresh.promise; }
    const before = render().snapshot();
    expect(signal.aborted).toBe(true);
    if (outcome === "resolve") old.resolve(resultFor(withAge(12)));
    else old.reject(new Error("Late intake error"));
    expect(await updating).toBe(false);
    expect(render().snapshot()).toEqual(before);
    expect(render()).toMatchObject({ busy: !freshFirst, hasData: false, error: "" });
    expect(render().patientName).toBeUndefined();
    expect(storage.has(draftKey)).toBe(false);
    fresh.resolve(resultFor(template)); await fresh.promise;
    expect(render()).toMatchObject({ busy: false, hasData: false, encounter: template });
    expect(storage.has(draftKey)).toBe(false);
  });

  it("ignores intake after unmount without changing metadata or storage", async () => {
    const { unmount } = mount(); await Promise.resolve();
    const before = render().snapshot();
    const pending = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValueOnce(pending.promise);
    const updating = render().updateIntake(name, 11, before.revision);
    unmount(); pending.resolve(resultFor(withAge(11)));
    expect(await updating).toBe(false);
    expect(render().snapshot()).toEqual(before);
    expect(render().patientName).toBeUndefined();
    expect(storage.has(draftKey)).toBe(false);
  });

  it.each([false, true])("keeps a coherent in-memory intake on storage failure, stale removal fails=%s", async (removeFails) => {
    mount(); await Promise.resolve();
    await render().updateIntake(name, 11, render().revision);
    const previous = storage.get(draftKey);
    setItem.mockImplementation(() => { throw new Error("QuotaExceededError"); });
    if (removeFails) vi.spyOn(sessionStorage, "removeItem").mockImplementation(() => { throw new Error("SecurityError"); });
    expect(await render().updateIntake("New Synthetic Name", 12, render().revision)).toBe(true);
    expect(render()).toMatchObject({ patientName: "New Synthetic Name", encounter: withAge(12), hasData: true });
    expect(render().snapshot().evaluation?.encounter).toEqual(withAge(12));
    expect(render().storageHint).toContain(removeFails ? "Safe restoration cannot be guaranteed" : "older saved draft was removed");
    expect(storage.get(draftKey)).toBe(removeFails ? previous : undefined);
  });

  it.each([
    { value: null, resolution: "replace" }, { value: 12, resolution: "unknown" }, { value: null, resolution: "unknown" },
    { value: 1, resolution: "replace" }, { value: 60, resolution: "replace" }, { value: 11.5, resolution: "replace" },
  ] as const)("rejects age proposal $value resolved as $resolution before API or trace writes", async ({ value, resolution }) => {
    mount(); await Promise.resolve();
    await render().updateIntake(name, 11, render().revision);
    const before = render().snapshot();
    const saved = storage.get(draftKey);
    const ageCandidate = { ...candidate, changes: [{ ...candidate.changes[0], field: "patient_facts.age_months", previous: 11, value, conflict: true }] };
    expect(await render().accept(ageCandidate, { "patient_facts.age_months": resolution }, before.revision)).toBe(false);
    expect(acceptAssessment).not.toHaveBeenCalled();
    expect(render().snapshot()).toEqual(before);
    expect(storage.get(draftKey)).toBe(saved);
  });

  it("allows keeping age, supported age replacement, and unknown on other clinical fields without leaking the name", async () => {
    mount(); await Promise.resolve();
    await render().updateIntake(name, 11, render().revision);
    const ageCandidate = { ...candidate, changes: [{ ...candidate.changes[0], field: "patient_facts.age_months", previous: 11, value: null, conflict: true }] };
    vi.mocked(acceptAssessment).mockResolvedValueOnce(resultFor(withAge(11)));
    expect(await render().accept(ageCandidate, { "patient_facts.age_months": "keep" }, render().revision)).toBe(true);
    vi.mocked(acceptAssessment).mockResolvedValueOnce(resultFor(withAge(12)));
    expect(await render().accept({ ...ageCandidate, changes: [{ ...ageCandidate.changes[0], value: 12 }] },
      { "patient_facts.age_months": "replace" }, render().revision)).toBe(true);
    const unknownEar = { ...candidate, changes: [{ ...candidate.changes[0], value: null }] };
    vi.mocked(acceptAssessment).mockResolvedValueOnce(resultFor({ ...withAge(12), ear: { ear_pain: null } }));
    expect(await render().accept(unknownEar, { "ear.ear_pain": "unknown" }, render().revision)).toBe(true);
    expect(render().patientName).toBe(name);
    expect(render().interactions).toHaveLength(3);
    expect(JSON.stringify(render().snapshot())).not.toContain(name);
    expect(JSON.stringify(vi.mocked(acceptAssessment).mock.calls)).not.toContain(name);
    expect(JSON.stringify(vi.mocked(evaluateAssessment).mock.calls)).not.toContain(name);
    expect(parseDraft(storage.get(draftKey)!)?.patientName).toBe(name);
  });

  it("does not let generic evaluation or a backend response erase a known intake age", async () => {
    mount(); await Promise.resolve();
    await render().updateIntake(name, 11, render().revision);
    const before = render().snapshot();
    for (const input of [{}, withAge(null), withAge(60)]) {
      expect(await render().evaluate(input, [])).toBe(false);
    }
    expect(evaluateAssessment).toHaveBeenCalledTimes(2);
    vi.mocked(evaluateAssessment).mockResolvedValueOnce(resultFor(withAge(null)));
    expect(await render().evaluate(withAge(12), [])).toBe(false);
    expect(render().snapshot()).toEqual(before);
    vi.mocked(acceptAssessment).mockResolvedValueOnce(resultFor(withAge(null)));
    expect(await render().accept(candidate, {}, render().revision)).toBe(false);
    expect(render()).toMatchObject({ patientName: name, encounter: before.encounter, evaluation: before.evaluation, revision: before.revision });
    expect(render().interactions[0].status).toBe("failed");
  });

  it("retains legacy unnamed age-clearing semantics", async () => {
    mount(); await Promise.resolve();
    await render().evaluate(withAge(11), []);
    const ageCandidate = { ...candidate, changes: [{ ...candidate.changes[0], field: "patient_facts.age_months", previous: 11, value: null }] };
    vi.mocked(acceptAssessment).mockResolvedValueOnce(resultFor(withAge(null)));
    expect(await render().accept(ageCandidate, { "patient_facts.age_months": "unknown" }, render().revision)).toBe(true);
    expect(render().encounter).toEqual(withAge(null));
    expect(render().patientName).toBeUndefined();
  });
});

describe("saved assessment choice", () => {
  it.each([false, true])("holds saved ear pain=%s and history outside the active draft until a choice", async (earPain) => {
    const raw = JSON.stringify({ version: 1, encounter: { ear: { ear_pain: earPain } }, attempted: ["ear"], revision: 7,
      interactions: [{ ...trace, status: "accepted", result: evaluation }] });
    storage.set(draftKey, raw);
    const { session } = mount();
    await Promise.resolve();
    expect(render()).toMatchObject({ needsResumeDecision: true, encounter: {}, attempted: [], revision: 0,
      interactions: [], evaluation: null, hasData: false, ready: false, busy: false, error: "", interruptedCount: 0 });
    expect(session.snapshot()).toEqual({ encounter: {}, revision: 0, evaluation: null, interactions: [] });
    expect(await session.refresh()).toBe(false);
    expect(await render().refresh()).toBe(false);
    expect(evaluateAssessment).not.toHaveBeenCalled();
    expect(acceptAssessment).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
    expect(storage.get(draftKey)).toBe(raw);
  });

  it.each([
    { name: "history only", encounter: {}, attempted: [], interactions: [{ ...trace, status: "failed", error: "Synthetic failure" }], prompt: true },
    { name: "attempted only", encounter: {}, attempted: ["ear"], interactions: [], prompt: true },
    { name: "empty", encounter: {}, attempted: [], interactions: [], prompt: false },
    { name: "all unknown", encounter: { patient_facts: { age_months: null }, danger_signs: { convulsing_now: null },
      ear: { ear_pain: null }, diarrhoea: { dehydration: {} } }, attempted: [], interactions: [], prompt: false },
  ])("prompts only for retained work: $name", async ({ encounter, attempted, interactions, prompt }) => {
    storage.set(draftKey, JSON.stringify({ version: 1, encounter, attempted, interactions, revision: 7 }));
    const emptyEvaluation = { ...evaluation, encounter: {} };
    vi.mocked(evaluateAssessment).mockResolvedValue(emptyEvaluation);
    const { session } = mount();
    expect(session.needsResumeDecision).toBe(prompt);
    expect(session.encounter).toEqual({});
    expect(session.interactions).toEqual([]);
    if (prompt) {
      expect(evaluateAssessment).not.toHaveBeenCalled();
      expect(await session.resumeSaved()).toBe(true);
      expect(evaluateAssessment).toHaveBeenCalledExactlyOnceWith(encounter, attempted, expect.any(AbortSignal));
      expect(render().interactions).toEqual(interactions);
    } else {
      expect(await session.resumeSaved()).toBe(false);
      expect(evaluateAssessment).toHaveBeenCalledExactlyOnceWith(undefined, [], expect.any(AbortSignal));
      expect(render().hasData).toBe(false);
    }
  });

  it("consumes the saved draft once, including two resume calls before a rerender", async () => {
    storage.set(draftKey, JSON.stringify({ version: 1, encounter, attempted: ["ear"], revision: 7 }));
    const request = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValue(request.promise);
    const { session } = mount();
    const resuming = session.resumeSaved();
    expect(await session.resumeSaved()).toBe(false);
    expect(await render().resumeSaved()).toBe(false);
    expect(render()).toMatchObject({ needsResumeDecision: false, busy: true, evaluation: null });
    expect(evaluateAssessment).toHaveBeenCalledExactlyOnceWith(encounter, ["ear"], expect.any(AbortSignal));
    request.resolve(evaluation);
    expect(await resuming).toBe(true);
    expect(await session.resumeSaved()).toBe(false);
    expect(render()).toMatchObject({ revision: 8, busy: false, evaluation });
    expect(setItem).toHaveBeenCalledOnce();
    expect(evaluateAssessment).toHaveBeenCalledOnce();
  });

  it("discards the pending draft and storage on start new; an old resume handler cannot restore it", async () => {
    storage.set(draftKey, JSON.stringify({ version: 1, encounter, attempted: ["ear"], revision: 7,
      interactions: [{ ...trace, status: "accepted", result: evaluation }] }));
    const request = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValue(request.promise);
    const { session } = mount();
    const oldResume = session.resumeSaved;
    session.reset();
    expect(render()).toMatchObject({ needsResumeDecision: false, encounter: {}, attempted: [], interactions: [],
      hasData: false, evaluation: null, ready: false, interruptedCount: 0 });
    expect(storage.has(draftKey)).toBe(false);
    expect(await oldResume()).toBe(false);
    expect(evaluateAssessment).toHaveBeenCalledExactlyOnceWith(undefined, [], expect.any(AbortSignal));
    request.resolve({ ...evaluation, encounter: {} });
    await request.promise;
    expect(render()).toMatchObject({ encounter: {}, hasData: false, ready: true, busy: false, interactions: [] });
    expect(await render().resumeSaved()).toBe(false);
    expect(storage.has(draftKey)).toBe(false);
    expect(setItem).not.toHaveBeenCalled();
  });

  it.each((["resolve", "reject"] as const).flatMap((outcome) => [false, true].map((freshFirst) => ({ outcome, freshFirst }))))(
    "ignores a late old resume $outcome after reset, fresh evaluation finished=$freshFirst", async ({ outcome, freshFirst }) => {
    const urgent = { ...evaluation, analysis: { ...evaluation.analysis, is_urgent: true, urgent_actions: ["Old urgent action"] } };
    storage.set(draftKey, JSON.stringify({ version: 1, encounter, attempted: ["ear"], revision: 7,
      interactions: [{ ...trace, status: "accepted", result: urgent }] }));
    const old = deferred<AssessmentEvaluation>();
    const fresh = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValueOnce(old.promise).mockReturnValueOnce(fresh.promise);
    const { session } = mount();
    const resuming = session.resumeSaved();
    const oldSignal = vi.mocked(evaluateAssessment).mock.calls[0][2]!;
    render().reset();
    const revision = render().revision;
    expect(oldSignal.aborted).toBe(true);
    expect(render().snapshot()).toEqual({ encounter: {}, revision, evaluation: null, interactions: [] });
    const emptyEvaluation = { ...evaluation, encounter: {} };
    if (freshFirst) { fresh.resolve(emptyEvaluation); await fresh.promise; }
    if (outcome === "resolve") old.resolve(urgent);
    else old.reject(new Error("Old resume failed"));
    expect(await resuming).toBe(false);
    expect(render()).toMatchObject({ encounter: {}, attempted: [], interactions: [], evaluation: freshFirst ? emptyEvaluation : null,
      revision: revision + Number(freshFirst), hasData: false, needsResumeDecision: false, busy: !freshFirst, error: "", interruptedCount: 0 });
    if (!freshFirst) expect(await render().refresh()).toBe(false);
    expect(evaluateAssessment).toHaveBeenCalledTimes(2);
    expect(evaluateAssessment).toHaveBeenLastCalledWith(undefined, [], expect.any(AbortSignal));
    fresh.resolve(emptyEvaluation);
    await fresh.promise;
    expect(render()).toMatchObject({ encounter: {}, interactions: [], evaluation: emptyEvaluation, busy: false, hasData: false });
    expect(render().snapshot().evaluation).toEqual(emptyEvaluation);
    expect(storage.has(draftKey)).toBe(false);
    expect(setItem).not.toHaveBeenCalled();
  });

  it("keeps resumed input and history after backend failure and retries fresh evaluation without re-consuming the draft", async () => {
    const savedEncounter = { ear: { ear_pain: false }, danger_signs: { convulsing_now: true } };
    const raw = JSON.stringify({ version: 1, encounter: savedEncounter, attempted: ["danger", "ear"], revision: 7,
      interactions: [{ ...trace, status: "accepted", result: evaluation }] });
    storage.set(draftKey, raw);
    vi.mocked(evaluateAssessment).mockRejectedValueOnce(new Error("Synthetic backend unavailable"));
    const { session } = mount();
    expect(await session.resumeSaved()).toBe(false);
    const failed = render();
    expect(failed).toMatchObject({ encounter: savedEncounter, attempted: ["danger", "ear"], revision: 7, hasData: true,
      needsResumeDecision: false, evaluation: null, ready: false, busy: false, error: "Synthetic backend unavailable" });
    expect(failed.interactions).toEqual(JSON.parse(raw).interactions);
    expect(failed.snapshot()).toMatchObject({ encounter: savedEncounter, evaluation: null });
    expect(storage.get(draftKey)).toBe(raw);
    expect(await failed.resumeSaved()).toBe(false);
    expect(evaluateAssessment).toHaveBeenCalledOnce();
    const fresh = { ...evaluation, encounter: savedEncounter };
    vi.mocked(evaluateAssessment).mockResolvedValue(fresh);
    expect(await failed.refresh()).toBe(true);
    expect(evaluateAssessment).toHaveBeenLastCalledWith(savedEncounter, ["danger", "ear"], expect.any(AbortSignal));
    expect(render()).toMatchObject({ encounter: savedEncounter, evaluation: fresh, revision: 8, ready: true, busy: false, error: "" });
    expect(render().interactions).toEqual(JSON.parse(raw).interactions);
    expect(acceptAssessment).not.toHaveBeenCalled();
  });
});

describe("session provenance and clinical authority", () => {
  it.each([
    { fields: ["patient_facts.age_months"], attempted: [] },
    { fields: ["danger_signs.convulsing_now"], attempted: ["danger"] },
    { fields: ["respiratory.respiratory_rate", "patient_facts.has_fever"], attempted: ["respiratory", "fever"] },
    { fields: ["patient_facts.has_cough_or_difficult_breathing", "patient_facts.has_diarrhoea", "patient_facts.has_ear_problem"], attempted: ["respiratory", "diarrhoea", "ear"] },
    { fields: ["diarrhoea.dehydration.skin_pinch", "ear.ear_pain", "fever.temperature_c"], attempted: ["diarrhoea", "ear", "fever"] },
  ] satisfies Array<{ fields: string[]; attempted: AssessmentId[] }>) (
    "marks only full-note applied field owners as attempted: $fields", async ({ fields, attempted }) => {
    mount(); await Promise.resolve();
    const session = render();
    const report: AssessmentCandidate = { ...candidate, assessment: "full-note", changes: fields.map((field) => ({ ...candidate.changes[0], field })) };
    const request = deferred<AssessmentEvaluation>(); vi.mocked(acceptAssessment).mockReturnValueOnce(request.promise);
    const accepting = session.accept(report, {}, session.revision);
    expect(acceptAssessment).toHaveBeenCalledExactlyOnceWith(report, encounter, {}, attempted, expect.any(AbortSignal));
    expect(render().attempted).toEqual([]);
    expect(render().encounter).toEqual(encounter);
    const result: AssessmentEvaluation = { ...evaluation, assessments: Object.fromEntries(Object.entries(evaluation.assessments).map(([id, progress]) =>
      [id, { ...progress, status: attempted.some((owner) => owner === id) ? "INCOMPLETE" : "NOT_STARTED" }])) as AssessmentEvaluation["assessments"] };
    request.resolve(result); expect(await accepting).toBe(true);
    expect(render().attempted).toEqual(attempted);
    expect(render().evaluation!.assessments).toEqual(result.assessments);
    expect(Object.keys(render().evaluation!.assessments)).toHaveLength(5);
    expect(parseDraft(storage.get(draftKey)!)?.interactions?.[0]).toMatchObject({ assessment: "full-note", status: "accepted", candidate: report });
  });

  it("preserves existing attempts, excludes kept rows, and counts explicit unknown and same-value report answers", async () => {
    mount(); await Promise.resolve();
    await render().evaluate(encounter, ["ear"]);
    const report: AssessmentCandidate = { ...candidate, assessment: "full-note", changes: [
      { ...candidate.changes[0], field: "danger_signs.convulsing_now", previous: true, value: null },
      { ...candidate.changes[0], field: "patient_facts.has_fever" },
      { ...candidate.changes[0], field: "respiratory.respiratory_rate", previous: 42, value: 42 },
      { ...candidate.changes[0], field: "patient_facts.age_months", value: 24 },
    ] };
    const resolutions: Resolutions = { "danger_signs.convulsing_now": "unknown", "patient_facts.has_fever": "keep" };
    vi.mocked(acceptAssessment).mockResolvedValueOnce(evaluation);
    expect(await render().accept(report, resolutions, render().revision)).toBe(true);
    expect(acceptAssessment).toHaveBeenLastCalledWith(report, encounter, resolutions, ["ear", "danger", "respiratory"], expect.any(AbortSignal));
    expect(render().attempted).toEqual(["ear", "danger", "respiratory"]);
  });

  it("does not accept staged full notes automatically, rejects stale confirmation and drops late acceptance after reset", async () => {
    mount(); await Promise.resolve();
    const report: AssessmentCandidate = { ...candidate, assessment: "full-note" };
    const reportTrace: InteractionTrace = { ...trace, assessment: "full-note", candidate: report, pending: true };
    render().recordInteraction(reportTrace);
    expect(acceptAssessment).not.toHaveBeenCalled();
    expect(render().attempted).toEqual([]);
    expect(await render().accept(report, {}, render().revision - 1)).toBe(false);
    expect(acceptAssessment).not.toHaveBeenCalled();
    const request = deferred<AssessmentEvaluation>(); vi.mocked(acceptAssessment).mockReturnValueOnce(request.promise);
    const accepting = render().accept(report, {}, render().revision, reportTrace);
    render().reset();
    request.resolve(evaluation); expect(await accepting).toBe(false);
    expect(render()).toMatchObject({ interactions: [], attempted: [], hasData: false });
    expect(storage.has(draftKey)).toBe(false);
  });

  it("requires acknowledgement of interrupted captures without trusting or applying them", async () => {
    storage.set(draftKey, JSON.stringify({ version: 1, encounter, attempted: [], revision: 2,
      interactions: [{ ...trace, pending: true }] }));
    const { session: saved } = mount();
    expect(saved.needsResumeDecision).toBe(true);
    expect(saved.interruptedCount).toBe(0);
    expect(await saved.resumeSaved()).toBe(true);
    let session = render();
    expect(session.interruptedCount).toBe(1);
    expect(session.interactions[0].status).toBe("rejected");
    expect(acceptAssessment).not.toHaveBeenCalled();
    const revision = session.revision;
    session.acknowledgeInterrupted(); session = render();
    expect(session.interruptedCount).toBe(0);
    expect(session.revision).toBe(revision);
    expect(session.encounter).toEqual(encounter);
    expect(parseDraft(storage.get(draftKey)!)?.interactions?.[0].interruption_acknowledged).toBe(true);
  });

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

  it.each([false, true])("resumes canonical input with ear pain=%s, retaining historical outputs only as trace data", async (earPain) => {
    const savedEncounter = { ear: { ear_pain: earPain, ear_discharge_duration_days: 0 }, danger_signs: { convulsing_now: false } };
    const historical = { ...evaluation, encounter: { ear: { ear_pain: !earPain } }, analysis: { ...evaluation.analysis,
      is_complete: true, is_urgent: true, urgent_actions: ["Historical urgent action"], rendered_response: "Historical final plan" } };
    const fresh = { ...evaluation, encounter: savedEncounter, analysis: { ...evaluation.analysis, structured_encounter: savedEncounter } };
    storage.set(draftKey, JSON.stringify({ version: 1, encounter: savedEncounter, attempted: ["ear"], revision: 7,
      interactions: [{ ...trace, status: "accepted", result: historical }] }));
    const request = deferred<AssessmentEvaluation>();
    vi.mocked(evaluateAssessment).mockReturnValue(request.promise);
    const { session } = mount();
    expect(session.needsResumeDecision).toBe(true);
    expect(session.encounter).toEqual({});
    expect(session.interactions).toEqual([]);
    expect(evaluateAssessment).not.toHaveBeenCalled();
    const resuming = session.resumeSaved();
    const restoring = render();
    expect(restoring.needsResumeDecision).toBe(false);
    expect(restoring.encounter).toEqual(savedEncounter);
    expect(restoring.attempted).toEqual(["ear"]);
    expect(restoring.revision).toBe(7);
    expect(restoring.hasData).toBe(true);
    expect(restoring.busy).toBe(true);
    expect(restoring.snapshot()).toMatchObject({ encounter: savedEncounter, revision: 7, evaluation: null });
    expect(session.evaluation).toBeNull();
    expect(session.ready).toBe(false);
    expect(restoring.evaluation).toBeNull();
    expect(restoring.ready).toBe(false);
    expect(restoring.interactions[0].result).toEqual(historical);
    expect(evaluateAssessment).toHaveBeenCalledExactlyOnceWith(savedEncounter, ["ear"], expect.any(AbortSignal));
    request.resolve(fresh);
    expect(await resuming).toBe(true);
    expect(render()).toMatchObject({ evaluation: fresh, ready: true, busy: false, revision: 8 });
    expect(render().evaluation).not.toEqual(historical);
    expect(render().interactions[0].result).toEqual(historical);
    expect(parseDraft(storage.get(draftKey)!)?.encounter).toEqual(savedEncounter);
    expect(acceptAssessment).not.toHaveBeenCalled();
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
    expect(await render().resumeSaved()).toBe(true);
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
