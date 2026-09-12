# LocalLife W1.1 — Prachinburi Discovery Batch + Entity Resolution Dry Run V1

Status: **READ-ONLY LIVE DISCOVERY / NO PRODUCTION MUTATION**

W1.1 starts real external candidate discovery while preserving the W1.0 boundary.
It reuses `OSMPlaceAdapterV2`, W1.0 intake, `EntityResolutionEngine`,
`CanonicalResolutionOrchestrator`, and read-only canonical loading. It introduces
no competing dedup policy.

The first live OSM batch intentionally maps only high-confidence categories:
`restaurant`, `cafe`, `vegetarian`, `clinic`, and `pharmacy`.
`attraction`, `nature`, and `park` remain W1 targets but are deferred until their
broader OSM taxonomy gets an explicit mapping decision rather than being guessed.

The Overpass query is scoped to `ISO3166-2=TH-25`. For this dry run only, that
administrative scope supplies Prachinburi to intake/resolution when individual
OSM records omit `addr:province`. The candidate is marked that this is not an
explicit source province claim. No evidence is persisted.

Resolution semantics remain central and fail-closed:
- `matched`: exactly one deterministic canonical match and no review match.
- `review`: ambiguous or review-required comparison.
- `new`: no canonical match under the current deterministic policy.

`new` means candidate only. It is not verified, active, canonical, or published.

W1.1 also repairs the existing read-only categories decoder to support the V2
`{"__type__":"tuple","items":[...]}` SQLite representation while retaining
compatibility with plain JSON arrays. This is decoding only and performs no DB write.

The live run writes JSON and CSV diagnostic reports to Android Download. It must
finish with unchanged Canonical hash and zero evidence/canonical/publication writes.

Next after reviewing the live counts/samples: W1.2 Evidence Verification +
Controlled Adoption design for useful candidates with sufficient independent support.
