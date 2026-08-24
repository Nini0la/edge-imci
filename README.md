# EdgeIMCI

EdgeIMCI is a hackathon research project testing whether a small, locally deployable language model can normalize free-form primary-health-care findings from a whole sick-child encounter into canonical structured encounter state. The existing deterministic clinical pipeline then checks completeness and produces the supported IMCI classifications and management actions.

The target interaction is:

```text
free-form whole-encounter PHC findings
        |
        v
small EdgeIMCI structured extractor
        |
        v
model-facing encounter JSON
        |
        v
schema + deterministic completeness/IMCI engine
        |
        v
integrated classifications, actions and presentation
```

This repository is research software. It is **not** a production medical device, does not authorize autonomous clinical use, and does not claim coverage of every IMCI pathway or follow-up algorithm.

## Current status

The clinical-semantic foundation for the bounded hackathon scope is implemented. The 78-case product-level holistic semantic suite has undergone two technical/source review cycles, oracle-v3 remediation, explicit human/domain approval, and a controlled semantic freeze. Its exact approved content is hash-pinned; the current gate is to establish and review the golden language renderings without changing those semantics.

| Area | Status |
| --- | --- |
| Major sick-child clinical rule set and provenance | Implemented and versioned |
| Whole-encounter schema | Implemented |
| Mechanical completeness oracle | Implemented and deterministic |
| Integrated classification/action oracle | Deterministic oracle v3; technical/source verification passes |
| Clinical/policy review | All 13 original questions plus the source-literal oxygen-referral disposition are resolved and versioned |
| Automated verification | Full deterministic suite maintained in `tests/` |
| Archived selected-v0 14-case component slice | Frozen historical/component-regression artifact; product-ineligible |
| Product-level holistic golden semantic set | 78 cases approved and hash-frozen for bounded hackathon use; never direct training data |
| Golden language renderings | Preserved as product-language references and downstream presentation artifacts |
| Model-facing encounter contract | v1 schema, deterministic frozen-source projection and engine adapter implemented for review |
| Structured-extraction evaluation | Schema, exact/field/UNKNOWN and downstream decision-equivalence metrics implemented for review |
| Extraction dataset policy | Parent-case split inheritance and scope/acquisition/reassessment/contradiction decisions approved and versioned; bulk generation/training still unauthorized |
| Structured-extraction canary | Three reviewed existing PHC submissions paired with deterministic JSON targets; validated for review, not training-authorized |
| Experiment/run registry infrastructure | Implemented with versioned registry, immutable run sidecars, accounting, and profiling support |
| Bulk corpus generation | Not started |
| SFT/model training | Not started |
| Pre-fine-tuning ASUS candidate model-runtime admission | Planned; protocol defined, exact candidates/runtime/checksums/thresholds unresolved |
| Post-training ASUS deployment-artifact requalification | Not started; must reuse the frozen admission harness for paired evidence |

The approved review decisions are canonical in [`imci_major_sick_child_review_decisions_v1.json`](configs/information_policy/imci_major_sick_child_review_decisions_v1.json), with a generated YAML mirror. This approval is limited to the project’s hackathon representation and is not production clinical authorization.

The later oxygen-referral disposition is canonical in [`imci_major_sick_child_oxygen_referral_disposition_v1.json`](configs/information_policy/imci_major_sick_child_oxygen_referral_disposition_v1.json). It preserves the source wording as non-urgent referral: saturation below 90% does not independently activate `IP-CQ-004` or suppress other applicable actions.

## Supported encounter scope

`imci-major-sick-child-v1` covers the initial sick-child assessment for children aged 2 completed months to under 5 years across:

- general danger signs;
- cough or difficult breathing;
- diarrhoea;
- fever, including measles; and
- ear problem.

It is paired with `imci-major-sick-child-holistic-completeness-v2`. Omitted findings remain `UNKNOWN`; silence is never treated as a negative finding.

The product-level behavior is:

```text
COMPLETE SUPPORTED ENCOUNTER
→ emit integrated classifications and management

INCOMPLETE, NO KNOWN URGENT FINDING
→ report grouped missing assessment elements
→ withhold final holistic synthesis

INCOMPLETE, KNOWN URGENT FINDING
→ emit source-backed urgent/pre-referral actions immediately
→ report the remaining rapid assessment
→ withhold final holistic synthesis
```

