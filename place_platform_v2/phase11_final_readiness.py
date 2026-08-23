from __future__ import annotations
import json, sqlite3
from pathlib import Path

FIELDS=("address","area","district","subdistrict","opening_hours","phone","website","description","real_image")
MIN_COVERAGE={"address":2,"area":1,"district":2,"subdistrict":2,"opening_hours":3,"phone":5,"website":27,"description":1,"real_image":0}
PUBLIC_STATUSES={"supported","verified"}


def _present(v):
    return v not in (None,"",[],{})


def coverage(export_path):
    payload=json.loads(Path(export_path).read_text(encoding="utf-8"))
    places=payload.get("places") or []
    return {f:sum(_present(p.get(f)) for p in places) for f in FIELDS}, payload


def evidence_profile(database_path, place_ids):
    con=sqlite3.connect(database_path); con.row_factory=sqlite3.Row
    try:
        q="SELECT field_name,status,source_name,source_url,source_record_id,value_json FROM place_evidence WHERE place_id=?"
        by_field={f:{"supported":0,"candidate":0,"rejected":0,"stale":0,"other":0,"missing_provenance":0} for f in FIELDS}
        for pid in place_ids:
            for r in con.execute(q,(pid,)).fetchall():
                f=str(r["field_name"] or "")
                if f not in by_field: continue
                s=str(r["status"] or "").casefold()
                bucket=s if s in {"supported","candidate","rejected","stale"} else "other"
                by_field[f][bucket]+=1
                if s in PUBLIC_STATUSES and not (str(r["source_name"] or "").strip() and (str(r["source_url"] or "").strip() or str(r["source_record_id"] or "").strip())):
                    by_field[f]["missing_provenance"]+=1
        return by_field
    finally:
        con.close()


def final_readiness(database_path, export_path):
    cov,payload=coverage(export_path)
    places=payload.get("places") or []
    if payload.get("count") != 220 or len(places) != 220:
        raise AssertionError(f"expected 220 published places, got count={payload.get('count')} len={len(places)}")
    for f,minv in MIN_COVERAGE.items():
        if cov[f] < minv:
            raise AssertionError(f"coverage regression {f}: {cov[f]} < {minv}")
    profile=evidence_profile(database_path,[p.get("id") for p in places])
    for f,stats in profile.items():
        if stats["missing_provenance"]:
            raise AssertionError(f"supported evidence missing provenance for {f}: {stats['missing_provenance']}")
    # Any exported evidence-backed detail must carry supported provenance.
    evidence_only={"area","district","subdistrict","opening_hours","description","real_image"}
    for p in places:
        prov=p.get("detail_provenance") or {}
        for f in evidence_only:
            if _present(p.get(f)):
                meta=prov.get(f) or {}
                if str(meta.get("status") or "").casefold() not in PUBLIC_STATUSES:
                    raise AssertionError(f"public {f} lacks supported provenance: {p.get('id')}")
                if not str(meta.get("source_name") or "").strip():
                    raise AssertionError(f"public {f} lacks source_name: {p.get('id')}")
    # Phase 11 deliberately does not manufacture real images. Zero is an acceptable final state.
    if cov["real_image"] == 0:
        for p in places:
            if _present(p.get("image_url")):
                raise AssertionError(f"image_url exists without real_image: {p.get('id')}")
    return {"places":len(places),"coverage":cov,"evidence_profile":profile,"real_image_policy":"verified_real_image_only; master fallback otherwise"}
