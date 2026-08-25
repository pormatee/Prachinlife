"""Human/User Evidence V1 for Core Place Verification V2.

Category-agnostic reviewed-human path for exact place coordinates.
Human submissions are append-only review candidates. They cannot change the
canonical place or public export until an admin review is explicitly approved
and a separate controlled apply is executed.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_VERSION = "human-place-evidence-v1"
PENDING_STATE = "VERIFIED_PLACE_COORDINATE_PENDING"
READY_STATE = "VERIFIED_NEAR_ME_READY"
ALLOWED_SOURCE_KINDS = frozenset({"user", "admin"})
ALLOWED_REVIEW_BASES = frozenset({
    "admin_on_site",
    "admin_map_pin_review",
    "user_evidence_admin_review",
})
_NAMESPACE = uuid.UUID("31ba73d7-c4e9-4d3d-8d21-09ea665536b6")

SCHEMA = """
CREATE TABLE IF NOT EXISTS human_place_evidence_queue (
    submission_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    field_name TEXT NOT NULL,
    value_json TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_reference TEXT,
    evidence_note TEXT NOT NULL,
    status TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    reviewed_by TEXT,
    review_note TEXT,
    review_basis TEXT,
    coordinate_owner_confirmed INTEGER NOT NULL DEFAULT 0,
    reviewed_at TEXT,
    applied_at TEXT,
    policy_version TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_human_place_evidence_status
    ON human_place_evidence_queue(status, submitted_at);
CREATE INDEX IF NOT EXISTS idx_human_place_evidence_place
    ON human_place_evidence_queue(place_id, status);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _sha(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _state_from_revisions(con: sqlite3.Connection, place_id: str) -> str | None:
    rows = con.execute(
        "SELECT after_values_json FROM place_revisions WHERE place_id=? ORDER BY created_at DESC,rowid DESC",
        (place_id,),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row[0] or "{}")
        except Exception:
            continue
        state = str(payload.get("core_v2_state") or "").strip()
        if state:
            return state
    return None


def _valid_coordinates(latitude: Any, longitude: Any) -> tuple[float, float]:
    lat = float(latitude)
    lon = float(longitude)
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise ValueError("coordinates out of range")
    return lat, lon


def _submission_id(place_id: str, source_kind: str, source_name: str,
                   latitude: float, longitude: float, submitted_at: str) -> str:
    raw = "|".join((place_id, source_kind, source_name, f"{latitude:.8f}", f"{longitude:.8f}", submitted_at))
    return str(uuid.uuid5(_NAMESPACE, "submission|" + raw))


def _evidence_id(submission_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, "canonical-evidence|" + submission_id))


def _revision_id(submission_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, "coordinate-revision|" + submission_id))


def ensure_schema(database_path: str | Path) -> None:
    con = sqlite3.connect(database_path)
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.executescript(SCHEMA)
        con.commit()
    finally:
        con.close()


