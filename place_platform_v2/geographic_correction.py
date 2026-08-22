from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .contracts import EvidenceStatus, GeoPoint, SourceRef
from .models import EvidenceKind, PlaceEvidence
from .publication_export import _load_places_and_evidence
from .publication_readiness import evidence_lineage_key
from .sqlite_store import SQLitePlaceRepository, _dump, _iso
from .verification_source_acquisition import _name_key, _province_key

POLICY_VERSION = "2W.5-geographic-correction-v1"
MAX_BIND_DISTANCE_METERS = 500.0
MIN_INDEPENDENT_LINEAGES = 2


@dataclass(frozen=True)
class GeographicCorrectionObservation:
    source: SourceRef
    place_name: str
    province: str
    location: GeoPoint


@dataclass(frozen=True)
class GeographicCorrectionProposal:
    place_id: str
    proposed_province: str
    observations: tuple[GeographicCorrectionObservation, ...]
    proposal_id: str


@dataclass(frozen=True)
class GeographicCorrectionResult:
    mode: str
    result: str
    reason: str
    place_id: str
    proposal_id: str
    province_before: str | None
    province_after: str | None
    supporting_lineages: tuple[str, ...]
    observation_count: int
    evidence_ids: tuple[str, ...]
    revision_id: str | None
    canonical_fields_changed: tuple[str, ...]
    publication_performed: bool = False
    user_web_switched: bool = False
    policy_version: str = POLICY_VERSION


def _distance_m(a: GeoPoint, b: GeoPoint) -> float:
    r = 6371008.8
    p1 = math.radians(a.latitude)
    p2 = math.radians(b.latitude)
    dp = math.radians(b.latitude - a.latitude)
    dl = math.radians(b.longitude - a.longitude)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * (2 * math.atan2(math.sqrt(h), math.sqrt(1 - h)))


def _lineage(place_id: str, source: SourceRef) -> str:
    probe = PlaceEvidence(
        place_id=place_id,
        source=source,
        kind=EvidenceKind.OTHER,
        field_name="geographic_correction_probe",
        value=True,
        status=EvidenceStatus.CANDIDATE,
        observed_at=source.observed_at,
    )
    return evidence_lineage_key(probe)


def make_proposal(*, place_id: str, proposed_province: str,
                  observations: Iterable[GeographicCorrectionObservation]) -> GeographicCorrectionProposal:
    obs = tuple(observations)
    if not proposed_province.strip():
        raise ValueError("proposed_province is required")
    if not obs:
        raise ValueError("at least one correction observation is required")
    raw = "|".join(
        [place_id, _province_key(proposed_province)]
        + sorted(
            f"{o.source.source_type.value}:{o.source.source_name}:{o.source.source_record_id or ''}:{o.source.source_url or ''}"
            for o in obs
        )
    )
    return GeographicCorrectionProposal(
        place_id=place_id,
        proposed_province=proposed_province.strip(),
        observations=obs,
        proposal_id=hashlib.sha256(raw.encode()).hexdigest()[:32],
    )


def _load_place(database_path: str | Path, place_id: str):
    db = Path(database_path).resolve()
    con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
    try:
        row = con.execute("SELECT province FROM places WHERE place_id=?", (place_id,)).fetchone()
    finally:
        con.close()
    if row is None:
        raise KeyError(f"unknown place_id: {place_id}")
    places, by_place = _load_places_and_evidence(database_path, row[0])
    place = next((p for p in places if p.identity.place_id == place_id), None)
    if place is None:
        raise KeyError(f"unknown place_id: {place_id}")
    return place, by_place.get(place_id, ())


def evaluate_proposal(database_path: str | Path,
                      proposal: GeographicCorrectionProposal) -> GeographicCorrectionResult:
    place, _ = _load_place(database_path, proposal.place_id)
    base = dict(
        mode="DRY_RUN",
        place_id=proposal.place_id,
        proposal_id=proposal.proposal_id,
        province_before=place.province,
        province_after=place.province,
        observation_count=len(proposal.observations),
        evidence_ids=(),
        revision_id=None,
        canonical_fields_changed=(),
    )
    if place.location is None:
        return GeographicCorrectionResult(
            result="blocked_no_canonical_location",
            reason="canonical place has no location anchor",
            supporting_lineages=(),
            **base,
        )
    if _province_key(place.province) == _province_key(proposal.proposed_province):
        return GeographicCorrectionResult(
            result="no_change",
            reason="proposed province already equals canonical province",
            supporting_lineages=(),
            **base,
        )

    lineages: set[str] = set()
    for obs in proposal.observations:
        if _province_key(obs.province) != _province_key(proposal.proposed_province):
            return GeographicCorrectionResult(
                result="blocked_observation_disagreement",
                reason="supporting observation does not agree with proposed province",
                supporting_lineages=tuple(sorted(lineages)),
                **base,
            )
        if _name_key(obs.place_name) != _name_key(place.canonical_name):
            return GeographicCorrectionResult(
                result="blocked_identity_conflict",
                reason="supporting observation name does not match canonical identity",
                supporting_lineages=tuple(sorted(lineages)),
                **base,
            )
        if _distance_m(place.location, obs.location) > MAX_BIND_DISTANCE_METERS:
            return GeographicCorrectionResult(
                result="blocked_geo_unresolved",
                reason="supporting observation is too far from canonical location",
                supporting_lineages=tuple(sorted(lineages)),
                **base,
            )
        lineages.add(_lineage(proposal.place_id, obs.source))

    if len(lineages) < MIN_INDEPENDENT_LINEAGES:
        return GeographicCorrectionResult(
            result="blocked_insufficient_independent_lineage",
            reason=(
                f"geographic correction requires {MIN_INDEPENDENT_LINEAGES} independent lineages; "
                f"got {len(lineages)}"
            ),
            supporting_lineages=tuple(sorted(lineages)),
            **base,
        )

    return GeographicCorrectionResult(
        result="ready_to_commit",
        reason="independent geographic observations agree on canonical identity and proposed province",
        supporting_lineages=tuple(sorted(lineages)),
        province_after=proposal.proposed_province,
        canonical_fields_changed=("province",),
        **{k: v for k, v in base.items() if k not in {"province_after", "canonical_fields_changed"}},
    )


