import type { InteractionTrace } from "../types";

export function InteractionHistory({ interactions, showDebug = true }: { interactions: InteractionTrace[]; showDebug?: boolean }) {
  return <details className="interaction-history">
    <summary>{showDebug ? "Interaction trace" : "Assessment history"} ({interactions.length})</summary>
    {showDebug ? <p>Local to this tab. Synthetic data only. Transcripts, submitted text, provider results, review choices, and errors may contain sensitive health information (PHI). No audio is saved. Historical results are debug records, never current clinical guidance. Clear encounter removes this history.</p>
      : <p>Local to this tab. Synthetic data only. Submitted reports may contain sensitive health information (PHI). This history is not current clinical guidance. Starting a new assessment removes this history.</p>}
    {!interactions.length && <p>No interactions recorded in this tab.</p>}
    {interactions.map((entry) => <details className="trace-entry" key={entry.id}>
      <summary>{showDebug ? entry.assessment : ({
        danger: "Danger signs", respiratory: "Breathing", diarrhoea: "Diarrhoea", fever: "Fever", ear: "Ear symptoms", "full-note": "Full report",
      })[entry.assessment]} / {entry.pending ? "request in progress" : showDebug ? entry.status : ({
        transcribed: "Report received", candidate: "Awaiting confirmation", accepted: "Reviewed", rejected: "Not accepted", failed: "Report needs attention",
      })[entry.status]} / {entry.timestamp}
        {showDebug && entry.source.language ? ` / ${entry.source.language}` : ""}
        {showDebug && entry.candidate?.understanding?.provider ? ` / ${entry.candidate.understanding.provider}` : ""}
      </summary>
      {entry.error && <p className="capture-warning" role={showDebug ? undefined : "alert"}>{showDebug ? entry.error : "Could not process these findings. Review the original report."}</p>}
      {!showDebug && entry.source.question && <><strong>Question at capture</strong><p>{entry.source.question.text}</p></>}
      {entry.source.raw_asr_transcript !== undefined && <><strong>{showDebug ? "Original ASR transcript (read-only)" : "Original report"}</strong><p className="trace-text">{entry.source.raw_asr_transcript}</p></>}
      {entry.source.submitted_text !== undefined && (showDebug || entry.source.submitted_text !== entry.source.raw_asr_transcript) && <><strong>{showDebug ? "Submitted editable input" : "Submitted report"}</strong><p className="trace-text">{entry.source.submitted_text}</p></>}
      {!showDebug && entry.source.raw_asr_transcript === undefined && entry.source.submitted_text === undefined && entry.candidate && <><strong>Original report</strong><p className="trace-text">{entry.candidate.input_text}</p></>}
      {showDebug && entry.candidate?.english_rendering != null && <><strong>English rendering (nonauthoritative)</strong><p className="trace-text">{entry.candidate.english_rendering}</p></>}
      {!showDebug && !!entry.candidate?.warnings.length && <p className="capture-warning">Please review the report and confirm the findings on the assessment.</p>}
      {!showDebug && entry.candidate?.uncertainties?.map((item, index) => <p key={index}>{item.reason} <q>{item.source_text}</q></p>)}
      {showDebug && <details><summary>Debug JSON (sensitive data; not current guidance)</summary><pre>{JSON.stringify(entry, null, 2)}</pre></details>}
    </details>)}
  </details>;
}
