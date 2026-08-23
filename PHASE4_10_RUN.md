# Phase 4.10 — Batch Identity Verification

Goal: verify all Phase 4.9 new discovery candidates together, preserving independent-source rules and preventing premature canonical adoption.

Current batch:
- ร้านอาหารเจ AMITA VEGAN -> VERIFIED_IDENTITY
  - independent source families: Wongnai, Restaurant Guru
  - canonical duplicate matches: 0
  - geolocation not yet verified
  - next: acquire_geolocation_and_persist_precanonical_evidence
- ฉันทนา -> SUPPORTED_IDENTITY
  - independent source family: Innews
  - no trustworthy second independent source found in this pass
  - next: acquire_second_independent_source

Rules:
- same source family never counts twice
- global phone collision blocks candidate creation
- verified identity alone is not canonical-ready without geolocation
- batch processing is read-only
- no canonical/precanonical/pending/Production writes
- trust policy unchanged
