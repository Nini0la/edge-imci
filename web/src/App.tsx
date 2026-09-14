import { useEffect, useRef, useState } from "react";
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
import { AssessmentCapture } from "./components/AssessmentCapture";
import { ResultPanel } from "./components/ResultPanel";
import { ResponseContent } from "./components/ResponseContent";
import { InteractionHistory } from "./components/InteractionHistory";
import { evaluatePreview, extractFindings, fetchExamples } from "./lib/api";
import { assessmentIds, createRequestGate, pendingAssessmentIds } from "./lib/assessment";
import { useAssessmentSession } from "./lib/useAssessmentSession";
import type { AnalysisResult, AssessmentId, ExampleCase, ExtractionPreview, InteractionTrace } from "./types";

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

function VerificationGate({ onConfirm, disabled }: { onConfirm: () => void; disabled: boolean }) {
  return (
    <section className="verification-gate" aria-live="polite">
      <div className="verification-icon"><ClipboardCheck aria-hidden="true" size={24} /></div>
      <p className="panel-index">Worker verification required</p>
      <h2>Check the interpreted assessment</h2>
      <p>
        Review the checklist on the left. Confirm that present, absent, and unknown findings
        match what was observed before running the decision engine.
      </p>
      <p>This full-assessment interpretation replaces the accepted encounter when confirmed. Omitted findings become unknown. Use section capture for incremental updates.</p>
      <button type="button" onClick={onConfirm} disabled={disabled}>
        <CheckCircle2 aria-hidden="true" size={18} />
        Interpretation is correct
        <ArrowRight aria-hidden="true" size={18} />
      </button>
      <small>If anything is wrong, revise the findings and interpret them again.</small>
    </section>
  );
}

export function FullAssessmentReview({ preview, scopeResult, onConfirm, disabled }: {
  preview: ExtractionPreview; scopeResult: AnalysisResult | null; onConfirm: () => void; disabled: boolean;
}) {
  if (preview.outside_supported_scope) return <section className="scope-preview" role="alert">
    <h2>Outside supported scope</h2>
    <p>Use the applicable approved age-specific pathway. This full report cannot be accepted into the supported sick-child encounter.</p>
    {scopeResult?.outside_supported_scope && <ResponseContent response={scopeResult.rendered_response} />}
    <p>The accepted encounter and any urgent guidance are unchanged. Revise or explicitly discard this full note.</p>
  </section>;
  if (!preview.schema_valid || preview.error) return <p className="scope-preview" role="alert">{preview.error || "The full report is invalid. Revise the findings before confirming."}</p>;
  return <VerificationGate disabled={disabled} onConfirm={onConfirm} />;
}