def submit_coordinate_evidence(
    *, database_path: str | Path, place_id: str, latitude: Any, longitude: Any,
    source_kind: str, source_name: str, evidence_note: str,
    source_reference: str | None = None, submitted_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a human coordinate claim to review queue; never canonicalize it."""
    lat, lon = _valid_coordinates(latitude, longitude)
    kind = str(source_kind or "").strip().casefold()
    if kind not in ALLOWED_SOURCE_KINDS:
        raise ValueError("source_kind must be user or admin")
    name = str(source_name or "").strip()
    note = str(evidence_note or "").strip()
    if not name or not note:
        raise ValueError("source_name and evidence_note are required")
    when = submitted_at or _now_iso()
    try:
        dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError("submitted_at must be ISO-8601") from exc
    if dt.tzinfo is None:
        raise ValueError("submitted_at must be timezone-aware")
    when = dt.astimezone(timezone.utc).isoformat()

    ensure_schema(database_path)
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys=ON")
        place = con.execute("SELECT * FROM places WHERE place_id=?", (place_id,)).fetchone()
        if place is None:
            raise KeyError("unknown canonical place_id")
        state = _state_from_revisions(con, place_id)
        if state != PENDING_STATE:
            raise ValueError(f"human coordinate submission requires {PENDING_STATE}; got {state!r}")
        if place["latitude"] is not None or place["longitude"] is not None:
            raise ValueError("coordinate-pending place must not already have canonical coordinates")

        sid = _submission_id(place_id, kind, name, lat, lon, when)
        cur = con.execute(
            """INSERT OR IGNORE INTO human_place_evidence_queue(
                submission_id,place_id,field_name,value_json,source_kind,source_name,
                source_reference,evidence_note,status,submitted_at,policy_version,metadata_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid, place_id, "location", _json({"latitude": lat, "longitude": lon}),
             kind, name, source_reference, note, "pending_review", when,
             POLICY_VERSION, _json(metadata or {})),
        )
        con.commit()
        return {
            "status": "PENDING_REVIEW",
            "submission_id": sid,
            "inserted": max(cur.rowcount, 0) == 1,
            "canonical_mutation": False,
            "automatic_approval": False,
            "automatic_publication": False,
            "near_me_enabled": False,
            "trust_policy_lowered": False,
            "category_agnostic": True,
        }
    finally:
        con.close()


def review_coordinate_evidence(
    *, database_path: str | Path, submission_id: str, approve: bool,
    reviewer: str, review_note: str, review_basis: str | None = None,
    coordinate_owner_confirmed: bool = False, reviewed_at: str | None = None,
) -> dict[str, Any]:
    """Record explicit admin review. Approval requires candidate-owned exact pin confirmation."""
    ensure_schema(database_path)
    reviewer = str(reviewer or "").strip()
    note = str(review_note or "").strip()
    if not reviewer or not note:
        raise ValueError("reviewer and review_note are required")
    basis = str(review_basis or "").strip()
    if approve:
        if basis not in ALLOWED_REVIEW_BASES:
            raise ValueError("approved review requires an allowed review_basis")
        if not coordinate_owner_confirmed:
            raise ValueError("approved coordinate requires coordinate_owner_confirmed=true")
    when = reviewed_at or _now_iso()

    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT * FROM human_place_evidence_queue WHERE submission_id=?",
            (submission_id,),
        ).fetchone()
        if row is None:
            raise KeyError("unknown submission_id")
        if row["status"] != "pending_review":
            raise ValueError("submission is not pending review")
        new_status = "approved" if approve else "rejected"
        con.execute(
            """UPDATE human_place_evidence_queue
               SET status=?,reviewed_by=?,review_note=?,review_basis=?,
                   coordinate_owner_confirmed=?,reviewed_at=?
               WHERE submission_id=? AND status='pending_review'""",
            (new_status, reviewer, note, basis or None,
             1 if coordinate_owner_confirmed else 0, when, submission_id),
        )
        con.commit()
        return {
            "status": new_status.upper(),
            "submission_id": submission_id,
            "canonical_mutation": False,
            "automatic_publication": False,
            "trust_policy_lowered": False,
        }
    finally:
        con.close()


