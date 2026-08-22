# Phase 2U.3.3.5 — Review Diff Semantics Fix

- Separates legacy seed/baseline data from operator changes.
- Review shows only fields actually changed/added by Admin in the actionable diff.
- Description and real-image changes are explicit.
- Legacy create-candidate review renders baseline Card instead of an empty 'new place' box.
- Direct internal media URL is preferred by Admin preview renderer, with master-image fallback.
- Canonical DB and publication remain unchanged/disabled.
