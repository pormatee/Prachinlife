from __future__ import annotations
import hashlib, json, sqlite3
from collections import Counter, defaultdict
from pathlib import Path

POLICY_VERSION = "4.1-discovery-coverage-audit-v1"
CORE_CATEGORIES = ("eat","vegetarian","go","service")
ALIASES = {
    "eat":"eat","food":"eat","restaurant":"eat","cafe":"eat",
    "vegetarian":"vegetarian","vegan":"vegetarian","jay":"vegetarian","vegetarian_candidate":"vegetarian",
    "go":"go","travel":"go","attraction":"go","temple":"go","park":"go","nature":"go",
    "service":"service","services":"service","fuel":"service","laundry":"service",
    "car_repair":"service","clinic":"service","pharmacy":"service",
}

def _sha(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024), b""): h.update(c)
    return h.hexdigest()

def _cats(raw):
    try: vals=json.loads(raw or "[]")
    except Exception: vals=[]
    if isinstance(vals,dict) and vals.get("__type__") in {"tuple","list"}:
        vals=vals.get("items") or []
    if isinstance(vals,str): vals=[vals]
    out=set()
    for v in vals if isinstance(vals,(list,tuple)) else []:
        s=str(v).strip().casefold()
        if s in ALIASES: out.add(ALIASES[s])
    return sorted(out)

def audit_discovery_coverage(database_path: str|Path, priority_limit: int=50, focus_province: str|None=None) -> dict:
    db=Path(database_path)
    before=_sha(db)
    con=sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)
    con.row_factory=sqlite3.Row
    try:
        rows=list(con.execute("SELECT place_id,canonical_name,province,categories_json,latitude,longitude,phone,website,lifecycle FROM places"))
    finally:
        con.close()

    provinces=defaultdict(lambda: {"total":0,"categories":Counter(),"missing_contact":0,"missing_coordinates":0})
    category_totals=Counter()
    unmapped=0
    lifecycle_counts=Counter()
    for r in rows:
        lifecycle_counts[str(r["lifecycle"] or "unknown")] += 1
        prov=(r["province"] or "").strip() or "<unknown>"
        cats=_cats(r["categories_json"])
        provinces[prov]["total"] += 1
        if not cats: unmapped += 1
        for c in cats:
            category_totals[c]+=1; provinces[prov]["categories"][c]+=1
        if not r["phone"] and not r["website"]: provinces[prov]["missing_contact"]+=1
        if r["latitude"] is None or r["longitude"] is None: provinces[prov]["missing_coordinates"]+=1

    # Coverage priority is intentionally relative, not a claim about real-world completeness.
    # For each province already represented in the DB, identify missing/sparse core categories.
    queue=[]
    for prov,d in provinces.items():
        if prov=="<unknown>": continue
        counts={c:int(d["categories"].get(c,0)) for c in CORE_CATEGORIES}
        maxc=max(counts.values()) if counts else 0
        for c,n in counts.items():
            if n==0:
                gap="missing"; score=100
            elif maxc and n <= max(2, int(maxc*0.15)):
                gap="sparse"; score=70
            else:
                continue
            queue.append({
                "province":prov,"category":c,"gap_kind":gap,
                "known_place_count":n,"province_place_count":d["total"],
                "priority_score":score + min(20,d["total"]//10) + (30 if focus_province and prov==focus_province else 0),
                "next_step":"discover_new_places",
            })
    queue.sort(key=lambda x:(-x["priority_score"],-x["province_place_count"],x["province"],x["category"]))
    queue=queue[:priority_limit]

    provout={}
    for p,d in sorted(provinces.items()):
        provout[p]={
            "place_count":d["total"],
            "categories":{c:int(d["categories"].get(c,0)) for c in CORE_CATEGORIES},
            "missing_contact_count":d["missing_contact"],
            "missing_coordinates_count":d["missing_coordinates"],
        }
    after=_sha(db)
    return {
        "status":"PASS",
        "policy_version":POLICY_VERSION,
        "canonical_place_count":len(rows),
        "lifecycle_counts":dict(sorted(lifecycle_counts.items())),
        "province_count":len([p for p in provinces if p!="<unknown>"]),
        "category_totals":{c:int(category_totals.get(c,0)) for c in CORE_CATEGORIES},
        "unmapped_category_place_count":unmapped,
        "province_coverage":provout,
        "coverage_priority_queue":queue,
        "coverage_priority_count":len(queue),
        "focus_province_summary": provout.get(focus_province) if focus_province else None,
        "next_recommended_work": (
            {"mode":"coverage","province":queue[0]["province"],"category":queue[0]["category"],
             "reason":queue[0]["gap_kind"] + "_relative_coverage"}
            if queue else None
        ),
        "interpretation":{
            "coverage_is_relative_to_current_database":True,
            "not_a_real_world_completeness_claim":True,
            "queue_purpose":"Phase 4.2 discovery targeting",
            "focus_province":focus_province,
        },
        "safety":{
            "database_unchanged":before==after,
            "database_writes":False,
            "production_json_writes":False,
            "trust_policy_lowered":False,
            "province_agnostic":True,
        },
    }
