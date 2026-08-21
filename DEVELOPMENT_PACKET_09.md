# Development Packet #9 — Published Repository / Search Read Model

## Goal
Create a consumer-facing read boundary that serves only `PublishedPlaceView`
records to PrachinLife, future local brands, and AI consumers. Near Me and text
search must operate on the published read model rather than internal canonical
records.

## Constraints
- Do not modify PrachinLife V1 production files or frozen V1 behavior.
- Do not expose canonical records, evidence, source records, or revisions.
- Search remains deterministic and storage-neutral.
- Near Me remains a first-class platform capability.
- Province/category filters are context inputs, not hard-coded local forks.
- No database vendor dependency in this packet.
- No production integration or automatic publication.

## Tests / Acceptance
- Published repository stores only consumer-safe published views.
- Near Me filters by radius/category/province and orders by distance.
- Text search works across safe published fields.
- Upsert/remove semantics support publication refresh/unpublish.
- Internal evidence/revision data is absent from search results.
- Invalid search queries fail deterministically.
- All prior V2 regression tests remain green.

## Non-goals
- PostgreSQL/PostGIS implementation.
- Ranking/recommendation scoring.
- Natural-language intent parsing.
- Production API/UI integration.

## Checkpoint
All V2 tests pass and the patch only adds Packet #9 read-model files/tests/docs.
