# LocalLife / PrachinLife Architecture Ownership V1

Status: FROZEN_FOR_ALIGNMENT_V1
Purpose: define architectural ownership before any source relocation.

## Ownership model

### LocalLife Core
Shared platform/domain layer used by all regional products.

Owns:
- public API boundary
- application orchestration
- Project Brain / decision services
- intake / verification / adoption
- canonical data access
- published read model access
- regional runtime/adapter
- shared contracts
- CBI integration adapter/boundary

Does not own:
- PrachinLife-specific branding or visual presentation
- shared CBI Core implementation
- external intelligence engines

### PrachinLife Regional Product
Regional product/pilot for Prachinburi.

Owns:
- regional product config
- regional taxonomy/source configuration
- Prachinburi-specific presentation/branding
- regional web entry points
- regional presentation assets
- region-specific domain configuration

Must not:
- duplicate LocalLife databases
- duplicate LocalLife Project Brain
- call AI providers directly
- become the owner of CBI Core

### MEasyMate CBI
Shared conversation-intelligence infrastructure.

Owns:
- conversation act / intent interpretation
- conversation context/state
- topic change
- stable reference resolution
- confidence / clarification

Does not:
- rank places
- make LocalLife business decisions
- write canonical/published data
- replace Project Brain

Logical integration:
PrachinLife Web -> LocalLife API -> LocalLife CBI Adapter
-> pinned MEasyMate CBI Runtime -> LocalLife Project Brain
-> Published Read Model

### Intelligence Engines
Examples: Promo Intelligence / discovery engines.

Own:
- discovery / candidate/evidence generation in their own project boundary.

Must enter LocalLife through contracts/intake.
Must not direct-write LocalLife canonical/published data.

## Protected compatibility boundaries for Alignment V1

The following paths remain stable during Alignment V1:
- `/prachinburi/`
- `/prachinburi/search/`
- `/prachinburi/eat/`
- `/prachinburi/go/`
- `/prachinburi/services/`
- `data/v2/place_platform_v2.sqlite3`
- `data/v2/decision_published_places_v1.sqlite3`
- existing Python import paths until compatibility wrappers are in place

## Non-negotiable migration rules

1. No deletion in the first migration checkpoint.
2. No SQLite relocation in Architecture Alignment V1.
3. No business-logic change inside a pure move step.
4. Every moved Python module keeps a compatibility import path until callers migrate.
5. Every wave must be independently reversible.
6. Known regression baseline must not be hidden by changing expected values.
7. Production cutover remains false until a separate readiness gate passes.
