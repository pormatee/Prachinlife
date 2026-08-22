# Phase 2W.2 — Publication Data Readiness Pilot

Goal: measure real publication readiness without weakening the Phase 2W.1 gate or mutating canonical/publication state.

Adds:
- lineage-aware evidence independence check
- read-only pilot readiness CLI
- regression tests preventing V1 JSON derived from the same OSM object from counting as an independent confirmation

Safety:
- no canonical writes
- no publication writes
- no export writes
- no User Web switch

Validation in development workspace:
- focused: 5/5 OK
- full V2 regression: 555 tests OK
