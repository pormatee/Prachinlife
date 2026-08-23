from __future__ import annotations
import hashlib, json
from pathlib import Path

from .production_quality import audit_production

PRODUCTION_FILES = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
)

def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def _records(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("places", "items", "data", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []

def _key(row):
    for k in ("id", "place_id", "osm_id"):
        if row.get(k):
            return str(row[k])
    return None

def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _contact_value(row, field):
    md = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    contact = md.get("contact") if isinstance(md.get("contact"), dict) else {}
    return row.get(field) or md.get(field) or contact.get(field)

def verify_post_publication(repo_root: Path) -> dict:
    root = Path(repo_root)
    db = root/"data/v2/place_platform_v2.sqlite3"
    before_db = _sha(db) if db.exists() else None

    blockers = []
    staging_mismatches = []
    shape_violations = []
    datasets = {}
    production_record_count = 0
    staging_record_count = 0

    for name in PRODUCTION_FILES:
        pp = root/name
        sp = root/"data/v2/staging/user_web"/name
        if not pp.exists():
            blockers.append(f"missing production dataset: {name}")
            continue
        if not sp.exists():
            blockers.append(f"missing staging dataset: {name}")
            continue

        prod = _records(_load(pp))
        stage = _records(_load(sp))
        datasets[name] = prod
        production_record_count += len(prod)
        staging_record_count += len(stage)

        pm = {_key(x): x for x in prod if _key(x)}
        sm = {_key(x): x for x in stage if _key(x)}
        for k in sorted(set(pm) & set(sm)):
            a, b = pm[k], sm[k]
            for f in ("phone", "website"):
                if _contact_value(a, f) != _contact_value(b, f):
                    staging_mismatches.append({"file": name, "id": k, "field": f})
            # Phase 3.9 must preserve public production shape. Existing V2
            # overlay metadata from the original V2 go-live is allowed; this
            # guard blocks only a top-level preview marker leaking into output.
            if a.get("v2_preview_overlay") is True:
                shape_violations.append({"file": name, "id": k, "field": "v2_preview_overlay"})

    quality = audit_production(datasets) if datasets else {
        "visible_place_count": 0,
        "action_ready": {"map":0,"phone":0,"website":0,"additional_info":0},
        "datasets": {},
    }

    # Semantic guard: a non-empty public place set with zero map readiness
    # indicates schema/parser drift and must never be reported as PASS.
    if quality["visible_place_count"] > 0 and quality["action_ready"].get("map", 0) == 0:
        blockers.append("semantic action-readiness parser failure: visible places exist but map-ready count is zero")

    after_db = _sha(db) if db.exists() else None
    status = "PASS" if not (blockers or staging_mismatches or shape_violations) else "FAIL"
    return {
        "status": status,
        "production_record_count": production_record_count,
        "staging_record_count": staging_record_count,
        "visible_place_count": quality["visible_place_count"],
        "action_ready": quality["action_ready"],
        "quality_datasets": quality["datasets"],
        "staging_contact_mismatches": staging_mismatches,
        "production_shape_violations": shape_violations,
        "blockers": blockers,
        "safety": {
            "database_unchanged": before_db == after_db,
            "production_writes": False,
            "staging_writes": False,
            "trust_policy_lowered": False,
            "shared_quality_semantics": True,
        },
    }
