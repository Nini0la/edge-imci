import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ResultPanel } from "./ResultPanel";
import type { AnalysisResult } from "../types";

const result: AnalysisResult = {
  input_text: "Original report", extraction_mode: "private-mode", matched_case_id: "private-fixture", structured_encounter: { ear: { ear_pain: false } },
  structured_view: [], schema_valid: true, extraction_warnings: [], is_complete: true, missing_elements: {}, contradictions: [], is_urgent: false,
  classifications: ["Accepted classification"], urgent_actions: [], final_actions: ["Accepted management"], deferred_actions: [],
  rendered_response: "Accepted classification\nAccepted management", error: null, outside_supported_scope: false, state: "COMPLETE",
  decision_trace: [{ rule_id: "private-rule", pathway: "Ear", classification: "Accepted classification", findings: [["Ear pain", "Absent"]], rule_description: "Accepted clinical rationale" }],
  pipeline_trace: [{ kind: "LEARNED", label: "Private processing step", detail: "private-pipeline" }],
};

describe("ResultPanel debug presentation", () => {
  it("keeps desktop processing trace and rule identifiers by default", () => {
    const html = renderToStaticMarkup(<ResultPanel result={result} />);
    expect(html).toBe(renderToStaticMarkup(<ResultPanel result={result} showDebug />));
    for (const text of ["<code>private-rule</code>", "Processing trace", "Private processing step", "private-pipeline", "Mode: private-mode", "Fixture: private-fixture"]) expect(html).toContain(text);
  });

  it.each([
    ["COMPLETE", "Clinical synthesis ready"],
    ["URGENT_COMPLETE", "Act now"],
    ["INCOMPLETE", "More findings are needed"],
    ["URGENT_INCOMPLETE", "Act now, then complete rapidly"],
    ["OUT_OF_SCOPE", "Use the applicable pathway"],
    ["ERROR", "Review the submitted findings"],
  ] as const)("suppresses only technical output for %s, retaining clinical guidance and immutable evidence", (state, title) => {
    const input: AnalysisResult = { ...result, state, is_complete: state === "COMPLETE" || state === "URGENT_COMPLETE", is_urgent: state.startsWith("URGENT"),
      outside_supported_scope: state === "OUT_OF_SCOPE", error: state === "ERROR" ? "Could not evaluate findings" : null };
    const original = structuredClone(input);
    const html = renderToStaticMarkup(<ResultPanel result={input} showDebug={false} />);
    expect(html).toContain(title);
    for (const hidden of ["<pre", "<code", "JSON", "private-", "Private processing step", "Processing trace", "Technical view"]) expect(html).not.toContain(hidden);
    for (const clinical of ["Why EdgeIMCI reached this result", "Ear pain", "Absent", "Accepted clinical rationale"]) expect(html).toContain(clinical);
    if (state === "ERROR") {
      expect(html).toContain('role="alert">Could not evaluate findings');
      expect(html).not.toContain("Accepted management");
    } else expect(html).toContain("Accepted management");
    expect(input).toEqual(original);
  });

  it.each([false, true])("retains the blocked gate with showDebug=%s", (showDebug) => {
    const html = renderToStaticMarkup(<ResultPanel result={result} blocked showDebug={showDebug} />);
    expect(html).toContain('class="progress-blocked" role="alert"');
    expect(html).toContain("Progress blocked; resolve evidence issues before using final synthesis.");
    for (const hidden of ["Clinical synthesis ready", "Accepted classification", "Accepted management", "Accepted clinical rationale", "private-"]) expect(html).not.toContain(hidden);
  });
});
