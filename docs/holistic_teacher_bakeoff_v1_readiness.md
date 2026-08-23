# Holistic teacher/prompt bake-off v1 readiness

> **Authority:** `IMPLEMENTATION_REFERENCE` · **Lifecycle:** `CURRENT` · Readiness record for experiment `holistic-teacher-prompt-bakeoff-v1`.

## Current state

The model-independent pilot infrastructure is ready for review. It builds an identical comparison surface from all 78 frozen product-level holistic cases and two prompt strategies:

1. `phc-concise-complete-v1`
2. `phc-natural-complete-v1`

That produces 156 potential requests per teacher snapshot: one variant for every case under each strategy. Building the surface is local and deterministic. It neither sends requests nor persists synthetic candidates.

No teacher has been selected or called. No generated language variant, mock teacher output, disposable corpus, API usage or spend has been created by this work.

## What the pilot compares

Each authorized teacher receives the same frozen cases and the same two pinned prompt strategies. The teacher returns only the PHC-worker input and fact-evidence annotations. The pipeline attaches the already approved assistant response and alignment. The comparison can then measure:

- parse and schema success;
- deterministic mechanical acceptance;
- error-code distribution;
- human-reviewed semantic faithfulness;
- human-reviewed naturalness and PHC suitability;
- duplicate/near-duplicate behavior;
- latency, token usage, retries and cost once real calls are authorized.

Deterministic checks are a screening layer, not final language approval.

## Completed prerequisites

- The 78-case holistic semantic suite is approved and frozen.
- The 78 canonical language renderings are approved and frozen.
- The stable response grammar is pinned.
- The candidate, final-record and attempt schemas exist.
- The blind human-review schema, proposed selection policy and stable scoring anchors exist.
- An authorized immutable schedule can be constructed once the approval gate is satisfied.
- Resume state is derived without automatic semantic retries or duplicate retries of uncertain provider requests.
- The Azure Foundry v1 Responses adapter, structured-output compatibility layer, secret-safe authentication setup and bounded one-unit executor are implemented.
- The Azure executor persists a `REQUESTED` receipt before network I/O and leaves ambiguous provider failures for reconciliation.
- Azure execution remains blocked by its checked-in provider configuration. Deployment `gpt-4.1`, model `gpt-4.1`, snapshot `2025-04-14` and API-key environment names are project-owner supplied and pinned; the attempt ceiling, budget and remote-call authorization remain unresolved.
- Six canary cases are deterministically selected across complete/incomplete, urgent/non-urgent, stateful and all-pathway strata, producing 12 unauthorized source requests across the two prompt strategies.
- The request builder excludes encounter provenance fields from teacher-renderable facts.
- The teacher payload excludes the frozen assistant response, classifications, actions, target urgency language, evaluator traces, rule IDs and source hashes.
- Source-value hashes are attached internally only after candidate validation.
- Unknown values remain visible as unknown in the structured payload and are excluded from the required known-fact evidence set.
- Tests cover equal-case scheduling, no-generation guardrails, source-fact exactness, rejection mutations, frozen-target attachment and training ineligibility.

## Explicit authorization gate

The pilot config remains `BLOCKED_PENDING_TEACHER_BUDGET_AND_REMOTE_CALL_AUTHORIZATION`. Before a real run, the project owner must approve:

- the teacher candidates and immutable model snapshots;
- provider and credential context;
- remote model calls;
- a maximum budget or credit limit;
- sampling and maximum-output-token settings; and
- the proposed language-variant contract.

Those decisions must be written into a new versioned run configuration and immutable schedule before calls begin. The infrastructure must not treat an environment credential or an available API as authorization.

The provider-specific fields are recorded in `configs/generation/azure_foundry_teacher_execution_v1.json`. Its checked-in state is `BLOCKED_PENDING_PROJECT_OWNER_AUTHORIZATION`, so the implemented transport cannot be constructed from that file for a real run.

## After authorization

Run each approved teacher/strategy configuration against the identical 78 cases, store every attempt with provenance and raw usage, perform deterministic screening, then review the passing candidates. Select a winning recipe only after the review record is complete. Bulk generation and training remain separately gated.
