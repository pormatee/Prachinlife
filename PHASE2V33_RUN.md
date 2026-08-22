# PrachinLife V2 Phase 2V.3.3 — Admin Provenance Repair

Goal: preserve review semantics in canonical evidence provenance.

- seed/declared-source evidence keeps its declared source (e.g. OpenStreetMap)
- operator_changes become manual evidence from `PrachinLife Admin Operator`
- committed legacy 2V.3.2 evidence can be repaired by draft id
- repair changes evidence provenance only, never canonical place fields
- repair creates an immutable `admin_provenance_repairs` audit record
- publication/export remains disabled

Tests: 543/543 OK at package build.
