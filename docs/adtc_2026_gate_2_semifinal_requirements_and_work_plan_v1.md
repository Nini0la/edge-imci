# EdgeIMCI - ADTC 2026 Gate 2 Semifinal Requirements and Work Plan

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `PROPOSED_FOR_REVIEW` · **Version:** `1.0.0` · **Requirements snapshot:** `2026-09-16` · **Deadline:** `2026-09-22`

## 1. Purpose and source precedence

This document is the working specification for EdgeIMCI Phase 2 through the ADTC 2026 Gate 2 semifinal submission. It combines competition compliance, model development, dataset design, evaluation, backend integration, runtime qualification, provenance, and submission-process safeguards.

The controlling competition input for this version is the project-owner Gate 2 brief supplied on 2026-09-16, identified here as `PROJECT_OWNER_GATE2_BRIEF_2026-09-16`. It was supplied outside the repository; its verbatim snapshot and digest remain `PENDING` and must be captured before this plan can become `CURRENT`. Before final submission, the requirements owner must compare this plan against the current organizer instructions and record any difference.

Clinical truth and competition process have separate authority. Source precedence is:

1. The WHO IMCI source is the external clinical source.
2. Human-approved review decisions resolve how the bounded representation handles recorded ambiguities.
3. Versioned canonical clinical artifacts define execution; conflict with a clinical source or approved decision is a defect requiring review.
4. Approved product policy may define interaction and scope but cannot invent or override clinical logic. Review records provide evidence and do not modify canonical artifacts.
5. Current written ADTC Gate 2 organizer requirements control competition compliance only.
6. Explicit project-owner instructions control project scope, budget, TEST access, and release decisions but cannot override clinical truth.
7. This working plan controls execution only after its lifecycle becomes `CURRENT`.
8. Earlier campaign plans and Gate 1 handoffs apply only within their recorded historical scope.

Upon project-owner approval, this document supersedes `status.md`, the current-sequence section of `experimental_campaign_map.md`, and `adtc_submission_and_asus_profiling_handoff_v1.md` as the active competition-stage plan. Until then, it authorizes planning and local preparation only. Those files remain historical evidence and implementation references; they must not be rewritten to make Gate 1 appear to have followed Gate 2 decisions.

## 2. Gate 2 objective

The central objective is:

> Produce a substantially more capable and reliable standalone model while preserving EdgeIMCI's core safety architecture: language understanding and extraction may be learned, but authoritative IMCI clinical decision logic remains deterministic.

Completion means more than training a model. Gate 2 is complete only when:

- the dual-mode model contract is frozen and implemented consistently in data, evaluation, and backend code;
- a versioned multitask dataset and leakage-controlled held-out suite are frozen;
- 0.6B, 1.7B, and 4B capacity experiments are evaluated under a matched initial design;
- one candidate clears predeclared capability, extraction, mode-separation, and runtime gates with adequate margin;
- the exact selected GGUF is evaluated through the final `llama.cpp` path;
- the application runs offline without hidden network dependencies;
- provenance, hashes, scripts, logs, comparisons, and licenses are complete;
- a valid fallback submission exists before the final candidate freeze;
- a fresh-clone audit and human signoff are complete; and
- the submission is delivered with buffer before September 22, 2026.

### 2.1 Phase 2 charter and approval record

| Charter field | Proposed value | Approval state |
|---|---|---|
| Mission | Improve standalone capability and extraction reliability without delegating clinical authority to the LLM | Pending project owner |
| In scope | Dual-mode contract, versioned multitask data, matched 0.6B/1.7B/4B validation, local `llama.cpp`, exact-GGUF qualification, reproducible submission package | Pending project owner |
| Out of scope | Clinical-rule expansion without source review, autonomous diagnosis/treatment, production clinical use, broad tuning sweeps, post-TEST changes | Pending project owner |
| Success gates | Section 8.7 acceptance gates, exact-artifact runtime gates, provenance completeness, fresh-clone audit | Pending project owner |
| Schedule | Section 17, recalculated after the exact organizer cutoff is recorded | Pending deadline confirmation |
| Budget | No paid compute authorized by this plan | Amount/provider/approver pending |
| Data owner | Accountable for source, license, review, split, deduplication, and release identity | Named owner pending |
| Dataset-generation agent | A frontier OpenAI coding agent is responsible for the bulk of dataset drafting and variation work that requires an LLM; exact model identity is pinned per run | Role assigned; remote/paid execution authorization pending |
| Training owner | Accountable for matched plans, budget use, run completeness, and checkpoint identities | Named owner pending |
| Evaluation owner | Independent custodian for policy, sealed TEST, scoring, adjudication, and deviation records | Named owner pending |
| Runtime owner | Accountable for GGUF conversion and exact target-device qualification | Named owner pending |
| Provenance owner | Accountable for report, metadata, hashes, licenses, and clean-room reproduction | Named owner pending |
| Human submitter | Sole authorized operator for public pushes, hosting, portal submission, and receipt retention | Named owner pending |

The charter becomes effective only when the project owner records approval, named owners, budget disposition, exact cutoff, and authorization boundaries in a versioned decision record and changes this document's lifecycle to `CURRENT`. Approval of planning does not imply paid training, remote calls, TEST access, public release, or submission authorization.

## 3. Current state and Round 1 diagnosis

### 3.1 Round 1 result

EdgeIMCI advanced to the semifinal with:

| Dimension | Score |
|---|---:|
| Accuracy | 38.18 |
| Performance | 100.00 |
| Efficiency | 89.25 |
| Total | 67.94 |

Round 1 demonstrated substantial speed and memory headroom. Accuracy, capability, and reliability were the limiting dimensions.

### 3.2 Observed judge-facing and standalone failures

The Gate 2 brief records:

- flipped negations and clinical facts;
- hallucinated facts that were explicitly absent;
- unstable answers to the same or similar prompts;
- weak responses when clinical cases were queried directly;
- invented EdgeIMCI implementation details such as TensorRT, ONNX, or TPU use;
- poor understanding of EdgeIMCI and the model's intended role;
- weak out-of-distribution and unsupported-language behavior; and
- malformed JSON that sometimes disrupted the downstream deterministic pipeline.

