import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { InteractionHistory } from "./InteractionHistory";
import type { InteractionTrace } from "../types";

describe("local interaction history", () => {
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
  });
});
