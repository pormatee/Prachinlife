# Architecture Wave 5D — Pathum Decision Reference Model Move

## Role

The Pathum Thani model is retained as the LocalLife Decision Reference Model
for realistic shop-search decision scenarios.

It is not discarded and it is not converted into publication logic.

## Canonical module

`place_platform_v2.decision.scenarios.real_pathum_v1`

## Historical compatibility module

`place_platform_v2.real_pathum_decision_scenarios_v1`

## Architectural reason

The module proves the end-to-end decision behavior using controlled Pathum
scenario fixtures while calling the real LocalLife decision and presentation
chain. It belongs under the Decision domain, but separately under `scenarios/`
so reference scenarios do not mix with core decision engines.

## Safety contract

- Scenario/business behavior must remain unchanged.
- Only package-relative imports may change because the module moves two levels deeper.
- Historical import path remains supported.
- No CBI changes.
- No `web_ai_runtime_v1.py` changes.
- No publication/read-model logic changes.
- No data or SQLite changes.
- No protected PrachinLife web changes.
- Root production `index.html` remains unchanged.
- Full regression is required before push.
