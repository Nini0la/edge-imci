# EdgeIMCI - Work Categories Before Full-Speed Development

> **Status:** `CURRENT` only as pre-Phase-2 planning history. Proposed successor `docs/adtc_2026_gate_2_semifinal_requirements_and_work_plan_v1.md` becomes controlling only after project-owner approval.

## 1. Clinical substrate integrity

This is the “are we teaching the right thing?” layer.

**Work:**
- Finish human review of the currently encoded IMCI rules.
- Resolve or explicitly defer remaining ambiguities.
- Keep JSON/YAML synchronized.
- Preserve source provenance.
- Freeze clinical-rules-v0.

**Status:** Mostly done.

**Gate:**
We trust the current three-pathway rule set enough to generate data from it.

---

## 2. Interaction / task definition

This is the biggest conceptual clarification we made today.

The final model should not merely map complete cases to classifications. It should handle:
- Sparse user presentation.
- Partially complete presentation.
- Complete presentation.
- Follow-up questioning.
- Eventual classification/action only when enough information exists.

The model task becomes:

```
user describes case
→ determine what is known
→ identify what is still required
→ ask only necessary follow-up questions
→ receive more information
→ classify when sufficient
→ explain the IMCI result/action in natural language
```

**Work:**
- Formally define “sufficient information” per pathway.
- Define expected response behavior for incomplete cases.
- Define multi-turn trajectory format.
- Decide what natural-language answer style we want.

**Status:** Concept decided, specification not yet written.

This should happen before the real corpus is generated.

---

## 3. Dataset / corpus generation

This is where the actual SFT material comes from.

### Training corpus

Natural-language examples derived from structured clinical truth.

Likely categories:
- Complete single-turn cases.
- Very incomplete presentations.
- Partially complete presentations.
- Multi-turn follow-up trajectories.
- Danger-sign escalation.
- Threshold/boundary cases.
- Counterfactuals.
- Distracting irrelevant details.
- Varying linguistic styles.

### Validation corpus

Used for checkpoint and hyperparameter selection.

### Final held-out benchmarks

Separate:
- IID.
- Wording/template shift.
- Compositional generalization.
- Counterfactual/boundary.
- Multi-turn information-gathering.

**Work:**
- Expand generator.
- Generate genuinely new latent case families.
- Freeze test groups before SFT.
- Ensure no group/template/signature leakage.

**Status:** Split machinery exists; real corpus does not.

This is probably the next major coding/data task.

---

## 4. Evaluation design

We now need two kinds of evaluation, because output format and clinical competence are not the same thing.

### A. Natural-language task evaluation

This is the actual user-facing capability.

Metrics could include:
- Premature-classification rate.
- Required-question recall.
- Unnecessary-question rate.
- Danger-sign omission.
- Final classification accuracy.
- Referral correctness.
- Action correctness.
- Successful completion over multiple turns.

### B. Structured diagnostic evaluation

For clean measurement.

Options:
- Constrained JSON generation.
- Oracle serialization test.
- Classification-only probes.
- Referral-only probes.
- Structured extraction of natural-language answers.

The structured evaluation is measurement infrastructure, not necessarily the final user experience.

**Work:**
- Keep strict JSON benchmark for diagnostics.
- Add natural-language scoring path.
- Retain structured ground truth behind every prose target.
- Validate any strong-LLM extractor against hand-labeled examples before trusting it.

**Status:** Strict JSON exists; natural-language evaluation is missing.

---

## 5. Baseline model characterization

Before training, understand the candidate models.

**Current candidates:**
- Qwen3-0.6B
- Qwen3-1.7B
- Qwen3-4B

**Already known:**
- 1.7B performs surprisingly close to 4B on the external IMCI benchmark.
- Strict internal JSON results are not clinically interpretable yet.

**We still need:**
- Natural-language clinical baseline.
- Formatting-independent diagnostic baseline.
- ASUS performance.

**Status:** Partially done.

---

## 6. Edge hardware / quantization experiments

Separate this from model-quality evaluation.

For ASUS, benchmark representations that make sense for each size, not blindly Q4 everything.

| Model | Representations worth testing |
|-------|-------------------------------|
| 0.6B  | FP16/BF16, Q8, maybe Q4       |
| 1.7B  | FP16/BF16 if feasible, Q8, Q6, Q4 |
| 4B    | Q4 primarily                  |

Measure on the same ASUS:
- Generation tok/s.
- Prompt tok/s.
- TTFT.
- Peak RAM.
- Max practical context.
- Stability.

**Goal:**
Find each model’s best edge Pareto point.

**Status:** ASUS comparison pending.

This should start very soon and can run in parallel with corpus work.

---

## 7. Model training experiments

This is where Modal becomes useful.

### Phase A — SFT

Probably start with 1.7B.

**Experiments:**
- LoRA vs full/partial fine-tuning where practical.
- Rank.
- Learning rate.
- Epochs.
- Dataset mixture.
- Proportion of incomplete vs complete cases.
- Single-turn vs multi-turn balance.
- Natural-language target style.

**Evaluate every checkpoint on:**
- Validation sets.
- Strict structured diagnostics.
- Natural-language clinical benchmarks.
- External Lundin benchmark.

### Phase B — optional reward/RL

Only after SFT.

**Potential rewards:**
- Does not classify prematurely.
- Asks required missing questions.
- Detects danger signs.
- Correct classification.
- Correct referral.
- Avoids unsupported actions.

Prime Intellect becomes more interesting here.

**Status:** Not started.

---

## 8. External validation / scientific story

We should preserve three distinct evaluation stories:

1. **Internal procedural benchmark**  
   Can the model actually execute IMCI decision logic?

2. **Multi-turn information-gathering benchmark**  
   Can it know what it does not yet know?

3. **External Lundin benchmark**  
   Does specialization generalize to an independently constructed IMCI evaluation?

And then combine that with:

4. **Edge performance**  
   Does it run fast enough on constrained hardware?

That gives the final thesis:

> A small specialist model can outperform or match larger general models on bounded IMCI tasks while running substantially faster on commodity edge hardware, including the ability to request missing clinical information before classification.

That is much stronger than:

> “We fine-tuned Qwen on a medical PDF.”

---

# Where we are right now

| Workstream | Approx. status |
|------------|----------------|
| Clinical rules | ~90% |
| Evaluation infrastructure | ~70% |
| Interaction specification | ~40% |
| Real training corpus | ~10% |
| ASUS model characterization | ~25% |
| SFT | 0% |
| RL | 0% |
| Final hackathon evidence | ~15% |

We are no longer in scaffolding land.

We are at the transition:

```
trusted rule substrate → define real task → generate real corpus + benchmark hardware → train
```

---

# What should happen next, in parallel

- **Lane A — Coding/data agent**  
  Formalize the natural-language + follow-up-question task and generate the real training/held-out corpus.

- **Lane B — ASUS**  
  Download sensible representations of 0.6B / 1.7B / 4B and run a controlled performance matrix.

- **Lane C — Evaluation agent**  
  Add diagnostics that separate:
  - Formatting ability.
  - Underlying clinical competence.
  - Multi-turn information gathering.

Once those three are done, we start Modal SFT immediately.
