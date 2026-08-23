# PrachinLife V2 Phase 11 Final Diagnostic / Freeze Strategy

Base checkpoint: `d724fe4` (Phase 11 Loop 2).

## Final decision
Phase 11 closes on **verified coverage + durable enrichment pipeline**, not on forcing every one of 220 places to have every field.

Current minimum accepted coverage after Loops 1–2:
- address 2
- area 1
- district 2
- subdistrict 2
- opening_hours 3
- phone 5
- website 27
- description 1
- real_image 0

`real_image=0` is intentionally acceptable at freeze. A page containing an image is not sufficient proof that a reusable direct image URL represents the exact place. No image is synthesized, guessed, scraped blindly, or promoted from candidate evidence. Place Detail continues to use the existing verified-real-image → Master Image fallback contract.

Official-source verification used in Loop 2 includes Fine Arts Department pages for Prachinburi National Museum contact information and Si Mahosot ancient city descriptive information. Phase 11 Final adds no new canonical values and performs no production switch.

## Freeze gates
1. exactly 220 published Prachinburi places
2. no coverage regression below Loop 2
3. public evidence-backed detail fields have supported/verified provenance
4. supported detail evidence has traceable source_name plus URL/record ID
5. candidate/rejected/stale evidence cannot appear as public detail provenance
6. real image remains fail-closed
7. Master Image fallback remains installed
8. full V2 regression passes
9. JS syntax passes
10. no automatic canonical adoption, trust-policy lowering, or production switch
