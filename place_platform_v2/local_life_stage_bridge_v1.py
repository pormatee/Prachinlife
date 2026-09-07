from __future__ import annotations

import json
from pathlib import Path

PUBLIC_FILES = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
)


def _categories(row):
    raw = None
    if isinstance(row, dict):
        raw = row.get("categories_json", row.get("categories"))
    else:
        raw = getattr(row, "categories_json", getattr(row, "categories", None))
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = [raw]
    if isinstance(raw, dict):
        if raw.get("__type__") == "tuple":
            raw = raw.get("items", [])
        elif isinstance(raw.get("items"), list):
            raw = raw.get("items", [])
        else:
            raw = []
    if isinstance(raw, tuple):
        raw = list(raw)
    if not isinstance(raw, list):
        raw = [] if raw in (None, "") else [raw]
    return {str(x).strip().casefold() for x in raw if str(x).strip()}


def _targets(cats):
    out = []
    if cats & {"vegetarian", "vegan", "jay", "เจ", "มังสวิรัติ", "อาหารเจ", "อาหารมังสวิรัติ"}:
        out.append("vegetarian_index.json")
    if cats & {"eat", "food", "restaurant", "restaurants", "cafe", "coffee", "fast_food", "food_court", "ice_cream", "อาหาร", "ร้านอาหาร", "กิน", "ของกิน"}:
        out.append("prachinlife_index.json")
    if cats & {"go", "travel", "tourism", "attraction", "temple", "park", "nature", "เที่ยว", "ท่องเที่ยว"}:
        out.append("go_index.json")
    if cats & {"service", "services", "hospital", "clinic", "pharmacy", "bank", "atm", "fuel", "school", "college", "university", "laundry", "car_repair", "บริการ"}:
        out.append("service_index.json")
    return tuple(out)


def _load_list(path: Path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, list):
        raise ValueError(f"{path.name} staging payload must be a list")
    return obj


def bridge_local_life_unmapped_places(
    database_path,
    province,
    staging_dir,
):
    from .local_life_trust_policy_v1 import local_life_eligible_place_ids
    from .staged_overlay import _canonical_rows, _public_enrichment_rows, _overlay_record
    from .controlled_production_switch import _overlay_place_ids

    database_path = Path(database_path).resolve()
    staging_dir = Path(staging_dir).resolve()

    eligible_ids, blocked = local_life_eligible_place_ids(database_path, province)
    eligible = set(str(x) for x in eligible_ids)
    existing = set(_overlay_place_ids(staging_dir)) & eligible
    missing = sorted(eligible - existing)

    canon = _canonical_rows(database_path, set(missing)) if missing else {}
    enrichment = _public_enrichment_rows(database_path, set(missing)) if missing else {}

    added_records = {fn: 0 for fn in PUBLIC_FILES}
    added_place_ids = []

    for pid in missing:
        row = canon.get(pid)
        if row is None:
            continue
        targets = _targets(_categories(row))
        if not targets:
            continue

# LOCAL_LIFE_GENERIC_NEW_PLACE_RECORD_SHAPE_V1_1: seed canonical display/location scalars for generic new-place compatibility records.
        record = _overlay_record({"id": pid, "place_id": pid, "name": (row.get("canonical_name") or row.get("name")), "province": row.get("province"), "latitude": row.get("latitude"), "longitude": row.get("longitude")}, row, pid, enrichment.get(pid))
        if not isinstance(record, dict):
            raise TypeError("new-place overlay serializer must return dict")
        record = dict(record)
        record["id"] = pid
        record["place_id"] = pid

        metadata = record.get("metadata")
        metadata = dict(metadata) if isinstance(metadata, dict) else {}
        metadata["v2_place_id"] = pid
        metadata["local_life_staging_bridge"] = "LOCAL-LIFE-STAGE-BRIDGE-V1"
        record["metadata"] = metadata

        written = False
        for fn in targets:
            path = staging_dir / fn
            if not path.exists():
                continue
            payload = _load_list(path)
            if any(
                isinstance(x, dict)
                and str(
                    x.get("place_id")
                    or (
                        (x.get("metadata") or {}).get("v2_place_id")
                        if isinstance(x.get("metadata"), dict)
                        else ""
                    )
                    or x.get("id")
                    or ""
                ) == pid
                for x in payload
            ):
                continue
            payload.append(dict(record))
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            added_records[fn] += 1
            written = True
        if written:
            added_place_ids.append(pid)

    existing_after = set(_overlay_place_ids(staging_dir)) & eligible
    unmapped_after = sorted(eligible - existing_after)

    manifest_path = staging_dir / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    if not isinstance(manifest, dict):
        manifest = {}

    manifest["eligible_place_count"] = len(eligible)
    manifest["overlay_place_count"] = len(existing_after)
    manifest["unmapped_eligible_place_count"] = len(unmapped_after)
    manifest["new_place_bridge_place_count"] = len(added_place_ids)
    manifest["new_place_bridge_records"] = added_records
    manifest["local_life_stage_bridge_version"] = "LOCAL-LIFE-STAGE-BRIDGE-V1"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "eligible_place_count": len(eligible),
        "overlay_place_count": len(existing_after),
        "unmapped_eligible_place_ids": unmapped_after,
        "added_place_ids": added_place_ids,
        "added_records": added_records,
        "blocked": blocked,
    }
