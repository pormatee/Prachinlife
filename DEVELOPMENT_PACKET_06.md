# Development Packet #6 — Evidence Aggregation + Verification Contract

## Goal
Add a deterministic, source-aware verification layer that aggregates field-level PlaceEvidence after entity resolution and reports support, verification, conflict, or insufficient evidence without mutating canonical data or publishing it.

## Constraints
- Frozen V1 remains untouched.
- Verification is field-level, not a single opaque place-wide score.
- Independent sources matter; repeated observations from one source record must not inflate quorum.
- Rejected and stale evidence remain stored but do not count as active verification support.
- Conflicting active claims must be surfaced, never silently resolved.
- Verification must not mutate CanonicalPlace, evidence status, or publication state.
- Policy thresholds are explicit/versionable and storage-neutral.

## Tests / Acceptance
- Existing V2 regression suite remains PASS.
- No evidence => insufficient evidence.
- One independent source => supported, not verified.
- Two independent sources agreeing => verified under default policy.
- Duplicate observations from one source identity do not count as independent confirmation.
- Competing active values => conflicting.
- Rejected/stale evidence do not create false current support/conflict.
- Evidence from another place cannot affect assessment.
- Collection-valued evidence aggregates deterministically.
- Policy threshold can change without changing engine core.
- Engine has no side effects and has no publish authority.

## Non-goals
- No canonical merge/adoption logic.
- No publication policy.
- No source reliability weighting yet.
- No freshness decay policy beyond excluding evidence already marked stale.
- No database implementation change.
- No production integration.
