from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core_place_verification_compat import (
    COORDINATE_REPORT_NAMES,
    evaluate_compatibility,
)

POLICY_VERSION = "core-place-verification-v2-controlled-adoption-v1"
_NAMESPACE = uuid.UUID("a691ef73-c45b-4c48-8b43-52355cf807bd")


def _norm(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").casefold(), flags=re.UNICODE)


def _phone(value: Any) -> str:
    digits = re.sub(r"\D+", "", str(value or ""))
    return "0" + digits[2:] if digits.startswith("66") and len(digits) >= 10 else digits


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(row.get("payload_json") or "{}")
    except Exception:
        return {}


def _snapshot(con: sqlite3.Connection) -> dict[str, list[tuple[Any, ...]]]:
    names = [
        r[0]
        for r in con.execute(
            "select name from sqlite_master "
            "where type='table' and name not like 'sqlite_%' order by name"
        )
    ]
    return {
        name: [tuple(x) for x in con.execute(f'SELECT * FROM "{name}" ORDER BY rowid')]
        for name in names
    }


def _pid(candidate_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, "place|" + candidate_id))


def _eid(candidate_id: str, source_eid: str, field: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"evidence|{candidate_id}|{source_eid}|{field}"))


def _rid(candidate_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, "revision|" + candidate_id))


def _coordinate_report_paths(paths=()) -> list[Path]:
    if paths:
        return [Path(x) for x in paths]
    root = Path(__file__).resolve().parents[1]
    report_dir = root / "data/v2/discovery_reports"
    return [report_dir / name for name in COORDINATE_REPORT_NAMES]


def _load_coordinate_details(paths=()) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path in _coordinate_report_paths(paths):
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for row in payload.get("results", []):
            name = str(row.get("name") or "").strip()
            province = str(row.get("province") or "").strip()
            outcome = row.get("coordinate_outcome")
            if not name or not province or not outcome:
                continue
            item = dict(row)
            item["report_path"] = str(path)
            result[(name, province)] = item
    return result


def evaluate_controlled_new_place_adoption_core_v2(
    *, database_path, coordinate_report_paths=()
) -> dict[str, Any]:
    db = Path(database_path)
    before = db.read_bytes()
    compat = evaluate_compatibility(
        database_path=db,
        coordinate_report_paths=coordinate_report_paths,
    )
    decisions = []
    counts = Counter()
    for row in compat["decisions"]:
        state = row["state"]
        if state == "VERIFIED_NEAR_ME_READY":
            outcome = "READY_CANONICAL_NEAR_ME"
            next_step = "explicit_controlled_commit"
        elif state == "VERIFIED_PLACE_COORDINATE_PENDING":
            outcome = "READY_CANONICAL_COORDINATE_PENDING"
            next_step = "explicit_controlled_commit_then_coordinate_followup"
        else:
            outcome = "NOT_READY"
            next_step = "resolve_verification_or_review_blockers"
        counts[outcome] += 1
        decisions.append({**row, "outcome": outcome, "next_step": next_step})
    after = db.read_bytes()
    return {
        "status": "PASS",
        "policy_version": POLICY_VERSION,
        "candidate_count": len(decisions),
        "decision_counts": dict(sorted(counts.items())),
        "canonical_eligible_count": sum(x["canonical_eligible"] for x in decisions),
        "near_me_ready_count": sum(x["near_me_eligible"] for x in decisions),
        "coordinate_pending_count": sum(
            x["outcome"] == "READY_CANONICAL_COORDINATE_PENDING" for x in decisions
        ),
        "not_ready_count": counts["NOT_READY"],
        "decisions": decisions,
        "safety": {
            "database_unchanged": before == after,
            "database_writes": False,
            "production_json_writes": False,
            "automatic_canonical_adoption": False,
            "automatic_publication": False,
            "near_me_requires_exact_coordinates": True,
            "coordinate_pending_can_have_canonical_shell": True,
            "trust_policy_lowered": False,
            "category_agnostic_core": True,
        },
    }


