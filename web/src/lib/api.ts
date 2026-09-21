import type {
  AnalysisResult, ASRLanguage, AssessmentCandidate, AssessmentChange, AssessmentEvaluation, AssessmentId,
  CaptureScope, ClinicalSchema, ExampleCase, ExtractionPreview, Resolutions, Transcription,
} from "../types";
import { maxAudioBytes } from "./audio";

async function readJson<T>(response: Response): Promise<T> {
  let payload: T & { error?: string };
  try {
    payload = await response.json();
  } catch {
    throw new Error("The service returned an unreadable response. Please try again.");
  }
  if (!response.ok || payload.error) {
    throw new Error(payload.error ?? "The EdgeIMCI service could not complete the request.");
  }
  return payload;
}

export async function fetchExamples(signal?: AbortSignal): Promise<ExampleCase[]> {
  const response = await fetch("/api/examples", { signal });
  const payload = await readJson<{ examples: ExampleCase[] }>(response);
  return payload.examples;
}

export async function fetchClinicalSchema(signal?: AbortSignal): Promise<ClinicalSchema> {
  return readJson<ClinicalSchema>(await fetch("/api/assessment/schema", { signal }));
}

export async function analyzeFindings(findings: string): Promise<AnalysisResult> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ findings }),
  });
  return readJson<AnalysisResult>(response);
}

export function extractFindings(findings: string, signal?: AbortSignal): Promise<ExtractionPreview> {
  return postJson("/api/extract", { findings }, signal);
}

export function evaluatePreview(preview: ExtractionPreview, signal?: AbortSignal): Promise<AnalysisResult> {
  return postJson("/api/evaluate", preview, signal);
}

async function post<T>(path: string, body: BodyInit, contentType: string, signal?: AbortSignal, timeout = 60_000, headers: Record<string, string> = {}): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  if (signal?.aborted) controller.abort();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
  try {
    return await readJson<T>(await fetch(path, {
      method: "POST", headers: { "Content-Type": contentType, ...headers }, body, signal: controller.signal,
    }));
  } catch (error) {
    if (timedOut) throw new Error("The request timed out. Accepted findings are unchanged; please retry.");
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}

function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return post(path, JSON.stringify(body), "application/json", signal);
}

export function evaluateAssessment(encounter?: Record<string, unknown>, attempted: AssessmentId[] = [], signal?: AbortSignal): Promise<AssessmentEvaluation> {
  return postJson("/api/assessment/evaluate", { encounter, attempted }, signal);
}

export function extractAssessment(assessment: CaptureScope, findings: string, encounter: Record<string, unknown>, question_field?: string, signal?: AbortSignal): Promise<AssessmentCandidate> {
  return postJson("/api/assessment/extract", { assessment, findings, encounter, question_field: assessment === "full-note" ? undefined : question_field }, signal);
}

export function acceptAssessment(candidate: AssessmentCandidate, encounter: Record<string, unknown>, resolutions: Resolutions, attempted: AssessmentId[], signal?: AbortSignal): Promise<AssessmentEvaluation> {
  return postJson("/api/assessment/accept", {
    assessment: candidate.assessment, encounter, changes: candidate.changes,
    resolutions, confirmed: true, attempted,
  }, signal);
}

export function prepareAssessmentReview(assessment: CaptureScope, encounter: Record<string, unknown>, changes: AssessmentChange[], signal?: AbortSignal): Promise<{ changes: AssessmentChange[]; changed_fields: string[] }> {
  return postJson("/api/assessment/review", { assessment, encounter, changes }, signal);
}

export function transcribeAudio(audio: Blob, language: ASRLanguage, signal?: AbortSignal): Promise<Transcription> {
  if (!audio.size || audio.size > maxAudioBytes) return Promise.reject(new Error("Audio must be between 1 byte and 5 MB. Record a shorter report."));
  if (!["en", "pcm", "yo", "ig", "ha"].includes(language)) return Promise.reject(new Error("Select a language for this recording."));
  return post("/api/transcribe", audio, audio.type, signal, 110_000, { "X-EdgeIMCI-ASR-Language": language });
}
