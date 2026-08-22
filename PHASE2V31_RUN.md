# PrachinLife V2 Phase 2V.3.1 — Create Candidate Resolution Diagnostic

Read-only diagnostic for an Approved `create_place_candidate` that Phase 2V.3 blocks as duplicate/review.

It compares the candidate with every canonical place using the existing deterministic entity-resolution engine and prints only relevant `same_entity` / `review` comparisons, including canonical place id/name, coordinates, distance, score, signals, and reason.

It does not modify canonical DB, draft/review DB, adoption policy, publication/export, V1 JSON, or User Web.

Run:

```bash
python scripts/diagnose_create_candidate_resolution.py --draft-id <DRAFT_ID>
```
