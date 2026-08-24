# EdgeIMCI structured-extraction campaign final report v1

> **Authority:** `PROJECT_OWNER_DELEGATED_REVIEW` · **Lifecycle:** `CORPUS_EXPORT_COMPLETE` · Training and production clinical use remain unauthorized.

The guarded Azure campaign is reconciled at exactly 2,142 candidate-bearing allocation slots plus eight preserved transport-only receipts. The exported learning pair is free-form PHC language to deterministic model-facing encounter JSON; no classification, action, urgency, or frozen assistant response is used as the student target.

## Outcome

- Approved canonical corpus records: **1497**
- Excluded/held receipts: **653**
- Parent encounters represented: **78 / 78**
- T3 deterministic-pass semantic sample: **145** (one rejected)
- T1/T2 policy: only individually approved pass records were promoted; unsampled pre-remediation passes remain held.
- All deterministic rejections, parse failures, and transport-only receipts remain immutable evidence and were excluded.

## Approved records by style

- `NIGERIAN_ENGLISH`: 390
- `NIGERIAN_PIDGIN`: 300
- `NOISY_TYPED_ENGLISH`: 394
- `TELEGRAPHIC_PHC_NOTE`: 413

## Parent-derived partitions

- `TEST`: 143
- `TRAIN`: 1239
- `VALIDATION`: 115

## Export boundary

`canonical_records.jsonl` is the reusable, model-neutral dataset artifact. `chat_messages.jsonl` is a deterministic system/user/assistant serialization whose assistant content is JSON only. Applying a Qwen chat template remains a later deterministic training-preparation step.

No Azure calls, fine-tuning, clinical-rule changes, or training authorization are performed by the export step.
