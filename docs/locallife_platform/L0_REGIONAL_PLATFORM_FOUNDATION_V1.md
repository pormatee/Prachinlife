# LocalLife Platform + PrachinLife Regional Reference Model
## L0 Regional Platform Foundation V1

Status: **PHASE STARTED / ADDITIVE ONLY / NO PRODUCTION CUTOVER**
Date: 2026-09-13

### Baseline
- Repository: `pormatee/Prachinlife`
- Checked remote HEAD before L0.1: `e007b77dea35d3c6358096d33045c66623554669`
- Latest architecture/code commit before that data update: `5a5bea1dceda708dd29dfd665c9d9f805260cbc9`
- Existing `place_platform_v2` remains the domain core.
- Existing W0.7 publication boundary, W1 verification/adoption policy and W1.1E aggregation semantics remain authoritative.
- Existing `/v1/decision` behavior remains authoritative.

### Architecture decision
`LocalLife Platform -> Regional Product Contract -> Regional Pack -> Existing Domain Core`

PrachinLife is the first Regional Reference Model. The platform core must not import named Prachinburi configuration.

### L0.1 scope
Adds only:
- `RegionalProductV1` declaration parser/validator
- `RegionalProductRegistryV1`
- PrachinLife regional product declaration
- synthetic second-region fixture
- targeted contract tests

L0.1 does not alter candidate normalization, entity resolution, evidence, verification, adoption, Canonical, publication, Published Projection, MSB/DQE/Semantic behavior or the existing web/API contract.

### Safety invariants
1. Unknown or malformed declarations fail closed.
2. `fail_closed=true` is mandatory.
3. `human_final_decision=true` is mandatory.
4. `direct_canonical_write=false` is mandatory.
5. `direct_published_write=false` is mandatory.
6. Configuration refs must be safe relative POSIX paths under `regional_products/`.
7. A second-region fixture must validate through the same contract without core changes.
8. PrachinLife compatibility is preserved; no route or consumer cutover is authorized.

### Next work after L0.1 targeted PASS
L0.2 — add the PrachinLife Regional Reference Adapter and config files (`sources.json`, `entity_keys.json`, `taxonomy.json`, `web.json`) as a thin compatibility layer. Then run full existing regression before Web V1.0 Regional Context Seam.
