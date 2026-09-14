# Architecture Alignment V1 — Wave 3C Regional Web Context Boundary

Status: MIGRATION_SLICE

Canonical implementation moved from:

`place_platform_v2/regional_web_context_v1.py`

to:

`place_platform_v2/regional/web_context_v1.py`

The old module remains as a compatibility wrapper.

The moved implementation now imports the canonical sibling reference adapter:

`place_platform_v2.regional.reference_adapter_v1`

This slice changes no regional contract semantics, route values, domain data,
database paths, production page, or published/canonical records.
