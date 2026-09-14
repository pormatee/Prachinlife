# Architecture Alignment V1 — Wave 4A API Transport Boundary

Status: MIGRATION_SLICE

Canonical LocalLife API V1 transport implementation moved from:

`place_platform_v2/locallife_api_v1.py`

to:

`place_platform_v2/api/locallife_v1.py`

The historical module remains as a compatibility entrypoint.

For imported use, the historical module name aliases directly to the canonical
module object. This is required to preserve existing monkeypatch and symbol
binding behavior; a simple symbol-copy wrapper was explicitly rejected by the
Wave 4A compatibility probe because three API tests exposed binding drift.

The historical launch command remains supported:

`python -m place_platform_v2.locallife_api_v1`

The canonical transport implementation changes only package-relative import
paths required by its new physical depth. Regional imports point to the
canonical Regional Runtime Boundary completed in Wave 3.

Application-service extraction is intentionally deferred to Waves 4B and 4C.

No HTTP route, response contract, CORS rule, body-size rule, decision behavior,
regional behavior, database path, canonical/published data, or production web
asset is intentionally changed.
