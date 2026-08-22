# PrachinLife V2 Phase 2V.3.2 — Existing Canonical Reconciliation

Goal: safely reconcile an approved `create_place_candidate` to one deterministic existing canonical place instead of creating a duplicate.

Safety semantics:
- Exactly one `SAME_ENTITY` match dominates incidental nearby `REVIEW` candidates for reconciliation only.
- More than one `SAME_ENTITY` remains blocked for manual review.
- Reconciliation never overwrites canonical place fields.
- All approved draft evidence is rebound to the existing canonical place while preserving original candidate id and draft id in evidence metadata.
- An idempotency receipt and entity-resolution audit are committed atomically with the evidence.
- No canonical revision is created because no canonical field changes occur.
- Publication/export remains disabled.
- Diagnostic CLI bootstrap is fixed so `PYTHONPATH=.` is no longer required.

Validation checkpoint:
- Phase 2V.3 + 2V.3.2 focused tests: 18/18 OK
- Full V2 regression: 538 tests OK
