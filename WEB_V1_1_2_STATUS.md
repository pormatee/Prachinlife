# LocalLife Web V1.1.2 Navigation Escape Fix

Status target: differential regression verified, mobile preview pending.

## Why
Web V1.1.1 could temporarily trap a user on a sub-page while Regional Context was loading or unavailable because the bottom navigation stayed disabled until the API contract loaded.

## Change
- Add API-independent sub-page controls: `← ย้อนกลับ` and `⌂ หน้าหลัก`.
- Back uses same-origin browser history when available and otherwise falls back to the regional home route.
- Regional home route is derived only from the validated `data-region` slug; no named-region logic is added to the shared shell.
- Preserve the approved `apiBase` query parameter on fallback/home navigation.
- Keep the Home escape route enabled during loading and fail-closed error states; other Regional Context-owned routes remain disabled when context is unavailable.
- No place data is embedded, no canonical read/write is added, and production `/` remains untouched.

## Verification gate
- Web static contract suite: 16 tests expected PASS.
- Existing LocalLife L0/Web V1.0 targeted suite: 34 tests expected PASS.
- Full `tests_v2` failing-test signature must be identical before and after this patch.
- Production cutover remains FALSE.
