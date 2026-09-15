import { describe, expect, it } from "vitest";
import type { AssessmentCandidate, ClinicalValue, FieldDescriptor, WorkerEdit } from "../types";
import { clinicalValue, effectiveChanges, guideResolutions, parseClinicalInput, pendingEvidenceVersion } from "./guideEvidence";
import type { CaptureJob } from "./useVoiceCapture";

const boolean: FieldDescriptor = { path: "ear.ear_pain", label: "Ear pain", kind: "boolean", nullable: true, assessments: ["ear"] };
const integer: FieldDescriptor = { path: "respiratory.respiratory_rate", label: "Respiratory rate", kind: "integer", nullable: true,
  minimum: 0, maximum: 200, unit: "breaths/min", assessments: ["respiratory"] };
const number: FieldDescriptor = { path: "fever.temperature_c", label: "Temperature", kind: "number", nullable: true, unit: "C", assessments: ["fever"] };
const enumeration: FieldDescriptor = { path: "diarrhoea.dehydration.skin_pinch", label: "Skin pinch", kind: "enum", nullable: true,
  options: [{ value: "NORMAL", label: "Normal" }, { value: "VERY_SLOWLY", label: "Very slowly" }], assessments: ["diarrhoea"] };

function job(workerEdits?: Record<string, WorkerEdit>): CaptureJob {
  const originalCandidate: AssessmentCandidate = { assessment: "ear", input_text: "Maybe ear pain", extraction_mode: "test", warnings: [],
    changes: [{ field: boolean.path, label: boolean.label, previous: false, value: null, conflict: true, outside_assessment: false, uncertain: true }],
    uncertainties: [{ field: boolean.path, source_text: "Maybe ear pain", reason: "Not established" }],
    evidence_spans: [{ field: boolean.path, source_text: "Maybe ear pain" }] };
  return { id: "capture", assessment: "ear", status: "review", originalEncounter: { ear: { ear_pain: false } }, originalRevision: 10,
    originalCandidate, candidate: structuredClone(originalCandidate), reviewRevision: 10, reviewVersion: 1, changedFields: [], workerEdits,
    trace: { id: "capture", assessment: "ear", timestamp: "2026-09-15T12:00:00Z", status: "candidate", source: { raw_asr_transcript: "Maybe ear pain" } } };
}

describe("schema-typed clinical input", () => {
  it.each([true, false, null])("preserves boolean %j without coercion", (value) => {
    expect(parseClinicalInput(boolean, value)).toEqual({ value });
  });

  it.each(["true", "false", "Yes", 0, 1])("rejects non-boolean %j", (value) => {
    expect(parseClinicalInput(boolean, value)).toEqual({ error: expect.any(String) });
  });

  it("uses enum wire values rather than labels and preserves explicit unknown", () => {
    expect(parseClinicalInput(enumeration, "VERY_SLOWLY")).toEqual({ value: "VERY_SLOWLY" });
    expect(parseClinicalInput(enumeration, "Very slowly")).toEqual({ error: expect.any(String) });
    expect(parseClinicalInput(enumeration, "normal")).toEqual({ error: expect.any(String) });
    expect(parseClinicalInput(enumeration, null)).toEqual({ value: null });
  });

  it.each([
    [integer, "0", 0], [integer, 42, 42], [integer, " 042 ", 42], [integer, "200", 200],
    [number, "37.5", 37.5], [number, ".5", 0.5], [number, "-1.5", -1.5], [number, "1.", 1],
  ] satisfies Array<[FieldDescriptor, ClinicalValue, number]>)("parses %j input %j as an actual number", (descriptor, input, value) => {
    expect(parseClinicalInput(descriptor, input)).toEqual({ value, raw: String(input) });
  });

  it.each(["", "   "])("never defaults empty numeric text %j to zero", (raw) => {
    expect(parseClinicalInput(integer, raw)).toEqual({ value: null, raw });
    expect(parseClinicalInput(number, raw)).toEqual({ value: null, raw });
    expect(parseClinicalInput(number, null)).toEqual({ value: null });
  });

  it.each(["-", "12x", "1e2", "0x10", "1,2", "Infinity", "NaN", true, false])("retains invalid numeric input %j without inventing a value", (input) => {
    expect(parseClinicalInput(number, input)).toEqual({ raw: String(input), error: expect.any(String) });
  });

  it.each(["-1", "201", "1.5", "9007199254740992"])("enforces integer bounds and precision for %j", (raw) => {
    expect(parseClinicalInput(integer, raw)).toEqual({ raw, error: expect.any(String) });
  });

  it("does not invent bounds absent from the descriptor and rejects non-finite numbers", () => {
    expect(parseClinicalInput(number, "1000")).toEqual({ value: 1000, raw: "1000" });
    expect(parseClinicalInput(number, "9".repeat(400))).toEqual({ raw: "9".repeat(400), error: expect.any(String) });
  });

  it("reads sparse nested accepted evidence without losing false or zero", () => {
    const encounter = { ear: { ear_pain: false }, diarrhoea: { dehydration: { skin_pinch: "NORMAL" } }, respiratory: { respiratory_rate: 0 } };
    expect(clinicalValue(encounter, boolean.path)).toBe(false);
    expect(clinicalValue(encounter, enumeration.path)).toBe("NORMAL");
    expect(clinicalValue(encounter, integer.path)).toBe(0);
    expect(clinicalValue(encounter, number.path)).toBeNull();
    expect(clinicalValue({ diarrhoea: null }, enumeration.path)).toBeNull();
    expect(encounter).not.toHaveProperty("fever");
  });
});

