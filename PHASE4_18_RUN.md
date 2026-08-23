# Phase 4.18 — Controlled New Place Adoption Machine

Goal: turn Phase 4 discovery/verification into a reusable generic adoption machine.

Eligibility guards: VERIFIED_IDENTITY; >=2 independent source families; no unresolved lifecycle conflict; no pending manual/coordinate confirmation; exact candidate coordinates; no canonical duplicate risk.

Current dry run: 2 precanonical candidates, 0 eligible. AMITA is blocked by pending coordinate confirmation and unresolved exact coordinates. ต้นหลิวอาหารเจ is blocked by lifecycle conflict, pending confirmation, and unresolved exact coordinates.

Synthetic commit tests prove a fully eligible candidate creates one canonical place, carries evidence forward, records a revision, is idempotent, and never auto-publishes Production JSON.

Targeted tests: 5/5 OK. Full regression must run in the real repository because the development packet omits root frontend/admin assets required by legacy tests.
