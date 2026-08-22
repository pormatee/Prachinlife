from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .contracts import EvidenceStatus, GeoPoint, SourceRef
from .models import EvidenceKind, PlaceEvidence, PlaceLifecycle
from .publication_export import _load_places_and_evidence
from .publication_readiness import (
    evidence_lineage_key,
    evaluate_pilot_readiness,
    lineage_source_count,
)
from .sqlite_store import SQLitePlaceRepository, _dump, _iso

POLICY_VERSION = "2W.3-independent-verification-v1"
REQUIRED_FIELDS = (
    "canonical_name",
    "categories",
    "location",
    "province",
    "lifecycle",
)


@dataclass(frozen=True)
class VerificationBundle:
    place_id: str
    source: SourceRef
    claims: Mapping[str, Any]
    bundle_id: str
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True)
class VerificationBundleResult:
    mode: str
    result: str
    reason: str
    place_id: str
    bundle_id: str
    source_lineage: str
    evidence_ids: tuple[str, ...]
    lifecycle_before: str
    lifecycle_after: str
    publication_ready_after: bool | None
    canonical_fields_changed: tuple[str, ...]
    publication_performed: bool = False
    user_web_switched: bool = False
    policy_version: str = POLICY_VERSION


def deterministic_bundle_id(place_id: str, source: SourceRef) -> str:
    raw = "|".join(
        (
            place_id,
            source.source_type.value,
            source.source_name.strip().casefold(),
            source.source_record_id or "",
            source.source_url or "",
        )
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def make_bundle(*, place_id: str, source: SourceRef, claims: Mapping[str, Any]) -> VerificationBundle:
    missing = [field for field in REQUIRED_FIELDS if field not in claims]
    if missing:
        raise ValueError(
            "verification bundle missing required claims: " + ", ".join(missing)
        )
    if claims["lifecycle"] not in (PlaceLifecycle.ACTIVE, "active"):
        raise ValueError("verification bundle must explicitly claim lifecycle=active")
    return VerificationBundle(
        place_id=place_id,
        source=source,
        claims=dict(claims),
        bundle_id=deterministic_bundle_id(place_id, source),
    )


def _kind(field: str) -> EvidenceKind:
    return {
        "canonical_name": EvidenceKind.NAME,
        "location": EvidenceKind.LOCATION,
        "categories": EvidenceKind.CATEGORY,
        "lifecycle": EvidenceKind.OPENING_STATUS,
    }.get(field, EvidenceKind.OTHER)


def _normalize_value(field: str, value: Any) -> Any:
    if field == "lifecycle" and value == "active":
        return PlaceLifecycle.ACTIVE
    if field == "categories" and isinstance(value, list):
        return tuple(value)
    if field == "location" and isinstance(value, dict):
        return GeoPoint(float(value["latitude"]), float(value["longitude"]))
    return value


def _probe_lineage(place_id: str, source: SourceRef) -> str:
    probe = PlaceEvidence(
        place_id=place_id,
        source=source,
        kind=EvidenceKind.OTHER,
        field_name="probe",
        value=True,
        observed_at=source.observed_at,
    )
    return evidence_lineage_key(probe)


def _existing_lineages(evidence) -> set[str]:
    return {
        evidence_lineage_key(item)
        for item in evidence
        if item.status not in {EvidenceStatus.REJECTED, EvidenceStatus.STALE}
    }


def evaluate_bundle(database_path: str | Path, bundle: VerificationBundle) -> VerificationBundleResult:
    places, by_place = _load_places_and_evidence(database_path, "ปราจีนบุรี")
    place = next(
        (item for item in places if item.identity.place_id == bundle.place_id),
        None,
    )
    if place is None:
        raise KeyError("unknown place_id")

    evidence = by_place.get(bundle.place_id, ())
    lineage = _probe_lineage(bundle.place_id, bundle.source)

    if lineage in _existing_lineages(evidence):
        return VerificationBundleResult(
            mode="DRY_RUN",
            result="blocked_same_lineage",
            reason="verification source is not independent from existing evidence",
            place_id=bundle.place_id,
            bundle_id=bundle.bundle_id,
            source_lineage=lineage,
            evidence_ids=(),
            lifecycle_before=place.lifecycle.value,
            lifecycle_after=place.lifecycle.value,
            publication_ready_after=None,
            canonical_fields_changed=(),
        )

    conflicts = []
    for field in ("canonical_name", "categories", "location", "province"):
        if _normalize_value(field, bundle.claims[field]) != getattr(place, field):
            conflicts.append(field)
    if conflicts:
        return VerificationBundleResult(
            mode="DRY_RUN",
            result="blocked_conflict",
            reason="verification claims conflict with canonical fields: " + ", ".join(conflicts),
            place_id=bundle.place_id,
            bundle_id=bundle.bundle_id,
            source_lineage=lineage,
            evidence_ids=(),
            lifecycle_before=place.lifecycle.value,
            lifecycle_after=place.lifecycle.value,
            publication_ready_after=None,
            canonical_fields_changed=(),
        )

    current_lifecycle_sources = lineage_source_count(
        evidence,
        "lifecycle",
        PlaceLifecycle.ACTIVE,
    )
    will_activate = current_lifecycle_sources + 1 >= 2

    return VerificationBundleResult(
        mode="DRY_RUN",
        result="ready_to_commit",
        reason=(
            "independent verification bundle agrees with canonical identity; "
            "lifecycle activates only when active-lifecycle lineage quorum is reached"
        ),
        place_id=bundle.place_id,
        bundle_id=bundle.bundle_id,
        source_lineage=lineage,
        evidence_ids=(),
        lifecycle_before=place.lifecycle.value,
        lifecycle_after=(
            PlaceLifecycle.ACTIVE.value if will_activate else place.lifecycle.value
        ),
        publication_ready_after=None,
        canonical_fields_changed=(
            ("lifecycle",)
            if will_activate and place.lifecycle is not PlaceLifecycle.ACTIVE
            else ()
        ),
    )


def _get_existing_bundle(database_path: str | Path, bundle_id: str):
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        try:
            return con.execute(
                "SELECT * FROM publication_verification_bundles WHERE bundle_id=?",
                (bundle_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    finally:
        con.close()


def commit_bundle(database_path: str | Path, bundle: VerificationBundle) -> VerificationBundleResult:
    existing = _get_existing_bundle(database_path, bundle.bundle_id)
    if existing is not None:
        ready = evaluate_pilot_readiness(
            database_path,
            bundle.place_id,
        ).publication_ready
        return VerificationBundleResult(
            mode="COMMIT",
            result="already_committed",
            reason="verification bundle already committed",
            place_id=bundle.place_id,
            bundle_id=bundle.bundle_id,
            source_lineage="stored",
            evidence_ids=tuple(json.loads(existing["evidence_ids_json"])),
            lifecycle_before=existing["lifecycle_before"],
            lifecycle_after=existing["lifecycle_after"],
            publication_ready_after=ready,
            canonical_fields_changed=(),
        )

    preview = evaluate_bundle(database_path, bundle)
    if preview.result != "ready_to_commit":
        return preview

    repo = SQLitePlaceRepository(database_path)
    con = repo._connection
    try:
        place = repo.get_place(bundle.place_id)
        if place is None:
            raise KeyError("unknown place_id")
        existing_evidence = repo.list_evidence(bundle.place_id)
        now = datetime.now(timezone.utc)

        evidence_items = tuple(
            PlaceEvidence(
                place_id=bundle.place_id,
                source=bundle.source,
                kind=_kind(field),
                field_name=field,
                value=_normalize_value(field, bundle.claims[field]),
                status=EvidenceStatus.CANDIDATE,
                observed_at=bundle.source.observed_at,
                metadata={
                    "publication_verification_bundle_id": bundle.bundle_id,
                    "provenance_origin": "independent_verification",
                    "policy_version": POLICY_VERSION,
                },
            )
            for field in REQUIRED_FIELDS
        )

        lifecycle_sources_after = lineage_source_count(
            tuple(existing_evidence) + evidence_items,
            "lifecycle",
            PlaceLifecycle.ACTIVE,
        )
        activate = lifecycle_sources_after >= 2
        before = place.lifecycle.value
        after = PlaceLifecycle.ACTIVE.value if activate else before

        with con:
            for item in evidence_items:
                con.execute(
                    """
                    INSERT INTO place_evidence(
                        evidence_id, place_id, source_type, source_name,
                        source_record_id, source_url, source_observed_at, kind,
                        field_name, value_json, status, observed_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
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
                    ),
                )

            if activate and place.lifecycle is not PlaceLifecycle.ACTIVE:
                con.execute(
                    "UPDATE places SET lifecycle=?, updated_at=? WHERE place_id=?",
                    (PlaceLifecycle.ACTIVE.value, _iso(now), bundle.place_id),
                )

            con.execute(
                """
                INSERT INTO publication_verification_bundles(
                    bundle_id, place_id, source_type, source_name,
                    source_record_id, source_url, evidence_ids_json,
                    lifecycle_before, lifecycle_after, policy_version, committed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bundle.bundle_id,
                    bundle.place_id,
                    bundle.source.source_type.value,
                    bundle.source.source_name,
                    bundle.source.source_record_id,
                    bundle.source.source_url,
                    json.dumps([item.evidence_id for item in evidence_items]),
                    before,
                    after,
                    POLICY_VERSION,
                    _iso(now),
                ),
            )

        ready = evaluate_pilot_readiness(
            database_path,
            bundle.place_id,
        ).publication_ready
        return VerificationBundleResult(
            mode="COMMIT",
            result="committed",
            reason=(
                "independent verification evidence committed atomically; "
                "canonical lifecycle activates only after lifecycle lineage quorum"
            ),
            place_id=bundle.place_id,
            bundle_id=bundle.bundle_id,
            source_lineage=preview.source_lineage,
            evidence_ids=tuple(item.evidence_id for item in evidence_items),
            lifecycle_before=before,
            lifecycle_after=after,
            publication_ready_after=ready,
            canonical_fields_changed=("lifecycle",) if before != after else (),
        )
    except Exception:
        con.rollback()
        raise
    finally:
        repo.close()
