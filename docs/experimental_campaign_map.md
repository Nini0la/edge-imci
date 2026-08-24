# EdgeIMCI Experimental Campaign Map

> **Authority:** `WORKING_PLAN` · **Lifecycle:** `CURRENT` · Maintained Markdown working version; the corresponding DOCX is its source snapshot.

*Critical path, parallel lanes and evidence-based branches*

**Status:** High-level roadmap for the hackathon campaign; Lundin is off the main track and the domain-expert questionnaire remains separate.

> **Critical-path question:** Can the selected EdgeIMCI checkpoint recover canonical whole-encounter state from PHC language accurately enough that the deterministic pipeline preserves safe clinical behavior, while running effectively on target hardware?

## Main track and parallel data lane

```text
CLINICAL APPROVAL
        |
HOLISTIC GOLDEN SET
        |
SYNTHETIC GENERATION BAKE-OFF
        |
FAST ~1K LANGUAGE+JSON DATASET ------->  LARGE AZURE BATCH
        |                                  10K / 20K / 30K
        |                                          |
ASUS CANDIDATE MODEL-RUNTIME ADMISSION            |
        |                                          |
ADMITTED PARENT ONLY                              |
        |                                          |
QWEN3-1.7B SFT-v1 ON MODAL                       |
        |                                  ARRIVES LATER
EXTRACTION + DECISION EVALS <----------  SCALE / NEXT-TRAINING INPUT
        |
CONVERT / QUANTIZE DEPLOYMENT ARTIFACT
        |
SAME-ASUS POST-TRAINING REQUALIFICATION
        |
GOOD ENOUGH?  -- YES --> SELECT / SUBMIT
        | NO
IDENTIFY BOTTLENECK --> TAKE ONLY THE RELEVANT BRANCH --> RE-EVALUATE
```

## Evidence gates

| Gate | Decision point | Minimum evidence |
| ---: | --- | --- |
| 1 | Clinical approval | Semantic rules and holistic cases are approved for use. |
| 2 | Generation recipe | Teacher/prompt behavior is stable; acceptance is high; no systematic semantic corruption. |
| 3 | Candidate model-runtime admission | Each base candidate is source- and checksum-pinned, run through the frozen harness on the intended ASUS Ubuntu device, and admitted only if predeclared quality, reliability, time-to-valid, speed, memory and thermal gates pass. |
| 4 | Extraction SFT-v1 | Fine-tuning uses an ASUS-admitted parent; the checkpoint and complete training provenance exist. |
| 5 | Core extraction/decision evals | Structured-state metrics and downstream classification, management, completeness and urgent-action equivalence are available. |
| 6 | Post-training ASUS requalification | The converted or quantized deployment artifact passes the same frozen qualification on the same ASUS, with paired before-and-after evidence. |
| 7 | Branch decision | A specific bottleneck and expected value justify any additional experiment. |

## Optional branches - only when evidence points there

| Branch | Trigger | Evidence required to keep it |
| --- | --- | --- |
| SFT-v2 | SFT-v1 error analysis shows correctable data or training issues | Improved clinical metrics without new safety regressions |
| 4B SFT / capacity | 1.7B appears capacity-limited or 4B base evidence is compelling | Gain versus 1.7B justifies slower/larger deployment |
| Learning curve | Large batch is available and data-scale value is uncertain | Matched-base 1k/3k/10k comparison |
| Qwen3.5 / Tinker | Specialist branch can test a supported newer model with existing credits | Comparable clinical and deployment evidence |
| Preference / RL | SFT plateaus on a targeted, rewardable behavior | Targeted gain justifies complexity and cost |
| SVD / compression | Size/capacity trade-off warrants a research compression test | Quality-size-speed curve |
| Quantization | Target profile shows meaningful speed, memory or deployability points left on the table | Matched Q8/Q6/Q4 quality-runtime trade-off; otherwise skip |
| Lundin external eval | Time remains after hackathon evidence is secure | Optional research/generalization evidence; never blocks submission |

## Operating rhythm

- Keep the fast approximately 1k lane and large Azure Batch lane concurrent.
- Treat each training, evaluation, generation and profile as a versioned experiment with automatic provenance.
- Qualify exact model-runtime combinations on the intended ASUS; never infer deployability from a model-only or laboratory benchmark.
- Freeze admission thresholds before inspecting candidate results, and do not fine-tune an unadmitted parent.
- Compare scientific outcomes alongside time, usage and cost; do not confuse cheap execution with useful evidence.
- Branch from measured bottlenecks, not from a desire to run every available technique.
- Keep Lundin off the hackathon critical path and keep the domain-expert clinical questionnaire in its separate review document.

## Current next sequence

1. Complete clinical approval and freeze the holistic golden set.
2. Run the teacher/prompt bake-off and lock the first stable generation recipe.
3. Generate approximately 500-1,000 accepted examples and launch the large Azure Batch lane in parallel.
4. Freeze the candidate, runtime, repository, workload, checksum, measurement and threshold package; qualify each base candidate-runtime combination on the ASUS.
5. Admit only passing combinations, then train the selected admitted parent and run structured-extraction and deterministic decision-equivalence evaluation.
6. Convert or quantize the selected checkpoint and rerun the same frozen qualification on the same ASUS.
7. Select, submit or branch according to the paired quality and deployment evidence.

The detailed protocol is [target-device model-runtime admission and qualification](target_device_model_runtime_qualification_plan.md).
