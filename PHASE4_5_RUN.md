# Phase 4.5 — Controlled New Place Adoption Review

Goal: decide whether verified pre-canonical candidates are safe to adopt into the canonical place table.

Decision rules:
- VERIFIED_IDENTITY required
- at least two independent source families required
- proposed name must be observed in evidence
- canonical duplicate guard: same phone globally, same normalized name within province
- unresolved lifecycle conflicts prevent automatic adoption
- review is read-only

Current result:
- ต้นหลิวอาหารเจ -> NEEDS_REVIEW
- identity sources: 4 independent families
- evidence records: 4
- phone 0959176495 supported by 3 evidence records
- lifecycle observations: open=2, permanently_closed=1
- duplicate matches: 0
- blocker: none
- review flag: open_vs_closed_source_conflict
- proposed lifecycle: none
- next: resolve_lifecycle_before_canonical_adoption

No canonical place was created.
