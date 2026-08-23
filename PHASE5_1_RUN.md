# Phase 5.1 — Coverage Cycle Orchestrator

Goal: provide one operational entry point over the frozen Phase 4 coverage/adoption machine.

The orchestrator runs the current coverage re-audit, evaluates all pre-canonical candidates through the controlled adoption gate, routes blockers into explicit work queues, and keeps discovery non-blocking. It defaults to read-only operation and requires an explicit --commit-adoption flag before the existing controlled adoption machine may write. It never publishes Production JSON, fabricates evidence, or auto-resolves conflicts.

Current cycle: canonical primary 1; accounted unique 8; pre-canonical 2; ready for adoption 0; work items 2. AMITA VEGAN routes to coordinate/manual confirmation; ต้นหลิวอาหารเจ routes to lifecycle/manual confirmation.

Targeted tests: 5/5 OK. Full regression must be run in the real repository.
