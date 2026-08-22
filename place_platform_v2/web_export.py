from __future__ import annotations
import json, sqlite3
from pathlib import Path
import re
from urllib.parse import urlparse, urlunparse

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


def _decode_evidence_value(raw):
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return raw


def _detail_evidence_for_place(con, place_id):
    wanted = {"district", "subdistrict", "area", "opening_hours", "real_image", "description", "prachinlife_page_url"}
    rows = con.execute(
        "SELECT field_name,value_json,status,observed_at FROM place_evidence "
        "WHERE place_id=? ORDER BY observed_at DESC,evidence_id",
        (place_id,),
    ).fetchall()
    result = {}
    for row in rows:
        field = str(row["field_name"] or "")
        if field not in wanted or field in result:
            continue
        # Public detail enrichment follows the same trust boundary as public
        # navigation: only supported or verified evidence may be published.
        if str(row["status"] or "").casefold() not in {"supported", "verified"}:
            continue
        value = _decode_evidence_value(row["value_json"])
        if value not in (None, "", [], {}):
            result[field] = value
    return result


def _public_http_url(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw):
        pass
    elif "://" not in raw and not raw.startswith(("/", "#")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        return None
    return raw




def _canonical_url_key(value):
    raw = _public_http_url(value)
    if not raw:
        return None
    parsed = urlparse(raw)
    hostname = (parsed.hostname or "").casefold()
    port = parsed.port
    if (parsed.scheme.casefold() == "https" and port == 443) or (parsed.scheme.casefold() == "http" and port == 80):
        port = None
    netloc = hostname
    if port:
        netloc = f"{hostname}:{port}"
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.casefold(), netloc, path, parsed.params, parsed.query, ""))

def _source_kind(name, url):
    value = str(url or "").casefold()
    label = str(name or "").casefold()
    if "openstreetmap.org" in value or label == "openstreetmap":
        return "osm"
    if "maps.app.goo.gl" in value or "google.com/maps" in value:
        return "google_maps"
    if "wongnai.com" in value:
        return "wongnai"
    if "facebook.com" in value or "fb.com" in value:
        return "facebook"
    return "web"


def _links_for_place(con, place_id, website=None):
    rows = con.execute(
        "SELECT source_name,source_record_id,source_url,status FROM place_evidence "
        "WHERE place_id=? ORDER BY observed_at DESC,evidence_id",
        (place_id,),
    ).fetchall()
    links = []
    seen = set()
    for row in rows:
        # Public navigation must not expose candidate/rejected/stale evidence links.
        if str(row["status"] or "").casefold() not in {"supported", "verified"}:
            continue
        direct = str(row["source_url"] or "").strip()
        derived = _source_link_from_record_id(row["source_record_id"])
        url = _public_http_url(direct or derived)
        key = _canonical_url_key(url)
        if not url or not key or key in seen:
            continue
        seen.add(key)
        kind = _source_kind(row["source_name"], url)
        links.append({
            "type": kind,
            "label": row["source_name"] or ("OpenStreetMap" if kind == "osm" else "ข้อมูลเพิ่มเติม"),
            "url": url,
        })
    if website:
        website = _public_http_url(website)
        website_key = _canonical_url_key(website)
        if website and website_key and website_key not in seen:
            seen.add(website_key)
            links.insert(0, {"type": "official_website", "label": "เว็บไซต์", "url": website})
    return links


def _best_source_for_place(con, place_id):
    links = _links_for_place(con, place_id)
    for link in links:
        if link["type"] != "osm":
            return {"source_name": link["label"], "source_url": link["url"]}
    for link in links:
        if link["type"] == "osm":
            return {"source_name": "OpenStreetMap", "source_url": link["url"]}
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
            external_links = _links_for_place(con, r["place_id"], r["website"])
            details = _detail_evidence_for_place(con, r["place_id"])
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
                "external_links": external_links,
                "district": details.get("district"),
                "subdistrict": details.get("subdistrict"),
                "area": details.get("area"),
                "opening_hours": details.get("opening_hours"),
                "real_image": details.get("real_image"),
                "image_url": details.get("real_image"),
                "description": details.get("description"),
                "prachinlife_page_url": details.get("prachinlife_page_url"),
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