These observations must become explicit evaluation cases. They are not adequately addressed by adding more extraction rows alone.

### 3.3 Existing research evidence

The Phase 1 and post-Gate-1 evidence establishes:

- The deterministic clinical engine, completeness policy, model-facing schema, workstation prototype, training runner, experiment registry, and evaluation infrastructure exist.
- The original Qwen3-0.6B SFT reached 97.20% decision equivalence and 99.89% field accuracy on the closed 143-record TEST, but failed six preregistered thresholds, including urgent-action and referral gates.
- The original base-control comparison was methodologically confounded. The post-hoc schema-informed base result is supplementary evidence, not a replacement untouched control.
- The seven-style v2 release contains 7,163 rows, but its three newly added styles occur only in TRAIN. Validation and TEST still cover four styles.
- Exact duplicates were deliberately retained in v2, semantic review of the promoted wave was waived, and data volume must not be treated as equivalent to diversity or independently reviewed quality.
- Matched 24-cell Qwen3-0.6B and Qwen3-1.7B dataset-v2 matrices produced no promotion-eligible cell.
- The policy-ranked 1.7B cell improved validation decision equivalence over 0.6B, 86.09% versus 80.87%, but remained well below the 99% gate.
- The current arbitrary-text application path uses Modal. The offline path is a fixed-fixture stub, not a complete local product backend.
- The final Gate 1 GGUF did not receive the same broad product-clinical evaluation as the merged checkpoint.

### 3.4 Phase 1 weakness ledger

`PROJECT_OWNER_GATE2_BRIEF_2026-09-16` observations are qualitative until the external brief snapshot is stored and hashed. Repository measurements use immutable paths below; rates are accompanied by raw denominators where available.

| ID | Weakness | Measured or observed evidence | Source | Required Phase 2 response |
|---|---|---|---|---|
| P1-01 | Low competition accuracy | Round 1 accuracy 38.18; performance 100.00; efficiency 89.25; total 67.94 | Project-owner brief, snapshot pending | Add standalone capability, self-knowledge, OOD, stability, and medical-safety evaluation |
| P1-02 | Proposition and negation failures | Reversed and invented facts observed; no reliable Phase 1 denominator | Project-owner brief, snapshot pending | Add adversarial minimal pairs, preserve raw errors, and score propositions separately |
| P1-03 | JSON fragility | Malformed output observed; selected SFT nevertheless had 143/143 parse and schema validity on closed TEST, so the judge-facing failure is not quantified by that suite | Brief; `experiments/evaluation/qwen3-0.6b-one-shot-test-v1/aggregate_report_final_v2.json` | Train strict extraction mode and measure raw protocol, parse, schema, and repaired validity separately |
| P1-04 | Project hallucination | TensorRT, ONNX, and TPU claims observed; denominator unavailable | Project-owner brief, snapshot pending | Add a frozen factual card, trap questions, and reviewed scoring |
| P1-05 | Weak mode identity | Bounded-role confusion observed; Phase 1 had no explicit dual-mode suite | Project-owner brief; absence documented by this plan | Introduce a dual-mode contract and marker-abuse gates |
| P1-06 | OOD overconfidence | Unsupported language/domain fabrication observed; denominator unavailable | Project-owner brief, snapshot pending | Train and evaluate uncertainty, scope refusal, and safe escalation |
| P1-07 | Instability | Similar-prompt inconsistency observed; no repeated-prompt Phase 1 denominator | Project-owner brief, snapshot pending | Repeat fixed prompts and score proposition, safety, and mode stability |
| P1-08 | Management decision gap | Selected SFT closed TEST: 139/143 exact/decision, 140/143 management, 141/143 urgent action, 142/143 referral despite 99.89% field accuracy | `aggregate_report_final_v2.json` | Perform field-to-decision attribution and targeted remediation |
| P1-09 | Pidgin weakness | Selected SFT Pidgin TEST: 28/31 exact/decision, 29/31 management, 30/31 urgent action/referral; later source generation recorded repeated Pidgin polarity, omission, and fabrication defects | `aggregate_report_final_v2.json`; `docs/structured_extraction_bulk_t3_*review.md` | Add reviewed Pidgin hard cases and retain per-style hard gates |
| P1-10 | Missing held-out styles | The 5,666 promoted TRAIN-only rows are 1,854 clinical-standard English, 1,865 natural conversational English, and 1,947 subjectless/unpunctuated shorthand; VALIDATION remains 115 and TEST 143 from the older four-style line | `manifest.json` and `duplicate_report.json` under `data/training_sources/structured_extraction_seven_style_v2/` | Create fresh parent-separated validation and TEST evidence for every claimed style |
| P1-11 | Duplicate-heavy expansion | Promoted wave: 5,666 rows, 2,823 unique texts, 2,843 duplicate rows, 693 duplicate groups, maximum multiplicity 59 | `data/training_sources/structured_extraction_seven_style_v2/duplicate_report.json` | Report unique text, parent, template, and effective sampling weight |
| P1-12 | No eligible v2 checkpoint | 0/24 eligible 0.6B cells and 0/24 eligible 1.7B cells on 115 validation examples; policy-ranked decision equivalence was 93/115 and 99/115 respectively | Both `experiments/training/matrices/*-seven-style-sft-matrix-v2/leaderboard.json` files | Diagnose data/objective errors before broad tuning |
| P1-13 | Confounded base comparison | Original base received an under-specified prompt; post-hoc schema-informed base was 0/143 parse/schema valid and is supplementary, not untouched | `docs/qwen3_0_6b_base_control_methodology_correction_v1.md`; TEST report | Run matched base and fine-tuned prompts on the fresh Gate 2 suite |
| P1-14 | Deployment evidence mismatch | Final Gate 1 GGUF lacked the merged checkpoint's complete clinical evaluation | `docs/adtc_submission_and_asus_profiling_handoff_v1.md` | Evaluate the exact GGUF through the final prompt, parser, and backend path |
| P1-15 | Incomplete local application | Arbitrary text uses Modal; offline mode is a fixture stub | Current backend implementation and README | Implement a pinned local `llama.cpp` extractor backend |
| P1-16 | Process failures | Late video-audio and placeholder-prompt failures observed; denominator not applicable | Project-owner brief, snapshot pending | Require early fallback, video playback audit, fresh clone, and human signoff |

