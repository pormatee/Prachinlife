"""SQLite reference persistence for Place Platform V2.

This module is a concrete, stdlib-only implementation of the repository
contracts. It is intentionally a reference store for local development,
regression tests, migration tooling, and small deployments. The domain model
remains storage-neutral so PostgreSQL/PostGIS can replace this implementation
without changing discovery, verification, adoption, publication, or consumers.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .adoption import PlaceRevision
from .contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from .models import CanonicalPlace, EvidenceKind, PlaceEvidence, PlaceIdentity, PlaceLifecycle
from .persistence import NearbyPlaceQuery, NearbyPlaceResult
from .publication import PublishedPlaceView
from .read_model import (
    PublishedNearbyQuery,
    PublishedNearbyResult,
    PublishedTextQuery,
    _distance_km,
    _matches_categories,
    _matches_province,
    _normal,
)
from .repository import _distance_km as _canonical_distance_km


SQLITE_SCHEMA_VERSION = "2.0-packet10"
MIGRATION_SCHEMA_VERSION = "1.0-packet13"


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.isoformat()


def _dt(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("stored datetime must be timezone-aware")
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, GeoPoint):
        return {"__type__": "GeoPoint", "latitude": value.latitude, "longitude": value.longitude}
    if isinstance(value, PlaceLifecycle):
        return {"__type__": "PlaceLifecycle", "value": value.value}
    if isinstance(value, tuple):
        return {"__type__": "tuple", "items": [_jsonable(item) for item in value]}
    if isinstance(value, frozenset):
        return {"__type__": "frozenset", "items": [_jsonable(item) for item in sorted(value, key=str)]}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported SQLite JSON value: {type(value).__name__}")


def _from_jsonable(value: Any) -> Any:
    if isinstance(value, list):
        return [_from_jsonable(item) for item in value]
    if not isinstance(value, dict):
        return value
    marker = value.get("__type__")
    if marker == "GeoPoint":
        return GeoPoint(float(value["latitude"]), float(value["longitude"]))
    if marker == "PlaceLifecycle":
        return PlaceLifecycle(value["value"])
    if marker == "tuple":
        return tuple(_from_jsonable(item) for item in value["items"])
    if marker == "frozenset":
        return frozenset(_from_jsonable(item) for item in value["items"])
    return {key: _from_jsonable(item) for key, item in value.items()}


def _dump(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load(value: str) -> Any:
    return _from_jsonable(json.loads(value))


_INTERNAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS platform_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    address_text TEXT,
    province TEXT,
    categories_json TEXT NOT NULL,
    phone TEXT,
    website TEXT,
    lifecycle TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS place_evidence (
    evidence_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_record_id TEXT,
    source_url TEXT,
    source_observed_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    field_name TEXT NOT NULL,
    value_json TEXT NOT NULL,
    status TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_place_evidence_place ON place_evidence(place_id);
CREATE TABLE IF NOT EXISTS place_revisions (
    revision_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    changed_fields_json TEXT NOT NULL,
    before_values_json TEXT NOT NULL,
    after_values_json TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_place_revisions_place ON place_revisions(place_id);
CREATE TABLE IF NOT EXISTS admin_adoption_receipts (
    draft_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    revision_ids_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    committed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_admin_adoption_receipts_place ON admin_adoption_receipts(place_id);
CREATE TABLE IF NOT EXISTS admin_candidate_resolution_audit (
    draft_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    operation TEXT NOT NULL,
    resolution_outcome TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    committed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_admin_candidate_resolution_place
    ON admin_candidate_resolution_audit(place_id);
CREATE TABLE IF NOT EXISTS admin_provenance_repairs (
    repair_id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    evidence_ids_json TEXT NOT NULL,
    before_json TEXT NOT NULL,
    after_json TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    repaired_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_provenance_repairs_draft
    ON admin_provenance_repairs(draft_id);
CREATE INDEX IF NOT EXISTS idx_admin_provenance_repairs_place
    ON admin_provenance_repairs(place_id);
CREATE TABLE IF NOT EXISTS canonical_geographic_corrections (
    proposal_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    province_before TEXT,
    province_after TEXT NOT NULL,
    supporting_lineages_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    revision_id TEXT NOT NULL REFERENCES place_revisions(revision_id) ON DELETE RESTRICT,
    policy_version TEXT NOT NULL,
    committed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_canonical_geographic_corrections_place
    ON canonical_geographic_corrections(place_id);
CREATE TABLE IF NOT EXISTS publication_verification_bundles (
    bundle_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_record_id TEXT,
    source_url TEXT,
    evidence_ids_json TEXT NOT NULL,
    lifecycle_before TEXT NOT NULL,
    lifecycle_after TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    committed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_publication_verification_bundles_place
    ON publication_verification_bundles(place_id);
CREATE TABLE IF NOT EXISTS migration_imports (
    import_key TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    candidate_key TEXT NOT NULL,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE RESTRICT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_migration_imports_place ON migration_imports(place_id);
"""


