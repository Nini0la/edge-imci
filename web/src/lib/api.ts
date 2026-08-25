import type { AnalysisResult, ExampleCase, ExtractionPreview } from "../types";

async function readJson<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & { error?: string };
  if (!response.ok) {
    throw new Error(payload.error ?? "The EdgeIMCI service could not complete the request.");
  }
  return payload;
}

export async function fetchExamples(signal?: AbortSignal): Promise<ExampleCase[]> {
  const response = await fetch("/api/examples", { signal });
  const payload = await readJson<{ examples: ExampleCase[] }>(response);
  return payload.examples;
}

export async function analyzeFindings(findings: string): Promise<AnalysisResult> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ findings }),
  });
  return readJson<AnalysisResult>(response);
}

export async function extractFindings(findings: string): Promise<ExtractionPreview> {
  const response = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ findings }),
  });
  return readJson<ExtractionPreview>(response);
}

export async function evaluatePreview(preview: ExtractionPreview): Promise<AnalysisResult> {
  const response = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preview),
  });
  return readJson<AnalysisResult>(response);
}
