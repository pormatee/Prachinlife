# Phase 4.12 — Exact Coordinate Acquisition

Goal: acquire exact coordinates for AMITA without guessing from landmarks or map imagery.

Current source state:
- Wongnai: candidate address + static map are present, but numeric candidate lat/lon are not exposed.
- Restaurant Guru: candidate listing exists in Si Maha Phot, but numeric candidate lat/lon are not exposed.
- Kasemrad Prachinburi: numeric coordinates exist for the hospital landmark, not for AMITA, so they are rejected.

Outcome:
EXACT_COORDINATES_UNRESOLVED

Gate rules:
- coordinates must explicitly belong to the candidate
- coordinates must be numeric and within Thailand bounds
- landmark coordinates are rejected
- multiple candidate coordinate sources must agree within 120 meters
- conflicts block adoption
- no coordinate is inferred from a static map or nearby landmark

Next:
direct_map_or_operator_coordinate_confirmation

No DB, canonical, pre-canonical, or Production writes.
