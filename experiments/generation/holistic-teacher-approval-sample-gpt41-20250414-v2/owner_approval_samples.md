# EdgeIMCI teacher approval samples

Status: **ready for project-owner large-scale decision**. Large-scale generation remains unauthorized.

## Recommended teacher recipe

Use Azure GPT-4.1 `2025-04-14`, the natural-complete v2 prompt, temperature `0.7`, and `2,000` maximum output tokens. The teacher remains blind to classifications, actions, urgency wording, evaluator traces, and the frozen assistant target.

The concise style is not recommended: its complex candidate changed the source disjunction `cough or difficult breathing` into the stronger claim `cough and difficult breathing`.

## Teacher-generation instruction

```text
You render one fixed EdgeIMCI whole-encounter semantic record as a natural, coherent submission from a trained frontline PHC worker.

Clinical truth is fixed. Express every supplied known fact and no others. Preserve positive findings, explicit negative findings, measurements, durations, area context, and unknown values that the source explicitly requires you to mention. Never turn an unknown or omitted field into a negative statement.

Do not infer or add diagnoses, classifications, interpretations, urgency, treatments, advice, or summary conclusions, even when they seem logically implied by the findings. For example, do not add phrases such as "no signs of dehydration" unless that exact conclusion is itself a supplied source fact. Describe only the observations supplied in the structured encounter.

Produce only the worker's case submission. Do not produce an EdgeIMCI response: the approved canonical response is attached deterministically after validation. Do not expose field names, schema terms, hashes, rule IDs, policy IDs, or implementation commentary.

Return one JSON object matching the supplied candidate schema. `fact_evidence` must contain every supplied `fact_id` exactly once. Every `evidence_text` must be copied character-for-character as one contiguous substring from `user_submission`. If one combined phrase expresses several facts, you may reuse the same exact larger phrase for each applicable fact ID. Before returning, check every evidence string against the final submission and correct any that is not an exact substring. Do not include unknown fact IDs.

Style: natural and easy to read while remaining complete; vary sentence structure and the ordering of supplied assessment domains where coherence permits; avoid unnecessary repetition, storytelling, greetings, and conclusions.

SOURCE_PACKAGE_JSON:
{{SOURCE_PACKAGE_JSON}}
```

## Sample 1: `hpg-001-all-negative`

### Final user submission

This child is 18 months old. The child is not convulsing now and has not had convulsions. The child is not lethargic or unconscious, and is able to drink or breastfeed. The child does not vomit everything. There is no cough or difficult breathing, no diarrhoea, no ear problem, and no fever.

### Frozen expected EdgeIMCI response

Classifications:
- None of the currently supported classifications is triggered.

Management:
- No management action is indicated by the supported assessment.

### Review result

Approved as an owner-review sample for language and source alignment. The assistant response was attached deterministically after generation; it was never shown to the teacher.

## Sample 2: `hpg-076-complete-danger-plus-all-pathways`

### Final user submission

This child is 18 months old and presents with cough or difficult breathing, diarrhoea, ear problems, and fever. The cough has been present for 3 days. I counted the breaths for one minute while the child was calm and found a respiratory rate of 35 breaths per minute. There is no chest indrawing, no stridor when calm, and no wheezing or recurrent wheeze. A pulse oximeter is not available. Diarrhoea has lasted 3 days, with no blood in the stool. The child's drinking status and skin pinch are normal, with no sunken eyes and the child is not restless or irritable. The child is not convulsing now and has not had convulsions. The child is not lethargic or unconscious and is able to drink or breastfeed. However, the child vomits everything. There is no ear pain, no ear discharge reported, no pus draining from the ear, and no tender swelling behind the ear. The fever has lasted for 2 days, with a measured temperature of 38.0°C. There is no generalized rash, no obvious cause of fever, no identified bacterial cause, and no red eyes or runny nose. There is no history of measles within the last 3 months, no measles cough, and no stiff neck. The malaria risk is high, a malaria test is available and the result is negative.

### Frozen expected EdgeIMCI response

URGENT: Act now and do not delay referral.

Classifications:
- Very severe disease
- Severe pneumonia or very severe disease
- No dehydration
- Very severe febrile disease
- No ear infection

Immediate management:
- Complete the remaining assessment quickly.
- Give the first dose of an appropriate antibiotic.
- Give the first dose of severe-malaria treatment.
- Give the indicated pre-referral treatment immediately.
- Keep the child warm.
- Prevent low blood sugar.
- Arrange urgent referral.

Deferred routine care:
- Routine home-care counselling and scheduled follow-up are deferred so they do not delay or compete with the urgent referral workflow.

### Review result

Approved as an owner-review sample for language and source alignment. The assistant response was attached deterministically after generation; it was never shown to the teacher.

Two exact evidence-pointer strings were corrected without changing the user submission or assistant response. Full provenance is in the JSON sibling.
