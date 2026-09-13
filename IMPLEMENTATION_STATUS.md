# LocalLife Platform + PrachinLife Regional Reference Model
## Implementation Status — 2026-09-13

Status: **TARGETED VERIFIED / CURRENT REPO HAS PRE-EXISTING DATA-READINESS REGRESSION / INSTALLER V3 READY FOR DIFFERENTIAL GATE**

### Implemented locally

- L0.1 `RegionalProductV1` strict read-only contract + registry.
- PrachinLife regional product declaration (`th-prachinburi`, `TH-25`).
- Synthetic second-region fixture proving region-agnostic loading.
- L0.2 generic `RegionalReferencePackV1` adapter.
- PrachinLife source/intake, entity-key, one-way taxonomy and web presentation configs.
- `RegionalWebContextV1` with no place records embedded.
- Web V1.0 GET seam: `/v1/regions/{region_slug}/context`.
- Existing `/v1/health` and `/v1/decision` behavior retained by targeted HTTP regression tests.
- Regional context is GET-only; POST creates no new write surface.
- Unknown region -> 404 fail-closed.
- Invalid regional config -> sanitized 503; internal details are not exposed.

### Targeted verification

Command:

```bash
python -m unittest \
  tests_v2.test_v2_regional_product_v1 \
  tests_v2.test_v2_regional_reference_adapter_v1 \
  tests_v2.test_v2_locallife_api_regional_context_v1 -v
```

Result: **Ran 34 tests — OK**.

This targeted verification is green. On the current repository HEAD `e007b77`, the user also ran the full `tests_v2` suite before LocalLife was applied: **1611 tests ran with 10 failures and 11 errors**. The installer rolled LocalLife back. A focused no-patch rerun reproduced the readiness/comparative failures, confirming that the current HEAD already has a pre-existing data/readiness regression.

### Guardrails preserved

- No production data mutation.
- No direct Canonical write.
- No direct Published write.
- No verification/adoption/publication bypass.
- No pairwise EntityResolutionEngine redesign.
- No `if Prachinburi` branch in generic regional modules.
- W0.7 one-way taxonomy behavior preserved.
- Region/query scope is not promoted into evidence truth.
- Existing root `index.html` is not replaced and `/` is not cut over.

### Blockers

1. Current PrachinLife HEAD `e007b77` is not full-regression green before LocalLife: current data/readiness checks fail, including changed visible-place count and comparative/canonical consistency.
2. Production readiness therefore remains blocked independently of LocalLife.
3. No production cutover is allowed while those baseline failures remain.

### Required gate before CLOSED_VERIFIED

Installer V3 uses a differential gate because the current HEAD is already red. It must prove: (1) the 34 LocalLife targeted tests pass, (2) the post-patch full-regression failing-test set is exactly identical to the isolated pre-patch baseline, and (3) no test-generated staging changes remain in the final working tree. This can justify a LocalLife checkpoint commit, but **not** `CLOSED_VERIFIED` and **not** production cutover while the pre-existing PrachinLife readiness regression remains.

### Next safe work after full regression

Create the additive `/prachinburi` shared web-shell prototype and wire it to the regional context endpoint without changing existing `/` behavior. Do not perform production consumer cutover in the same step.

## Installer V3 isolated baseline + side-effect cleanup
V2 exposed an existing test behavior: the full regression writes `data/v2/staging/user_web/manifest.json` and `prachinlife_index.json`. V3 therefore runs the baseline suite in a detached temporary Git worktree so those mutations never touch the target checkout. After applying LocalLife, it runs the 34 targeted tests and the full suite, requires the failing-test signature to be exactly identical to baseline, then restores the target to HEAD and re-applies only the audited LocalLife files. Any changed failure set or unexpected final path causes rollback. Existing baseline failures are reported as `BASELINE_REGRESSION_PRESENT=TRUE`; production readiness remains blocked.

## Installer V4 fix
- Baseline regression runs in an isolated temporary Git worktree.
- Post-patch regression failure set must exactly match baseline.
- Known test side effects are cleaned before the final patch state is rebuilt.
- Final allowlist validation now uses `git status --porcelain=v1 --untracked-files=all` so Git reports individual additive files instead of collapsing new directories such as `docs/`, `regional_products/`, and `tests_v2/fixtures/`.
- This fixes the V3 false rollback; it does not weaken the allowlist or fail-closed behavior.
