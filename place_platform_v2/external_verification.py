from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Any

from .staged_milestone import POLICY_VERSION, _ensure_observation_table

EXTERNAL_POLICY_VERSION = "external-verification-v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def commit_external_verifications(
    database_path: str | Path,
    records: Iterable[Mapping[str, Any]],
):
    """Append source-backed current existence/category evidence.

    This function never mutates canonical place fields. It only appends evidence
    and staged observation receipts. Calls are idempotent for the same
    place/source/observed_at tuple.
    """
    con = sqlite3.connect(database_path)
    committed = []
    try:
        with con:
            _ensure_observation_table(con)
            for raw in records:
                item = dict(raw)
                place_id = str(item["place_id"])
                source_url = str(item["source_url"])
                source_type = str(item.get("source_type") or "web")
                source_name = str(item["source_name"])
                source_record_id = str(item.get("source_record_id") or source_url)
                observed_at = str(item.get("observed_at") or _now_iso())
                categories = tuple(item.get("categories") or ())

                exists = con.execute(
                    "select 1 from places where place_id=?",
                    (place_id,),
                ).fetchone()
                if not exists:
                    raise KeyError(f"unknown place_id: {place_id}")

                observation_id = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"external|{place_id}|{source_url}|{observed_at}",
                ))
                if con.execute(
                    "select 1 from staged_existence_observations where observation_id=?",
                    (observation_id,),
                ).fetchone():
                    continue

                evidence_id = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    observation_id + "|existence",
                ))
                metadata = {
                    "provenance_origin": "current_existence_observation",
                    "policy_version": EXTERNAL_POLICY_VERSION,
                    "observation_status": "current_listing",
                }
                con.execute(
                    """insert into place_evidence(
                    evidence_id,place_id,source_type,source_name,source_record_id,
                    source_url,source_observed_at,kind,field_name,value_json,status,
                    observed_at,metadata_json)
                    values(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        evidence_id, place_id, source_type, source_name,
                        source_record_id, source_url, observed_at, "existence",
                        "existence", "true", "supported", observed_at,
                        json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                    ),
                )

                category_evidence_id = None
                if categories:
                    category_evidence_id = str(uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        observation_id + "|categories",
                    ))
                    value_json = json.dumps(
                        {"__type__": "tuple", "items": list(categories)},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    category_metadata = {
                        "provenance_origin": "external_verification",
                        "policy_version": EXTERNAL_POLICY_VERSION,
                    }
                    con.execute(
                        """insert into place_evidence(
                        evidence_id,place_id,source_type,source_name,source_record_id,
                        source_url,source_observed_at,kind,field_name,value_json,status,
                        observed_at,metadata_json)
                        values(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            category_evidence_id, place_id, source_type, source_name,
                            source_record_id, source_url, observed_at, "category",
                            "categories", value_json, "supported", observed_at,
                            json.dumps(category_metadata, ensure_ascii=False, sort_keys=True),
                        ),
                    )

                    if item.get("supersede_legacy_category_subsets") is True:
                        canonical_set = set(categories)
                        rows = con.execute(
                            "select evidence_id,value_json,metadata_json from place_evidence "
                            "where place_id=? and field_name='categories' "
                            "and source_name='prachinlife-v1-json' and status='candidate'",
                            (place_id,),
                        ).fetchall()
                        for legacy_id, legacy_value_json, legacy_metadata_json in rows:
                            try:
                                legacy_value = json.loads(legacy_value_json)
                                if isinstance(legacy_value, dict) and legacy_value.get("__type__") == "tuple":
                                    legacy_items = set(legacy_value.get("items") or [])
                                elif isinstance(legacy_value, list):
                                    legacy_items = set(legacy_value)
                                else:
                                    continue
                            except Exception:
                                continue
                            if not legacy_items or legacy_items == canonical_set or not legacy_items < canonical_set:
                                continue
                            try:
                                legacy_md = json.loads(legacy_metadata_json or "{}")
                            except Exception:
                                legacy_md = {}
                            legacy_md.update({
                                "superseded_by_evidence_id": category_evidence_id,
                                "superseded_reason": "official source confirms canonical category union",
                                "resolution_policy_version": EXTERNAL_POLICY_VERSION,
                            })
                            con.execute(
                                "update place_evidence set status='stale',metadata_json=? where evidence_id=?",
                                (json.dumps(legacy_md, ensure_ascii=False, sort_keys=True), legacy_id),
                            )

                payload = {
                    **item,
                    "status": "current_listing",
                    "observed_at": observed_at,
                    "policy_version": EXTERNAL_POLICY_VERSION,
                }
                con.execute(
                    "insert into staged_existence_observations values(?,?,?,?,?,?,?,?)",
                    (
                        observation_id, place_id, source_url, "current_listing",
                        observed_at, evidence_id, EXTERNAL_POLICY_VERSION,
                        json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    ),
                )
                committed.append({
                    "place_id": place_id,
                    "observation_id": observation_id,
                    "evidence_id": evidence_id,
                    "category_evidence_id": category_evidence_id,
                })
        return committed
    finally:
        con.close()
