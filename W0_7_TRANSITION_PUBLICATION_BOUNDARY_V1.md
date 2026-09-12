# LocalLife W0.7 — Transition Publication Boundary V1

Status: **IMPLEMENTATION CONTRACT / NO PRODUCTION DATA MUTATION**

## Audited transition baseline

- Canonical total: 923
- Published total: 923
- ID overlap: 923
- Canonical lifecycle: 923 `unknown`
- Legacy Published lifecycle: 923 `active`
- Prachinburi: 221 Canonical / 221 Published / 221 ID overlap
- Prachinburi canonical↔published name mismatch: 0
- phone mismatch: 0
- website mismatch: 0
- coordinate mismatch: 0
- canonical address missing while legacy display address exists: 220
- category representation mismatch: 219/221
- lifecycle two-source quorum: 0

These counts identify a migration/publication-lineage transition. They do **not**
authorize bulk activation or copying legacy presentation data into Canonical.

## Boundary rules

1. Existing legacy Published baseline remains readable during transition.
2. No bulk `unknown -> active`.
3. No legacy Published field may be written back to Canonical by this boundary.
4. Legacy display address is presentation fallback only and is not evidence.
5. Canonical category codes remain source-of-truth taxonomy.
6. Thai/finer web category labels are one-way presentation mapping only.
7. New or updated place data must follow:
   `Candidate+Evidence -> Verification/Entity Resolution -> Canonical -> Publication Gate -> Published Projection`.
8. New/updated data must not enter legacy bundle files.
9. Unknown boundary operations fail closed.
10. W0.7 itself has no SQLite/database write authority and does not switch production consumers.

## Initial one-way presentation taxonomy

- `fuel` → `ปั๊มน้ำมัน`
- `temple` → `วัด / ศาสนสถาน`
- `restaurant` → `ร้านอาหาร`
- `cafe` → `คาเฟ่`
- `park` → `สวน / พื้นที่พักผ่อน`
- `laundry` → `ซักรีด`
- `car_repair` → `ซ่อมรถ`
- `clinic` → `คลินิก`
- `vegetarian` → `vegetarian`
- `pharmacy` → `ร้านยา`
- `nature` → `ธรรมชาติ / จุดชมวิว`
- `attraction` → `สถานที่ท่องเที่ยว`

Legacy fine-grained labels such as museum/history remain legacy presentation
labels until a future canonical subtype taxonomy is explicitly designed. There
is deliberately no reverse mapping API.

## Exit from W0.7

W0.7 is complete when the contract/module and guard tests are committed with:
- targeted tests PASS;
- no production DB mutation;
- no production consumer switch;
- no new legacy-bundle write path.

Next work: **W1 Prachinburi Data Expansion**.

