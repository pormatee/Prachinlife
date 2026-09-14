# Architecture Alignment V1 — Wave 3D Regional Context Runtime Boundary

Status: MIGRATION_SLICE

Canonical implementation moved from:

`place_platform_v2/regional_context_runtime_v1.py`

to:

`place_platform_v2/regional/context_runtime_v1.py`

The old module remains as a compatibility wrapper.

Because the canonical file is now one package level deeper, the module-relative
repository-root fallback changes from `parents[1]` to `parents[2]`. This preserves
the same resolved repository root; it is a path-preservation adjustment, not a
behavioral change.

Canonical imports now target the sibling modules already migrated in Waves
3A–3C:

- `regional.product_v1`
- `regional.reference_adapter_v1`
- `regional.web_context_v1`

No regional contract semantics, API route, domain data, database path,
production page, canonical record, or published record is changed.
