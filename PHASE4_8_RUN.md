# Phase 4.8 — Pending Review Queue + Continue Discovery

Goal: park unresolved manual-confirmation candidates without blocking the coverage/discovery loop.

Behavior:
- Reads Phase 4.5 adoption review, Phase 4.6 lifecycle resolution, Phase 4.7 direct confirmation, and Phase 4.1 coverage audit.
- Queues only candidates that remain NEEDS_REVIEW -> UNRESOLVED_NEEDS_DIRECT_CONFIRMATION and have no resolving direct confirmation.
- Queue persistence is idempotent via one row per candidate.
- Writes only `precanonical_pending_review` in commit mode.
- Does not modify canonical places, canonical evidence, pre-canonical identity/evidence, or Production JSON.
- A pending individual candidate never blocks category discovery.
- Current next discovery work remains Prachinburi / vegetarian / sparse_relative_coverage.

Run:
`python scripts/queue_pending_reviews_v2.py --commit`