## 4. Product architecture and non-goals

The architecture remains neuro-symbolic:

```text
free-form clinical speech or text
        |
        v
LLM language understanding and structured extraction
        |
        v
schema and semantic validation
        |
        v
deterministic completeness checks
        |
        v
deterministic IMCI rules engine
        |
        v
classification, referral, management, and follow-up presentation
```

The LLM is not the authoritative clinical decision-maker. It must not be trained to emit treatment or classification fields inside the extraction payload merely to improve judge-facing answers.

Phase 2 non-goals are:

- production medical-device authorization;
- autonomous diagnosis or treatment;
- silent expansion to unsupported IMCI pathways;
- changing clinical rules solely to fit model outputs;
- reopening or tuning against the closed Gate 1 TEST;
- reporting synthetic or project-owner review as qualified PHC-worker field validation;
- selecting a model solely on throughput; and
- treating parameter count, row count, or training loss as success criteria.

## 5. Dual-mode model contract

### 5.1 Contract identity

The initial Phase 2 contract identity is:

`edge-imci-dual-mode-model-contract-v1`

The working extraction wrapper is frozen for initial dataset and backend implementation as:

```text
<EDGEIMCI_EXTRACT_V1>
{encounter_text}
</EDGEIMCI_EXTRACT_V1>
```

The braces above describe substitution and are not sent literally. The backend must preserve the opening tag, newline placement, payload, closing newline, and closing tag exactly. If implementation testing requires a material syntax change, create a new contract version and regenerate affected training/evaluation examples. Do not silently modify the marker after training starts.

The backend must reject or deterministically escape literal control markers inside user-supplied content so arbitrary text cannot terminate or activate the wrapper accidentally.

### 5.2 Default/free-form mode

Without the extraction marker, the model should:

- respond in normal text rather than JSON by default;
- accurately describe EdgeIMCI's architecture, model role, offline objective, runtime choices, limitations, and intended users;
- preserve propositions and negations;
- respond sensibly to straightforward healthcare questions without claiming autonomous authority;
- recognize obvious emergency or danger situations and recommend appropriate urgent help;
- distinguish known information from unknown information;
- avoid invented diagnoses, capabilities, benchmarks, implementation details, and project history;
- acknowledge unsupported languages and unavailable information;
- handle unrelated, malformed, ambiguous, or out-of-scope requests gracefully; and
- use bounded uncertainty rather than confident fabrication.

The objective is competent, grounded, safety-oriented behavior, not a general autonomous medical chatbot.

### 5.3 EdgeIMCI extraction mode

With the exact marker, the model must:

- interpret only the enclosed content as encounter material;
- return the pinned model-facing encounter representation;
- emit one JSON object and no conversational prose;
- avoid classifications, prescriptions, treatment advice, rule IDs, or evaluator reasoning;
- preserve positive, negative, unknown, omitted, and contradictory findings;
- avoid guessing absent information; and
- conform to the pinned schema.

### 5.4 Mode failures

The following are first-class failures:

- JSON emitted without the marker when normal prose is expected;
- prose, markdown fences, explanations, or treatment emitted with the marker;
- marker activation from partial, malformed, or user-quoted marker text;
- free-form data degrading extraction behavior;
- extraction training making free-form behavior unusably rigid; and
- small wrapper formatting changes causing uncontrolled semantic changes.

## 6. Backend contract

The production extraction path must be:

```text
front end or transcribed speech
        |
        v
backend validates input and adds the exact extraction wrapper
        |
        v
local llama.cpp model
        |
        v
raw-output capture
        |
        v
JSON parser
        |
        v
safe deterministic serialization repair
        |
        v
model-facing schema validation
        |
        v
deterministic adapter and IMCI engine
```

Users must never add the extraction marker manually. Training, evaluation, and backend code must share one machine-readable contract artifact rather than copying prompt text independently.

The local backend must pin:

- GGUF SHA-256;
- base and fine-tuned lineage;
- `llama.cpp` revision and build identity;
- chat template and system instruction;
- extraction wrapper version;
- context, batch, thread, seed, temperature, and generation settings;
- parser and repair-policy version; and
- schema, completeness, and clinical-rule identities.

The backend must fail closed. Invalid or semantically ambiguous extraction must not reach the clinical engine as repaired fact.

## 7. Dataset redesign

### 7.1 Release boundary

Create an immutable release with working identity:

`edge-imci-gate2-multitask-sft-v1`

This is a successor dataset, not an in-place extension of `structured_extraction_seven_style_v2`. The existing extraction corpus remains a source component with explicit provenance.

### 7.2 Training families

The multitask mixture must contain:

1. Extraction-mode records using the exact versioned wrapper and JSON schema.
2. Proposition and negation adversarial records.
3. EdgeIMCI self-knowledge records.
4. Safe free-form medical competence records.
5. OOD, unsupported-language, ambiguity, and graceful-refusal records.
6. Mode-boundary and marker-abuse records.

Extraction remains product-critical and must receive the dominant effective weight. Mixture percentages are experimental configuration, not assumptions baked into the dataset manifest.

### 7.3 LLM dataset-generation responsibility

The coding agent, operating with a frontier OpenAI model, is the primary generator for the bulk of Phase 2 dataset work that requires LLM judgment or language generation. This includes drafting linguistic variants, adversarial and mode-boundary prompts, self-knowledge question variants, OOD examples, and other candidate records defined by frozen construction policies. A different generator requires an explicit, versioned project-owner decision.

This responsibility does not make the coding agent a source of clinical truth or an approval authority. It must generate from frozen semantic parents, canonical clinical artifacts, the factual project card, and the medical safety source manifest. Extraction targets and other mechanically derivable labels must be exported deterministically rather than authored by the model. Generated records remain candidates until they pass deterministic checks and the required independent human, domain, or clinical review; the generating agent cannot self-approve safety-critical records.

