from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import EvidenceStatus, SourceRef, SourceType
from .models import EvidenceKind, PlaceEvidence
from .verification import EvidenceVerificationEngine, VerificationOutcome

POLICY_VERSION = "3.5-controlled-evidence-persistence-v1"
_NAMESPACE = uuid.UUID("6d62ccf9-5fe6-4d08-99d1-8e7920932d93")
ALLOWED_FIELDS = {"phone", "website"}


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _db_snapshot(con: sqlite3.Connection) -> dict[str, Any]:
    tables = [
        str(row[0]) for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        if str(row[0]) != "place_evidence"
    ]
    return {table: [tuple(r) for r in con.execute(f'SELECT * FROM "{table}" ORDER BY rowid')] for table in tables}


def _deterministic_evidence_id(claim: dict[str, Any]) -> str:
    material = "|".join([
        str(claim.get("place_id") or ""),
        str(claim.get("field_name") or ""),
        str(claim.get("value") or ""),
        str(claim.get("source_name") or ""),
        str(claim.get("source_record_id") or ""),
        str(claim.get("source_url") or ""),
    ])
    return str(uuid.uuid5(_NAMESPACE, material))


def _claim_to_evidence(claim: dict[str, Any], *, observed_at: datetime) -> PlaceEvidence:
    return PlaceEvidence(
        place_id=str(claim["place_id"]),
        source=SourceRef(
            source_type=SourceType.WEB,
            source_name=str(claim["source_name"]),
            source_record_id=str(claim.get("source_record_id") or "") or None,
            source_url=str(claim.get("source_url") or "") or None,
            observed_at=observed_at,
        ),
        kind=EvidenceKind.CONTACT,
        field_name=str(claim["field_name"]),
        value=claim["value"],
        status=EvidenceStatus.CANDIDATE,
        evidence_id=_deterministic_evidence_id(claim),
        observed_at=observed_at,
        metadata={
            "persistence": "phase3_5_controlled_web_evidence",
            "policy_version": POLICY_VERSION,
            "phase3_4_evidence_id": claim.get("evidence_id"),
            "target_rank": claim.get("target_rank"),
        },
    )


def _row_to_evidence(row: sqlite3.Row) -> PlaceEvidence:
    source = SourceRef(
        source_type=SourceType(row["source_type"]),
        source_name=row["source_name"],
        source_record_id=row["source_record_id"],
        source_url=row["source_url"],
        observed_at=datetime.fromisoformat(row["source_observed_at"]),
    )
    return PlaceEvidence(
        place_id=row["place_id"],
        source=source,
        kind=EvidenceKind(row["kind"]),
        field_name=row["field_name"],
        value=json.loads(row["value_json"]),
        status=EvidenceStatus(row["status"]),
        evidence_id=row["evidence_id"],
        observed_at=datetime.fromisoformat(row["observed_at"]),
        metadata=json.loads(row["metadata_json"]),
    )


