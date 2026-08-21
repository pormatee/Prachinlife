# Development Packet #11 — V1 JSON → V2 Migration / Import Contract

## Goal
Create a deterministic, provenance-preserving and idempotent migration boundary for importing legacy PrachinLife V1 JSON records into the V2 discovery pipeline without modifying V1 source files or publishing data.

## Constraints
- Frozen V1 files are read-only inputs.
- Import does not create CanonicalPlace directly and does not publish.
- Every migrated record has stable source provenance and an import idempotency key.
- Invalid legacy data is reported explicitly rather than silently guessed.
- Duplicate/replayed legacy records are marked skipped.
- Mapping policy is versioned and storage-neutral.
- No production integration.

## Tests
- Existing V2 regression remains green.
- Common V1 aliases map deterministically.
- Input mappings are not mutated.
- Provenance and migration policy version are preserved.
- Replay and duplicate-in-batch are idempotent.
- Invalid/missing fields are handled explicitly.
- Dry-run reporting is available before any future commit phase.
- Supported JSON top-level shapes are explicit.

## Non-goals
- No live import of production JSON yet.
- No canonical entity creation/merge.
- No PostgreSQL/PostGIS implementation.
- No production switch to V2.

## Rollback
Revert this packet commit; no V1 or production data is modified.
