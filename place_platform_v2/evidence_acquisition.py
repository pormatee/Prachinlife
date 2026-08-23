from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from .models import EvidenceKind, PlaceEvidence
from .osm_adapter import element_to_candidate, osm_record_id
from .osm_live import fetch_overpass
from .sqlite_store import SQLitePlaceRepository

POLICY_VERSION = "3.3-osm-evidence-acquisition-v1"
TARGET_FIELDS = ("phone", "website")
_OSM_RECORD_RE = re.compile(r"^osm-(node|way|relation)-(\d+)$")
_NAME_CLEAN_RE = re.compile(r"[^0-9a-zก-๙]+", re.I)
MAX_IDENTITY_DISTANCE_M = 250.0


@dataclass(frozen=True)
class AcquisitionTarget:
    rank: int
    dataset: str
    record_id: str
    place_id: str
    canonical_name: str
    osm_type: str
    osm_id: int


@dataclass(frozen=True)
class AcquiredClaim:
    rank: int
    place_id: str
    canonical_name: str
    field_name: str
    value: str
    evidence_id: str
    source_type: str
    source_name: str
    source_record_id: str
    source_url: str
    status: str


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _name_key(value: str | None) -> str:
    text = (value or "").strip().casefold()
    text = _NAME_CLEAN_RE.sub("", text)
    aliases = {
        "ปั๊มคาลเท็กซ์": "caltex",
        "สถานีบริการคาลเท็กซ์": "caltex",
        "คาลเท็กซ์": "caltex",
        "caltex": "caltex",
        "ปั๊มบางจาก": "bangchak",
        "สถานีบริการบางจาก": "bangchak",
        "บางจาก": "bangchak",
        "bangchak": "bangchak",
        "bangchakstation": "bangchak",
    }
    if text in aliases:
        return aliases[text]
    if "คาลเท็กซ์" in text or "caltex" in text:
        return "caltex"
    if "บางจาก" in text or "bangchak" in text:
        return "bangchak"
    return text


def _distance_m(a: GeoPoint | None, b: GeoPoint | None) -> float | None:
    if a is None or b is None:
        return None
    r = 6371008.8
    p1 = math.radians(a.latitude)
    p2 = math.radians(b.latitude)
    dp = math.radians(b.latitude - a.latitude)
    dl = math.radians(b.longitude - a.longitude)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * (2 * math.atan2(math.sqrt(h), math.sqrt(1 - h)))


def parse_osm_target(record_id: str) -> tuple[str, int] | None:
    match = _OSM_RECORD_RE.fullmatch((record_id or "").strip())
    if not match:
        return None
    return match.group(1), int(match.group(2))


def build_osm_acquisition_targets(plan: dict[str, Any]) -> tuple[AcquisitionTarget, ...]:
    targets: list[AcquisitionTarget] = []
    for item in plan.get("queue") or ():
        parsed = parse_osm_target(str(item.get("record_id") or ""))
        if parsed is None:
            continue
        actions = item.get("actions") or {}
        if not any(
            str((actions.get(field) or {}).get("next_step") or "") == f"acquire_new_{field}_evidence"
            for field in TARGET_FIELDS
        ):
            continue
        osm_type, osm_id = parsed
        targets.append(
            AcquisitionTarget(
                rank=int(item.get("rank") or len(targets) + 1),
                dataset=str(item.get("dataset") or ""),
                record_id=str(item.get("record_id") or ""),
                place_id=str(item.get("place_id") or ""),
                canonical_name=str(item.get("name") or ""),
                osm_type=osm_type,
                osm_id=osm_id,
            )
        )
    return tuple(sorted(targets, key=lambda x: (x.rank, x.record_id)))


def build_exact_osm_query(targets: Iterable[AcquisitionTarget]) -> str:
    rows = tuple(targets)
    if not rows:
        raise ValueError("at least one OSM acquisition target is required")
    body = "\n".join(f"  {item.osm_type}({item.osm_id});" for item in rows)
    return f"[out:json][timeout:120];\n(\n{body}\n);\nout center tags;"


