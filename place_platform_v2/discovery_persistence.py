from __future__ import annotations
import json, sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from .contracts import EvidenceStatus

@dataclass(frozen=True)
class PersistenceResult:
    matched_attached: int
    new_places_created: int
    review_skipped: int
    duplicate_observations_skipped: int

def _key(obs):
    c, s = obs.candidate, obs.candidate.source
    raw = "|".join([
        s.source_type.value,
        s.source_name.strip().casefold(),
        (s.source_record_id or "").strip().casefold(),
        c.candidate_key,
    ])
    return sha256(raw.encode("utf-8")).hexdigest()

def _dump(value):
    if hasattr(value, "latitude") and hasattr(value, "longitude"):
        value = {"latitude": value.latitude, "longitude": value.longitude}
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

def ensure_ledger(con):
    con.execute(
        "CREATE TABLE IF NOT EXISTS discovery_imports ("
        "observation_key TEXT PRIMARY KEY,"
        "source_type TEXT NOT NULL,"
        "source_name TEXT NOT NULL,"
        "source_record_id TEXT,"
        "candidate_key TEXT NOT NULL,"
        "place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,"
        "resolution_outcome TEXT NOT NULL,"
        "imported_at TEXT NOT NULL)"
    )

def _new_place(con, obs):
    c = obs.candidate
    place_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    lat = c.location.latitude if c.location else None
    lon = c.location.longitude if c.location else None
    con.execute(
        "INSERT INTO places("
        "place_id,canonical_name,latitude,longitude,address_text,province,"
        "categories_json,phone,website,lifecycle,created_at,updated_at"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            place_id, c.name, lat, lon, c.address_text, c.province,
            json.dumps(tuple(c.categories), ensure_ascii=False),
            c.phone, c.website, "unknown", now, now,
        ),
    )
    return place_id

def _evidence(con, place_id, obs):
    now = datetime.now(timezone.utc).isoformat()
    for claim in obs.claims:
        s = claim.source
        con.execute(
            "INSERT INTO place_evidence("
            "evidence_id,place_id,source_type,source_name,source_record_id,"
            "source_url,source_observed_at,kind,field_name,value_json,status,"
            "observed_at,metadata_json"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(uuid4()), place_id, s.source_type.value, s.source_name,
                s.source_record_id, s.source_url, s.observed_at.isoformat(),
                claim.kind.value, claim.field_name, _dump(claim.value),
                EvidenceStatus.CANDIDATE.value, now,
                json.dumps({"discovery_v2": True}, ensure_ascii=False),
            ),
        )

def persist_resolution_report(database_path, report):
    con = sqlite3.connect(Path(database_path).resolve())
    con.execute("PRAGMA foreign_keys=ON")
    matched = created = review = duplicate = 0
    try:
        con.execute("BEGIN IMMEDIATE")
        ensure_ledger(con)
        for item in report.items:
            if item.outcome.value == "review":
                review += 1
                continue
            key = _key(item.observation)
            if con.execute(
                "SELECT 1 FROM discovery_imports WHERE observation_key=?",
                (key,),
            ).fetchone():
                duplicate += 1
                continue
            if item.outcome.value == "matched":
                if not item.matched_place_id:
                    raise ValueError("matched item requires matched_place_id")
                place_id = item.matched_place_id
                matched += 1
            elif item.outcome.value == "new":
                place_id = _new_place(con, item.observation)
                created += 1
            else:
                raise ValueError("unsupported outcome")
            _evidence(con, place_id, item.observation)
            s = item.observation.candidate.source
            con.execute(
                "INSERT INTO discovery_imports("
                "observation_key,source_type,source_name,source_record_id,"
                "candidate_key,place_id,resolution_outcome,imported_at"
                ") VALUES (?,?,?,?,?,?,?,?)",
                (
                    key, s.source_type.value, s.source_name, s.source_record_id,
                    item.observation.candidate.candidate_key, place_id,
                    item.outcome.value, datetime.now(timezone.utc).isoformat(),
                ),
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return PersistenceResult(matched, created, review, duplicate)
