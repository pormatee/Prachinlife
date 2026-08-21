# Development Packet #4 — Source Adapter + Discovery Ingestion Contract

## Goal
Create the storage- and source-neutral ingestion boundary that allows OSM, Web,
Manual and future sources to enter Place Platform V2 through one contract.

## Constraints
- Do not modify frozen V1 or production behavior.
- Do not publish or mutate CanonicalPlace during ingestion.
- Preserve source provenance for every observation and field claim.
- Do not make category-specific ingestion paths.
- Do not bind to a database, network client, or third-party SDK.
- Keep entity resolution/dedup authority out of ingestion.

## Acceptance tests
- Existing Packet #1–#3 regression tests remain green.
- Blank discovery query is rejected.
- Normalization and candidate fingerprinting are deterministic.
- Source provenance is preserved.
- Adapter/source mismatches are rejected.
- Evidence claim drafts are field-level and source-backed.
- Manual and future sources use the same pipeline as OSM/Web.
- Ingestion does not mutate source raw attributes.

## Non-goals
- No live OSM/Web/API requests.
- No canonical entity merge.
- No verification/confidence scoring.
- No database implementation.
- No production integration.

## Rollback
This packet adds one V2 module, one V2 test module, and this document only.
Reverting the packet commit removes all behavior introduced here.
