# Phase 6 Final — Prachinburi Data Expansion & Quality

Phase 6 promotes the Phase 5 operational machine from a vegetarian-focused cycle to a multi-category Prachinburi expansion and quality cycle.

## Scope
- 12 canonical place categories are audited together.
- Thin categories are routed to coverage discovery.
- Established categories with systematic/partial detail gaps are routed to quality enrichment.
- Existing concrete Phase 5 candidate blockers are carried forward.
- All work is reconciled through the persistent operational queue using category `all`.

## Safety
- Queue persistence is the only automatic database mutation when `--commit-queue` is supplied.
- No canonical or pre-canonical adoption is automatic.
- No production JSON is written.
- Trust thresholds are unchanged.
- Real-world completeness is explicitly not claimed.

## Current baseline result
220 canonical Prachinburi places across 12 accounted categories. The current routing produces 12 category-level work items plus 2 concrete carried-forward candidate items: 4 coverage-discovery, 8 quality-enrichment, 1 coordinate/manual confirmation, and 1 manual confirmation.

Targeted Phase 6 tests: 8/8 OK in the development packet. Full repository regression must run after applying the package because the development packet intentionally omits root frontend/staging fixtures used by older tests.
