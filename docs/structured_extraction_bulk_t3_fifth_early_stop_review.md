# Structured-extraction campaign: fifth T3 early-stop review

> **Authority:** project-owner delegated execution and semantic review · **Lifecycle:** `IMMUTABLE_CAMPAIGN_REVIEW`  
> **Decision:** remediation complete; exact-slot continuation released  
> **Training:** not authorized by this review

The v9 run produced 104 language candidates and eight network-only failure receipts before stopping. Review of all 17 deterministic language rejections found two genuine polarity defects and 15 conservative validator outcomes. The Pidgin drinking polarity and noisy-English generalized-rash polarity were made explicit; a five-case gate then passed semantic review 5/5.

Transport-only failures do not complete a language allocation slot. The next continuation therefore skips the 844 slots with language candidates, retries the same eight transport-only slots, and covers the other 1,290 unattempted slots: 1,298 calls in total. This yields the original 2,142 candidate-bearing allocation slots while preserving eight additional transport-failure receipts. At the campaign reservation rate, the resulting 2,150 remote-attempt ceiling is $43, still below the existing $50 hard guard.
