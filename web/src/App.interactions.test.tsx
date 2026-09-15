import { isValidElement, type ReactElement, type ReactNode, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { AssessmentCapture } from "./components/AssessmentCapture";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
import { CaptureProgress } from "./components/CaptureProgress";
import { ClinicalFieldControl } from "./components/ClinicalFieldControl";
import { MobileAssessmentHome, MobileDock } from "./components/MobileWorkspace";
import { ResultPanel } from "./components/ResultPanel";
import { acceptAssessment, evaluateAssessment, extractAssessment, transcribeAudio } from "./lib/api";
import { draftKey } from "./lib/assessment";
import { clinicalValue } from "./lib/guideEvidence";
import { useMobileLayout } from "./lib/layout";
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
vi.mock("./lib/layout", () => ({ useMobileLayout: vi.fn() }));
vi.mock("./lib/api", () => ({ evaluateAssessment: vi.fn(), acceptAssessment: vi.fn(), extractAssessment: vi.fn(), transcribeAudio: vi.fn() }));

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
  vi.mocked(evaluateAssessment).mockReset();
  vi.mocked(useMobileLayout).mockReturnValue(false);
  voice = { jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
    addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
    retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(), stageField: vi.fn() };
  session = { version: 1, encounter: evaluation.encounter, attempted: [], revision: 2, evaluation, hasData: true, ready: true,
    busy: false, error: "", storageHint: "", currentRevision: () => session.revision,
    needsResumeDecision: false, resumeSaved: vi.fn().mockResolvedValue(false),
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
  vi.stubGlobal("document", { getElementById: vi.fn().mockReturnValue(null), querySelector: vi.fn().mockReturnValue(null), activeElement: null });
  vi.stubGlobal("HTMLElement", class {});
});
afterEach(() => { runtime.current = null; vi.unstubAllGlobals(); });

