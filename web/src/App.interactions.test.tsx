import { isValidElement, type ReactElement, type ReactNode, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { AssessmentCapture } from "./components/AssessmentCapture";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
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
let props: ComponentProps<typeof AssessmentCapture>;
let dirtySections: Partial<Record<AssessmentId, boolean>>;
beforeEach(() => {
  vi.clearAllMocks();
  voice = { jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
    addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
    retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn() };
  session = { version: 1, encounter: evaluation.encounter, attempted: [], revision: 2, evaluation, hasData: true, ready: true,
    busy: false, error: "", storageHint: "", currentRevision: () => 2,
    snapshot: () => ({ encounter: evaluation.encounter, revision: 2, evaluation }), interruptedCount: 0, acknowledgeInterrupted: vi.fn(),
    refresh: vi.fn().mockResolvedValue(true), reset: vi.fn(), evaluate: vi.fn().mockResolvedValue(true), accept: vi.fn().mockResolvedValue(true),
    interactions: [], recordInteraction: vi.fn(), rejectPending: vi.fn() };
  vi.mocked(useAssessmentSession).mockReturnValue(session);
  vi.mocked(useVoiceCapture).mockReturnValue(voice);
  dirtySections = {};
  props = { assessment: "ear", encounter: { ear: { ear_pain: null } }, revision: 2, urgent: false, ready: true,
    progress: { ...complete, status: "INCOMPLETE", decision: "ASK", question: { field: "ear.ear_pain", text: "Question A: ear pain?" } },
    language: "en", consent: { audio: true, understanding: true }, reviewDisabled: false, voice,
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

describe("unprocessed corrections and retractions", () => {
  const reviewJob: CaptureJob = { id: "clip", assessment: "ear", status: "review", inputText: "No", originalEncounter: {},
    originalRevision: 2, reviewRevision: 2, reviewVersion: 1, changedFields: [],
    candidate: { assessment: "ear", input_text: "No", extraction_mode: "test", warnings: [],
      changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: null, value: false, conflict: false, outside_assessment: false }] },
    trace: { id: "clip", timestamp: "today", assessment: "ear", status: "candidate", source: {} } };

  it("blocks old Apply without sending text, and clears dirty state on cancellation or job removal", () => {
    props.voice.jobs = [reviewJob];
    const sectionHooks = createHooks();
    const jobHooks = createHooks();
    const section = () => render(sectionHooks, () => AssessmentCapture(props));
    const card = () => renderJob(jobHooks, section());
    edit(find(card(), (node) => node.props.id === "correct-transcript-clip"), "Yes");
    let tree = card();
    section();
    expect(dirtySections.ear).toBe(true);
    expect(renderToStaticMarkup(tree)).toMatch(/<button[^>]*disabled=""[^>]*>Apply reviewed findings/);
    expect(voice.retry).not.toHaveBeenCalled();
    click(button(tree, "Cancel correction"));
    tree = card();
    section();
    expect(dirtySections.ear).toBe(false);
    expect(renderToStaticMarkup(tree)).toContain('<button type="button">Apply reviewed findings</button>');
    edit(find(tree, (node) => node.props.id === "correct-transcript-clip"), "Corrected words");
    tree = card();
    click(button(tree, "Process corrected transcript"));
    expect(voice.retry).toHaveBeenCalledWith("clip", "Corrected words");
    unmount(jobHooks);
    props.voice.jobs = [];
    section();
    expect(dirtySections.ear).toBe(false);
  });

  it("keeps deletion of the entire correction dirty and requires cancel rather than applying old evidence", () => {
    props.voice.jobs = [reviewJob];
    const sectionHooks = createHooks();
    const jobHooks = createHooks();
    const section = () => render(sectionHooks, () => AssessmentCapture(props));
    edit(find(renderJob(jobHooks, section()), (node) => node.props.id === "correct-transcript-clip"), "");
    const tree = renderJob(jobHooks, section());
    section();
    expect(dirtySections.ear).toBe(true);
    expect(button(tree, "Process corrected transcript").props.disabled).toBe(true);
    expect(renderToStaticMarkup(tree)).toMatch(/<button[^>]*disabled=""[^>]*>Apply reviewed findings/);
  });

  it("reports selected retractions as dirty until they become a review job", () => {
    props = { ...props, encounter: { ear: { ear_pain: true } }, ready: false };
    const hooks = createHooks();
    const view = () => render(hooks, () => AssessmentCapture(props));
    const checkbox = find(view(), (node) => node.type === "input" && node.props.type === "checkbox");
    (checkbox.props.onChange as (event: { target: { checked: boolean } }) => void)({ target: { checked: true } });
    let tree = view();
    expect(dirtySections.ear).toBe(true);
    expect(button(tree, "Review selected retractions").props.disabled).toBe(true);
    click(button(tree, "Review selected retractions"));
    expect(voice.retract).not.toHaveBeenCalled();
    props.ready = true;
    tree = view();
    click(button(tree, "Review selected retractions"));
    expect(voice.retract).toHaveBeenCalledWith("ear", ["ear.ear_pain"]);
    view();
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
    expect(vi.mocked(voice.clear).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(session.reset).mock.invocationCallOrder[0]);
  });
});
