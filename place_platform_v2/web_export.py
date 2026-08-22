from __future__ import annotations
import json, sqlite3
from pathlib import Path
import re

def _decode_categories(raw):
    value = json.loads(raw)
    if isinstance(value, dict):
        if value.get("__type__") == "tuple" and isinstance(value.get("items"), list):
            return [str(x) for x in value["items"]]
        raise ValueError("unsupported typed categories payload")
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, tuple):
        return [str(x) for x in value]
    raise ValueError("unsupported categories payload")



def _source_link_from_record_id(record_id):
    value = str(record_id or "")
    match = re.search(r"osm-(node|way|relation)-(\d+)", value)
    if not match:
        return None
    kind, object_id = match.groups()
    return f"https://www.openstreetmap.org/{kind}/{object_id}"

def _best_source_for_place(con, place_id):
    rows = con.execute(
        "SELECT source_name,source_record_id,source_url FROM place_evidence "
        "WHERE place_id=? ORDER BY observed_at DESC,evidence_id",
        (place_id,),
    ).fetchall()
    for row in rows:
        direct = row["source_url"]
        if direct:
            return {"source_name": row["source_name"] or "แหล่งข้อมูลสาธารณะ", "source_url": direct}
        derived = _source_link_from_record_id(row["source_record_id"])
        if derived:
            return {"source_name": "OpenStreetMap", "source_url": derived}
    return {"source_name": "แหล่งข้อมูลสาธารณะ", "source_url": None}

def export_prachinlife_json(database_path, output_path, province="ปราจีนบุรี"):
    db = Path(database_path).resolve()
    out = Path(output_path).resolve()
    con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT place_id,canonical_name,latitude,longitude,address_text,province,"
            "categories_json,phone,website,lifecycle FROM places "
            "WHERE province=? AND latitude IS NOT NULL AND longitude IS NOT NULL "
            "ORDER BY canonical_name COLLATE NOCASE, place_id",
            (province,),
        ).fetchall()
        places = []
        for r in rows:
            source = _best_source_for_place(con, r["place_id"])
            places.append({
                "id": r["place_id"],
                "name": r["canonical_name"],
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "address": r["address_text"],
                "province": r["province"],
                "categories": _decode_categories(r["categories_json"]),
                "phone": r["phone"],
                "website": r["website"],
                "lifecycle": r["lifecycle"],
                "source": "place_platform_v2",
                "source_name": source["source_name"],
                "source_url": source["source_url"],
            })
    finally:
        con.close()
    payload = {
        "schema_version": "prachinlife-v2-json-1",
        "province": province,
        "count": len(places),
        "places": places,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

