# PrachinLife V2 Phase 2W.1 — Publication Contract + Staged Export Safety

## Goal
Create a fail-closed boundary from internal canonical data to a staged compatibility export. No production JSON replacement and no User Web switch are allowed in this phase.

## Safety contracts
- Canonical/evidence DB evaluation is SQLite read-only.
- Publication uses the existing `PublicationPolicy` and field verification engine.
- Only `ELIGIBLE` published views may enter a staged payload.
- A zero-eligible result cannot write a staged JSON file.
- Writes are restricted to `data/v2/staging/`.
- `data/v2/exports/prachinlife_places_v2.json` is not written.
- `published_places` is not mutated.
- User Web switch remains disabled.

## Tests
Focused: 7/7 OK.
Full V2 regression: 550 tests OK.

## Real checkpoint dry-run
- Province: ปราจีนบุรี
- Canonical places: 220
- Eligible: 0
- Blocked: 220
- Staged payload: 0
- Production export: unchanged
- User Web switch: disabled

Primary blocker: all 220 Prachinburi canonical places currently have non-active (`unknown`) lifecycle; required publication fields also generally lack VERIFIED quorum.

## Next
Phase 2W.2 should be Data Publication Readiness, not a frontend switch: establish explicit lifecycle/existence verification and verified identity fields for a controlled pilot set, then re-run 2W.1 until a non-zero eligible set is produced and validated.
