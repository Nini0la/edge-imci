import { isValidElement, type ComponentProps, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { buildChecklist } from "../lib/checklist";
import type { CaptureJob } from "../lib/useVoiceCapture";
import { CaptureJobCard } from "./AssessmentCapture";
import { ReportPanel } from "./ReportPanel";

type Element = ReactElement<Record<string, unknown>>;
function elements(tree: ReactNode): Element[] {
  if (Array.isArray(tree)) return tree.flatMap(elements);
  return isValidElement<Record<string, unknown>>(tree) ? [tree, ...elements(tree.props.children as ReactNode)] : [];
}
function button(tree: ReactNode, label: string) {
  const node = elements(tree).find((node) => node.type === "button" && renderToStaticMarkup(node).includes(label));
  expect(node).toBeDefined();
  return node!;
}
const click = (node: Element) => (node.props.onClick as () => void)();
function props(overrides: Partial<ComponentProps<typeof ReportPanel>> = {}): ComponentProps<typeof ReportPanel> {
  return { text: "", ready: true, onChange: vi.fn(), onInterpret: vi.fn(), onClear: vi.fn(), review: null,
    sections: [], onReviewSection: vi.fn(), onReviewJob: vi.fn(), reviewDisabled: false,
    voice: { jobs: [], recordingId: null, audioState: "idle", error: "", startRecording: vi.fn(), stop: vi.fn(), cancelRecording: vi.fn(),
      addText: vi.fn(), prepareReview: vi.fn(), accept: vi.fn(), retry: vi.fn(), discard: vi.fn(), retract: vi.fn(), clear: vi.fn(), stageField: vi.fn() },
    ...overrides };
}
function job(status: CaptureJob["status"], overrides: Partial<CaptureJob> = {}): CaptureJob {
  return { id: `report-${status}`, assessment: "full-note", status, inputText: "Original synthetic report <unchanged>",
    originalEncounter: {}, originalRevision: 2, reviewVersion: 0, changedFields: [],
    originalCandidate: { assessment: "full-note", input_text: "Original synthetic report <unchanged>", changes: [], warnings: [],
      extraction_mode: "private-extraction", understanding: { provider: "private-provider", model: "private-model",
        request_id: "private-request", prompt_version: "private-prompt", usage: { input_tokens: 42 } } },
    trace: { id: `report-${status}`, assessment: "full-note", timestamp: "today", status: "candidate", source: {} }, ...overrides };
}

describe("ReportPanel", () => {
  it.each([
    { text: "", ready: true, disabled: true }, { text: " \n\t", ready: true, disabled: true },
    { text: "Synthetic findings", ready: false, disabled: true }, { text: "Synthetic findings", ready: true, disabled: false },
  ])("gates interpretation for $text with ready=$ready without preventing draft entry", ({ text, ready, disabled }) => {
    const input = props({ text, ready });
    const tree = ReportPanel(input);
    expect(button(tree, "Interpret text").props.disabled).toBe(disabled);
    const textarea = elements(tree).find((node) => node.type === "textarea")!;
    expect(textarea.props).toMatchObject({ id: "assessment-report", value: text, maxLength: 8000, "aria-describedby": "report-help" });
    expect(textarea.props.disabled).not.toBe(true);
    const html = renderToStaticMarkup(tree);
    expect(html).toContain('for="assessment-report"');
    expect(html.includes("Waiting for the assessment to be ready.")).toBe(!ready);
    expect(html.includes("Clear text")).toBe(Boolean(text));
    expect(input.onInterpret).not.toHaveBeenCalled();
  });

  it("delegates typed values, interpretation and clear without changing controlled props or accepting findings", () => {
    const input = props({ text: "Initial report" });
    const tree = ReportPanel(input);
    const textarea = elements(tree).find((node) => node.type === "textarea")!;
    (textarea.props.onChange as (event: { target: { value: string } }) => void)({ target: { value: "Edited report\nNo ear pain" } });
    expect(input.onChange).toHaveBeenCalledExactlyOnceWith("Edited report\nNo ear pain");
    expect(input.onInterpret).not.toHaveBeenCalled();
    click(button(tree, "Interpret text"));
    expect(input.onInterpret).toHaveBeenCalledExactlyOnceWith();
    click(button(tree, "Clear text"));
    expect(input.onClear).toHaveBeenCalledExactlyOnceWith();
    expect(input.text).toBe("Initial report");
    expect(textarea.props.value).toBe("Initial report");
    for (const operation of [input.voice.addText, input.voice.accept, input.voice.clear, input.voice.discard]) expect(operation).not.toHaveBeenCalled();
  });

  it("renders only retained full-note jobs, preserving original words without JSON or editable source copies", () => {
    const input = props();
    input.voice.jobs = [job("review"), job("accepted"), job("discarded"), job("review", { id: "ear-clip", assessment: "ear" })];
    const before = structuredClone(input.voice.jobs);
    const tree = ReportPanel(input);
    const cards = elements(tree).filter((node) => node.type === CaptureJobCard);
    expect(cards.map((node) => node.key)).toEqual(["report-review", "report-accepted"]);
    cards.forEach((node, index) => {
      expect(node.props.job).toBe(input.voice.jobs[index]);
      expect(node.props).toMatchObject({ showDebug: false, voice: input.voice, onReviewJob: input.onReviewJob, reviewDisabled: false });
    });
    const html = renderToStaticMarkup(tree);
    expect(html.match(/Original text report/g)).toHaveLength(2);
    expect(html.match(/Original synthetic report &lt;unchanged&gt;/g)).toHaveLength(2);
    expect(html.match(/<textarea/g)).toHaveLength(1);
    for (const hidden of ["private-", "JSON", "<pre", "<code", "ear-clip", "Discarded", "Apply reviewed findings"]) expect(html).not.toContain(hidden);
    expect(input.voice.jobs).toEqual(before);
  });

  it("keeps the parent's review node and delegates labelled guide links without confirmation", () => {
    const confirm = vi.fn();
    const review = <section><button onClick={confirm}>Confirm findings</button></section>;
    const sections = buildChecklist({}).sections.filter((section) => section.id === "danger" || section.id === "ear");
    const before = structuredClone(sections);
    const input = props({ review, sections });
    const tree = ReportPanel(input);
    expect(elements(tree)).toContain(review);
    for (const section of sections) click(button(tree, section.label));
    expect(input.onReviewSection).toHaveBeenNthCalledWith(1, "danger");
    expect(input.onReviewSection).toHaveBeenNthCalledWith(2, "ear");
    expect(confirm).not.toHaveBeenCalled();
    expect(input.voice.accept).not.toHaveBeenCalled();
    expect(sections).toEqual(before);
    click(button(tree, "Confirm findings"));
    expect(confirm).toHaveBeenCalledOnce();
  });

  it.each([false, true])("delegates report review and preserves its disabled gate=%s", (reviewDisabled) => {
    const input = props({ reviewDisabled });
    input.voice.jobs = [job("review")];
    const card = elements(ReportPanel(input)).find((node) => node.type === CaptureJobCard) as ReactElement<ComponentProps<typeof CaptureJobCard>>;
    const review = button(CaptureJobCard(card.props), "Review on assessment");
    expect(review.props.disabled).toBe(reviewDisabled);
    if (!reviewDisabled) {
      click(review);
      expect(input.onReviewJob).toHaveBeenCalledExactlyOnceWith("report-review");
    }
    expect(input.voice.accept).not.toHaveBeenCalled();
    expect(input.voice.prepareReview).not.toHaveBeenCalled();
  });

  it("delegates retry and discard for a failed report without automatically confirming or mutating it", () => {
    const input = props();
    input.voice.jobs = [job("failed", { error: "Understanding unavailable" })];
    const before = structuredClone(input.voice.jobs);
    const card = elements(ReportPanel(input)).find((node) => node.type === CaptureJobCard) as ReactElement<ComponentProps<typeof CaptureJobCard>>;
    const tree = CaptureJobCard(card.props);
    expect(renderToStaticMarkup(tree)).toContain("Understanding unavailable");
    expect(input.voice.retry).not.toHaveBeenCalled();
    expect(input.voice.discard).not.toHaveBeenCalled();
    click(button(tree, "Retry"));
    expect(input.voice.retry).toHaveBeenCalledExactlyOnceWith("report-failed");
    click(button(tree, "Discard"));
    expect(input.voice.discard).toHaveBeenCalledExactlyOnceWith("report-failed");
    for (const operation of [input.voice.accept, input.voice.prepareReview, input.onInterpret, input.onClear, input.onReviewJob]) expect(operation).not.toHaveBeenCalled();
    expect(input.voice.jobs).toEqual(before);
  });
});
