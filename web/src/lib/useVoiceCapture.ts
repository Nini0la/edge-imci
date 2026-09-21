import { useEffect, useRef, useState } from "react";
import type { ASRLanguage, AssessmentCandidate, AssessmentId, CaptureScope, ClinicalValue, FieldDescriptor, InteractionTrace, Resolutions, Transcription, WorkerEdit } from "../types";
import { clinicalValue, effectiveChanges, parseClinicalInput, pendingEvidenceVersion } from "./guideEvidence";
import { extractAssessment, prepareAssessmentReview, transcribeAudio } from "./api";
import { createAudioCapture, type AudioState } from "./audio";
import { assessmentIds, normalizePatientName, unresolvedChanges, workerRetraction } from "./assessment";
import { acceptedSectionFields } from "./checklist";
import type { useAssessmentSession } from "./useAssessmentSession";

type Session = ReturnType<typeof useAssessmentSession>;
export interface CaptureContext {
  encounter: Record<string, unknown>;
  revision: number;
  question?: { field: string; text: string };
}
export interface CaptureJob {
  id: string;
  assessment: CaptureScope;
  language?: ASRLanguage;
  status: "recording" | "queued" | "transcribing" | "extracting" | "captured" | "preparing_review" | "review" | "applying" | "accepted" | "failed" | "discarded";
  audio?: Blob;
  inputText?: string;
  transcript?: Transcription;
  originalEncounter: Record<string, unknown>;
  originalRevision: number;
  question?: { field: string; text: string };
  originalCandidate?: AssessmentCandidate;
  candidate?: AssessmentCandidate;
  reviewRevision?: number;
  reviewVersion: number;
  changedFields: string[];
  error?: string;
  trace: InteractionTrace;
  workerEdits?: Record<string, WorkerEdit>;
  editVersion?: number;
  reviewEditVersion?: number;
}

interface CaptureState {
  jobs: CaptureJob[];
  recordingId: string | null;
  audioState: AudioState;
  error: string;
}

const initialState = (): CaptureState => ({ jobs: [], recordingId: null, audioState: "idle", error: "" });

