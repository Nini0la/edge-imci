import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleX,
  GitBranch,
  ListChecks,
  ShieldAlert,
} from "lucide-react";
import type { AnalysisResult, AnalysisState } from "../types";
import { ResponseContent } from "./ResponseContent";

const stateContent: Record<
  AnalysisState,
  { eyebrow: string; title: string; note: string; icon: typeof CheckCircle2 }
> = {
  COMPLETE: {
    eyebrow: "Assessment complete",
    title: "Clinical synthesis ready",
    note: "All required findings for the supported encounter are present.",
    icon: CheckCircle2,
  },
  URGENT_COMPLETE: {
    eyebrow: "Urgent complete assessment",
    title: "Act now",
    note: "Immediate management takes priority. Do not delay referral.",
    icon: AlertTriangle,
  },
  INCOMPLETE: {
    eyebrow: "Assessment incomplete",
    title: "More findings are needed",
    note: "Final classifications are withheld until the required checks are supplied.",
    icon: ListChecks,
  },
  URGENT_INCOMPLETE: {
    eyebrow: "Urgent finding identified",
    title: "Act now, then complete rapidly",
    note: "Begin immediate management without waiting for the remaining assessment.",
    icon: ShieldAlert,
  },
  OUT_OF_SCOPE: {
    eyebrow: "Outside supported scope",
    title: "Use the applicable pathway",
    note: "This prototype supports children aged 2 to under 60 months.",
    icon: CircleX,
  },
  ERROR: {
    eyebrow: "Analysis not completed",
    title: "Review the submitted findings",
    note: "The prototype could not interpret this assessment.",
    icon: AlertCircle,
  },
};

interface ResultPanelProps {
  result: AnalysisResult;
}

export function ResultPanel({ result }: ResultPanelProps) {
  const content = stateContent[result.state];
  const StateIcon = content.icon;

  return (
    <article className={`result-panel state-${result.state.toLowerCase()}`} aria-live="polite">
      <header className="result-state-header">
        <div className="result-state-icon">
          <StateIcon aria-hidden="true" size={26} strokeWidth={2} />
        </div>
        <div>
          <p className="result-eyebrow">{content.eyebrow}</p>
          <h2>{content.title}</h2>
          <p>{content.note}</p>
        </div>
      </header>

      {result.error ? (
        <div className="error-message" role="alert">
          {result.error}
        </div>
      ) : (
        <section className="worker-response" aria-labelledby="worker-response-title">
          <div className="section-kicker">
            <Activity aria-hidden="true" size={17} />
            <h2 id="worker-response-title">Worker response</h2>
          </div>
          <ResponseContent response={result.rendered_response} />
        </section>
      )}

      {result.decision_trace.length > 0 && (
        <details className="evidence-section">
          <summary>
            <span className="summary-title">
              <GitBranch aria-hidden="true" size={19} />
              Why EdgeIMCI reached this result
            </span>
            <span className="summary-meta">Deterministic evidence</span>
            <ChevronDown className="summary-chevron" aria-hidden="true" size={19} />
          </summary>
          <div className="trace-list">
            {result.decision_trace.map((trace) => (
              <article className="trace-card" key={`${trace.rule_id}-${trace.classification}`}>
                <div className="trace-heading">
                  <div>
                    <span>{trace.pathway}</span>
                    <h3>{trace.classification}</h3>
                  </div>
                  <code>{trace.rule_id}</code>
                </div>
                {trace.findings.length > 0 && (
                  <dl className="trace-findings">
                    {trace.findings.map(([label, value]) => (
                      <div key={`${trace.rule_id}-${label}`}>
                        <dt>{label}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                )}
                <p>{trace.rule_description}</p>
              </article>
            ))}
          </div>
        </details>
      )}

      {result.pipeline_trace.length > 0 && (
        <details className="evidence-section technical-section">
          <summary>
            <span className="summary-title">
              <ListChecks aria-hidden="true" size={19} />
              Processing trace
            </span>
            <span className="summary-meta">Technical view</span>
            <ChevronDown className="summary-chevron" aria-hidden="true" size={19} />
          </summary>
          <ol className="pipeline-list">
            {result.pipeline_trace.map((step, index) => (
              <li key={`${step.label}-${index}`}>
                <span className={`pipeline-index kind-${step.kind.toLowerCase()}`}>{index + 1}</span>
                <div>
                  <span className="pipeline-kind">{step.kind}</span>
                  <h3>{step.label}</h3>
                  <p>{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
          <footer className="technical-meta">
            <span>Mode: {result.extraction_mode}</span>
            {result.matched_case_id && <span>Fixture: {result.matched_case_id}</span>}
          </footer>
        </details>
      )}
    </article>
  );
}