export default function App() {
  const [examples, setExamples] = useState<ExampleCase[]>([]);
  const [findings, setFindings] = useState("");
  const [fullTextDirty, setFullTextDirty] = useState(false);
  const [preview, setPreview] = useState<ExtractionPreview | null>(null);
  const [scopeResult, setScopeResult] = useState<AnalysisResult | null>(null);
  const fullInteraction = useRef<InteractionTrace | undefined>(undefined);
  const session = useAssessmentSession();
  const result = session.evaluation?.analysis ?? null;
  const [activeAssessment, setActiveAssessment] = useState<AssessmentId | null>(null);
  const [captureBusy, setCaptureBusy] = useState(false);
  const [capturePending, setCapturePending] = useState<AssessmentId[]>([]);
  const [macroGate] = useState(createRequestGate);
  const [workflowState, setWorkflowState] = useState<WorkflowState>("idle");
  const [activePanel, setActivePanel] = useState<ActivePanel>("findings");
  const [fieldError, setFieldError] = useState("");
  const [serviceError, setServiceError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const macroBusy = workflowState === "extracting" || workflowState === "evaluating";
  const actionsBlocked = captureBusy || session.busy || macroBusy;
  const urgent = Boolean(result?.is_urgent || Object.values(session.evaluation?.assessments ?? {}).some((item) => item.status === "URGENT" || item.decision === "URGENT"));
  const progressBlocked = Object.values(session.evaluation?.assessments ?? {}).some((item) => item.decision === "BLOCK");

  useEffect(() => () => macroGate.cancel(), [macroGate]);

  useEffect(() => {
    const controller = new AbortController();
    fetchExamples(controller.signal)
      .then(setExamples)
      .catch((error: unknown) => {
        if (error instanceof Error && error.name !== "AbortError") setServiceError(error.message);
      });
    return () => controller.abort();
  }, []);

  function invalidateInterpretation() {
    const entry = fullInteraction.current;
    if (entry && entry.status === "candidate") session.recordInteraction({ ...entry, pending: false, status: "rejected", error: "Full note edited or discarded before acceptance." });
    fullInteraction.current = undefined;
    macroGate.cancel();
    setPreview(null);
    setScopeResult(null);
    setWorkflowState("idle");
    if (fieldError) setFieldError("");
  }

  function editFindings(nextFindings: string) {
    invalidateInterpretation();
    setFindings(nextFindings);
    setFullTextDirty(true);
  }

  function discardFullNote() {
    if (actionsBlocked) return;
    if ((fullTextDirty || preview) && !window.confirm("Discard this full note and its interpretation? Accepted findings and section evidence will remain unchanged.")) return;
    invalidateInterpretation();
    setFindings("");
    setFullTextDirty(false);
  }

  async function interpretAssessment() {
    if (actionsBlocked || !session.ready) return;
    if (!findings.trim()) {
      setFieldError("Enter the assessment findings before continuing.");
      textareaRef.current?.focus();
      return;
    }

    if (capturePending.length && !window.confirm("Discard unaccepted section findings and interpret the full assessment instead?")) return;
    session.rejectPending("Switched to full-note interpretation; prior capture not accepted.");
    setActiveAssessment(null);
    setCapturePending([]);
    setCaptureBusy(false);
    const request = macroGate.begin(session.currentRevision());
    const trace: InteractionTrace = { id: crypto.randomUUID(), timestamp: new Date().toISOString(), assessment: "full-note",
      status: "candidate", pending: true, source: { submitted_text: findings }, before_encounter: session.encounter };
    fullInteraction.current = trace;
    session.recordInteraction(trace);
    setFieldError("");
    setServiceError("");
    setPreview(null);
    setScopeResult(null);
    setWorkflowState("extracting");
    setActivePanel("result");
    try {
      const extraction = await extractFindings(findings, request.signal);
      if (!request.isCurrent(session.currentRevision())) return;
      if (extraction.error) {
        fullInteraction.current = { ...trace, pending: false, status: "failed", native_preview: extraction, error: extraction.error };
        session.recordInteraction(fullInteraction.current);
        setServiceError(extraction.error);
        setWorkflowState("idle");
        setActivePanel("findings");
        return;
      }
      setPreview(extraction);
      fullInteraction.current = { ...trace, pending: false, native_preview: extraction };
      session.recordInteraction(fullInteraction.current);
      if (extraction.outside_supported_scope) {
        setWorkflowState("evaluating");
        const outsideResult = await evaluatePreview(extraction, request.signal);
        if (!request.isCurrent(session.currentRevision())) return;
        setScopeResult(outsideResult);
        fullInteraction.current = { ...fullInteraction.current, diagnostic_result: outsideResult };
        session.recordInteraction(fullInteraction.current);
      }
      setWorkflowState("review");
      setActivePanel("checklist");
    } catch (error) {
      if (!request.isCurrent(session.currentRevision())) return;
      setServiceError(error instanceof Error ? error.message : "The service could not be reached.");
      fullInteraction.current = { ...fullInteraction.current!, pending: false, status: "failed", error: error instanceof Error ? error.message : "The service could not be reached." };
      session.recordInteraction(fullInteraction.current);
      setWorkflowState("idle");
      setActivePanel("findings");
    }
  }

  async function confirmAndEvaluate() {
    if (!preview || preview.outside_supported_scope || !preview.schema_valid || preview.error || actionsBlocked || !session.ready) return;
    const request = macroGate.begin(session.currentRevision());
    setServiceError("");
    setWorkflowState("evaluating");
    setActivePanel("result");
    const trace: InteractionTrace = { ...fullInteraction.current,
      id: fullInteraction.current?.status === "failed" ? crypto.randomUUID() : fullInteraction.current?.id ?? crypto.randomUUID(),
      timestamp: new Date().toISOString(), assessment: "full-note", status: "candidate", pending: true,
      source: fullInteraction.current?.source ?? { submitted_text: findings }, native_preview: preview, before_encounter: session.encounter };
    fullInteraction.current = trace;
    session.recordInteraction(trace);
    const accepted = await session.evaluate(preview.structured_encounter, assessmentIds, trace);
    if (!request.isCurrent()) return;
    if (accepted) {
      fullInteraction.current = undefined;
      setPreview(null);
      setFullTextDirty(false);
      setWorkflowState("complete");
      setActivePanel("checklist");
    } else {
      fullInteraction.current = { ...trace, status: "failed", pending: false };
      setWorkflowState("review");
    }
  }

  function loadExample(exampleId: string) {
    if (actionsBlocked) return;
    const example = examples.find((item) => item.id === exampleId);
    if (!example) return;
    editFindings(example.text);
    setServiceError("");
    textareaRef.current?.focus();
  }

  function clearAssessment() {
    if ((session.hasData || session.interactions.length || findings || fullTextDirty || preview || capturePending.length || captureBusy) && !window.confirm("Clear this encounter, all unaccepted findings, audio, interaction history, and the saved tab draft? This cannot be undone.")) return;
    setActiveAssessment(null);
    setCapturePending([]);
    setCaptureBusy(false);
    fullInteraction.current = undefined;
    invalidateInterpretation();
    session.reset();
    setFindings("");
    setFullTextDirty(false);
    setServiceError("");
    setActivePanel("findings");
    textareaRef.current?.focus();
  }

  function selectAssessment(id: AssessmentId | null) {
    if (macroBusy || session.busy) return;
    if ((capturePending.length || captureBusy || preview) && !window.confirm("Discard the unaccepted capture or interpretation? The full note and accepted findings will remain.")) return;
    invalidateInterpretation();
    session.rejectPending("Capture closed or assessment switched; unaccepted capture retained only in history.");
    setActiveAssessment(id);
    setCaptureBusy(false);
    setCapturePending([]);
  }

  function retryEvaluation() {
    if (actionsBlocked) return;
    if ((capturePending.length || preview) && !window.confirm("Recheck accepted findings and discard the unaccepted capture or interpretation? The full note will remain.")) return;
    invalidateInterpretation();
    session.rejectPending("Rechecking accepted findings; unaccepted capture discarded.");
    setActiveAssessment(null);
    setCapturePending([]);
    setCaptureBusy(false);
    void session.refresh();
  }

  const encounter = preview?.structured_encounter ?? session.encounter;
  const pendingAssessments = pendingAssessmentIds(fullTextDirty || Boolean(preview) || macroBusy, capturePending);

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
        <div className="header-trust"><LockKeyhole aria-hidden="true" size={14} /> Intron voice demo</div>
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
            {panel === "result" && urgent && <span className="urgent-dot" />}
          </button>
        ))}
      </nav>

      {urgent && <section className="workspace-urgent" aria-label="Accepted urgent guidance" role="alert">
        <strong>Urgent: prioritize immediate care. Do not delay referral.</strong>
        <ul>{result?.urgent_actions.map((action, index) => <li key={index}>{action}</li>)}</ul>
      </section>}

      {(!session.ready || session.storageHint || session.error || serviceError || progressBlocked) && <section className="workspace-notices" aria-label="Encounter service and safety notices">
        {!session.ready && <p role="status">{session.busy ? "Checking accepted findings with the server. Completion is not yet verified." : "Interpret is unavailable until the server evaluates accepted findings. Retry evaluation below."}</p>}
        {session.storageHint && <p role="status">{session.storageHint}</p>}
        {session.error && <p role="alert">{session.error}</p>}
        {serviceError && <p role="alert">{serviceError}</p>}
        {session.error && <button type="button" disabled={actionsBlocked} onClick={retryEvaluation}>Retry accepted assessment evaluation</button>}
        {progressBlocked && <p role="alert"><strong>Progress blocked; resolve evidence issues before using final synthesis.</strong> Routine classifications and management are withheld. Accepted urgent actions remain active.</p>}
      </section>}

      <main className="clinical-workspace" data-active-panel={activePanel}>
        <AssessmentChecklist encounter={encounter} result={result}
          progress={session.evaluation?.assessments} pendingAssessments={pendingAssessments}
          activeAssessment={activeAssessment}
          guideStatus={<div className="guide-session">
            {Object.entries(session.evaluation?.assessments ?? {}).flatMap(([id, progress]) => progress.blockers.map((blocker, index) => <p className="capture-warning" key={`${id}-${index}`}><strong>{id}:</strong> {blocker}</p>))}
            {preview && <>
              <p className="capture-warning">Checklist annotations are an unaccepted full-assessment preview. Accepted clinical guidance is unchanged.</p>
              {preview.extraction_warnings.map((warning, index) => <p className="capture-warning" key={index}>{warning}</p>)}
              <FullAssessmentReview preview={preview} scopeResult={scopeResult} disabled={actionsBlocked} onConfirm={() => void confirmAndEvaluate()} />
            </>}
            {fullTextDirty && <p className="capture-warning">The full note has unaccepted edits. All sections remain pending review until that note is accepted or explicitly discarded.</p>}
            {(findings || fullTextDirty || preview) && <button type="button" disabled={actionsBlocked} onClick={discardFullNote}>Discard full note</button>}
            {macroBusy && <p role="status">{workflowState === "extracting" ? "Interpreting full assessment..." : "Evaluating confirmed assessment..."}</p>}
            <button type="button" className="guide-clear" onClick={clearAssessment}>Clear encounter</button>
          </div>}
          renderCapture={(id) => activeAssessment === id ? <>
            <button className="capture-toggle" type="button" disabled={macroBusy || session.busy} onClick={() => selectAssessment(null)}>Close capture</button>
            <AssessmentCapture key={`${id}-${session.revision}`} assessment={id} encounter={session.encounter}
              revision={session.revision} progress={session.evaluation?.assessments[id]} urgent={urgent}
              serviceError={session.error}
              disabled={macroBusy || session.busy || !session.ready} onBusy={setCaptureBusy} onPending={setCapturePending}
               onAccept={session.accept} onRecordInteraction={session.recordInteraction} />
          </> : <button className="capture-toggle" type="button" disabled={macroBusy || session.busy}
            onClick={() => selectAssessment(id)}>Add voice or text findings</button>}
        />

        <section className="findings-panel" aria-labelledby="findings-title">
          <header className="pane-header">
            <div>
              <p className="panel-index">Encounter findings</p>
              <h1 id="findings-title">Describe the completed assessment</h1>
            </div>
            {(findings || session.hasData) && (
              <button className="text-button" type="button" onClick={clearAssessment}>
                <RotateCcw aria-hidden="true" size={14} /> Clear
              </button>
            )}
          </header>

          <p className="field-help" id="findings-help">
            Include age, all danger signs, and the cough/breathing, diarrhoea, fever, and ear
            assessment findings. Omitted findings remain unknown.
          </p>
          <p className="field-help capture-disclosure">Research/demo only. Findings are sent to Modal for interpretation. Full-note transcripts/results are retained in this tab's local interaction trace. Use synthetic data only. For incremental voice or text reports, use the assessment Guide.</p>

          <div className={`textarea-shell ${fieldError ? "has-error" : ""}`}>
            <textarea
              ref={textareaRef}
              value={findings}
              disabled={actionsBlocked}
              onChange={(event) => editFindings(event.target.value)}
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
          {fullTextDirty && <p className="field-help">Unaccepted full-note edits. Any displayed result reflects accepted findings only.</p>}
          {(findings || fullTextDirty || preview) && <button className="text-button discard-full-note" type="button" disabled={actionsBlocked} onClick={discardFullNote}>Discard full note</button>}

          <button
            className="analyze-button"
            type="button"
            disabled={actionsBlocked || !session.ready}
            onClick={() => void interpretAssessment()}
          >
            {workflowState === "extracting" ? (
              <><LoaderCircle className="button-spinner" aria-hidden="true" size={18} /> Interpreting findings</>
            ) : (
              <><FileText aria-hidden="true" size={18} /> Interpret findings <ArrowRight aria-hidden="true" size={18} /></>
            )}
          </button>

          {preview && !preview.outside_supported_scope && preview.schema_valid && workflowState === "review" && (
            <div className="review-status">
              <ShieldCheck aria-hidden="true" size={18} />
              <div><strong>Interpretation ready</strong><span>Review the checklist before evaluation.</span></div>
            </div>
          )}

          <div className="example-picker">
            <label htmlFor="example-case">Demonstration input</label>
            <select id="example-case" disabled={actionsBlocked} defaultValue="" onChange={(event) => loadExample(event.target.value)}>
              <option value="" disabled>Load a demonstration input…</option>
              {examples.map((example) => <option value={example.id} key={example.id}>{example.label}</option>)}
            </select>
            <small>Use a prepared input for a repeatable demonstration, or enter new findings.</small>
          </div>

          <InteractionHistory interactions={session.interactions} />

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
            {workflowState === "idle" && !result && !preview && <EmptyResult />}
            {workflowState === "extracting" && <ProcessingState stage="extracting" />}
            {preview && <FullAssessmentReview preview={preview} scopeResult={scopeResult} disabled={actionsBlocked} onConfirm={() => void confirmAndEvaluate()} />}
            {workflowState === "evaluating" && <ProcessingState stage="evaluating" />}
            {result && <>
              {pendingAssessments.length > 0 && <p className="field-help">The result below reflects accepted findings only. New findings have not yet been applied.</p>}
              <ResultPanel result={result} blocked={progressBlocked} />
            </>}
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