describe("explicit recommendation generation", () => {
  const partial: AssessmentEvaluation = { ...evaluation, analysis: { ...evaluation.analysis, is_complete: false, state: "INCOMPLETE",
    missing_elements: { ear: ["ear_discharge_reported"] }, rendered_response: "Information needed: check for ear discharge." } };
  function generate(tree: ReactNode) {
    const checklist = find(tree, (node) => node.type === AssessmentChecklist);
    return find(checklist.props.tools as ReactNode, (node) => node.type === "button" && node.props.className === "generate-assessment");
  }
  function expectNoProcessing() {
    for (const operation of [voice.startRecording, voice.addText, voice.prepareReview, voice.accept, voice.retry, voice.discard,
      voice.stageField, guide.confirm, session.accept, session.evaluate, session.rejectPending, transcribeAudio, extractAssessment, acceptAssessment])
      expect(operation).not.toHaveBeenCalled();
  }

  it.each(["empty", "partial", "urgent"])("renders the backend missing response for %s only after a successful new revision", async (kind) => {
    session.encounter = kind === "empty" ? {} : kind === "urgent" ? { danger_signs: { convulsing_now: true } } : partial.encounter;
    session.evaluation = { ...partial, encounter: session.encounter, analysis: { ...partial.analysis,
      state: kind === "urgent" ? "URGENT_INCOMPLETE" : "INCOMPLETE", is_urgent: kind === "urgent",
      urgent_actions: kind === "urgent" ? ["Begin accepted urgent care now."] : [] } };
    const fresh = { ...session.evaluation, analysis: { ...session.evaluation.analysis,
      rendered_response: `Backend ${kind} assessment: information needed before final management.` } };
    let resolve!: (success: boolean) => void;
    vi.mocked(session.refresh).mockImplementation(() => {
      session.busy = true;
      return new Promise<boolean>((yes) => { resolve = yes; });
    });
    const hooks = createHooks();
    const view = () => render(hooks, App);
    expect(renderToStaticMarkup(view())).not.toContain(partial.analysis.rendered_response);
    expect(generate(view()).props.disabled).toBe(false);
    click(generate(view()));
    expect(session.refresh).toHaveBeenCalledExactlyOnceWith();
    expect(find(view(), (node) => node.type === "main").props["data-active-panel"]).toBe("result");
    expect(renderToStaticMarkup(view())).toContain("Checking your confirmed findings");
    expect(elements(view()).some((node) => node.type === ResultPanel)).toBe(false);
    session.evaluation = fresh;
    session.revision++;
    session.busy = false;
    resolve(true);
    await Promise.resolve();
    const tree = view();
    expect(find(tree, (node) => node.type === ResultPanel).props.result).toBe(fresh.analysis);
    const html = renderToStaticMarkup(tree);
    expect(html).toContain(fresh.analysis.rendered_response);
    expect(html).toContain(kind === "urgent" ? "Act now, then complete rapidly" : "More findings are needed");
    expect(html).not.toContain("Ready when you are");
    expect(html).not.toContain("Clinical synthesis ready");
    expectNoProcessing();
    unmount(hooks);
  });

  it.each([{ success: false, increment: 1 }, { success: true, increment: 0 }, { success: true, increment: 2 }])(
    "does not authorize an incomplete report for refresh outcome %j", async ({ success, increment }) => {
      session.evaluation = partial;
      vi.mocked(session.refresh).mockImplementation(async () => { session.revision += increment; return success; });
      const hooks = createHooks();
      const view = () => render(hooks, App);
      click(generate(view()));
      await Promise.resolve();
      expect(elements(view()).some((node) => node.type === ResultPanel)).toBe(false);
      expect(renderToStaticMarkup(view())).not.toContain(partial.analysis.rendered_response);
      expectNoProcessing();
      unmount(hooks);
    });

  it("guards the generation handler itself while busy", () => {
    session.busy = true;
    const hooks = createHooks();
    const view = () => render(hooks, App);
    expect(generate(view()).props.disabled).toBe(true);
    click(generate(view()));
    expect(session.refresh).not.toHaveBeenCalled();
    expect(find(view(), (node) => node.type === "main").props["data-active-panel"]).toBe("assessment");
    expectNoProcessing();
    unmount(hooks);
  });

  it.each(["recording", "queued", "transcribing", "extracting", "captured", "preparing_review", "review", "applying", "failed",
    "worker", "dirty", "interrupted", "blocker", "contradiction", "BLOCK decision"])(
    "requests review rather than refreshing or accepting %s evidence", (gate) => {
      if (gate === "interrupted") session.interruptedCount = 1;
      else if (["blocker", "contradiction", "BLOCK decision"].includes(gate)) session.evaluation = { ...evaluation,
        analysis: { ...evaluation.analysis, contradictions: gate === "contradiction" ? ["Conflicting evidence"] : [] },
        assessments: { ...evaluation.assessments, ear: { ...complete, decision: gate === "BLOCK decision" ? "BLOCK" : "COMPLETE",
          blockers: gate === "blocker" ? ["Review ear evidence"] : [] } } };
      else if (gate !== "dirty") voice.jobs = [{ id: "pending-ear", assessment: "ear", status: gate === "worker" ? "captured" : gate as CaptureJob["status"],
        originalEncounter: {}, originalRevision: 2, reviewVersion: 0, changedFields: [],
        ...(gate === "worker" ? { originalCandidate: { assessment: "ear" as const, input_text: "", extraction_mode: "worker-review", warnings: [], changes: [] },
          workerEdits: { "ear.ear_pain": { value: false, previous: null, label: "Ear pain", revision: 2 } } } : {}),
        trace: { id: "pending-ear", timestamp: "today", assessment: "ear", status: "candidate", source: {} } }];
      const hooks = createHooks();
      const view = () => render(hooks, App);
      if (gate === "dirty") {
        const checklist = find(view(), (node) => node.type === AssessmentChecklist) as ReactElement<ComponentProps<typeof AssessmentChecklist>>;
        (checklist.props.renderCapture!("ear") as ReactElement<ComponentProps<typeof AssessmentCapture>>).props.onDirty({ ear: true });
      }
      const before = structuredClone({ jobs: voice.jobs, encounter: session.encounter, evaluation: session.evaluation });
      click(generate(view()));
      const tree = view();
      const html = renderToStaticMarkup(tree);
      expect(html).toContain(gate === "interrupted" ? "Acknowledge interrupted captures before final plan"
        : ["blocker", "contradiction", "BLOCK decision"].includes(gate) ? "Review evidence issues" : "Review findings before generating recommendations");
      expect(html).not.toContain("Accepted final plan");
      expect(session.refresh).not.toHaveBeenCalled();
      if (!["interrupted", "contradiction", "BLOCK decision"].includes(gate)) {
        const section = { open: false, querySelector: vi.fn().mockReturnValue({ focus: vi.fn() }), scrollIntoView: vi.fn() };
        vi.mocked(document.querySelector).mockReturnValue(section as unknown as HTMLDetailsElement);
        click(find(tree, (node) => node.type === "button" && node.props.className === "assessment-review-link"
          && renderToStaticMarkup(node).includes("Review Ear problem")));
        expect(document.querySelector).toHaveBeenCalledWith('details[data-assessment="ear"]');
        expect(section.open).toBe(true);
        expect(section.querySelector).toHaveBeenCalledWith("summary");
        expect(section.scrollIntoView).toHaveBeenCalledOnce();
        expect(find(view(), (node) => node.type === "main").props["data-active-panel"]).toBe("assessment");
        if (voice.jobs.length) expect(guide.selectJob).toHaveBeenCalledExactlyOnceWith("pending-ear");
        else expect(guide.selectJob).not.toHaveBeenCalled();
      }
      expect({ jobs: voice.jobs, encounter: session.encounter, evaluation: session.evaluation }).toEqual(before);
      expect(session.refresh).not.toHaveBeenCalled();
      expectNoProcessing();
      unmount(hooks);
    });

  it.each(["unready", "busy", "session error", "invalid", "analysis error", "out of scope"])(
    "withholds a requested incomplete report behind the %s result-ready guard", async (gate) => {
      session.evaluation = structuredClone(partial);
      vi.mocked(session.refresh).mockImplementation(async () => { session.revision++; return true; });
      const hooks = createHooks();
      const view = () => render(hooks, App);
      click(generate(view()));
      await Promise.resolve();
      expect(renderToStaticMarkup(view())).toContain(partial.analysis.rendered_response);
      if (gate === "unready") session.ready = false;
      if (gate === "busy") session.busy = true;
      if (gate === "session error") session.error = "Check failed";
      if (gate === "invalid") session.evaluation!.analysis.schema_valid = false;
      if (gate === "analysis error") session.evaluation!.analysis.error = "Invalid evidence";
      if (gate === "out of scope") session.evaluation!.analysis.outside_supported_scope = true;
      expect(renderToStaticMarkup(view())).not.toContain(partial.analysis.rendered_response);
      expect(elements(view()).some((node) => node.type === ResultPanel)).toBe(false);
      unmount(hooks);
    });

  it("invalidates an old incomplete report on a new accepted revision and clears it before a failed repeat request", async () => {
    session.evaluation = partial;
    vi.mocked(session.refresh).mockImplementation(async () => { session.revision++; return true; });
    const hooks = createHooks();
    const view = () => render(hooks, App);
    click(generate(view()));
    await Promise.resolve();
    expect(renderToStaticMarkup(view())).toContain(partial.analysis.rendered_response);
    session.revision++;
    session.encounter = { ...session.encounter, ear: { ear_pain: false } };
    session.evaluation = { ...partial, encounter: session.encounter, analysis: { ...partial.analysis, rendered_response: "New accepted partial report" } };
    expect(renderToStaticMarkup(view())).not.toContain("New accepted partial report");
    expect(renderToStaticMarkup(view())).not.toContain(partial.analysis.rendered_response);
    click(generate(view()));
    await Promise.resolve();
    expect(renderToStaticMarkup(view())).toContain("New accepted partial report");
    vi.mocked(session.refresh).mockResolvedValue(false);
    click(generate(view()));
    await Promise.resolve();
    expect(renderToStaticMarkup(view())).not.toContain("New accepted partial report");
    expect(session.refresh).toHaveBeenCalledTimes(3);
    expectNoProcessing();
    unmount(hooks);
  });

  async function liveSession(initial: AssessmentEvaluation) {
    const actual = await vi.importActual<typeof import("./lib/useAssessmentSession")>("./lib/useAssessmentSession");
    vi.mocked(useAssessmentSession).mockImplementation(actual.useAssessmentSession);
    vi.stubGlobal("sessionStorage", { getItem: vi.fn().mockReturnValue(null), setItem: vi.fn(), removeItem: vi.fn() });
    vi.mocked(evaluateAssessment).mockResolvedValueOnce(initial);
    const hooks = createHooks();
    const view = () => render(hooks, App);
    view();
    await Promise.resolve();
    view();
    return { hooks, view };
  }

  it("withholds a prior complete evaluation throughout failed refresh and retry until the real session succeeds", async () => {
    const { hooks, view } = await liveSession(evaluation);
    expect(renderToStaticMarkup(view())).toContain("Accepted final plan");
    vi.mocked(evaluateAssessment).mockRejectedValueOnce(new Error("Service unavailable"));
    click(generate(view()));
    expect(renderToStaticMarkup(view())).not.toContain("Accepted final plan");
    await Promise.resolve();
    await Promise.resolve();
    const failed = view();
    expect(renderToStaticMarkup(failed)).toContain("Could not check the assessment");
    expect(renderToStaticMarkup(failed)).not.toContain("Accepted final plan");
    expect(vi.mocked(useVoiceCapture).mock.lastCall![0].evaluation).toBe(evaluation);
    let resolve!: (value: AssessmentEvaluation) => void;
    vi.mocked(evaluateAssessment).mockReturnValueOnce(new Promise((yes) => { resolve = yes; }));
    click(button(failed, "Retry assessment"));
    expect(renderToStaticMarkup(view())).not.toContain("Accepted final plan");
    resolve(partial);
    await Promise.resolve();
    await Promise.resolve();
    expect(renderToStaticMarkup(view())).toContain(partial.analysis.rendered_response);
    expect(evaluateAssessment).toHaveBeenCalledTimes(3);
    expectNoProcessing();
    unmount(hooks);
  });

  it.each([false, true])("does not resurrect a deferred old report after reset, new check finished first=%s", async (newFirst) => {
    const { hooks, view } = await liveSession(partial);
    let resolveOld!: (value: AssessmentEvaluation) => void;
    let resolveNew!: (value: AssessmentEvaluation) => void;
    vi.mocked(evaluateAssessment).mockReturnValueOnce(new Promise((yes) => { resolveOld = yes; }))
      .mockReturnValueOnce(new Promise((yes) => { resolveNew = yes; }));
    click(generate(view()));
    const oldSignal = vi.mocked(evaluateAssessment).mock.lastCall![2]!;
    const checklist = find(view(), (node) => node.type === AssessmentChecklist);
    click(button(checklist.props.tools as ReactNode, "Clear encounter"));
    expect(oldSignal.aborted).toBe(true);
    const empty = { ...partial, encounter: {}, analysis: { ...partial.analysis, rendered_response: "New empty assessment missing findings" } };
    for (const resolve of newFirst ? [() => resolveNew(empty), () => resolveOld(partial)] : [() => resolveOld(partial), () => resolveNew(empty)]) {
      resolve();
      await Promise.resolve();
      await Promise.resolve();
      const html = renderToStaticMarkup(view());
      expect(html).toContain("Ready when you are");
      expect(html).not.toContain(partial.analysis.rendered_response);
      expect(html).not.toContain(empty.analysis.rendered_response);
      expect(find(view(), (node) => node.type === "main").props["data-active-panel"]).toBe("assessment");
    }
    expect(vi.mocked(useVoiceCapture).mock.lastCall![0].evaluation).toBe(empty);
    expect(vi.mocked(useVoiceCapture).mock.lastCall![0].encounter).toEqual({});
    expect(voice.clear).toHaveBeenCalledOnce();
    expect(guide.reset).toHaveBeenCalledOnce();
    expectNoProcessing();
    unmount(hooks);
  });
});

