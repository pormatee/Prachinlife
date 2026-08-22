# PrachinLife V2 Phase 2W.4 — Verification Source Acquisition Gate

Goal: bind an acquired independent source to a canonical place safely before it can become a Phase 2W.3 verification bundle.

Safety rules:
- Read-only only; no canonical/publication/User Web writes.
- Strong geographic match with province disagreement => `scope_conflict` and canonical correction review.
- Missing/far geographic anchors cannot verify a place.
- Nearby identity/name conflict => entity-resolution review.
- Existing lineage cannot count as independent verification.
- Explicit active lifecycle is required before source can become a W.3 bundle candidate.

Caltex pilot finding: the current canonical coordinates require geographic scope review before any lifecycle activation because external locality evidence places that coordinate in Sa Kaeo while the canonical row says Prachinburi.