Every generation run must pin the OpenAI model identifier and available revision/snapshot, coding-agent and tool version, system and user prompts, generation settings, source artifact identities and hashes, run time, authorization, raw outputs, acceptance/rejection disposition, and token/cost records where applicable. A change of model, material prompt, source boundary, or generation policy creates a new run/config identity. This assignment does not itself authorize a remote API call, paid usage, bulk execution, or relaxation of review gates.

### 7.4 Extraction coverage

Include:

- straightforward positives and explicit negatives;
- multiple negations and scoped negation;
- omissions, unknowns, ambiguity, and contradictions;
- long encounters and irrelevant conversational material;
- reordered findings and paraphrases;
- noisy typed or transcribed speech;
- appropriate code-switching;
- partially complete categories;
- closely related concepts that must not be conflated; and
- every claimed language/input style in TRAIN, VALIDATION, and the new sealed TEST.

### 7.5 Negation and proposition minimal pairs

Required distinctions include:

- blood in stool versus no blood in stool;
- drinking normally versus unable to drink;
- convulsing now versus history of convulsion;
- lethargic versus not lethargic;
- sunken eyes versus no sunken eyes;
- restless versus not restless; and
- fever versus no fever.

Minimal pairs must preserve all non-target facts so polarity sensitivity can be measured directly.

### 7.6 Self-knowledge truth source

Self-knowledge records must be generated from a frozen factual project card covering:

- what EdgeIMCI does;
- why an LLM is used;
- why deterministic clinical logic is retained;
- extraction and completeness architecture;
- offline operation and actual runtime;
- limitations and unsupported claims;
- intended users;
- incomplete information behavior; and
- why treatment authority is not delegated to the model.

Do not train aspirational or false implementation facts as if they already exist.

### 7.7 Free-form medical safety source

Free-form medical data is prohibited until a versioned source-and-review manifest exists. Initial scope is limited to source-grounded IMCI danger recognition, uncertainty, scope statements, and urgent escalation. It does not authorize free-form diagnosis, dosing, prescriptions, or treatment advice beyond approved clinical sources.

The manifest must pin source documents and digests, included and excluded behaviors, target-authoring rules, refusal/escalation policy, reviewer qualifications, adjudication procedure, licenses, and record provenance. Every safety-critical target requires independent clinical review; disagreements remain ineligible until adjudicated. Any scope, source, target policy, or review-policy change creates a new manifest version.

### 7.8 Split and contamination policy

- Split by semantic parent before creating variants.
- Group minimal pairs and paraphrase families so they cannot cross partitions.
- Group self-knowledge question templates by intent, not wording alone.
- Keep the new TEST sealed and separately authorized.
- Keep Gate 1 TEST records historical and ineligible for Gate 2 selection.
- Detect exact, normalized, semantic-parent, and template leakage.
- Report total rows, unique texts, semantic parents, duplicate groups, and effective sampling weight.
- Keep training examples out of the standalone/judge-facing held-out suite even when answers are factual.

## 8. Evaluation suite

The evaluation suite must be built and frozen before final checkpoint selection.

### 8.1 Product-critical extraction

Measure:

- proposition-level accuracy;
- positive and negative finding preservation;
- negation-scope accuracy;
- omission and unknown preservation;
- contradiction handling;
- long-context and irrelevant-material behavior;
- per-style and per-concept results;
- raw JSON validity;
- JSON validity after safe repair;
- schema validity;
- exact and field accuracy;
- deterministic-engine compatibility;
- decision, urgency, urgent-action, referral, and management equivalence; and
- time to first valid structured result, including retries.

### 8.2 Mode separation

Measure:

- extraction activation with the exact marker;
- normal behavior without it;
- partial, quoted, nested, malformed, and whitespace-varied markers;
- prose leakage into tagged output;
- JSON leakage into free-form output; and
- behavior under user content containing marker-like strings.

### 8.3 Standalone and judge-facing capability

Include held-out questions about:

- what EdgeIMCI is and is not;
- system architecture and model responsibility;
- offline/edge implementation;
- incomplete data and uncertainty;
- limitations and supported scope;
- design rationale; and
- basic medical safety and obvious danger situations.

Include explicit false-premise traps about TensorRT, ONNX, TPUs, cloud dependencies, model size, clinical authorization, and unsupported pathways.

### 8.4 OOD behavior

Include:

- unsupported languages;
- garbled or impossible input;
- unrelated prompts;
- unsupported clinical domains;
- ambiguous requests; and
- questions requiring unavailable information.

Score uncertainty, scope recognition, non-fabrication, and safe escalation separately.

### 8.5 Stability

Repeat selected prompts across pinned runs and allowed decoding settings. Preserve raw generations and measure:

- exact stability where deterministic output is required;
- proposition-level consistency;
- clinical-safety consistency; and
- mode consistency.

### 8.6 Matched controls

Every serious model family must receive the same complete prompt/schema treatment in base and fine-tuned evaluations. The Gate 1 base-control mistake must not recur.

### 8.7 Draft acceptance gates

These thresholds are the initial values to freeze before viewing candidate results. Any approved change requires a versioned decision record.

| Gate | Initial threshold |
|---|---:|
| Extraction coverage | 100% |
| Repaired JSON and schema validity | 100% |
| Raw JSON validity | At least 99.5% |
| Global field accuracy | At least 99.5% |
| Global decision equivalence | At least 99.0% |
| Global urgency equivalence | At least 99.5% |
| Global and per-style urgent-action equivalence | 100% |
| Global and per-style referral equivalence | 100% |
| Global management equivalence | At least 99.0% |
| Critical negation minimal-pair accuracy | 100% |
| Unknown and omission preservation | 100% on critical cases; at least 99.5% overall |
| Contradiction handling | 100% safe rejection/flagging; no silent resolution |
| Exact-marker extraction activation | 100% |
| Tagged-output JSON-only compliance | At least 99.5% raw, 100% after safe repair |
| Free-form mode leakage | At most 1.0% |
| Explicit implementation-fact trap accuracy | 100% |
| Overall EdgeIMCI factual-card accuracy | At least 98.0% |
| Medical-safety critical items | 100% clinically acceptable with zero unsafe advice |
| OOD non-fabrication and scope handling | At least 95% |
| Deterministic-setting semantic stability | At least 99% |
| Retry rate | At most 1.0%; no retry may conceal a safety-critical first response |
| Runtime completion without crash/OOM | 100% of qualification runs |
| Peak process RSS on 8 GB target | At most 6.5 GiB |
| P95 end-to-end extraction latency | At most 15 seconds on the target profile |
| Sustained generation throughput | At least 5 tokens/second on the target profile |
| Peak temperature | Below 85 C |

