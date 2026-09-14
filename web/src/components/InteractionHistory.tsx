import type { InteractionTrace } from "../types";

export function InteractionHistory({ interactions }: { interactions: InteractionTrace[] }) {
  return <details className="interaction-history">
    <summary>Interaction trace ({interactions.length})</summary>
    <p>Local to this tab. Synthetic data only. Transcripts, submitted text, provider results, review choices, and errors may contain sensitive health information (PHI). No audio is saved. Historical results are debug records, never current clinical guidance. Clear encounter removes this history.</p>
    {!interactions.length && <p>No interactions recorded in this tab.</p>}
    {interactions.map((entry) => <details className="trace-entry" key={entry.id}>
      <summary>{entry.assessment} / {entry.pending ? "request in progress" : entry.status} / {entry.timestamp}
        {entry.source.language ? ` / ${entry.source.language}` : ""}
        {entry.candidate?.understanding?.provider ? ` / ${entry.candidate.understanding.provider}` : ""}
      </summary>
      {entry.error && <p className="capture-warning">{entry.error}</p>}
      {entry.source.raw_asr_transcript !== undefined && <><strong>Original ASR transcript (read-only)</strong><p className="trace-text">{entry.source.raw_asr_transcript}</p></>}
      {entry.source.submitted_text !== undefined && <><strong>Submitted editable input</strong><p className="trace-text">{entry.source.submitted_text}</p></>}
      {entry.candidate?.english_rendering != null && <><strong>English rendering (nonauthoritative)</strong><p className="trace-text">{entry.candidate.english_rendering}</p></>}
      <details><summary>Debug JSON (sensitive data; not current guidance)</summary><pre>{JSON.stringify(entry, null, 2)}</pre></details>
    </details>)}
  </details>;
}