describe("typed draft context", () => {
  it.each([false, true])("uses Root authorization for typed fallback without a language, with mobile=%s", (mobile) => {
    vi.mocked(useMobileLayout).mockReturnValue(mobile);
    const rootHooks = createHooks();
    const captureHooks = createHooks();
    const root = () => render(rootHooks, App);
    const capture = () => {
      const checklist = find(root(), (node) => node.type === AssessmentChecklist) as ReactElement<ComponentProps<typeof AssessmentChecklist>>;
      return checklist.props.renderCapture!("ear") as ReactElement<ComponentProps<typeof AssessmentCapture>>;
    };
    const view = () => {
      const node = capture();
      return render(captureHooks, () => AssessmentCapture(node.props));
    };
    expect(capture().props.language).toBe("");
    expect(capture().props.consent).toEqual({ audio: true, understanding: true });
    edit(find(view(), (node) => node.props.id === "capture-text-ear"), "Synthetic typed finding");
    expect(button(view(), "Process typed finding").props.disabled).toBe(false);
    click(button(view(), "Process typed finding"));
    expect(voice.addText).toHaveBeenCalledExactlyOnceWith("ear", "Synthetic typed finding", true,
      { encounter: session.encounter, revision: session.revision, question: undefined });
    expect(voice.startRecording).not.toHaveBeenCalled();
    unmount(captureHooks);
    unmount(rootHooks);
  });

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
  it.each([false, true].flatMap((mobile) => [false, true].map((savedValue) => ({ mobile, savedValue }))))(
    "requires explicit resume of saved boolean=$savedValue with mobile=$mobile, then resets to unknown",
    async ({ mobile, savedValue }) => {
      const actual = await vi.importActual<typeof import("./lib/useAssessmentSession")>("./lib/useAssessmentSession");
      vi.mocked(useAssessmentSession).mockImplementation(actual.useAssessmentSession);
      vi.mocked(useMobileLayout).mockReturnValue(mobile);
      const savedEncounter = { ear: { ear_pain: savedValue }, danger_signs: { convulsing_now: savedValue } };
      const historical = { ...evaluation, encounter: savedEncounter, analysis: { ...evaluation.analysis,
        is_urgent: true, urgent_actions: ["Historical urgency"], rendered_response: "Historical final plan" } };
      const raw = JSON.stringify({ version: 1, encounter: savedEncounter, attempted: ["danger", "ear"], revision: 7,
        interactions: [{ id: "synthetic-saved", timestamp: "2026-09-15T12:00:00Z", assessment: "ear", status: "accepted",
          source: { submitted_text: "Synthetic saved report" }, result: historical }] });
      const storage = new Map([[draftKey, raw]]);
      vi.stubGlobal("sessionStorage", { getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => { storage.set(key, value); }, removeItem: (key: string) => storage.delete(key) });
      let resolve!: (value: AssessmentEvaluation) => void;
      vi.mocked(evaluateAssessment).mockReturnValueOnce(new Promise((yes) => { resolve = yes; }));
      vi.mocked(useGuideEditor).mockImplementation((active) => ({ ...guide, workingEncounter: active.encounter,
        field: (assessment, path) => !path.startsWith("danger_signs.") && path !== "ear.ear_pain" ? null : {
          descriptor: { path, label: path, kind: "boolean", nullable: true, assessments: [assessment] },
          value: clinicalValue(active.encounter, path), acceptedValue: clinicalValue(active.encounter, path), raw: undefined,
          error: undefined, jobId: "", pending: false, requiresChoice: false, disabled: !active.ready,
          source: "accepted", onChange: vi.fn(), onKeep: vi.fn(),
        } }));
      const hooks = createHooks();
      const view = () => render(hooks, App);
      const gate = view();
      const hookCount = hooks.cursor;
      const html = renderToStaticMarkup(gate);
      expect(html).toContain("Saved assessment</h1>");
      expect(html).not.toContain('role="radiogroup"');
      expect(html).not.toContain("Synthetic saved report");
      expect(html).not.toContain("Historical urgency");
      expect(elements(gate).some((node) => node.type === AssessmentChecklist)).toBe(false);
      expect(useVoiceCapture).toHaveBeenCalledOnce();
      expect(useGuideEditor).toHaveBeenCalledOnce();
      expect(evaluateAssessment).not.toHaveBeenCalled();
      expect(storage.get(draftKey)).toBe(raw);

      // Two clicks on the same rendered handler still consume the real session ref only once.
      click(button(gate, "Resume saved assessment"));
      click(button(gate, "Resume saved assessment"));
      const restoring = view();
      expect(hooks.cursor).toBe(hookCount);
      expect(evaluateAssessment).toHaveBeenCalledExactlyOnceWith(savedEncounter, ["danger", "ear"], expect.any(AbortSignal));
      expect(window.confirm).not.toHaveBeenCalled();
      expect(voice.clear).not.toHaveBeenCalled();
      expect(guide.reset).not.toHaveBeenCalled();
      const checklist = find(restoring, (node) => node.type === AssessmentChecklist);
      const renderField = checklist.props.renderField as (id: AssessmentId, path: string) => ReactNode;
      const control = find(renderField("ear", "ear.ear_pain"), (node) => node.type === ClinicalFieldControl);
      expect(control.props.value).toBe(savedValue);
      expect(control.props.disabled).toBe(true);
      expect(renderToStaticMarkup(control)).toContain(`aria-checked="true" tabindex="0" disabled="">${savedValue ? "Yes" : "No"}`);
      expect(renderToStaticMarkup(restoring)).not.toContain('aria-label="Immediate management"');
      expect(renderToStaticMarkup(restoring)).not.toContain('aria-label="View urgent guidance"');
      expect(renderToStaticMarkup(restoring)).not.toContain("Clinical synthesis ready");
      const fresh = { ...historical, analysis: { ...historical.analysis, state: "URGENT_COMPLETE" as const,
        urgent_actions: ["Fresh urgent action"], rendered_response: "Fresh urgent action\n\nFresh final plan" } };
      resolve(fresh);
      await Promise.resolve();
      const restoredHtml = renderToStaticMarkup(view());
      expect(restoredHtml.slice(restoredHtml.indexOf('<section class="output-panel"'))).toContain("Fresh urgent action");
      expect(restoredHtml.slice(0, restoredHtml.indexOf("<main"))).not.toContain("Fresh urgent action");
      expect(restoredHtml.split("Fresh urgent action")).toHaveLength(2);
      expect(restoredHtml).not.toContain("workspace-urgent");
      if (mobile) {
        const dock = find(view(), (node) => node.type === MobileDock) as ReactElement<ComponentProps<typeof MobileDock>>;
        dock.props.onLanguageChange("yo");
        expect(voice.startRecording).not.toHaveBeenCalled();
        (find(view(), (node) => node.type === MobileDock) as typeof dock).props.onSpeak();
        const snapshot = vi.mocked(useVoiceCapture).mock.lastCall![0].snapshot();
        expect(snapshot).toMatchObject({ encounter: savedEncounter, evaluation: fresh });
        expect(voice.startRecording).toHaveBeenCalledExactlyOnceWith("danger", "yo", { audio: true, understanding: true },
          { ...snapshot, question: undefined });
      }

      vi.mocked(evaluateAssessment).mockResolvedValueOnce({ ...evaluation, encounter: {}, analysis: { ...evaluation.analysis,
        is_complete: false, state: "INCOMPLETE", rendered_response: "Unknown observations" } });
      const resumed = find(view(), (node) => node.type === AssessmentChecklist) as ReactElement<ComponentProps<typeof AssessmentChecklist>>;
      expect((resumed.props.renderCapture!("ear") as ReactElement<ComponentProps<typeof AssessmentCapture>>).props.consent)
        .toEqual({ audio: true, understanding: true });
      expect(renderToStaticMarkup(view())).toContain("Synthetic saved report");
      const tools = mobile ? (find(resumed.props.mobileHome, (node) => node.type === MobileAssessmentHome)
        .props.tools as ReactNode) : resumed.props.tools;
      click(button(tools, mobile ? "Start new assessment" : "Clear encounter"));
      expect(voice.clear).toHaveBeenCalledOnce();
      expect(guide.reset).toHaveBeenCalledOnce();
      expect(storage.has(draftKey)).toBe(false);
      await Promise.resolve();
      const cleared = view();
      expect(hooks.cursor).toBe(hookCount);
      const empty = find(cleared, (node) => node.type === AssessmentChecklist);
      const emptyCapture = (empty.props.renderCapture as (id: AssessmentId) => ReactElement<ComponentProps<typeof AssessmentCapture>>)("ear");
      expect(emptyCapture.props.consent).toEqual({ audio: true, understanding: true });
      expect(empty.props.encounter).toEqual({});
      const emptyField = empty.props.renderField as typeof renderField;
      expect(find(emptyField("ear", "ear.ear_pain"), (node) => node.type === ClinicalFieldControl).props.value).toBeNull();
      expect(find(emptyField("danger", "danger_signs.convulsing_now"), (node) => node.type === ClinicalFieldControl).props.value).toBeNull();
      const clearedHtml = renderToStaticMarkup(cleared);
      expect(clearedHtml).toContain("Ready when you are");
      for (const hidden of ["Fresh urgent action", "Fresh final plan", "Historical urgency", "Synthetic saved report", "Saved assessment</h1>"])
        expect(clearedHtml).not.toContain(hidden);
      click(button(gate, "Resume saved assessment"));
      await Promise.resolve();
      expect(evaluateAssessment).toHaveBeenCalledTimes(2);
      expect(storage.has(draftKey)).toBe(false);
      expect(find(view(), (node) => node.type === AssessmentChecklist).props.encounter).toEqual({});
      unmount(hooks);
    });

  it.each([false, true])("only confirmed Start new leaves the saved gate and clears voice, guide, then session with mobile=%s", (mobile) => {
    vi.mocked(useMobileLayout).mockReturnValue(mobile);
    session.needsResumeDecision = true;
    vi.mocked(session.reset).mockImplementation(() => {
      session.needsResumeDecision = false;
      session.encounter = {};
      session.evaluation = null;
      session.hasData = false;
      session.ready = false;
    });
    const hooks = createHooks();
    const view = () => render(hooks, App);
    const tree = view();
    const hookCount = hooks.cursor;
    vi.mocked(window.confirm).mockReturnValue(false);
    click(button(tree, "Start new assessment"));
    expect(window.confirm).toHaveBeenCalledWith("Start a new assessment? This clears the saved answers, pending captures, and history in this tab.");
    expect(renderToStaticMarkup(view())).toContain("Saved assessment</h1>");
    for (const operation of [voice.clear, guide.reset, session.reset, session.resumeSaved]) expect(operation).not.toHaveBeenCalled();
    vi.mocked(window.confirm).mockReturnValue(true);
    click(button(tree, "Start new assessment"));
    for (const operation of [voice.clear, guide.reset, session.reset]) expect(operation).toHaveBeenCalledOnce();
    expect(vi.mocked(voice.clear).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(guide.reset).mock.invocationCallOrder[0]);
    expect(vi.mocked(guide.reset).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(session.reset).mock.invocationCallOrder[0]);
    const normal = view();
    expect(hooks.cursor).toBe(hookCount);
    expect(find(normal, (node) => node.type === AssessmentChecklist).key).toBe("1");
    expect(renderToStaticMarkup(normal)).not.toContain("Saved assessment</h1>");
    expect(session.resumeSaved).not.toHaveBeenCalled();
    expect(useVoiceCapture).toHaveBeenCalledTimes(3);
    expect(useGuideEditor).toHaveBeenCalledTimes(3);
    unmount(hooks);
  });

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
    expect(html.slice(0, html.indexOf("<main"))).not.toContain("Accepted urgent action");
    expect(html.slice(html.indexOf('<section class="output-panel"'))).toContain("Accepted urgent action");
    expect(html.split("Accepted urgent action")).toHaveLength(2);
    expect(html).not.toContain("workspace-urgent");
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

  it.each(["recording card", "global progress"])("opens and focuses a desktop origin section only after explicit review from %s", (source) => {
    setupJob();
    const focus = vi.fn();
    const section = { open: false, querySelector: vi.fn().mockReturnValue({ focus }), scrollIntoView: vi.fn() };
    vi.stubGlobal("document", { activeElement: null, querySelector: vi.fn().mockReturnValue(section) });
    vi.stubGlobal("HTMLElement", class {});
    const root = render(createHooks(), App);
    const tree = find(root, (node) => node.type === AssessmentChecklist);
    expect(section.open).toBe(false);
    expect(section.scrollIntoView).not.toHaveBeenCalled();
    const capture = (tree.props.renderCapture as (id: AssessmentId) => ReactElement<ComponentProps<typeof AssessmentCapture>>)("ear");
    const progress = find(root, (node) => node.type === CaptureProgress) as ReactElement<ComponentProps<typeof CaptureProgress>>;
    expect(progress.props.jobs).toBe(voice.jobs);
    expect(progress.props.onReview).toBe(capture.props.onReviewJob);
    expect(guide.selectJob).not.toHaveBeenCalled();
    const original = structuredClone(voice.jobs);
    if (source === "global progress") click(button(CaptureProgress(progress.props), "Review"));
    else capture.props.onReviewJob("guide-clip");
    expect(guide.selectJob).toHaveBeenCalledWith("guide-clip");
    expect(section.open).toBe(true);
    expect(focus).toHaveBeenCalledOnce();
    expect(section.scrollIntoView).toHaveBeenCalledOnce();
    expect(guide.confirm).not.toHaveBeenCalled();
    expect(voice.jobs).toEqual(original);
    for (const operation of [voice.accept, voice.discard, voice.prepareReview, voice.startRecording, voice.addText,
      voice.retry, voice.clear, session.accept, session.rejectPending]) expect(operation).not.toHaveBeenCalled();
  });

  it.each([false, true].flatMap((mobile) => ["schema", "unready", "busy", "invalid", "preparing_review", "applying"].map((gate) => ({ mobile, gate }))))("disables confirmation for $gate with mobile=$mobile", ({ mobile, gate }) => {
    vi.mocked(useMobileLayout).mockReturnValue(mobile);
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

  it.each([false, true].flatMap((mobile) => [undefined, 1].map((reviewRevision) => ({ mobile, reviewRevision }))))("labels stale context $reviewRevision as Refresh review with mobile=$mobile, delegating the first-click guard", ({ mobile, reviewRevision }) => {
    vi.mocked(useMobileLayout).mockReturnValue(mobile);
    setupJob({ originalRevision: 1, reviewRevision });
    const tree = footer();
    expect(renderToStaticMarkup(tree)).toContain(mobile ? "Answers changed. Refresh review." : "Refresh review first");
    click(button(tree, "Refresh review"));
    expect(guide.confirm).toHaveBeenCalledWith("ear");
    expect(voice.accept).not.toHaveBeenCalled();
  });

  it.each([false, true])("requires a separate no-change acknowledgement before calling confirm with mobile=%s", (mobile) => {
    vi.mocked(useMobileLayout).mockReturnValue(mobile);
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

  it("keeps flagged answers actionable without duplicating source and technical details in confirmation", () => {
    const guarded = { ...candidate, changes: [{ ...candidate.changes[0], uncertain: true }] };
    setupJob({ candidate: guarded, originalCandidate: guarded, question: { field: "ear.ear_pain", text: "Original question?" } });
    const tree = footer();
    const html = renderToStaticMarkup(tree);
    expect(html).toContain("Choose answers above or keep confirmed answers for 1 flagged observation(s)");
    expect(button(tree, "Ear pain")).toBeDefined();
    for (const text of ["Details: original report and review", "Original words", "Review metadata", "Control schema", "<pre", "<code"]) expect(html).not.toContain(text);
    expect(voice.jobs[0].originalCandidate).toEqual(guarded);
  });

  it.each([false, true])("focuses unresolved age in the single Scope editor with mobile=%s without accepting it", (mobile) => {
    vi.mocked(useMobileLayout).mockReturnValue(mobile);
    const age = { ...candidate.changes[0], field: "patient_facts.age_months", label: "Age", value: 12, uncertain: true, outside_assessment: true };
    const guarded = { ...candidate, changes: [age] };
    setupJob({ candidate: guarded, originalCandidate: guarded });
    guide.schema!.fields[age.field] = { path: age.field, label: "Age", kind: "integer", nullable: true, assessments: ["danger"] };
    const focus = vi.fn();
    const field = { querySelector: vi.fn().mockReturnValue({ focus }), scrollIntoView: vi.fn() };
    const section = { open: false };
    vi.mocked(document.querySelector).mockImplementation((selector) => selector === 'details[data-assessment="danger"]' ? section as unknown as HTMLDetailsElement
      : selector === '.assessment-scope [data-guide-field="patient_facts.age_months"]' ? field as unknown as HTMLElement : null);
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => { callback(0); return 1; });
    const hooks = createHooks();
    const view = () => find(render(hooks, App), (node) => node.type === AssessmentChecklist);
    const review = (view().props.renderSectionReview as (id: AssessmentId) => ReactNode)("ear");
    expect(renderToStaticMarkup(review)).toContain(mobile ? "1 answer(s) need review." : "1 flagged observation(s)");
    click(button(review, "Age"));
    expect(document.querySelector).toHaveBeenCalledWith('.assessment-scope [data-guide-field="patient_facts.age_months"]');
    expect(field.querySelector).toHaveBeenCalledWith("input, button");
    expect(focus).toHaveBeenCalledOnce();
    expect(field.scrollIntoView).toHaveBeenCalledOnce();
    expect(section.open).toBe(!mobile);
    if (mobile) expect(view().props.mobileView).toEqual({ screen: "assessment", assessment: "danger", tab: "guidance", intro: false });
    expect(guide.confirm).not.toHaveBeenCalled();
    expect(voice.accept).not.toHaveBeenCalled();
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
