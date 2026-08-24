# EdgeIMCI structured-extraction architecture impact

> **Authority:** `WORKING_ARCHITECTURE` · **Lifecycle:** `IMPLEMENTED_FOR_REVIEW` · No clinical-rule change.

## Decision and compatibility

The new learned task is compatible with the current repository without major clinical rework:

```text
free-form PHC findings
        -> learned structured extraction
        -> model-facing encounter JSON
        -> deterministic adapter and validity checks
        -> existing completeness and IMCI evaluator
        -> deterministic classifications and actions
        -> presentation
```

The frozen 78-case semantic suite already contains the required source state under `input.encounter`. The existing teacher pipeline already produces the required free-form input while remaining blind to target-side decisions. The architecture change therefore replaces the student label; it does not replace the semantic suite, teacher task, clinical rules, completeness policy, deterministic evaluator or frozen presentation references.

## Existing effective source and required projection

The clean v1 projection is:

```text
frozen_record.input.encounter
    - encounter_id
    - schema_version
    = model-facing encounter target
```

All remaining fields are observations or encounter context currently consumed by the deterministic evaluator. Every field remains present in the canonical target. JSON `null` means `UNKNOWN`; it never means negative. An inactive pathway is represented by a `null` pathway object, matching the frozen source.

Included groups and fields:

- `patient_facts`: age and the four pathway-entry observations;
- `danger_signs`: the five general danger-sign observations;
- `respiratory`: duration, rate, signs, validity conditions, oximetry, HIV modifier, bronchodilator-trial and post-trial observations;
- `diarrhoea`: duration, blood, dehydration signs, cholera context and the currently reserved rehydration-stage fields;
- `fever`: measurement, malaria context/testing, duration, bacterial-cause qualifier, stiff neck, measles and eye/mouth observations;
- `ear`: pain, caregiver-reported discharge, duration, observed pus and observed swelling.

The existing field names already preserve important distinctions such as `ear_discharge_reported` versus `pus_draining_from_ear`, measurement validity, pre/post-bronchodilator state, and `identified_bacterial_cause_present` rather than an unrestricted claim about whether a bacterial cause exists.

## Intentionally excluded fields

The model target excludes:

- `encounter_id` — dataset/runtime identity, not a clinical observation;
- internal `schema_version` — the target contract is pinned outside the clinical payload;
- the semantic record's `expected` evaluation;
- completeness results and missing-element lists;
- classifications, urgency, referral and actions;
- rule IDs, evaluator traces and oracle IDs;
- coverage tags, review decisions and clinical citations;
- source hashes, logic signatures and freeze metadata;
- teacher/generation metadata and evidence hashes;
- frozen assistant responses and semantic alignment.

These remain deterministic outputs, audit metadata or presentation references and must not become learned clinical labels.

## Adapter boundary

A small deterministic adapter is required. It validates model JSON, supplies a runtime `encounter_id`, restores the pinned internal encounter schema version and constructs the existing `HolisticEncounter`. The current evaluator then runs unchanged.

The model-facing schema permits truthful non-negative ages outside 2–59 months so the extractor can represent the two frozen scope-boundary cases. The adapter retains the existing deterministic age-scope rejection; the model must not distort age to satisfy the supported clinical range.

The v1 adapter continues to reject non-null Plan B/C post-rehydration treatment-stage state because that evaluator remains outside the approved initial-encounter product scope. Bronchodilator pre/post reassessment remains supported.

## Existing language reuse

Accepted teacher submissions can be reused without regeneration:

```text
accepted user_submission + deterministic projection(source semantic case)
```

The teacher's `fact_evidence` remains validation/audit evidence. It is not the student target. Rejected semantic attempts remain rejected evidence. Frozen assistant responses remain product-language references and downstream presentation artifacts but are not the primary extraction SFT label.

## Canonical dataset and serialization direction

The canonical dataset record should retain the user submission and target as separate structured values, plus source/variant/target-contract provenance. It should not store only tokenizer-specific text.

```text
canonical extraction record
        -> deterministic role-message formatter
        -> model tokenizer's pinned Qwen chat template
        -> SFT token sequence
```

This keeps the corpus reusable across Qwen3-1.7B and later challenger models.

## Evaluation impact

Primary evaluation moves to structured extraction: schema validity, exact match, field accuracy, positive/negative/UNKNOWN preservation, measurements, durations, qualifiers and pre/post state. The same deterministic evaluator supplies downstream decision-equivalence metrics for completeness, classifications, urgent action, referral behavior, actions, missing information and contradictions.

