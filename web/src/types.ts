export type AnalysisState =
  | "COMPLETE"
  | "URGENT_COMPLETE"
  | "INCOMPLETE"
  | "URGENT_INCOMPLETE"
  | "OUT_OF_SCOPE"
  | "ERROR";

export type AssessmentId = "danger" | "respiratory" | "diarrhoea" | "fever" | "ear";
export type ASRLanguage = "en" | "pcm" | "yo" | "ig" | "ha";

export interface AssessmentProgress {
  status: "NOT_STARTED" | "INCOMPLETE" | "COMPLETE" | "URGENT";
  decision: "ASK" | "COMPLETE" | "URGENT" | "BLOCK";
  missing_fields: string[];
  question: { field: string; text: string } | null;
  blockers: string[];
}

export interface AssessmentEvaluation {
  encounter: Record<string, unknown>;
  analysis: AnalysisResult;
  assessments: Record<AssessmentId, AssessmentProgress>;
}

export interface AssessmentChange {
  field: string;
  label: string;
  previous: unknown;
  value: unknown;
  conflict: boolean;
  outside_assessment: boolean;
  uncertain?: boolean;
}

export interface AssessmentCandidate {
  assessment: AssessmentId;
  input_text: string;
  extraction_mode: string;
  changes: AssessmentChange[];
  warnings: string[];
  candidate_encounter?: Record<string, unknown>;
  english_rendering?: string | null;
  uncertainties?: Array<{ field: string | null; source_text: string; reason: string }>;
  evidence_spans?: Array<{ field: string; source_text: string }>;
  understanding?: {
    provider: string;
    model: string | null;
    request_id: string | null;
    prompt_version: string;
    usage: Record<string, number>;
  };
}

export interface InteractionTrace {
  id: string;
  timestamp: string;
  assessment: AssessmentId | "full-note";
  status: "transcribed" | "candidate" | "accepted" | "rejected" | "failed";
  pending?: boolean;
  source: {
    recording_id?: string;
    asr_provider?: string;
    asr_model?: string | null;
    language?: ASRLanguage;
    raw_asr_transcript?: string;
    submitted_text?: string;
    question?: { field: string; text: string };
  };
  candidate?: AssessmentCandidate;
  native_preview?: ExtractionPreview;
  diagnostic_result?: AnalysisResult;
  resolutions?: Resolutions;
  before_encounter?: Record<string, unknown>;
  result?: AssessmentEvaluation;
  error?: string;
}

export type Resolution = "replace" | "keep" | "unknown";
export type Resolutions = Record<string, Resolution>;

export interface Transcription {
  transcript: string;
  provider: "intron";
  model: null;
  duration_seconds: number | null;
}

export interface ExampleCase {
  id: string;
  label: string;
  text: string;
}

export interface PipelineStep {
  label: string;
  kind: "LEARNED" | "DETERMINISTIC";
  detail: string;
}

export interface TraceEntry {
  classification: string;
  pathway: string;
  findings: [string, string][];
  rule_description: string;
  rule_id: string;
}

export interface ExtractionPreview {
  input_text: string;
  extraction_mode: string;
  matched_case_id: string | null;
  structured_encounter: Record<string, unknown>;
  structured_view: [string, string][];
  schema_valid: boolean;
  extraction_warnings: string[];
  pipeline_trace: PipelineStep[];
  error: string | null;
  outside_supported_scope: boolean;
  state: "READY_FOR_REVIEW" | "OUT_OF_SCOPE" | "ERROR";
}

export interface AnalysisResult {
  input_text: string;
  extraction_mode: string;
  matched_case_id: string | null;
  structured_encounter: Record<string, unknown>;
  structured_view: [string, string][];
  schema_valid: boolean;
  extraction_warnings: string[];
  is_complete: boolean;
  missing_elements: Record<string, string[]>;
  contradictions: string[];
  is_urgent: boolean;
  classifications: string[];
  urgent_actions: string[];
  final_actions: string[];
  deferred_actions: string[];
  rendered_response: string;
  decision_trace: TraceEntry[];
  pipeline_trace: PipelineStep[];
  error: string | null;
  outside_supported_scope: boolean;
  state: AnalysisState;
}
