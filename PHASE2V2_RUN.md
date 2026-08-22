# PrachinLife V2 — Phase 2V.2 Controlled Canonical Commit

## Safety model
- Default command remains dry-run only.
- Commit requires both `--commit` and one explicit `--draft-id`.
- Phase 2V.2 supports `update_place_candidate` only; new-place creation remains blocked.
- Approved evidence + canonical field revisions + adoption receipt commit in one SQLite transaction.
- Idempotency receipt prevents applying the same draft twice.
- CLI creates a canonical DB backup before commit and restores it on failure.
- Publication/export is not performed.

## Dry-run
`python scripts/commit_approved_adoption.py`

## Controlled commit
`python scripts/commit_approved_adoption.py --commit --draft-id <APPROVED_DRAFT_ID>`

After commit, verify canonical data/revision first. Public User data does not change until Phase 2W publication/export.
