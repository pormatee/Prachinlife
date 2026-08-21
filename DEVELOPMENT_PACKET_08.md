# Development Packet #8 — Publication Policy + Published Place View

## Goal
Create an explicit, deterministic publication boundary between internal canonical place data and consumer-visible place data.

## Constraints
- Do not modify frozen PrachinLife V1 production files or behavior.
- Discovery, verification, and canonical adoption must not publish automatically.
- Publication must be versioned and side-effect free in this packet.
- Required high-impact fields must be verified and must match canonical values.
- Closed/inactive/unknown lifecycle records are not published by the default policy.
- Published views expose consumer-safe place fields only; no evidence/source/revision internals.
- No database/vendor dependency and no production integration.

## Tests
- Previous V2 regression suite remains green.
- Active, complete, verified canonical place becomes eligible.
- Missing/non-verified/mismatched required evidence blocks publication.
- Non-active or incomplete place blocks publication.
- Verifications for another place do not count.
- Blocked decisions cannot produce a published view.
- Published view excludes evidence/source/revision internals.
- Publication does not mutate CanonicalPlace.
- Publication policy/version and timezone-aware timestamp are enforced.

## Non-goals
- No web/UI integration.
- No persistent publication table yet.
- No automatic scheduling/re-publication.
- No search ranking/recommendation.
- No category-specific publication workaround.

## Rollback
This packet adds only V2 files/tests and can be reverted independently from the frozen V1 baseline.