Before candidate evaluation, freeze at least 600 extraction examples, including at least 50 per claimed style and 50 each for negation, unknown/omission, contradiction, and marker abuse. Freeze at least 150 self-knowledge/fact-trap items, 100 OOD items, 300 mode-boundary items, 300 repeated-prompt stability comparisons, and 60 clinically reviewed medical-safety items. Cases may contribute to more than one declared stratum, but semantic parents and prompt templates cannot cross partitions.

Two reviewers independently score subjective free-form items against a frozen rubric. Every safety disagreement and a stratified 20% sample of other items require adjudication by the evaluation owner or delegated qualified reviewer. Report inter-rater agreement, disagreement counts, adjudication changes, raw numerators/denominators, and exact 95% confidence intervals.

Observed zero-tolerance gates pass only with zero failures; confidence intervals still qualify the uncertainty. For minimum-success-rate gates, the one-sided 95% lower confidence bound must meet the threshold. For maximum-failure-rate gates, including leakage and retries, the one-sided 95% upper confidence bound must not exceed the threshold. These rules and minimum sample counts define adequate statistical margin. Runtime margin additionally requires P95 latency and peak RSS to be at least 20% inside their limits. A candidate that meets a point threshold without the required margin is `BORDERLINE`, not selected unless the project owner records a justified exception before TEST access.

## 9. Safe deterministic repair

Track raw and repaired validity separately.

Allowed repair is limited to unambiguous serialization normalization, such as:

- removing markdown fences around one otherwise valid object;
- removing a trailing comma where the parse is unique;
- normalizing whitespace;
- normalizing a predeclared enum casing alias; and
- applying explicitly defined defaults only to optional, non-clinical metadata.

A raw mode-contract violation remains a protocol failure even if its JSON payload can be recovered. For example, removing markdown fences may improve repaired parse validity, but it does not make the original tagged response JSON-only compliant.

Repair must never:

- infer a symptom, sign, measurement, duration, qualifier, or clinical state;
- convert omitted information to negative;
- resolve a contradiction;
- choose among multiple plausible enum meanings;
- add classifications, referrals, or treatments; or
- make invalid clinical content appear valid.

If repair requires semantic guessing, reject, retry under the pinned policy, or preserve the field as unknown when the schema and evidence permit it.

## 10. Initial model-capacity experiment

The first serious Phase 2 experiment compares:

- Qwen3-0.6B;
- Qwen3-1.7B; and
- Qwen3-4B.

The 4B candidate is a capability ceiling, not a presumed winner.

All three must first pass Gate A in `target_device_model_runtime_qualification_plan.md`. Admitted candidates then use:

- the same frozen multitask release;
- the same train and validation partitions and the same sealed TEST specification;
- the same task-family objectives and effective mixture;
- equivalent LoRA or QLoRA SFT recipes where hardware permits;
- one predeclared primary seed and, if budget permits, one replication seed;
- matched generation settings; and
- the same evaluation and ranking policy.

The initial capacity comparison and any corrective round use VALIDATION only. The sealed TEST is not part of the September 18-20 model comparison. After all corrective work ends, select and freeze one final candidate overall from VALIDATION and exact-artifact qualification evidence. The project owner may then authorize one one-shot TEST audit of that candidate. TEST results cannot be used to return to another model family. No model, data, wrapper, repair, schema, or threshold change is permitted after unsealing.

Do not begin with a large hyperparameter sweep. The first question is whether capacity changes the required behaviors when data and evaluation are held constant.

Interpretation policy:

- If 1.7B nearly matches 4B and clears gates, prefer 1.7B for deployment efficiency.
- If 4B substantially outperforms both smaller models, capacity is a measured bottleneck.
- If all sizes fail the same items, investigate dataset labels, task mixture, prompt contract, or evaluation before increasing model size.
- If extraction improves while free-form behavior regresses, adjust mixture or objective rather than selecting on aggregate score.
- Do not assume more epochs are beneficial. Monitor per-family validation behavior and stop on clinically relevant regression.

## 11. Fine-tuning strategy

The default method remains LoRA/QLoRA supervised fine-tuning. Full-parameter training, preference optimization, or RL requires evidence that SFT and data correction cannot address a specific measured failure.

Each training run must pin:

- base model repository and immutable revision;
- tokenizer revision;
- data release and mixture configuration;
- task-family weights;
- LoRA/QLoRA target modules and hyperparameters;
- optimizer, schedule, precision, sequence length, and seed;
- software image and dependency lock;
- source repository commit and clean-worktree state;
- checkpoint and adapter hashes; and
- per-family training and validation metrics.

## 12. Model selection

Select the smallest candidate that clears all capability, reliability, safety, and runtime gates with adequate margin.

Selection order is:

1. Hard safety, schema, mode, and provenance gates.
2. Product extraction and deterministic decision equivalence.
3. Standalone capability, grounding, OOD behavior, and stability.
4. Exact-GGUF quality preservation.
5. Runtime feasibility on ADTC-like hardware.
6. Latency, throughput, memory, model size, and thermal margin.

Performance and efficiency may be traded for a substantial accuracy improvement because Round 1 already demonstrated large performance headroom. A simplistic model must not be selected merely because throughput is high.

## 13. Runtime and deployment constraints

The final candidate must use:

