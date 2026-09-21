import { useEffect, useRef, useState } from "react";
import type { AssessmentCandidate, AssessmentEvaluation, AssessmentId, InteractionTrace, Resolutions } from "../types";
import { acceptAssessment, evaluateAssessment } from "./api";
import { assessmentIds, createRequestGate, draftKey, hasMeaningfulEvidence, normalizePatientName, parseDraft, recordDraftInteraction, unresolvedChanges, type AssessmentDraft } from "./assessment";

const emptyDraft = (revision = 0): AssessmentDraft => ({ version: 1, encounter: {}, attempted: [], revision, interactions: [] });
const validIntakeAge = (age: unknown): age is number => typeof age === "number" && Number.isInteger(age) && age >= 2 && age <= 59;
const encounterAge = (encounter: Record<string, unknown>) => (encounter.patient_facts as Record<string, unknown> | undefined)?.age_months;

export function useAssessmentSession() {
  const [restored] = useState(() => {
    try { return { draft: parseDraft(sessionStorage.getItem(draftKey)), hint: "" }; }
    catch { return { draft: null, hint: "The tab draft could not be restored. Storage may be unavailable; do not rely on reload to save findings." }; }
  });
  const pendingRestore = useRef(restored.draft && (
    restored.draft.patientName || hasMeaningfulEvidence(restored.draft.encounter) || restored.draft.attempted.length || restored.draft.interactions?.length
  ) ? restored.draft : null);
  const [needsResumeDecision, setNeedsResumeDecision] = useState(Boolean(pendingRestore.current));
  // A saved encounter is not a default answer set for a new patient.
  const [draft, setDraft] = useState(emptyDraft());
  const current = useRef(draft);
  const [evaluation, setEvaluation] = useState<AssessmentEvaluation | null>(null);
  const evaluationRef = useRef<AssessmentEvaluation | null>(null);
  const [hasData, setHasData] = useState(false);
  const retainRef = useRef(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState("");
  const [storageHint, setStorageHint] = useState(restored.hint);
  const [gate] = useState(createRequestGate);

  function store(next: AssessmentDraft) {
    current.current = next;
    setDraft(next);
    try { sessionStorage.setItem(draftKey, JSON.stringify(next)); setStorageHint(""); }
    catch {
      // An older saved encounter must not survive a failed save of newer evidence.
      try {
        sessionStorage.removeItem(draftKey);
        setStorageHint("Tab storage is full or unavailable. The older saved draft was removed to prevent restoring stale evidence. Current findings and full interaction history remain in memory only; reload will lose them. Use synthetic data only.");
      } catch {
        setStorageHint("Tab storage is full or unavailable, and the older saved draft could not be removed. Current findings and full interaction history remain in memory only. Safe restoration cannot be guaranteed: close this tab when finished; do not reload, as it may restore stale evidence.");
      }
    }
  }

  function recordInteraction(interaction: InteractionTrace) {
    store(recordDraftInteraction(current.current, interaction));
  }

  function rejectPending(reason: string) {
    for (const entry of current.current.interactions ?? []) {
      if (entry.status === "candidate" || entry.status === "transcribed") {
        recordInteraction({ ...entry, pending: false, status: "rejected", error: reason });
      }
    }
  }

  const wasInterrupted = (entry: InteractionTrace) => !entry.interruption_acknowledged
    && entry.status === "rejected" && entry.error === "Request interrupted by tab reload; no result accepted.";

  async function run(operation: (signal: AbortSignal) => Promise<AssessmentEvaluation>, attempted: AssessmentId[], retain: boolean, interaction?: InteractionTrace, intakeName?: string) {
    if (pendingRestore.current || busyRef.current) return false;
    busyRef.current = true;
    setBusy(true);
    setError("");
    const request = gate.begin(current.current.revision);
    try {
      const next = await operation(request.signal);
      if (!request.isCurrent(current.current.revision)) return false;
      const patientName = intakeName ?? current.current.patientName;
      // Legacy identity-only drafts can load a template, but a known intake age cannot be cleared.
      if (patientName && (intakeName !== undefined || validIntakeAge(encounterAge(current.current.encounter)))
        && !validIntakeAge(encounterAge(next.encounter))) {
        throw new Error("Intake age must remain a whole number from 2 to 59 months. Accepted findings are unchanged.");
      }
      let accepted: AssessmentDraft = {
        version: 1, encounter: next.encounter, attempted, revision: current.current.revision + 1,
        ...(patientName ? { patientName } : {}),
        interactions: current.current.interactions ?? [],
      };
      if (interaction) accepted = recordDraftInteraction(accepted, { ...interaction, status: "accepted", pending: false, result: next, error: undefined });
      current.current = accepted;
      setDraft(accepted);
      setEvaluation(next);
      evaluationRef.current = next;
      retainRef.current = retain;
      setHasData(retain);
      if (retain || accepted.patientName || accepted.interactions?.length) store(accepted);
      return true;
    } catch (failure) {
      if (request.isCurrent(current.current.revision)) {
        const message = failure instanceof Error ? failure.message : "The assessment service could not be reached. Accepted findings are unchanged.";
        setError(message);
        if (interaction) recordInteraction({ ...interaction, status: "failed", pending: false, error: message });
      }
      return false;
    } finally {
      // Successful commits increment revision; request identity still owns the busy flag.
      if (request.isCurrent()) { busyRef.current = false; setBusy(false); }
    }
  }

  function refresh() {
    if (pendingRestore.current) return Promise.resolve(false);
    const snapshot = current.current;
    const retain = retainRef.current;
    return run((signal) => evaluateAssessment(retain ? snapshot.encounter : undefined, snapshot.attempted, signal), snapshot.attempted, retain);
  }

  useEffect(() => {
    busyRef.current = false;
    void refresh();
    return () => { gate.cancel(); busyRef.current = false; };
    // Restoration is evaluated once per mount; computed results are never restored.
  }, []);

  function reset() {
    pendingRestore.current = null;
    setNeedsResumeDecision(false);
    gate.cancel();
    busyRef.current = false;
    const next = emptyDraft(current.current.revision + 1);
    current.current = next;
    setDraft(next);
    setEvaluation(null);
    evaluationRef.current = null;
    retainRef.current = false;
    setHasData(false);
    setError("");
    try { sessionStorage.removeItem(draftKey); setStorageHint(""); }
    catch { setStorageHint("The saved tab draft could not be cleared. Close this tab to end the session; do not reload an old draft."); }
    void run((signal) => evaluateAssessment(undefined, [], signal), [], false);
  }

  return {
    ...draft, interactions: draft.interactions ?? [], evaluation, hasData, busy, error, storageHint, ready: evaluation !== null,
    needsResumeDecision,
    resumeSaved() {
      const saved = pendingRestore.current;
      if (!saved) return Promise.resolve(false);
      pendingRestore.current = null;
      setNeedsResumeDecision(false);
      current.current = saved;
      setDraft(saved);
      retainRef.current = true;
      setHasData(true);
      return run((signal) => evaluateAssessment(saved.encounter, saved.attempted, signal), saved.attempted, true);
    },
    interruptedCount: (draft.interactions ?? []).filter(wasInterrupted).length,
    acknowledgeInterrupted() {
      store({ ...current.current, interactions: (current.current.interactions ?? []).map((entry) =>
        wasInterrupted(entry) ? { ...entry, interruption_acknowledged: true } : entry) });
    },
    currentRevision: () => current.current.revision,
    snapshot: (): { encounter: Record<string, unknown>; revision: number; evaluation: AssessmentEvaluation | null; interactions?: InteractionTrace[] } =>
      ({ encounter: current.current.encounter, revision: current.current.revision, evaluation: evaluationRef.current, interactions: current.current.interactions }),
    refresh, reset, recordInteraction, rejectPending,
    updateIntake(name: string, ageMonths: number, expectedRevision: number): Promise<boolean> {
      if (pendingRestore.current || busyRef.current || !evaluationRef.current) return Promise.resolve(false);
      const patientName = normalizePatientName(name);
      if (!patientName || !validIntakeAge(ageMonths)) {
        setError("Enter a patient name of 1 to 200 characters and a whole-number age from 2 to 59 months.");
        return Promise.resolve(false);
      }
      const snapshot = current.current;
      if (expectedRevision !== snapshot.revision) {
        setError("Intake is stale. Review the current patient details before applying.");
        return Promise.resolve(false);
      }
      const encounter = structuredClone(snapshot.encounter);
      encounter.patient_facts = { ...(encounter.patient_facts as Record<string, unknown>), age_months: ageMonths };
      return run(async (signal) => {
        const next = await evaluateAssessment(encounter, snapshot.attempted, signal);
        if (next.analysis?.schema_valid !== true || next.analysis.error || next.analysis.state === "ERROR"
          || encounterAge(next.encounter) !== ageMonths) {
          throw new Error("The assessment service could not validate intake. Accepted findings are unchanged.");
        }
        return next;
      }, snapshot.attempted, true, undefined, patientName);
    },
    evaluate(encounter: Record<string, unknown>, attempted: AssessmentId[], interaction?: InteractionTrace) {
      if (current.current.patientName && !validIntakeAge(encounterAge(encounter))) {
        setError("Intake age must remain a whole number from 2 to 59 months. Accepted findings are unchanged.");
        return Promise.resolve(false);
      }
      return run((signal) => evaluateAssessment(encounter, attempted, signal), attempted, true, interaction);
    },
    accept(candidate: AssessmentCandidate, resolutions: Resolutions, revision: number, interaction?: InteractionTrace) {
      if (revision !== current.current.revision || unresolvedChanges(candidate.changes, resolutions).length) {
        setError("Review is stale or has unresolved choices. Interpret the findings again before applying.");
        return Promise.resolve(false);
      }
      if (current.current.patientName && candidate.changes.some((change) => change.field === "patient_facts.age_months"
        && resolutions[change.field] !== "keep" && (resolutions[change.field] === "unknown" || !validIntakeAge(change.value)))) {
        setError("Intake age is required. Keep the current age or replace it with a whole number from 2 to 59 months.");
        return Promise.resolve(false);
      }
      // Completion attempts follow applied field ownership, not shared evaluation dependencies.
      const entries: Record<string, AssessmentId> = {
        "patient_facts.has_cough_or_difficult_breathing": "respiratory",
        "patient_facts.has_diarrhoea": "diarrhoea",
        "patient_facts.has_fever": "fever",
        "patient_facts.has_ear_problem": "ear",
      };
      const appliedOwners = candidate.assessment === "full-note" ? candidate.changes
        .filter((change) => resolutions[change.field] !== "keep")
        .map((change) => entries[change.field] ?? (change.field.startsWith("danger_signs.") ? "danger" : change.field.split(".")[0]))
        .filter((owner): owner is AssessmentId => assessmentIds.includes(owner as AssessmentId)) : [candidate.assessment];
      const attempted = [...new Set([...current.current.attempted, ...appliedOwners])];
      const encounter = current.current.encounter;
      const trace: InteractionTrace = { ...interaction, id: interaction?.id ?? crypto.randomUUID(),
        timestamp: interaction?.timestamp ?? new Date().toISOString(), assessment: candidate.assessment,
        source: interaction?.source ?? { submitted_text: candidate.input_text },
        status: "candidate", pending: true, candidate, resolutions, before_encounter: encounter };
      if (pendingRestore.current || busyRef.current) return Promise.resolve(false);
      recordInteraction(trace);
      return run((signal) => acceptAssessment(candidate, encounter, resolutions, attempted, signal), attempted, true, trace);
    },
  };
}
