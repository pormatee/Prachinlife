# Development Packet #12.2 — Production Schema Mapping + Duplicate Audit

## Goal
Align the read-only V1 migration audit with the four actual production JSON schemas before any database migration.

## Constraints
- V1 JSON remains read-only.
- No production database writes.
- No canonical adoption or publication.
- No inference of missing province/location.
- Explicit non-place content is skipped, not forced into the Place model.
- Preserve full legacy record and source provenance.

## Mapping contract
- `location.latitude/longitude` -> geographic point.
- `location.province` -> province.
- `food_types` -> categories (Vegetarian dataset).
- top-level contact fields take precedence; `metadata.phone/website` are fallbacks.
- explicit shopping/deal/promotion content -> skipped as non-place.

## Acceptance tests
- all previous V2 regression tests pass.
- production-shaped nested location maps correctly.
- Vegetarian `food_types` maps correctly.
- metadata contact fallback works without overriding top-level values.
- explicit non-place content is skipped.
- missing coordinates alone do not cause a place to be skipped.
- duplicate groups are printed by the audit CLI for operator review.

## Non-goal
No controlled migration into SQLite/PostgreSQL in this packet.
