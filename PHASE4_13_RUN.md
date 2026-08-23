# Phase 4.13 — Direct Coordinate Confirmation

Goal: provide an auditable direct-confirmation path for AMITA exact coordinates without guessing or copying nearby landmark coordinates.

Default packet:
- intentionally contains no real coordinate confirmation
- outcome remains STILL_UNRESOLVED
- next step is supply_valid_direct_coordinate_confirmation

Valid confirmation requires:
- confirmer
- confirmer role
- method: map_pin / operator / merchant / in_person / admin
- numeric latitude + longitude
- timezone-aware confirmed_at
- reference
- coordinate inside Thailand and Prachinburi context

A valid committed confirmation writes only to precanonical_direct_coordinates.
It does not mutate canonical rows, pre-canonical candidate rows, or Production JSON.

Current default result:
STILL_UNRESOLVED
