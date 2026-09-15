import { describe, expect, it } from "vitest";
import { affectedAssessments, assessmentBadge, assessmentIds, createRequestGate, parseDraft, pendingAssessmentIds, recordDraftInteraction, unresolvedChanges, workerRetraction } from "./assessment";
import type { AssessmentChange, AssessmentProgress, InteractionTrace, Resolution } from "../types";

const progress = (status: AssessmentProgress["status"], decision: AssessmentProgress["decision"] = "ASK"): AssessmentProgress => ({
  status, decision, missing_fields: [], question: null, blockers: [],
});
const change: AssessmentChange = { field: "danger_signs.convulsing_now", label: "Convulsing now", previous: false, value: true, conflict: true, outside_assessment: false };

describe("assessment authority and review", () => {
  it("routes candidate fields to every affected UI section, including shared evidence", () => {
    expect(affectedAssessments("ear", ["fever.stiff_neck", "ear.ear_pain"])).toEqual(["fever", "ear"]);
    expect(affectedAssessments("danger", ["patient_facts.has_cough_or_difficult_breathing"])).toEqual(["danger", "respiratory"]);
    expect(affectedAssessments("ear", ["patient_facts.age_months"])).toEqual(assessmentIds);
    expect(affectedAssessments("diarrhoea", ["danger_signs.lethargic_or_unconscious"])).toEqual(assessmentIds);
    expect(affectedAssessments("ear", [])).toEqual(["ear"]);
  });

  it("keeps dirty full text pending without a request or candidate, independently of capture selection", () => {
    expect(pendingAssessmentIds(true, [])).toEqual(assessmentIds);
    expect(pendingAssessmentIds(true, ["ear"])).toEqual(assessmentIds);
    expect(pendingAssessmentIds(false, ["ear"])).toEqual(["ear"]);
    expect(pendingAssessmentIds(false, [])).toEqual([]);
  });

  it("constructs explicit null retractions with the exact accepted previous value", () => {
    const candidate = workerRetraction("danger", [change]);
    expect(candidate).toEqual({
      assessment: "danger", input_text: "Worker-requested retraction", extraction_mode: "worker-review",
      changes: [{ ...change, value: null, conflict: true, outside_assessment: false }], warnings: [],
    });
    expect(change.value).toBe(true);
    expect(unresolvedChanges(candidate.changes, {})).toHaveLength(1);
    expect(unresolvedChanges(candidate.changes, { [change.field]: "unknown" })).toEqual([]);
  });

  it("does not authorize completion before evaluation, or from a pending candidate", () => {
    expect(assessmentBadge().label).toBe("Not started");
    expect(assessmentBadge(progress("COMPLETE", "COMPLETE")).label).toBe("Complete");
    expect(assessmentBadge(progress("COMPLETE", "COMPLETE"), true).label).toBe("Needs review");
    expect(assessmentBadge(progress("INCOMPLETE")).label).toBe("Needs info");
    expect(assessmentBadge(progress("INCOMPLETE", "BLOCK")).label).toBe("Blocked");
  });

  it.each([
    ["NOT_STARTED", "Not started", "pending"],
    ["INCOMPLETE", "Needs info", "incomplete"],
    ["COMPLETE", "Complete", "complete"],
  ] as const)("preserves %s badges despite a global urgent decision", (status, label, kind) => {
    expect(assessmentBadge(progress(status, "URGENT"))).toEqual({ label, kind });
    expect(assessmentBadge(progress(status, "URGENT"), true)).toEqual({ label: "Needs review", kind: "incomplete" });
  });

  it.each([false, true])("retains accepted urgency with pending review=%s", (pending) => {
    expect(assessmentBadge(progress("URGENT", "URGENT"), pending)).toEqual({ label: "Urgent", kind: "urgent" });
  });

  it("requires choices for conflicts and out-of-assessment changes, even from unknown", () => {
    const outside = { ...change, field: "ear.ear_pain", previous: null, conflict: false, outside_assessment: true };
    const ordinary = { ...change, field: "patient_facts.age_months", conflict: false };
    expect(unresolvedChanges([change, outside, ordinary], {})).toEqual([change, outside]);
    for (const choice of ["replace", "keep", "unknown"] as Resolution[]) {
      expect(unresolvedChanges([change, outside], { [change.field]: choice, [outside.field]: choice })).toEqual([]);
    }
    expect(unresolvedChanges([change], { [change.field]: "invalid" as Resolution })).toEqual([change]);
  });

  it("requires explicit uncertainty and every null proposal to be resolved, even from unknown", () => {
    const uncertain = { ...change, previous: null, value: null, conflict: false, uncertain: true };
    expect(unresolvedChanges([uncertain], {})).toEqual([uncertain]);
    expect(unresolvedChanges([{ ...uncertain, uncertain: undefined }], {})).toHaveLength(1);
    for (const choice of ["replace", "keep", "unknown"] as Resolution[]) {
      expect(unresolvedChanges([uncertain], { [uncertain.field]: choice })).toEqual([]);
    }
  });
});

