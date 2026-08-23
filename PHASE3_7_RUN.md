# Phase 3.7 Run — Explicit Controlled Canonical Adoption

This phase explicitly applies the eight Phase 3.6 phone/website proposals to the V2 canonical database. It does not publish Production JSON.

## Safety contract
- Back up the V2 DB before commit.
- Dry-run first.
- Recompute verification/adoption review from current evidence.
- Only `places.phone`, `places.website`, `places.updated_at`, and append-only `place_revisions` may change.
- Evidence rows must remain unchanged.
- No Production JSON writes.
- Transactional and idempotent.

## Expected development result
- proposals: 8
- dry-run ready: 8
- controlled commit: 8 fields updated, 8 revisions
- repeated commit: 0 updates / 8 already applied
- full regression: 734 tests OK
