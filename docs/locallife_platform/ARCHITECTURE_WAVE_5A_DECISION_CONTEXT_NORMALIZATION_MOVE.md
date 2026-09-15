# Architecture Wave 5A — Decision Context Normalization Move

## Scope

Move the pure decision-context normalization helper into the LocalLife
decision-domain package.

Canonical module:

`place_platform_v2.decision.context_normalization_v1`

Historical compatibility module:

`place_platform_v2.decision_context_normalization_v1`

## Safety contract

- No business-logic change.
- Canonical implementation is moved byte-for-byte.
- Historical import path remains supported.
- No CBI changes.
- No `web_ai_runtime_v1.py` changes.
- No API/application behavior changes.
- No data or SQLite changes.
- No protected PrachinLife web changes.
- Root production `index.html` remains unchanged.
- Targeted tests are required before checkpointing.

This is intentionally a single-module architectural slice.
