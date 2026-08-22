from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

FILES = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _decode_categories(value: str | None):
    if not value:
        return []
    obj = json.loads(value)
    if isinstance(obj, dict) and obj.get("__type__") == "tuple":
        return list(obj.get("items") or [])
    return list(obj) if isinstance(obj, (list, tuple)) else []


def _overlay_rows(rows):
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        md = r.get("metadata")
        if isinstance(md, dict) and md.get("v2_preview_overlay") is True:
            out.append(r)
    return out


def _row_id(r):
    return r.get("id") if isinstance(r, dict) else None


def _core_tuple(r):
    loc = r.get("location") or {}
    return (
        r.get("title") or r.get("name"),
        loc.get("province") or r.get("province"),
        loc.get("latitude") if "latitude" in loc else r.get("latitude"),
        loc.get("longitude") if "longitude" in loc else r.get("longitude"),
    )


def audit_fresh_comparative_release(repo_root: str | Path, database_path: str | Path, staging_root: str | Path):
    root = Path(repo_root)
    staging = Path(staging_root)
    db = Path(database_path)

    checks = []
    blockers = []

    def check(name, ok, detail):
        ok = bool(ok)
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            blockers.append(f"{name}: {detail}")

    manifest = _load(staging / "manifest.json")
    eligible = int(manifest.get("eligible_place_count", 0) or 0)
    overlays = int(manifest.get("overlay_place_count", 0) or 0)
    check("manifest_overlay_mode", manifest.get("preview_mode") == "v2_overlay_with_v1_fallback", manifest.get("preview_mode"))
    check("manifest_eligible_overlay_equal", eligible > 0 and eligible == overlays, f"eligible={eligible}, overlay={overlays}")
    check("manifest_unmapped_zero", int(manifest.get("unmapped_eligible_place_count", -1)) == 0, f"unmapped={manifest.get('unmapped_eligible_place_count')}")
    check("manifest_production_unchanged", manifest.get("production_unchanged") is True, "production_unchanged must be true")
    check("manifest_public_switch_disabled", manifest.get("public_user_web_switched") is False, "public_user_web_switched must be false")

    # Load canonical rows for overlay verification.
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        canonical = {
            r["place_id"]: r
            for r in con.execute("SELECT place_id, canonical_name, latitude, longitude, province, categories_json FROM places")
        }
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        con.close()
    check("database_integrity", integrity == "ok", f"integrity={integrity}")
    check("database_foreign_keys", len(fk) == 0, f"foreign_key_errors={len(fk)}")

    total_overlay_records = 0
    unique_overlay_place_ids = set()
    file_report = {}
    fallback_mutations = []
    overlay_core_mismatches = []

    for fn in FILES:
        prod_rows = _load(root / fn)
        staged_rows = _load(staging / fn)
        check(f"{fn}:record_count_preserved", len(prod_rows) == len(staged_rows), f"v1={len(prod_rows)}, staged={len(staged_rows)}")

        prod_by_id = {_row_id(r): r for r in prod_rows if _row_id(r) is not None}
        staged_by_id = {_row_id(r): r for r in staged_rows if _row_id(r) is not None}
        check(f"{fn}:id_set_preserved", set(prod_by_id) == set(staged_by_id), f"v1_ids={len(prod_by_id)}, staged_ids={len(staged_by_id)}")

        ov = _overlay_rows(staged_rows)
        total_overlay_records += len(ov)
        for r in ov:
            md = r["metadata"]
            pid = md.get("v2_place_id")
            unique_overlay_place_ids.add(pid)
            c = canonical.get(pid)
            if c is None:
                overlay_core_mismatches.append({"file": fn, "id": r.get("id"), "reason": "missing canonical"})
                continue
            title, province, lat, lon = _core_tuple(r)
            ok = (
                title == c["canonical_name"]
                and province == c["province"]
                and lat is not None and lon is not None
                and math.isclose(float(lat), float(c["latitude"]), abs_tol=1e-7)
                and math.isclose(float(lon), float(c["longitude"]), abs_tol=1e-7)
                and md.get("v2_core_identity_source") == "canonical_v2"
            )
            if not ok:
                overlay_core_mismatches.append({"file": fn, "id": r.get("id"), "place_id": pid})

        # Non-overlay fallback rows must be byte-equivalent at object level to V1.
        for rid, sr in staged_by_id.items():
            md = sr.get("metadata") if isinstance(sr, dict) else None
            is_overlay = isinstance(md, dict) and md.get("v2_preview_overlay") is True
            if not is_overlay and prod_by_id.get(rid) != sr:
                fallback_mutations.append({"file": fn, "id": rid})

        file_report[fn] = {
            "v1_count": len(prod_rows),
            "staged_count": len(staged_rows),
            "overlay_records": len(ov),
            "fallback_records": len(staged_rows) - len(ov),
        }

    check("overlay_unique_place_count", len(unique_overlay_place_ids) == overlays == eligible, f"unique_overlay_places={len(unique_overlay_place_ids)}, manifest={overlays}")
    check("overlay_core_identity_matches_v2", not overlay_core_mismatches, f"mismatches={len(overlay_core_mismatches)}")
    check("fallback_rows_unchanged", not fallback_mutations, f"mutations={len(fallback_mutations)}")

    # Browser contracts required by current user web.
    app = (root / "app.js").read_text(encoding="utf-8")
    check("preview_opt_in_query", 'get("v2preview") === "1"' in app, "?v2preview=1 opt-in required")
    check("preview_separate_staging_root", 'V2_STAGED_ROOT = "data/v2/staging/user_web"' in app, "separate staging root required")
    check("search_contract_present", "function bindSearchEvents" in app and "function performSearch" in app and "searchInput" in app, "search binding + execution markers")
    check("near_me_distance_contract_present", "function calculatePlaceDistance" in app and "activateNearMe" in app, "distance + Near Me functions")
    check("vegetarian_near_me_contract_present", "activateVegetarianNearMe" in app, "vegetarian Near Me")
    check("go_near_me_contract_present", "activateGoNearMe" in app, "go Near Me")
    check("service_near_me_contract_present", "activateServiceNearMe" in app, "service Near Me")

    # Category compatibility: every overlay keeps a content/category discriminator from V1.
    bad_category_shape = []
    for fn in FILES:
        for r in _overlay_rows(_load(staging / fn)):
            if fn == "prachinlife_index.json" and not r.get("content_type"):
                bad_category_shape.append((fn, r.get("id")))
            if fn in ("go_index.json", "service_index.json") and not (r.get("content_type") or r.get("category")):
                bad_category_shape.append((fn, r.get("id")))
    check("category_shape_preserved", not bad_category_shape, f"bad_rows={len(bad_category_shape)}")

    # Rollback is query-param reversible: default URLs remain V1 files.
    default_v1 = all([
        ': "prachinlife_index.json"' in app,
        ': "vegetarian_index.json"' in app,
        ': "go_index.json"' in app,
        ': "service_index.json"' in app,
    ])
    check("rollback_default_v1_paths_present", default_v1, "remove ?v2preview=1 to return to V1 data paths")

    passed = not blockers
    return {
        "policy_version": "fresh-comparative-release-gate-v1",
        "status": "PASS" if passed else "FAIL",
        "supersedes": "phase2h_comparative_beta_ready.json",
        "supersede_reason": "current staged overlay preserves full V1 coverage while overlaying eligible canonical V2 core identity",
        "checks_passed": sum(1 for x in checks if x["ok"]),
        "checks_total": len(checks),
        "eligible_place_count": eligible,
        "overlay_place_count": overlays,
        "total_overlay_records": total_overlay_records,
        "files": file_report,
        "blockers": blockers,
        "overlay_core_mismatches": overlay_core_mismatches,
        "fallback_mutations": fallback_mutations,
        "rollback_verified": default_v1,
        "production_switch": "DISABLED",
        "public_user_web_switched": False,
        "checks": checks,
    }
