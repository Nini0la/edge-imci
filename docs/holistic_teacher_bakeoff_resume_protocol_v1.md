# Holistic teacher bake-off resume protocol v1

> **Authority:** `IMPLEMENTATION_REFERENCE` · **Lifecycle:** `CURRENT` · Provider-independent execution-safety behavior; it does not authorize execution.

## Immutable schedule

A real bake-off begins with one versioned schedule created only after the variant contract, remote calls and a positive budget ceiling have been explicitly approved. The schedule pins:

- teacher provider, model and immutable snapshot;
- prompt ID, version and hash;
- sampling settings and maximum output tokens;
- the frozen semantic and language sources;
- contract, validator, attempt schema, review schema, selection policy and schedule-schema hashes;
- one request unit per configuration and frozen case; and
- one opaque blind-review ID per request unit.

The persisted schedule is immutable. Changing a teacher, prompt, sampling setting, source pin or budget authorization creates a new run and schedule rather than silently changing work in progress.

## Attempt lifecycle

Each scheduled request has an attempt receipt. A `REQUESTED` receipt may be finalized when its provider outcome is known. Once it records a terminal generation outcome, it is immutable. Human approval is a separate review record and never rewrites the teacher attempt.

Generation outcomes are:

- `TRANSPORT_FAILED`;
- `PARSE_FAILED`;
- `DETERMINISTIC_REJECTED`; or
- `PENDING_HUMAN_REVIEW`.

The latter means generation and deterministic screening finished; it does not mean the item is approved.

## Derived resume states

Resume state is recomputed from the immutable schedule and recorded attempts:

| State | Meaning | Next behavior |
|---|---|---|
| `PENDING` | No attempt exists. | Eligible for its first authorized call. |
| `RETRYABLE_TRANSPORT` | A confirmed transport failure occurred without a provider request ID and the one-retry allowance remains. | One transport retry may be scheduled. |
| `RECONCILIATION_REQUIRED` | A request was dispatched or has a provider ID but its outcome is uncertain. | Reconcile with the provider before any retry. |
| `TERMINAL` | Parse, deterministic or reviewable generation outcome is recorded. | Do not regenerate automatically. |
| `TERMINAL_TRANSPORT_FAILURE` | The single transport retry was exhausted. | Record the failure; do not retry again. |

Parse failures and semantic/deterministic rejections are never automatic-retry triggers in v1. This prevents repeated spending on a configuration that may be systematically wrong. An uncertain provider outcome is never treated as a clean transport failure, preventing duplicate billable requests.

## Relationship to common run tracking

The existing EdgeIMCI run sidecar remains the top-level provenance and accounting record. The bake-off schedule and attempts add request-level resume safety beneath it. No provider adapter or model call is implemented by this protocol.

## Verification boundary

Tests construct schedules, receipts, candidates and reviews only in memory. They do not persist mock teacher output or create a disposable corpus. Real schedule persistence and provider execution remain blocked by the approval gate.