def _existing_audit(database_path: str | Path, proposal_id: str):
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        try:
            return con.execute(
                "SELECT * FROM canonical_geographic_corrections WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    finally:
        con.close()


def commit_proposal(database_path: str | Path,
                    proposal: GeographicCorrectionProposal) -> GeographicCorrectionResult:
    existing = _existing_audit(database_path, proposal.proposal_id)
    if existing is not None:
        return GeographicCorrectionResult(
            mode="COMMIT",
            result="already_committed",
            reason="geographic correction proposal already committed",
            place_id=proposal.place_id,
            proposal_id=proposal.proposal_id,
            province_before=existing["province_before"],
            province_after=existing["province_after"],
            supporting_lineages=tuple(json.loads(existing["supporting_lineages_json"])),
            observation_count=len(proposal.observations),
            evidence_ids=tuple(json.loads(existing["evidence_ids_json"])),
            revision_id=existing["revision_id"],
            canonical_fields_changed=(),
        )

    preview = evaluate_proposal(database_path, proposal)
    if preview.result != "ready_to_commit":
        return preview

    repo = SQLitePlaceRepository(database_path)
    con = repo._connection
    try:
        place = repo.get_place(proposal.place_id)
        if place is None:
            raise KeyError(f"unknown place_id: {proposal.place_id}")
        now = datetime.now(timezone.utc)
        evidence_items: list[PlaceEvidence] = []
        for obs in proposal.observations:
            evidence_items.append(PlaceEvidence(
                place_id=proposal.place_id,
                source=obs.source,
                kind=EvidenceKind.OTHER,
                field_name="province",
                value=proposal.proposed_province,
                status=EvidenceStatus.CANDIDATE,
                observed_at=obs.source.observed_at,
                metadata={
                    "provenance_origin": "geographic_correction_review",
                    "geographic_correction_proposal_id": proposal.proposal_id,
                    "policy_version": POLICY_VERSION,
                },
            ))
            evidence_items.append(PlaceEvidence(
                place_id=proposal.place_id,
                source=obs.source,
                kind=EvidenceKind.LOCATION,
                field_name="location",
                value=obs.location,
                status=EvidenceStatus.CANDIDATE,
                observed_at=obs.source.observed_at,
                metadata={
                    "provenance_origin": "geographic_correction_review",
                    "geographic_correction_proposal_id": proposal.proposal_id,
                    "policy_version": POLICY_VERSION,
                },
            ))

        revision_id = hashlib.sha256((proposal.proposal_id + "|revision").encode()).hexdigest()[:32]
        with con:
            for item in evidence_items:
                con.execute(
                    """
                    INSERT INTO place_evidence(
                        evidence_id, place_id, source_type, source_name, source_record_id,
                        source_url, source_observed_at, kind, field_name, value_json,
                        status, observed_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.evidence_id, item.place_id, item.source.source_type.value,
                        item.source.source_name, item.source.source_record_id, item.source.source_url,
                        _iso(item.source.observed_at), item.kind.value, item.field_name,
                        _dump(item.value), item.status.value, _iso(item.observed_at),
                        _dump(dict(item.metadata)),
                    ),
                )
            con.execute(
                "UPDATE places SET province=?, updated_at=? WHERE place_id=?",
                (proposal.proposed_province, _iso(now), proposal.place_id),
            )
            con.execute(
                """
                INSERT INTO place_revisions(
                    revision_id, place_id, changed_fields_json, before_values_json,
                    after_values_json, reason, evidence_ids_json, policy_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id, proposal.place_id, _dump(("province",)),
                    _dump({"province": place.province}),
                    _dump({"province": proposal.proposed_province}),
                    "controlled geographic scope correction after independent evidence review",
                    _dump(tuple(item.evidence_id for item in evidence_items)),
                    POLICY_VERSION, _iso(now),
                ),
            )
            con.execute(
                """
                INSERT INTO canonical_geographic_corrections(
                    proposal_id, place_id, province_before, province_after,
                    supporting_lineages_json, evidence_ids_json, revision_id,
                    policy_version, committed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id, proposal.place_id, place.province,
                    proposal.proposed_province, json.dumps(list(preview.supporting_lineages), ensure_ascii=False),
                    json.dumps([item.evidence_id for item in evidence_items], ensure_ascii=False),
                    revision_id, POLICY_VERSION, _iso(now),
                ),
            )

        return GeographicCorrectionResult(
            mode="COMMIT",
            result="corrected",
            reason="canonical province corrected with evidence, revision, and immutable correction audit",
            place_id=proposal.place_id,
            proposal_id=proposal.proposal_id,
            province_before=place.province,
            province_after=proposal.proposed_province,
            supporting_lineages=preview.supporting_lineages,
            observation_count=len(proposal.observations),
            evidence_ids=tuple(item.evidence_id for item in evidence_items),
            revision_id=revision_id,
            canonical_fields_changed=("province",),
        )
    finally:
        repo.close()