def apply_approved_coordinate_evidence(
    *, database_path: str | Path, submission_id: str, commit: bool = False,
    applied_at: str | None = None,
) -> dict[str, Any]:
    """Controlled canonical coordinate activation after approved human review."""
    ensure_schema(database_path)
    db = Path(database_path)
    before_hash = _sha(db)
    when = applied_at or _now_iso()
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        row = con.execute(
            "SELECT * FROM human_place_evidence_queue WHERE submission_id=?",
            (submission_id,),
        ).fetchone()
        if row is None:
            raise KeyError("unknown submission_id")
        if row["status"] == "applied":
            return {
                "status": "ALREADY_APPLIED", "submission_id": submission_id,
                "canonical_mutation": False, "near_me_eligible": True,
                "automatic_publication": False, "trust_policy_lowered": False,
            }
        if row["status"] != "approved":
            raise ValueError("only approved evidence may be applied")
        if not row["coordinate_owner_confirmed"]:
            raise ValueError("approved evidence lacks coordinate ownership confirmation")
        if row["review_basis"] not in ALLOWED_REVIEW_BASES:
            raise ValueError("approved evidence lacks valid review basis")
        state = _state_from_revisions(con, row["place_id"])
        if state != PENDING_STATE:
            raise ValueError(f"canonical place is not coordinate pending: {state!r}")
        value = json.loads(row["value_json"])
        lat, lon = _valid_coordinates(value["latitude"], value["longitude"])
        place = con.execute("SELECT * FROM places WHERE place_id=?", (row["place_id"],)).fetchone()
        if place is None:
            raise KeyError("canonical place missing")
        if place["latitude"] is not None or place["longitude"] is not None:
            raise ValueError("canonical coordinates already present")

        result = {
            "status": "READY_TO_APPLY" if not commit else "APPLIED",
            "submission_id": submission_id,
            "place_id": row["place_id"],
            "latitude": lat, "longitude": lon,
            "state_before": PENDING_STATE, "state_after": READY_STATE,
            "near_me_eligible": bool(commit),
            "canonical_mutation": bool(commit),
            "automatic_publication": False,
            "trust_policy_lowered": False,
            "category_agnostic": True,
        }
        if not commit:
            con.close()
            return {**result, "database_unchanged": before_hash == _sha(db)}

        con.execute("BEGIN IMMEDIATE")
        eid = _evidence_id(submission_id)
        rid = _revision_id(submission_id)
        metadata = {
            "human_submission_id": submission_id,
            "source_kind": row["source_kind"],
            "reviewed_by": row["reviewed_by"],
            "review_basis": row["review_basis"],
            "coordinate_owner_confirmed": True,
            "human_review_policy_version": POLICY_VERSION,
            "automatic_publication": False,
        }
        con.execute(
            """INSERT OR IGNORE INTO place_evidence(
                evidence_id,place_id,source_type,source_name,source_record_id,source_url,
                source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, row["place_id"], "human_reviewed", row["source_name"], submission_id,
             row["source_reference"], row["submitted_at"], "location", "location",
             row["value_json"], "verified", when, _json(metadata)),
        )
        con.execute(
            "UPDATE places SET latitude=?,longitude=?,updated_at=? WHERE place_id=?",
            (lat, lon, when, row["place_id"]),
        )
        con.execute(
            """INSERT OR IGNORE INTO place_revisions(
                revision_id,place_id,changed_fields_json,before_values_json,
                after_values_json,reason,evidence_ids_json,policy_version,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (rid, row["place_id"], _json(["latitude", "longitude", "core_v2_state"]),
             _json({"latitude": None, "longitude": None, "core_v2_state": PENDING_STATE}),
             _json({"latitude": lat, "longitude": lon, "core_v2_state": READY_STATE}),
             "Reviewed human evidence activated exact candidate coordinates",
             _json([eid]), POLICY_VERSION, when),
        )
        con.execute(
            "UPDATE human_place_evidence_queue SET status='applied',applied_at=? WHERE submission_id=?",
            (when, submission_id),
        )
        con.commit()
        return result
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            con.close()
        except Exception:
            pass


def list_review_queue(database_path: str | Path, *, status: str = "pending_review") -> list[dict[str, Any]]:
    ensure_schema(database_path)
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT * FROM human_place_evidence_queue WHERE status=? ORDER BY submitted_at,submission_id",
            (status,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["value"] = json.loads(item.pop("value_json"))
            item["metadata"] = json.loads(item.pop("metadata_json"))
            result.append(item)
        return result
    finally:
        con.close()