/** Jobs belong to an encounter, not an expanded section or an accepted revision. */
export function createVoiceCapture({ getSession, onChange, transcribe = transcribeAudio, extract = extractAssessment,
  prepare = prepareAssessmentReview, audioFactory = createAudioCapture, audioEnabled = true }: {
  getSession: () => Session;
  onChange: (state: CaptureState) => void;
  transcribe?: typeof transcribeAudio;
  extract?: typeof extractAssessment;
  prepare?: typeof prepareAssessmentReview;
  audioFactory?: typeof createAudioCapture;
  audioEnabled?: boolean;
}) {
  let state = initialState();
  let generation = 0;
  let processing = 0;
  let silent = false;
  const controllers = new Map<string, AbortController>();
  const get = (id: string) => state.jobs.find((job) => job.id === id);
  const publish = () => { if (!silent) onChange({ ...state, jobs: [...state.jobs] }); };
  const update = (id: string, change: Partial<CaptureJob>) => {
    state = { ...state, jobs: state.jobs.map((job) => job.id === id ? { ...job, ...change } : job) };
    publish();
  };
  const record = (job: CaptureJob, change: Partial<InteractionTrace>) => {
    const trace = { ...job.trace, ...change };
    update(job.id, { trace });
    getSession().recordInteraction(trace);
  };
  const fail = (id: string, message: string) => {
    const job = get(id);
    if (!job) return;
    update(id, { status: "failed", error: message });
    record(get(id)!, { status: "failed", pending: false, error: message });
  };

  const microphone = audioEnabled ? audioFactory({
    state(phase) { state = { ...state, audioState: phase }; publish(); },
    audio(blob) {
      const id = state.recordingId;
      state = { ...state, recordingId: null };
      if (!id || get(id)?.status !== "recording") { publish(); return; }
      update(id, { audio: blob, status: "queued" });
      pump();
    },
    error(message) {
      const id = state.recordingId;
      state = { ...state, recordingId: null, error: message };
      if (id) fail(id, message);
      publish();
    },
  }) : { record: async () => {}, stop: () => {}, cancel: () => {} };

  const alive = (id: string, epoch: number, signal: AbortSignal) =>
    epoch === generation && !signal.aborted && get(id)?.status !== "discarded" && Boolean(get(id));

  async function process(id: string) {
    const epoch = generation;
    const controller = new AbortController();
    controllers.set(id, controller);
    const signal = controller.signal;
    processing += 1;
    try {
      let job = get(id)!;
      if (job.inputText === undefined) {
        if (!audioEnabled) throw new Error("Audio capture is disabled. Type a finding instead.");
        if (!job.audio || !job.language) throw new Error("No usable recording or language. Record again or type a finding.");
        update(id, { status: "transcribing" });
        const transcript = await transcribe(job.audio, job.language, signal);
        if (!alive(id, epoch, signal)) return;
        if (!transcript.transcript.trim()) throw new Error("No usable speech was transcribed. Please record again.");
        update(id, { transcript, inputText: transcript.transcript });
        job = get(id)!;
        record(job, { status: "transcribed", pending: true, source: { ...job.trace.source,
          raw_asr_transcript: transcript.transcript, submitted_text: transcript.transcript,
          asr_provider: transcript.provider, asr_model: transcript.model } });
      }
      job = get(id)!;
      update(id, { status: "extracting" });
      // Keep the original question and state even if another job has been accepted.
      const candidate = await extract(job.assessment, job.inputText!, job.originalEncounter, job.question?.field, signal);
      if (!alive(id, epoch, signal)) return;
      if (candidate.assessment !== job.assessment) throw new Error("The service returned the wrong assessment. Retry this capture.");
      update(id, { originalCandidate: candidate, candidate, status: "captured", error: undefined });
      record(get(id)!, { status: "candidate", pending: true, candidate, error: undefined });
    } catch (error) {
      if (alive(id, epoch, signal)) fail(id, error instanceof Error ? error.message : "Capture processing failed. Retry or record again.");
    } finally {
      if (epoch === generation) {
        controllers.delete(id);
        processing -= 1;
        pump();
      }
    }
  }

  function pump() {
    // Bound remote work without blocking the microphone, navigation, or review.
    while (processing < 2) {
      const queued = state.jobs.find((job) => job.status === "queued");
      if (!queued) return;
      void process(queued.id);
    }
  }

  function newJob(assessment: CaptureScope, context?: CaptureContext): CaptureJob | undefined {
    const snapshot = getSession().snapshot();
    if (!snapshot.evaluation || (assessment !== "full-note" && !assessmentIds.includes(assessment))) {
      state = { ...state, error: "The encounter must be evaluated before starting a new capture." }; publish(); return;
    }
    const progress = assessment === "full-note" ? undefined : snapshot.evaluation.assessments[assessment];
    const question = assessment === "full-note" ? undefined : context ? context.question
      : progress?.decision === "ASK" && progress.question ? progress.question : undefined;
    const encounter = structuredClone(context?.encounter ?? snapshot.encounter);
    const revision = context?.revision ?? snapshot.revision;
    const id = crypto.randomUUID();
    return { id, assessment, status: "queued", originalEncounter: encounter, originalRevision: revision,
      question: question ? { ...question } : undefined, reviewVersion: 0, changedFields: [], trace: { id, timestamp: new Date().toISOString(), assessment,
        status: "candidate", pending: true, source: { question: question ? { ...question } : undefined }, before_encounter: encounter,
        capture_context: { encounter, revision } } };
  }

  function add(job: CaptureJob) {
    state = { ...state, jobs: [...state.jobs, job], error: "" };
    getSession().recordInteraction(job.trace);
    publish();
  }

  function discard(id: string) {
    const job = get(id);
    if (!job || ["accepted", "applying", "discarded"].includes(job.status)) return;
    controllers.get(id)?.abort();
    if (state.recordingId === id) {
      state = { ...state, recordingId: null };
      microphone.cancel();
    }
    update(id, { status: "discarded", audio: undefined });
    // Preserve a failure receipt instead of overwriting it when retrying/discarding.
    if (job.status !== "failed" && job.trace.status !== "failed") record(get(id)!, { status: "rejected", pending: false, error: "Capture discarded; accepted findings unchanged." });
    pump();
  }

  const clear = (notify = true) => {
    silent = !notify;
    generation += 1;
    for (const controller of controllers.values()) controller.abort();
    controllers.clear();
    processing = 0;
    state = initialState();
    microphone.cancel();
    if (notify) publish();
    silent = false;
  };

  return {
    clear,
    startRecording(assessment: AssessmentId, language: ASRLanguage, consent: { audio: boolean; understanding: boolean }, context?: CaptureContext) {
      if (!audioEnabled) return;
      if (!assessmentIds.includes(assessment)) return;
      if (state.recordingId || state.audioState !== "idle") return;
      if (!consent.audio || !consent.understanding || !["en", "pcm", "yo", "ig", "ha"].includes(language)) {
        state = { ...state, error: "Select a language and consent to both transcription and structuring before recording." }; publish(); return;
      }
      const job = newJob(assessment, context);
      if (!job) return;
      job.status = "recording"; job.language = language;
      job.trace.source = { ...job.trace.source, recording_id: job.id, language };
      state = { ...state, recordingId: job.id };
      add(job);
      void microphone.record();
    },
    stop: microphone.stop,
    cancelRecording() { if (state.recordingId) discard(state.recordingId); },
    addText(assessment: CaptureScope, text: string, consent: boolean, context?: CaptureContext) {
      if (!consent || !text.trim()) return false;
      const job = newJob(assessment, context);
      if (!job) return false;
      job.inputText = text.trim(); job.trace.source.submitted_text = job.inputText;
      add(job); pump();
      return true;
    },
    async prepareReview(id: string) {
      const job = get(id);
      if (!job?.originalCandidate || !["captured", "review"].includes(job.status)
        || Object.values(job.workerEdits ?? {}).some((edit) => edit.error)) return;
      const snapshot = getSession().snapshot();
      if (!snapshot.evaluation) return;
      const epoch = generation;
      const editVersion = job.editVersion ?? 0;
      const controller = new AbortController();
      controllers.set(id, controller);
      update(id, { status: "preparing_review", error: undefined });
      try {
        const review = await prepare(job.assessment, snapshot.encounter, effectiveChanges(job), controller.signal);
        if (!alive(id, epoch, controller.signal)) return;
        if ((get(id)?.editVersion ?? 0) !== editVersion) return;
        if (snapshot.revision !== getSession().currentRevision()) {
          update(id, { status: "captured", error: "Accepted evidence changed during review preparation. Review this capture again." }); return;
        }
        update(id, { status: "review", reviewRevision: snapshot.revision, reviewVersion: job.reviewVersion + 1,
          reviewEditVersion: editVersion,
          changedFields: review.changed_fields, candidate: { ...job.originalCandidate, changes: review.changes } });
        return get(id);
      } catch (error) {
        if (alive(id, epoch, controller.signal)) update(id, { status: "captured", error: error instanceof Error ? error.message : "Review could not be prepared. Try again." });
      } finally {
        if (controllers.get(id) === controller) controllers.delete(id);
      }
    },
    async accept(id: string, resolutions: Resolutions, expected?: { revision: number; editVersion: number; pendingEvidence?: string }) {
      const job = get(id);
      if (!job?.candidate || job.status !== "review") return;
      const session = getSession();
      if (state.jobs.some((pending) => pending.assessment === "full-note" && ["queued", "extracting"].includes(pending.status))) {
        update(id, { error: "A full report is still being interpreted. Review its findings before confirming." }); return;
      }
      if (expected && (expected.revision !== session.currentRevision() || expected.editVersion !== (job.editVersion ?? 0))) {
        update(id, { error: "The working answers changed. Review them and confirm again." }); return;
      }
      if (expected?.pendingEvidence !== undefined && expected.pendingEvidence !== pendingEvidenceVersion(
        state.jobs, job.candidate.changes.map((row) => row.field), session.snapshot().encounter,
      )) {
        update(id, { error: "Another recording changed the pending evidence. Review the answers and confirm again." }); return;
      }
      if (job.reviewRevision !== session.currentRevision() || (job.reviewEditVersion ?? 0) !== (job.editVersion ?? 0)
        || Object.values(job.workerEdits ?? {}).some((edit) => edit.error)
        || unresolvedChanges(job.candidate.changes, resolutions).length) {
        update(id, { error: "Review against the latest encounter and resolve all choices before applying." }); return;
      }
      if (session.busy) { update(id, { error: "Another reviewed update is being applied. Try again shortly." }); return; }
      const epoch = generation;
      const before = session.snapshot().encounter;
      const attempt = job.trace.status === "failed"
        ? { ...job.trace, id: crypto.randomUUID(), timestamp: new Date().toISOString(), status: "candidate" as const, pending: true, error: undefined }
        : job.trace;
      update(id, { status: "applying", error: undefined });
      const accepted = await session.accept(job.candidate, resolutions, job.reviewRevision, {
        ...attempt, original_candidate: job.originalCandidate, worker_edits: job.workerEdits,
      });
      if (epoch !== generation || !get(id)) return;
      const receipt = session.snapshot().interactions?.find((entry) => entry.id === attempt.id);
      if (accepted) {
        const after = getSession().snapshot().encounter;
        const value = (encounter: Record<string, unknown>, field: string) => field.split(".").reduce<unknown>((node, part) =>
          node && typeof node === "object" ? (node as Record<string, unknown>)[part] : null, encounter) ?? null;
        update(id, { status: "accepted", trace: receipt ?? { ...attempt, status: "accepted", pending: false }, audio: undefined, changedFields: job.candidate.changes.filter((change) =>
          value(before, change.field) !== value(after, change.field)).map((change) => change.field) });
      } else update(id, { status: "review", trace: receipt ?? { ...attempt, status: "failed", pending: false },
        error: "Findings were not applied. Review the encounter message, then retry or record a correction." });
    },
    retry(id: string, correctedText?: string) {
      const job = get(id);
      if (!job || !["captured", "review", "failed"].includes(job.status)) return;
      if (correctedText !== undefined && !correctedText.trim()) return;
      const nextId = crypto.randomUUID();
      const inputText = correctedText?.trim() ?? job.inputText;
      const next: CaptureJob = { ...job, id: nextId, status: "queued", inputText, originalCandidate: undefined,
        candidate: undefined, workerEdits: undefined, editVersion: 0, reviewEditVersion: undefined,
        reviewRevision: undefined, reviewVersion: 0, changedFields: [], error: undefined,
        trace: { id: nextId, timestamp: new Date().toISOString(), assessment: job.assessment, status: "candidate", pending: true,
          capture_context: job.trace.capture_context, before_encounter: job.originalEncounter,
          source: { ...job.trace.source, submitted_text: inputText } } };
      discard(id); add(next); pump();
    },
    discard,
    stageField(assessment: CaptureScope, descriptor: FieldDescriptor, input: ClinicalValue, jobId?: string, keep = false): string | undefined {
      let job = jobId ? get(jobId) : undefined;
      // A stale control must not recreate a discarded/reset job or split a report correction.
      if (jobId && (!job?.originalCandidate || !["captured", "review", "preparing_review"].includes(job.status))) return;
      if (!job?.originalCandidate || !["captured", "review", "preparing_review"].includes(job.status)) {
        if (assessment === "full-note" || !descriptor.assessments.includes(assessment)) return;
        const snapshot = getSession().snapshot();
        job = newJob(assessment, { ...snapshot, question: undefined });
        if (!job) return;
        job.status = "captured";
        job.originalCandidate = { assessment, input_text: "Worker-entered structured observations", extraction_mode: "worker-review", changes: [], warnings: [] };
        job.candidate = job.originalCandidate;
        job.trace.source = { submitted_text: job.originalCandidate.input_text };
        add(job);
      }
      controllers.get(job.id)?.abort();
      const session = getSession();
      const snapshot = session.snapshot();
      const edit: WorkerEdit = { ...parseClinicalInput(descriptor, input), label: descriptor.label,
        previous: job.workerEdits?.[descriptor.path] ? job.workerEdits[descriptor.path].previous : clinicalValue(snapshot.encounter, descriptor.path), revision: snapshot.revision, keep };
      // Named intake requires a supported age; legacy clinical observations remain nullable.
      if (descriptor.path === "patient_facts.age_months" && normalizePatientName(session.patientName)
        && (typeof edit.value !== "number" || !Number.isInteger(edit.value) || edit.value < 2 || edit.value > 59)) {
        edit.value = undefined;
        edit.error = "Enter age in completed months from 2 to 59.";
      }
      const next = { ...job, workerEdits: { ...job.workerEdits, [descriptor.path]: edit }, editVersion: (job.editVersion ?? 0) + 1 };
      const candidate = { ...job.originalCandidate!, changes: effectiveChanges(next) };
      update(job.id, { workerEdits: next.workerEdits, editVersion: next.editVersion, status: "captured", candidate, error: undefined });
      record(get(job.id)!, { status: "candidate", pending: true, original_candidate: job.originalCandidate,
        candidate, worker_edits: next.workerEdits, error: undefined });
      return job.id;
    },
    retract(assessment: AssessmentId, fields: string[]) {
      const job = newJob(assessment);
      if (!job) return;
      const changes = acceptedSectionFields(job.originalEncounter, assessment).filter((change) => fields.includes(change.field));
      if (!changes.length) return;
      const candidate = workerRetraction(assessment, changes);
      job.status = "captured"; job.inputText = candidate.input_text; job.question = undefined;
      job.originalCandidate = candidate; job.candidate = candidate;
      job.trace.source = { submitted_text: candidate.input_text }; job.trace.candidate = candidate;
      add(job);
    },
  };
}

export function useVoiceCapture(session: Session, audioEnabled = true) {
  const latest = useRef(session);
  latest.current = session;
  const [state, setState] = useState(initialState);
  const [capture] = useState(() => createVoiceCapture({ getSession: () => latest.current, onChange: setState, audioEnabled }));
  useEffect(() => () => capture.clear(false), [capture]);
  const pending = state.jobs.some((job) => job.status !== "accepted" && job.status !== "discarded");
  useEffect(() => {
    if (!pending) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [pending]);
  return { ...state, ...capture, clear: () => capture.clear() };
}