def verify_and_persist_web_evidence(
    *,
    database_path: str | Path,
    acquisition_report_path: str | Path,
    commit: bool = False,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Verify Phase 3.4 web claims and optionally append supported evidence.

    Canonical place rows, published rows and production JSON are out of scope.  The
    only permitted write is append-only place_evidence for claims whose field value
    reaches SUPPORTED or VERIFIED under the existing VerificationPolicy.
    """
    observed_at = observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")

    db_path = Path(database_path)
    report = _load_json(acquisition_report_path)
    claims = report.get("claims") if isinstance(report, dict) else None
    if not isinstance(claims, list):
        raise ValueError("acquisition report must contain claims list")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    before_snapshot = _db_snapshot(con)
    evidence_before = con.execute("SELECT COUNT(*) FROM place_evidence").fetchone()[0]
    db_hash_before = _sha256(db_path)

    candidate_objects: list[PlaceEvidence] = []
    blocked = Counter()
    for claim in claims:
        if not isinstance(claim, dict):
            blocked["invalid_claim"] += 1
            continue
        field = str(claim.get("field_name") or "")
        if field not in ALLOWED_FIELDS:
            blocked["field_not_allowed"] += 1
            continue
        if str(claim.get("status") or "") != EvidenceStatus.CANDIDATE.value:
            blocked["input_not_candidate"] += 1
            continue
        pid = str(claim.get("place_id") or "")
        if con.execute("SELECT 1 FROM places WHERE place_id=?", (pid,)).fetchone() is None:
            blocked["unknown_place"] += 1
            continue
        candidate_objects.append(_claim_to_evidence(claim, observed_at=observed_at))

    by_place_field: dict[tuple[str, str], list[PlaceEvidence]] = defaultdict(list)
    for item in candidate_objects:
        by_place_field[(item.place_id, item.field_name)].append(item)

    engine = EvidenceVerificationEngine()
    decisions: list[dict[str, Any]] = []
    persistable: list[PlaceEvidence] = []
    status_counts = Counter()

    for (place_id, field_name), new_items in sorted(by_place_field.items()):
        existing_rows = con.execute(
            "SELECT * FROM place_evidence WHERE place_id=? AND field_name=? ORDER BY rowid",
            (place_id, field_name),
        ).fetchall()
        existing = [_row_to_evidence(row) for row in existing_rows]
        assessment = engine.verify_field(
            place_id=place_id,
            field_name=field_name,
            evidence=tuple(existing) + tuple(new_items),
        )
        status_counts[assessment.outcome.value] += len(new_items)
        selected = assessment.selected_value
        accepted_ids: list[str] = []
        if assessment.outcome in {VerificationOutcome.SUPPORTED, VerificationOutcome.VERIFIED}:
            for item in new_items:
                if item.value == selected:
                    final = PlaceEvidence(
                        place_id=item.place_id,
                        source=item.source,
                        kind=item.kind,
                        field_name=item.field_name,
                        value=item.value,
                        status=assessment.evidence_status,
                        evidence_id=item.evidence_id,
                        observed_at=item.observed_at,
                        metadata={**dict(item.metadata), "verification_outcome": assessment.outcome.value},
                    )
                    persistable.append(final)
                    accepted_ids.append(final.evidence_id)
        else:
            blocked[f"verification_{assessment.outcome.value}"] += len(new_items)

        decisions.append({
            "place_id": place_id,
            "field_name": field_name,
            "outcome": assessment.outcome.value,
            "selected_value": selected,
            "source_support": [
                {"value": s.value, "source_count": s.source_count, "evidence_count": s.evidence_count}
                for s in assessment.supports
            ],
            "accepted_evidence_ids": accepted_ids,
            "reason": assessment.reason,
        })

    inserted = 0
    already_present = 0
    try:
        if commit:
            con.execute("BEGIN IMMEDIATE")
            for item in persistable:
                if con.execute("SELECT 1 FROM place_evidence WHERE evidence_id=?", (item.evidence_id,)).fetchone():
                    already_present += 1
                    continue
                con.execute(
                    """INSERT INTO place_evidence(
                        evidence_id,place_id,source_type,source_name,source_record_id,source_url,
                        source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        item.evidence_id,item.place_id,item.source.source_type.value,item.source.source_name,
                        item.source.source_record_id,item.source.source_url,item.source.observed_at.isoformat(),
                        item.kind.value,item.field_name,json.dumps(item.value,ensure_ascii=False,sort_keys=True),
                        item.status.value,item.observed_at.isoformat(),
                        json.dumps(dict(item.metadata),ensure_ascii=False,sort_keys=True),
                    ),
                )
                inserted += 1
            if _db_snapshot(con) != before_snapshot:
                raise RuntimeError("canonical or published snapshot changed during evidence persistence")
            con.commit()
        else:
            already_present = sum(
                1 for item in persistable
                if con.execute("SELECT 1 FROM place_evidence WHERE evidence_id=?", (item.evidence_id,)).fetchone()
            )
    except Exception:
        con.rollback()
        raise

    evidence_after = con.execute("SELECT COUNT(*) FROM place_evidence").fetchone()[0]
    after_snapshot = _db_snapshot(con)
    con.close()
    db_hash_after = _sha256(db_path)

    mode = "COMMIT" if commit else "DRY_RUN"
    return {
        "mode": mode,
        "policy_version": POLICY_VERSION,
        "input_claim_count": len(claims),
        "validated_candidate_count": len(candidate_objects),
        "verification_decisions": decisions,
        "verification_status_counts": dict(sorted(status_counts.items())),
        "persistable_evidence_count": len(persistable),
        "persistable_status_counts": dict(sorted(Counter(x.status.value for x in persistable).items())),
        "inserted_evidence_count": inserted,
        "already_present_count": already_present,
        "blocked_counts": dict(sorted(blocked.items())),
        "safety": {
            "evidence_only_writes": True,
            "canonical_unchanged": after_snapshot.get("places") == before_snapshot.get("places"),
            "non_evidence_tables_unchanged": after_snapshot == before_snapshot,
            "trust_policy_lowered": False,
            "production_json_writes": False,
            "evidence_count_before": evidence_before,
            "evidence_count_after": evidence_after,
            "database_sha256_before": db_hash_before,
            "database_sha256_after": db_hash_after,
        },
        "next_stage": "controlled_canonical_adoption_review_required",
    }
