# Phase 4.9 — Continue Discovery Batch

Goal: continue Prachinburi vegetarian/jay coverage discovery in batches without being blocked by manual-review candidates.

Pipeline:
source observations -> candidate grouping -> canonical duplicate screening -> pending screening
-> prior-discovery screening -> new-candidate verification queue

Current batch:
- source observations: 6
- candidate groups: 5
- existing canonical: 1
- known prior discovery candidate: 1
- pending manual review: 1
- new discovery candidates: 2

New candidates:
1. ร้านอาหารเจ AMITA VEGAN
   - independent source families: 2
   - ready for batch identity verification
   - geolocation still needs evidence before canonical adoption
2. ฉันทนา
   - independent source families: 1
   - needs a second independent source

Other outcomes:
- อาหารเจ ปราจีนบุรี -> existing canonical match via shared phone with อาหารเจ ซั่นสี่
- มังสวิรัติ🥕🥦🍞🫘 -> known discovery candidate; do not rediscover
- ต้นหลิวอาหารเจ -> pending manual review; skipped without blocking discovery

Safety:
- read-only DB
- no canonical/precanonical/pending writes
- no Production writes
- no automatic adoption/publication
- trust policy unchanged
