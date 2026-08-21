# Development Packet #7 — Canonical Adoption / Merge Policy

## Goal
Create an explicit, deterministic boundary between field verification and canonical place mutation.

## Constraints
- Frozen V1 remains untouched.
- Verification never mutates canonical data.
- Adoption never publishes data.
- Identity/timestamps are never evidence-adoptable fields.
- High-impact identity/location/category fields require VERIFIED evidence by default.
- Lower-risk descriptive/contact fields may be proposed from SUPPORTED evidence.
- Every applied canonical change produces an immutable revision carrying policy version and evidence IDs.
- No database/vendor dependency is introduced.

## Tests / Acceptance
- Existing V2 regression remains green.
- Supported evidence cannot change high-impact fields by default.
- Verified evidence can produce a proposal.
- Conflicting/insufficient evidence cannot be adopted.
- Cross-place and unknown-field proposals are blocked.
- No-op changes are explicit.
- Applying a proposal is an explicit separate operation and preserves the original immutable place.
- Every apply creates a revision/audit record.
- Adoption has no publication authority.

## Non-goals
- Publication policy.
- Database implementation/transactions.
- Automated moderation.
- Production integration.
