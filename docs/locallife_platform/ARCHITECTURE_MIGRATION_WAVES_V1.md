# LocalLife / PrachinLife Architecture Alignment V1 — Migration Waves

## Wave 0 — Protect current R6 working checkpoint
Status: PASS
- local backup created outside repository
- no repository files moved
- no files deleted
- no data mutation

## Wave 1 — Architecture manifest only
Goal:
- add ownership contract
- add path manifest
- add migration-wave plan
- zero runtime changes
- zero data changes

Exit gate:
- only new documentation/manifest files introduced by Wave 1
- protected runtime/data hashes unchanged

## Wave 2 — Regional presentation alignment
Goal:
- keep public `/prachinburi/*` routes stable
- treat `regional_products/prachinburi/web/` as canonical regional presentation implementation
- retain compatibility references
- preserve current R6 UX

Exit gate:
- PrachinLife visual/AI regression tests pass
- root production `index.html` unchanged
- no domain/data mutation

## Wave 3 — LocalLife Regional Runtime boundary
Goal:
- introduce `place_platform_v2/regional/`
- migrate `regional_*` modules one at a time
- old module paths become compatibility wrappers

Exit gate:
- targeted regional tests pass
- full regression does not worsen baseline

## Wave 4 — LocalLife API / Application boundary
Goal:
- introduce `place_platform_v2/api/` and `application/`
- keep `place_platform_v2/locallife_api_v1.py` as stable entrypoint wrapper
- behavior remains unchanged

## Wave 5 — Publication / Decision boundaries
Goal:
- introduce `publication/` and `decision/`
- migrate code only; database paths remain frozen in Alignment V1
- no canonical/published data rewrite as part of relocation

## Wave 6 — CBI integration
Only after architecture alignment checkpoints are stable.

Flow:
PrachinLife Web -> LocalLife API -> LocalLife CBI Adapter
-> pinned MEasyMate CBI Runtime -> LocalLife Project Brain
-> Published Read Model

Rollout:
SHADOW -> verify -> ACTIVE

CBI remains shared infrastructure; PrachinLife does not own CBI Core.
