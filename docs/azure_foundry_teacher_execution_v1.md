# Azure Foundry teacher execution v1

> **Authority:** `IMPLEMENTATION_REFERENCE` · **Lifecycle:** `CURRENT` · Provider adapter and safety gates for the EdgeIMCI teacher bake-off. This document does not authorize remote calls.

## Purpose

The Azure Foundry execution layer connects the provider-neutral holistic teacher bake-off to the Azure OpenAI v1 Responses API. It preserves the existing experiment boundaries:

- the teacher receives the structured encounter and rendering instructions, never the frozen assistant target;
- the Azure deployment name and exact underlying model snapshot are recorded separately;
- the provider returns only a PHC-worker submission and its fact-evidence spans;
- full local deterministic validation remains authoritative;
- generated candidates remain pending human review and training-ineligible;
- every started request has an immutable `REQUESTED` receipt before network I/O; and
- a timeout or other uncertain provider outcome remains `REQUESTED` for reconciliation rather than being retried automatically.

The checked-in execution configuration is deliberately blocked. It records the project-owner-supplied Azure deployment `gpt-4.1`, model `gpt-4.1`, snapshot `2025-04-14`, and API-key environment names. It contains no credential value and does not infer authorization or spend from the presence of Azure access.

## Versioned artifacts

| Artifact | Role |
|---|---|
| `configs/generation/azure_foundry_teacher_execution_v1.json` | Canonical secret-free execution configuration and authorization state; the YAML sibling is generated for readability. |
| `configs/generation/azure_foundry_teacher_execution_v1.schema.json` | Shape of blocked and authorized Azure execution configurations. |
| `src/edge_imci/generation/azure_foundry.py` | URL normalization, provider request construction, execution gates, attempt receipts and response normalization. |
| `configs/generation/holistic_teacher_bakeoff_schedule_v1.schema.json` | Existing immutable per-run schedule and budget authorization. |
| `configs/generation/holistic_teacher_attempt_v1.schema.json` | Existing immutable attempt record. |

The execution configuration does not contain secrets. It stores only environment-variable names. The actual environment values are read only when an authorized transport is constructed and are not copied into payloads or attempt records.

## Azure API contract

The adapter uses the Azure OpenAI-compatible v1 Responses API through either supported Azure endpoint family:

- Azure OpenAI resource: `https://<resource>.openai.azure.com/openai/v1/`; or
- Foundry project: `https://<resource>.services.ai.azure.com/api/projects/<project>/openai/v1/`;
- `model`: the Azure deployment name resolved from the authorized execution configuration;
- `input`: the blind teacher prompt already built by `holistic_variants.py`;
- `store`: `false`;
- `max_output_tokens`: the value pinned in the teacher configuration; and
- `text.format`: strict JSON Schema structured output for the teacher candidate.

Azure structured outputs support only a subset of JSON Schema. The provider-facing copy removes unsupported constraints such as `minLength`, `maxLength`, `pattern`, `minItems`, and `uniqueItems`, and represents fixed `const` values as single-value enums. It also narrows the case and strategy IDs to the scheduled request. This does not relax EdgeIMCI acceptance: the returned candidate is checked against the complete canonical candidate schema and the existing source-fact validator after receipt.

## Authentication modes

The execution configuration supports:

- `API_KEY`, using the named environment variable (normally `AZURE_OPENAI_API_KEY`); or
- `ENTRA_ID`, using Azure Identity's default credential chain and the Azure Cognitive Services scope.

The project owner selected `API_KEY` for this bake-off. `UNRESOLVED` remains an invalid execution state for later configurations.

The resource or project endpoint is supplied through the configured environment name, currently `AZURE_OPENAI_BASE_URL`. A valid Foundry project endpoint may omit the final `/openai/v1/`, which the adapter appends deterministically. An endpoint with credentials, a query string, a fragment, a non-HTTPS scheme, or an unsupported path is rejected.

## Independent authorization gates

A remote request is possible only when all of the following agree:

1. The Azure execution config has status `AUTHORIZED_FOR_RECORDED_BAKEOFF_ONLY` and `remote_calls_authorized = true`.
2. At least one Azure deployment name, model family and immutable model snapshot are pinned.
3. Authentication mode and secret environment name are resolved.
4. A positive maximum remote-attempt count and maximum USD budget are recorded.
5. The immutable bake-off schedule separately records project-owner approval, calls authorization and a budget ceiling.
6. The scheduled provider, model family, snapshot, prompt pin, strategy, case ID and request hash match the execution configuration and source request; that exact model/snapshot pair resolves to one deployment name.
7. The next attempt fits under both the attempt ceiling and the reserved maximum cost for that call.

An available credential alone satisfies none of these authorization gates.

## Per-request state transition

```text
authorized config + immutable scheduled unit
                  |
                  v
validate deployment, snapshot, request hash, attempt ceiling and cost reservation
                  |
                  v
persist REQUESTED receipt before network I/O
                  |
          +-------+--------+
          |                |
          v                v
provider result       ambiguous exception
          |                |
          v                v
parse + validate       leave REQUESTED
          |            reconcile; do not guess/retry
          v
persist PARSE_FAILED / DETERMINISTIC_REJECTED / PENDING_HUMAN_REVIEW
```

Confirmed pre-request transport failures can be represented separately as `TRANSPORT_FAILED`, but generic SDK exceptions are not automatically treated as proof that Azure received nothing.

The OpenAI SDK's built-in retry behavior is disabled (`max_retries = 0`). Retry and reconciliation decisions belong to the recorded EdgeIMCI schedule rather than an invisible transport-level loop.

## What is ready

- Provider request payload construction is deterministic and does not call Azure.
- Azure's structured-output schema subset is generated from the canonical local schema.
- API-key and Entra ID client construction are secret-safe and lazy.
- Attempt receipts, successful responses, parse failures, deterministic rejections and confirmed transport failures normalize to the existing attempt schema.
- The bounded executor enforces deployment/snapshot equality, attempt ceilings, cost reservation and receipt-before-I/O ordering.
- Tests use an in-memory fake transport only. They produce no synthetic corpus and consume no Azure resources.

## What remains blocked

Before the first paid request, the project owner must record:

- the exact first-run attempt ceiling;
- the hard USD ceiling for that run;
- temperature/top-p and maximum output tokens for each configuration; and
- explicit approval of the proposed language-variant contract and remote bake-off calls.

After those values are recorded, construct and persist the immutable schedule, inspect its request count and maximum exposure, and authorize a deliberately small first tranche. The first tranche should be reviewed before expanding to the 2,184-attempt standard lane or the later Azure Batch lane.