- GGUF format;
- `llama.cpp` only;
- fully offline inference;
- no network dependency during evaluation;
- a standard-laptop target of 8 GB RAM, 4 vCPU, Intel i5 10th-12th generation, and integrated graphics;
- a static, plainly readable final model URL in `download_model.sh`;
- no OOM or runtime crash; and
- operation below the 85 C thermal penalty threshold.

The organizer-requirements audit must confirm the permitted CPU families, architecture, operating system, storage, profiler, and scoring constraints. The internal baseline in the project-owner brief is 8 GB RAM, 4 vCPU, Intel i5 10th-12th generation, and integrated graphics. Do not silently broaden or narrow that target from memory.

Each qualification unit is the exact tuple:

```text
checkpoint + GGUF digest + quantization + llama.cpp revision/build
+ chat template + extraction contract + generation settings
+ backend/parser/repair versions + hardware/OS
```

Q8, Q6, and Q4 are different artifacts and require separate quality/runtime evidence. Do not infer final-GGUF quality from the merged Modal checkpoint.

## 14. Version boundaries

| Boundary | Phase 1 identity | Phase 2 boundary and trigger |
|---|---|---|
| Campaign | `edgeimci-hackathon-campaign-v1` | Create `edgeimci-adtc-2026-gate2-v1`; never repurpose old experiment rows |
| Dual-mode contract | Extraction-only implicit behavior | `edge-imci-dual-mode-model-contract-v1`; bump on marker, mode responsibility, or output behavior change |
| Training dataset | Campaign v1 and seven-style v2 | `edge-imci-gate2-multitask-sft-v1`; new release for source rows, labels, deduplication, split, or eligibility changes |
| Mixture configuration | No multitask mixture identity | New versioned config for task-family weights and sampling; weight changes create a new experiment/config, not new immutable source rows |
| Training record schema | Structured extraction record v1 | Create a multitask envelope schema v1 with task family, mode, source, and target; keep extraction targets separately schema-validated |
| Model-facing encounter schema | `model_facing_encounter_v1` | Keep v1 unless fields, requiredness, enums, null semantics, or pathway representation change |
| Clinical rules | Rules v1, completeness v2, deterministic oracle v3 | Keep frozen unless a source-reviewed clinical change is approved |
| Project factual card | No frozen standalone-model truth card | Create factual card v1; bump when shipped architecture, model, runtime, limitations, or capability facts change |
| Free-form medical safety source | No Gate 2 source policy | Create safety source/review manifest v1; bump for scope, source, target-authoring, or review-policy changes |
| Evaluation | Checkpoint policy v1 and closed TEST v1 | Create Gate 2 policy v1 and a new untouched TEST line; bump for datasets, metrics, thresholds, or candidate treatment |
| Backend | Modal extractor and fixture stub | Add a versioned local `llama.cpp` extractor contract; bump on transport, wrapper, parse, retry, or failure semantics |
| Repair policy | No formal Gate 2 boundary | Create serialization-repair policy v1; bump on any accepted transformation |
| Prompt/chat template | Implicit training/runtime templates | Pin system prompt, chat template, thinking mode, and wrapper; material changes create a new config/contract |
| Model artifact | Gate 1 Q8 tuple | One artifact identity per exact checkpoint/GGUF bytes and quantization |
| Qualification run | Gate 1 ASUS profile | One run identity per artifact, build, settings, workload, hardware, OS, power, and thermal state |
| Official tooling | Gate 1 template/profiler snapshots | Pin Gate 2 submission-template, profiler, and profiler-schema revisions before final evidence |
| Submission package | Gate 1 public package | Pin repository commit, metadata, prompts, report, download script, model URL, video, and receipt |
| Provenance | Existing run schema and scattered handoff artifacts | Keep schema if sufficient; create new Gate 2 campaign, run, candidate, and final-artifact identities |

Filename suffix `v1` denotes the first repository artifact in a lineage. A structured artifact's internal `1.0.0` uses semantic versioning: increment MAJOR for incompatible meaning or contract changes, MINOR for backward-compatible additions, and PATCH for non-semantic corrections. Dataset releases, experiments, runs, model artifacts, qualification runs, and submission packages are immutable identities rather than mutable semantic versions. Every successor artifact must record lifecycle, accountable owner, predecessor, source path, and SHA-256 where applicable.

### 14.1 Clinical logic change control

A data or model change is not a clinical-logic version. Any proposed deterministic logic change requires:

1. source citation and rationale;
2. explicit scope and clinical review;
3. a new canonical artifact version;
4. golden-suite regeneration and review;
5. regression tests and migration notes;
6. target regeneration for every affected dataset record; and
7. a new evaluation baseline.

Never patch deterministic logic merely to make model errors score as correct.

### 14.2 Schema change control

Do not create `model_facing_encounter_v2` merely because the model or dataset changes. Create it only if payload semantics change. If it changes, the old and new schema lines must remain separately evaluable and the backend must reject version ambiguity.

## 15. Provenance and reproducibility

For the selected model, `REPORT.md` must include:

- base model and exact source repository;
- immutable base revision and Git commit in `metadata.json`;
- fine-tuning method and exact configuration;
- training datasets, sources, sizes, and licenses;
- at least two base-vs-fine-tuned comparison examples; and
- final GGUF, runtime, and benchmark identities.

It must also retain the required narrative: problem and African PHC context, system constraints, alternatives considered, tool/model rationale, quantization rationale, measured benchmarks, limitations, and safety boundaries.

Use `provenance/` for, where applicable:

- LoRA/QLoRA adapter weights and `adapter_config.json`;
- training scripts, configs, notebooks, and dependency locks;
- logs and loss/metric history;
- dataset description, license, sample, or immutable link;
- base, adapter, merged, and final GGUF SHA-256 values;
- merge, conversion, and quantization scripts;
- hosted notebook execution link; and
- candidate-selection and supersession records.

Capture these during every serious run. Do not reconstruct provenance at the deadline.

No benchmark number may enter `REPORT.md` unless its inputs, artifact identity, runtime settings, hardware, and reproduction command are known. The final repository must run from a fresh checkout.

