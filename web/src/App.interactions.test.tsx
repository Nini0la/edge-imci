import { isValidElement, type ReactElement, type ReactNode, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { AssessmentCapture } from "./components/AssessmentCapture";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
import { ClinicalFieldControl } from "./components/ClinicalFieldControl";
import { useGuideEditor } from "./lib/useGuideEditor";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import { useVoiceCapture, type CaptureJob } from "./lib/useVoiceCapture";
import type { AssessmentEvaluation, AssessmentId } from "./types";

// Exercise UI handlers and effect cleanup without adding a DOM test dependency.
type Hooks = {
  cursor: number; values: unknown[]; setters: Array<(next: unknown) => void>;
  effects: Map<number, { deps?: readonly unknown[]; cleanup?: () => void }>;
  pending: Array<() => void>;
};
const runtime = vi.hoisted(() => ({ current: null as Hooks | null }));
vi.mock("react", async (importOriginal) => {
  const react = await importOriginal<typeof import("react")>();
  return { ...react,
    useRef(initial: unknown) {
      const hooks = runtime.current;
      if (!hooks) return react.useRef(initial);
      const index = hooks.cursor++;
      if (!(index in hooks.values)) hooks.values[index] = { current: initial };
      return hooks.values[index];
    },
    useState(initial: unknown) {
      const hooks = runtime.current;
      if (!hooks) return react.useState(initial);
      const index = hooks.cursor++;
      if (!(index in hooks.values)) {
        hooks.values[index] = typeof initial === "function" ? initial() : initial;
        hooks.setters[index] = (next: unknown) => { hooks.values[index] = typeof next === "function" ? next(hooks.values[index]) : next; };
      }
      return [hooks.values[index], hooks.setters[index]];
    },
    useEffect(effect: () => void | (() => void), deps?: readonly unknown[]) {
      const hooks = runtime.current;
      if (!hooks) return react.useEffect(effect, deps);
      const index = hooks.cursor++;
      const previous = hooks.effects.get(index);
      if (previous?.deps && deps && deps.length === previous.deps.length && deps.every((dep, i) => Object.is(dep, previous.deps![i]))) return;
      hooks.pending.push(() => {
        previous?.cleanup?.();
        hooks.effects.set(index, { deps, cleanup: effect() || undefined });
      });
    },
  };
});
vi.mock("./lib/useAssessmentSession", () => ({ useAssessmentSession: vi.fn() }));
vi.mock("./lib/useVoiceCapture", () => ({ useVoiceCapture: vi.fn() }));
vi.mock("./lib/useGuideEditor", () => ({ useGuideEditor: vi.fn() }));
vi.mock("./lib/layout", () => ({ useMobileLayout: () => false }));

const createHooks = (): Hooks => ({ cursor: 0, values: [], setters: [], effects: new Map(), pending: [] });
function render(hooks: Hooks, component: () => ReactNode) {
  hooks.cursor = 0;
  runtime.current = hooks;
  let tree: ReactNode;
  try { tree = component(); } finally { runtime.current = null; }
  hooks.pending.splice(0).forEach((effect) => effect());
  return tree;
}
function unmount(hooks: Hooks) { hooks.effects.forEach((effect) => effect.cleanup?.()); hooks.effects.clear(); }
type Element = ReactElement<Record<string, unknown>>;
function elements(tree: ReactNode): Element[] {
  if (Array.isArray(tree)) return tree.flatMap(elements);
  return isValidElement<Record<string, unknown>>(tree) ? [tree, ...elements(tree.props.children as ReactNode)] : [];
}
function find(tree: ReactNode, predicate: (element: Element) => boolean) {
  const node = elements(tree).find(predicate);
  if (!node) throw new Error("UI element not found");
  return node;
}
const button = (tree: ReactNode, label: string) => find(tree, (node) => node.type === "button" && node.props.children === label);
const click = (node: Element) => (node.props.onClick as () => void)();
const edit = (node: Element, value: string) => (node.props.onChange as (event: { target: { value: string } }) => void)({ target: { value } });
function renderJob(hooks: Hooks, section: ReactNode) {
  const node = find(section, (item) => typeof item.type === "function" && item.type.name === "CaptureJobCard");
  return render(hooks, () => (node.type as (props: Record<string, unknown>) => ReactNode)(node.props));
}

const complete = { status: "COMPLETE" as const, decision: "COMPLETE" as const, question: null, missing_fields: [], blockers: [] };
const evaluation: AssessmentEvaluation = {
  encounter: { patient_facts: { age_months: 24 } },
  assessments: { danger: complete, respiratory: complete, diarrhoea: complete, fever: complete, ear: complete },
  analysis: { input_text: "", extraction_mode: "test", matched_case_id: null, structured_encounter: {}, structured_view: [],
    schema_valid: true, extraction_warnings: [], is_complete: true, missing_elements: {}, contradictions: [], is_urgent: false,
    classifications: [], urgent_actions: [], final_actions: [], deferred_actions: [], rendered_response: "Accepted final plan",
    decision_trace: [], pipeline_trace: [], error: null, outside_supported_scope: false, state: "COMPLETE" },
};
let voice: ReturnType<typeof useVoiceCapture>;
let session: ReturnType<typeof useAssessmentSession>;
let guide: ReturnType<typeof useGuideEditor>;
let props: ComponentProps<typeof AssessmentCapture>;
let dirtySections: Partial<Record<AssessmentId, boolean>>;
beforeEach(() => {
  vi.clearAllMocks();
  voice = { jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
    addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
    retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(), stageField: vi.fn() };
  session = { version: 1, encounter: evaluation.encounter, attempted: [], revision: 2, evaluation, hasData: true, ready: true,
    busy: false, error: "", storageHint: "", currentRevision: () => 2,
    snapshot: () => ({ encounter: evaluation.encounter, revision: 2, evaluation }), interruptedCount: 0, acknowledgeInterrupted: vi.fn(),
    refresh: vi.fn().mockResolvedValue(true), reset: vi.fn(), evaluate: vi.fn().mockResolvedValue(true), accept: vi.fn().mockResolvedValue(true),
    interactions: [], recordInteraction: vi.fn(), rejectPending: vi.fn() };
  vi.mocked(useAssessmentSession).mockReturnValue(session);
  vi.mocked(useVoiceCapture).mockReturnValue(voice);
  guide = { schema: { schema_id: "test", schema_sha256: "test", fields: {} }, schemaError: "", workingEncounter: session.encounter,
    pendingFieldPaths: [], field: vi.fn().mockReturnValue(null), selectedJob: (assessment) => voice.jobs.find((job) => job.assessment === assessment),
    selectJob: vi.fn(), confirm: vi.fn().mockResolvedValue(undefined), reset: vi.fn(), retrySchema: vi.fn() };
  vi.mocked(useGuideEditor).mockReturnValue(guide);
  dirtySections = {};
  props = { assessment: "ear", encounter: { ear: { ear_pain: null } }, revision: 2, urgent: false, ready: true,
    progress: { ...complete, status: "INCOMPLETE", decision: "ASK", question: { field: "ear.ear_pain", text: "Question A: ear pain?" } },
    language: "en", consent: { audio: true, understanding: true }, reviewDisabled: false, voice, onReviewJob: vi.fn(),
    onDirty: (next) => { dirtySections = typeof next === "function" ? next(dirtySections) : next; } };
  vi.stubGlobal("window", { addEventListener: vi.fn(), removeEventListener: vi.fn(), confirm: vi.fn().mockReturnValue(true) });
});
afterEach(() => { runtime.current = null; vi.unstubAllGlobals(); });

describe("typed draft context", () => {
  it("freezes the first question and clones the encounter through later edits and acceptance", () => {
    const hooks = createHooks();
    const view = () => render(hooks, () => AssessmentCapture(props));
    edit(find(view(), (node) => node.props.id === "capture-text-ear"), "Yes");
    (props.encounter.ear as Record<string, unknown>).ear_pain = true;
    props = { ...props, revision: 3, progress: { ...props.progress!, question: { field: "ear.ear_discharge_reported", text: "Question B: discharge?" } } };
    edit(find(view(), (node) => node.props.id === "capture-text-ear"), "Yes, pain");
    const tree = view();
    expect(renderToStaticMarkup(tree)).toContain("Question A: ear pain?");
    expect(renderToStaticMarkup(tree)).toContain("Accepted findings changed while you were typing");
    expect(dirtySections.ear).toBe(true);
    click(button(tree, "Process typed finding"));
    expect(voice.addText).toHaveBeenCalledWith("ear", "Yes, pain", true, {
      encounter: { ear: { ear_pain: null } }, revision: 2, question: { field: "ear.ear_pain", text: "Question A: ear pain?" },
    });
    expect(find(view(), (node) => node.props.id === "capture-text-ear").props.value).toBe("");
    expect(dirtySections.ear).toBe(false);
  });

  it("never binds a pre-ready draft to a newly appearing question and allows processing during session busy", () => {
    props = { ...props, ready: false, progress: undefined };
    const hooks = createHooks();
    const view = () => render(hooks, () => AssessmentCapture(props));
    edit(find(view(), (node) => node.props.id === "capture-text-ear"), "Yes");
    expect(button(view(), "Process typed finding").props.disabled).toBe(true);
    click(button(view(), "Process typed finding"));
    expect(voice.addText).not.toHaveBeenCalled();
    props = { ...props, ready: true, reviewDisabled: true, revision: 4, encounter: { ear: { ear_pain: false } },
      progress: { ...complete, decision: "ASK", question: { field: "ear.ear_discharge_reported", text: "New question" } } };
    edit(find(view(), (node) => node.props.id === "capture-text-ear"), "Yes ");
    const tree = view();
    expect(button(tree, "Process typed finding").props.disabled).toBe(false);
    click(button(tree, "Process typed finding"));
    expect(voice.addText).toHaveBeenCalledWith("ear", "Yes ", true, { encounter: props.encounter, revision: 4, question: undefined });
  });

  it("retains text and its frozen context on rejected submission until an explicit clear", () => {
    vi.mocked(voice.addText).mockReturnValue(false);
    const hooks = createHooks();
    const view = () => render(hooks, () => AssessmentCapture(props));
    edit(find(view(), (node) => node.props.id === "capture-text-ear"), "Yes");
    click(button(view(), "Process typed finding"));
    expect(find(view(), (node) => node.props.id === "capture-text-ear").props.value).toBe("Yes");
    expect(dirtySections.ear).toBe(true);
    props = { ...props, revision: 5 };
    click(button(view(), "Clear typed finding"));
    edit(find(view(), (node) => node.props.id === "capture-text-ear"), "New answer");
    click(button(view(), "Process typed finding"));
    expect(vi.mocked(voice.addText).mock.lastCall?.[3]?.revision).toBe(5);
    unmount(hooks);
    expect(dirtySections.ear).toBeUndefined();
  });
});

describe("assessment review routing", () => {
  const reviewJob: CaptureJob = { id: "clip", assessment: "ear", status: "review", inputText: "No", originalEncounter: {},
    originalRevision: 2, reviewRevision: 2, reviewVersion: 1, changedFields: [],
    candidate: { assessment: "ear", input_text: "No", extraction_mode: "test", warnings: [],
      changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: null, value: false, conflict: false, outside_assessment: false }] },
    trace: { id: "clip", timestamp: "today", assessment: "ear", status: "candidate", source: {} } };

  it("routes job review to the assessment without a parallel form or editable transcript", () => {
    props.voice.jobs = [reviewJob];
    const sectionHooks = createHooks();
    const jobHooks = createHooks();
    const section = () => render(sectionHooks, () => AssessmentCapture(props));
    const card = () => renderJob(jobHooks, section());
    const tree = card();
    section();
    expect(dirtySections.ear).toBe(false);
    const html = renderToStaticMarkup(tree);
    expect(html).not.toContain("Apply reviewed findings");
    expect(html).not.toContain("Correct transcript");
    expect(html).not.toContain("<select");
    click(button(tree, "Review on assessment"));
    expect(props.onReviewJob).toHaveBeenCalledWith("clip");
    expect(voice.retry).not.toHaveBeenCalled();
    expect(voice.accept).not.toHaveBeenCalled();
  });

  it("disables review routing while controls are unavailable", () => {
    props.voice.jobs = [reviewJob];
    props.reviewDisabled = true;
    const sectionHooks = createHooks();
    const jobHooks = createHooks();
    const section = () => render(sectionHooks, () => AssessmentCapture(props));
    const tree = renderJob(jobHooks, section());
    expect(button(tree, "Review on assessment").props.disabled).toBe(true);
  });

  it("leaves retractions to explicit Not assessed controls rather than ordinary checkboxes", () => {
    props = { ...props, encounter: { ear: { ear_pain: true } }, ready: false };
    const hooks = createHooks();
    const view = () => render(hooks, () => AssessmentCapture(props));
    expect(renderToStaticMarkup(view())).not.toContain('type="checkbox"');
    expect(renderToStaticMarkup(view())).not.toContain("Review selected retractions");
    expect(voice.retract).not.toHaveBeenCalled();
    expect(dirtySections.ear).toBe(false);
  });
});

