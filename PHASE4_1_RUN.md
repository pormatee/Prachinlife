# Phase 4.1 — Discovery Coverage Audit

Goal: measure relative coverage gaps in the current V2 Central DB and produce a deterministic Phase 4.2 new-place discovery queue.

Constraints:
- read-only SQLite access
- no Production JSON writes
- no canonical/evidence writes
- trust policy unchanged
- province-agnostic engine
- current CLI focus is Prachinburi; focus is a ranking boost, not hard-coded engine behavior
- coverage means relative coverage in our current database, not a claim of real-world completeness

Core category families normalize current V2 categories into eat / vegetarian / go / service.
