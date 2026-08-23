# Phase 4.11 — Geolocation Verification + Pre-Canonical Persistence

Goal: verify AMITA's location conservatively, then persist only pre-canonical candidate/evidence.

Current evidence:
- Wongnai verifies candidate address: 701/177 Soi 5, Moo 10, Tha Tum, Si Maha Phot, Prachinburi.
- Wongnai describes the shop as beside Kasemrad Prachinburi Hospital.
- Kasemrad official information verifies the hospital is in Moo 10, Tha Tum, Si Maha Phot.
- A public locator gives the hospital coordinates 13.89862, 101.59631.

Critical guard:
Hospital coordinates belong to the hospital, not AMITA. They are retained only as landmark reference and are never promoted to candidate coordinates.

Outcome:
ADDRESS_LOCATION_VERIFIED_COORDINATES_UNRESOLVED

Commit simulation:
- inserted pre-canonical candidates: 1
- inserted evidence: 4
- pre-canonical candidates total: 2
- pre-canonical evidence total: 8
- canonical places unchanged
- replay idempotent

Next:
acquire_exact_candidate_coordinates

No canonical creation or Production publication.
