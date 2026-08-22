from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from .contracts import GeoPoint
from .models import CanonicalPlace, PlaceIdentity, PlaceLifecycle

def load_canonical_places_readonly(database_path):
    path = Path(database_path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    con = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT place_id,canonical_name,latitude,longitude,address_text,"
            "province,categories_json,phone,website,lifecycle,created_at,updated_at "
            "FROM places ORDER BY place_id"
        ).fetchall()
    finally:
        con.close()
    result = []
    for row in rows:
        location = None
        if row["latitude"] is not None and row["longitude"] is not None:
            location = GeoPoint(float(row["latitude"]), float(row["longitude"]))
        categories = tuple(str(x) for x in json.loads(row["categories_json"]))
        result.append(CanonicalPlace(
            identity=PlaceIdentity(row["place_id"]),
            canonical_name=row["canonical_name"],
            location=location,
            address_text=row["address_text"],
            province=row["province"],
            categories=categories,
            phone=row["phone"],
            website=row["website"],
            lifecycle=PlaceLifecycle(row["lifecycle"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        ))
    return tuple(result)
