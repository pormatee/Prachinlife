from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

PUBLIC_FILES = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
)

DETAIL_FIELDS = (
    "address",
    "area",
    "district",
    "subdistrict",
    "opening_hours",
    "phone",
    "website",
    "description",
    "real_image",
)

def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _rows(path: Path):
    value = _json(path)
    if not isinstance(value, list):
        raise ValueError(f"{path} must contain a JSON array")
    return value

def detail_coverage(export_path: str | Path):
    data = _json(Path(export_path))
    places = data.get("places")
    if not isinstance(places, list):
        raise ValueError("V2 export missing places[]")
    out = {"places": len(places)}
    for field in DETAIL_FIELDS:
        out[field] = sum(
            1 for p in places
            if p.get(field) not in (None, "", [], {})
        )
    return out

def database_counts(db_path: str | Path):
    con = sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True)
    try:
        tables = {
            row[0] for row in con.execute(
                "select name from sqlite_master where type='table'"
            )
        }
        out = {}
        for name in ("places", "place_evidence", "field_provenance", "review_queue"):
            if name in tables:
                out[name] = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        return out
    finally:
        con.close()

def production_observability(repo_root: str | Path):
    root = Path(repo_root)
    staging = root / "data/v2/staging/user_web"
    export = root / "data/v2/exports/prachinlife_places_v2.json"
    db = root / "data/v2/place_platform_v2.sqlite3"
    switch_path = root / "data/v2/discovery_reports/v2_production_switch_current.json"

    files = {}
    for name in PUBLIC_FILES:
        prod = root / name
        stage = staging / name
        if not prod.exists():
            raise FileNotFoundError(prod)
        if not stage.exists():
            raise FileNotFoundError(stage)
        prod_rows = _rows(prod)
        stage_rows = _rows(stage)
        files[name] = {
            "production_count": len(prod_rows),
            "staging_count": len(stage_rows),
            "production_sha256": _sha(prod),
            "staging_sha256": _sha(stage),
            "matches_staging": _sha(prod) == _sha(stage),
        }

    switch = _json(switch_path)
    report = {
        "status": "PASS",
        "public_files": files,
        "all_public_match_staging": all(
            x["matches_staging"] for x in files.values()
        ),
        "detail_coverage": detail_coverage(export),
        "database_counts": database_counts(db),
        "database_sha256": _sha(db),
        "switch": {
            "status": switch.get("status"),
            "rollback_available": switch.get("rollback_available"),
            "automatic_rollback_performed": switch.get("automatic_rollback_performed"),
            "public_user_web_switched": switch.get("public_user_web_switched"),
            "database_changed": switch.get("database_changed"),
        },
    }
    return report

def assert_healthy(report, baseline=None):
    errors = []
    if not report.get("all_public_match_staging"):
        errors.append("production/staging drift detected")

    switch = report.get("switch", {})
    if switch.get("status") != "SWITCHED":
        errors.append("current switch status is not SWITCHED")
    if switch.get("rollback_available") is not True:
        errors.append("rollback is unavailable")
    if switch.get("public_user_web_switched") is not True:
        errors.append("public user web is not switched")
    if switch.get("database_changed") is not False:
        errors.append("switch reports database mutation")

    cov = report.get("detail_coverage", {})
    if cov.get("places") != 220:
        errors.append(f"unexpected V2 place count: {cov.get('places')}")

    if baseline:
        base_cov = baseline.get("detail_coverage", {})
        for field in DETAIL_FIELDS:
            if cov.get(field, 0) < base_cov.get(field, 0):
                errors.append(
                    f"detail coverage regressed: {field} "
                    f"{cov.get(field, 0)} < {base_cov.get(field, 0)}"
                )
        base_counts = baseline.get("public_counts", {})
        for name, expected in base_counts.items():
            got = report["public_files"].get(name, {}).get("production_count")
            if got != expected:
                errors.append(f"public count changed: {name} {got} != {expected}")

    if errors:
        raise RuntimeError("; ".join(errors))
    return True
