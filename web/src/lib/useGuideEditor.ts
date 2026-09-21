import { useEffect, useRef, useState } from "react";
import type { CaptureScope, ClinicalSchema, ClinicalValue } from "../types";
import { fetchClinicalSchema } from "./api";
import { assessmentIds, unresolvedChanges } from "./assessment";
import { clinicalValue, effectiveChanges, guideResolutions, pendingEvidenceVersion } from "./guideEvidence";
import type { useAssessmentSession } from "./useAssessmentSession";
import type { CaptureJob, useVoiceCapture } from "./useVoiceCapture";

type Session = ReturnType<typeof useAssessmentSession>;
type Voice = ReturnType<typeof useVoiceCapture>;
const editable = (job: CaptureJob) => Boolean(job.originalCandidate)
  && ["captured", "review", "preparing_review", "applying"].includes(job.status);

/** A view of existing capture drafts, not another authoritative encounter. */
export function useGuideEditor(session: Session, voice: Voice) {
  const latest = useRef({ session, voice });
  latest.current = { session, voice };
  const [schema, setSchema] = useState<ClinicalSchema | null>(null);
  const [schemaError, setSchemaError] = useState("");
  const [schemaAttempt, setSchemaAttempt] = useState(0);
  const [selected, setSelected] = useState<Partial<Record<CaptureScope, string>>>({});
  const [owners, setOwners] = useState<Record<string, string>>({});
  const prepared = useRef(new Set<string>());
  useEffect(() => {
    const controller = new AbortController();
    setSchemaError("");
    fetchClinicalSchema(controller.signal).then((result) => {
      if (!controller.signal.aborted) setSchema(result);
    }).catch((error) => {
      if (!controller.signal.aborted) setSchemaError(error instanceof Error ? error.message : "Clinical controls could not be loaded.");
    });
    return () => controller.abort();
  }, [schemaAttempt]);

  function selectedJob(assessment: CaptureScope): CaptureJob | undefined {
    const jobs = voice.jobs.filter((job) => job.assessment === assessment && editable(job));
    return jobs.find((job) => job.id === selected[assessment]) ?? jobs[0];
  }
  const activeJobs = [...assessmentIds, "full-note" as const].map(selectedJob).filter((job): job is CaptureJob => Boolean(job));

  useEffect(() => {
    if (!schema || !session.ready) return;
    for (const job of activeJobs) {
      const key = `${job.id}:${session.revision}:${job.editVersion ?? 0}`;
      if (job.status === "captured" && !job.workerEdits && !prepared.current.has(key)) {
        prepared.current.add(key);
        // Preparation is local/deterministic and never accepts a suggestion.
        void voice.prepareReview(job.id);
      }
    }
  }, [schema, session.ready, session.revision, voice.jobs, selected]);

  function edit(assessment: CaptureScope, field: string, value: ClinicalValue, jobId?: string, keep = false) {
    const descriptor = schema?.fields[field];
    if (!descriptor) return;
    const id = voice.stageField(assessment, descriptor, value, jobId, keep);
    if (id) {
      const origin = voice.jobs.find((job) => job.id === id)?.assessment ?? assessment;
      setSelected((previous) => ({ ...previous, [origin]: id }));
      setOwners((previous) => ({ ...previous, [field]: id }));
    }
  }

  function field(assessment: CaptureScope, path: string) {
    const descriptor = schema?.fields[path];
    if (!descriptor) return null;
    const acceptedValue = clinicalValue(session.encounter, path);
    const allProposals = voice.jobs.filter(editable).flatMap((job) => {
      const rows = job.status === "review" && (job.reviewEditVersion ?? 0) === (job.editVersion ?? 0)
        ? job.candidate?.changes ?? [] : effectiveChanges(job);
      const row = rows.find((item) => item.field === path);
      return row ? [{ job, row }] : [];
    });
    const preferred = allProposals.find(({ job }) => job.id === owners[path]);
    const proposals = allProposals.filter(({ job }) => activeJobs.some((active) => active.id === job.id));
    const chosen = preferred ?? proposals[0] ?? allProposals[0];
    const worker = chosen?.job.workerEdits?.[path];
    const conflicting = !(preferred && preferred.job.workerEdits?.[path])
      && allProposals.some(({ job, row }) => (job.workerEdits?.[path]?.keep ? acceptedValue : row.value)
        !== (allProposals[0].job.workerEdits?.[path]?.keep ? acceptedValue : allProposals[0].row.value));
    const source = conflicting ? "conflict" : worker?.keep ? "kept" : worker ? "worker"
      : chosen ? chosen.job.inputText && !chosen.job.language ? "text" : "voice" : "accepted";
    const value = conflicting ? acceptedValue : worker?.keep ? acceptedValue : worker ? worker.value : chosen ? chosen.row.value as ClinicalValue : acceptedValue;
    const raw = worker?.keep ? undefined : worker?.raw;
    const resolutions = chosen ? guideResolutions(chosen.job) : {};
    const requiresChoice = conflicting || Boolean(chosen && unresolvedChanges([chosen.row], resolutions).length);
    const target = chosen?.job ?? selectedJob(assessment);
    return { descriptor, acceptedValue, value, raw, source, pending: Boolean(chosen), requiresChoice,
      error: worker?.error ?? (conflicting ? "Recordings disagree. Choose the observed answer; other recordings remain available for review." : undefined),
      disabled: !session.ready || target?.status === "applying", jobId: chosen?.job.id,
      onChange: (next: ClinicalValue) => edit(target?.assessment ?? (assessment === "full-note" ? descriptor.assessments[0] : assessment), path, next, target?.id),
      onKeep: chosen && acceptedValue !== null ? () => edit(chosen.job.assessment, path, acceptedValue, chosen.job.id, true) : undefined,
    } as const;
  }

  const pendingFieldPaths = [...new Set(voice.jobs.filter(editable).flatMap((job) => effectiveChanges(job).map((row) => row.field)))];
  // This sparse projection controls presentation only; it never reaches accept/evaluate.
  const workingEncounter = structuredClone(session.encounter);
  for (const path of pendingFieldPaths) {
    const view = field(schema?.fields[path]?.assessments[0] ?? "danger", path);
    if (!view || view.error || view.value === undefined || view.source === "conflict") continue;
    let node: Record<string, unknown> = workingEncounter;
    const parts = path.split(".");
    for (const part of parts.slice(0, -1)) {
      if (!node[part] || typeof node[part] !== "object") node[part] = {};
      node = node[part] as Record<string, unknown>;
    }
    node[parts[parts.length - 1]] = view.value;
  }

  return {
    schema, schemaError, workingEncounter, pendingFieldPaths, selectedJob, field,
    retrySchema: () => setSchemaAttempt((count) => count + 1),
    reset() { setSelected({}); setOwners({}); prepared.current.clear(); },
    selectJob(id: string) {
      const job = voice.jobs.find((item) => item.id === id && editable(item));
      if (!job) return;
      setSelected((previous) => ({ ...previous, [job.assessment]: id }));
      setOwners((previous) => ({ ...previous, ...Object.fromEntries(effectiveChanges(job).map((row) => [row.field, id])) }));
      if (job.status === "captured") void voice.prepareReview(id);
    },
    async confirm(assessment: CaptureScope) {
      const job = selectedJob(assessment);
      if (!schema || !session.ready || session.busy || !job || job.status === "applying" || job.status === "preparing_review"
        || Object.values(job.workerEdits ?? {}).some((item) => item.error)
        || voice.jobs.some((pending) => pending.assessment === "full-note" && ["queued", "extracting"].includes(pending.status))) return;
      const revision = session.currentRevision();
      const editVersion = job.editVersion ?? 0;
      const rows = job.status === "review" ? job.candidate?.changes ?? [] : effectiveChanges(job);
      const choices = guideResolutions(job);
      const evidenceVersion = pendingEvidenceVersion(voice.jobs, rows.map((row) => row.field), session.encounter);
      if (rows.some((row) => {
        const shown = field(assessment, row.field);
        const proposed = choices[row.field] === "keep" ? clinicalValue(session.encounter, row.field) : row.value;
        return shown?.source === "conflict" || (shown?.pending && shown.jobId !== job.id && shown.value !== proposed);
      })) return;
      const contextWasCurrent = (job.reviewRevision ?? job.originalRevision) === revision;
      let preparedJob: CaptureJob | undefined;
      if (job.status !== "review" || job.reviewRevision !== revision || (job.reviewEditVersion ?? 0) !== (job.editVersion ?? 0)) {
        preparedJob = await voice.prepareReview(job.id);
        if (!preparedJob) return;
      }
      const current = latest.current;
      if (current.voice.jobs.some((pending) => pending.assessment === "full-note" && ["queued", "extracting"].includes(pending.status))) return;
      const reviewed = preparedJob ?? current.voice.jobs.find((item) => item.id === job.id);
      if (!contextWasCurrent || !reviewed || reviewed.status !== "review" || (reviewed.editVersion ?? 0) !== editVersion
        || reviewed.reviewRevision !== revision || revision !== current.session.currentRevision()) return;
      if (evidenceVersion !== pendingEvidenceVersion(current.voice.jobs, rows.map((row) => row.field), current.session.snapshot().encounter)) return;
      const resolutions = guideResolutions(reviewed);
      if (unresolvedChanges(reviewed.candidate?.changes ?? [], resolutions).length) return;
      await current.voice.accept(reviewed.id, resolutions, { revision, editVersion, pendingEvidence: evidenceVersion });
    },
  };
}