Urgency does not make the encounter complete. The remaining supported assessment must be completed rapidly without delaying referral or pre-referral treatment. When urgent referral is triggered, routine home-care courses and scheduled follow-up are deferred from the immediate workflow unless the source explicitly makes them pre-referral or transfer actions.

The current scope is the **initial assessment only**. It may state source-backed follow-up timing, but it does not execute later IMCI follow-up-visit algorithms.

## Clinical source and provenance

The EdgeIMCI rule sets are machine-readable artifacts derived from **WHO — Integrated Management of Childhood Illness, Chart Booklet, March 2014**. They are not WHO-authored machine-readable rule sets.

The expanded rule set uses PDF viewer pages 5–9 and linked treatment/reassessment pages. Every encoded logic unit records source provenance. The WHO PDF is not redistributed; obtain it separately and place it at:

```text
data/sources/IMCI chartbooklet 2014.pdf
```

See [`data/sources/README.md`](data/sources/README.md), [`major_sick_child_expansion_map_v1.md`](docs/major_sick_child_expansion_map_v1.md), and [`clinical_questions.md`](docs/clinical_questions.md).

The older `imci-selected-v0` rule set remains frozen as a historical development/regression substrate. It covers only general danger signs, selected cough/difficult-breathing logic, and dehydration classification. It must not be described as the complete IMCI respiratory or diarrhoea algorithm.

## Learned/deterministic architecture

The model owns language interpretation, not clinical decision authority:

```text
free-form PHC findings
        |
        v
EdgeIMCI extractor
        |
        v
model-facing encounter JSON
        |
        +-- schema / validity checks
        +-- deterministic completeness policy
        +-- deterministic IMCI evaluator
        +-- deterministic classifications and actions
        +-- worker-facing presentation
```

The model-facing target excludes classifications, urgency, referral, treatments, rule IDs, evaluator traces, provenance and presentation text. `null` means `UNKNOWN`, never negative. See the [architecture impact note](docs/structured_extraction_architecture_impact_v1.md) and versioned [model-facing JSON Schema](configs/model_io/model_facing_encounter_v1.schema.json).

## Install and test

Python 3.10 or newer is required.

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

The canonical clinical and policy artifacts are JSON. Their YAML files are generated, human-readable mirrors. Regenerate the expanded mirrors with:

```bash
python scripts/sync_holistic_artifacts.py
```

Tests reject JSON/YAML drift, unknown evaluator rule IDs, invalid scope pins, incomplete decision sets, and relevant clinical/completeness regressions.

## Current data gate: structured-extraction corpus calibration

The frozen `edge-imci-holistic-product-golden-v1` suite contains 78 structured cases using `corpus_role=HOLISTIC_PRODUCT_GOLDEN`. It is canonical as JSONL with a YAML mirror, pins the approved clinical/policy/oracle identities, and is mechanically recomputed by `edge-imci-holistic-golden-validator-v4`.

Each structured golden case should pin:

- complete encounter observations and explicit unknowns;
- supported-encounter completeness;
- simultaneous classifications across pathways;
- urgent, intermediate, deferred, and final actions;
- grouped missing elements for incomplete cases;
- exact rule/action traces and provenance; and
- any applicable approved review decision.

The proposed set includes complete encounters, every encoded classification family, multiple simultaneous conditions, explicit-negative/omission twins, urgent-incomplete cases, respiratory reassessment, initial Plan B/C behavior, malaria contexts, HIV/chest-indrawing, cholera, measles, ear boundaries, contradictions, and schema-rejected out-of-scope cases.

`HPG-GAP-REASSESS-001` is resolved by the versioned product-scope disposition `edge-imci-holistic-golden-scope-dispositions-v1`. Holistic golden v1 covers the initial dehydration classification, Plan B/C action, and timed-reassessment instruction. It does not execute longitudinal treatment state or automatic plan loops; a later full updated assessment may be submitted and evaluated afresh. This is an interaction/product-scope decision, not a new clinical rule.

The first review’s four findings and the second review’s three respiratory findings are closed in oracle v3. The reviewed semantic hash was explicitly accepted by the project domain owner and transformed into a frozen v4 record envelope without changing any clinical expectations. The approval record preserves both hashes and authorizes the frozen suite for golden-language generation, product evaluation, and teacher bake-off—not direct training or production clinical use.

