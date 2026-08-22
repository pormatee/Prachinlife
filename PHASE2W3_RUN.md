# PrachinLife V2 Phase 2W.3 — Independent Verification Intake

Purpose: add independent publication-verification evidence without weakening the 2-lineage publication gate.

Safety:
- dry-run is read-only
- same-lineage sources are rejected
- conflicting identity claims are rejected
- first independent lifecycle=active source does not activate canonical lifecycle
- lifecycle activates only after 2 independent active-lifecycle lineages
- evidence bundle + audit are atomic
- publication/export/user-web switch remain disabled

Tests:
- focused: 6/6 OK
- full V2 regression: 561 tests OK