describe("request revision fence", () => {
  it("rejects replies after reset, edits, switches, newer requests, or accepted revisions", () => {
    const gate = createRequestGate();
    const beforeReset = gate.begin(8);
    gate.cancel();
    expect(beforeReset.signal.aborted).toBe(true);
    expect(beforeReset.isCurrent(8)).toBe(false);
    const beforeEdit = gate.begin(9);
    const afterEdit = gate.begin(9);
    expect(beforeEdit.isCurrent(9)).toBe(false);
    expect(afterEdit.isCurrent(9)).toBe(true);
    expect(afterEdit.isCurrent(10)).toBe(false);
    gate.cancel();
    expect(afterEdit.isCurrent(9)).toBe(false);
  });
});

describe("tab draft", () => {
  it("restores only accepted inputs and revision, never clinical results or audio", () => {
    const draft = { version: 1, encounter: { patient_facts: { age_months: 24 } }, attempted: ["danger"], revision: 3 };
    expect(parseDraft(JSON.stringify({ ...draft, analysis: { is_complete: true }, audio: "blob:old" }))).toEqual({ ...draft, interactions: [] });
    expect(parseDraft(null)).toBeNull();
  });

  it("snapshots and updates sidecar IDs without changing clinical inputs or revision", () => {
    const draft = { version: 1 as const, encounter: { ear: { ear_pain: true } }, attempted: [], revision: 3 };
    const trace: InteractionTrace = { id: "capture-1", timestamp: "2026-09-13", assessment: "ear", status: "candidate",
      source: { raw_asr_transcript: "Original", submitted_text: "Edited" }, before_encounter: draft.encounter };
    const first = recordDraftInteraction(draft, trace);
    trace.source.submitted_text = "Changed later";
    expect(first.interactions?.[0].source.submitted_text).toBe("Edited");
    const updated = recordDraftInteraction(first, { ...first.interactions![0], status: "rejected" });
    const appended = recordDraftInteraction(updated, { ...trace, id: "capture-2", status: "failed", error: "Timeout" });
    expect(appended.interactions?.map((item) => item.status)).toEqual(["rejected", "failed"]);
    expect(appended.revision).toBe(3);
    expect(appended.encounter).toBe(draft.encounter);
    expect(appended.attempted).toBe(draft.attempted);
    expect(parseDraft(JSON.stringify(appended))?.interactions).toEqual(appended.interactions);
  });

  it("restores old empty history and flags interrupted requests without fabricating clinical output", () => {
    const draft = { version: 1, encounter: {}, attempted: [], revision: 0, interactions: [] };
    expect(parseDraft(JSON.stringify(draft))).toEqual(draft);
    const interrupted = { id: "pending", timestamp: "today", assessment: "ear", status: "candidate", pending: true, source: {} };
    expect(parseDraft(JSON.stringify({ ...draft, interactions: [interrupted] }))?.interactions?.[0]).toMatchObject({ status: "rejected", pending: false });
    for (const interactions of [{}, [null], [{ ...interrupted, source: { raw_asr_transcript: 3 } }], [{ ...interrupted, status: "complete" }]]) {
      expect(() => parseDraft(JSON.stringify({ ...draft, interactions }))).toThrow();
    }
  });

  it("rejects incompatible or malformed saved data", () => {
    for (const raw of ["{", "null", JSON.stringify({ version: 2 }), JSON.stringify({ version: 1, encounter: {}, attempted: ["bad"], revision: 1 })]) {
      expect(() => parseDraft(raw)).toThrow();
    }
  });
});
