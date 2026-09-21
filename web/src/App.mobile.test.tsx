import { isValidElement, type ComponentProps, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { AssessmentCapture } from "./components/AssessmentCapture";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
import { CaptureProgress } from "./components/CaptureProgress";
import { ClinicalFieldControl } from "./components/ClinicalFieldControl";
import { InteractionHistory } from "./components/InteractionHistory";
import { ResultPanel } from "./components/ResultPanel";
import { ReportPanel } from "./components/ReportPanel";
import { MobileAssessmentHome, MobileAssessmentTabs, MobileDock, MobileHeader, type MobileView } from "./components/MobileWorkspace";
import { assessmentIds } from "./lib/assessment";
import { buildChecklist } from "./lib/checklist";
import { useMobileLayout } from "./lib/layout";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import { useVoiceCapture, type CaptureJob } from "./lib/useVoiceCapture";
import { useGuideEditor } from "./lib/useGuideEditor";
import type { AssessmentEvaluation, AssessmentId } from "./types";

// The interaction-test scheduler invokes real App handlers without a DOM dependency.
// Paths below check structural reconciliation identity, not browser mount/state retention.
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
vi.mock("./lib/layout", () => ({ useMobileLayout: vi.fn() }));
vi.mock("./lib/useAssessmentSession", () => ({ useAssessmentSession: vi.fn() }));
vi.mock("./lib/useVoiceCapture", () => ({ useVoiceCapture: vi.fn() }));
vi.mock("./lib/useGuideEditor", () => ({ useGuideEditor: vi.fn() }));

let mounted: Hooks[];
function createHooks(): Hooks {
  const hooks: Hooks = { cursor: 0, values: [], setters: [], effects: new Map(), pending: [] };
  mounted.push(hooks);
  return hooks;
}
function render(hooks: Hooks, component: () => ReactNode) {
  hooks.cursor = 0;
  runtime.current = hooks;
  let tree: ReactNode;
  try { tree = component(); } finally { runtime.current = null; }
  hooks.pending.splice(0).forEach((effect) => effect());
  return tree;
}
type Element = ReactElement<Record<string, unknown>>;
function locations(tree: ReactNode, path: unknown[] = []): Array<{ node: Element; path: unknown[] }> {
  if (Array.isArray(tree)) return tree.flatMap((child, index) => locations(child, [...path, index]));
  if (!isValidElement<Record<string, unknown>>(tree)) return [];
  const identity = [...path, tree.type, tree.key];
  return [{ node: tree, path: identity }, ...locations(tree.props.children as ReactNode, identity)];
}
function find(tree: ReactNode, predicate: (node: Element) => boolean) {
  const entry = locations(tree).find(({ node }) => predicate(node));
  if (!entry) throw new Error("UI element not found");
  return entry.node;
}
function component<P>(tree: ReactNode, type: (props: P) => ReactNode) {
  return find(tree, (node) => node.type === type) as ReactElement<P>;
}
const button = (tree: ReactNode, label: string) => find(tree, (node) => node.type === "button" && node.props.children === label);
const click = (node: Element) => (node.props.onClick as () => void)();
const change = (node: Element, target: { value: string } | { checked: boolean }) =>
  (node.props.onChange as (event: { target: typeof target }) => void)({ target });

const complete = { status: "COMPLETE" as const, decision: "COMPLETE" as const, question: null, missing_fields: [], blockers: [] };
const evaluation: AssessmentEvaluation = {
  encounter: { patient_facts: { age_months: 24 }, ear: { ear_pain: true } },
  assessments: { danger: complete, respiratory: complete, diarrhoea: complete, fever: complete, ear: complete },
  analysis: { input_text: "", extraction_mode: "test", matched_case_id: null, structured_encounter: {}, structured_view: [],
    schema_valid: true, extraction_warnings: [], is_complete: true, missing_elements: {}, contradictions: [], is_urgent: false,
    classifications: ["Accepted routine classification"], urgent_actions: [], final_actions: ["Accepted routine management"],
    deferred_actions: [], rendered_response: "Accepted final plan", decision_trace: [], pipeline_trace: [], error: null,
    outside_supported_scope: false, state: "COMPLETE" },
};
function job(status: CaptureJob["status"], assessment: AssessmentId = "ear"): CaptureJob {
  const candidate: NonNullable<CaptureJob["candidate"]> = { assessment, input_text: assessment === "danger" ? "Original danger finding" : "Original ear finding", extraction_mode: "test", warnings: [],
    changes: [{ field: assessment === "danger" ? "danger_signs.convulsing_now" : "ear.ear_pain", label: assessment === "danger" ? "Convulsing now" : "Ear pain",
      previous: assessment === "danger" ? null : true, value: false, conflict: assessment !== "danger", outside_assessment: false }] };
  return { id: `${assessment}-clip`, assessment, language: "yo", status, inputText: "Original ear finding",
    originalEncounter: { ear: { ear_pain: null } }, originalRevision: 1, reviewRevision: 2, reviewVersion: 3,
    question: { field: "ear.ear_pain", text: "Original ear question?" }, changedFields: [],
    candidate, originalCandidate: candidate,
    trace: { id: `${assessment}-clip`, timestamp: "2026-09-15T12:00:00Z", assessment, status: "candidate", source: {} } };
}
let voice: ReturnType<typeof useVoiceCapture>;
let session: ReturnType<typeof useAssessmentSession>;
let guide: ReturnType<typeof useGuideEditor>;
beforeEach(() => {
  mounted = [];
  vi.clearAllMocks();
  vi.mocked(useMobileLayout).mockReturnValue(true);
  voice = { jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
    addText: vi.fn().mockReturnValue(true), prepareReview: vi.fn().mockResolvedValue(undefined), accept: vi.fn().mockResolvedValue(undefined),
    retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(), stageField: vi.fn() };
  session = { version: 1, encounter: structuredClone(evaluation.encounter), attempted: [], revision: 2,
    evaluation: structuredClone(evaluation), hasData: true, ready: true, busy: false, error: "", storageHint: "",
    currentRevision: () => session.revision, snapshot: () => ({ encounter: session.encounter, revision: session.revision, evaluation: session.evaluation }),
    interruptedCount: 0, acknowledgeInterrupted: vi.fn(), refresh: vi.fn().mockResolvedValue(true), reset: vi.fn(),
    needsResumeDecision: false, resumeSaved: vi.fn().mockResolvedValue(false),
    evaluate: vi.fn().mockResolvedValue(true), accept: vi.fn().mockResolvedValue(true), interactions: [], recordInteraction: vi.fn(), rejectPending: vi.fn() };
  vi.mocked(useAssessmentSession).mockReturnValue(session);
  vi.mocked(useVoiceCapture).mockReturnValue(voice);
  guide = { schema: { schema_id: "test", schema_sha256: "test", fields: {} }, schemaError: "",
    workingEncounter: session.encounter, pendingFieldPaths: [], field: vi.fn().mockReturnValue(null),
    selectedJob: (assessment) => voice.jobs.find((item) => item.assessment === assessment && item.status !== "accepted" && item.status !== "discarded"), selectJob: vi.fn(),
    confirm: vi.fn().mockResolvedValue(undefined), reset: vi.fn(), retrySchema: vi.fn() };
  vi.mocked(useGuideEditor).mockReturnValue(guide);
  vi.stubGlobal("window", { addEventListener: vi.fn(), removeEventListener: vi.fn(), confirm: vi.fn().mockReturnValue(true) });
  vi.stubGlobal("document", { getElementById: vi.fn().mockReturnValue(null), querySelector: vi.fn().mockReturnValue(null), activeElement: null });
  vi.stubGlobal("HTMLElement", class {});
});
afterEach(() => {
  mounted.forEach((hooks) => hooks.effects.forEach((effect) => effect.cleanup?.()));
  runtime.current = null;
  vi.unstubAllGlobals();
});

function workspace() {
  const rootHooks = createHooks();
  const checklistHooks = createHooks();
  const root = () => render(rootHooks, App);
  const checklist = () => component(root(), AssessmentChecklist);
  const captures = () => {
    const node = checklist();
    return render(checklistHooks, () => AssessmentChecklist(node.props));
  };
  const navigate = (view: MobileView, source: "home" | "tabs" | "dock" | "header" = "dock") => {
    if (source === "home") component(checklist().props.mobileHome, MobileAssessmentHome).props.onNavigate(view);
    else if (source === "tabs") component(checklist().props.mobileFocus, MobileAssessmentTabs).props.onNavigate(view);
    else if (source === "header") component(root(), MobileHeader).props.onNavigate(view);
    else component(root(), MobileDock).props.onNavigate(view);
  };
  const tools = () => component(checklist().props.mobileHome, MobileAssessmentHome).props.tools;
  return { root, checklist, captures, navigate, tools };
}
const intro: MobileView = { screen: "assessment", assessment: "danger", tab: "guidance", intro: true };
const views: MobileView[] = [
  { screen: "list", assessment: null, tab: "guidance" },
  { screen: "assessment", assessment: "ear", tab: "guidance" },
  { screen: "assessment", assessment: "ear", tab: "findings" },
  { screen: "assessment", assessment: "fever", tab: "guidance" },
  { screen: "results", assessment: "fever", tab: "guidance" },
  { screen: "report", assessment: null, tab: "guidance" },
];
function expectNavigationOnly() {
  for (const operation of [voice.clear, voice.cancelRecording, voice.stop, voice.accept, voice.prepareReview,
    voice.startRecording, voice.addText, voice.retry, voice.discard, voice.retract, voice.stageField, session.refresh, session.reset, session.accept, session.rejectPending, guide.confirm]) {
    expect(operation).not.toHaveBeenCalled();
  }
}

describe("integrated mobile workspace", () => {
  it("opens Write text from intro and Text report from the dock without ASR, reset or losing either editor", () => {
    const app = workspace();
    const report = () => component(app.root(), ReportPanel).props;
    const captureHooks = createHooks();
    const capture = () => {
      const node = component(app.checklist().props.renderCapture!("ear"), AssessmentCapture);
      return render(captureHooks, () => AssessmentCapture(node.props));
    };
    change(find(capture(), (node) => node.props.id === "capture-text-ear"), { value: "Retain scoped ear edit" });
    const key = app.checklist().key;
    const dock = () => MobileDock(component(app.root(), MobileDock).props);
    click(button(dock(), "Write text"));
    const reportView: MobileView = { screen: "report", assessment: null, tab: "guidance" };
    expect(app.checklist().props.mobileView).toEqual(reportView);
    expect(find(app.root(), (node) => node.type === "main").props["data-mobile-screen"]).toBe("report");
    expect(renderToStaticMarkup(component(app.root(), MobileHeader))).toContain('id="mobile-view-heading" tabindex="-1">Text report');
    expect(renderToStaticMarkup(dock())).not.toContain('aria-label="Speak"');
    report().onChange("Retain full report draft");
    for (const target of [views[0], views[1], views[4]]) {
      app.navigate(target);
      click(find(dock(), (node) => node.type === "button" && renderToStaticMarkup(node).includes("<span>Text report</span>")));
      expect(app.checklist().props.mobileView).toEqual(reportView);
      expect(report().text).toBe("Retain full report draft");
      expect(find(capture(), (node) => node.props.id === "capture-text-ear").props.value).toBe("Retain scoped ear edit");
      expect(app.checklist().key).toBe(key);
    }
    expectNavigationOnly();
    expect(guide.reset).not.toHaveBeenCalled();
    expect(session.evaluate).not.toHaveBeenCalled();
    app.navigate(views[0]);
    click(button(app.tools(), "Start new assessment"));
    expect(report().text).toBe("");
    expect(session.reset).toHaveBeenCalledOnce();
    expect(app.checklist().key).not.toBe(key);
  });

  it.each(["captured", "review", "failed"] as const)("routes full-note %s review to the report screen, not a fabricated assessment", (status) => {
    const candidate: NonNullable<CaptureJob["candidate"]> = { assessment: "full-note", input_text: "Synthetic report", extraction_mode: "test", warnings: [],
      changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: true, value: false, conflict: true, outside_assessment: false }] };
    const pending: CaptureJob = { ...job(status), id: "text-report", assessment: "full-note", language: undefined,
      candidate, originalCandidate: candidate, question: undefined,
      trace: { id: "text-report", assessment: "full-note", timestamp: "today", status: "candidate", source: { submitted_text: "Synthetic report" } } };
    voice.jobs = [pending, job("queued", "danger")];
    const before = structuredClone(voice.jobs);
    const app = workspace();
    const report = () => component(app.root(), ReportPanel).props;
    report().onChange("Keep newer unprocessed report");
    app.navigate(views[4]);
    const root = app.root();
    const progress = component(root, CaptureProgress);
    expect(progress.props.onReview).toBe(component(root, ReportPanel).props.onReviewJob);
    click(button(CaptureProgress(progress.props), status === "failed" ? "View report" : "Review"));
    expect(guide.selectJob).toHaveBeenCalledExactlyOnceWith("text-report");
    expect(app.checklist().props.mobileView).toEqual({ screen: "report", assessment: null, tab: "guidance" });
    expect(find(app.root(), (node) => node.type === "main").props).toMatchObject({ "data-active-panel": "report", "data-mobile-screen": "report", "data-mobile-assessment": undefined });
    expect(report().text).toBe("Keep newer unprocessed report");
    expect(document.querySelector).not.toHaveBeenCalledWith('details[data-assessment="full-note"]');
    expect(voice.jobs).toEqual(before);
    expectNavigationOnly();
  });

  it("routes blocked generation back to an unprocessed text report without processing it", () => {
    const app = workspace();
    component(app.root(), ReportPanel).props.onChange("Unprocessed full report");
    app.navigate(views[0]);
    const home = component(app.checklist().props.mobileHome, MobileAssessmentHome);
    click(find(MobileAssessmentHome(home.props), (node) => node.props.className === "generate-assessment"));
    expect(app.checklist().props.mobileView?.screen).toBe("results");
    expect(renderToStaticMarkup(app.root())).toContain("Review findings before generating recommendations");
    click(find(app.root(), (node) => node.props.className === "assessment-review-link" && renderToStaticMarkup(node).includes("Review text report")));
    expect(app.checklist().props.mobileView).toEqual({ screen: "report", assessment: null, tab: "guidance" });
    expect(component(app.root(), ReportPanel).props.text).toBe("Unprocessed full report");
    expectNavigationOnly();
  });

  it.each(["empty", "partial", "urgent"])("uses the shared Home generation handler for %s while dock Results remains navigation-only", async (kind) => {
    session.encounter = kind === "empty" ? {} : kind === "urgent" ? { danger_signs: { convulsing_now: true } } : evaluation.encounter;
    session.evaluation = { ...evaluation, encounter: session.encounter, analysis: { ...evaluation.analysis,
      is_complete: false, state: kind === "urgent" ? "URGENT_INCOMPLETE" : "INCOMPLETE", is_urgent: kind === "urgent",
      urgent_actions: kind === "urgent" ? ["Accepted urgent care now"] : [],
      missing_elements: { patient_facts: ["age_months"] }, rendered_response: `Backend ${kind} missing findings response` } };
    let resolve!: (success: boolean) => void;
    vi.mocked(session.refresh).mockImplementation(() => {
      session.busy = true;
      return new Promise<boolean>((yes) => { resolve = yes; });
    });
    const app = workspace();
    app.navigate(views[0]);
    const dock = MobileDock(component(app.root(), MobileDock).props);
    click(find(dock, (node) => node.type === "button" && renderToStaticMarkup(node).includes("<span>Results</span>")));
    expect(app.checklist().props.mobileView?.screen).toBe("results");
    expect(renderToStaticMarkup(app.root())).not.toContain(session.evaluation.analysis.rendered_response);
    expectNavigationOnly();
    app.navigate(views[0]);
    const home = component(app.checklist().props.mobileHome, MobileAssessmentHome);
    const action = find(MobileAssessmentHome(home.props), (node) => node.type === "button" && node.props.className === "generate-assessment");
    expect(action.props.onClick).toBe(find(home.props.assessmentAction, (node) => node.type === "button").props.onClick);
    expect(action.props.disabled).toBe(false);
    click(action);
    expect(session.refresh).toHaveBeenCalledExactlyOnceWith();
    expect(app.checklist().props.mobileView?.screen).toBe("results");
    expect(find(app.root(), (node) => node.type === "main").props["data-active-panel"]).toBe("result");
    expect(renderToStaticMarkup(app.root())).toContain("Checking your confirmed findings");
    expect(renderToStaticMarkup(app.root())).not.toContain(session.evaluation.analysis.rendered_response);
    const checkingHome = component(app.checklist().props.mobileHome, MobileAssessmentHome);
    const checking = find(MobileAssessmentHome(checkingHome.props), (node) => node.props.className === "generate-assessment");
    expect(checking.props.disabled).toBe(true);
    click(checking);
    expect(session.refresh).toHaveBeenCalledOnce();
    session.busy = false;
    session.revision++;
    resolve(true);
    await Promise.resolve();
    expect(component(app.root(), ResultPanel).props.result).toBe(session.evaluation.analysis);
    const html = renderToStaticMarkup(app.root());
    expect(html).toContain(session.evaluation.analysis.rendered_response);
    expect(html).toContain(kind === "urgent" ? "Act now, then complete rapidly" : "More findings are needed");
    expect(html).not.toContain("Ready when you are");
    for (const operation of [voice.startRecording, voice.addText, voice.prepareReview, voice.accept, voice.stageField, guide.confirm, session.accept])
      expect(operation).not.toHaveBeenCalled();
  });

  it.each(["captured", "failed", "worker", "dirty", "blocker"])(
    "routes the generation review link for %s to the correct mobile assessment tab without processing", (gate) => {
      if (gate === "blocker") session.evaluation!.assessments.ear = { ...complete, decision: "BLOCK", blockers: ["Review ear evidence"] };
      else if (gate !== "dirty") {
        const pending = job(gate === "failed" ? "failed" : "captured");
        if (gate === "worker") {
          pending.originalCandidate = { ...pending.originalCandidate!, extraction_mode: "worker-review", changes: [] };
          pending.workerEdits = { "ear.ear_pain": { value: false, previous: null, label: "Ear pain", revision: 2 } };
        }
        voice.jobs = [pending];
      }
      const original = structuredClone({ jobs: voice.jobs, evaluation: session.evaluation });
      const app = workspace();
      if (gate === "dirty") component(app.checklist().props.renderCapture!("ear"), AssessmentCapture).props.onDirty({ ear: true });
      app.navigate(views[0]);
      const home = component(app.checklist().props.mobileHome, MobileAssessmentHome);
      click(find(MobileAssessmentHome(home.props), (node) => node.props.className === "generate-assessment"));
      expect(app.checklist().props.mobileView?.screen).toBe("results");
      expect(find(app.root(), (node) => node.type === "main").props["data-active-panel"]).toBe("result");
      const html = renderToStaticMarkup(app.root());
      expect(html).toContain(gate === "blocker" ? "Review evidence issues" : "Review findings before generating recommendations");
      expect(html).not.toContain("Accepted final plan");
      const link = find(app.root(), (node) => node.props.className === "assessment-review-link" && renderToStaticMarkup(node).includes("Review Ear problem"));
      click(link);
      expect(app.checklist().props.mobileView).toEqual({ screen: "assessment", assessment: "ear", tab: gate === "failed" || gate === "dirty" ? "findings" : "guidance" });
      expect(find(app.root(), (node) => node.type === "main").props["data-active-panel"]).toBe("assessment");
      if (voice.jobs.length) expect(guide.selectJob).toHaveBeenCalledExactlyOnceWith("ear-clip");
      else expect(guide.selectJob).not.toHaveBeenCalled();
      expect({ jobs: voice.jobs, evaluation: session.evaluation }).toEqual(original);
      expectNavigationOnly();
    });

  it("selects language directly in the dock without speaking or navigating, then speaks only on an explicit click", () => {
    const app = workspace();
    const onSpeak = vi.fn();
    const dock = () => {
      const props = component(app.root(), MobileDock).props;
      return MobileDock({ ...props, onSpeak: () => { onSpeak(); props.onSpeak(); } });
    };
    const speak = () => find(dock(), (node) => node.props["aria-label"] === "Speak");
    expect(speak().props.disabled).toBe(true);
    click(speak());
    for (const value of ["yo", "ha", ""]) {
      change(find(dock(), (node) => node.props.id === "mobile-speech-language"), { value });
      expect(component(app.root(), MobileDock).props.language).toBe(value);
      expect(app.checklist().props.mobileView).toEqual(intro);
      expect(onSpeak).not.toHaveBeenCalled();
      expectNavigationOnly();
    }
    component(app.root(), MobileDock).props.onLanguageChange("en");
    session.ready = false;
    expect(speak().props.disabled).toBe(true);
    click(speak());
    expect(onSpeak).not.toHaveBeenCalled();
    session.ready = true;
    expect(speak().props.disabled).toBe(false);
    click(speak());
    expect(onSpeak).toHaveBeenCalledOnce();
    expect(voice.startRecording).toHaveBeenCalledExactlyOnceWith("danger", "en", { audio: true, understanding: true },
      { ...session.snapshot(), question: undefined });
  });

  it("keeps About, original history and New assessment in Home tools before generation with no mobile setup UI", () => {
    const pending = job("review");
    session.interactions = [{ ...pending.trace, source: { submitted_text: "Retained source words" }, candidate: pending.originalCandidate }];
    const original = structuredClone(session.interactions);
    const app = workspace();
    for (const view of [intro, ...views]) {
      app.navigate(view);
      const root = app.root();
      expect((root as Element).props["data-mobile-intro"]).toBe(view.intro || undefined);
      expect(app.checklist().props.guideStatus).toBe(false);
      expect(app.checklist().props.tools).toBe(false);
      const html = renderToStaticMarkup(root);
      for (const removed of ['type="checkbox"', "capture-toolbar", "capture-settings", "Encounter recording settings", "lucide-settings", 'data-mobile-screen="settings"'])
        expect(html).not.toContain(removed);
      const home = renderToStaticMarkup(app.checklist().props.mobileHome);
      for (const label of ["About processing", "Recording history (1)", "Retained source words", "Start new assessment"]) {
        expect(home).toContain(label);
        expect(home.indexOf(label)).toBeLessThan(home.indexOf("Generate IMCI recommendations"));
      }
      expect(component(app.tools(), InteractionHistory).props.interactions).toBe(session.interactions);
    }
    expect(session.interactions).toEqual(original);
    expectNavigationOnly();
  });

  it.each([false, true])(
    "shares deployment authorization across layouts and after reset with mobile=%s",
    (mobile) => {
      const app = workspace();
      const capture = () => component(app.checklist().props.renderCapture!("ear"), AssessmentCapture);
      const captureHooks = createHooks();
      const record = () => {
        const node = capture();
        return find(render(captureHooks, () => AssessmentCapture(node.props)), (node) => node.props.className === "record-findings");
      };
      vi.mocked(useMobileLayout).mockReturnValue(false);
      expect(record().props.disabled).toBe(true);
      expect(renderToStaticMarkup(app.root())).not.toContain('type="checkbox"');
      change(find(app.checklist().props.guideStatus, (node) => node.props.id === "capture-language"), { value: "yo" });
      expect(voice.startRecording).not.toHaveBeenCalled();
      expect(capture().props.consent).toEqual({ audio: true, understanding: true });
      expect(record().props.disabled).toBe(false);
      click(record());
      expect(voice.startRecording).toHaveBeenCalledExactlyOnceWith("ear", "yo", { audio: true, understanding: true });
      vi.mocked(useMobileLayout).mockReturnValue(true);
      expect(capture().props.consent).toEqual({ audio: true, understanding: true });
      expect(component(app.root(), MobileDock).props.language).toBe("yo");
      component(app.root(), MobileDock).props.onSpeak();
      expect(voice.startRecording).toHaveBeenCalledTimes(2);
      expect(voice.startRecording).toHaveBeenLastCalledWith("danger", "yo", { audio: true, understanding: true },
        { ...session.snapshot(), question: undefined });
      vi.mocked(useMobileLayout).mockReturnValue(false);
      expect(capture().props.consent).toEqual({ audio: true, understanding: true });
      expect(record().props.disabled).toBe(false);
      vi.mocked(useMobileLayout).mockReturnValue(mobile);
      if (mobile) app.navigate(views[0]);
      click(button(mobile ? app.tools() : app.checklist().props.tools, mobile ? "Start new assessment" : "Clear encounter"));
      expect(session.reset).toHaveBeenCalledOnce();
      vi.mocked(useMobileLayout).mockReturnValue(false);
      expect(renderToStaticMarkup(app.root())).not.toContain('type="checkbox"');
      expect(capture().props.consent).toEqual({ audio: true, understanding: true });
      expect(record().props.disabled).toBe(false);
      expect(voice.startRecording).toHaveBeenCalledTimes(2);
      expect(session.accept).not.toHaveBeenCalled();
      expect(guide.confirm).not.toHaveBeenCalled();
    });

  it("routes an explicit recording review to its assessment without discarding other drafts", () => {
    voice.jobs = [job("review"), { ...job("review"), id: "other-clip", assessment: "fever" }];
    const app = workspace();
    app.navigate({ screen: "assessment", assessment: "ear", tab: "findings" });
    const capture = app.checklist().props.renderCapture!("ear") as ReactElement<ComponentProps<typeof AssessmentCapture>>;
    const original = structuredClone(voice.jobs);
    capture.props.onReviewJob("ear-clip");
    expect(vi.mocked(useGuideEditor).mock.results[0].value.selectJob).toHaveBeenCalledWith("ear-clip");
    expect(app.checklist().props.mobileView).toEqual({ screen: "assessment", assessment: "ear", tab: "guidance" });
    expect(voice.jobs).toEqual(original);
    expect(voice.discard).not.toHaveBeenCalled();
    expect(voice.accept).not.toHaveBeenCalled();
  });

  it("keeps the same capture jobs in one global progress region across navigation and layout changes", () => {
    const statuses = ["queued", "transcribing", "extracting", "captured", "review", "preparing_review", "applying", "failed"] as const;
    voice.jobs = statuses.map((status, index) => ({ ...job(status, assessmentIds[index % assessmentIds.length]), id: `clip-${status}` }));
    const jobs = voice.jobs;
    const original = structuredClone(jobs);
    const app = workspace();
    expect(app.checklist().props.mobileView).toEqual(intro);
    let identity: unknown[] | undefined;
    for (const mobile of [true, false, true]) {
      vi.mocked(useMobileLayout).mockReturnValue(mobile);
      for (const view of [intro, ...views]) {
        app.navigate(view);
        const root = app.root();
        const regions = locations(root).filter(({ node }) => node.type === CaptureProgress);
        expect(regions).toHaveLength(1);
        expect(regions[0].path).not.toContain("main");
        identity ??= regions[0].path;
        expect(regions[0].path).toEqual(identity);
        expect(component(root, CaptureProgress).props.jobs).toBe(jobs);
        const html = renderToStaticMarkup(root);
        const global = html.slice(0, html.indexOf("<main"));
        expect(global).toContain('aria-label="Recording progress"');
        for (const status of statuses) expect(global).toContain(`data-stage="${status}"`);
        expect(html.match(/aria-label="Recording progress"/g)).toHaveLength(1);
        expect(html).not.toContain("mobile-intro-feedback");
        expect(app.checklist().props.mobileView).toEqual(mobile ? view : undefined);
        expect(voice.jobs).toBe(jobs);
        expect(jobs).toEqual(original);
        expect(guide.selectJob).not.toHaveBeenCalled();
        expectNavigationOnly();
      }
    }
  });

  it.each(["captured", "review", "failed"] as const)(
    "routes the global %s action to its own assessment without accepting or discarding findings", (status) => {
      const app = workspace();
      for (const assessment of ["ear", "danger"] as const) {
        app.navigate({ screen: "results", assessment: "fever", tab: "guidance" });
        const pending = job("transcribing", assessment);
        voice.jobs = [pending, job("queued", "respiratory")];
        expect(app.checklist().props.mobileView).toEqual({ screen: "results", assessment: "fever", tab: "guidance" });
        pending.status = status;
        const original = structuredClone(voice.jobs);
        const root = app.root();
        expect(app.checklist().props.mobileView).toEqual({ screen: "results", assessment: "fever", tab: "guidance" });
        expectNavigationOnly();
        const progress = component(root, CaptureProgress);
        const capture = component(component(root, AssessmentChecklist).props.renderCapture!(assessment), AssessmentCapture);
        expect(progress.props.onReview).toBe(capture.props.onReviewJob);
        click(button(CaptureProgress(progress.props), status === "failed" ? "View recording" : "Review"));
        expect(guide.selectJob).toHaveBeenLastCalledWith(pending.id);
        expect(app.checklist().props.mobileView).toEqual({ screen: "assessment", assessment, tab: status === "failed" ? "findings" : "guidance" });
        expect(voice.jobs).toEqual(original);
        expect(voice.jobs[0]).toBe(pending);
        expectNavigationOnly();
      }
      expect(guide.selectJob).toHaveBeenCalledTimes(2);
    });

  it("starts with the five canonical danger controls and preserves their identity through intro, full review, and layout switches", () => {
    const items = buildChecklist({}).sections[0].items;
    expect(items).toHaveLength(5);
    const onChange = vi.fn();
    vi.mocked(guide.field).mockImplementation((_assessment, path) => {
      const item = items.find((item) => item.id === path);
      return item ? { descriptor: { path, label: item.label, kind: "boolean", nullable: true, assessments: ["danger"] },
        value: null, acceptedValue: null, raw: undefined, error: undefined, jobId: "",
        pending: false, requiresChoice: false, disabled: false, source: "accepted", onChange, onKeep: vi.fn() } : null;
    });
    const before = structuredClone(session.encounter);
    const app = workspace();
    expect(app.checklist().props.mobileView).toEqual(intro);
    expect((app.root() as Element).props["data-mobile-intro"]).toBe(true);
    expect(find(app.root(), (node) => node.type === "main").props).toMatchObject({
      "data-mobile-screen": "assessment", "data-mobile-assessment": "danger", "data-mobile-tab": "guidance", "data-mobile-intro": true,
      "data-show-age": undefined,
    });
    let identity: unknown[][] | undefined;
    for (const [mobile, view] of [[true, intro], [true, { ...intro, intro: false }], [false, intro], [true, intro]] as const) {
      vi.mocked(useMobileLayout).mockReturnValue(mobile);
      app.navigate(view);
      const danger = find(app.captures(), (node) => node.type === "details" && node.props["data-assessment"] === "danger");
      const controls = locations(danger).filter(({ node }) => node.type === ClinicalFieldControl);
      expect(controls.map(({ node }) => (node.props.descriptor as { path: string }).path)).toEqual(items.map((item) => item.id));
      identity ??= controls.map(({ path }) => path);
      expect(controls.map(({ path }) => path)).toEqual(identity);
      for (const { node } of controls) expect(node.props).toMatchObject({ compact: mobile, value: null, onChange });
      expect(controls[0].node.props.booleanLabels).toEqual({ yes: "Unable", no: "Able" });
      const html = renderToStaticMarkup(danger);
      for (const item of items) expect(html).toContain(`<span class="danger-compact-label">${item.label}</span>`);
      expect(html).toContain('tabindex="-1">Unable</button>');
      expect(html).toContain('tabindex="-1">Able</button>');
      expect(html).not.toContain("patient_facts.age_months");
    }
    expect(onChange).not.toHaveBeenCalled();
    expect(session.encounter).toEqual(before);
    expectNavigationOnly();
  });

  it("reuses one Scope age editor across views and layouts, with no editable Home or Tabs copies", () => {
    const app = workspace();
    guide.pendingFieldPaths = ["patient_facts.age_months"];
    const age = { descriptor: { path: "patient_facts.age_months", label: "Age", kind: "integer" as const, nullable: true, unit: "months", assessments: ["danger" as const] },
      value: 12, raw: "12.", acceptedValue: 24, source: "worker" as const, pending: true, requiresChoice: false, disabled: false, error: undefined,
      jobId: "danger-draft", onChange: vi.fn(), onKeep: vi.fn() };
    vi.mocked(guide.field).mockImplementation((assessment, path) => assessment === "danger" && path === age.descriptor.path ? age : null);
    let identity: unknown[] | undefined;
    for (const mobile of [true, false, true]) {
      vi.mocked(useMobileLayout).mockReturnValue(mobile);
      for (const view of [intro, ...views]) {
        app.navigate(view);
        const tree = app.captures();
        const scopes = locations(tree).filter(({ node }) => node.props.className === "assessment-scope");
        expect(scopes).toHaveLength(1);
        const controls = locations(tree).filter(({ node }) => node.type === ClinicalFieldControl);
        expect(controls).toHaveLength(1);
        identity ??= controls[0].path;
        expect(controls[0].path).toEqual(identity);
        expect(component(scopes[0].node, ClinicalFieldControl).props).toMatchObject({ ...age, compact: mobile });
        if (mobile) {
          for (const chrome of [app.checklist().props.mobileHome, app.checklist().props.mobileFocus]) {
            expect((chrome as Element).props).not.toHaveProperty("ageControl");
            expect(renderToStaticMarkup(chrome)).not.toMatch(/<input|data-guide-field|Confirm age/);
          }
        }
      }
    }
    component(app.captures(), ClinicalFieldControl).props.onChange("13");
    expect(age.onChange).toHaveBeenCalledExactlyOnceWith("13");
    app.navigate(views[0]);
    expect(renderToStaticMarkup(app.checklist().props.ageReview)).toContain("Review age with");
    click(find(app.checklist().props.ageReview, (node) => node.type === "button"));
    expect(app.checklist().props.mobileView).toEqual({ ...intro, intro: false });
    expect(guide.confirm).not.toHaveBeenCalled();
    expect(voice.addText).not.toHaveBeenCalled();
    expect(voice.accept).not.toHaveBeenCalled();
  });

  it.each(["known", "unknown", "pending"])("uses main visibility attributes for %s age without exposing Scope on intro", (state) => {
    if (state === "unknown") session.encounter = { patient_facts: { age_months: null } };
    if (state === "pending") guide.pendingFieldPaths = ["patient_facts.age_months"];
    const app = workspace();
    for (const view of [intro, ...views]) {
      app.navigate(view);
      expect(find(app.root(), (node) => node.type === "main").props["data-show-age"])
        .toBe(!view.intro && (view.screen === "list" || view.screen === "assessment" && state !== "known") || undefined);
    }
    vi.mocked(useMobileLayout).mockReturnValue(false);
    app.navigate(views[0]);
    expect(find(app.root(), (node) => node.type === "main").props["data-show-age"]).toBeUndefined();
  });

  it.each(["age-only", "danger finding", "outside-assessment finding", "new worker edit"])("only allows overview Confirm age for an age-only report: %s", (scope) => {
    const pending = job("review", "danger");
    const age = { field: "patient_facts.age_months", label: "Age", previous: null, value: 12, conflict: false, outside_assessment: false };
    pending.candidate!.changes = [age, ...(scope === "danger finding" ? pending.candidate!.changes : scope === "outside-assessment finding"
      ? [{ ...age, field: "ear.ear_pain", label: "Ear pain", value: false, outside_assessment: true }] : [])];
    if (scope === "new worker edit") {
      pending.editVersion = 1;
      pending.workerEdits = { "danger_signs.convulsing_now": { value: false, label: "Convulsing now", previous: null, revision: 2 } };
    }
    voice.jobs = [pending];
    guide.pendingFieldPaths = [age.field];
    const original = structuredClone(pending);
    const app = workspace();
    app.navigate(views[0]);
    const review = app.checklist().props.ageReview;
    if (scope === "age-only") {
      expect(button(review, "Confirm age").props.disabled).toBe(false);
      click(button(review, "Confirm age"));
      expect(guide.confirm).toHaveBeenCalledExactlyOnceWith("danger");
      expect(app.checklist().props.mobileView).toEqual(views[0]);
    } else {
      expect(renderToStaticMarkup(review)).not.toContain("Confirm age");
      click(find(review, (node) => node.type === "button"));
      expect(app.checklist().props.mobileView).toEqual({ ...intro, intro: false });
      expect(guide.confirm).not.toHaveBeenCalled();
    }
    expect(pending).toEqual(original);
    expect(voice.accept).not.toHaveBeenCalled();
    expect(session.accept).not.toHaveBeenCalled();
  });

  it.each(["NOT_STARTED", "INCOMPLETE", "COMPLETE", "URGENT"] as const)("puts compact intro confirmation only in the dock, using accepted %s status", (status) => {
    voice.jobs = [job("review", "danger")];
    session.evaluation!.assessments.danger = { ...complete, status, decision: status === "URGENT" ? "URGENT" : "ASK" };
    guide.workingEncounter = { danger_signs: Object.fromEntries(buildChecklist({}).sections[0].items.map((item) => [item.id.split(".")[1], false])) };
    guide.pendingFieldPaths = ["danger_signs.convulsing_now"];
    const original = structuredClone({ jobs: voice.jobs, evaluation: session.evaluation });
    const app = workspace();
    expect(app.checklist().props.renderSectionReview!("danger")).toBeNull();
    const review = component(app.root(), MobileDock).props.confirmation;
    const html = renderToStaticMarkup(review);
    expect(find(review, (node) => node.type === "section").props["data-completeness"])
      .toBe(status === "URGENT" ? "urgent" : status === "COMPLETE" ? "complete" : "incomplete");
    for (const hidden of ["Awaiting confirmation", "observation(s) staged", "<h3", "<details", "<pre", "<code", "JSON", "Original danger finding"]) expect(html).not.toContain(hidden);
    if (status === "NOT_STARTED" || status === "INCOMPLETE") expect(html).toContain("Partial findings can be confirmed.");
    expect(component(app.root(), MobileHeader).props.urgent).toBe(status === "URGENT");
    expect(renderToStaticMarkup(app.root()).includes('aria-label="View urgent guidance"')).toBe(status === "URGENT");
    expect(renderToStaticMarkup(app.root())).not.toContain("workspace-urgent");
    expect(button(review, "Confirm findings").props.disabled).toBe(false);
    expect(guide.confirm).not.toHaveBeenCalled();
    click(button(review, "Confirm findings"));
    expect(guide.confirm).toHaveBeenCalledExactlyOnceWith("danger");
    expect(voice.accept).not.toHaveBeenCalled();
    expect(session.accept).not.toHaveBeenCalled();
    expect({ jobs: voice.jobs, evaluation: session.evaluation }).toEqual(original);
  });

  it.each(["patient_facts.age_months", "ear.ear_pain"])("requires full review before confirming an intro proposal containing %s", (field) => {
    const pending = job("review", "danger");
    pending.candidate!.changes.push({ field, label: "Other finding", value: field === "patient_facts.age_months" ? 12 : false,
      previous: null, conflict: false, outside_assessment: field.startsWith("ear.") });
    voice.jobs = [pending];
    const original = structuredClone(pending);
    const app = workspace();
    click(button(component(app.root(), MobileDock).props.confirmation, "Review other findings"));
    expect(app.checklist().props.mobileView).toEqual({ ...intro, intro: false });
    expect(component(app.root(), MobileDock).props.confirmation).toBeUndefined();
    expect(button(app.checklist().props.renderSectionReview!("danger"), "Confirm findings")).toBeDefined();
    expectNavigationOnly();
    expect(pending).toEqual(original);
  });

  it.each(["schema", "unready", "busy", "invalid", "preparing_review", "applying"])("retains the %s guard on the dock confirmation handler", (gate) => {
    const pending = job("review", "danger");
    voice.jobs = [pending];
    if (gate === "schema") guide.schema = null;
    if (gate === "unready") session.ready = false;
    if (gate === "busy") session.busy = true;
    if (gate === "invalid") pending.workerEdits = { "patient_facts.age_months": { raw: "12x", error: "Invalid number", previous: null, label: "Age", revision: 2 } };
    if (gate === "preparing_review" || gate === "applying") pending.status = gate;
    const app = workspace();
    const review = component(app.root(), MobileDock).props.confirmation;
    const confirm = find(review, (node) => node.type === "button" && node.props.className === "mobile-confirm-button");
    expect(confirm.props.disabled).toBe(true);
    click(confirm);
    expect(app.checklist().props.mobileView).toEqual(intro);
    expectNavigationOnly();
  });

  it("keeps stale and unresolved intro findings actionable without directly accepting them", () => {
    const pending = job("review", "danger");
    pending.reviewRevision = 1;
    pending.candidate!.changes[0].uncertain = true;
    voice.jobs = [pending];
    const original = structuredClone(pending);
    const app = workspace();
    const review = component(app.root(), MobileDock).props.confirmation;
    const html = renderToStaticMarkup(review);
    expect(html).toContain("Answers changed. Refresh review.");
    expect(html).toContain("1 answer(s) need review.");
    expect(button(review, "Convulsing now")).toBeDefined();
    click(button(review, "Refresh review"));
    expect(guide.confirm).toHaveBeenCalledExactlyOnceWith("danger");
    expect(voice.accept).not.toHaveBeenCalled();
    expect(session.accept).not.toHaveBeenCalled();
    expect(pending).toEqual(original);
  });

  it("passes an explicit question-free accepted snapshot only for intro speech, leaving ordinary three-argument capture unchanged", () => {
    session.evaluation!.assessments.danger = { ...complete, status: "INCOMPLETE", decision: "ASK",
      question: { field: "patient_facts.age_months", text: "Hidden age question?" }, missing_fields: ["patient_facts.age_months"] };
    const original = structuredClone(session.evaluation);
    const app = workspace();
    component(app.root(), MobileDock).props.onLanguageChange("yo");
    expectNavigationOnly();
    expect(renderToStaticMarkup(app.checklist().props.mobileFocus)).not.toContain("Hidden age question?");
    component(app.root(), MobileDock).props.onSpeak();
    expect(voice.startRecording).toHaveBeenCalledExactlyOnceWith("danger", "yo", { audio: true, understanding: true },
      { ...session.snapshot(), question: undefined });
    expect(vi.mocked(voice.startRecording).mock.calls[0][3]).toHaveProperty("question", undefined);
    for (const view of [{ ...intro, intro: false }, views[1]]) {
      app.navigate(view);
      component(app.root(), MobileDock).props.onSpeak();
      expect(voice.startRecording).toHaveBeenLastCalledWith(view.assessment, "yo", { audio: true, understanding: true });
      expect(vi.mocked(voice.startRecording).mock.lastCall).toHaveLength(3);
    }
    expect(session.evaluation).toEqual(original);
    expect(voice.accept).not.toHaveBeenCalled();
    expect(guide.confirm).not.toHaveBeenCalled();
  });

  it.each(["language", "unready", "no assessment"])("guards the Root onSpeak handler itself against missing %s", (gate) => {
    const app = workspace();
    if (gate !== "language") component(app.root(), MobileDock).props.onLanguageChange("en");
    if (gate === "unready") session.ready = false;
    for (const view of gate === "no assessment" ? [views[0]] : [intro, views[1]]) {
      app.navigate(view);
      component(app.root(), MobileDock).props.onSpeak();
    }
    expectNavigationOnly();
  });

  it("omits debug output across recordings, history, confirmation and results in both layouts without changing source data", () => {
    const pending = job("review");
    pending.originalCandidate!.understanding = { provider: "private-provider", model: "private-model", request_id: "private-request", prompt_version: "private-prompt", usage: { input_tokens: 42 } };
    session.interactions = [{ ...pending.trace, source: { submitted_text: "Retained original words" }, candidate: pending.originalCandidate }];
    session.evaluation!.analysis.pipeline_trace = [{ kind: "LEARNED", label: "Private processing step", detail: "private-pipeline" }];
    session.evaluation!.analysis.decision_trace = [{ rule_id: "private-rule", pathway: "Ear", classification: "Accepted explanation", findings: [["Pain", "Absent"]], rule_description: "Accepted rationale" }];
    voice.jobs = [pending];
    const app = workspace();
    for (const status of ["review", "accepted"] as const) {
      pending.status = status;
      const original = structuredClone({ jobs: voice.jobs, interactions: session.interactions, evaluation: session.evaluation });
      for (const view of [intro, ...views]) {
        app.navigate(view);
        const tree = app.root();
        const checklist = component(tree, AssessmentChecklist);
        for (const id of assessmentIds) expect(component(checklist.props.renderCapture!(id), AssessmentCapture).props.showDebug).toBe(false);
        expect(component(app.tools(), InteractionHistory).props.showDebug).toBe(false);
        if (status === "accepted") expect(component(tree, ResultPanel).props.showDebug).toBe(false);
        const html = renderToStaticMarkup(tree);
        for (const hidden of ["<pre", "<code", "JSON", "private-", "Private processing step", "Processing trace", "Details: original report and review", "Review metadata", "Control schema"]) expect(html).not.toContain(hidden);
        expect(html).toContain("Retained original words");
        if (status === "accepted") {
          expect(html).toContain("Accepted final plan");
          expect(html).toContain("Accepted rationale");
        }
        expect({ jobs: voice.jobs, interactions: session.interactions, evaluation: session.evaluation }).toEqual(original);
      }
    }
    vi.mocked(useMobileLayout).mockReturnValue(false);
    const desktop = app.root();
    expect(component(desktop, ResultPanel).props.showDebug).toBe(false);
    const html = renderToStaticMarkup(desktop);
    for (const debug of ["<pre", "<code", "private-model", "private-rule", "private-pipeline", "Processing trace"]) expect(html).not.toContain(debug);
    expectNavigationOnly();
  });

  it("keeps one guide, one report and five capture positions/types/keys through navigation, revisions, and layout switches", () => {
    const app = workspace();
    const identity = () => {
      const root = app.root();
      const checklists = locations(root).filter(({ node }) => node.type === AssessmentChecklist);
      expect(checklists).toHaveLength(1);
      const reports = locations(root).filter(({ node }) => node.type === ReportPanel);
      expect(reports).toHaveLength(1);
      const main = find(root, (node) => node.type === "main");
      expect((main.props.children as ReactNode[]).filter(isValidElement).map((node) => node.type)).toEqual([AssessmentChecklist, ReportPanel, "section"]);
      const tree = app.captures();
      const captures = locations(tree).filter(({ node }) => node.type === AssessmentCapture);
      expect(captures.map(({ node }) => node.props.assessment)).toEqual(assessmentIds);
      expect(captures).toHaveLength(5);
      const sections = locations(tree).filter(({ node }) => node.type === "details" && node.props["data-assessment"]);
      expect(sections.map(({ node }) => node.key)).toEqual(assessmentIds);
      const view = app.checklist().props.mobileView;
      if (view) expect(sections.filter(({ node }) => node.props.open).map(({ node }) => node.key))
        .toEqual(view.screen === "assessment" ? [view.assessment] : []);
      return { checklist: checklists[0].path, report: reports[0].path, captures: captures.map(({ path }) => path) };
    };
    const initial = identity();
    expect(app.checklist().key).toBe("0");
    for (const [index, view] of views.entries()) {
      app.navigate(view, index === 1 ? "home" : index === 2 ? "tabs" : "dock");
      expect(app.checklist().props.mobileView).toEqual(view);
      expect(find(app.root(), (node) => node.type === "main").props).toMatchObject({
        "data-mobile-screen": view.screen, "data-mobile-assessment": view.assessment ?? undefined, "data-mobile-tab": view.tab,
      });
      expect(identity()).toEqual(initial);
    }
    session.revision = 7;
    session.encounter = { ...session.encounter, fever: { fever_duration_days: 2 } };
    for (const mobile of [false, true, false, true]) {
      vi.mocked(useMobileLayout).mockReturnValue(mobile);
      expect(identity()).toEqual(initial);
      expect(app.checklist().props.mobileView).toEqual(mobile ? views[views.length - 1] : undefined);
      // Mobile chrome stays mounted but CSS-hidden on desktop, preserving focus ownership.
      expect(locations(app.root()).filter(({ node }) => node.type === MobileDock)).toHaveLength(1);
    }
    app.navigate(views[0], "header");
    expect(identity()).toEqual(initial);
    expectNavigationOnly();
    expect(useVoiceCapture).toHaveBeenLastCalledWith(session);
  });

  it.each(["recording", "transcribing", "review"] as const)("keeps a %s job with its original owner and context while navigating and changing language", (status) => {
    const pending = job(status);
    voice.jobs = [pending];
    if (status === "recording") { voice.recordingId = pending.id; voice.audioState = "recording"; }
    const original = structuredClone(pending);
    const app = workspace();
    const captureHooks = Object.fromEntries(assessmentIds.map((id) => [id, createHooks()])) as Record<AssessmentId, Hooks>;
    const jobHooks = createHooks();
    let ownerPath: unknown[] | undefined;
    for (const view of views) {
      app.navigate(view);
      if (view.screen === "results") {
        component(app.root(), MobileDock).props.onLanguageChange("ha");
        session.revision = 9;
        session.encounter = { ear: { ear_pain: false } };
      }
      if (status === "recording") {
        const dock = component(app.root(), MobileDock).props;
        const select = find(MobileDock(dock), (node) => node.props.id === "mobile-speech-language");
        expect(select.props).toMatchObject({ disabled: true, value: "yo" });
        change(select, { value: "ig" });
        expect(component(app.root(), MobileDock).props.language).toBe(dock.language);
      }
      const captures = locations(app.captures()).filter(({ node }) => node.type === AssessmentCapture);
      for (const { node } of captures) {
        const props = component(node, AssessmentCapture).props;
        expect(props.voice).toBe(voice);
        const section = render(captureHooks[props.assessment], () => AssessmentCapture(props));
        const cards = locations(section).filter(({ node: card }) => card.props.job === pending);
        expect(cards).toHaveLength(props.assessment === "ear" ? 1 : 0);
        if (props.assessment === "ear") {
          expect(cards[0].node.key).toBe(pending.id);
          ownerPath ??= cards[0].path;
          expect(cards[0].path).toEqual(ownerPath);
          if (status === "review") {
            const card = cards[0].node;
            const cardTree = render(jobHooks, () => (card.type as (props: Record<string, unknown>) => ReactNode)(card.props));
            expect(button(cardTree, "Review on assessment").props.disabled).toBe(false);
            expect(renderToStaticMarkup(cardTree)).not.toContain("Apply reviewed findings");
          }
        }
      }
      expect(pending).toEqual(original);
      expect(app.checklist().props.pendingAssessments).toEqual(["ear"]);
      expect(component(app.root(), MobileDock).props.pendingCount).toBe(1);
      expectNavigationOnly();
    }
    expect(component(app.root(), MobileDock).props.language).toBe("ha");
    expect(component(app.root(), MobileDock).props).not.toHaveProperty("consent");
    expect(pending.language).toBe("yo");
    expect(voice.jobs[0]).toBe(pending);
    // Finish the mocked active recording before explicitly starting the next clip.
    voice.recordingId = null;
    voice.audioState = "idle";
    app.navigate(views[3]);
    component(app.root(), MobileDock).props.onSpeak();
    expect(voice.startRecording).toHaveBeenCalledExactlyOnceWith("fever", "ha", { audio: true, understanding: true });
    expect(pending).toEqual(original);
  });

  it("only confirmed encounter clearing resets drafts and view while retaining mobile preauthorization", () => {
    voice.jobs = [job("review")];
    const app = workspace();
    const capture = app.checklist().props.renderCapture!("ear") as ReactElement<ComponentProps<typeof AssessmentCapture>>;
    capture.props.onDirty((previous) => ({ ...previous, ear: true }));
    app.navigate(views[0]);
    component(app.root(), MobileDock).props.onLanguageChange("en");
    const key = app.checklist().key;
    vi.mocked(window.confirm).mockReturnValue(false);
    expect(renderToStaticMarkup(app.tools())).not.toContain(">Clear encounter</button>");
    click(button(app.tools(), "Start new assessment"));
    expect(app.checklist().key).toBe(key);
    expect(app.checklist().props.mobileView).toEqual(views[0]);
    expect(app.checklist().props.captureStatuses?.ear).toBe("Unprocessed edits");
    expectNavigationOnly();
    vi.mocked(window.confirm).mockReturnValue(true);
    click(button(app.tools(), "Start new assessment"));
    expect(voice.clear).toHaveBeenCalledOnce();
    expect(guide.reset).toHaveBeenCalledOnce();
    expect(session.reset).toHaveBeenCalledOnce();
    expect(vi.mocked(voice.clear).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(guide.reset).mock.invocationCallOrder[0]);
    expect(vi.mocked(guide.reset).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(session.reset).mock.invocationCallOrder[0]);
    expect(vi.mocked(voice.clear).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(session.reset).mock.invocationCallOrder[0]);
    expect(app.checklist().key).toBe(String(Number(key) + 1));
    expect(app.checklist().props.mobileView).toEqual(intro);
    expect(find(app.root(), (node) => node.type === "main").props["data-mobile-intro"]).toBe(true);
    expect(find(app.root(), (node) => node.type === "main").props["data-show-age"]).toBeUndefined();
    expect(component(app.root(), MobileDock).props).not.toHaveProperty("consent");
    expect(component(app.checklist().props.renderCapture!("ear"), AssessmentCapture).props.consent).toEqual({ audio: true, understanding: true });
    component(app.root(), MobileDock).props.onSpeak();
    expect(voice.startRecording).toHaveBeenCalledExactlyOnceWith("danger", "en", { audio: true, understanding: true },
      { ...session.snapshot(), question: undefined });
    // Simulate the mocked queue's reset output; the root must have cleared its own dirty gate.
    voice.jobs = [];
    expect(app.checklist().props.pendingAssessments).toEqual([]);
    expect(renderToStaticMarkup(app.root())).toContain("Accepted final plan");
    expect(voice.accept).not.toHaveBeenCalled();
    expect(session.accept).not.toHaveBeenCalled();
    expect(voice.cancelRecording).not.toHaveBeenCalled();
  });

  it.each(["analysis", "assessment", "decision"] as const)("links shared %s urgency to results without duplicating management or accepting findings", (source) => {
    session.evaluation!.analysis.urgent_actions = ["Accepted urgent transfer action"];
    if (source === "analysis") session.evaluation!.analysis.is_urgent = true;
    else session.evaluation!.assessments.danger = { ...complete, status: source === "assessment" ? "URGENT" : "INCOMPLETE", decision: "URGENT" };
    voice.jobs = [job("transcribing")];
    const original = structuredClone({ jobs: voice.jobs, evaluation: session.evaluation });
    const app = workspace();
    for (const view of [intro, ...views]) {
      app.navigate(view);
      const tree = app.root();
      const header = component(tree, MobileHeader);
      expect(header.props.urgent).toBe(true);
      const html = renderToStaticMarkup(tree);
      expect(html).not.toMatch(/workspace-urgent|aria-label="Accepted urgent guidance"/);
      expect(html.slice(0, html.indexOf("<main"))).not.toContain("Accepted urgent transfer action");
      const right = html.slice(html.indexOf('<section class="output-panel"'));
      expect(right.includes("Accepted urgent transfer action")).toBe(source === "analysis");
      expect(html.split("Accepted urgent transfer action")).toHaveLength(source === "analysis" ? 2 : 1);
      expect(html).not.toContain("Accepted final plan");
      expect(html.match(/aria-label="View urgent guidance"/g) ?? []).toHaveLength(view.screen === "results" ? 0 : 1);
      expect(app.checklist().props.mobileView).toEqual(view);
      if (view.screen !== "results") {
        click(find(MobileHeader(header.props), (node) => node.props["aria-label"] === "View urgent guidance"));
        expect(app.checklist().props.mobileView).toEqual({ ...view, screen: "results" });
        const results = renderToStaticMarkup(app.root());
        expect(results).not.toContain('aria-label="View urgent guidance"');
        expect(results.split("Accepted urgent transfer action")).toHaveLength(source === "analysis" ? 2 : 1);
      }
      expectNavigationOnly();
      expect({ jobs: voice.jobs, evaluation: session.evaluation }).toEqual(original);
    }
    expectNavigationOnly();
  });

  it.each([
    ["empty", "Ready when you are"],
    ["incomplete", "Assessment in progress"],
    ["dirty", "Process or discard unprocessed edits before final plan"],
    ["interrupted", "Acknowledge interrupted captures before final plan"],
    ["blocked", "Review evidence issues"],
    ...(["recording", "queued", "transcribing", "extracting", "captured", "preparing_review", "review", "applying", "failed"] as const)
      .map((status) => [status, "Review captured findings before final plan"]),
  ])("withholds mobile final synthesis for %s", (gate, message) => {
    if (gate === "empty") session.encounter = { ear: { ear_pain: null } };
    else if (gate === "incomplete") session.evaluation!.analysis.is_complete = false;
    else if (gate === "interrupted") session.interruptedCount = 1;
    else if (gate === "blocked") session.evaluation!.assessments.ear = { ...complete, decision: "BLOCK", blockers: ["Resolve evidence"] };
    else if (gate !== "dirty") voice.jobs = [job(gate as CaptureJob["status"])];
    const app = workspace();
    if (gate === "dirty") {
      const capture = app.checklist().props.renderCapture!("ear") as ReactElement<ComponentProps<typeof AssessmentCapture>>;
      capture.props.onDirty({ ear: true });
    }
    app.navigate({ screen: "results", assessment: "ear", tab: "findings" });
    const html = renderToStaticMarkup(app.root());
    expect(html).toContain('data-mobile-screen="results"');
    expect(html).toContain(message);
    for (const final of ["Clinical synthesis ready", "Accepted final plan", "Accepted routine classification", "Accepted routine management"]) {
      expect(html).not.toContain(final);
    }
    expectNavigationOnly();
  });

  it("shows mobile final synthesis for complete accepted evidence with only terminal jobs", () => {
    voice.jobs = [job("accepted"), { ...job("discarded"), id: "discarded-clip" }];
    const app = workspace();
    app.navigate({ screen: "results", assessment: null, tab: "guidance" });
    const html = renderToStaticMarkup(app.root());
    expect(html).toContain("Clinical synthesis ready");
    expect(html).toContain("Accepted final plan");
    expect(app.checklist().props.pendingAssessments).toEqual([]);
    expectNavigationOnly();
  });
});