The canonical submission repository is `https://github.com/Nini0la/edgeIMCI-adtc-2026-submission`; creating a replacement requires project-owner approval. Before final evidence, pin the official submission-template revision, profiler revision, and profiler-schema revision. Preserve organizer audit results separately from participant measurements and retain the profiler-created `submission.json` unchanged with its SHA-256.

## 16. Required submission artifacts

The intended Gate 2 package includes:

- updated GitHub repository;
- compliant `metadata.json`;
- exactly two intentional domain test prompts;
- static `download_model.sh`;
- final downloadable GGUF at the declared URL;
- updated `REPORT.md` with model provenance;
- complete `provenance/` evidence;
- reproducible benchmark artifacts;
- correct `.gitignore` and model-directory handling;
- updated video no longer than two minutes; and
- required external-code/content citations.

The public repository must contain neither GGUF weights nor credentials. `download_model.sh` must be static, credential-free, idempotent, checksum-verifying, and consistent with `metadata.json`'s `_runtime.model_path`. Final metadata must satisfy every required field in the pinned official template, and the participant profiler must complete against the exact submitted GGUF and untouched `submission.json`.

The two test prompts, model URL, metadata, report claims, revisions, and hashes require explicit human signoff.

## 17. Work sequence and deadline plan

### September 16: control-plane freeze

- Approve this plan or record changes.
- Freeze the dual-mode contract and extraction marker.
- Create machine-readable dataset/evaluation/backend contract stubs.
- Freeze the Phase 1 weakness ledger and requirements traceability matrix.
- Identify the Gate 1 package that can seed a fallback and list every Gate 2 compliance gap.
- Resolve the official deadline time, timezone, portal, submitter, template revision, profiler revision, and submission-receipt process.
- Obtain or explicitly deny the Phase 2 compute budget and execution authorizations.

### September 17: data and evaluation freeze

- Build and validate the multitask dataset release.
- Freeze validation and new TEST manifests before model selection.
- Implement shared wrapper and mode-aware evaluation.
- Implement parser/repair instrumentation.
- Add local backend integration behind the existing extractor seam.
- Complete Gate A base candidate-runtime qualification for 0.6B, 1.7B, and 4B; do not train an unadmitted tuple.

### September 18-19: matched capacity experiment

- Train 0.6B, 1.7B, and 4B candidates with the matched initial design.
- Evaluate extraction, mode separation, standalone capability, OOD, stability, and matched base controls on VALIDATION only.
- Maintain a completely valid fallback submission by September 18.
- Record the first complete video and verify its audio and playback.

### September 20: targeted correction and shortlist

- Diagnose shared and model-specific failures.
- Run at most one justified targeted corrective training round if schedule and evidence permit.
- Freeze viable checkpoints.
- Convert/quantize the shortlist and begin exact-GGUF quality evaluation.
- Target final submission content freeze by the end of September 20, approximately 48 hours before deadline.

### September 21: final qualification and audit

- Select the smallest candidate that clears all gates.
- Freeze candidates and obtain explicit authorization before any new TEST is unsealed.
- Run the one-shot TEST policy; make no model, data, prompt, repair, schema, or threshold change afterward.
- Finish ADTC-like hardware profiling.
- Complete report, metadata, provenance, test prompts, download script, citations, and video.
- Perform fresh-clone and second-device/video audits.
- Absolute final-freeze target is at least 24 hours before deadline.

### September 22: submission and buffer

- Make no speculative model, data, or architecture changes.
- Repeat hash, URL, metadata, prompt, report, and video checks.
- Submit with buffer and retain immutable submitted commit/artifact identities.

September 22 is a submission/buffer day, not a construction day.

The exact organizer cutoff time and timezone are unresolved blockers until recorded. All internal freeze targets must be recalculated against that exact cutoff, not merely the calendar date.

## 18. Hard gates

- No serious training before dataset, contract, and evaluation-policy identities are pinned.
- No new TEST access before one final candidate overall is selected from non-TEST evidence, frozen, and explicitly authorized.
- No post-TEST hyperparameter, mixture, prompt, repair, or schema revision.
- No promotion when an urgent-action or referral gate fails.
- No model selection from training loss or ADTC throughput alone.
- No deployment selection without evaluation of the exact GGUF.
- No offline claim while arbitrary-text application inference requires Modal or another network service.
- No Standard Laptop claim from unmatched proxy hardware without qualification language.
- No benchmark publication from a dirty or unidentified repository state.
- No semantic medical repair in the deterministic repair layer.
- No remote provider call without explicit current authorization.
- No submission-critical placeholder without human verification.

## 19. Requirements traceability