_PUBLISHED_SCHEMA = """
CREATE TABLE IF NOT EXISTS published_places (
    place_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    province TEXT NOT NULL,
    categories_json TEXT NOT NULL,
    lifecycle TEXT NOT NULL,
    address_text TEXT,
    phone TEXT,
    website TEXT,
    publication_policy_version TEXT NOT NULL,
    published_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_published_places_province ON published_places(province);
"""


class _SQLiteBase:
    def __init__(self, database: str | Path = ":memory:") -> None:
        self._connection = sqlite3.connect(str(database))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class SQLitePlaceRepository(_SQLiteBase):
    """SQLite implementation of the internal canonical/evidence repository."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        super().__init__(database)
        self._connection.executescript(_INTERNAL_SCHEMA)
        self._connection.execute(
            "INSERT OR REPLACE INTO platform_meta(key, value) VALUES('schema_version', ?)",
            (SQLITE_SCHEMA_VERSION,),
        )
        self._connection.execute(
            "INSERT OR REPLACE INTO platform_meta(key, value) VALUES('migration_schema_version', ?)",
            (MIGRATION_SCHEMA_VERSION,),
        )
        self._connection.commit()

    def get_place(self, place_id: str) -> CanonicalPlace | None:
        row = self._connection.execute("SELECT * FROM places WHERE place_id = ?", (place_id,)).fetchone()
        return None if row is None else self._place_from_row(row)

    def save_place(self, place: CanonicalPlace) -> None:
        location = place.location
        self._connection.execute(
            """
            INSERT INTO places(
                place_id, canonical_name, latitude, longitude, address_text, province,
                categories_json, phone, website, lifecycle, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(place_id) DO UPDATE SET
                canonical_name=excluded.canonical_name,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                address_text=excluded.address_text,
                province=excluded.province,
                categories_json=excluded.categories_json,
                phone=excluded.phone,
                website=excluded.website,
                lifecycle=excluded.lifecycle,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                place.identity.place_id,
                place.canonical_name,
                location.latitude if location else None,
                location.longitude if location else None,
                place.address_text,
                place.province,
                _dump(tuple(place.categories)),
                place.phone,
                place.website,
                place.lifecycle.value,
                _iso(place.created_at),
                _iso(place.updated_at),
            ),
        )
        self._connection.commit()

    def add_evidence(self, evidence: PlaceEvidence) -> None:
        try:
            self._connection.execute(
                """
                INSERT INTO place_evidence(
                    evidence_id, place_id, source_type, source_name, source_record_id,
                    source_url, source_observed_at, kind, field_name, value_json,
                    status, observed_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    evidence.place_id,
                    evidence.source.source_type.value,
                    evidence.source.source_name,
                    evidence.source.source_record_id,
                    evidence.source.source_url,
                    _iso(evidence.source.observed_at),
                    evidence.kind.value,
                    evidence.field_name,
                    _dump(evidence.value),
                    evidence.status.value,
                    _iso(evidence.observed_at),
                    _dump(dict(evidence.metadata)),
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            self._connection.rollback()
            message = str(exc).lower()
            if "foreign key" in message:
                raise KeyError("evidence cannot be attached to an unknown place") from exc
            if "place_evidence.evidence_id" in message or "unique" in message:
                raise ValueError("duplicate evidence_id") from exc
            raise

    def list_evidence(self, place_id: str) -> tuple[PlaceEvidence, ...]:
        rows = self._connection.execute(
            "SELECT * FROM place_evidence WHERE place_id = ? ORDER BY rowid", (place_id,)
        ).fetchall()
        return tuple(self._evidence_from_row(row) for row in rows)

    def commit_adoption(self, place: CanonicalPlace, revision: PlaceRevision) -> None:
        place_id = place.identity.place_id
        if revision.place_id != place_id:
            raise ValueError("revision belongs to a different place")
        if self.get_place(place_id) is None:
            raise KeyError("adoption cannot update an unknown place")

        location = place.location
        try:
            with self._connection:
                self._connection.execute(
                    """
                    UPDATE places SET canonical_name=?, latitude=?, longitude=?, address_text=?,
                        province=?, categories_json=?, phone=?, website=?, lifecycle=?,
                        created_at=?, updated_at=? WHERE place_id=?
                    """,
                    (
                        place.canonical_name,
                        location.latitude if location else None,
                        location.longitude if location else None,
                        place.address_text,
                        place.province,
                        _dump(tuple(place.categories)),
                        place.phone,
                        place.website,
                        place.lifecycle.value,
                        _iso(place.created_at),
                        _iso(place.updated_at),
                        place_id,
                    ),
                )
                self._connection.execute(
                    """
                    INSERT INTO place_revisions(
                        revision_id, place_id, changed_fields_json, before_values_json,
                        after_values_json, reason, evidence_ids_json, policy_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.revision_id,
                        revision.place_id,
                        _dump(tuple(revision.changed_fields)),
                        _dump(dict(revision.before_values)),
                        _dump(dict(revision.after_values)),
                        revision.reason,
                        _dump(tuple(revision.evidence_ids)),
                        revision.policy_version,
                        _iso(revision.created_at),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            message = str(exc).lower()
            if "place_revisions.revision_id" in message or "unique" in message:
                raise ValueError("duplicate revision_id") from exc
            raise

    def get_admin_adoption_receipt(self, draft_id: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM admin_adoption_receipts WHERE draft_id = ?", (draft_id,)
        ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["revision_ids"] = _load(item.pop("revision_ids_json"))
        item["evidence_ids"] = _load(item.pop("evidence_ids_json"))
        return item

    def commit_admin_adoption_batch(
        self,
        *,
        draft_id: str,
        place: CanonicalPlace,
        revisions: Iterable[PlaceRevision],
        evidence: Iterable[PlaceEvidence],
        policy_version: str,
        committed_at: datetime,
    ) -> dict[str, Any]:
        """Atomically persist approved admin evidence + canonical revisions.

        The draft receipt is part of the same SQLite transaction and makes the
        operation idempotent. Publication is deliberately outside this method.
        """
        if committed_at.tzinfo is None:
            raise ValueError("committed_at must be timezone-aware")
        existing = self.get_admin_adoption_receipt(draft_id)
        if existing is not None:
            return existing
        place_id = place.identity.place_id
        if self.get_place(place_id) is None:
            raise KeyError("adoption cannot update an unknown place")
        revision_items = tuple(revisions)
        evidence_items = tuple(evidence)
        if not revision_items:
            raise ValueError("admin adoption requires at least one revision")
        if any(item.place_id != place_id for item in revision_items):
            raise ValueError("revision belongs to a different place")
        if any(item.place_id != place_id for item in evidence_items):
            raise ValueError("evidence belongs to a different place")

        location = place.location
        try:
            with self._connection:
                for item in evidence_items:
                    self._connection.execute(
                        """
                        INSERT INTO place_evidence(
                            evidence_id, place_id, source_type, source_name, source_record_id,
                            source_url, source_observed_at, kind, field_name, value_json,
                            status, observed_at, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.evidence_id, item.place_id, item.source.source_type.value,
                            item.source.source_name, item.source.source_record_id,
                            item.source.source_url, _iso(item.source.observed_at), item.kind.value,
                            item.field_name, _dump(item.value), item.status.value,
                            _iso(item.observed_at), _dump(dict(item.metadata)),
                        ),
                    )
                self._connection.execute(
                    """
                    UPDATE places SET canonical_name=?, latitude=?, longitude=?, address_text=?,
                        province=?, categories_json=?, phone=?, website=?, lifecycle=?,
                        created_at=?, updated_at=? WHERE place_id=?
                    """,
                    (
                        place.canonical_name,
                        location.latitude if location else None,
                        location.longitude if location else None,
                        place.address_text, place.province, _dump(tuple(place.categories)),
                        place.phone, place.website, place.lifecycle.value,
                        _iso(place.created_at), _iso(place.updated_at), place_id,
                    ),
                )
                for revision in revision_items:
                    self._connection.execute(
                        """
                        INSERT INTO place_revisions(
                            revision_id, place_id, changed_fields_json, before_values_json,
                            after_values_json, reason, evidence_ids_json, policy_version, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            revision.revision_id, revision.place_id,
                            _dump(tuple(revision.changed_fields)), _dump(dict(revision.before_values)),
                            _dump(dict(revision.after_values)), revision.reason,
                            _dump(tuple(revision.evidence_ids)), revision.policy_version,
                            _iso(revision.created_at),
                        ),
                    )
                self._connection.execute(
                    """
                    INSERT INTO admin_adoption_receipts(
                        draft_id, place_id, revision_ids_json, evidence_ids_json,
                        policy_version, committed_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_id, place_id,
                        _dump(tuple(item.revision_id for item in revision_items)),
                        _dump(tuple(item.evidence_id for item in evidence_items)),
                        policy_version, _iso(committed_at),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            message = str(exc).lower()
            if "evidence_id" in message or "revision_id" in message or "unique" in message:
                raise ValueError("duplicate adoption evidence/revision identifier") from exc
            raise
        return self.get_admin_adoption_receipt(draft_id) or {}

    def get_admin_candidate_resolution_audit(self, draft_id: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM admin_candidate_resolution_audit WHERE draft_id = ?", (draft_id,)
        ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["decision"] = _load(item.pop("decision_json"))
        return item

    def commit_admin_candidate_creation(
        self,
        *,
        draft_id: str,
        place: CanonicalPlace,
        revision: PlaceRevision,
        evidence: Iterable[PlaceEvidence],
        policy_version: str,
        decision: dict[str, Any],
        committed_at: datetime,
    ) -> dict[str, Any]:
        """Atomically create one canonical place from one approved admin candidate.

        This is an insert-only creation boundary. It never upserts an existing
        place and never writes to the published read model.
        """
        if committed_at.tzinfo is None:
            raise ValueError("committed_at must be timezone-aware")
        existing = self.get_admin_adoption_receipt(draft_id)
        if existing is not None:
            return existing
        place_id = place.identity.place_id
        if self.get_place(place_id) is not None:
            raise ValueError("candidate place_id already exists in canonical database")
        if revision.place_id != place_id:
            raise ValueError("creation revision belongs to a different place")
        evidence_items = tuple(evidence)
        if not evidence_items:
            raise ValueError("candidate creation requires evidence")
        if any(item.place_id != place_id for item in evidence_items):
            raise ValueError("candidate evidence belongs to a different place")
        location = place.location
        try:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO places(
                        place_id, canonical_name, latitude, longitude, address_text, province,
                        categories_json, phone, website, lifecycle, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        place_id, place.canonical_name,
                        location.latitude if location else None,
                        location.longitude if location else None,
                        place.address_text, place.province, _dump(tuple(place.categories)),
                        place.phone, place.website, place.lifecycle.value,
                        _iso(place.created_at), _iso(place.updated_at),
                    ),
                )
                for item in evidence_items:
                    self._connection.execute(
                        """
                        INSERT INTO place_evidence(
                            evidence_id, place_id, source_type, source_name, source_record_id,
                            source_url, source_observed_at, kind, field_name, value_json,
                            status, observed_at, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.evidence_id, item.place_id, item.source.source_type.value,
                            item.source.source_name, item.source.source_record_id,
                            item.source.source_url, _iso(item.source.observed_at), item.kind.value,
                            item.field_name, _dump(item.value), item.status.value,
                            _iso(item.observed_at), _dump(dict(item.metadata)),
                        ),
                    )
                self._connection.execute(
                    """
                    INSERT INTO place_revisions(
                        revision_id, place_id, changed_fields_json, before_values_json,
                        after_values_json, reason, evidence_ids_json, policy_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.revision_id, revision.place_id,
                        _dump(tuple(revision.changed_fields)), _dump(dict(revision.before_values)),
                        _dump(dict(revision.after_values)), revision.reason,
                        _dump(tuple(revision.evidence_ids)), revision.policy_version,
                        _iso(revision.created_at),
                    ),
                )
                self._connection.execute(
                    """
                    INSERT INTO admin_adoption_receipts(
                        draft_id, place_id, revision_ids_json, evidence_ids_json,
                        policy_version, committed_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_id, place_id, _dump((revision.revision_id,)),
                        _dump(tuple(item.evidence_id for item in evidence_items)),
                        policy_version, _iso(committed_at),
                    ),
                )
                self._connection.execute(
                    """
                    INSERT INTO admin_candidate_resolution_audit(
                        draft_id, place_id, operation, resolution_outcome, decision_json,
                        policy_version, committed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_id, place_id, str(decision.get("operation") or "create_place_candidate"),
                        str(decision.get("resolution_outcome") or ""), _dump(decision),
                        policy_version, _iso(committed_at),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("controlled candidate creation failed atomically") from exc
        return self.get_admin_adoption_receipt(draft_id) or {}

    def commit_admin_candidate_reconciliation(
        self,
        *,
        draft_id: str,
        place_id: str,
        evidence: Iterable[PlaceEvidence],
        policy_version: str,
        decision: dict[str, Any],
        committed_at: datetime,
    ) -> dict[str, Any]:
        """Atomically attach approved create-candidate evidence to an existing canonical.

        This path is evidence/audit-only: it never updates the canonical place row,
        never creates a revision, and never publishes. It is used only after one
        deterministic SAME_ENTITY match has been established.
        """
        if committed_at.tzinfo is None:
            raise ValueError("committed_at must be timezone-aware")
        existing = self.get_admin_adoption_receipt(draft_id)
        if existing is not None:
            return existing
        if self.get_place(place_id) is None:
            raise KeyError("reconciliation target canonical place does not exist")
        evidence_items = tuple(evidence)
        if not evidence_items:
            raise ValueError("candidate reconciliation requires evidence")
        if any(item.place_id != place_id for item in evidence_items):
            raise ValueError("reconciliation evidence belongs to a different place")
        try:
            with self._connection:
                for item in evidence_items:
                    self._connection.execute(
                        """
                        INSERT INTO place_evidence(
                            evidence_id, place_id, source_type, source_name, source_record_id,
                            source_url, source_observed_at, kind, field_name, value_json,
                            status, observed_at, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.evidence_id, item.place_id, item.source.source_type.value,
                            item.source.source_name, item.source.source_record_id,
                            item.source.source_url, _iso(item.source.observed_at), item.kind.value,
                            item.field_name, _dump(item.value), item.status.value,
                            _iso(item.observed_at), _dump(dict(item.metadata)),
                        ),
                    )
                self._connection.execute(
                    """
                    INSERT INTO admin_adoption_receipts(
                        draft_id, place_id, revision_ids_json, evidence_ids_json,
                        policy_version, committed_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_id, place_id, _dump(tuple()),
                        _dump(tuple(item.evidence_id for item in evidence_items)),
                        policy_version, _iso(committed_at),
                    ),
                )
                self._connection.execute(
                    """
                    INSERT INTO admin_candidate_resolution_audit(
                        draft_id, place_id, operation, resolution_outcome, decision_json,
                        policy_version, committed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_id, place_id, str(decision.get("operation") or "create_place_candidate"),
                        str(decision.get("resolution_outcome") or "matched"), _dump(decision),
                        policy_version, _iso(committed_at),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("controlled candidate reconciliation failed atomically") from exc
        return self.get_admin_adoption_receipt(draft_id) or {}

    def list_migration_import_keys(self) -> frozenset[str]:
        rows = self._connection.execute("SELECT import_key FROM migration_imports").fetchall()
        return frozenset(str(row["import_key"]) for row in rows)

    def migration_import_count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS n FROM migration_imports").fetchone()
        return int(row["n"])

    def canonical_place_count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS n FROM places").fetchone()
        return int(row["n"])

    def evidence_count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS n FROM place_evidence").fetchone()
        return int(row["n"])

    def commit_migration_batch(self, places, evidence, ledger) -> None:
        """Atomically persist one controlled migration batch.

        No helper that auto-commits is called here: either all places, evidence,
        and ledger entries land together, or SQLite rolls the whole batch back.
        """
        place_rows = []
        for place in places:
            location = place.location
            place_rows.append((
                place.identity.place_id,
                place.canonical_name,
                location.latitude if location else None,
                location.longitude if location else None,
                place.address_text,
                place.province,
                _dump(tuple(place.categories)),
                place.phone,
                place.website,
                place.lifecycle.value,
                _iso(place.created_at),
                _iso(place.updated_at),
            ))
        evidence_rows = [(
            item.evidence_id,
            item.place_id,
            item.source.source_type.value,
            item.source.source_name,
            item.source.source_record_id,
            item.source.source_url,
            _iso(item.source.observed_at),
            item.kind.value,
            item.field_name,
            _dump(item.value),
            item.status.value,
            _iso(item.observed_at),
            _dump(dict(item.metadata)),
        ) for item in evidence]
        ledger_rows = [(
            item.import_key,
            item.source_file,
            item.source_record_id,
            item.candidate_key,
            item.place_id,
        ) for item in ledger]

        try:
            with self._connection:
                self._connection.executemany(
                    """
                    INSERT INTO places(
                        place_id, canonical_name, latitude, longitude, address_text, province,
                        categories_json, phone, website, lifecycle, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(place_id) DO UPDATE SET
                        canonical_name=excluded.canonical_name,
                        latitude=excluded.latitude,
                        longitude=excluded.longitude,
                        address_text=COALESCE(places.address_text, excluded.address_text),
                        province=COALESCE(places.province, excluded.province),
                        categories_json=excluded.categories_json,
                        phone=COALESCE(places.phone, excluded.phone),
                        website=COALESCE(places.website, excluded.website),
                        lifecycle=places.lifecycle,
                        created_at=places.created_at,
                        updated_at=excluded.updated_at
                    """,
                    place_rows,
                )
                self._connection.executemany(
                    """
                    INSERT INTO place_evidence(
                        evidence_id, place_id, source_type, source_name, source_record_id,
                        source_url, source_observed_at, kind, field_name, value_json,
                        status, observed_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    evidence_rows,
                )
                self._connection.executemany(
                    """
                    INSERT INTO migration_imports(
                        import_key, source_file, source_record_id, candidate_key, place_id
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    ledger_rows,
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("controlled migration batch failed atomically") from exc

    def list_revisions(self, place_id: str) -> tuple[PlaceRevision, ...]:
        rows = self._connection.execute(
            "SELECT * FROM place_revisions WHERE place_id = ? ORDER BY rowid", (place_id,)
        ).fetchall()
        return tuple(self._revision_from_row(row) for row in rows)

    def search_nearby(self, query: NearbyPlaceQuery) -> tuple[NearbyPlaceResult, ...]:
        requested = {item.casefold().strip() for item in query.categories}
        rows = self._connection.execute("SELECT * FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL").fetchall()
        matches: list[NearbyPlaceResult] = []
        for row in rows:
            place = self._place_from_row(row)
            if not query.include_non_active and place.lifecycle in {PlaceLifecycle.INACTIVE, PlaceLifecycle.CLOSED}:
                continue
            if requested and not requested.intersection(item.casefold() for item in place.categories):
                continue
            distance = _canonical_distance_km(
                query.origin.latitude, query.origin.longitude,
                place.location.latitude, place.location.longitude,
            )
            if distance <= query.radius_km:
                matches.append(NearbyPlaceResult(place.identity.place_id, distance))
        matches.sort(key=lambda item: (item.distance_km, item.place_id))
        return tuple(matches[:query.limit])

    @staticmethod
    def _place_from_row(row: sqlite3.Row) -> CanonicalPlace:
        location = None
        if row["latitude"] is not None and row["longitude"] is not None:
            location = GeoPoint(float(row["latitude"]), float(row["longitude"]))
        return CanonicalPlace(
            identity=PlaceIdentity(row["place_id"]),
            canonical_name=row["canonical_name"],
            location=location,
            address_text=row["address_text"],
            province=row["province"],
            categories=tuple(_load(row["categories_json"])),
            phone=row["phone"],
            website=row["website"],
            lifecycle=PlaceLifecycle(row["lifecycle"]),
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
        )

    @staticmethod
    def _evidence_from_row(row: sqlite3.Row) -> PlaceEvidence:
        source = SourceRef(
            source_type=SourceType(row["source_type"]),
            source_name=row["source_name"],
            source_record_id=row["source_record_id"],
            source_url=row["source_url"],
            observed_at=_dt(row["source_observed_at"]),
        )
        return PlaceEvidence(
            place_id=row["place_id"],
            source=source,
            kind=EvidenceKind(row["kind"]),
            field_name=row["field_name"],
            value=_load(row["value_json"]),
            status=EvidenceStatus(row["status"]),
            evidence_id=row["evidence_id"],
            observed_at=_dt(row["observed_at"]),
            metadata=_load(row["metadata_json"]),
        )

    @staticmethod
    def _revision_from_row(row: sqlite3.Row) -> PlaceRevision:
        return PlaceRevision(
            revision_id=row["revision_id"],
            place_id=row["place_id"],
            changed_fields=tuple(_load(row["changed_fields_json"])),
            before_values=_load(row["before_values_json"]),
            after_values=_load(row["after_values_json"]),
            reason=row["reason"],
            evidence_ids=tuple(_load(row["evidence_ids_json"])),
            policy_version=row["policy_version"],
            created_at=_dt(row["created_at"]),
        )


class SQLitePublishedPlaceRepository(_SQLiteBase):
    """SQLite implementation of the consumer-safe published read model."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        super().__init__(database)
        self._connection.executescript(_PUBLISHED_SCHEMA)
        self._connection.commit()

    def upsert_published(self, place: PublishedPlaceView) -> None:
        self._connection.execute(
            """
            INSERT INTO published_places(
                place_id, name, latitude, longitude, province, categories_json,
                lifecycle, address_text, phone, website, publication_policy_version, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(place_id) DO UPDATE SET
                name=excluded.name, latitude=excluded.latitude, longitude=excluded.longitude,
                province=excluded.province, categories_json=excluded.categories_json,
                lifecycle=excluded.lifecycle, address_text=excluded.address_text,
                phone=excluded.phone, website=excluded.website,
                publication_policy_version=excluded.publication_policy_version,
                published_at=excluded.published_at
            """,
            (
                place.place_id, place.name, place.location.latitude, place.location.longitude,
                place.province, _dump(tuple(place.categories)), place.lifecycle.value,
                place.address_text, place.phone, place.website,
                place.publication_policy_version, _iso(place.published_at),
            ),
        )
        self._connection.commit()

    def remove_published(self, place_id: str) -> None:
        self._connection.execute("DELETE FROM published_places WHERE place_id = ?", (place_id,))
        self._connection.commit()

    def get_published(self, place_id: str) -> PublishedPlaceView | None:
        row = self._connection.execute("SELECT * FROM published_places WHERE place_id = ?", (place_id,)).fetchone()
        return None if row is None else self._view_from_row(row)

    def search_nearby(self, query: PublishedNearbyQuery) -> tuple[PublishedNearbyResult, ...]:
        rows = self._candidate_rows(query.province)
        matches: list[PublishedNearbyResult] = []
        for row in rows:
            place = self._view_from_row(row)
            if not _matches_categories(place, query.categories):
                continue
            distance = _distance_km(query.origin, place.location)
            if distance <= query.radius_km:
                matches.append(PublishedNearbyResult(place, distance))
        matches.sort(key=lambda item: (item.distance_km, item.place.place_id))
        return tuple(matches[:query.limit])

    def search_text(self, query: PublishedTextQuery) -> tuple[PublishedPlaceView, ...]:
        needle = _normal(query.text)
        matches: list[PublishedPlaceView] = []
        for row in self._candidate_rows(query.province):
            place = self._view_from_row(row)
            if not _matches_categories(place, query.categories):
                continue
            haystack = _normal(" ".join(
                value for value in (
                    place.name, place.address_text or "", place.province, " ".join(place.categories)
                ) if value
            ))
            if needle and needle not in haystack:
                continue
            matches.append(place)
        matches.sort(key=lambda place: (_normal(place.name), place.place_id))
        return tuple(matches[:query.limit])

    def _candidate_rows(self, province: str | None) -> Iterable[sqlite3.Row]:
        if province is None:
            return self._connection.execute("SELECT * FROM published_places").fetchall()
        # SQL narrowing is only an optimization. Normalized matching below keeps
        # the read-model semantics aligned with the in-memory reference model.
        return [
            row for row in self._connection.execute("SELECT * FROM published_places").fetchall()
            if _normal(row["province"]) == _normal(province)
        ]

    @staticmethod
    def _view_from_row(row: sqlite3.Row) -> PublishedPlaceView:
        return PublishedPlaceView(
            place_id=row["place_id"],
            name=row["name"],
            location=GeoPoint(float(row["latitude"]), float(row["longitude"])),
            province=row["province"],
            categories=tuple(_load(row["categories_json"])),
            lifecycle=PlaceLifecycle(row["lifecycle"]),
            address_text=row["address_text"],
            phone=row["phone"],
            website=row["website"],
            publication_policy_version=row["publication_policy_version"],
            published_at=_dt(row["published_at"]),
        )
