# Golden language rendering contract v1

> **Authority:** `APPROVED_PRODUCT_POLICY` · **Lifecycle:** `CURRENT` · Defines the approved bounded-hackathon language-layer contract; it cannot create or modify clinical semantics.

## Purpose

The 78 product-level golden semantic cases are approved and frozen. They specify what EdgeIMCI must mean. The next task is to establish what a good EdgeIMCI interaction should sound like.

This contract governs manually curated golden language renderings derived from those cases. It does not authorize bulk generation, dataset splitting, SFT, or changes to the frozen semantic records.

**Implementation status:** The versioned record schema and 16-case calibration are project-owner approved and frozen for the bounded hackathon. The first complete 78-case review passed semantic faithfulness and identified a formatting split. The project-owner-approved `edge-imci-response-grammar-v1` now governs exact canonical state templates and delimiters. All 78 formatted records are pending re-review. Teacher bake-off, bulk generation, and training remain blocked until the complete layer passes its own gate.

```text
frozen semantic case
        ↓
faithful language rendering
        ↓
human review of meaning + interaction quality
        ↓
frozen golden language layer
        ↓
teacher/prompt bake-off and later variant generation
```

## Separation of authority

The two golden layers have different roles:

| Layer | Governs | May change during language review? |
|---|---|---:|
| Golden semantics | Findings, completeness, classifications, actions, missing elements, urgency, traces, and provenance | No |
| Golden language | Natural phrasing, organization, turn boundaries, clarity, and frontline-worker usability | Yes |

If a rendering disagrees with its semantic case, the rendering is wrong. If review discovers an actual semantic defect, work must stop for a versioned semantic remediation; the language author must not repair it by improvising a different clinical answer.

The frozen semantic suite is an evaluation and generation authority, not direct training data. Later language variants may become corpus candidates only after separate acceptance and split controls.

## Intended interaction

The primary user is a frontline PHC worker who has performed the supported initial sick-child assessment and reports findings in free-form language. The normal successful interaction is one complete submission followed by one integrated answer. Conversation is mainly a recovery mechanism for omissions, contradictions, or missing context—not a recreation of the full paper checklist one question at a time.

The rendering should address the worker directly and use concise, natural clinical language suitable for the hackathon demonstration. It should not expose JSON paths, enum syntax, rule IDs, or internal evaluator terminology in the user-facing answer.

## Required rendering behavior

### Complete supported encounter

The response must:

1. present every frozen final classification;
2. present the complete integrated action plan;
3. lead with urgent referral or referral management when applicable;
4. distinguish urgent referral from non-urgent referral exactly as encoded;
5. preserve generic source-backed actions as generic when no drug or regimen is encoded;
6. reconcile repeated actions into a coherent plan without dropping independently indicated actions; and
7. include source-backed counselling, follow-up, reassessment, or transfer instructions represented by the semantic target.

A complete encounter with no positive classification must still communicate the frozen result and applicable actions clearly; it must not invent reassurance, diagnosis, or treatment.

### Incomplete encounter without known urgency

The response must:

1. state that the supported assessment is incomplete;
2. withhold final holistic classifications and treatment synthesis;
3. request all currently required missing elements in concise, clinically sensible groups;
4. retain already supplied information without asking for it again; and
5. make clear how each missing item must be acquired when that matters.

It must not present an internal or partial classification as the completed answer.

### Incomplete encounter with a known urgent finding

The response must:

1. place the frozen urgent and pre-referral actions first;
2. state that urgent referral or management must not be delayed;
3. state that the remaining supported assessment must be completed rapidly;
4. list the remaining required assessment elements; and
5. withhold the final holistic synthesis until the assessment is complete.

Urgency does not convert unknown observations into negatives and does not itself make the encounter complete.

### Contradictory or invalid evidence

The response must identify the conflict or invalid acquisition and request the exact correction or reassessment encoded by the semantic case. It must not choose the more convenient value, average conflicting values, or silently discard one observation.

### Out-of-scope/schema-rejected encounter

The response must state that the encounter is outside the supported EdgeIMCI scope and must not provide an unsupported classification or management synthesis. Wording may direct the worker to use the applicable approved workflow, but must not invent that workflow.

## Acquisition language

Renderings must preserve how information is obtained. These modes are not interchangeable:

