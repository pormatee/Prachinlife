# Architecture Alignment V1 — Wave 3B Regional Reference Adapter Boundary

Status: MIGRATION_SLICE

Canonical implementation moved from:

`place_platform_v2/regional_reference_adapter_v1.py`

to:

`place_platform_v2/regional/reference_adapter_v1.py`

The old module remains as a compatibility wrapper.

The only import-edge adjustment inside the moved implementation is:

`regional_product_v1` -> sibling canonical `regional.product_v1`

No domain behavior, validation rule, data path, public route, database, or
production presentation is changed by this migration slice.
