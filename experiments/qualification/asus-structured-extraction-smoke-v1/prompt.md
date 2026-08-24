# EdgeIMCI ASUS structured-extraction smoke prompt v1

> **Use:** application-task smoke testing only. This fixture comes from a `TRAIN` parent and is not held-out candidate-admission evidence.

Use [`system_prompt.txt`](system_prompt.txt) as the system message and [`user_prompt.txt`](user_prompt.txt) as the user message. The complete expected response is [`expected_target.json`](expected_target.json).

## System prompt

The canonical machine-ready system prompt is [`system_prompt.txt`](system_prompt.txt). It constrains the model to observation extraction, forbids clinical decisions, preserves `null` as `UNKNOWN`, enumerates the required schema fields, and requires exactly one JSON object.

Do not manually shorten or repair this prompt for one candidate during a matched comparison. Any revised prompt is a new fixture version and must be tested identically across every candidate.

## User prompt

```text
The child is not convulsing now. There has been no history of convulsions. The child is not lethargic or unconscious. The child is able to drink or breastfeed. The child does not vomit everything. The child is 18 months old. The child has cough or difficult breathing. The child does not have diarrhoea. The child does not have any ear problem. The child does not have fever. I counted the child's breaths for one full minute. There is no chest indrawing. The child was calm during the assessment. The cough has lasted for 3 days. The oxygen saturation is 90 percent. Pulse oximeter was available. There is no history of recurrent wheeze. The respiratory rate is 35 breaths per minute. There is no stridor when the child is calm. There is no wheezing.
```

## Expected response

```json
{
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_fever": false,
    "has_ear_problem": false
  },
  "danger_signs": {
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "convulsing_now": false
  },
  "respiratory": {
    "cough_duration_days": 3,
    "respiratory_rate": 35,
    "chest_indrawing": false,
    "stridor_when_calm": false,
    "wheezing": false,
    "recurrent_wheeze": false,
    "child_calm": true,
    "breaths_counted_one_minute": true,
    "pulse_oximeter_available": true,
    "oxygen_saturation_percent": 90.0,
    "hiv_exposed_or_infected": null,
    "bronchodilator_trial_completed": null,
    "post_bronchodilator_respiratory_rate": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_breaths_counted_one_minute": null
  },
  "diarrhoea": null,
  "fever": null,
  "ear": null
}
```
