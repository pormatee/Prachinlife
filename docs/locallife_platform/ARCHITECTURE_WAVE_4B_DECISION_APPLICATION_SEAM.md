# Architecture Alignment V1 — Wave 4B Decision Application Service Seam

Status: MIGRATION_SLICE

Wave 4B introduces the LocalLife application-service package and moves decision
request validation/orchestration semantics behind:

`place_platform_v2/application/decision_service_v1.py`

The HTTP transport remains:

`place_platform_v2/api/locallife_v1.py`

The transport acts as the composition root for the existing runtime callables.
It injects the current decision runtime and decision-action decorator into the
application service. This preserves historical monkeypatch/symbol-binding
behavior while removing the decision orchestration rules from HTTP transport.

Compatibility requirements preserved:

- `place_platform_v2.locallife_api_v1` remains an alias to canonical API.
- API `decision_payload(payload)` signature is unchanged.
- API `decision_response_payload(payload)` signature is unchanged.
- Patching `_run_master_brain_decision` on the API module still affects
  `decision_payload`.
- Patching `decision_payload` on the API module still affects
  `decision_response_payload`.
- Patching `attach_decision_actions_v1` on the API module still affects
  `decision_response_payload`.

The application service does not import HTTP transport, `web_ai_runtime_v1`,
database/published repositories, or regional modules directly.

No CBI work is included in this wave.
No business logic, ranking, candidate selection, publication behavior, data,
HTTP route, response envelope, or production asset is intentionally changed.
