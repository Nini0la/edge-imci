import { useId, type KeyboardEvent } from "react";
import type { ClinicalValue, FieldDescriptor } from "../types";
import "../clinical-controls.css";

export interface ClinicalFieldControlProps {
  descriptor: FieldDescriptor;
  value: ClinicalValue | undefined;
  raw?: string;
  acceptedValue: ClinicalValue;
  pending: boolean;
  source: "accepted" | "voice" | "worker" | "kept" | "conflict";
  error?: string;
  requiresChoice?: boolean;
  disabled?: boolean;
  onChange: (value: ClinicalValue) => void;
  onKeep?: () => void;
  booleanLabels?: { yes: string; no: string };
}

export function ClinicalFieldControl({
  descriptor, value, raw, acceptedValue, pending, source, error,
  requiresChoice = false, disabled = false, onChange, onKeep, booleanLabels,
}: ClinicalFieldControlProps) {
  const id = useId();
  const numeric = descriptor.kind === "integer" || descriptor.kind === "number";
  const inputValue = raw ?? (typeof value === "number" || typeof value === "string" ? String(value) : "");
  const bounds = [
    descriptor.minimum !== undefined ? `Minimum: ${descriptor.minimum}` : "",
    descriptor.maximum !== undefined ? `Maximum: ${descriptor.maximum}` : "",
  ].filter(Boolean).join(". ");
  const showAccepted = acceptedValue !== null && (source === "conflict" || (pending && (value !== acceptedValue
    || (numeric && raw !== undefined && raw !== String(acceptedValue)))));
  const acceptedLabel = acceptedValue === null ? "Not assessed"
    : typeof acceptedValue === "boolean" ? (acceptedValue ? booleanLabels?.yes ?? "Yes" : booleanLabels?.no ?? "No")
      : descriptor.options?.find((option) => option.value === acceptedValue)?.label ?? String(acceptedValue);
  const sourceLabel = source === "accepted" ? (acceptedValue === null ? "Not assessed" : "Confirmed")
    : source === "worker" ? "Your answer"
      : source === "kept" ? "Kept confirmed answer" : source === "conflict" ? "Conflicting recordings" : "From recording";
  const describedBy = [
    numeric && bounds ? `${id}-bounds` : "",
    showAccepted ? `${id}-accepted` : "",
    requiresChoice ? `${id}-choice` : "",
    error ? `${id}-error` : "",
  ].filter(Boolean).join(" ") || undefined;
  const choices: { value: ClinicalValue; label: string }[] = descriptor.kind === "boolean"
    ? [{ value: true, label: booleanLabels?.yes ?? "Yes" }, { value: false, label: booleanLabels?.no ?? "No" }]
    : descriptor.options ?? [];
  const allChoices = [...choices, { value: null, label: "Not assessed" }];
  // Arrow keys select explicitly, just like clicking a radio; rendering never accepts a proposal.
  const navigateChoices = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const direction = ["ArrowRight", "ArrowDown"].includes(event.key) ? 1
      : ["ArrowLeft", "ArrowUp"].includes(event.key) ? -1 : 0;
    if (!direction && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? allChoices.length - 1
      : (index + direction + allChoices.length) % allChoices.length;
    const buttons = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="radio"]');
    buttons?.[next]?.focus();
    onChange(allChoices[next].value);
  };
  const selectedIndex = source === "conflict" ? -1 : allChoices.findIndex((choice) => choice.value === (value ?? null));

  return (
    <div className="clinical-field-control" data-pending={pending || undefined} role="group" aria-labelledby={`${id}-label`} aria-describedby={describedBy}>
      <div className="clinical-field-control__heading">
        <label id={`${id}-label`} htmlFor={numeric ? `${id}-input` : undefined}>{descriptor.label}</label>
        <span className="clinical-field-control__source">{sourceLabel}</span>
      </div>
      {numeric ? (
        <div className="clinical-field-control__number">
          <input
            id={`${id}-input`}
            type="text"
            inputMode={descriptor.kind === "integer" ? "numeric" : "decimal"}
            value={inputValue}
            disabled={disabled}
            aria-invalid={Boolean(error)}
            aria-describedby={[describedBy, descriptor.unit ? `${id}-unit` : ""].filter(Boolean).join(" ") || undefined}
            onChange={(event) => onChange(event.target.value)}
          />
          {descriptor.unit && <span id={`${id}-unit`}>{descriptor.unit}</span>}
          <button type="button" disabled={disabled} onClick={() => onChange(null)}>Not assessed</button>
        </div>
      ) : (
        <div className="clinical-field-control__choices" role="radiogroup" aria-labelledby={`${id}-label`} aria-describedby={describedBy} aria-invalid={Boolean(error)}>
          {allChoices.map((choice, index) => (
            <button
              key={String(choice.value)}
              type="button"
              role="radio"
              aria-checked={index === selectedIndex}
              data-unknown={choice.value === null || undefined}
              tabIndex={index === (selectedIndex < 0 ? 0 : selectedIndex) ? 0 : -1}
              disabled={disabled}
              onClick={() => onChange(choice.value)}
              onKeyDown={(event) => navigateChoices(event, index)}
            >{choice.label}</button>
          ))}
        </div>
      )}
      {numeric && bounds && <p id={`${id}-bounds`} className="clinical-field-control__help">{bounds}{descriptor.unit ? ` (${descriptor.unit})` : ""}</p>}
      {showAccepted && <p id={`${id}-accepted`} className="clinical-field-control__help">Confirmed: {acceptedLabel}{numeric && acceptedValue !== null && descriptor.unit ? ` ${descriptor.unit}` : ""}</p>}
      {requiresChoice && <p id={`${id}-choice`} className="clinical-field-control__warning">Choose an answer to confirm this observation.</p>}
      {error && <p id={`${id}-error`} className="clinical-field-control__error" role="alert">{error}</p>}
      {onKeep && <button className="clinical-field-control__keep" type="button" disabled={disabled} onClick={onKeep}>Keep confirmed answer</button>}
    </div>
  );
}
