# Architecture Alignment V1 — Wave 6A CBI Shadow Adapter

Canonical LocalLife integration boundary:

`place_platform_v2.cbi.adapter_v1`

External owner:

`pormatee/MEasyMate_CBI`

Pinned CBI runtime:

- Version: `1.0.0`
- Commit: `0c35f4b81bdb928939c73b2cb669f3ec3f756f51`
- LocalLife Domain Pack: `1.1.0`

## Authority contract

CBI may provide:

- intent
- slots/entities
- conversation context/state
- reference resolution
- confidence
- ambiguity
- clarification

CBI must not:

- rank places
- choose a place
- score candidates
- write canonical data
- write publication data
- write projection data
- make LocalLife business decisions

LocalLife Project Brain / MSB / DQE retains decision authority.

## Wave 6A mode

`SHADOW`

The adapter output has no production effect.

Wave 6A does not modify:

- `web_ai_runtime_v1.py`
- existing semantic production behavior
- API behavior
- published/canonical data
- SQLite paths
- PrachinLife web
- production cutover

No external AI provider is allowed through this adapter.

CBI V1 remains owned and developed in the separate MEasyMate CBI repository.
