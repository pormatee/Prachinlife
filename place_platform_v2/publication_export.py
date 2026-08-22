from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .publication import PublicationDecision, PublicationPolicy, build_published_view, evaluate_publication
from .sqlite_store import SQLitePlaceRepository
from .verification import VerificationPolicy, verify_field

PHASE2W1_POLICY_VERSION = "2W.1-publication-export-v1"
DEFAULT_STAGING_DIR = Path("data/v2/staging")
PRODUCTION_EXPORT = Path("data/v2/exports/prachinlife_places_v2.json")


@dataclass(frozen=True)
class PublicationExportReport:
    province: str
    canonical_count: int
    eligible_count: int
    blocked_count: int
    reason_counts: tuple[tuple[str, int], ...]
    policy_version: str
    export_performed: bool
    publication_store_written: bool
    user_web_switched: bool

    @property
    def may_stage_export(self) -> bool:
        return self.eligible_count > 0


def _open_readonly(database_path: str | Path):
    path = Path(database_path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    con = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _load_places_and_evidence(database_path: str | Path, province: str):
    con = _open_readonly(database_path)
    try:
        place_rows = con.execute(
            "SELECT * FROM places WHERE province=? ORDER BY place_id",
            (province,),
        ).fetchall()
        evidence_rows = con.execute(
            "SELECT pe.* FROM place_evidence pe JOIN places p ON p.place_id=pe.place_id "
            "WHERE p.province=? ORDER BY pe.place_id,pe.evidence_id",
            (province,),
        ).fetchall()
    finally:
        con.close()

    places = tuple(SQLitePlaceRepository._place_from_row(row) for row in place_rows)
    evidence_by_place: dict[str, list] = {}
    for row in evidence_rows:
        item = SQLitePlaceRepository._evidence_from_row(row)
        evidence_by_place.setdefault(item.place_id, []).append(item)
    return places, {key: tuple(value) for key, value in evidence_by_place.items()}


def evaluate_publication_database(
    database_path: str | Path,
    *,
    province: str = "ปราจีนบุรี",
    publication_policy: PublicationPolicy = PublicationPolicy(),
    verification_policy: VerificationPolicy = VerificationPolicy(),
):
    places, evidence_by_place = _load_places_and_evidence(database_path, province)
    decisions: list[tuple[object, PublicationDecision]] = []
    reason_counts: Counter[str] = Counter()

    for place in places:
        evidence = evidence_by_place.get(place.identity.place_id, ())
        verifications = tuple(
            verify_field(
                place_id=place.identity.place_id,
                field_name=field_name,
                evidence=evidence,
                policy=verification_policy,
            )
            for field_name in sorted(publication_policy.required_verified_fields)
        )
        decision = evaluate_publication(
            place=place,
            verifications=verifications,
            policy=publication_policy,
        )
        decisions.append((place, decision))
        if not decision.may_publish:
            reason_counts.update(decision.reasons)

    eligible = sum(1 for _, decision in decisions if decision.may_publish)
    report = PublicationExportReport(
        province=province,
        canonical_count=len(places),
        eligible_count=eligible,
        blocked_count=len(places) - eligible,
        reason_counts=tuple(sorted(reason_counts.items())),
        policy_version=PHASE2W1_POLICY_VERSION,
        export_performed=False,
        publication_store_written=False,
        user_web_switched=False,
    )
    return report, tuple(decisions)


def _view_to_compat(view):
    return {
        "id": view.place_id,
        "name": view.name,
        "latitude": view.location.latitude,
        "longitude": view.location.longitude,
        "address": view.address_text,
        "province": view.province,
        "categories": list(view.categories),
        "phone": view.phone,
        "website": view.website,
        "lifecycle": view.lifecycle.value,
        "source": "place_platform_v2_published",
        "publication_policy_version": view.publication_policy_version,
        "published_at": view.published_at.isoformat(),
    }


def build_staged_payload(
    decisions,
    *,
    province: str,
    published_at: datetime | None = None,
):
    when = published_at or datetime.now(timezone.utc)
    views = [
        build_published_view(place=place, decision=decision, published_at=when)
        for place, decision in decisions
        if decision.may_publish
    ]
    places = [_view_to_compat(view) for view in sorted(views, key=lambda x: (x.name.casefold(), x.place_id))]
    return {
        "schema_version": "prachinlife-v2-published-json-1",
        "publication_gate": PHASE2W1_POLICY_VERSION,
        "province": province,
        "count": len(places),
        "places": places,
    }


def write_staged_export(
    payload: dict,
    *,
    output_path: str | Path,
    staging_root: str | Path = DEFAULT_STAGING_DIR,
):
    out = Path(output_path).resolve()
    root = Path(staging_root).resolve()
    try:
        out.relative_to(root)
    except ValueError as exc:
        raise ValueError("Phase 2W.1 may write only inside the staging directory") from exc
    if out == PRODUCTION_EXPORT.resolve():
        raise ValueError("Phase 2W.1 cannot write the production export path")
    if int(payload.get("count", 0)) <= 0:
        raise ValueError("fail-closed: no publication-eligible places; staged export not written")
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    out.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