describe("workspace dirty and restore gates", () => {
  it("marks dirty sections pending, withholds the final plan, and warns before leaving", () => {
    const hooks = createHooks();
    const view = () => render(hooks, App);
    let tree = view();
    const checklist = find(tree, (node) => node.type === AssessmentChecklist);
    const capture = (checklist.props.renderCapture as (id: AssessmentId) => ReactElement<ComponentProps<typeof AssessmentCapture>>)("ear");
    capture.props.onDirty((previous) => ({ ...previous, ear: true }));
    session.evaluation = { ...evaluation, analysis: { ...evaluation.analysis, is_urgent: true, urgent_actions: ["Accepted urgent action"] } };
    tree = view();
    expect(renderToStaticMarkup(tree)).toContain("Process or discard unprocessed edits before final plan");
    expect(renderToStaticMarkup(tree)).not.toContain("Accepted final plan");
    const html = renderToStaticMarkup(tree);
    expect(html.slice(0, html.indexOf("<main"))).toContain("Accepted urgent action");
    expect(find(tree, (node) => node.type === AssessmentChecklist).props.pendingAssessments).toContain("ear");
    expect(window.addEventListener).toHaveBeenCalledWith("beforeunload", expect.any(Function));
    const warn = vi.mocked(window.addEventListener).mock.calls[0][1] as (event: { preventDefault: () => void; returnValue: unknown }) => void;
    const event = { preventDefault: vi.fn(), returnValue: undefined as unknown };
    warn(event);
    expect(event.preventDefault).toHaveBeenCalled();
    capture.props.onDirty((previous) => ({ ...previous, ear: false }));
    expect(renderToStaticMarkup(view())).toContain("Accepted final plan");
    expect(window.removeEventListener).toHaveBeenCalledWith("beforeunload", warn);
  });

  it("acknowledges interrupted captures explicitly and clears voice before resetting the encounter", () => {
    session.interruptedCount = 2;
    const hooks = createHooks();
    const tree = render(hooks, App);
    click(button(tree, "Acknowledge interrupted captures"));
    expect(session.acknowledgeInterrupted).toHaveBeenCalledOnce();
    expect(voice.accept).not.toHaveBeenCalled();
    const checklist = find(tree, (node) => node.type === AssessmentChecklist);
    click(button(checklist.props.tools as ReactNode, "Clear encounter"));
    expect(window.confirm).toHaveBeenCalledOnce();
    expect(voice.clear).toHaveBeenCalledOnce();
    expect(guide.reset).toHaveBeenCalledOnce();
    expect(vi.mocked(voice.clear).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(session.reset).mock.invocationCallOrder[0]);
  });
});

