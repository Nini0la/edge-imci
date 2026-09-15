import { isValidElement, type ComponentProps, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { AssessmentCapture } from "./components/AssessmentCapture";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
import { ClinicalFieldControl } from "./components/ClinicalFieldControl";
import { MobileAssessmentHome, MobileAssessmentTabs, MobileDock, MobileHeader, type MobileView } from "./components/MobileWorkspace";
import { assessmentIds } from "./lib/assessment";
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
function job(status: CaptureJob["status"]): CaptureJob {
  return { id: "ear-clip", assessment: "ear", language: "yo", status, inputText: "Original ear finding",
    originalEncounter: { ear: { ear_pain: null } }, originalRevision: 1, reviewRevision: 2, reviewVersion: 3,
    question: { field: "ear.ear_pain", text: "Original ear question?" }, changedFields: [],
    candidate: { assessment: "ear", input_text: "Original ear finding", extraction_mode: "test", warnings: [],
      changes: [{ field: "ear.ear_pain", label: "Ear pain", previous: true, value: false, conflict: true, outside_assessment: false }] },
    trace: { id: "ear-clip", timestamp: "2026-09-15T12:00:00Z", assessment: "ear", status: "candidate", source: {} } };
}
let voice: ReturnType<typeof useVoiceCapture>;
let session: ReturnType<typeof useAssessmentSession>;
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
    evaluate: vi.fn().mockResolvedValue(true), accept: vi.fn().mockResolvedValue(true), interactions: [], recordInteraction: vi.fn(), rejectPending: vi.fn() };
  vi.mocked(useAssessmentSession).mockReturnValue(session);
  vi.mocked(useVoiceCapture).mockReturnValue(voice);
  vi.mocked(useGuideEditor).mockReturnValue({ schema: { schema_id: "test", schema_sha256: "test", fields: {} }, schemaError: "",
    workingEncounter: session.encounter, pendingFieldPaths: [], field: vi.fn().mockReturnValue(null), selectedJob: () => undefined, selectJob: vi.fn(),
    confirm: vi.fn().mockResolvedValue(undefined), reset: vi.fn(), retrySchema: vi.fn() });
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
  return { root, checklist, captures, navigate };
}
const views: MobileView[] = [
  { screen: "list", assessment: null, tab: "guidance" },
  { screen: "assessment", assessment: "ear", tab: "guidance" },
  { screen: "assessment", assessment: "ear", tab: "findings" },
  { screen: "assessment", assessment: "fever", tab: "guidance" },
  { screen: "results", assessment: "fever", tab: "guidance" },
  { screen: "settings", assessment: "fever", tab: "guidance" },
];
function expectNavigationOnly() {
  for (const operation of [voice.clear, voice.cancelRecording, voice.stop, voice.accept, voice.prepareReview,
    voice.startRecording, voice.addText, voice.retry, voice.discard, voice.retract, session.reset, session.accept, session.rejectPending]) {
    expect(operation).not.toHaveBeenCalled();
  }
}

