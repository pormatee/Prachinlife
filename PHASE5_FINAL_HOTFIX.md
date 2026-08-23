# Phase 5 Final — Test Isolation Hotfix

Root cause:
The Phase 5 operational run intentionally commits `operational_work_queue` before
full regression. The test fixture copied that already-mutated real database and
incorrectly assumed the queue table was absent and empty.

Fix:
Each Phase 5 Final test now copies the real SQLite database and drops only
`operational_work_queue` inside the temporary test database before each test.

This changes test isolation only. Operational queue logic, canonical data,
pre-canonical data, and Production data are unchanged.
