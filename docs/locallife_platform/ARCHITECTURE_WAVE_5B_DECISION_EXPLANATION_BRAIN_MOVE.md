# Architecture Wave 5B — Decision Explanation Brain Move

Canonical module: `place_platform_v2.decision.explanation_brain_v1`

Historical compatibility module: `place_platform_v2.decision_explanation_brain_v1`

The implementation moves one package level deeper, so the sole approved source
adjustment is the relative import of `candidate_comparison_brain_v1` from `.`
to `..`. No decision logic changes are permitted.

Safety: single module only; compatibility path retained; no CBI, runtime, API,
data/SQLite, protected PrachinLife web, or production root changes. Full
regression is required before push.