describe("integrated mobile workspace", () => {
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

  it("reuses the exact danger age field on Home and Assessment without confirming unseen danger findings", () => {
    const app = workspace();
    app.root();
    const guide = vi.mocked(useGuideEditor).mock.results[0].value as ReturnType<typeof useGuideEditor>;
    guide.pendingFieldPaths = ["patient_facts.age_months"];
    const age = { descriptor: { path: "patient_facts.age_months", label: "Age", kind: "integer" as const, nullable: true, unit: "months", assessments: ["danger" as const] },
      value: 12, raw: "12.", acceptedValue: 24, source: "worker" as const, pending: true, requiresChoice: false, disabled: false, error: undefined,
      jobId: "danger-draft", onChange: vi.fn(), onKeep: vi.fn() };
    vi.mocked(guide.field).mockImplementation((assessment, path) => assessment === "danger" && path === age.descriptor.path ? age : null);
    app.navigate({ screen: "assessment", assessment: "ear", tab: "guidance" });
    const tree = app.checklist();
    const home = component(tree.props.mobileHome, MobileAssessmentHome);
    const tabs = component(tree.props.mobileFocus, MobileAssessmentTabs);
    for (const node of [home.props.ageControl, tabs.props.ageControl]) {
      const control = component(node, ClinicalFieldControl);
      expect(control.props.raw).toBe("12.");
      expect(control.props.onChange).toBe(age.onChange);
      control.props.onChange("13");
      expect(renderToStaticMarkup(node)).not.toContain("Confirm age");
    }
    expect(age.onChange).toHaveBeenCalledTimes(2);
    expect(renderToStaticMarkup(home.props.ageControl)).toContain("Review age with");
    click(find(home.props.ageControl, (node) => node.type === "button" && node.props.className === "guide-clear"));
    expect(app.checklist().props.mobileView).toEqual({ screen: "assessment", assessment: "danger", tab: "guidance" });
    expect(guide.confirm).not.toHaveBeenCalled();
    expect(voice.addText).not.toHaveBeenCalled();
    expect(voice.accept).not.toHaveBeenCalled();
  });

  it("shows the focused age control only when accepted age is unknown or age is pending", () => {
    const app = workspace();
    app.navigate(views[1]);
    expect(component(app.checklist().props.mobileFocus, MobileAssessmentTabs).props.ageControl).toBeUndefined();
    session.encounter = { patient_facts: { age_months: null } };
    expect(component(app.checklist().props.mobileFocus, MobileAssessmentTabs).props.ageControl).toBeDefined();
  });

  it("keeps one checklist and five capture positions/types/keys through navigation, revisions, and layout switches", () => {
    const app = workspace();
    const identity = () => {
      const checklists = locations(app.root()).filter(({ node }) => node.type === AssessmentChecklist);
      expect(checklists).toHaveLength(1);
      const tree = app.captures();
      const captures = locations(tree).filter(({ node }) => node.type === AssessmentCapture);
      expect(captures.map(({ node }) => node.props.assessment)).toEqual(assessmentIds);
      expect(captures).toHaveLength(5);
      const sections = locations(tree).filter(({ node }) => node.type === "details" && node.props["data-assessment"]);
      expect(sections.map(({ node }) => node.key)).toEqual(assessmentIds);
      const view = app.checklist().props.mobileView;
      if (view) expect(sections.filter(({ node }) => node.props.open).map(({ node }) => node.key))
        .toEqual(view.screen === "assessment" ? [view.assessment] : []);
      return { checklist: checklists[0].path, captures: captures.map(({ path }) => path) };
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
      expect(app.checklist().props.mobileView).toEqual(mobile ? views[5] : undefined);
      // Mobile chrome stays mounted but CSS-hidden on desktop, preserving focus ownership.
      expect(locations(app.root()).filter(({ node }) => node.type === MobileDock)).toHaveLength(1);
    }
    app.navigate(views[0], "header");
    expect(identity()).toEqual(initial);
    expectNavigationOnly();
    expect(useVoiceCapture).toHaveBeenLastCalledWith(session);
  });

  it.each(["recording", "transcribing", "review"] as const)("keeps a %s job with its original owner and context while navigating and changing setup", (status) => {
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
      if (view.screen === "settings") {
        const settings = app.checklist().props.guideStatus;
        change(find(settings, (node) => node.props.id === "capture-language"), { value: "ha" });
        locations(settings).filter(({ node }) => node.props.type === "checkbox")
          .forEach(({ node }) => change(node, { checked: true }));
        session.revision = 9;
        session.encounter = { ear: { ear_pain: false } };
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
    expect(component(app.root(), MobileDock).props).toMatchObject({ language: "ha", consent: { audio: true, understanding: true } });
    expect(pending.language).toBe("yo");
    expect(voice.jobs[0]).toBe(pending);
  });

  it("only confirmed encounter clearing resets the queue, session, dirty gate, capture key, and mobile setup/view", () => {
    voice.jobs = [job("review")];
    const app = workspace();
    const capture = app.checklist().props.renderCapture!("ear") as ReactElement<ComponentProps<typeof AssessmentCapture>>;
    capture.props.onDirty((previous) => ({ ...previous, ear: true }));
    app.navigate(views[5]);
    const settings = app.checklist().props.guideStatus;
    change(find(settings, (node) => node.props.id === "capture-language"), { value: "en" });
    locations(settings).filter(({ node }) => node.props.type === "checkbox").forEach(({ node }) => change(node, { checked: true }));
    const key = app.checklist().key;
    vi.mocked(window.confirm).mockReturnValue(false);
    click(button(app.checklist().props.tools, "Clear encounter"));
    expect(app.checklist().key).toBe(key);
    expect(app.checklist().props.mobileView).toEqual(views[5]);
    expect(app.checklist().props.captureStatuses?.ear).toBe("Unprocessed edits");
    expectNavigationOnly();
    vi.mocked(window.confirm).mockReturnValue(true);
    click(button(app.checklist().props.tools, "Clear encounter"));
    expect(voice.clear).toHaveBeenCalledOnce();
    expect(session.reset).toHaveBeenCalledOnce();
    expect(vi.mocked(voice.clear).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(session.reset).mock.invocationCallOrder[0]);
    expect(app.checklist().key).toBe(String(Number(key) + 1));
    expect(app.checklist().props.mobileView).toEqual(views[0]);
    expect(component(app.root(), MobileDock).props.consent).toEqual({ audio: false, understanding: false });
    // Simulate the mocked queue's reset output; the root must have cleared its own dirty gate.
    voice.jobs = [];
    expect(app.checklist().props.pendingAssessments).toEqual([]);
    expect(renderToStaticMarkup(app.root())).toContain("Accepted final plan");
    expect(voice.accept).not.toHaveBeenCalled();
    expect(session.accept).not.toHaveBeenCalled();
    expect(voice.cancelRecording).not.toHaveBeenCalled();
  });

  it.each(["analysis", "assessment"] as const)("keeps shared %s urgency outside the switched main on every screen", (source) => {
    session.evaluation!.analysis.urgent_actions = ["Accepted urgent transfer action"];
    if (source === "analysis") session.evaluation!.analysis.is_urgent = true;
    else session.evaluation!.assessments.danger = { ...complete, status: "URGENT", decision: "URGENT" };
    voice.jobs = [job("transcribing")];
    const app = workspace();
    for (const view of views) {
      app.navigate(view);
      const tree = app.root();
      const alerts = locations(tree).filter(({ node }) => node.props["aria-label"] === "Accepted urgent guidance");
      expect(alerts).toHaveLength(1);
      expect(alerts[0].path).not.toContain("main");
      expect(alerts[0].node.props.role).toBe("alert");
      const html = renderToStaticMarkup(tree);
      expect(html.slice(0, html.indexOf("<main"))).toContain("Accepted urgent transfer action");
      expect(html).not.toContain("Accepted final plan");
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
