import { useState } from "react";
import "../patient-intake.css";

export function PatientIntake({ patientName = "", age, revision, busy, error, onSave, onCancel }: {
  patientName?: string;
  age: number | null;
  revision: number;
  busy: boolean;
  error: string;
  onSave: (name: string, age: number, revision: number) => Promise<boolean>;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(patientName);
  const [months, setMonths] = useState(age == null ? "" : String(age));
  const [originalRevision, setOriginalRevision] = useState(revision);
  const [validation, setValidation] = useState("");
  const stale = revision !== originalRevision;

  return <form className="patient-intake-form" onSubmit={(event) => {
    event.preventDefault();
    if (busy || stale) return;
    const value = Number(months);
    if (!name.trim() || name.trim().length > 200 || !months.trim() || !Number.isInteger(value) || value < 2 || value > 59) {
      setValidation("Enter a patient name and age in completed months, from 2 to 59.");
      return;
    }
    setValidation("");
    void onSave(name.trim(), value, originalRevision);
  }}>
    <div className="patient-intake-fields">
      <label htmlFor="patient-name">Patient name
        <input id="patient-name" name="patient-name" type="text" autoComplete="off" maxLength={200} required
          value={name} disabled={busy} onChange={(event) => setName(event.target.value)} />
      </label>
      <label htmlFor="patient-age">Age in completed months
        <input id="patient-age" name="patient-age" type="number" inputMode="numeric" min={2} max={59} step={1} required
          value={months} disabled={busy} aria-describedby="patient-age-help" onChange={(event) => setMonths(event.target.value)} />
      </label>
    </div>
    <p id="patient-age-help">This assessment is for children aged 2 to 59 months. Both fields are required.</p>
    {(validation || error) && <p className="intake-error" role="alert">{validation || error}</p>}
    {stale && <div role="status"><p>Patient details or confirmed findings changed. Reload the current details before saving.</p>
      <button type="button" disabled={busy} onClick={() => {
        setName(patientName); setMonths(age == null ? "" : String(age)); setOriginalRevision(revision); setValidation("");
      }}>Reload patient details</button>
    </div>}
    <div className="patient-intake-actions">
      <button type="submit" disabled={busy || stale}>{busy ? "Saving patient details..." : onCancel ? "Save patient details" : "Start assessment"}</button>
      {onCancel && <button type="button" className="intake-cancel" disabled={busy} onClick={onCancel}>Cancel</button>}
    </div>
    <p className="patient-privacy">Use a synthetic name for this demo. The intake name stays in this browser tab and is not automatically sent for text interpretation.</p>
  </form>;
}
