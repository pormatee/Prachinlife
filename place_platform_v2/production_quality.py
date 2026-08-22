from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

ACTION_FIELDS = ("map", "phone", "website", "additional_info")


def _present(v: Any) -> bool:
    return v not in (None, "", [], {}, ())


def _loc(p: dict[str, Any]) -> dict[str, Any]:
    return p.get("location") if isinstance(p.get("location"), dict) else {}


def _meta(p: dict[str, Any]) -> dict[str, Any]:
    return p.get("metadata") if isinstance(p.get("metadata"), dict) else {}


def _name(p: dict[str, Any]) -> Any:
    return p.get("name") or p.get("title")


def _coords(p: dict[str, Any]) -> bool:
    l = _loc(p)
    lat = p.get("latitude", l.get("latitude")); lon = p.get("longitude", l.get("longitude"))
    return _present(lat) and _present(lon)


def _phone(p: dict[str, Any]) -> Any:
    m = _meta(p); c = m.get("contact") if isinstance(m.get("contact"), dict) else {}
    return p.get("phone") or m.get("phone") or c.get("phone")


def _website(p: dict[str, Any]) -> Any:
    m = _meta(p); c = m.get("contact") if isinstance(m.get("contact"), dict) else {}
    return p.get("website") or m.get("website") or c.get("website")


def _details(p: dict[str, Any]) -> bool:
    # Mirrors the public-card concept of useful additional information:
    # OSM is provenance/map support, not a user-facing additional-info link.
    if _present(p.get("prachinlife_page_url")):
        return True
    links = p.get("external_links")
    if not isinstance(links, list):
        return False
    for link in links:
        if not isinstance(link, dict) or not _present(link.get("url")):
            continue
        kind = str(link.get("type") or "").lower()
        url = str(link.get("url") or "").lower()
        if kind != "osm" and "openstreetmap.org" not in url:
            return True
    return False


def _source(p: dict[str, Any]) -> bool:
    s = p.get("source")
    if isinstance(s, dict):
        return _present(s.get("name")) and _present(s.get("url"))
    return _present(s or p.get("source_name")) and _present(p.get("source_url"))


def _category(p: dict[str, Any]) -> bool:
    return _present(p.get("categories") or p.get("category") or p.get("content_type") or p.get("food_types"))


def _province(p: dict[str, Any]) -> bool:
    return _present(p.get("province") or _loc(p).get("province"))


def _visible(p: dict[str, Any], dataset: str) -> bool:
    if dataset == "prachinlife_index.json":
        # Public PrachinLife place cards in this compatibility index are
        # represented by content_type="eat".  content_type="deal" rows are
        # promotions, not canonical places, and must stay outside place-quality
        # scoring.
        return p.get("content_type") == "eat"
    m = _meta(p)
    if "show_in_primary_directory" in m:
        return bool(m.get("show_in_primary_directory"))
    return True


def score_place(p: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "name": bool(_name(p)), "coordinates": _coords(p), "province": _province(p),
        "category": _category(p), "source": _source(p), "phone": bool(_phone(p)),
        "website": bool(_website(p)), "additional_info": _details(p),
    }
    weights = {"name":15,"coordinates":20,"province":10,"category":10,"source":15,"phone":10,"website":10,"additional_info":10}
    score = sum(weights[k] for k, ok in checks.items() if ok)
    if score >= 80: tier = "high"
    elif score >= 60: tier = "medium"
    else: tier = "low"
    actions = {"map": checks["coordinates"], "phone": checks["phone"], "website": checks["website"], "additional_info": checks["additional_info"]}
    return {"score": score, "tier": tier, "checks": checks, "actions": actions}


def audit_production(datasets: dict[str, Iterable[dict[str, Any]]]) -> dict[str, Any]:
    tier_counts: Counter[str] = Counter(); action_counts: Counter[str] = Counter(); missing: Counter[str] = Counter()
    by_dataset: dict[str, Any] = {}; priorities: list[dict[str, Any]] = []
    total = 0
    for dataset, places in datasets.items():
        rows = [p for p in places if isinstance(p, dict) and _visible(p, dataset)]
        dt = Counter()
        for p in rows:
            q = score_place(p); total += 1; tier_counts[q["tier"]] += 1; dt[q["tier"]] += 1
            for k, ok in q["actions"].items():
                if ok: action_counts[k] += 1
            for k, ok in q["checks"].items():
                if not ok: missing[k] += 1
            missing_checks = [k for k, v in q["checks"].items() if not v]
            missing_actions = [k for k, v in q["actions"].items() if not v]
            # A production place can still be medium/high quality while lacking
            # the contact/detail actions that most improve user value. Keep
            # those places in the deterministic enrichment queue instead of
            # limiting priorities to low-tier rows (which can legitimately be 0).
            if missing_actions:
                priorities.append({
                    "dataset": dataset,
                    "id": p.get("id"),
                    "name": _name(p),
                    "score": q["score"],
                    "tier": q["tier"],
                    "missing": missing_checks,
                    "missing_actions": missing_actions,
                })
        by_dataset[dataset] = {"visible_places": len(rows), "quality": dict(dt)}
    priorities.sort(key=lambda x: (x["score"], -len(x["missing_actions"]), str(x["name"] or ""), str(x.get("id") or "")))
    return {"mode":"read_only_production_quality_audit", "visible_place_count": total,
            "quality_tiers": {k:tier_counts.get(k,0) for k in ("high","medium","low")},
            "action_ready": {k:action_counts.get(k,0) for k in ACTION_FIELDS},
            "missing_fields": dict(missing), "datasets": by_dataset,
            "top_enrichment_priorities": priorities[:50]}
