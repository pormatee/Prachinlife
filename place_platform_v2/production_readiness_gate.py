from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .comparative_release_gate import audit_fresh_comparative_release


def audit_production_readiness(repo_root: str | Path, database_path: str | Path, staging_root: str | Path):
    root = Path(repo_root)
    db = Path(database_path)
    staging = Path(staging_root)
    comparative = audit_fresh_comparative_release(root, db, staging)

    checks = []
    blockers = []
    warnings = []

    def check(name, ok, detail):
        ok = bool(ok)
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            blockers.append(f"{name}: {detail}")

    check("fresh_comparative_pass", comparative["status"] == "PASS", f"comparative={comparative['status']}")
    check("rollback_verified", comparative.get("rollback_verified") is True, f"rollback={comparative.get('rollback_verified')}")
    check("eligible_overlay_complete", comparative.get("eligible_place_count", 0) > 0 and comparative.get("eligible_place_count") == comparative.get("overlay_place_count"), f"eligible={comparative.get('eligible_place_count')}, overlay={comparative.get('overlay_place_count')}")
    check("comparative_has_no_blockers", not comparative.get("blockers"), f"blockers={len(comparative.get('blockers') or [])}")

    con = sqlite3.connect(db)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        con.close()
    check("database_integrity", integrity == "ok", f"integrity={integrity}")
    check("database_foreign_keys", len(fk) == 0, f"foreign_key_errors={len(fk)}")

    manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
    check("staging_production_unchanged", manifest.get("production_unchanged") is True, "production source files remain unchanged")
    check("public_switch_still_disabled", manifest.get("public_user_web_switched") is False, "public switch remains disabled")

    # The old Phase 2H NO remains preserved as history. It is not a blocker once a
    # newer comparative gate has PASSed; record the supersession explicitly.
    old = root / "data/v2/discovery_reports/phase2h_comparative_beta_ready.json"
    if old.exists():
        old_report = json.loads(old.read_text(encoding="utf-8"))
        if old_report.get("production_switch") == "NO":
            warnings.append("Phase 2H historical NO is preserved but superseded by fresh-comparative-release-gate-v1 PASS.")

    # Historical warning is informational only once supersession is explicit.
    ready = not blockers and comparative["status"] == "PASS"
    return {
        "policy_version": "v2-production-readiness-gate-v2",
        "status": "READY" if ready else "NOT_READY",
        "checks_passed": sum(1 for x in checks if x["ok"]),
        "checks_total": len(checks),
        "blockers": blockers,
        "warnings": warnings,
        "eligible_place_count": comparative.get("eligible_place_count", 0),
        "overlay_place_count": comparative.get("overlay_place_count", 0),
        "comparative_status": comparative["status"],
        "comparative_policy_version": comparative["policy_version"],
        "phase2h_superseded": comparative["status"] == "PASS",
        "rollback_verified": comparative.get("rollback_verified") is True,
        "production_switch_performed": False,
        "public_user_web_switched": False,
        "checks": checks,
    }
