# PrachinLife V2 — Phase 2V.3 Create Candidate Adoption

Safety boundary:
- only the latest **Approved** `create_place_candidate` is eligible;
- entity resolution must return `NEW`; `MATCHED` or `REVIEW` is blocked;
- `canonical_name`, `location`, `province`, and `categories` each need active `SUPPORTED` or `VERIFIED` evidence;
- one approved human-reviewed source may establish `SUPPORTED` initial canonical data, but does **not** become a second independent source;
- commit is insert-only and atomic: canonical place + all admin evidence + creation revision + idempotency receipt + entity-resolution audit;
- no JSON export, published read model, or User Web publication occurs in Phase 2V.3.

Dry-run one approved create candidate:
```bash
python scripts/commit_approved_create_candidate.py --draft-id <APPROVED_DRAFT_ID>
```

Explicit internal canonical commit after inspecting dry-run:
```bash
python scripts/commit_approved_create_candidate.py --commit --draft-id <APPROVED_DRAFT_ID>
```

Then run full regression:
```bash
python -m unittest discover -s tests_v2 -p 'test_*.py'
```
