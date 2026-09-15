import type { AssessmentChange, ClinicalValue, FieldDescriptor, Resolutions, WorkerEdit } from "../types";
import type { CaptureJob } from "./useVoiceCapture";

export function clinicalValue(encounter: Record<string, unknown>, field: string): ClinicalValue {
  return field.split(".").reduce<unknown>((node, part) => node && typeof node === "object"
    ? (node as Record<string, unknown>)[part] : null, encounter) as ClinicalValue ?? null;
}

export function parseClinicalInput(descriptor: FieldDescriptor, input: ClinicalValue): Pick<WorkerEdit, "value" | "raw" | "error"> {
  if (input === null) return { value: null };
  if (descriptor.kind === "boolean") return typeof input === "boolean" ? { value: input } : { error: "Choose Yes, No, or Not assessed." };
  if (descriptor.kind === "enum") return descriptor.options?.some((item) => item.value === input)
    ? { value: input } : { error: "Choose one of the listed observations." };
  const raw = String(input);
  const text = raw.trim();
  if (!text) return { value: null, raw };
  if (!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text)) return { raw, error: "Enter a valid number, or choose Not assessed." };
  const value = Number(text);
  if (!Number.isFinite(value) || (descriptor.kind === "integer" && !Number.isSafeInteger(value))) {
    return { raw, error: "Enter a whole number in the displayed unit." };
  }
  if ((descriptor.minimum !== undefined && value < descriptor.minimum) || (descriptor.maximum !== undefined && value > descriptor.maximum)) {
    return { raw, error: "Value is outside the schema's allowed bounds." };
  }
  return { value, raw };
}

export function effectiveChanges(job: CaptureJob): AssessmentChange[] {
  const original = job.originalCandidate?.changes ?? [];
  const edits = job.workerEdits ?? {};
  const paths = [...new Set([...original.map((row) => row.field), ...Object.keys(edits)])];
  return paths.map((field) => {
    const source = original.find((row) => row.field === field);
    const edit = edits[field];
    if (!edit) return { ...source! };
    const previous = source ? source.previous : edit.previous;
    const value = edit.keep ? (source ? source.value : edit.previous) : edit.value ?? null;
    return { ...source, field, label: source?.label ?? edit.label, previous, value,
      conflict: previous !== null && previous !== value, outside_assessment: source?.outside_assessment ?? false,
      uncertain: edit.keep ? source?.uncertain ?? false : false, worker_entered: !edit.keep };
  });
}

export function guideResolutions(job: CaptureJob): Resolutions {
  const resolutions: Resolutions = {};
  for (const row of job.candidate?.changes ?? []) {
    const edit = job.workerEdits?.[row.field];
    if (!edit || edit.error || (row.review_changed && edit.revision !== job.reviewRevision)) continue;
    resolutions[row.field] = edit.keep ? "keep" : edit.value === null ? "unknown" : "replace";
  }
  return resolutions;
}

export function pendingEvidenceVersion(jobs: CaptureJob[], fields: string[], encounter: Record<string, unknown>): string {
  const included = new Set(fields);
  return JSON.stringify(jobs.filter((job) => job.originalCandidate && !["accepted", "discarded", "failed"].includes(job.status))
    .flatMap((job) => effectiveChanges(job).filter((row) => included.has(row.field)).map((row) => [
      job.id, row.field, job.workerEdits?.[row.field]?.keep ? clinicalValue(encounter, row.field) : row.value,
    ])));
}
