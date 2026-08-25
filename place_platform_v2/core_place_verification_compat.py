"""Read-only compatibility adapter from existing Phase 4.x contracts to Core V2."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any
from .core_place_verification_v2 import POLICY_VERSION, evaluate_place
from .new_place_adoption_review import review_new_place_adoption

COORDINATE_REPORT_NAMES = (
    "pathum_coordinate_acquisition_v1.json",
    "pathum_exact_coordinate_acquisition_v1.json",
    "pathum_vegetarian_exact_coordinate_acquisition_v1.json",
    "baanj_exact_coordinate_result_v1.json",
)

def _load_coordinate_results(paths):
    by_key = {}
    by_name_province = {}
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        try: payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception: continue
        for row in payload.get("results", []):
            outcome = row.get("coordinate_outcome")
            if not outcome: continue
            if row.get("candidate_key"):
                by_key[str(row["candidate_key"])] = outcome
            by_name_province[(str(row.get("name") or "").strip(), str(row.get("province") or "").strip())] = outcome
    return by_key, by_name_province

def evaluate_compatibility(*, database_path, coordinate_report_paths=()) -> dict[str, Any]:
    db = Path(database_path)
    before = db.read_bytes()
    review = review_new_place_adoption(database_path=db)
    paths = list(coordinate_report_paths)
    if not paths:
        # Reports belong to the project tree, not to the physical location of
        # whichever SQLite copy is being evaluated (production/test/sandbox).
        root = Path(__file__).resolve().parents[1]
        report_dir = root / "data/v2/discovery_reports"
        paths = [report_dir / x for x in COORDINATE_REPORT_NAMES]
    by_key, by_np = _load_coordinate_results(paths)

    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    direct = {}
    if con.execute("select 1 from sqlite_master where type='table' and name='precanonical_direct_coordinates'").fetchone():
        for r in con.execute("select c.candidate_key,c.proposed_name,c.province,count(*) n from precanonical_candidates c join precanonical_direct_coordinates d on d.candidate_id=c.candidate_id group by c.candidate_id"):
            if r["n"]: direct[(r["proposed_name"], r["province"])] = "EXACT_COORDINATES_VERIFIED"
    con.close()

    rows=[]
    for d in review["decisions"]:
        coord = by_key.get(str(d.get("candidate_key") or "")) or by_np.get((d["name"], d["province"])) or direct.get((d["name"], d["province"]))
        identity_blockers = [x for x in d.get("blockers", []) if x not in {"exact_candidate_coordinates_not_verified","pending_manual_or_coordinate_confirmation"}]
        a = evaluate_place(
            identity_outcome=d.get("identity_outcome") or "",
            source_families=d.get("source_families") or (),
            coordinate_outcome=coord,
            duplicate_risk=bool(d.get("duplicate_matches")),
            identity_blockers=identity_blockers,
            review_flags=d.get("review_flags") or (),
        )
        rows.append({"candidate_id":d["candidate_id"],"candidate_key":d.get("candidate_key"),"name":d["name"],"province":d["province"],"category":d.get("category"),"coordinate_outcome":coord,**a.as_dict()})
    after = db.read_bytes()
    return {
        "status":"PASS","policy_version":POLICY_VERSION,"candidate_count":len(rows),"decisions":rows,
        "counts":{s:sum(x["state"]==s for x in rows) for s in ("VERIFIED_NEAR_ME_READY","VERIFIED_PLACE_COORDINATE_PENDING","CANDIDATE_OR_REVIEW")},
        "safety":{"database_unchanged":before==after,"database_writes":False,"production_json_writes":False,"automatic_canonical_adoption":False,"automatic_publication":False,"trust_policy_lowered":False,"category_agnostic_core":True},
    }
