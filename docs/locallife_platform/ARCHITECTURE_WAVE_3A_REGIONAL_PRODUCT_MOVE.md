# Architecture Alignment V1 — Wave 3A Regional Product Boundary

Status: MIGRATION_SLICE

This slice moves the canonical implementation of:

`place_platform_v2/regional_product_v1.py`

to:

`place_platform_v2/regional/product_v1.py`

The old import path remains as a compatibility wrapper.

Rules:
- no business-logic change
- no database relocation
- no canonical/published data mutation
- no public web-route change
- no production root change
- rollback if targeted tests fail

This is the first small source relocation in the Regional Runtime boundary.
