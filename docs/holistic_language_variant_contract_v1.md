# EdgeIMCI holistic language-variant contract v1

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `PROPOSED_FOR_REVIEW` · Human-readable companion to the canonical JSON contract.

## Purpose

This contract governs the first controlled variation of the approved 78-case product-level holistic golden language layer. It does not alter clinical semantics, authorize model calls, approve a dataset for training or introduce a new clinical rule.

The semantic unit remains one whole supported encounter. Each generated variant must preserve every supplied known observation, every explicit negative, every measurement and duration, the encounter context, and all unknowns as unknown.

## Generation boundary

For v1, a teacher may generate only:

- a varied, coherent PHC-worker `user_submission`; and
- `fact_evidence` annotations that map each known source fact to an exact text span.

The pipeline attaches the following deterministically from the frozen parent record:

- the canonical approved assistant response;
- semantic alignment;
- frozen source hashes; and
- parent rendering identity.

The teacher does not regenerate classifications, actions, urgency, missing-assessment elements, acquisition modes, contradictions, scope disposition or any assistant response. This is a controlled input-language experiment, not a new clinical synthesis experiment.

### Teacher-visible information

- structured encounter findings;
- known negatives;
- measurements and durations;
- relevant encounter context;
- acquisition information only when it is present in the source encounter; and
- explicit unknown-state representation.

### Teacher-hidden information

- the canonical assistant response or wording;
- expected classification labels;
- expected actions or treatment synthesis;
- target-side urgency wording;
- evaluator traces, rule IDs and policy IDs; and
- frozen source-value hashes.

The teacher returns fact IDs and evidence spans only. Source-value hashes are attached internally after validation. The request builder must never derive user-language prompts from the expected output, because that would allow target leakage and unnaturally answer-shaped PHC submissions.

## Allowed and forbidden change

Allowed change is limited to connected prose, sentence structure, coherent domain ordering and the difference between concise-complete and natural-complete PHC styles.

The following are forbidden:

- adding, omitting or changing a clinical fact;
- converting an unknown into a negative;
- changing how an observation was acquired;
- adding unapproved clinical shorthand;
- leaking schema fields, hashes, internal IDs, rule IDs or policy IDs; and
- rewriting the frozen assistant target.

## Deterministic acceptance boundary

The v1 validator checks the candidate schema, exact fact-ID set, presence of claimed evidence spans, source pins, internal-marker leakage, deterministic attachment of source-value hashes, exact attachment of the frozen assistant response and alignment, and non-duplication of the canonical user submission.

These checks establish mechanical integrity only. A teacher can copy the expected hashes while expressing a fact incorrectly, or point a fact to an irrelevant span. Deterministic acceptance therefore does **not** prove semantic faithfulness, naturalness or PHC suitability. Every pilot candidate remains `PENDING_HUMAN_REVIEW`, corpus-ineligible and training-ineligible until reviewed and separately approved.

## No-waste policy

- No mock teacher or disposable synthetic corpus is permitted.
- Infrastructure tests use frozen records and temporary in-memory mutations only.
- Infrastructure validation must not call a teacher.
- Rejected semantic generations are retained as attempt evidence but are not automatically regenerated.
- One transport retry is allowed for a genuine transport failure; it is not a semantic retry.
- Outputs from a winning configuration may be promoted later because they already use the final record and provenance shape.

## Canonical artifacts

- `configs/generation/holistic_language_variant_contract_v1.json` — canonical contract.
- `configs/generation/holistic_language_variant_contract_v1.yaml` — generated readable mirror.
- `configs/generation/holistic_language_variant_candidate_v1.schema.json` — teacher-returned candidate schema.
- `configs/generation/holistic_language_variant_record_v1.schema.json` — assembled variant schema.
- `configs/generation/holistic_teacher_attempt_v1.schema.json` — request/attempt/usage evidence schema.
- `configs/generation/holistic_language_variant_review_v1.schema.json` — blind human-review result schema.
- `configs/generation/holistic_teacher_bakeoff_schedule_v1.schema.json` — immutable authorized schedule schema.
- `configs/generation/holistic_teacher_bakeoff_selection_policy_v1.json` — proposed winner-evidence policy.
- `src/edge_imci/generation/holistic_variants.py` — request construction, deterministic validation and frozen-target assembly.
- `src/edge_imci/generation/holistic_bakeoff.py` — blind review, resume-state and comparison-summary logic.

## Approval effect

Approving this proposed contract would approve the controlled variation boundary. It would not select a teacher, authorize remote calls or spending, choose a winner, approve a corpus, or authorize training.