describe("interactive guide integration", () => {
  const candidate = { assessment: "ear" as const, input_text: "Original words", extraction_mode: "test", warnings: [],
    changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: null, value: false, conflict: false, outside_assessment: false }] };
  function setupJob(overrides: Partial<CaptureJob> = {}) {
    const job: CaptureJob = { id: "guide-clip", assessment: "ear", status: "review", originalEncounter: {}, originalRevision: 2,
      reviewRevision: 2, reviewVersion: 1, candidate, originalCandidate: candidate, changedFields: [],
      trace: { id: "guide-clip", timestamp: "today", assessment: "ear", status: "candidate", source: {} }, ...overrides };
    voice.jobs = [job];
    return job;
  }
  function checklist() { return find(render(createHooks(), App), (node) => node.type === AssessmentChecklist); }
  function footer() { return (checklist().props.renderSectionReview as (id: AssessmentId) => ReactNode)("ear"); }

  it("passes staged previews and server-required paths without substituting the accepted encounter", () => {
    guide.workingEncounter = { patient_facts: { has_ear_problem: true } };
    guide.pendingFieldPaths = ["patient_facts.has_ear_problem"];
    session.evaluation = { ...evaluation, assessments: { ...evaluation.assessments,
      ear: { ...complete, missing_fields: ["ear.ear_pain"], question: { field: "ear.ear_discharge_reported", text: "Discharge?" } } } };
    const tree = checklist();
    expect(useGuideEditor).toHaveBeenCalledWith(session, voice);
    expect(tree.props.encounter).toBe(session.encounter);
    expect(tree.props.workingEncounter).toBe(guide.workingEncounter);
    expect(tree.props.pendingFieldPaths).toEqual(guide.pendingFieldPaths);
    expect(tree.props.requiredFieldPaths).toEqual(["ear.ear_pain", "ear.ear_discharge_reported"]);
  });

  it("binds voice-prefilled answers, explicit corrections, raw numeric input and keep to the hook without provider consent", () => {
    const field = { descriptor: { path: "ear.ear_pain", label: "Ear pain", kind: "boolean" as const, nullable: true, assessments: ["ear" as const] },
      value: false, acceptedValue: true, pending: true, requiresChoice: true, source: "voice" as const, disabled: false,
      jobId: "guide-clip", raw: undefined, error: undefined, onChange: vi.fn(), onKeep: vi.fn() };
    vi.mocked(guide.field).mockReturnValue(field);
    const renderField = checklist().props.renderField as (id: AssessmentId, path: string) => ReactNode;
    const tree = renderField("ear", "ear.ear_pain");
    const control = find(tree, (node) => node.type === ClinicalFieldControl);
    expect(guide.field).toHaveBeenLastCalledWith("ear", "ear.ear_pain");
    expect(control.props).toMatchObject(field);
    expect(renderToStaticMarkup(tree)).toContain('aria-checked="true" tabindex="0">No');
    (control.props.onChange as (value: unknown) => void)(false);
    (control.props.onChange as (value: unknown) => void)(null);
    (control.props.onChange as (value: unknown) => void)("12x");
    (control.props.onKeep as () => void)();
    expect(field.onChange.mock.calls).toEqual([[false], [null], ["12x"]]);
    expect(field.onKeep).toHaveBeenCalledOnce();
    expect(voice.addText).not.toHaveBeenCalled();
    expect(voice.startRecording).not.toHaveBeenCalled();
    expect(guide.confirm).not.toHaveBeenCalled();
  });

  it("shows unavailable controls and an actionable global schema retry rather than fabricated defaults", () => {
    guide.schema = null;
    guide.schemaError = "Schema offline";
    const tree = render(createHooks(), App);
    const html = renderToStaticMarkup(tree);
    expect(html).toContain("Assessment controls could not load: Schema offline");
    expect(html).not.toContain('role="radiogroup"');
    expect(html).toContain("Confirmed evidence remains unchanged");
    click(button(tree, "Retry controls"));
    expect(guide.retrySchema).toHaveBeenCalledOnce();
    guide.schemaError = "";
    expect(renderToStaticMarkup(render(createHooks(), App))).toContain("Loading assessment controls...");
  });

  it("confirms explicitly on the guide and never exposes generic include/replace menus", () => {
    setupJob();
    const tree = footer();
    expect(guide.confirm).not.toHaveBeenCalled();
    expect(renderToStaticMarkup(tree)).not.toContain("<select");
    expect(renderToStaticMarkup(tree)).toContain("1 observation(s) staged");
    click(button(tree, "Confirm findings"));
    expect(guide.confirm).toHaveBeenCalledWith("ear");
    expect(voice.accept).not.toHaveBeenCalled();
    expect(window.confirm).not.toHaveBeenCalled();
  });

  it("opens and focuses a desktop origin section only after explicit Review on assessment", () => {
    setupJob();
    const focus = vi.fn();
    const section = { open: false, querySelector: vi.fn().mockReturnValue({ focus }), scrollIntoView: vi.fn() };
    vi.stubGlobal("document", { activeElement: null, querySelector: vi.fn().mockReturnValue(section) });
    vi.stubGlobal("HTMLElement", class {});
    const tree = checklist();
    expect(section.open).toBe(false);
    expect(section.scrollIntoView).not.toHaveBeenCalled();
    const capture = (tree.props.renderCapture as (id: AssessmentId) => ReactElement<ComponentProps<typeof AssessmentCapture>>)("ear");
    capture.props.onReviewJob("guide-clip");
    expect(guide.selectJob).toHaveBeenCalledWith("guide-clip");
    expect(section.open).toBe(true);
    expect(focus).toHaveBeenCalledOnce();
    expect(section.scrollIntoView).toHaveBeenCalledOnce();
    expect(guide.confirm).not.toHaveBeenCalled();
  });

  it.each(["schema", "unready", "busy", "invalid", "preparing_review", "applying"])("disables confirmation for %s", (gate) => {
    const job = setupJob();
    if (gate === "schema") guide.schema = null;
    if (gate === "unready") session.ready = false;
    if (gate === "busy") session.busy = true;
    if (gate === "invalid") job.workerEdits = { "ear.ear_pain": { raw: "12x", error: "Invalid number", previous: null, label: "Ear pain", revision: 2 } };
    if (gate === "preparing_review" || gate === "applying") job.status = gate;
    const label = gate === "preparing_review" ? "Preparing review..." : gate === "applying" ? "Confirming findings..." : "Confirm findings";
    const confirm = button(footer(), label);
    expect(confirm.props.disabled).toBe(true);
    click(confirm);
    expect(guide.confirm).not.toHaveBeenCalled();
  });

  it.each([undefined, 1])("labels stale capture/review context %s as Refresh review, delegating the first-click guard", (reviewRevision) => {
    setupJob({ originalRevision: 1, reviewRevision });
    const tree = footer();
    expect(renderToStaticMarkup(tree)).toContain("Refresh review first");
    click(button(tree, "Refresh review"));
    expect(guide.confirm).toHaveBeenCalledWith("ear");
    expect(voice.accept).not.toHaveBeenCalled();
  });

  it("requires a separate no-change acknowledgement before calling confirm", () => {
    setupJob({ candidate: { ...candidate, changes: [] }, originalCandidate: { ...candidate, changes: [] } });
    vi.mocked(window.confirm).mockReturnValue(false);
    click(button(footer(), "Confirm findings"));
    expect(guide.confirm).not.toHaveBeenCalled();
    vi.mocked(window.confirm).mockReturnValue(true);
    click(button(footer(), "Confirm findings"));
    expect(guide.confirm).toHaveBeenCalledOnce();
  });

  it("uses effective edits rather than an old empty review when deciding whether to acknowledge no evidence", () => {
    setupJob({ status: "captured", originalCandidate: { ...candidate, changes: [] }, candidate: { ...candidate, changes: [] }, editVersion: 2, reviewEditVersion: 1,
      workerEdits: { "ear.ear_pain": { value: false, previous: null, label: "Ear pain", revision: 2 } } });
    click(button(footer(), "Confirm findings"));
    expect(window.confirm).not.toHaveBeenCalled();
    expect(guide.confirm).toHaveBeenCalledOnce();
  });

  it("keeps flagged answers actionable on the guide and original evidence under Details", () => {
    const guarded = { ...candidate, changes: [{ ...candidate.changes[0], uncertain: true }] };
    setupJob({ candidate: guarded, originalCandidate: guarded, question: { field: "ear.ear_pain", text: "Original question?" } });
    const tree = footer();
    const html = renderToStaticMarkup(tree);
    expect(html).toContain("Choose answers above or keep confirmed answers for 1 flagged observation(s)");
    expect(button(tree, "Ear pain")).toBeDefined();
    expect(html.indexOf("Original question?")).toBeGreaterThan(html.indexOf("Details: original report and review"));
    expect(html.indexOf("Original words")).toBeGreaterThan(html.indexOf("Details: original report and review"));
  });

  it("retains worker drafts when selecting another recording and keeps pending work out of final results", () => {
    const job = setupJob();
    voice.jobs.push({ ...job, id: "worker", originalCandidate: { ...candidate, extraction_mode: "worker-review", changes: [] },
      workerEdits: { "ear.ear_pain": { value: true, previous: null, label: "Ear pain", revision: 2 } } });
    const snapshot = structuredClone(voice.jobs);
    const tree = footer();
    expect(renderToStaticMarkup(tree)).toContain("Other drafts are retained");
    click(button(tree, "Review worker answers"));
    expect(guide.selectJob).toHaveBeenCalledWith("worker");
    click(button(tree, "Review recording 1"));
    expect(guide.selectJob).toHaveBeenLastCalledWith("guide-clip");
    expect(voice.jobs).toEqual(snapshot);
    expect(voice.discard).not.toHaveBeenCalled();
    expect(renderToStaticMarkup(render(createHooks(), App))).not.toContain("Accepted final plan");
  });
});
