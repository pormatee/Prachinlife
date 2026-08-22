# Development Packet 14 — Phase 2S.4 Admin Field Contract

## Goal
Define the single validation/intake boundary that a future Admin Web must use for place-detail edits.

## Safety boundary
Admin edits **do not write canonical fields directly**. Every accepted edit becomes `CANDIDATE` `PlaceEvidence` with a required traceable source name and source URL. Existing verification → adoption → publication boundaries remain unchanged.

## Fields
The contract covers canonical identity/location/contact fields plus the Phase 2S.3 completeness priorities: district, subdistrict, area, opening hours, phone, website, real image, and description.

## Validation
URLs require HTTP(S), coordinates use `GeoPoint`, categories are normalized, lifecycle uses the existing enum, blank values are rejected, and unknown fields are rejected.

## Non-goals
No Admin UI, no database mutation, no production switch, no automatic verification, and no automatic publication.