| Acquisition mode | Language behavior |
|---|---|
| `CAREGIVER_QUESTION` | Ask the worker to obtain or report history from the caregiver. |
| `CLINICIAN_OBSERVATION` | Instruct the worker to observe or examine the child; do not phrase it as a caregiver opinion. |
| `MEASUREMENT` | Instruct the worker to measure and report the value or validity condition. |
| Application/deployment context | Request the configured or known contextual fact, such as the area's malaria-risk category; do not infer it from geography. |
| Intervention/reassessment | State the encoded intervention and subsequent reassessment requirement; keep pre- and post-treatment findings distinct. |

Related acquisitions should normally be batched. A single focused request is preferable when one correction or measurement alone resolves the incomplete state, or when the action must be performed and reassessed before later information can be validly obtained.

Missing-element requests should expose the actual checks rather than merely naming a checklist section. For example, “complete the danger-sign assessment” is less useful than listing the remaining danger-sign checks.

## Clinical-faithfulness constraints

Every rendering must satisfy all of the following:

- Unmentioned information remains `UNKNOWN`, never absent.
- No observation, diagnosis, classification, drug, dose, duration, regimen, or local protocol may be invented.
- Source-generic actions such as “give an appropriate antibiotic” or “apply the applicable local cholera protocol” remain generic unless the frozen target supplies more detail.
- Respiratory-rate classification uses only a valid calm, full-minute assessment and uses post-bronchodilator findings when the encoded trial was indicated and completed.
- A positive clinically confirmed inability to drink/breastfeed may appear in both supported domains as encoded; a negative general-danger finding must not be expanded into diarrhoea-specific drinking behavior.
- Routine home-care and scheduled follow-up must not compete with an urgent pre-referral workflow when the semantic target defers them.
- Non-urgent referral must not be upgraded to urgent referral.
- Initial Plan B/C actions and their timed reassessment instructions may be rendered, but longitudinal treatment state or an automatic repeated plan must not be invented.
- Follow-up visits remain outside the supported initial-assessment algorithm.

## Language-quality criteria

A good rendering is:

- faithful: every clinical claim maps to the frozen target;
- complete: no required classification, action, urgency, or acquisition is omitted;
- prioritized: immediate actions appear before supporting detail;
- concise: repetition and unnecessary background are removed;
- actionable: the worker can tell what to do, assess, measure, or report;
- natural: it reads like professional assistance, not serialized schema fields;
- calibrated: it does not overstate certainty, urgency, or product scope; and
- internally coherent: combined actions form one plan rather than unrelated pathway dumps.

Tone variation is allowed only after a canonical interaction style is approved. Style must never be used as a source of clinical diversity.

## Proposed rendering record

Each golden language record should be machine-readable and contain at least:

```yaml
rendering_id: hpg-001-language-v1
golden_case_id: hpg-001-all-negative
semantic_suite_id: edge-imci-holistic-product-golden-v1
semantic_cases_sha256: 9026186ea67aea26981985e02b88c503e18a098cca564db33b7ed4313808665f
rendering_contract_id: edge-imci-golden-language-rendering-contract-v1
language: en
input_turns:
  - role: user
    content: "..."
assistant_turns:
  - role: assistant
    content: "..."
alignment:
  expected_state: COMPLETE
  classifications_covered: []
  actions_covered: []
  missing_elements_covered: []
  urgency_rendered: false
  acquisition_modes_preserved: true
review:
  semantic_faithfulness: PENDING
  interaction_quality: PENDING
  reviewer: null
  notes: ""
```

The exact schema should be versioned before the first rendering is frozen. Renderings must pin the semantic-suite hash so that no language item can silently drift to a different semantic target.

## Review rubric

Reviewers should score or disposition each rendering separately on:

1. semantic completeness;
2. absence of unsupported clinical content;
3. correct complete/incomplete/out-of-scope behavior;
4. urgency and referral priority;
5. preservation of acquisition modes;
6. usefulness and grouping of missing-element requests;
7. integrated-plan coherence and action deduplication;
8. naturalness, clarity, and concision; and
9. consistency with the approved EdgeIMCI product voice.

Semantic faithfulness is a hard gate. A fluent rendering with a missing, altered, or invented clinical element fails.

## Controlled work sequence

