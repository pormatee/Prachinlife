from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .staged_overlay import FILES, _canonical_rows, _overlay_record, _public_enrichment_rows

POLICY_VERSION = "3.8-controlled-publication-impact-preview-v1"
ADOPTION_POLICY_VERSION = "3.7-explicit-controlled-canonical-adoption-v1"
_ALLOWED_CONTACT_PATHS = {"metadata.phone", "metadata.website"}
_ALLOWED_MARKER_PATHS = {
    "metadata.v2_preview_overlay",
    "metadata.v2_place_id",
    "metadata.v2_policy_version",
    "metadata.v2_core_identity_source",
}
_IDENTITY_PATHS = {
    "title",
    "provider.name",
    "location.place_name",
    "location.province",
    "location.latitude",
    "location.longitude",
    "category",
    "original_type",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _open_ro(database_path: str | Path):
    path = Path(database_path).resolve()
    con = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _revision_scope(database_path: str | Path) -> list[dict[str, Any]]:
    con = _open_ro(database_path)
    try:
        rows = con.execute(
            "SELECT revision_id,place_id,changed_fields_json,before_values_json,"
            "after_values_json,evidence_ids_json,policy_version,created_at "
            "FROM place_revisions WHERE policy_version=? ORDER BY created_at,revision_id",
            (ADOPTION_POLICY_VERSION,),
        ).fetchall()
    finally:
        con.close()
    result = []
    for row in rows:
        fields = json.loads(row["changed_fields_json"] or "[]")
        before = json.loads(row["before_values_json"] or "{}")
        after = json.loads(row["after_values_json"] or "{}")
        for field in fields:
            if field not in {"phone", "website"}:
                continue
            result.append({
                "revision_id": row["revision_id"],
                "place_id": row["place_id"],
                "field_name": field,
                "before_value": before.get(field),
                "after_value": after.get(field),
                "evidence_ids": json.loads(row["evidence_ids_json"] or "[]"),
                "created_at": row["created_at"],
            })
    return result


def _production_mapping(database_path: str | Path, place_ids: set[str]) -> dict[str, list[tuple[str, str]]]:
    con = _open_ro(database_path)
    try:
        mapping: dict[str, set[tuple[str, str]]] = {pid: set() for pid in place_ids}
        for pid in sorted(place_ids):
            rows = con.execute(
                "SELECT source_record_id FROM place_evidence WHERE place_id=?",
                (pid,),
            ).fetchall()
            for row in rows:
                record_id = str(row["source_record_id"] or "")
                if "#" not in record_id:
                    continue
                filename, source_id = record_id.split("#", 1)
                if filename in FILES and source_id:
                    mapping[pid].add((filename, source_id))
        return {pid: sorted(values) for pid, values in mapping.items()}
    finally:
        con.close()


def _diff(old: Any, new: Any, prefix: str = "") -> list[dict[str, Any]]:
    if isinstance(old, dict) and isinstance(new, dict):
        out: list[dict[str, Any]] = []
        for key in sorted(set(old) | set(new)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in old:
                out.append({"path": path, "kind": "add", "before": None, "after": copy.deepcopy(new[key])})
            elif key not in new:
                out.append({"path": path, "kind": "remove", "before": copy.deepcopy(old[key]), "after": None})
            else:
                out.extend(_diff(old[key], new[key], path))
        return out
    if old != new:
        return [{"path": prefix, "kind": "change", "before": copy.deepcopy(old), "after": copy.deepcopy(new)}]
    return []


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def preview_controlled_publication_impact(*, database_path: str | Path, repo_root: str | Path) -> dict[str, Any]:
    """Preview Phase 3.7 contact adoption against current production JSON.

    Read-only by construction: opens SQLite in mode=ro and never writes production JSON.
    The preview is national/province-agnostic and follows source-record mappings across all
    four production datasets.
    """
    db = Path(database_path).resolve()
    root = Path(repo_root).resolve()
    db_hash_before = _sha256(db)
    prod_hash_before = {fn: _sha256(root / fn) for fn in FILES}

    revisions = _revision_scope(db)
    place_ids = {r["place_id"] for r in revisions}
    canonical = _canonical_rows(db, place_ids)
    enrichment = _public_enrichment_rows(db, place_ids)
    mappings = _production_mapping(db, place_ids)

    records_by_file: dict[str, dict[str, dict[str, Any]]] = {}
    for fn in FILES:
        rows = _load_json(root / fn)
        records_by_file[fn] = {str(row.get("id", "")): row for row in rows if isinstance(row, dict)}

    revisions_by_place: dict[str, list[dict[str, Any]]] = {}
    for item in revisions:
        revisions_by_place.setdefault(item["place_id"], []).append(item)

    blockers: list[str] = []
    impacts: list[dict[str, Any]] = []
    changed_records: set[tuple[str, str]] = set()
    field_impact_counts: Counter[str] = Counter()
    external_link_additions = 0
    unexpected_change_count = 0
    destructive_change_count = 0
    overwrite_count = 0
    identity_change_count = 0

    for pid in sorted(place_ids):
        if pid not in canonical:
            blockers.append(f"canonical_missing:{pid}")
            continue
        mapped = mappings.get(pid) or []
        if not mapped:
            blockers.append(f"production_mapping_missing:{pid}")
            continue
        targeted_fields = {r["field_name"] for r in revisions_by_place.get(pid, [])}
        for fn, source_id in mapped:
            record = records_by_file.get(fn, {}).get(source_id)
            if record is None:
                blockers.append(f"production_record_missing:{fn}#{source_id}:{pid}")
                continue
            preview = _overlay_record(record, canonical[pid], pid, enrichment.get(pid))
            diffs = _diff(record, preview)
            classified = []
            for change in diffs:
                path = change["path"]
                category = "unexpected"
                if path in _IDENTITY_PATHS:
                    category = "identity_change"
                    identity_change_count += 1
                    blockers.append(f"identity_change:{fn}#{source_id}:{path}")
                elif path in _ALLOWED_CONTACT_PATHS:
                    field = path.split(".", 1)[1]
                    if field not in targeted_fields:
                        category = "unexpected_contact_change"
                        unexpected_change_count += 1
                        blockers.append(f"untargeted_contact_change:{fn}#{source_id}:{path}")
                    elif _nonempty(change["before"]) and change["before"] != change["after"]:
                        category = "contact_overwrite"
                        overwrite_count += 1
                        blockers.append(f"contact_overwrite:{fn}#{source_id}:{path}")
                    else:
                        category = "targeted_contact_addition"
                        field_impact_counts[field] += 1
                elif path == "external_links":
                    category = "trusted_external_links_addition"
                    before_urls = {x.get("url") for x in (change["before"] or []) if isinstance(x, dict)}
                    after_urls = {x.get("url") for x in (change["after"] or []) if isinstance(x, dict)}
                    external_link_additions += len(after_urls - before_urls)
                    if change["kind"] == "remove":
                        destructive_change_count += 1
                        blockers.append(f"external_links_removed:{fn}#{source_id}")
                elif path in _ALLOWED_MARKER_PATHS:
                    category = "v2_overlay_marker"
                elif change["kind"] == "remove":
                    category = "destructive_change"
                    destructive_change_count += 1
                    blockers.append(f"destructive_change:{fn}#{source_id}:{path}")
                elif _nonempty(change["before"]) and change["before"] != change["after"]:
                    category = "unexpected_overwrite"
                    overwrite_count += 1
                    blockers.append(f"unexpected_overwrite:{fn}#{source_id}:{path}")
                else:
                    unexpected_change_count += 1
                    blockers.append(f"unexpected_change:{fn}#{source_id}:{path}")
                classified.append({**change, "category": category})
            if diffs:
                changed_records.add((fn, source_id))
            impacts.append({
                "place_id": pid,
                "canonical_name": canonical[pid]["canonical_name"],
                "province": canonical[pid]["province"],
                "production_file": fn,
                "production_record_id": source_id,
                "targeted_fields": sorted(targeted_fields),
                "changes": classified,
            })

    # Each Phase 3.7 field should affect exactly one current production record.
    for item in revisions:
        if field_impact_counts[item["field_name"]] <= 0:
            # Field-specific global count is coarse; per-place validation below is exact.
            pass
    for pid, revs in revisions_by_place.items():
        for rev in revs:
            expected_path = f"metadata.{rev['field_name']}"
            matches = [
                c for impact in impacts if impact["place_id"] == pid
                for c in impact["changes"]
                if c["path"] == expected_path and c["category"] == "targeted_contact_addition"
            ]
            if len(matches) != 1:
                blockers.append(f"targeted_field_impact_count:{pid}:{rev['field_name']}:{len(matches)}")

    db_hash_after = _sha256(db)
    prod_hash_after = {fn: _sha256(root / fn) for fn in FILES}
    status = "PASS" if not blockers else "BLOCKED"
    return {
        "policy_version": POLICY_VERSION,
        "mode": "READ_ONLY_PREVIEW",
        "status": status,
        "adoption_revision_count": len(revisions),
        "adopted_place_count": len(place_ids),
        "mapped_place_count": sum(1 for pid in place_ids if mappings.get(pid)),
        "changed_production_record_count": len(changed_records),
        "targeted_field_impact_counts": dict(sorted(field_impact_counts.items())),
        "external_link_addition_count": external_link_additions,
        "identity_change_count": identity_change_count,
        "overwrite_count": overwrite_count,
        "destructive_change_count": destructive_change_count,
        "unexpected_change_count": unexpected_change_count,
        "blockers": blockers,
        "impacts": impacts,
        "safety": {
            "database_unchanged": db_hash_before == db_hash_after,
            "production_json_unchanged": prod_hash_before == prod_hash_after,
            "production_json_writes": False,
            "automatic_publication": False,
            "trust_policy_lowered": False,
            "province_agnostic": True,
            "destructive_changes_allowed": False,
        },
    }
