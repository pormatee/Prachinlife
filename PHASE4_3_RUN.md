# Phase 4.3 — Independent Evidence + Identity Verification

Goal: verify Phase 4.2 new-place candidates using independent source families before any Central DB creation.

Current outcomes:
- มังสวิรัติ🥕🥦🍞🫘 -> SUPPORTED_IDENTITY
  - Wongnai + Wongnai delivery count as one source family
  - needs a second independent source before new-place creation
- ต้นหลิวอาหารเจ -> VERIFIED_IDENTITY
  - independent source families: Vegetarian Thailand directory, Restaurant Guru, Facebook official page, Wongnai
  - phone identity is corroborated by multiple sources
  - lifecycle/open-vs-closed conflict remains explicitly flagged and is NOT auto-resolved

Safety:
- no database writes
- no evidence writes
- no canonical writes
- no Production writes
- no automatic place creation
- source-family independence enforced
- cross-province generic-name collisions do not block candidates
- trust policy unchanged
