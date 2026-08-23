from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .adoption import AdoptionOutcome, AdoptionPolicy, propose_adoption
from .controlled_evidence_persistence import _row_to_evidence
from .contracts import GeoPoint
from .models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from .verification import EvidenceVerificationEngine

POLICY_VERSION = "3.6-controlled-canonical-adoption-review-v1"
PHASE35_MARKER = "phase3_5_controlled_web_evidence"
REVIEW_FIELDS = frozenset({"phone", "website"})


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _db_snapshot(con: sqlite3.Connection) -> dict[str, list[tuple[Any, ...]]]:
    tables = [
        str(r[0])
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    return {
        table: [tuple(row) for row in con.execute(f'SELECT * FROM "{table}" ORDER BY rowid')]
        for table in tables
    }


def review_controlled_canonical_adoption(*, database_path: str | Path) -> dict[str, Any]:
    """Review persisted Phase 3.5 evidence for canonical adoption without writes.

    All active evidence for each affected place/field participates in verification;
    Phase 3.5 evidence is used only to define review scope.  Existing AdoptionPolicy
    remains authoritative.  This function never applies proposals or publishes data.
    """
    db_path = Path(database_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    before_hash = _sha256(db_path)
    before_snapshot = _db_snapshot(con)

    scope_rows = con.execute(
        "SELECT * FROM place_evidence WHERE metadata_json LIKE ? ORDER BY place_id, field_name, rowid",
        (f'%"persistence": "{PHASE35_MARKER}"%',),
    ).fetchall()
    scope_keys = sorted({(str(r["place_id"]), str(r["field_name"])) for r in scope_rows})

    engine = EvidenceVerificationEngine()
    policy = AdoptionPolicy()
    decisions: list[dict[str, Any]] = []
    counts = Counter()
    verification_counts = Counter()

    for place_id, field_name in scope_keys:
            if field_name not in REVIEW_FIELDS:
                counts["blocked"] += 1
                decisions.append({
                    "place_id": place_id,
                    "field_name": field_name,
                    "outcome": "blocked",
                    "reason": "field outside Phase 3.6 review scope",
                })
                continue

            row = con.execute("SELECT * FROM places WHERE place_id=?", (place_id,)).fetchone()
            if row is None:
                counts["blocked"] += 1
                decisions.append({
                    "place_id": place_id,
                    "field_name": field_name,
                    "outcome": "blocked",
                    "reason": "canonical place missing",
                })
                continue

            cats_raw = json.loads(row["categories_json"])
            if isinstance(cats_raw, dict) and cats_raw.get("__type__") == "tuple":
                categories = tuple(cats_raw.get("items", ()))
            else:
                categories = tuple(cats_raw) if isinstance(cats_raw, list) else ()
            location = None
            if row["latitude"] is not None and row["longitude"] is not None:
                location = GeoPoint(float(row["latitude"]), float(row["longitude"]))
            place = CanonicalPlace(
                identity=PlaceIdentity(str(row["place_id"])),
                canonical_name=str(row["canonical_name"]),
                location=location,
                address_text=row["address_text"],
                province=row["province"],
                categories=categories,
                phone=row["phone"],
                website=row["website"],
                lifecycle=PlaceLifecycle(str(row["lifecycle"])),
                created_at=__import__("datetime").datetime.fromisoformat(row["created_at"]),
                updated_at=__import__("datetime").datetime.fromisoformat(row["updated_at"]),
            )

            all_rows = con.execute(
                "SELECT * FROM place_evidence WHERE place_id=? AND field_name=? ORDER BY rowid",
                (place_id, field_name),
            ).fetchall()
            evidence = tuple(_row_to_evidence(row) for row in all_rows)
            verification = engine.verify_field(
                place_id=place_id,
                field_name=field_name,
                evidence=evidence,
            )
            verification_counts[verification.outcome.value] += 1

            selected_ids = tuple(
                item.evidence_id
                for item in evidence
                if item.value == verification.selected_value
                and item.status.value not in {"rejected", "stale"}
            )
            proposal = propose_adoption(
                place=place,
                verification=verification,
                policy=policy,
                evidence_ids=selected_ids,
            )
            counts[proposal.outcome.value] += 1
            current_value = getattr(place, field_name)

            decisions.append({
                "place_id": place_id,
                "canonical_name": place.canonical_name,
                "province": place.province,
                "field_name": field_name,
                "current_value": current_value,
                "verification_outcome": verification.outcome.value,
                "selected_value": verification.selected_value,
                "source_support": [
                    {
                        "value": s.value,
                        "source_count": s.source_count,
                        "evidence_count": s.evidence_count,
                    }
                    for s in verification.supports
                ],
                "adoption_outcome": proposal.outcome.value,
                "proposed_value": proposal.proposed_value,
                "evidence_ids": list(proposal.evidence_ids),
                "adoption_policy_version": proposal.policy_version,
                "reason": proposal.reason,
            })
    after_snapshot = _db_snapshot(con)
    con.close()
    after_hash = _sha256(db_path)

    return {
        "policy_version": POLICY_VERSION,
        "review_scope_evidence_count": len(scope_rows),
        "review_place_field_count": len(scope_keys),
        "adoption_outcome_counts": dict(sorted(counts.items())),
        "verification_outcome_counts": dict(sorted(verification_counts.items())),
        "decisions": decisions,
        "next_stage": "explicit_controlled_canonical_adoption_required",
        "safety": {
            "database_unchanged": before_hash == after_hash,
            "all_tables_unchanged": before_snapshot == after_snapshot,
            "canonical_writes": False,
            "evidence_writes": False,
            "production_json_writes": False,
            "trust_policy_lowered": False,
            "automatic_adoption": False,
            "province_agnostic": True,
        },
    }
