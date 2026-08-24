export type AnalysisState =
  | "COMPLETE"
  | "URGENT_COMPLETE"
  | "INCOMPLETE"
  | "URGENT_INCOMPLETE"
  | "OUT_OF_SCOPE"
  | "ERROR";

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
