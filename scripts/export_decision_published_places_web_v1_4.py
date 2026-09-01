#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path

def unwrap_typed(value):
    if isinstance(value, dict):
        kind=value.get("__kind__")
        if kind=="dataclass" and isinstance(value.get("fields"), dict):
            return {k: unwrap_typed(v) for k,v in value["fields"].items()}
        if kind=="tuple" and isinstance(value.get("items"), list):
            return [unwrap_typed(v) for v in value["items"]]
        if kind=="enum" and "value" in value:
            return unwrap_typed(value["value"])
        if kind=="datetime" and "value" in value:
            return unwrap_typed(value["value"])
        return {k: unwrap_typed(v) for k,v in value.items()
                if k not in ("__kind__","__type__")}
    if isinstance(value, list):
        return [unwrap_typed(v) for v in value]
    return value

def text(v):
    return "" if v is None else str(v)

def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None

def cats(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str):
        s=v.strip()
        if not s:
            return []
        try:
            parsed=json.loads(s)
            if isinstance(parsed,list):
                return [str(x) for x in parsed]
        except Exception:
            pass
        return [s]
    return []

def normalize(row):
    payload=unwrap_typed(json.loads(row["payload_json"]))
    if not isinstance(payload, dict):
        raise ValueError(f"published place {row['place_id']} payload is not object")

    place_id=str(payload.get("place_id") or row["place_id"])
    if place_id != str(row["place_id"]):
        raise ValueError(f"place_id mismatch row={row['place_id']} payload={place_id}")

    location=payload.get("location") if isinstance(payload.get("location"),dict) else {}
    name=text(payload.get("name")).strip()
    if not name:
        raise ValueError(f"published place {place_id} has no usable name after typed payload decode")

    latitude=num(location.get("latitude"))
    longitude=num(location.get("longitude"))
    if latitude is None:
        latitude=num(row["latitude"])
    if longitude is None:
        longitude=num(row["longitude"])

    if latitude is None or longitude is None:
        latitude = None
        longitude = None

    categories=cats(payload.get("categories"))
    if not categories:
        categories=cats(row["categories_json"])

    return {
        "id": place_id,
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "address": text(payload.get("address_text")),
        "province": text(payload.get("province") or row["province"]),
        "categories": categories,
        "phone": text(payload.get("phone")),
        "website": text(payload.get("website")),
        "lifecycle": text(payload.get("lifecycle") or "published"),
        "source": "decision_published_places_v1",
        "publication_policy_version": text(payload.get("publication_policy_version")),
        "published_at": text(payload.get("published_at")),
        "metadata": {
            "v2_place_id": place_id,
            "published_projection": "decision_published_places_v1",
            "projection_schema_version": text(row["projection_schema_version"]),
        },
    }

def export_projection(database_path: Path, output_path: Path):
    db=database_path.resolve()
    con=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    con.row_factory=sqlite3.Row
    try:
        rows=con.execute(
            "select place_id,province,categories_json,latitude,longitude,"
            "payload_json,projection_schema_version "
            "from decision_published_places_v1 order by place_id"
        ).fetchall()
    finally:
        con.close()

    places=[normalize(r) for r in rows]
    ids=[p["id"] for p in places]
    if len(ids)!=len(set(ids)):
        raise RuntimeError("duplicate published place ids")

    payload={
        "schema_version":"prachinlife-published-projection-web-1",
        "authority":"decision_published_places_v1",
        "count":len(places),
        "places":places,
    }
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    return payload

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--database",default="data/v2/decision_published_places_v1.sqlite3")
    ap.add_argument("--output",default="data/v2/exports/decision_published_places_v1.json")
    a=ap.parse_args()
    p=export_projection(Path(a.database),Path(a.output))
    print("EXPORTED_COUNT=",p["count"])
    print("AUTHORITY=",p["authority"])

if __name__=="__main__":
    main()