The frozen language layer remains useful, but it is no longer the primary SFT label. The teacher continues to generate only semantically faithful PHC-worker submissions and fact-evidence annotations. Each accepted submission is paired with a model-facing target exported deterministically from the same frozen semantic case. Existing valid language is therefore reusable without another teacher call; frozen assistant responses remain presentation references.

Dataset variants are split by parent semantic encounter under [`structured_extraction_dataset_policy_v1.json`](configs/training/structured_extraction_dataset_policy_v1.json). Every paraphrase inherits its parent's partition. Cases 77 and 78 remain out-of-scope TEST parents. The distinct TRAIN parents `oos-extract-young-respiratory-001` and `oos-extract-older-fever-001` are ready as extraction-only structured sources; their language generation/review has not started.

## Experimental campaign

The hackathon critical path is evidence-driven:

1. approve the golden-language rendering contract and a small manually reviewed calibration set;
2. render and review the complete 78-case golden language layer;
3. run 4–6 teacher/prompt bake-off runs over the same frozen semantic cases;
4. select a stable generation recipe with high semantic acceptance and no systematic corruption;
5. generate a fast corpus of approximately 500–1,000 accepted examples;
6. freeze candidate, runtime, checksum, ASUS, workload, scoring and admission-threshold identities, then qualify each base candidate-runtime combination on the ASUS;
7. admit only viable combinations, assemble canonical language-to-JSON records, authorize a dataset split, and fine-tune the selected admitted parent on Modal;
8. launch the larger Azure Batch data lane in parallel when justified;
9. run structured-extraction metrics plus downstream deterministic decision-equivalence evaluations;
10. convert or quantize the selected fine-tuned checkpoint and rerun the same frozen qualification on the same ASUS; and
11. select/submit or take only the branch justified by the paired before-and-after evidence.

SFT-v2, Qwen3-4B, Qwen3.5/Tinker, preference optimization or RL, SVD/compression, expanded quantization comparisons, and Lundin evaluation are conditional branches. They are not prerequisites for the first submission.

The operating plans are:

- [`experimental_campaign_map.md`](docs/experimental_campaign_map.md)
- [`synthetic_data_generation_experiment_plan.md`](docs/synthetic_data_generation_experiment_plan.md)
- [`experiment_operations_and_tracking_plan.md`](docs/experiment_operations_and_tracking_plan.md)
- [`target_device_model_runtime_qualification_plan.md`](docs/target_device_model_runtime_qualification_plan.md)
- [`experiments/README.md`](experiments/README.md)

Before the campaign expands, each generation, training, evaluation, and profile runner should automatically create a versioned run sidecar containing configuration identity, inputs, outputs, hashes, telemetry, status, and raw provider usage. Scientific results must remain distinguishable from execution time and derived cost.

## Historical v0 regression assets

The committed `data/benchmark/imci_v0.jsonl` is an exposed 82-case development/regression set. It is not an untouched final benchmark and must never be used as future training data. Regenerate it deterministically with:

```bash
python scripts/generate_benchmark.py \
  --output data/benchmark/imci_v0.jsonl \
  --seed 20240301
```

The historical 14-case `LEGACY_SELECTED_V0_COMPONENT_REGRESSION` slice remains fixed as an archived component regression suite for selected-v0 semantics, information states, acquisition modes, and controlled semantic-to-language conversion. It is not the new product-level holistic golden set and is mechanically ineligible for training, holistic generation, product evaluation, and new teacher selection.

The committed split demonstration proves group-aware leakage controls, but is not the eventual training, validation, or benchmark corpus:

```bash
python scripts/generate_splits.py
```

## Baseline and external-evaluation tooling

The mock runner exercises serialization, prompting, strict scoring, and run-artifact generation without invoking a model:

```bash
python scripts/run_baseline.py \
  --benchmark data/benchmark/imci_v0.jsonl \
  --output experiments/baselines/mock-run/
```

Pinned local MLX Qwen baselines remain useful historical/component evidence. Install the optional model dependencies and run, for example:

```bash
python -m pip install -e ".[models]"

python scripts/run_model_baseline.py qwen3-0.6b \
  --output experiments/baselines/qwen3-0.6b/internal-v0
```

`configs/external_benchmarks.json` pins two Lundin IMCI benchmark revisions without redistributing them. Lundin is now optional external/generalization evidence and is intentionally off the hackathon critical path. Fetch a pinned revision with:

```bash
python scripts/fetch_external_benchmark.py lundin_current_07c6f0f
```