def _place_map(database_path: str | Path, place_ids: Iterable[str]):
    ids = set(place_ids)
    db = Path(database_path)
    # Repository may initialize metadata, so use direct sqlite read through helper row decoding.
    import sqlite3
    con = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT * FROM places ORDER BY place_id").fetchall()
        return {
            row["place_id"]: SQLitePlaceRepository._place_from_row(row)
            for row in rows
            if row["place_id"] in ids
        }
    finally:
        con.close()


def _candidate_evidence(*, target: AcquisitionTarget, candidate, field: str, value: str, observed_at: datetime):
    return PlaceEvidence(
        place_id=target.place_id,
        source=SourceRef(
            source_type=SourceType.OSM,
            source_name="OpenStreetMap current observation",
            source_record_id=candidate.source.source_record_id,
            source_url=candidate.source.source_url,
            observed_at=observed_at,
        ),
        kind=EvidenceKind.CONTACT,
        field_name=field,
        value=value,
        status=EvidenceStatus.CANDIDATE,
        observed_at=observed_at,
        metadata={
            "acquisition": "phase3_3_osm_reobservation",
            "policy_version": POLICY_VERSION,
            "production_dataset": target.dataset,
            "production_record_id": target.record_id,
        },
    )


def acquire_osm_contact_evidence(
    *,
    database_path: str | Path,
    targeted_plan_path: str | Path,
    fetcher: Callable[[str], Any] | None = None,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Safely re-observe exact OSM objects for missing contact evidence.

    This function is read-only with respect to the canonical DB and production files.
    It emits candidate evidence in the report only. Identity mismatches, moved objects,
    missing elements, and empty contact tags are never adopted or stored.
    """
    observed_at = observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")

    db_before = _sha256(database_path)
    plan = _load_json(targeted_plan_path)
    targets = build_osm_acquisition_targets(plan)
    query = build_exact_osm_query(targets) if targets else None

    if not targets:
        return {
            "mode": "READ_ONLY_OSM_EVIDENCE_ACQUISITION",
            "policy_version": POLICY_VERSION,
            "target_count": 0,
            "queried_osm_target_count": 0,
            "matched_target_count": 0,
            "candidate_claim_count": 0,
            "candidate_field_counts": {},
            "blocked_counts": {},
            "claims": [],
            "targets": [],
            "safety": {
                "canonical_writes": False,
                "evidence_writes": False,
                "production_json_writes": False,
                "trust_policy_lowered": False,
                "database_unchanged": True,
                "database_sha256_before": db_before,
                "database_sha256_after": db_before,
            },
        }

    if fetcher is None:
        def fetcher(q: str):
            return fetch_overpass(q, max_retries=1)

    try:
        fetched = fetcher(query)
    except Exception as exc:
        db_after = _sha256(database_path)
        return {
            "mode": "READ_ONLY_OSM_EVIDENCE_ACQUISITION",
            "policy_version": POLICY_VERSION,
            "source_available": False,
            "acquisition_complete": False,
            "source_error": f"{type(exc).__name__}: {exc}",
            "target_count": len(targets),
            "queried_osm_target_count": len(targets),
            "returned_osm_element_count": 0,
            "matched_target_count": 0,
            "candidate_claim_count": 0,
            "candidate_field_counts": {},
            "blocked_counts": {"source_unavailable": len(targets)},
            "query": query,
            "claims": [],
            "targets": [
                {**asdict(target), "matched": False, "blocked_reason": "source_unavailable"}
                for target in targets
            ],
            "next_stage": "retry_source_acquisition_without_changing_trust_policy",
            "safety": {
                "canonical_writes": False,
                "evidence_writes": False,
                "production_json_writes": False,
                "trust_policy_lowered": False,
                "candidate_only": True,
                "database_unchanged": db_before == db_after,
                "database_sha256_before": db_before,
                "database_sha256_after": db_after,
            },
        }
    elements = fetched.elements if hasattr(fetched, "elements") else fetched
    if isinstance(elements, dict):
        elements = elements.get("elements") or []
    if not isinstance(elements, (list, tuple)):
        raise ValueError("fetcher must return elements or an object with .elements")

    by_record: dict[str, dict[str, Any]] = {}
    for element in elements:
        if not isinstance(element, dict):
            continue
        try:
            by_record[osm_record_id(element)] = element
        except ValueError:
            continue

    places = _place_map(database_path, (t.place_id for t in targets))
    claims: list[PlaceEvidence] = []
    target_rows: list[dict[str, Any]] = []
    blocked = Counter()
    matched = 0

    for target in targets:
        expected_osm_record = f"{target.osm_type}/{target.osm_id}"
        element = by_record.get(expected_osm_record)
        row: dict[str, Any] = {
            **asdict(target),
            "expected_osm_record_id": expected_osm_record,
            "matched": False,
            "name_compatible": None,
            "distance_m": None,
            "acquired_fields": [],
            "blocked_reason": None,
        }
        if element is None:
            row["blocked_reason"] = "osm_object_not_returned"
            blocked["osm_object_not_returned"] += 1
            target_rows.append(row)
            continue
        place = places.get(target.place_id)
        if place is None:
            row["blocked_reason"] = "canonical_place_missing"
            blocked["canonical_place_missing"] += 1
            target_rows.append(row)
            continue
        candidate = element_to_candidate(element, observed_at=observed_at)
        if candidate is None:
            row["blocked_reason"] = "osm_object_has_no_named_place_candidate"
            blocked["osm_object_has_no_named_place_candidate"] += 1
            target_rows.append(row)
            continue

        name_ok = _name_key(place.canonical_name) == _name_key(candidate.name)
        distance = _distance_m(place.location, candidate.location)
        row["name_compatible"] = name_ok
        row["distance_m"] = round(distance, 1) if distance is not None else None
        if not name_ok:
            row["blocked_reason"] = "identity_name_conflict"
            blocked["identity_name_conflict"] += 1
            target_rows.append(row)
            continue
        if distance is None or distance > MAX_IDENTITY_DISTANCE_M:
            row["blocked_reason"] = "identity_location_conflict_or_missing"
            blocked["identity_location_conflict_or_missing"] += 1
            target_rows.append(row)
            continue

        row["matched"] = True
        matched += 1
        for field in TARGET_FIELDS:
            value = getattr(candidate, field)
            if value:
                claims.append(_candidate_evidence(
                    target=target,
                    candidate=candidate,
                    field=field,
                    value=value,
                    observed_at=observed_at,
                ))
                row["acquired_fields"].append(field)
        if not row["acquired_fields"]:
            row["blocked_reason"] = "osm_has_no_missing_contact_tags"
            blocked["osm_has_no_missing_contact_tags"] += 1
        target_rows.append(row)

    field_counts = Counter(item.field_name for item in claims)
    serialized_claims = []
    for item in claims:
        serialized_claims.append({
            "evidence_id": item.evidence_id,
            "place_id": item.place_id,
            "field_name": item.field_name,
            "value": item.value,
            "kind": item.kind.value,
            "status": item.status.value,
            "observed_at": item.observed_at.isoformat(),
            "source": {
                "source_type": item.source.source_type.value,
                "source_name": item.source.source_name,
                "source_record_id": item.source.source_record_id,
                "source_url": item.source.source_url,
                "observed_at": item.source.observed_at.isoformat(),
            },
            "metadata": dict(item.metadata),
        })

    db_after = _sha256(database_path)
    return {
        "mode": "READ_ONLY_OSM_EVIDENCE_ACQUISITION",
        "policy_version": POLICY_VERSION,
        "source_available": True,
        "acquisition_complete": True,
        "source_error": None,
        "target_count": len(targets),
        "queried_osm_target_count": len(targets),
        "returned_osm_element_count": len(by_record),
        "matched_target_count": matched,
        "candidate_claim_count": len(serialized_claims),
        "candidate_field_counts": dict(sorted(field_counts.items())),
        "blocked_counts": dict(sorted(blocked.items())),
        "query": query,
        "claims": serialized_claims,
        "targets": target_rows,
        "next_stage": "verification_and_controlled_adoption_dry_run",
        "safety": {
            "canonical_writes": False,
            "evidence_writes": False,
            "production_json_writes": False,
            "trust_policy_lowered": False,
            "candidate_only": True,
            "database_unchanged": db_before == db_after,
            "database_sha256_before": db_before,
            "database_sha256_after": db_after,
        },
    }
