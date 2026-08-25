import { startTransition, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  CornerDownLeft,
  FileText,
  LoaderCircle,
  LockKeyhole,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import { AssessmentChecklist } from "./components/AssessmentChecklist";
import { ResultPanel } from "./components/ResultPanel";
import { evaluatePreview, extractFindings, fetchExamples } from "./lib/api";
import type { AnalysisResult, ExampleCase, ExtractionPreview } from "./types";

type WorkflowState = "idle" | "extracting" | "review" | "evaluating" | "complete";
type ActivePanel = "checklist" | "findings" | "result";

function EmptyResult() {
  return (
    <section className="compact-empty-result">
      <ClipboardCheck aria-hidden="true" size={27} />
      <h2>Result pending</h2>
      <p>Enter the completed assessment, then review the structured interpretation.</p>
      <div className="empty-steps">
        <span><strong>1</strong> Interpret findings</span>
        <span><strong>2</strong> Verify checklist</span>
        <span><strong>3</strong> Run decision engine</span>
      </div>
    </section>
  );
}

function ProcessingState({ stage }: { stage: "extracting" | "evaluating" }) {
  return (
    <section className="processing-state" aria-live="polite" aria-busy="true">
      <LoaderCircle className="loading-spinner" aria-hidden="true" size={27} />
      <h2>{stage === "extracting" ? "Interpreting findings" : "Applying deterministic rules"}</h2>
      <p>
        {stage === "extracting"
          ? "Converting the submitted account into explicit assessment states."
          : "Checking completeness, classifications, urgency, and management."}
      </p>
    </section>
  );
}

function VerificationGate({ onConfirm }: { onConfirm: () => void }) {
  return (
    <section className="verification-gate" aria-live="polite">
      <div className="verification-icon"><ClipboardCheck aria-hidden="true" size={24} /></div>
      <p className="panel-index">Worker verification required</p>
      <h2>Check the interpreted assessment</h2>
      <p>
        Review the checklist on the left. Confirm that present, absent, and unknown findings
        match what was observed before running the decision engine.
      </p>
      <button type="button" onClick={onConfirm}>
        <CheckCircle2 aria-hidden="true" size={18} />
        Interpretation is correct
        <ArrowRight aria-hidden="true" size={18} />
      </button>
      <small>If anything is wrong, revise the findings and interpret them again.</small>
    </section>
  );
}

export default function App() {
  const [examples, setExamples] = useState<ExampleCase[]>([]);
  const [findings, setFindings] = useState("");
  const [preview, setPreview] = useState<ExtractionPreview | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [workflowState, setWorkflowState] = useState<WorkflowState>("idle");
  const [activePanel, setActivePanel] = useState<ActivePanel>("findings");
  const [fieldError, setFieldError] = useState("");
  const [serviceError, setServiceError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchExamples(controller.signal)
      .then(setExamples)
      .catch((error: unknown) => {
        if (error instanceof Error && error.name !== "AbortError") setServiceError(error.message);
      });
    return () => controller.abort();
  }, []);

  function invalidateInterpretation(nextFindings: string) {
    setFindings(nextFindings);
    setPreview(null);
    setResult(null);
    setWorkflowState("idle");
    if (fieldError) setFieldError("");
  }

  async function interpretAssessment() {
    if (!findings.trim()) {
      setFieldError("Enter the assessment findings before continuing.");
      textareaRef.current?.focus();
      return;
    }

    setFieldError("");
    setServiceError("");
    setWorkflowState("extracting");
    setActivePanel("result");
    try {
      const extraction = await extractFindings(findings);
      if (extraction.error) {
        setServiceError(extraction.error);
        setWorkflowState("idle");
        setActivePanel("findings");
        return;
      }
      startTransition(() => {
        setPreview(extraction);
        setResult(null);
        setWorkflowState("review");
        setActivePanel("checklist");
      });
    } catch (error) {
      setServiceError(error instanceof Error ? error.message : "The service could not be reached.");
      setWorkflowState("idle");
      setActivePanel("findings");
    }
  }

  async function confirmAndEvaluate() {
    if (!preview) return;
    setServiceError("");
    setWorkflowState("evaluating");
    setActivePanel("result");
    try {
      const analysis = await evaluatePreview(preview);
      startTransition(() => {
        setResult(analysis);
        setWorkflowState("complete");
      });
    } catch (error) {
      setServiceError(error instanceof Error ? error.message : "The service could not be reached.");
      setWorkflowState("review");
    }
  }

  function loadExample(exampleId: string) {
    const example = examples.find((item) => item.id === exampleId);
    if (!example) return;
    invalidateInterpretation(example.text);
    setServiceError("");
    textareaRef.current?.focus();
  }

  function clearAssessment() {
    invalidateInterpretation("");
    setServiceError("");
    setActivePanel("findings");
    textareaRef.current?.focus();
  }

  const encounter = result?.structured_encounter ?? preview?.structured_encounter;
  const reviewState = workflowState === "complete" ? "verified" : preview ? "review" : "empty";

  return (
    <div className="app-frame">
      <header className="site-header">
        <a className="brand" href="/" aria-label="EdgeIMCI home">
          <span className="brand-symbol">
            <img src="/edge-imci-mark.svg" alt="" aria-hidden="true" />
          </span>
          <span>Edge<strong>IMCI</strong></span>
        </a>
        <div className="header-context">
          <span>Initial sick-child assessment</span>
          <span>Ages 2–59 months</span>
        </div>
        <div className="header-trust"><LockKeyhole aria-hidden="true" size={14} /> Research prototype</div>
      </header>

      <nav className="mobile-panel-nav" aria-label="Application panels">
        {(["checklist", "findings", "result"] as ActivePanel[]).map((panel) => (
          <button
            className={activePanel === panel ? "active" : ""}
            type="button"
            key={panel}
            onClick={() => setActivePanel(panel)}
          >
            {panel === "checklist" ? "Guide" : panel === "findings" ? "Findings" : "Result"}
            {panel === "checklist" && preview && <span />}
            {panel === "result" && result?.is_urgent && <span className="urgent-dot" />}
          </button>
        ))}
      </nav>

      <main className="clinical-workspace" data-active-panel={activePanel}>
        <AssessmentChecklist encounter={encounter} result={result} />

        <section className="findings-panel" aria-labelledby="findings-title">
          <header className="pane-header">
            <div>
              <p className="panel-index">Encounter findings</p>
              <h1 id="findings-title">Describe the completed assessment</h1>
            </div>
            {findings && (
              <button className="text-button" type="button" onClick={clearAssessment}>
                <RotateCcw aria-hidden="true" size={14} /> Clear
              </button>
            )}
          </header>

          <p className="field-help" id="findings-help">
            Include age, all danger signs, and the cough/breathing, diarrhoea, fever, and ear
            assessment findings. Omitted findings remain unknown.
          </p>

          <div className={`textarea-shell ${fieldError ? "has-error" : ""}`}>
            <textarea
              ref={textareaRef}
              value={findings}
              onChange={(event) => invalidateInterpretation(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                  event.preventDefault();
                  void interpretAssessment();
                }
              }}
              aria-describedby={`findings-help${fieldError ? " findings-error" : ""}`}
              aria-invalid={Boolean(fieldError)}
              placeholder="Enter the worker’s complete assessment findings…"
            />
            <div className="textarea-meta">
              <span>{findings.length.toLocaleString()} characters</span>
              <span><CornerDownLeft aria-hidden="true" size={13} /> {navigator.platform.includes("Mac") ? "⌘" : "Ctrl"} Enter</span>
            </div>
          </div>

          {fieldError && <p className="field-error" id="findings-error">{fieldError}</p>}
          {serviceError && <p className="service-error" role="alert">{serviceError}</p>}

          <button
            className="analyze-button"
            type="button"
            disabled={workflowState === "extracting" || workflowState === "evaluating"}
            onClick={() => void interpretAssessment()}
          >
            {workflowState === "extracting" ? (
              <><LoaderCircle className="button-spinner" aria-hidden="true" size={18} /> Interpreting findings</>
            ) : (
              <><FileText aria-hidden="true" size={18} /> Interpret findings <ArrowRight aria-hidden="true" size={18} /></>
            )}
          </button>

          {preview && workflowState === "review" && (
            <div className="review-status">
              <ShieldCheck aria-hidden="true" size={18} />
              <div><strong>Interpretation ready</strong><span>Review the checklist before evaluation.</span></div>
            </div>
          )}

          <div className="example-picker">
            <label htmlFor="example-case">Demonstration input</label>
            <select id="example-case" defaultValue="" onChange={(event) => loadExample(event.target.value)}>
              <option value="" disabled>Load a demonstration input…</option>
              {examples.map((example) => <option value={example.id} key={example.id}>{example.label}</option>)}
            </select>
            <small>Use a prepared input for a repeatable demonstration, or enter new findings.</small>
          </div>

          <footer className="findings-footer">
            <LockKeyhole aria-hidden="true" size={14} />
            <span>
              <strong>AI model limitation:</strong> The AI does not classify illness or prescribe
              treatment. It only structures the documented findings. After worker verification,
              the deterministic engine uses those findings to produce classifications and
              management guidance.
            </span>
          </footer>
        </section>

        <section className="output-panel" aria-label="Clinical result">
          <header className="pane-header result-pane-header">
            <div>
              <p className="panel-index">Clinical result</p>
              <h1>Classification and management</h1>
            </div>
            <span className="deterministic-label"><ShieldCheck aria-hidden="true" size={14} /> Deterministic</span>
          </header>

          <div className="result-scroll">
            {workflowState === "idle" && <EmptyResult />}
            {workflowState === "extracting" && <ProcessingState stage="extracting" />}
            {workflowState === "review" && <VerificationGate onConfirm={() => void confirmAndEvaluate()} />}
            {workflowState === "evaluating" && <ProcessingState stage="evaluating" />}
            {workflowState === "complete" && result && <ResultPanel result={result} />}
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <p><strong>Research prototype.</strong> Not a production medical device or authorization for autonomous clinical use.</p>
        <p>Unchecked findings remain unknown; they are never inferred absent.</p>
      </footer>
    </div>
  );
}
