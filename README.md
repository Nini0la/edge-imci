# EdgeIMCI

**Offline-first clinical NLP with deterministic decision support for sick-child primary care.**

EdgeIMCI explores how a locally deployable language model can normalize free-form primary-health-care findings into a bounded encounter schema while keeping clinical decision authority in a deterministic, source-backed Integrated Management of Childhood Illness (IMCI) engine. The system is designed for constrained hardware and settings where connectivity may be limited or unavailable.

This repository documents the full engineering path: clinical-rule encoding, information-state design, synthetic-data governance, model training, leakage-controlled evaluation, experiment tracking, edge packaging, and a worker-facing prototype.

> EdgeIMCI is research software, not a diagnostic system or production medical device. It does not authorize autonomous clinical use and does not cover every IMCI pathway or follow-up algorithm.

## Product demo

[![Watch the two-minute EdgeIMCI prototype demo](https://img.youtube.com/vi/4GQwY4otV_8/hqdefault.jpg)](https://youtu.be/4GQwY4otV_8)

**[Watch the two-minute EdgeIMCI prototype demo](https://youtu.be/4GQwY4otV_8).**

The video demonstrates the worker-facing encounter flow. The interface shown uses the earlier 0.6B model integration; the latest 4B artifact is published and evaluated separately in the [ADTC submission repository](https://github.com/Nini0la/edgeIMCI-adtc-2026-submission).

## System design

The learned component interprets language. It does not own clinical decisions:

```text
free-form whole-encounter findings
                |
                v
      EdgeIMCI extractor
                |
                v
   model-facing encounter JSON
                |
                v
 schema and information-state checks
                |
                v
 deterministic completeness + IMCI engine
                |
                v
 classifications, actions and presentation
```

The model-facing target deliberately excludes classifications, urgency, referral, treatments, rule IDs, evaluator traces, provenance, and presentation text. Those outputs are produced by deterministic code after schema validation.

`null` means `UNKNOWN`, never a negative finding. Silence is not converted into clinical evidence.

## Engineering highlights

- **Hybrid safety-oriented architecture:** learned language normalization is separated from deterministic clinical logic.
- **Machine-readable clinical provenance:** encoded rules link back to the WHO IMCI source material and versioned review decisions.
- **Explicit completeness policy:** incomplete assessments are distinguished from complete encounters, while known urgent findings can still trigger immediate source-backed actions.
- **Controlled data lifecycle:** semantic parents govern dataset splits so paraphrases cannot cross TRAIN, VALIDATION, and TEST boundaries.
- **Frozen evaluation assets:** golden cases, schemas, approval records, hashes, and historical test authorizations are retained for reproducibility.
- **Experiment operations:** provider-neutral run registries, immutable sidecars, telemetry, accounting, and profiling distinguish scientific results from execution metadata.
- **Edge delivery:** the model-development line includes LoRA fine-tuning, GGUF conversion, quantization, public artifact verification, and CPU profiling.
- **Failure-aware reporting:** threshold failures, confounded comparisons, scope limits, and unresolved review work are recorded rather than hidden.

The implementation spans Python, JSON Schema, pytest, React, TypeScript, and Vite. Model and experiment workflows include MLX, Modal, Azure OpenAI, Hugging Face, and `llama.cpp`, with immutable revisions and checksums recorded where they affect reproducibility.

## Current evidence

This repository contains the deterministic clinical foundation, product semantics, data/evaluation infrastructure, prototype application, and the original 0.6B model-development line. The latest standalone 4B model, immutable download, provenance packet, and profiling evidence are maintained in the public [EdgeIMCI ADTC submission](https://github.com/Nini0la/edgeIMCI-adtc-2026-submission).

| Workstream | Evidence |
|---|---|
| Clinical engine | Versioned major sick-child rule set, whole-encounter schema, deterministic completeness policy, integrated evaluator, and source-linked review decisions |
| Product semantics | 78 hash-frozen holistic cases covering complete, incomplete, urgent, contradictory, boundary, and out-of-scope encounters; not authorized as direct training data |
| Data engineering | Parent-aware split controls, deterministic target export, synthetic-language review, corpus accounting, and frozen artifact identities |
| 0.6B research line | 1,497-record extraction corpus and one authorized 143-record reserved TEST comparison; 97.20% exact-record and decision equivalence, 99.89% field accuracy, and 100% schema validity, with six preregistered thresholds missed |
| 4B release line | Enriched 2,258-row fine-tune, public Q4_K_M GGUF and adapter, reproducible provenance, CPU profiling, and retained official participant report in the separate submission repository |

The 0.6B TEST result is historical evidence, not a production-readiness claim. Its original base comparison was methodologically confounded by an under-specified prompt; a separately authorized schema-informed base run is retained as supplementary evidence. See the [methodology correction](docs/qwen3_0_6b_base_control_methodology_correction_v1.md).

The current 4B Q4_K_M participant profile reports 5.03 generation tokens/s, 4,288.94 MiB peak RSS, and ARC-Easy `acc_norm` 0.78 on 50 questions on an Intel Core i5-4210U. These are participant measurements, not an organizer audit, an official 8 GB qualification, or evidence of clinical accuracy. The complete limitations and original files are in the [4B profiling packet](https://github.com/Nini0la/edgeIMCI-adtc-2026-submission/tree/main/provenance/4B-alpha-second/profiling/2026-09-22-ubuntu-adtc).

## Supported encounter scope

`imci-major-sick-child-v1` covers initial sick-child assessment for children aged 2 completed months to under 5 years across:

- general danger signs;
- cough or difficult breathing;
- diarrhoea;
- fever, including measles; and
- ear problems.

It is paired with `imci-major-sick-child-holistic-completeness-v2`. The product-level behavior is:

```text
COMPLETE SUPPORTED ENCOUNTER
-> emit integrated classifications and management

INCOMPLETE, NO KNOWN URGENT FINDING
-> report grouped missing assessment elements
-> withhold final holistic synthesis

INCOMPLETE, KNOWN URGENT FINDING
-> emit source-backed urgent/pre-referral actions immediately
-> report the remaining rapid assessment
-> withhold final holistic synthesis
```

Urgency does not make an encounter complete. The remaining supported assessment must be completed rapidly without delaying referral or pre-referral treatment. The current scope is initial assessment only; it does not execute later IMCI follow-up-visit algorithms.

## Run locally

Python 3.10 or newer is required.

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

The prototype can run with a deterministic fixture extractor, without model credentials:

```bash
cd web
npm ci
npm run build
cd ..
PYTHONPATH="src:." python -m app --extractor stub
```

Open `http://127.0.0.1:8000`. Stub mode recognizes only the frozen demonstration fixtures. See [`app/README.md`](app/README.md) for frontend development and the historical Modal-backed path.

The canonical clinical and policy artifacts are JSON; YAML siblings are generated human-readable mirrors. Regenerate and verify them with:

```bash
python scripts/sync_holistic_artifacts.py
python -m pytest
```

Tests reject JSON/YAML drift, unknown evaluator rule IDs, invalid scope pins, incomplete decision sets, and relevant clinical/completeness regressions.

## Clinical source and provenance

The machine-readable rule sets are derived from the **WHO Integrated Management of Childhood Illness Chart Booklet, March 2014**. They are project-authored software artifacts, not WHO-authored machine-readable rules.

The WHO PDF is not redistributed. Obtain it separately and place it at:

```text
data/sources/IMCI chartbooklet 2014.pdf
```

Every encoded logic unit records source provenance. Start with:

- [`data/sources/README.md`](data/sources/README.md) for source handling;
- [`major_sick_child_expansion_map_v1.md`](docs/major_sick_child_expansion_map_v1.md) for the source-to-rule map;
- [`clinical_questions.md`](docs/clinical_questions.md) for reviewed clinical questions; and
- [`docs/README.md`](docs/README.md) for document authority, lifecycle, and supersession.

The older `imci-selected-v0` rule set and its evaluation assets remain frozen as historical regression material. They must not be represented as the complete respiratory or diarrhoea algorithm or reused as product training data.

## Repository guide

| Path | Purpose |
|---|---|
| [`src/edge_imci/`](src/edge_imci) | Schemas, deterministic evaluation, generation, review, experiment tracking, and CLI infrastructure |
| [`app/`](app) | Python API and extraction adapters for the prototype application |
| [`web/`](web) | React worker interface |
| [`data/rules/`](data/rules) | Versioned clinical rules and provenance |
| [`data/golden/`](data/golden) | Frozen semantic and language evaluation assets |
| [`configs/`](configs) | Information policy, schemas, review decisions, experiment definitions, and rendering contracts |
| [`experiments/`](experiments) | Run registry and retained model, generation, evaluation, and profiling evidence |
| [`tests/`](tests) | Clinical boundaries, provenance, completeness, synthesis, artifact, and pipeline verification |
| [`docs/`](docs) | Architecture, methodology, audit history, operating plans, and document-control index |

## Project history

EdgeIMCI was developed through the Africa Deep Tech Challenge, which supplied a concrete external target for laptop deployment, reproducibility, and evidence packaging. The competition is one milestone in the project rather than its technical scope: the repository remains a case study in constrained clinical NLP, safety-oriented system architecture, data governance, evaluation design, and edge-model operations.

## Safety and license

Independent clinical review remains incomplete. EdgeIMCI must not be used for autonomous diagnosis, treatment, referral, or production clinical care. The encoded scope and review decisions are bounded research representations and do not replace current clinical guidance, professional judgment, local policy, or regulatory review.

The repository is licensed under [GNU GPL v3](LICENSE). Third-party models, datasets, source publications, and hosted artifacts retain their own terms; the repository license is not a blanket license determination for those materials.
