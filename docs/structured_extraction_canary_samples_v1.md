# EdgeIMCI structured-extraction canary samples v1

> **Authority:** `PROJECT_OWNER_APPROVED_CANARY` · **Lifecycle:** `APPROVED_EXTRACTION_CANARY` · Three reused teacher submissions; no remote calls, bulk generation or training authorization.

These samples demonstrate the new primary learning pair. The user message comes from an already reviewed teacher attempt. The assistant message is deterministic canonical JSON projected from the frozen semantic source; it contains no classification, action, urgency or frozen assistant prose.

## 1. `hpg-020-resp-post-bronchodilator-improved`

Partition: `TRAIN`  
Variant: `hpg-020-resp-post-bronchodilator-improved__natural-complete-prompt-v2-0-0__v1`

### Teacher-generated PHC submission

The child is 18 months old and has had cough or difficult breathing for 3 days. There have not been any convulsions, and the child is not convulsing now. The child is not lethargic or unconscious, is able to drink or breastfeed, and does not vomit everything. There is no diarrhoea, no ear problem, and no fever. Wheezing was noted, but no stridor when calm was present. Breaths were counted for one minute before and after bronchodilator trial. Respiratory rate before bronchodilator was 45, with the child calm and no chest indrawing. After bronchodilator, breaths were counted again for one minute, the respiratory rate was 35, the child remained calm, and there was no chest indrawing. A pulse oximeter was not available. The child does not have recurrent wheeze.

### Expected model response

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": true,
    "chest_indrawing": false,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": null,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": true,
    "post_bronchodilator_chest_indrawing": false,
    "post_bronchodilator_child_calm": true,
    "post_bronchodilator_respiratory_rate": 35,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 45,
    "stridor_when_calm": false,
    "wheezing": true
  }
}
```

## 2. `hpg-014-resp-chest-hiv-positive`

Partition: `TRAIN`  
Variant: `hpg-014-resp-chest-hiv-positive__natural-complete-prompt-v2-1-0__v1`

### Teacher-generated PHC submission

This child is 18 months old and has had cough or difficult breathing for 3 days. The child is calm during assessment. Convulsions are not present now and there has been no history of convulsions. The child is not lethargic or unconscious, is able to drink or breastfeed, and does not vomit everything. There is no diarrhoea, ear problem, or fever. Breaths were counted over one minute, with a respiratory rate of 35 breaths per minute. Chest indrawing is present. There is no stridor when calm, and wheezing or recurrent wheeze are not present. HIV exposure or infection is confirmed, and a pulse oximeter is not available.

### Expected model response

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": true,
    "has_diarrhoea": false,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": {
    "breaths_counted_one_minute": true,
    "bronchodilator_trial_completed": null,
    "chest_indrawing": true,
    "child_calm": true,
    "cough_duration_days": 3,
    "hiv_exposed_or_infected": true,
    "oxygen_saturation_percent": null,
    "post_bronchodilator_breaths_counted_one_minute": null,
    "post_bronchodilator_chest_indrawing": null,
    "post_bronchodilator_child_calm": null,
    "post_bronchodilator_respiratory_rate": null,
    "pulse_oximeter_available": false,
    "recurrent_wheeze": false,
    "respiratory_rate": 35,
    "stridor_when_calm": false,
    "wheezing": false
  }
}
```

## 3. `hpg-071-incomplete-entry-unknown`

Partition: `TRAIN`  
Variant: `hpg-071-incomplete-entry-unknown__natural-complete-prompt-v2-0-0__v1`

### Teacher-generated PHC submission

The child is 18 months old. There is no cough or difficult breathing, no ear problem, and no fever. The child is not convulsing now, has not had convulsions, is not lethargic or unconscious, is able to drink or breastfeed, and does not vomit everything.

### Expected model response

```json
{
  "danger_signs": {
    "convulsing_now": false,
    "had_convulsions": false,
    "lethargic_or_unconscious": false,
    "unable_to_drink_or_breastfeed": false,
    "vomits_everything": false
  },
  "diarrhoea": null,
  "ear": null,
  "fever": null,
  "patient_facts": {
    "age_months": 18,
    "has_cough_or_difficult_breathing": false,
    "has_diarrhoea": null,
    "has_ear_problem": false,
    "has_fever": false
  },
  "respiratory": null
}
```

## Serialization boundary

`chat_messages.jsonl` contains model-neutral system/user/assistant messages. It does not apply the Qwen tokenizer or chat template. That model-specific transformation remains a deterministic training-configuration step.
