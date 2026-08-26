from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .controlled_production_switch import FILES, plan_production_switch
from .production_readiness_gate import audit_production_readiness
from .comparative_release_gate import audit_fresh_comparative_release
from .staged_milestone import eligible_place_ids
from .staged_overlay import build_overlay_staging

POLICY_VERSION = "v2-final-readiness-gate-y7"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_final_readiness(
    repo_root: str | Path,
    database_path: str | Path,
    staging_root: str | Path,
    province: str = "ปราจีนบุรี",
    *,
    rebuild_staging: bool = True,
):
    root = Path(repo_root).resolve()
    db = Path(database_path).resolve()
    staging = Path(staging_root).resolve()

    production_before = {filename: _sha256(root / filename) for filename in FILES}

    staging_manifest = None
    if rebuild_staging:
        staging_manifest = build_overlay_staging(db, root, staging, province)
    elif (staging / "manifest.json").exists():
        staging_manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))

    eligible, blocked = eligible_place_ids(db, province)
    comparative = audit_fresh_comparative_release(root, db, staging)
    readiness = audit_production_readiness(root, db, staging)
    switch_plan = plan_production_switch(root, db, staging)

    checks = []
    blockers = []

    def check(name: str, ok: bool, detail: str):
        item = {"name": name, "ok": bool(ok), "detail": detail}
        checks.append(item)
        if not ok:
            blockers.append(f"{name}: {detail}")

    manifest_eligible = int((staging_manifest or {}).get("eligible_place_count", 0) or 0)
    manifest_overlay = int((staging_manifest or {}).get("overlay_place_count", 0) or 0)

    check("all_current_places_eligible", len(blocked) == 0, f"eligible={len(eligible)}, blocked={len(blocked)}")
    check(
        "staging_matches_current_eligibility",
        len(eligible) > 0 and manifest_eligible == manifest_overlay == len(eligible),
        f"current={len(eligible)}, manifest_eligible={manifest_eligible}, overlay={manifest_overlay}",
    )
    check("fresh_comparative_pass", comparative.get("status") == "PASS", f"status={comparative.get('status')}")
    check("production_readiness_ready", readiness.get("status") == "READY", f"status={readiness.get('status')}")
    check("switch_plan_ready", switch_plan.get("status") == "READY_TO_SWITCH", f"status={switch_plan.get('status')}")
    check("rollback_verified", switch_plan.get("rollback_verified") is True, f"rollback={switch_plan.get('rollback_verified')}")
    check("public_switch_not_yet_performed", switch_plan.get("public_user_web_switched") is False, "pre-cutover gate must not switch users")
    check("production_not_changed_by_gate", production_before == {filename: _sha256(root / filename) for filename in FILES}, "gate must be read-only for production JSON")

    status = "READY_FOR_CUTOVER" if not blockers else "BLOCKED"
    return {
        "policy_version": POLICY_VERSION,
        "status": status,
        "province": province,
        "eligible_place_count": len(eligible),
        "blocked_place_count": len(blocked),
        "staging_eligible_place_count": manifest_eligible,
        "staging_overlay_place_count": manifest_overlay,
        "comparative_status": comparative.get("status"),
        "production_readiness_status": readiness.get("status"),
        "switch_plan_status": switch_plan.get("status"),
        "rollback_verified": switch_plan.get("rollback_verified") is True,
        "production_json_changed": production_before != {filename: _sha256(root / filename) for filename in FILES},
        "public_user_web_switched": False,
        "checks_passed": sum(1 for item in checks if item["ok"]),
        "checks_total": len(checks),
        "blockers": blockers,
        "checks": checks,
    }
