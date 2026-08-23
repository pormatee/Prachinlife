# Phase 4.4 — Pre-Canonical Evidence Persistence

Goal: persist evidence for VERIFIED_IDENTITY new-place candidates without creating canonical places.

Current scope:
- ต้นหลิวอาหารเจ: VERIFIED_IDENTITY -> eligible
- มังสวิรัติ🥕🥦🍞🫘: SUPPORTED_IDENTITY -> excluded until a second independent source is found

Persistence model:
- precanonical_candidates: candidate identity holding area
- precanonical_evidence: append/idempotent source observations linked to the candidate
- deterministic UUIDs prevent replay duplicates
- lifecycle conflict is retained, not auto-resolved

Safety:
- places table unchanged
- place_evidence table unchanged
- all existing non-precanonical tables unchanged
- no Production JSON writes
- no automatic canonical creation
- no automatic publication
- trust policy unchanged
