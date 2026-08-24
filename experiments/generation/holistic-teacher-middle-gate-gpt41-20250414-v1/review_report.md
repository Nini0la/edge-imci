# Natural teacher middle-coverage review

Status: **middle examples ready for project-owner review; large-scale recipe not yet frozen**.

## Outcome

The natural-complete v2 middle gate executed eight target-blind GPT-4.1 requests.

- Six of eight passed deterministic validation.
- Two contained correct user-language content but invalid evidence pointers.
- Delegated semantic review approved six unique cases and rejected two.
- The resulting unique-case language acceptance rate was `6/8` (`75%`).

The rejected semantic patterns were:

1. changing the frozen composite observation `able to drink or breastfeed` into the stronger statement `able to drink and breastfeed`; and
2. changing `no identified bacterial cause` into the stronger conclusion `no bacterial cause is present`.

The two evidence-pointer failures used reconstructed or ellipsis-containing strings instead of literal substrings. Their PHC submissions remained semantically acceptable.

## Targeted v2.1 regression

Four affected cases were regenerated after making logical-connector, epistemic-qualifier, and evidence-span instructions explicit.

- The non-urgent referral case passed both deterministic and semantic review.
- The ordinary respiratory case corrected its logical connector but retained one evidence-pointer mismatch.
- The fever case corrected the bacterial-cause qualifier but again changed `drink or breastfeed` to `drink and breastfeed`.
- The ear case added an unrequested statement about an unknown discharge duration and was rejected.

This regression shows that prompt wording alone is not a sufficient semantic safeguard. Before bulk generation, the local validator should explicitly check composite logical connectors and epistemic qualifiers, and the prompt should explicitly require null fields to remain unmentioned unless a separate source observation says the worker knows that information is missing.

## Representative approved middle pairs

The teacher generated only the PHC-worker submission. Each expected assistant response below was attached afterward from the frozen product-level golden language layer.

### 1. Stateful bronchodilator reassessment

Semantic case: `hpg-020-resp-post-bronchodilator-improved`

#### Generated PHC submission

The child is 18 months old and has had cough or difficult breathing for 3 days. There have not been any convulsions, and the child is not convulsing now. The child is not lethargic or unconscious, is able to drink or breastfeed, and does not vomit everything. There is no diarrhoea, no ear problem, and no fever. Wheezing was noted, but no stridor when calm was present. Breaths were counted for one minute before and after bronchodilator trial. Respiratory rate before bronchodilator was 45, with the child calm and no chest indrawing. After bronchodilator, breaths were counted again for one minute, the respiratory rate was 35, the child remained calm, and there was no chest indrawing. A pulse oximeter was not available. The child does not have recurrent wheeze.

#### Frozen expected EdgeIMCI response

Classifications:
- Cough or cold

Management:
- Give an inhaled bronchodilator for 5 days.
- The rapid-acting inhaled bronchodilator trial was completed.
- Breathing was reassessed after the bronchodilator trial.
- Soothe the throat and relieve the cough with a safe remedy.
- Advise the caregiver when to return immediately.
- Follow up in 5 days if the child is not improving.

### 2. Non-urgent referral

Semantic case: `hpg-014-resp-chest-hiv-positive`

#### Generated PHC submission

This child is 18 months old and has had cough or difficult breathing for 3 days. The child is calm during assessment. Convulsions are not present now and there has been no history of convulsions. The child is not lethargic or unconscious, is able to drink or breastfeed, and does not vomit everything. There is no diarrhoea, ear problem, or fever. Breaths were counted over one minute, with a respiratory rate of 35 breaths per minute. Chest indrawing is present. There is no stridor when calm, and wheezing or recurrent wheeze are not present. HIV exposure or infection is confirmed, and a pulse oximeter is not available.

#### Frozen expected EdgeIMCI response

Classifications:
- Pneumonia

Management:
- Give the first dose of amoxicillin, then refer the child. This finding alone calls for referral, not urgent referral.

### 3. Incomplete encounter requiring acquisition

Semantic case: `hpg-071-incomplete-entry-unknown`

#### Generated PHC submission

The child is 18 months old. There is no cough or difficult breathing, no ear problem, and no fever. The child is not convulsing now, has not had convulsions, is not lethargic or unconscious, is able to drink or breastfeed, and does not vomit everything.

#### Frozen expected EdgeIMCI response

ASSESSMENT INCOMPLETE

Information needed:
- Ask whether the child has diarrhoea.

I cannot provide the final classifications and complete management plan until these findings are supplied.

## Readiness decision

These three pairs are approved as representative owner-review samples. The natural teacher approach is viable, but bulk generation should remain unauthorized until the deterministic connector/qualifier guards and null-field instruction are incorporated into the pinned generation recipe.