describe("draft evidence and explicit resolutions", () => {
  it("overlays worker corrections separately, clears effective uncertainty, and leaves original quotes and uncertainty immutable", () => {
    const draft = job({ [boolean.path]: { value: true, label: boolean.label, previous: false, revision: 10 } });
    const before = structuredClone(draft);
    Object.freeze(draft.originalCandidate!.changes[0]);
    Object.freeze(draft.originalCandidate!.changes);
    Object.freeze(draft.originalCandidate!);
    expect(effectiveChanges(draft)).toEqual([{ ...before.originalCandidate!.changes[0], value: true, uncertain: false, worker_entered: true }]);
    expect(draft).toEqual(before);
    expect(draft.originalCandidate!.uncertainties).toEqual(before.originalCandidate!.uncertainties);
    expect(draft.originalCandidate!.evidence_spans).toEqual(before.originalCandidate!.evidence_spans);
    expect(guideResolutions(draft)).toEqual({ [boolean.path]: "replace" });
  });

  it("keeps unresolved model uncertainty until the worker explicitly chooses an answer", () => {
    const draft = job();
    expect(effectiveChanges(draft)).toEqual(draft.originalCandidate!.changes);
    expect(effectiveChanges(draft)[0]).not.toBe(draft.originalCandidate!.changes[0]);
    expect(guideResolutions(draft)).toEqual({});
    draft.workerEdits = { [boolean.path]: { value: null, previous: false, label: boolean.label, revision: 10 } };
    expect(guideResolutions(draft)).toEqual({ [boolean.path]: "unknown" });
    expect(effectiveChanges(draft)[0]).toMatchObject({ value: null, uncertain: false, worker_entered: true });
  });

  it("retains same-value reconfirmation and explicit unknown rows absent from extraction", () => {
    const draft = job({
      [integer.path]: { value: 42, raw: "42", previous: 42, label: integer.label, revision: 10 },
      [number.path]: { value: null, previous: null, label: number.label, revision: 10 },
    });
    const changes = effectiveChanges(draft);
    expect(changes).toHaveLength(3);
    expect(changes[1]).toMatchObject({ field: integer.path, value: 42, previous: 42, conflict: false, worker_entered: true });
    expect(changes[2]).toMatchObject({ field: number.path, value: null, previous: null, conflict: false, worker_entered: true });
    draft.candidate = { ...draft.candidate!, changes };
    expect(guideResolutions(draft)).toEqual({ [integer.path]: "replace", [number.path]: "unknown" });
  });

  it("records keep separately without recasting uncertain model evidence as a worker finding", () => {
    const draft = job({ [boolean.path]: { value: false, previous: false, label: boolean.label, revision: 10, keep: true } });
    expect(effectiveChanges(draft)[0]).toMatchObject({ value: null, uncertain: true, worker_entered: false });
    expect(guideResolutions(draft)).toEqual({ [boolean.path]: "keep" });
  });

  it("does not resolve invalid edits or reuse a choice after its review context changed", () => {
    const draft = job({ [boolean.path]: { value: true, previous: false, label: boolean.label, revision: 10 } });
    draft.reviewRevision = 11;
    draft.candidate!.changes[0].review_changed = true;
    expect(guideResolutions(draft)).toEqual({});
    draft.workerEdits![boolean.path].revision = 11;
    expect(guideResolutions(draft)).toEqual({ [boolean.path]: "replace" });
    draft.workerEdits![boolean.path].error = "Invalid answer";
    expect(guideResolutions(draft)).toEqual({});
  });

  it("retains valid choices for unchanged rows across re-review without resolving unedited rows", () => {
    const draft = job({ [boolean.path]: { value: true, previous: false, label: boolean.label, revision: 10 },
      "not.in.review": { value: true, previous: null, label: "Not reviewed", revision: 10 } });
    draft.reviewRevision = 11;
    expect(guideResolutions(draft)).toEqual({ [boolean.path]: "replace" });
  });
});

