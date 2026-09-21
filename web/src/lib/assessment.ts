import type { AssessmentCandidate, AssessmentChange, AssessmentId, AssessmentProgress, CaptureScope, InteractionTrace, Resolutions } from "../types";

export const assessmentIds: AssessmentId[] = ["danger", "respiratory", "diarrhoea", "fever", "ear"];
export const draftKey = "edge-imci.assessment.v1";

export interface AssessmentDraft {
  version: 1;
  encounter: Record<string, unknown>;
  attempted: AssessmentId[];
  revision: number;
  interactions?: InteractionTrace[];
}

export function parseDraft(raw: string | null): AssessmentDraft | null {
  if (!raw) return null;
  const draft = JSON.parse(raw) as AssessmentDraft;
  if (draft.version !== 1 || !draft.encounter || typeof draft.encounter !== "object"
    || Array.isArray(draft.encounter) || !Array.isArray(draft.attempted)
    || !draft.attempted.every((id) => assessmentIds.includes(id))
    || !Number.isSafeInteger(draft.revision) || draft.revision < 0) {
    throw new Error("Invalid saved assessment");
  }
  const interactions = draft.interactions === undefined ? [] : draft.interactions;
  if (!Array.isArray(interactions) || !interactions.every(validInteraction)) throw new Error("Invalid saved interaction trace");
  // Historical outputs are debug data only. The hook re-evaluates accepted input.
  return { version: 1, encounter: draft.encounter, attempted: draft.attempted, revision: draft.revision,
    interactions: interactions.map((entry) => entry.pending
      ? { ...entry, pending: false, status: "rejected", error: "Request interrupted by tab reload; no result accepted." } : entry) };
}

function validInteraction(value: unknown): value is InteractionTrace {
  if (!value || typeof value !== "object") return false;
  const entry = value as InteractionTrace;
  const record = (item: unknown) => Boolean(item && typeof item === "object" && !Array.isArray(item));
  if (typeof entry.id !== "string" || typeof entry.timestamp !== "string"
    || ![...assessmentIds, "full-note"].includes(entry.assessment)
    || !["transcribed", "candidate", "accepted", "rejected", "failed"].includes(entry.status)
     || !record(entry.source) || (entry.pending !== undefined && typeof entry.pending !== "boolean")) return false;
  if (entry.interruption_acknowledged !== undefined && typeof entry.interruption_acknowledged !== "boolean") return false;
  const source = entry.source;
  if (![source.recording_id, source.asr_provider, source.raw_asr_transcript, source.submitted_text, entry.error]
    .every((item) => item === undefined || typeof item === "string")) return false;
  if (source.asr_model != null && typeof source.asr_model !== "string") return false;
  if (source.language !== undefined && !["en", "pcm", "yo", "ig", "ha"].includes(source.language)) return false;
  if (source.question !== undefined && (!record(source.question) || typeof source.question.field !== "string" || typeof source.question.text !== "string")) return false;
  if (entry.candidate !== undefined && (!record(entry.candidate) || ![...assessmentIds, "full-note"].includes(entry.candidate.assessment)
    || typeof entry.candidate.input_text !== "string" || !Array.isArray(entry.candidate.changes) || !Array.isArray(entry.candidate.warnings))) return false;
  return [entry.before_encounter, entry.result, entry.native_preview, entry.diagnostic_result, entry.resolutions].every((item) => item === undefined || record(item));
}

export function recordDraftInteraction(draft: AssessmentDraft, interaction: InteractionTrace): AssessmentDraft {
  // Snapshot the sidecar independently, without changing clinical inputs or revision.
  const snapshot = JSON.parse(JSON.stringify(interaction)) as InteractionTrace;
  const interactions = [...(draft.interactions ?? [])];
  const index = interactions.findIndex((entry) => entry.id === snapshot.id);
  if (index < 0) interactions.push(snapshot);
  else interactions[index] = snapshot;
  return { ...draft, interactions };
}

export function assessmentBadge(progress?: AssessmentProgress, pending = false) {
  if (progress?.status === "URGENT") return { label: "Urgent", kind: "urgent" };
  if (pending) return { label: "Needs review", kind: "incomplete" };
  if (progress?.decision === "BLOCK") return { label: "Blocked", kind: "incomplete" };
  if (progress?.status === "COMPLETE") return { label: "Complete", kind: "complete" };
  if (progress?.status === "INCOMPLETE") return { label: "Needs info", kind: "incomplete" };
  return { label: "Not started", kind: "pending" };
}

export function unresolvedChanges(changes: AssessmentChange[], resolutions: Resolutions) {
  return changes.filter((change) => (change.conflict || change.outside_assessment || change.uncertain || change.review_changed || change.value === null)
    && !["replace", "keep", "unknown"].includes(resolutions[change.field]));
}

export function hasMeaningfulEvidence(encounter: Record<string, unknown>): boolean {
  return Object.values(encounter).some((value) => {
    if (value === null || value === undefined) return false;
    if (typeof value === "object") return hasMeaningfulEvidence(value as Record<string, unknown>);
    return true; // Explicit false and zero are known evidence, not omissions.
  });
}

export function affectedAssessments(assessment: CaptureScope, fields: string[]): AssessmentId[] {
  const entries: Record<string, AssessmentId> = {
    "patient_facts.has_cough_or_difficult_breathing": "respiratory",
    "patient_facts.has_diarrhoea": "diarrhoea",
    "patient_facts.has_fever": "fever",
    "patient_facts.has_ear_problem": "ear",
  };
  if (assessment === "full-note" && !fields.length) return [...assessmentIds];
  const affected = new Set<AssessmentId>(assessment === "full-note" ? [] : [assessment]);
  // UI group routing only. Shared age/danger evidence conservatively marks every group pending.
  for (const field of fields) {
    if (field === "patient_facts.age_months" || field.startsWith("danger_signs.")) return [...assessmentIds];
    const group = entries[field] ?? field.split(".")[0] as AssessmentId;
    if (assessmentIds.includes(group)) affected.add(group);
    else return [...assessmentIds];
  }
  return assessmentIds.filter((id) => affected.has(id));
}

export function pendingAssessmentIds(fullTextPending: boolean, capturePending: AssessmentId[]): AssessmentId[] {
  return fullTextPending ? [...assessmentIds] : capturePending;
}

export function workerRetraction(assessment: AssessmentId, changes: AssessmentChange[]): AssessmentCandidate {
  return {
    assessment, input_text: "Worker-requested retraction", extraction_mode: "worker-review",
    changes: changes.map((change) => ({ ...change, value: null, conflict: true, outside_assessment: false })),
    warnings: [],
  };
}

// Cancellation alone cannot prevent a response (or microphone grant) already queued.
export function createRequestGate() {
  let identity = 0;
  let controller: AbortController | undefined;
  const cancel = () => { identity += 1; controller?.abort(); };
  return {
    cancel,
    begin(revision = 0) {
      cancel();
      controller = new AbortController();
      const signal = controller.signal;
      const requestId = identity;
      return { signal, isCurrent: (currentRevision = revision) => requestId === identity && !signal.aborted && currentRevision === revision };
    },
  };
}
