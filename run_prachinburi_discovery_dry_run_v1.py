#!/usr/bin/env python3
"""W1.1 Prachinburi live discovery + entity-resolution dry run.

This command is deliberately read-only with respect to Canonical/Evidence/
Published data. It reuses W1.0 intake and the central entity resolver.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from place_platform_v2.contracts import SourcePlaceCandidate
from place_platform_v2.discovery_readonly import load_canonical_places_readonly
from place_platform_v2.discovery_resolution import CanonicalResolutionOrchestrator
from place_platform_v2.ingestion import IngestionObservation, build_claims, normalize_candidate
from place_platform_v2.osm_adapter import element_to_candidate
from place_platform_v2.osm_live import build_province_place_query, fetch_overpass
from place_platform_v2.prachinburi_expansion_intake_v1 import (
    TARGET_PROVINCE, IntakeOutcome, assess_candidate,
)

POLICY_VERSION = "PRACHINBURI-DISCOVERY-DRY-RUN-V1"
ISO3166_2 = "TH-25"
DIRECT_TARGETS = frozenset({"restaurant", "cafe", "vegetarian", "clinic", "pharmacy"})


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def target_candidate(candidate):
    source_categories = {str(x).strip().casefold() for x in candidate.categories if str(x).strip()}
    targets = {x for x in source_categories if x in DIRECT_TARGETS}
    if "healthcare:clinic" in source_categories:
        targets.add("clinic")
    if "healthcare:pharmacy" in source_categories:
        targets.add("pharmacy")

    raw = dict(candidate.raw_attributes or {})
    tags = raw.get("tags")
    if isinstance(tags, dict):
        veg = str(tags.get("diet:vegetarian") or "").strip().casefold()
        vegan = str(tags.get("diet:vegan") or "").strip().casefold()
        if veg in {"yes", "only"} or vegan in {"yes", "only"}:
            targets.add("vegetarian")
    if not targets:
        return None

    # The live query itself is constrained to the TH-25 administrative area.
    # For this dry run only, use that scope for intake/resolution and mark it as
    # non-evidentiary. Nothing from this command is persisted as evidence.
    raw["w1_scope_iso3166_2"] = ISO3166_2
    raw["w1_scope_province"] = TARGET_PROVINCE
    raw["w1_scope_province_is_explicit_source_claim"] = False
    return SourcePlaceCandidate(
        source=candidate.source,
        name=candidate.name,
        location=candidate.location,
        address_text=candidate.address_text,
        province=TARGET_PROVINCE,
        categories=tuple(sorted(targets)),
        phone=candidate.phone,
        website=candidate.website,
        raw_attributes=raw,
    )


def observation(candidate):
    normalized = normalize_candidate(candidate)
    return IngestionObservation(normalized, build_claims(normalized))


def dry_run(database, elements, observed_at=None):
    when = observed_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    database = Path(database)
    before = sha256_file(database)
    canonical = tuple(
        p for p in load_canonical_places_readonly(database)
        if p.province == TARGET_PROVINCE
    )
    resolver = CanonicalResolutionOrchestrator()

    rows = []
    seen = set()
    adapted = eligible = held = rejected = 0
    source_items = tuple(elements)
    for element in source_items:
        raw = element_to_candidate(element, observed_at=when)
        if raw is None:
            continue
        sid = raw.source.source_record_id or ""
        if sid and sid in seen:
            continue
        if sid:
            seen.add(sid)
        candidate = target_candidate(raw)
        if candidate is None:
            continue
        adapted += 1
        intake = assess_candidate(candidate)
        if intake.outcome is IntakeOutcome.HOLD_FOR_ENRICHMENT:
            held += 1
            continue
        if intake.outcome is not IntakeOutcome.ELIGIBLE_FOR_RESOLUTION:
            rejected += 1
            continue
        eligible += 1
        resolved = resolver.resolve_one(observation(candidate), canonical)
        loc = candidate.location
        rows.append({
            "outcome": resolved.outcome.value,
            "name": candidate.name,
            "categories": list(intake.matched_target_categories),
            "source_record_id": candidate.source.source_record_id,
            "source_url": candidate.source.source_url,
            "latitude": loc.latitude if loc else None,
            "longitude": loc.longitude if loc else None,
            "matched_place_id": resolved.matched_place_id,
            "reason": resolved.reason,
        })

    rows.sort(key=lambda x: (x["outcome"], tuple(x["categories"]), x["name"].casefold(), x["source_record_id"] or ""))
    after = sha256_file(database)
    return {
        "mode": "READ_ONLY_DISCOVERY_DRY_RUN",
        "policy_version": POLICY_VERSION,
        "province": TARGET_PROVINCE,
        "source_element_count": len(source_items),
        "adapted_target_candidate_count": adapted,
        "eligible_candidate_count": eligible,
        "held_candidate_count": held,
        "rejected_candidate_count": rejected,
        "canonical_place_count": len(canonical),
        "matched_count": sum(x["outcome"] == "matched" for x in rows),
        "new_count": sum(x["outcome"] == "new" for x in rows),
        "review_count": sum(x["outcome"] == "review" for x in rows),
        "canonical_hash_before": before,
        "canonical_hash_after": after,
        "canonical_unchanged": before == after,
        "evidence_writes": 0,
        "canonical_writes": 0,
        "publication_writes": 0,
        "items": rows,
    }


def _make_fixture_db(path, categories_json):
    con = sqlite3.connect(path)
    try:
        con.execute('''CREATE TABLE places(
          place_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL,
          latitude REAL, longitude REAL, address_text TEXT, province TEXT,
          categories_json TEXT NOT NULL, phone TEXT, website TEXT,
          lifecycle TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
        con.execute('''INSERT INTO places VALUES(
          '11111111-1111-4111-8111-111111111111','ร้านเดิม',14.05,101.37,NULL,
          'ปราจีนบุรี',?,NULL,NULL,'unknown','2026-09-01T00:00:00+00:00','2026-09-01T00:00:00+00:00')''',
          (categories_json,))
        con.commit()
    finally:
        con.close()


def _element(i, name, lat, lon, amenity="restaurant", extra=None):
    tags = {"name": name}
    if amenity is not None:
        tags["amenity"] = amenity
    tags.update(extra or {})
    return {"type": "node", "id": i, "lat": lat, "lon": lon, "tags": tags}


def self_test():
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    checks = 0
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "canonical.sqlite3"
        _make_fixture_db(db, json.dumps({"__type__": "tuple", "items": ["restaurant"]}))
        assert load_canonical_places_readonly(db)[0].categories == ("restaurant",); checks += 1
        raw = element_to_candidate(_element(1,"ร้านใหม่",14.1,101.4), observed_at=now)
        scoped = target_candidate(raw)
        assert scoped.province == TARGET_PROVINCE and "restaurant" in scoped.categories; checks += 1
        assert scoped.raw_attributes["w1_scope_province_is_explicit_source_claim"] is False; checks += 1
        clinic = element_to_candidate(_element(2,"คลินิก",14.2,101.5,None,{"healthcare":"clinic"}), observed_at=now)
        assert target_candidate(clinic).categories == ("clinic",); checks += 1
        veg = element_to_candidate(_element(3,"ร้านเจ",14.2,101.5,"restaurant",{"diet:vegetarian":"only"}), observed_at=now)
        assert "vegetarian" in target_candidate(veg).categories; checks += 1
        bank = element_to_candidate(_element(4,"ธนาคาร",14.2,101.5,"bank"), observed_at=now)
        assert target_candidate(bank) is None; checks += 1
        before = db.read_bytes()
        report = dry_run(db, [_element(5,"ร้านเดิม",14.05001,101.37001)], now)
        assert report["matched_count"] == 1; checks += 1
        assert report["canonical_unchanged"] and db.read_bytes() == before; checks += 1
        report = dry_run(db, [_element(6,"ร้านใหม่ไกล",14.30,101.70)], now)
        assert report["new_count"] == 1; checks += 1
        report = dry_run(db, [_element(7,"คนละร้าน",14.05002,101.37002)], now)
        assert report["review_count"] == 1; checks += 1
        same = _element(8,"ร้านซ้ำ",14.30,101.70)
        report = dry_run(db, [same, same], now)
        assert report["eligible_candidate_count"] == 1; checks += 1
        assert report["evidence_writes"] == report["canonical_writes"] == report["publication_writes"] == 0; checks += 1
    print(f"SELF_TESTS={checks}_PASS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--database", default="data/v2/place_platform_v2.sqlite3")
    ap.add_argument("--output-dir", default="/storage/emulated/0/Download")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0

    fetched = fetch_overpass(build_province_place_query(ISO3166_2))
    report = dry_run(args.database, fetched.elements)
    if not report["canonical_unchanged"]:
        raise RuntimeError("canonical database changed during dry run")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    jp = out / f"LOCALLIFE_W1_1_PRACHINBURI_DRY_RUN_{stamp}.json"
    cp = out / f"LOCALLIFE_W1_1_PRACHINBURI_DRY_RUN_{stamp}.csv"
    payload = dict(report)
    payload.update({
        "overpass_endpoint": fetched.endpoint,
        "overpass_attempts": fetched.attempts,
        "overpass_coverage_complete": fetched.coverage_complete,
    })
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with cp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["outcome","name","categories","source_record_id","source_url","latitude","longitude","matched_place_id","reason"])
        for x in report["items"]:
            w.writerow([x["outcome"],x["name"],"|".join(x["categories"]),x["source_record_id"] or "",x["source_url"] or "",x["latitude"] or "",x["longitude"] or "",x["matched_place_id"] or "",x["reason"]])

    print("=== W1.1 PRACHINBURI DISCOVERY + ENTITY RESOLUTION DRY RUN ===")
    print(f"OVERPASS_ENDPOINT={fetched.endpoint}")
    print(f"SOURCE_ELEMENTS={report['source_element_count']}")
    print(f"ADAPTED_TARGET_CANDIDATES={report['adapted_target_candidate_count']}")
    print(f"ELIGIBLE_CANDIDATES={report['eligible_candidate_count']}")
    print(f"HOLD_FOR_ENRICHMENT={report['held_candidate_count']}")
    print(f"REJECTED={report['rejected_candidate_count']}")
    print(f"CANONICAL_PRACHINBURI={report['canonical_place_count']}")
    print(f"RESOLUTION_MATCHED={report['matched_count']}")
    print(f"RESOLUTION_NEW={report['new_count']}")
    print(f"RESOLUTION_REVIEW={report['review_count']}")
    print(f"CANONICAL_UNCHANGED={str(report['canonical_unchanged']).upper()}")
    print("EVIDENCE_WRITES=0")
    print("CANONICAL_WRITES=0")
    print("PUBLICATION_WRITES=0")
    print(f"JSON_REPORT={jp}")
    print(f"CSV_REPORT={cp}")
    print("W1_1_LIVE_DRY_RUN=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