| Requirement ID | Brief section | Requirement | Deliverable/evidence | Owner/status | Gate |
|---|---:|---|---|---|---|
| G2-STATE-001 | 1 | Preserve Round 1 diagnosis and scores | Section 3 ledger and pinned source note | Project owner / review pending | No unsupported denominator or rewritten history |
| G2-ARCH-001 | 2 | Preserve neuro-symbolic clinical authority | Contract, backend tests, schema boundary | Engineering / pending | LLM cannot directly control clinical decisions |
| G2-MODE-001 | 3, 8 | Support and separate free-form/extraction modes | Dual-mode contract and held-out mode suite | Engineering / pending | Mode thresholds in Section 8.7 |
| G2-BACK-001 | 4 | Reproduce training contract in backend | Shared machine-readable wrapper and local extractor | Engineering / pending | Byte-identical wrapper and fail-closed path |
| G2-DATA-001 | 5, 7 | Build a balanced multitask dataset | Frozen manifest, sources, licenses, counts, hashes | Data owner unassigned | Leakage/deduplication checks pass |
| G2-MODEL-001 | 6 | Compare 0.6B, 1.7B, and 4B | Matched plans and validation reports | Training owner unassigned | Same initial data/objective/evaluation |
| G2-JSON-001 | 9 | Protect engine from malformed output | Raw parser, safe repair, schema validation | Engineering / pending | Raw/repaired metrics separate; semantic repair prohibited |
| G2-EVAL-001 | 10 | Freeze evaluation before selection | Versioned policy and sealed manifests | Evaluation owner unassigned | No candidate-specific threshold changes |
| G2-SELECT-001 | 11 | Select smallest model clearing gates | Versioned selection report | Project owner / pending | No throughput-only selection |
| G2-RUNTIME-001 | 12 | Run final model offline in GGUF via `llama.cpp` | Exact runtime manifest and network-isolation test | Runtime owner unassigned | No network, crash, OOM, or thermal penalty |
| G2-PROV-001 | 13, 14 | Preserve complete, honest provenance | `REPORT.md`, `metadata.json`, `provenance/` | Provenance owner unassigned | Fresh reviewer can trace base to final GGUF |
| G2-ANTI-001 | 15 | Demonstrate genuine useful capability | Capability/OOD/safety suite and examples | Evaluation owner unassigned | Anti-gaming usefulness review passes |
| G2-SUB-001 | 16 | Supply complete Gate 2 package | Repository, model, report, prompts, video | Human submitter unassigned | Checklist and human signoff complete |
| G2-PROC-001 | 17 | Avoid deadline and placeholder failures | Early fallback, early video, freeze schedule | Project owner / pending | Submission day remains buffer-only |
| G2-SEQ-001 | 18 | Execute the ordered Phase 2 sequence | Dated workboard and immutable phase outputs | Project owner / pending | Hard gates block out-of-order work |
| P2-CHARTER-001 | Internal | Approve Phase 2 charter and resources | Section 2.1 approval record | Project owner / pending | Plan lifecycle becomes `CURRENT` |
| P2-VERSION-001 | Internal | Define independent version boundaries | Section 14 and machine-readable successor artifacts | Engineering / drafted | No silent mutation of Phase 1 lines |
| P2-WEAKNESS-001 | Internal | Pin measured and observed Phase 1 weaknesses | Section 3.4 with sources and raw counts | Evaluation / drafted | No invented metrics; gaps instrumented in Phase 2 |

## 20. Submission safeguards

### 20.1 Valid fallback

The Gate 1 package is a fallback seed, not yet presumed Gate 2 compliant. Its known model identity is Qwen3-0.6B SFT Q8_0, SHA-256 `26d11ee99801455fcef011a3e5ff124b2ff1cce943ed06cbe611c8fbcc42aca2`, hosted from the lineage recorded in `REPORT.md`. Its public repository is `https://github.com/Nini0la/edgeIMCI-adtc-2026-submission`.

By September 18, create and fresh-clone test one explicitly identified fallback commit/package against the current Gate 2 template. Record its repository commit, GGUF URL and digest, metadata version, profiler result, report, prompts, and video. Until that audit passes, no document may call the fallback valid.

### 20.2 Video

Record a complete first video early. Verify:

- microphone and screencast audio;
- visual readability;
- duration;
- final export playback; and
- playback with another device or headphones.

### 20.3 Fresh-clone audit

From a new directory and clean environment:

1. Clone the exact intended submission commit.
2. Run `download_model.sh`.
3. Verify every SHA-256.
4. Run the model and both intentional test prompts.
5. Run the profiler and reproduction commands.
6. Inspect `metadata.json`, model URL, provenance, licenses, and citations.
7. Confirm every report number against an immutable artifact.
8. Build and run the application offline.
9. Watch the final video from beginning to end.

### 20.4 Human signoff

The project owner or explicitly delegated human reviewer must sign off:

- test prompts;
- model identity and revision;
- base, adapter, merged, and GGUF hashes;
- benchmark numbers and hardware claims;
- URLs and download behavior;
- metadata and provenance claims;
- report limitations and safety wording; and
- final video content.

## 21. Risk register and fallback policy

| Risk | Early warning | Mitigation | Fallback |
|---|---|---|---|
| Dataset not ready | Leakage, labels, or licenses unresolved by Sep 17 | Reduce breadth, not review rigor; retain frozen validated subset | Use only the audited Gate 2 fallback; otherwise report the blocker |
| 4B misses runtime budget | OOM, poor thermal margin, or unacceptable latency | Quantize and compare only after checkpoint quality gate | Select smallest passing 0.6B/1.7B candidate |
| All scales fail same cases | Shared error clusters | Correct data/objective/contract once; avoid broad sweep | Submit best valid bounded candidate with transparent limitations |
| Free-form training harms extraction | Extraction or mode regression | Increase extraction weight or separate prompt formatting | Revert to last frozen extraction-safe mixture |
| Repair masks semantic errors | Repaired rate rises while decision quality falls | Audit every repair class and preserve raw output | Disable offending repair rule |
| New TEST is contaminated | Parent/template overlap found | Rebuild before unsealing | Do not claim final held-out result |
| Provenance incomplete | Missing hash/log/config during run | Fail run completeness immediately | Candidate becomes ineligible |
| Local backend remains networked | Modal call or download during evaluation | Add network-isolation test and local extractor | Demo prior valid offline GGUF path, not cloud application |
| Video/report delayed | No complete draft by Sep 18-19 | Freeze first acceptable version early | Submit verified fallback assets |
| Submission placeholder survives | Human checklist incomplete | Block release commit until signoff | Do not submit until verified or use known-good fallback |

## 22. Change control

- Historical Gate 1 evidence is append-only and immutable.
- A material requirement or strategy change creates a new document version.
- A material scientific change creates a new config, release, experiment, or candidate identity.
- Threshold changes after candidate results are visible require an explicit deviation record and cannot retroactively qualify a failed run.
- TEST authorization, public model hosting, public pushes, and final submission remain explicit project-owner decisions.
- At closeout, record completed, superseded, deferred, rejected, and fallback branches.

## 23. Immediate next artifacts

This working plan authorizes planning and implementation preparation, not remote calls, paid training, TEST unsealing, deployment, or clinical use. The next machine-readable artifacts should be:

1. Dual-mode model contract v1.
2. Gate 2 multitask record schema v1.
3. Gate 2 dataset construction and mixture config v1.
4. Gate 2 evaluation policy v1 with frozen thresholds.
5. Backend extraction-wrapper and repair policy v1.
6. Matched 0.6B/1.7B/4B initial experiment plan.
7. Requirements and submission checklist with named owners and status.
