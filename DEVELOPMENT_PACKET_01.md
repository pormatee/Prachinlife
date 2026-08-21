# Development Packet #1 — Discovery V2 Foundation

## Goal
Create an isolated, versioned foundation for a country-wide Local Place Intelligence Platform V2 without changing PrachinLife V1 production behavior.

## Frozen baseline
- Tag: `prachinlife-platform-v1`
- Commit: `6810d4c7e6ba88d911162720b715d2ee7528cf7f`
- V1 is immutable.

## Constraints
- No changes to frozen V1 core.
- No production UI or JSON index integration.
- No category-specific workaround.
- V2 must be source-extensible.
- Discovery must not directly imply publication.
- Provenance is mandatory at the source-candidate boundary.
- No new dependency is introduced in Packet #1.

## Tests / Acceptance criteria
1. V2 namespace imports independently.
2. Frozen V1 tag/commit is recorded exactly and marked immutable.
3. Geographic coordinates have deterministic validity checks.
4. Every discovered candidate has source provenance and a non-blank name.
5. Future/unknown sources have an extensibility path.
6. Discovery candidate is non-publishable by default.
7. Candidate/rejected states cannot be marked publishable.
8. Supported/verified states may pass an explicit publish policy.
9. Tests run using Python standard library only.
10. No V1 production file is included in this change set.

## Non-goals
- Database implementation.
- OSM/Web adapter implementation.
- Deduplication/entity resolution.
- Confidence scoring.
- Search API.
- Production integration.

## Next checkpoint
Packet #2 should define the canonical Place / Evidence data model and persistence boundary before choosing the concrete database implementation.