def run_controlled_new_place_adoption_core_v2(
    *, database_path, coordinate_report_paths=(), commit=False, adopted_at=None,
    candidate_ids=(),
) -> dict[str, Any]:
    adopted_at = adopted_at or datetime.now(timezone.utc)
    if adopted_at.tzinfo is None:
        raise ValueError("adopted_at must be timezone-aware")

    db = Path(database_path)
    evaluation = evaluate_controlled_new_place_adoption_core_v2(
        database_path=db,
        coordinate_report_paths=coordinate_report_paths,
    )
    eligible = [x for x in evaluation["decisions"] if x["canonical_eligible"]]
    requested_candidate_ids = {str(x) for x in candidate_ids if str(x)}
    if requested_candidate_ids:
        known_candidate_ids = {str(x["candidate_id"]) for x in evaluation["decisions"]}
        unknown = requested_candidate_ids - known_candidate_ids
        if unknown:
            raise RuntimeError(
                "controlled adoption scope contains unknown candidate_ids: "
                + ",".join(sorted(unknown))
            )
        eligible = [
            x for x in eligible
            if str(x["candidate_id"]) in requested_candidate_ids
        ]
    coordinate_details = _load_coordinate_details(coordinate_report_paths)

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.execute("pragma foreign_keys=on")
    before = _snapshot(con)
    inserted_places = 0
    inserted_evidence = 0
    inserted_revisions = 0

    if commit and eligible:
        con.execute("BEGIN IMMEDIATE")
        try:
            for decision in eligible:
                candidate = dict(
                    con.execute(
                        "select * from precanonical_candidates where candidate_id=?",
                        (decision["candidate_id"],),
                    ).fetchone()
                )
                evidence = [
                    dict(r)
                    for r in con.execute(
                        "select * from precanonical_evidence where candidate_id=? order by evidence_id",
                        (decision["candidate_id"],),
                    )
                ]

                coord = coordinate_details.get((decision["name"], decision["province"]))
                lat = lon = None
                if decision["near_me_eligible"]:
                    if not coord or coord.get("coordinate_outcome") != "EXACT_COORDINATES_VERIFIED":
                        raise RuntimeError(
                            f"near-me eligible candidate lacks verified coordinate details: {decision['name']}"
                        )
                    lat = float(coord["latitude"])
                    lon = float(coord["longitude"])

                pid = _pid(candidate["candidate_id"])
                now = adopted_at.isoformat()
                phones = Counter(_phone(x["phone"]) for x in evidence if _phone(x["phone"]))
                phone = phones.most_common(1)[0][0] if phones else None
                addresses = [
                    _payload(x).get("address_text")
                    for x in evidence
                    if _payload(x).get("address_text")
                ]
                address = addresses[0] if addresses else None
                life = Counter(
                    str(x["lifecycle_status"]).casefold()
                    for x in evidence
                    if x["lifecycle_status"]
                )
                lifecycle = "active" if life.get("open") else "unknown"

                cur = con.execute(
                    "insert or ignore into places values(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        pid,
                        candidate["proposed_name"],
                        lat,
                        lon,
                        address,
                        candidate["province"],
                        json.dumps([candidate["category"]], ensure_ascii=False),
                        phone,
                        None,
                        lifecycle,
                        now,
                        now,
                    ),
                )
                inserted_places += max(cur.rowcount, 0)

                for source in evidence:
                    claims = [
                        ("canonical_name", candidate["proposed_name"], "name"),
                        ("province", candidate["province"], "other"),
                    ]
                    if source.get("phone"):
                        claims.append(("phone", _phone(source["phone"]), "contact"))
                    payload = _payload(source)
                    if (
                        payload.get("latitude") is not None
                        and payload.get("longitude") is not None
                        and payload.get("coordinate_owner") in (None, "candidate")
                    ):
                        claims.append(
                            (
                                "location",
                                {
                                    "latitude": payload["latitude"],
                                    "longitude": payload["longitude"],
                                },
                                "location",
                            )
                        )
                    for field, value, kind in claims:
                        eid = _eid(candidate["candidate_id"], source["evidence_id"], field)
                        cur = con.execute(
                            """insert or ignore into place_evidence(
                                evidence_id,place_id,source_type,source_name,source_record_id,
                                source_url,source_observed_at,kind,field_name,value_json,status,
                                observed_at,metadata_json
                            ) values(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                eid,
                                pid,
                                source["source_type"],
                                source["source_name"],
                                source["source_record_id"],
                                source["source_url"],
                                source["created_at"],
                                kind,
                                field,
                                json.dumps(value, ensure_ascii=False),
                                "supported",
                                now,
                                json.dumps(
                                    {
                                        "precanonical_evidence_id": source["evidence_id"],
                                        "source_family": source["source_family"],
                                        "core_v2_state": decision["state"],
                                    },
                                    ensure_ascii=False,
                                ),
                            ),
                        )
                        inserted_evidence += max(cur.rowcount, 0)

                if decision["near_me_eligible"]:
                    synthetic_source_id = "core-v2-coordinate|" + decision["candidate_id"]
                    eid = _eid(candidate["candidate_id"], synthetic_source_id, "location")
                    cur = con.execute(
                        """insert or ignore into place_evidence(
                            evidence_id,place_id,source_type,source_name,source_record_id,
                            source_url,source_observed_at,kind,field_name,value_json,status,
                            observed_at,metadata_json
                        ) values(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            eid,
                            pid,
                            "verification_report",
                            "Core Place Verification V2 exact coordinate report",
                            candidate["candidate_key"],
                            None,
                            now,
                            "location",
                            "location",
                            json.dumps({"latitude": lat, "longitude": lon}, ensure_ascii=False),
                            "verified",
                            now,
                            json.dumps(
                                {
                                    "coordinate_report_path": coord.get("report_path"),
                                    "accepted_source_families": coord.get("accepted_source_families") or [],
                                    "core_v2_state": decision["state"],
                                },
                                ensure_ascii=False,
                            ),
                        ),
                    )
                    inserted_evidence += max(cur.rowcount, 0)

                rid = _rid(candidate["candidate_id"])
                after_values = {
                    "canonical_name": candidate["proposed_name"],
                    "province": candidate["province"],
                    "latitude": lat,
                    "longitude": lon,
                    "core_v2_state": decision["state"],
                }
                cur = con.execute(
                    """insert or ignore into place_revisions(
                        revision_id,place_id,changed_fields_json,before_values_json,
                        after_values_json,reason,evidence_ids_json,policy_version,created_at
                    ) values(?,?,?,?,?,?,?,?,?)""",
                    (
                        rid,
                        pid,
                        json.dumps(["create_place"], ensure_ascii=False),
                        json.dumps({}),
                        json.dumps(after_values, ensure_ascii=False),
                        "Core Place Verification V2 controlled canonical shell adoption",
                        json.dumps([x["evidence_id"] for x in evidence], ensure_ascii=False),
                        POLICY_VERSION,
                        now,
                    ),
                )
                inserted_revisions += max(cur.rowcount, 0)

                status = (
                    "adopted_canonical_near_me_ready"
                    if decision["near_me_eligible"]
                    else "adopted_canonical_coordinate_pending"
                )
                con.execute(
                    "update precanonical_candidates set status=?,policy_version=? where candidate_id=?",
                    (status, POLICY_VERSION, candidate["candidate_id"]),
                )
            con.commit()
        except Exception:
            con.rollback()
            raise

    after = _snapshot(con)
    con.close()
    return {
        "status": "PASS",
        "mode": "COMMIT" if commit else "DRY_RUN",
        "requested_candidate_ids": sorted(requested_candidate_ids),
        "scoped_commit": bool(requested_candidate_ids),
        "policy_version": POLICY_VERSION,
        "eligible_count": len(eligible),
        "near_me_ready_count": evaluation["near_me_ready_count"],
        "coordinate_pending_count": evaluation["coordinate_pending_count"],
        "inserted_place_count": inserted_places,
        "inserted_evidence_count": inserted_evidence,
        "inserted_revision_count": inserted_revisions,
        "decisions": evaluation["decisions"],
        "safety": {
            "database_unchanged": before == after,
            "production_json_writes": False,
            "automatic_publication": False,
            "automatic_canonical_adoption": False,
            "explicit_commit_required": True,
            "near_me_requires_exact_coordinates": True,
            "coordinate_pending_canonical_shell_has_null_coordinates": True,
            "trust_policy_lowered": False,
        },
    }
