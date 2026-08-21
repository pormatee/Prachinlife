# Development Packet #5 — Entity Resolution / Dedup Engine V2

## Goal
Create a deterministic, source-neutral entity-resolution layer that decides whether two ingested place observations are safe to link, require review, are distinct, or lack enough evidence.

## Constraints
- Do not modify frozen V1 production behavior or datasets.
- Entity resolution must not publish, verify, mutate, or merge CanonicalPlace records.
- Use source-neutral signals; no category-specific workaround.
- Preserve uncertainty: ambiguous cases must route to review rather than auto-merge.
- No new third-party dependency.
- Keep thresholds explicit and versionable through a policy object.

## Matching signals
- same source record identity
- same deterministic candidate fingerprint
- normalized phone identity
- normalized website identity
- normalized/similar name
- geographic distance
- province agreement/conflict

## Safety policy
- Strong identity + no geographic contradiction may auto-link.
- Similar name + nearby location requires review.
- Same name alone requires review.
- Far/province-conflicting similar-name records are distinct.
- Strong contact identity with geographic contradiction requires review, not auto-link.
- Unrelated records with weak evidence remain insufficient_evidence rather than being forced into a false distinction.

## Tests
Existing regression tests 1–41 must remain PASS. New tests 42–54 cover exact identity, cross-source strong identifiers, geographic safety boundaries, ambiguity/review, policy validation, and side-effect freedom.

## Non-goals
- Canonical merge implementation
- verification/confidence scoring
- database-backed blocking/indexing
- production integration
- category-specific matching

## Checkpoint
PASS requires all V2 tests to pass and the change set to contain only V2 development artifacts.
