# Pre-Phase-2 worktree preservation record

> **Authority:** `HISTORICAL_ARCHIVE` · **Lifecycle:** `CURRENT` · **Recorded:** `2026-09-16`

## Purpose

This record separates reviewed source history from raw execution material before the ADTC 2026 Gate 2 work begins. It does not authorize remote calls, training, TEST access, deployment, or clinical use.

## Git preservation

The pre-transition source work is preserved on the local branch:

`archive/pre-phase2-generation-review-20260916`

The branch contains focused commits for:

- expanded generation-style schemas and semantic guards;
- reviewer calibration provenance and structural-null review regressions;
- controlled Azure/Modal generation tooling, zero-call packages, and remote-call prohibition;
- consolidated deterministic-rejection and transport-reconciliation evidence; and
- the Gate 1 report and Lundin-derived benchmark handoff.

The branch is an archival integration surface. It contains infrastructure identifiers and historical execution details and must not be pushed or published without a separate disclosure review.

## Raw artifact boundary

The original worktree also contains approximately 12,484 untracked experiment artifacts totaling approximately 418 MB. Most are raw provider attempts, copied request packages, schedules, sealed evaluation inputs, or reviewer outputs. They were not bulk-added to Git because doing so would duplicate large payloads, expose provider-level execution material, and impose permanent repository clone cost.

The raw material remains untouched in the original worktree, including:

- the 12,002 per-attempt files from the 6,000-request full generation run;
- large 45–79 MB `source_requests.jsonl` packages and copied schedules;
- provider review outputs and synchronous receipts;
- held-out evaluation request payloads; and
- detailed authorization and execution directories not selected as compact evidence.

No likely API key, bearer token, private key, Azure connection string, or obvious real-patient PHI was found during the transition audit. The raw artifacts do contain synthetic clinical narratives, provider request identifiers, timestamps, usage, and model responses, so absence of credentials does not make them appropriate for public publication.

## Retention rule

Do not delete, clean, publish, or migrate the remaining raw artifacts until a project-owner-approved private artifact destination and checksum manifest exist. No cloud upload was performed during this transition.

Phase 2 must begin from current `origin/main` in a separate clean worktree. Only reviewed preservation commits or individual files should be carried forward when they are required by the Gate 2 plan.