External results must identify the pinned revision and one of the repository’s separated strict or upstream-compatibility scoring policies. Do not merge Lundin scores with EdgeIMCI product metrics into a single accuracy figure.

## Repository map

Documentation authority and lifecycle are defined in [`docs/README.md`](docs/README.md). Working plans, exploratory notes, review evidence, approved policy, and historical records must not be treated as interchangeable.

### Clinical semantics and completeness

- [`data/rules/imci_major_sick_child_v1.json`](data/rules/imci_major_sick_child_v1.json): canonical expanded clinical rule set and provenance.
- [`configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json`](configs/information_policy/imci_major_sick_child_holistic_completeness_v2.json): whole-encounter completeness and synthesis policy.
- [`configs/information_policy/imci_major_sick_child_review_decisions_v1.json`](configs/information_policy/imci_major_sick_child_review_decisions_v1.json): the 13 approved hackathon-scope review decisions.
- [`src/edge_imci/schemas/holistic.py`](src/edge_imci/schemas/holistic.py): whole-encounter schema.
- [`src/edge_imci/evaluation/holistic.py`](src/edge_imci/evaluation/holistic.py): deterministic integrated evaluator.
- [`docs/system_level_clinical_audit_v2.md`](docs/system_level_clinical_audit_v2.md): verification record and readiness decision.

### Golden semantics and language work

- [`data/golden/holistic_product_v1/`](data/golden/holistic_product_v1): approved, hash-frozen 78-case product-level holistic semantic suite, canonical manifest, and YAML mirror.
- [`configs/golden/holistic_product_golden_approval_v1.json`](configs/golden/holistic_product_golden_approval_v1.json): canonical approval/freeze record, including reviewed and frozen hashes and bounded-use permissions.
- [`docs/product_holistic_golden_approval_v1.md`](docs/product_holistic_golden_approval_v1.md): human-readable approval, freeze, and change-control record.
- [`docs/golden_language_rendering_contract_v1.md`](docs/golden_language_rendering_contract_v1.md): approved bounded-hackathon language contract and calibration boundary.
- [`configs/rendering/edgeimci_response_grammar_v1.json`](configs/rendering/edgeimci_response_grammar_v1.json): canonical project-owner-approved state templates, exact delimiters, and formatting change control.
- [`docs/edgeimci_response_grammar_v1.md`](docs/edgeimci_response_grammar_v1.md): human-readable deterministic response grammar.
- [`data/golden/holistic_product_v1/language_calibration_v1.jsonl`](data/golden/holistic_product_v1/language_calibration_v1.jsonl): canonical, project-owner-approved 16-case style calibration; frozen and not training-eligible.
- [`docs/product_holistic_golden_language_calibration_review_v1.md`](docs/product_holistic_golden_language_calibration_review_v1.md): reviewer-facing presentation of the 16 frozen calibration conversations.
- [`docs/product_holistic_golden_language_technical_review_v1.md`](docs/product_holistic_golden_language_technical_review_v1.md): same-agent alignment/editorial review and remediated findings used as an approval input.
- [`docs/product_holistic_golden_language_independent_review_v1.md`](docs/product_holistic_golden_language_independent_review_v1.md): independent coding-agent review of the pinned pre-freeze calibration and its two subsequently remediated language findings.
- [`configs/rendering/holistic_golden_language_approval_v1.json`](configs/rendering/holistic_golden_language_approval_v1.json): canonical project-owner approval, freeze hashes, permissions, and validation limitations.
- [`docs/product_holistic_golden_language_approval_v1.md`](docs/product_holistic_golden_language_approval_v1.md): human-readable language approval and controlled-freeze record.
- [`data/golden/holistic_product_v1/language_renderings_v1.jsonl`](data/golden/holistic_product_v1/language_renderings_v1.jsonl): complete 78-case grammar-normalized language layer; all records pending re-review.
- [`docs/product_holistic_golden_language_review_v1_report.md`](docs/product_holistic_golden_language_review_v1_report.md): hash-pinned pre-format review that passed semantics and motivated the stable grammar.
- [`docs/product_holistic_golden_language_review_v1.md`](docs/product_holistic_golden_language_review_v1.md): reviewer-facing grammar-normalized complete language layer.
- [`docs/holistic_golden_language_format_re_review_agent_instructions.md`](docs/holistic_golden_language_format_re_review_agent_instructions.md): hash-pinned instructions for independent re-review of the formatted 78-case layer.
- [`docs/holistic_golden_language_independent_review_agent_instructions.md`](docs/holistic_golden_language_independent_review_agent_instructions.md): executed, superseded pre-freeze review handoff retained for history.
- [`docs/product_holistic_golden_suite_requirements_v1.md`](docs/product_holistic_golden_suite_requirements_v1.md): product-level semantic-suite contract.
- [`configs/golden/holistic_product_golden_scope_dispositions_v1.json`](configs/golden/holistic_product_golden_scope_dispositions_v1.json): versioned product-scope resolution for later Plan B/C treatment-stage execution.
- [`docs/product_holistic_golden_review_v1.md`](docs/product_holistic_golden_review_v1.md): case index, pinned substrate, review instructions, and resolved scope disposition.
- [`docs/product_holistic_golden_domain_review_v1.md`](docs/product_holistic_golden_domain_review_v1.md): superseded technical/source review of the pre-remediation hash and its four findings.
- [`docs/product_holistic_golden_domain_re_review_v1.md`](docs/product_holistic_golden_domain_re_review_v1.md): superseded oracle-v2 independent review and respiratory finding record.
- [`docs/product_holistic_golden_domain_re_review_v2.md`](docs/product_holistic_golden_domain_re_review_v2.md): oracle-v3 technical/source verification used as the basis for human/domain approval.
- [`docs/interaction_design_retrieval_assessment_bundles.md`](docs/interaction_design_retrieval_assessment_bundles.md): current holistic interaction framing.
- [`docs/synthetic_data_generation_experiment_notes.md`](docs/synthetic_data_generation_experiment_notes.md): structured-first language-generation hypotheses and experiments.
- [`data/archive/selected_v0/`](data/archive/selected_v0): quarantined historical 14-case selected-v0 component semantics and proposed renderings; lifecycle restrictions are machine-readable in its archive manifest.
- [`experiments/rendering_bakeoff_v1/`](experiments/rendering_bakeoff_v1): historical component rendering candidates and metrics.

