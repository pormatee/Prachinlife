from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .evidence_trust_calibration import classify_evidence
from .production_quality import _visible
from .sqlite_store import SQLitePlaceRepository

POLICY_VERSION = "3.2-targeted-enrichment-acquisition-v1"
PRODUCTION_FILES = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
)
TARGET_ACTIONS = ("phone", "website", "additional_info")
TRUSTED_CLASSES = frozenset({"direct_osm", "admin_operator", "independent_web"})


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _source_mapping(con: sqlite3.Connection) -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    for row in con.execute("SELECT place_id, source_record_id FROM place_evidence"):
        rec = row["source_record_id"] or ""
        if "#" not in rec:
            continue
        fn, record_id = rec.split("#", 1)
        if fn in PRODUCTION_FILES and record_id:
            mapping[(fn, record_id)] = row["place_id"]
    return mapping


def _load_database(database_path: str | Path):
    db = Path(database_path).resolve()
    con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        mapping = _source_mapping(con)
        places = {}
        for row in con.execute("SELECT * FROM places ORDER BY place_id"):
            place = SQLitePlaceRepository._place_from_row(row)
            places[place.identity.place_id] = place
        evidence = defaultdict(list)
        for row in con.execute("SELECT * FROM place_evidence ORDER BY place_id,evidence_id"):
            item = SQLitePlaceRepository._evidence_from_row(row)
            evidence[item.place_id].append(item)
        return mapping, places, {k: tuple(v) for k, v in evidence.items()}
    finally:
        con.close()


def _visible_records(repo_root: str | Path, mapping):
    root = Path(repo_root)
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for fn in PRODUCTION_FILES:
        for row in _load_json(root / fn):
            if not isinstance(row, dict) or not _visible(row, fn):
                continue
            record_id = str(row.get("id") or "")
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            place_id = metadata.get("v2_place_id") or mapping.get((fn, record_id))
            result[(fn, record_id)] = {"record": row, "place_id": place_id}
    return result


def _active_field_evidence(items, field: str):
    return tuple(
        e for e in items
        if e.field_name == field and e.status.value not in {"rejected", "stale"}
    )


def _additional_info_evidence(items):
    result = []
    for e in items:
        if e.status.value in {"rejected", "stale"}:
            continue
        url = e.source.source_url or ""
        if not url.startswith(("http://", "https://")):
            continue
        if "openstreetmap.org" in url.casefold():
            continue
        result.append(e)
    return tuple(result)


def _evidence_summary(items, action: str):
    selected = _additional_info_evidence(items) if action == "additional_info" else _active_field_evidence(items, action)
    classes = Counter(classify_evidence(e) for e in selected)
    return {
        "active_evidence_count": len(selected),
        "trust_classes": dict(sorted(classes.items())),
        "trusted_evidence_available": any(k in TRUSTED_CLASSES for k in classes),
    }


def _readiness(record: dict[str, Any], place, action: str) -> bool:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    if action == "phone":
        return bool(place.phone or record.get("phone") or metadata.get("phone"))
    if action == "website":
        return bool(place.website or record.get("website") or metadata.get("website"))
    if action == "additional_info":
        if record.get("prachinlife_page_url"):
            return True
        for link in record.get("external_links") or ():
            if not isinstance(link, dict) or not link.get("url"):
                continue
            kind = str(link.get("type") or "").casefold()
            url = str(link.get("url") or "").casefold()
            if kind != "osm" and "openstreetmap.org" not in url:
                return True
        return False
    raise ValueError(action)


def _next_step(ready: bool, summary: dict[str, Any], action: str) -> str:
    if ready:
        return "already_ready"
    if summary["trusted_evidence_available"]:
        return "review_existing_trusted_evidence"
    if summary["active_evidence_count"]:
        return "manual_review_untrusted_or_legacy_evidence"
    return f"acquire_new_{action}_evidence"


def build_targeted_enrichment_plan(
    *,
    database_path: str | Path,
    repo_root: str | Path,
    quality_report_path: str | Path,
    limit: int = 50,
) -> dict[str, Any]:
    """Build a deterministic, read-only evidence acquisition plan.

    This phase never adopts values, changes evidence status, writes canonical data,
    or changes production JSON. Missing enrichment with no evidence remains missing.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    db_before = _sha256(database_path)
    mapping, places, evidence = _load_database(database_path)
    visible = _visible_records(repo_root, mapping)
    quality = _load_json(Path(quality_report_path))
    priorities = list(quality.get("top_enrichment_priorities") or ())[:limit]

    queue = []
    status_counts = Counter()
    unmapped = []
    for priority in priorities:
        key = (str(priority.get("dataset") or ""), str(priority.get("id") or ""))
        item = visible.get(key)
        if not item or not item.get("place_id") or item["place_id"] not in places:
            unmapped.append({"dataset": key[0], "id": key[1], "name": priority.get("name")})
            continue
        place_id = item["place_id"]
        place = places[place_id]
        ev = evidence.get(place_id, ())
        actions = {}
        for action in TARGET_ACTIONS:
            ready = _readiness(item["record"], place, action)
            summary = _evidence_summary(ev, action)
            step = _next_step(ready, summary, action)
            status_counts[step] += 1
            actions[action] = {"ready": ready, "next_step": step, **summary}
        queue.append({
            "rank": len(queue) + 1,
            "dataset": key[0],
            "record_id": key[1],
            "place_id": place_id,
            "name": priority.get("name") or place.canonical_name,
            "quality_score": priority.get("score"),
            "quality_tier": priority.get("tier"),
            "actions": actions,
        })

    db_after = _sha256(database_path)
    mapped_visible = sum(1 for x in visible.values() if x.get("place_id") in places)
    return {
        "mode": "READ_ONLY_TARGETED_ENRICHMENT_ACQUISITION_PLAN",
        "policy_version": POLICY_VERSION,
        "quality_priority_count": len(priorities),
        "queue_count": len(queue),
        "visible_place_count": len(visible),
        "mapped_visible_place_count": mapped_visible,
        "unmapped_priority_count": len(unmapped),
        "unmapped_priorities": unmapped,
        "next_step_counts": dict(sorted(status_counts.items())),
        "queue": queue,
        "safety": {
            "canonical_writes": False,
            "evidence_writes": False,
            "production_json_writes": False,
            "trust_policy_lowered": False,
            "database_unchanged": db_before == db_after,
            "database_sha256_before": db_before,
            "database_sha256_after": db_after,
        },
    }