1. ~~Approve or revise this contract.~~ Completed.
2. ~~Define the versioned rendering schema and deterministic semantic-alignment checks.~~ Completed.
3. ~~Use the proposed 16-case calibration set below, or approve a revised set with equivalent coverage.~~ Completed.
4. ~~Manually draft and review the calibration renderings to establish the EdgeIMCI voice and organization.~~ Project-owner approved for the bounded hackathon; qualified PHC field validation was not performed.
5. ~~Update and freeze the contract/schema if calibration reveals interaction-policy problems.~~ Completed without changing clinical semantics.
6. Produce and review one canonical rendering for each of the 78 semantic cases. **Current stage.**
7. Freeze the approved language layer with its own manifest, hashes, and review record.
8. Use the frozen semantics and reviewed language layer to run teacher/prompt bake-offs.
9. Only after a generation recipe passes acceptance checks should language variants and corpus candidates be generated.

## Proposed calibration set

The first language pass should use these cases. This set is intentionally small enough for close wording review while covering the interaction states most likely to establish or break the product voice.

| Case | Calibration purpose |
|---|---|
| `hpg-001-all-negative` | Complete low-severity encounter without invented reassurance or treatment. |
| `hpg-008-resp-age-2-rate-50` | Straightforward complete classification and outpatient actions. |
| `hpg-014-resp-chest-hiv-positive` | Source-specific non-urgent referral plus first-dose behavior. |
| `hpg-016-resp-oximeter-89-9` | Non-urgent oxygen referral that must not be upgraded to urgent. |
| `hpg-020-resp-post-bronchodilator-improved` | Intervention/reassessment wording and use of post-treatment findings. |
| `hpg-028-diarrhoea-some-dehydration` | Initial Plan B plus timed reassessment without inventing longitudinal state. |
| `hpg-031-diarrhoea-severe-age-24-cholera` | Generic local cholera-protocol action without an invented drug. |
| `hpg-052-fever-identified-bacterial-cause` | Generic appropriate-antibiotic action without an invented regimen. |
| `hpg-055-fever-severe-measles-cornea` | Urgent pre-referral prioritization with multiple immediate treatments. |
| `hpg-068-cross-four-pathways` | Complete multi-pathway integrated plan and action reconciliation. |
| `hpg-070-cross-multiple-urgent` | Multiple urgent classifications with deduplicated urgent management. |
| `hpg-071-incomplete-entry-unknown` | One missing supported-encounter entry; unknown must not become negative. |
| `hpg-072-incomplete-multiple-groups` | Batched missing-element request across assessment groups. |
| `hpg-073-incomplete-known-urgent` | Immediate urgent action plus rapid remaining assessment; final synthesis withheld. |
| `hpg-075-contradiction-drinking` | Explicit conflict resolution without guessing. |
| `hpg-077-out-of-scope-age-1` | Clear scope rejection without unsupported clinical synthesis. |

The frozen calibration authorized the first complete 78-case language pass and remains immutable historical evidence. The complete layer has now been authored, reviewed, language-remediated, explicitly approved by the project owner, and frozen at its versioned hash. All 16 anchor user submissions and every semantic alignment were preserved. The freeze authorizes controlled variant work, teacher bake-off, and product evaluation, but not direct training use or production clinical use.

## Deterministic response grammar

The canonical grammar is `configs/rendering/edgeimci_response_grammar_v1.json`, with a generated YAML mirror and human-readable explanation in `edgeimci_response_grammar_v1.md`. It defines exact headings, casing, bullet delimiters, state-dependent section order, deterministic action priority, and deterministic acquisition order for complete, urgent-complete, incomplete, urgent-incomplete, and out-of-scope responses.

This is an interaction and post-training consistency policy, not an IMCI rule. If the grammar and a frozen semantic target disagree, the semantic target wins and the rendering must return to review.

## Explicit non-goals for this stage

This stage does not:

- generate the real SFT corpus;
- create paraphrase variants at scale;
- select a teacher model or prompt winner;
- split data into training, validation, and test sets;
- fine-tune a model; or
- change `clinical-rules-v0`, the expanded clinical rules, completeness policy, approved decisions, or frozen golden semantics.

## Completed calibration approval gate

The calibration approval confirmed:

- the required response behavior for each semantic state;
- the proposed user-facing organization and tone;
- the handling of urgent versus non-urgent referral;
- the acquisition-mode wording policy;
- the proposed rendering record fields; and
- the calibration-set coverage.

The 16 calibration cases are now frozen style anchors; the complete 78-case golden language layer is not yet authored, reviewed, or frozen.
