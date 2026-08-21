# Development Packet #12.1 — Production Audit Scope Correction

## Goal
Correct Packet #12 after the first real Termux audit revealed that recursive auto-discovery included historical backups/archive/candidate datasets, inflating migration population and duplicate counts. Add schema-key diagnostics without guessing legacy aliases.

## Constraints
- V1 production data remains read-only.
- No database writes and no production integration.
- Default auto-discovery audits only root-level index JSON files; historical datasets require explicit paths.
- Do not infer province/category from unknown keys until observed from production schema diagnostics.
- Preserve all previous V2 contracts and regression tests.

## Acceptance
- Historical nested JSON is excluded from default audit.
- Explicit file paths remain auditable.
- Per-file top-level key frequencies are included for migration mapping diagnostics.
- Full V2 regression passes.
