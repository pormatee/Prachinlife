# Phase 4.14 — Pending Coordinate Confirmation Queue

Goal: park candidates whose exact coordinates remain unresolved without blocking Discovery/Coverage.

Current queue state after commit simulation:
- ต้นหลิวอาหารเจ -> pending_manual_confirmation (lifecycle)
- ร้านอาหารเจ AMITA VEGAN -> pending_coordinate_confirmation

AMITA queue reason:
- unresolved_exact_coordinates
- current_state = EXACT_COORDINATES_UNRESOLVED
- next_action = supply_valid_direct_coordinate_confirmation

Queue behavior:
- lifecycle and coordinate pending types are separated
- queue insertion is idempotent
- non-queue tables are unchanged
- no canonical/precanonical evidence/Production writes
- pending candidates do not block discovery

Discovery continues with Prachinburi vegetarian coverage.