### Infrastructure

- [`scripts/sync_holistic_artifacts.py`](scripts/sync_holistic_artifacts.py): deterministic expanded JSON-to-YAML synchronization.
- [`scripts/generate_holistic_golden_suite.py`](scripts/generate_holistic_golden_suite.py): deterministic proposed holistic semantic-suite generation and review package.
- [`scripts/generate_holistic_language_calibration.py`](scripts/generate_holistic_language_calibration.py): deterministic materialization and validation of the approved and frozen 16-case language calibration.
- [`scripts/generate_holistic_golden_language_suite.py`](scripts/generate_holistic_golden_language_suite.py): deterministic grammar-normalized complete-language generation from frozen semantics and preserved calibration inputs.
- [`experiments/registry/`](experiments/registry): versioned planned experiment definitions, campaign branches, schemas, generated YAML mirror, and generated run index.
- [`src/edge_imci/experiments/`](src/edge_imci/experiments): provider-neutral automatic run tracking, provenance, telemetry, accounting, profiling, and CLI infrastructure.
- [`experiments/README.md`](experiments/README.md): implemented experiment operations, immutable sidecar, accounting, and ADTC profiling conventions.
- [`src/edge_imci/information_policy/`](src/edge_imci/information_policy): policy artifact validation and legacy selected-v0 information-policy machinery.
- [`src/edge_imci/generation/`](src/edge_imci/generation): deterministic case, split, and historical golden-slice utilities.
- [`src/edge_imci/evaluation/`](src/edge_imci/evaluation): clinical, parsing, scoring, external-evaluation, and reporting logic.
- [`tests/`](tests): scope boundaries, source/provenance, completeness, action synthesis, artifact mirrors, and pipeline behavior.

## Change-control boundaries

- Do not modify the frozen `imci-selected-v0` clinical semantics to make the expanded product model easier to implement.
- Do not treat `UNKNOWN` as negative or manufacture missing observations.
- Do not let language-generation code create or alter clinical truth.
- Do not use the historical 82-case benchmark or archived 14-case selected-v0 slice as training data or as product-level holistic semantics.
- Do not silently convert generic source actions into invented drug names, doses, durations, or regimens.
- Do not call the hackathon review decision set production clinical approval.
- Preserve immutable raw run evidence; derive summaries and cost without overwriting it.
