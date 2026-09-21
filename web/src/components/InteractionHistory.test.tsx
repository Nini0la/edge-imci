import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { InteractionHistory } from "./InteractionHistory";
import type { InteractionTrace } from "../types";

describe("local interaction history", () => {
  it("preserves historical source wording without exposing provider metadata", () => {
    const interactions: InteractionTrace[] = [{ id: "legacy", timestamp: "today", assessment: "ear", status: "transcribed",
      source: { raw_asr_transcript: "The worker mentioned Intron.", asr_provider: "intron", language: "yo" },
    }];
    const before = JSON.stringify(interactions);
    const html = renderToStaticMarkup(<InteractionHistory interactions={interactions} showDebug={false} />);
    expect(html).toContain("The worker mentioned Intron.");
    expect(html).toContain("Original report");
    expect(html).not.toContain("intron");
    expect(html).not.toContain(" / yo");
    expect(JSON.stringify(interactions)).toBe(before);
  });

  it("retains failed/rejected and native/retraction outcomes as collapsed, escaped debug data", () => {
    const source = { raw_asr_transcript: "<script>ASR</script>", submitted_text: "Worker correction", recording_id: "recording-1", language: "yo" as const };
    const interactions: InteractionTrace[] = [
      { id: "1", timestamp: "today", assessment: "ear", source, status: "failed", error: "Provider timeout" },
      { id: "2", timestamp: "today", assessment: "ear", source, status: "rejected", candidate: {
        assessment: "ear", input_text: "normalized", extraction_mode: "frontier", changes: [], warnings: [], english_rendering: "English review only",
      } },
      { id: "3", timestamp: "today", assessment: "full-note", source: { submitted_text: "New full note" }, status: "accepted" },
      { id: "4", timestamp: "today", assessment: "ear", source: { submitted_text: "Worker-requested retraction" }, status: "accepted" },
    ];
    const html = renderToStaticMarkup(<InteractionHistory interactions={interactions} />);
    expect(html).toContain("Interaction trace (4)");
    expect(html).toContain("ear / failed");
    expect(html).toContain("ear / rejected");
    expect(html).toContain("full-note / accepted");
    expect(html).toContain("Worker-requested retraction");
    expect(html).toContain("Provider timeout");
    expect(html).toContain("&lt;script&gt;ASR&lt;/script&gt;");
    expect(html).not.toContain("<script>");
    expect(html).toContain("Worker correction");
    expect(html).toContain("English review only");
    expect(html).toContain("sensitive health information (PHI)");
    expect(html).not.toMatch(/<details[^>]*open/);
    expect(html).not.toContain("<audio");
    expect(html).toContain("<pre>");
    expect(html).toBe(renderToStaticMarkup(<InteractionHistory interactions={interactions} showDebug />));
  });

  it("renders nondebug events, errors, and source words without serializing history or showing technical identifiers", () => {
    const interactions: InteractionTrace[] = [{ id: "private-trace", timestamp: "today", assessment: "ear", status: "failed", error: "Intron ASR recording could not be processed",
      source: { raw_asr_transcript: "Original spoken words", submitted_text: "Worker words", recording_id: "private-recording", asr_provider: "intron", asr_model: "private-asr",
        language: "yo", question: { field: "ear.ear_pain", text: "Does the child have ear pain?" } },
      candidate: { assessment: "ear", input_text: "normalized", extraction_mode: "frontier", changes: [],
        warnings: ["Check the reported duration", 'JSON schema mismatch: {"ear.ear_pain": null} from azure_openai'], english_rendering: "English words",
        understanding: { provider: "azure_openai", model: "private-model", request_id: "private-request", prompt_version: "v1", usage: { input_tokens: 42 } },
        uncertainties: [{ field: "ear.ear_pain", reason: "The answer was unclear", source_text: "Maybe pain" }],
      },
      before_encounter: { ear: { ear_pain: true } }, resolutions: { "ear.ear_pain": "keep" }, worker_edits: { "ear.ear_pain": { value: false, label: "Ear pain", previous: true, revision: 2 } },
    }];
    const before = JSON.stringify(interactions);
    const html = renderToStaticMarkup(<InteractionHistory interactions={interactions} showDebug={false} />);
    for (const text of ["<pre", "<code", "JSON", "schema", "private-", "azure_openai", "intron", "Intron", "ASR", "Recording", " / yo", "ear.ear_pain", "input_tokens", "before_encounter", "resolutions", "worker_edits", "extraction_mode", "English words", "Check the reported duration", "normalized"]) {
      expect(html).not.toContain(text);
    }
    for (const text of ["Assessment history (1)", "Ear symptoms / Report needs attention", "Original report", "Original spoken words", "Worker words", "Does the child have ear pain?", "Please review the report and confirm the findings on the assessment.", "The answer was unclear", "Maybe pain"]) {
      expect(html).toContain(text);
    }
    expect(html).toContain('role="alert">Could not process these findings.');
    expect(JSON.stringify(interactions)).toBe(before);
  });

  it.each(["same", "typed", "candidate"] as const)("shows the report once for %s nondebug sources without changing history", (source) => {
    const interactions: InteractionTrace[] = [{ id: "1", timestamp: "today", assessment: "ear", status: "accepted",
      source: source === "candidate" ? {} : { submitted_text: "Original report words", ...(source === "same" ? { raw_asr_transcript: "Original report words" } : {}) },
      candidate: { assessment: "ear", input_text: "Original report words", extraction_mode: "frontier", changes: [], warnings: [], english_rendering: "Original report words" },
    }];
    const before = JSON.stringify(interactions);
    const html = renderToStaticMarkup(<InteractionHistory interactions={interactions} showDebug={false} />);
    expect(html.match(/Original report words/g)).toHaveLength(1);
    expect(html).not.toContain("Please review the report");
    expect(html).not.toMatch(/<details[^>]*open/);
    expect(JSON.stringify(interactions)).toBe(before);
  });

  it.each([["transcribed", "Report received"], ["candidate", "Awaiting confirmation"], ["accepted", "Reviewed"], ["rejected", "Not accepted"]] as const)("uses a human mobile status for %s", (status, label) => {
    const entry: InteractionTrace = { id: "1", timestamp: "today", assessment: "full-note", source: {}, status };
    expect(renderToStaticMarkup(<InteractionHistory interactions={[entry]} showDebug={false} />)).toContain(`Full report / ${label}`);
    expect(renderToStaticMarkup(<InteractionHistory interactions={[{ ...entry, pending: true }]} showDebug={false} />)).toContain("request in progress");
  });
});
