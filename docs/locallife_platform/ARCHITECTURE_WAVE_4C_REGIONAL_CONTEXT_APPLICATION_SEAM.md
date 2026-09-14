# Architecture Alignment V1 — Wave 4C Regional Context Application Service Seam

Status: MIGRATION_SLICE

Wave 4C moves the regional-context orchestration seam behind:

`place_platform_v2/application/regional_context_service_v1.py`

The HTTP transport remains:

`place_platform_v2/api/locallife_v1.py`

The API remains the composition root and injects the existing canonical regional
runtime loader into the application service. This preserves the current
regional runtime and HTTP error-mapping contracts while removing the regional
context orchestration function from transport.

Compatibility requirements preserved:

- `place_platform_v2.locallife_api_v1` remains an alias to canonical API.
- API `regional_context_response_payload(region_slug)` signature is unchanged.
- Patching `regional_context_payload_v1` on the API module still affects the
  application-service call.
- Patching `regional_context_response_payload` on the API module still affects
  the HTTP handler because the handler continues to call the API-level wrapper.
- Regional product exceptions remain transport-facing because the HTTP layer
  maps them to existing status/error envelopes.

The application service does not import HTTP transport, regional runtime,
regional product contracts, repositories, databases, decision runtime, or CBI.

No business logic, regional lookup behavior, error envelope, route, data,
production asset, or CBI behavior is intentionally changed.