describe("pending evidence fingerprint", () => {
  it("ignores preparation metadata and review lifecycle changes when the underlying proposals are unchanged", () => {
    const draft = job();
    draft.status = "captured";
    const version = pendingEvidenceVersion([draft], [boolean.path], draft.originalEncounter);
    draft.status = "preparing_review";
    expect(pendingEvidenceVersion([draft], [boolean.path], draft.originalEncounter)).toBe(version);
    draft.status = "review";
    draft.reviewVersion += 1;
    draft.reviewRevision = 11;
    draft.reviewEditVersion = 0;
    draft.changedFields = [boolean.path];
    draft.candidate!.changes[0] = { ...draft.candidate!.changes[0], previous: true, conflict: true, review_changed: true };
    expect(pendingEvidenceVersion([draft], [boolean.path], draft.originalEncounter)).toBe(version);
  });

  it("tracks relevant proposal arrival, worker value changes and discard, including unselected jobs in the same assessment", () => {
    const first = job();
    const second = job(); second.id = "second-capture";
    second.originalCandidate!.changes[0].value = true;
    const version = pendingEvidenceVersion([first], [boolean.path], {});
    const arrived = pendingEvidenceVersion([first, second], [boolean.path], {});
    expect(arrived).not.toBe(version);
    second.workerEdits = { [boolean.path]: { value: false, previous: null, label: boolean.label, revision: 10 } };
    expect(pendingEvidenceVersion([first, second], [boolean.path], {})).not.toBe(arrived);
    second.status = "discarded";
    expect(pendingEvidenceVersion([first, second], [boolean.path], {})).toBe(version);
  });

  it("ignores disjoint fields, unfinished extraction, and terminal jobs", () => {
    const first = job();
    const other = job(); other.id = "other-capture";
    const version = pendingEvidenceVersion([first], [boolean.path], {});
    const disjoint = job(); disjoint.id = "disjoint";
    disjoint.originalCandidate!.changes[0].field = integer.path;
    expect(pendingEvidenceVersion([first, disjoint], [boolean.path], {})).toBe(version);
    for (const status of ["accepted", "discarded", "failed"] as const) {
      other.status = status;
      expect(pendingEvidenceVersion([first, other], [boolean.path], {})).toBe(version);
    }
    other.status = "extracting"; other.originalCandidate = undefined;
    expect(pendingEvidenceVersion([first, other], [boolean.path], {})).toBe(version);
  });

  it("fingerprints a keep choice using the accepted value rather than the original recording's value", () => {
    const draft = job({ [boolean.path]: { value: false, previous: false, label: boolean.label, revision: 10, keep: true } });
    const version = pendingEvidenceVersion([draft], [boolean.path], { ear: { ear_pain: false } });
    draft.originalCandidate!.changes[0].value = true;
    expect(pendingEvidenceVersion([draft], [boolean.path], { ear: { ear_pain: false } })).toBe(version);
    expect(pendingEvidenceVersion([draft], [boolean.path], { ear: { ear_pain: true } })).not.toBe(version);
  });
});