Urgent-action equivalence must remain separately visible even when overall decision equivalence fails.

## Stale documentation and experiment definitions

The following currently describe direct clinical-response generation as the main student task and require updates:

- root `README.md` and `experiments/README.md`;
- `docs/synthetic_data_generation_experiment_plan.md`;
- `docs/synthetic_data_generation_experiment_notes.md`;
- `docs/experimental_campaign_map.md`;
- direct-output SFT/evaluation entries in `experiments/registry/experiment_matrix.json`.

The language-variant contract and teacher bake-off remain substantively valid, but their deterministic assembly language must distinguish preserved assistant references from the new primary structured target.

## Approved dataset-policy decisions

The project owner approved `edge-imci-structured-extraction-dataset-policy-v1`:

1. The extractor must preserve truthful out-of-scope ages and findings; the deterministic scope checker owns rejection. Cases 77 and 78 are reserved as TEST parents. Two distinct extraction-only TRAIN parents now exist: `oos-extract-young-respiratory-001` and `oos-extract-older-fever-001`. They contain no clinical output labels and still require generated/reviewed input language before SFT pairing.
2. The split unit is the parent semantic encounter. A frozen SHA-256 bucket policy assigns approximately 80% `TRAIN`, 10% `VALIDATION` and 10% `TEST` before generation at scale, and every language realization inherits its parent's partition. Cross-partition parent reuse is prohibited.
3. V1 does not invent a generic acquisition-mode label. Acquisition/source distinctions remain only where the existing substrate explicitly represents them and they matter downstream. Generic acquisition-mode evaluation is `NOT_APPLICABLE`.
4. Non-null Plan B/C longitudinal reassessment state is corpus-ineligible until an approved evaluator exists. This does not block ordinary initial-encounter language generation.
5. The model predicts the underlying observations in contradictory evidence. The deterministic evaluator—not the model target—derives contradiction state.

Bulk generation, final corpus eligibility and training remain separately unauthorized.

No Azure/teacher calls, bulk generation or training are authorized by this note.

## Implemented review surface

The minimum infrastructure implementing this proposal is deliberately separate from the frozen clinical substrate:

| Artifact | Purpose |
| --- | --- |
| `configs/model_io/model_facing_encounter_v1.schema.json` | Versioned, strict model output contract; every field is present and `null` is UNKNOWN. |
| `src/edge_imci/model_io/encounter.py` | Frozen-source projection, schema validation, canonical JSON and deterministic adapter. |
| `configs/training/structured_extraction_sft_record_v1.schema.json` | Model-neutral canonical dataset record; training remains explicitly unauthorized. |
| `configs/training/structured_extraction_dataset_policy_v1.json` | Approved parent-split, scope-boundary, acquisition, reassessment and contradiction policy. |
| `src/edge_imci/training/structured_extraction.py` | Pairs only approved language variants with deterministic targets and formats role messages before a model-specific chat template. |
| `src/edge_imci/training/dataset_policy.py` | Deterministic parent partitioning and corpus-eligibility enforcement. |
| `src/edge_imci/evaluation/structured_extraction.py` | Structured extraction metrics and downstream deterministic decision equivalence. |
| `data/canary/structured_extraction_v1/` | Three reused, approved PHC submissions paired with deterministic targets and model-neutral chat messages. |
| `data/canary/input_language_styles_v1/` | Nine reviewed Nigerian English, Nigerian Pidgin, noisy-English and telegraphic canary pairs; three failures remain rejection evidence. |
| `data/canary/input_language_style_remediation_v1/` | Five reviewed v1.1 remediation pairs; noisy typed English passed 3/3, while Nigerian English remains pending a v1.2 validation gate. |
| `data/training_sources/structured_extraction_out_of_scope_v1/` | Two distinct TRAIN parents for truthful out-of-scope extraction; language generation has not started. |

The projection reproduces the frozen evaluator result exactly for all 76 in-scope semantic cases. The two scope-boundary cases retain ages 1 and 60 in the model target and reproduce the deterministic scope rejection at the adapter. The schema can represent Plan B/C reassessment state, while the adapter continues to reject it until an approved evaluator exists; this prevents silent misuse of the initial-encounter engine.

The canonical SFT record contains `input` and structured `target` separately. Its deterministic formatter creates system/user/assistant role messages, with the target serialized as compact canonical JSON. Applying a pinned Qwen chat template and tokenizer remains a later training configuration step, not part of the canonical dataset.
