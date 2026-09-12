# LocalLife W1.0 — Prachinburi Expansion Target + Intake Contract V1

Status: **IMPLEMENTATION CONTRACT / NO PRODUCTION DATA MUTATION**

## Objective

Increase useful Prachinburi place coverage without weakening the current
verification, adoption, publication, sponsor-neutrality, or fail-closed rules.

W1.0 only defines expansion priorities and the pre-resolution intake boundary.
It does not add places to production yet.

## Audited baseline and target floors

Target floors are coverage goals, **not publication quotas**.

| Canonical category | Audited baseline | Target floor | Gap | Priority |
|---|---:|---:|---:|---:|
| restaurant | 30 | 60 | 30 | 1 |
| vegetarian | 2 | 15 | 13 | 1 |
| cafe | 25 | 45 | 20 | 2 |
| attraction | 5 | 20 | 15 | 2 |
| nature | 1 | 10 | 9 | 2 |
| clinic | 2 | 10 | 8 | 2 |
| pharmacy | 1 | 10 | 9 | 2 |
| park | 5 | 15 | 10 | 3 |

`fuel` is deliberately excluded from W1 expansion because the audited
Prachinburi Published baseline already contains 111 fuel places.

A place contributes to a target only after the normal
verification/adoption/publication path succeeds.

## Candidate intake boundary

A discovery candidate may enter entity resolution only when:

- province is `ปราจีนบุรี`;
- at least one canonical category is in the W1 target set;
- source is traceable by `source_record_id` or `source_url`;
- coordinates are present for the W1 near-me-capable expansion path.

Candidates lacking traceability or coordinates are held for enrichment, not
silently accepted. Out-of-scope province/category candidates are rejected from
this W1 batch, not deleted from their source.

Legacy Published presentation data cannot be submitted as new evidence.

## Mandatory data path

`Source Candidate -> Intake Triage -> Entity Resolution/Dedup -> Field Evidence -> Verification -> Adoption -> Canonical -> Publication Gate -> Published Projection`

No discovery/intelligence engine may write Canonical or Published directly.

## Dedup / entity resolution rules for W1.1+

Before evidence is attached:

- resolve against existing stable `place_id`;
- never create a second place only because category wording differs;
- use coordinates/name/address/contact as resolution signals;
- ambiguous matches fail closed to review;
- legacy Published may be used as a lookup aid but not as independent evidence.

## Existing trust policy remains unchanged

The current `VerificationPolicy` requires two independent sources for
`VERIFIED`. The current `AdoptionPolicy` requires `VERIFIED` for
`canonical_name`, `location`, `province`, `categories`, and `lifecycle`.

W1 must not lower those thresholds to hit coverage targets.

## Exit from W1.0

W1.0 is complete when:

- target policy is installed;
- intake guard tests pass;
- no production DB mutation occurs;
- no legacy-bundle write path is added;
- current verification/adoption thresholds remain unchanged.

Next: **W1.1 — Prachinburi Discovery Batch + Entity Resolution Dry Run**.

