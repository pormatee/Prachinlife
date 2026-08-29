from __future__ import annotations
from typing import Any, Mapping

def _first_number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except Exception:
                pass
    return None

def normalize_decision_context_v1(context: Mapping[str, Any] | None) -> dict[str, Any]:
    src = dict(context or {})
    loc = src.get("current_location")
    lat = None
    lon = None

    if isinstance(loc, (tuple, list)) and len(loc) >= 2:
        lat = _first_number(loc[0])
        lon = _first_number(loc[1])
    elif isinstance(loc, Mapping):
        lat = _first_number(loc.get("latitude"), loc.get("lat"))
        lon = _first_number(loc.get("longitude"), loc.get("lon"), loc.get("lng"))

    lat = _first_number(lat, src.get("latitude"), src.get("lat"), src.get("current_latitude"), src.get("user_latitude"))
    lon = _first_number(lon, src.get("longitude"), src.get("lon"), src.get("lng"), src.get("current_longitude"), src.get("user_longitude"))

    if lat is not None and lon is not None:
        src["latitude"] = lat
        src["longitude"] = lon
        src["lat"] = lat
        src["lon"] = lon
        src["lng"] = lon
        src["current_latitude"] = lat
        src["current_longitude"] = lon
        src["user_latitude"] = lat
        src["user_longitude"] = lon
        if not (isinstance(loc, (tuple, list)) and len(loc) >= 2):
            src["current_location"] = (lat, lon)
    return src
