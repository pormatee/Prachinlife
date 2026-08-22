from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .comparative_release_gate import audit_fresh_comparative_release
from .production_readiness_gate import audit_production_readiness

FILES = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
)
POLICY_VERSION = "controlled-production-switch-v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-v2-switch")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _copy_atomic(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp-v2-switch")
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def _overlay_place_ids(staging_root: Path) -> set[str]:
    place_ids: set[str] = set()
    for filename in FILES:
        for row in _load(staging_root / filename):
            if not isinstance(row, dict):
                continue
            metadata = row.get("metadata")
            if isinstance(metadata, dict) and metadata.get("v2_preview_overlay") is True:
                place_id = metadata.get("v2_place_id")
                if place_id:
                    place_ids.add(str(place_id))
    return place_ids


def _validate_promoted_files(root: Path, staging_root: Path, expected_overlay_places: int):
    checks = []
    blockers = []

    def check(name: str, ok: bool, detail: str):
        item = {"name": name, "ok": bool(ok), "detail": detail}
        checks.append(item)
        if not ok:
            blockers.append(f"{name}: {detail}")

    for filename in FILES:
        production = root / filename
        staged = staging_root / filename
        check(
            f"{filename}:hash_matches_staging",
            production.exists() and staged.exists() and _sha256(production) == _sha256(staged),
            "promoted production JSON must byte-match staged overlay JSON",
        )
        if production.exists():
            try:
                rows = _load(production)
                check(f"{filename}:valid_json_array", isinstance(rows, list), f"type={type(rows).__name__}")
            except Exception as exc:  # pragma: no cover - defensive release check
                check(f"{filename}:valid_json_array", False, repr(exc))

    overlay_ids = _overlay_place_ids(root)
    check(
        "overlay_place_count_after_switch",
        len(overlay_ids) == expected_overlay_places,
        f"overlay_places={len(overlay_ids)}, expected={expected_overlay_places}",
    )
    return checks, blockers


def _backup_manifest(root: Path, backup_dir: Path, release_id: str):
    files = {}
    for filename in FILES:
        source = root / filename
        target = backup_dir / filename
        shutil.copy2(source, target)
        files[filename] = {
            "sha256": _sha256(source),
            "size_bytes": source.stat().st_size,
        }
    manifest = {
        "policy_version": POLICY_VERSION,
        "release_id": release_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    _write_json_atomic(backup_dir / "backup_manifest.json", manifest)
    return manifest


def plan_production_switch(
    repo_root: str | Path,
    database_path: str | Path,
    staging_root: str | Path,
):
    root = Path(repo_root).resolve()
    db = Path(database_path).resolve()
    staging = Path(staging_root).resolve()
    readiness = audit_production_readiness(root, db, staging)
    comparative = audit_fresh_comparative_release(root, db, staging)
    manifest = _load(staging / "manifest.json")

    blockers = []
    if readiness.get("status") != "READY":
        blockers.append(f"production readiness is {readiness.get('status')}")
    if comparative.get("status") != "PASS":
        blockers.append(f"comparative validation is {comparative.get('status')}")
    if comparative.get("rollback_verified") is not True:
        blockers.append("rollback was not verified")
    if int(manifest.get("eligible_place_count", 0) or 0) <= 0:
        blockers.append("eligible staged set is empty")
    if manifest.get("production_unchanged") is not True:
        blockers.append("staging manifest does not represent a pre-switch snapshot")

    file_plan = {}
    for filename in FILES:
        prod = root / filename
        staged = staging / filename
        if not prod.exists() or not staged.exists():
            blockers.append(f"missing production or staged file: {filename}")
            continue
        file_plan[filename] = {
            "production_sha256_before": _sha256(prod),
            "staged_sha256": _sha256(staged),
            "will_change": _sha256(prod) != _sha256(staged),
            "record_count": len(_load(staged)),
        }

    return {
        "mode": "DRY_RUN",
        "policy_version": POLICY_VERSION,
        "status": "READY_TO_SWITCH" if not blockers else "BLOCKED",
        "blockers": blockers,
        "eligible_place_count": int(manifest.get("eligible_place_count", 0) or 0),
        "overlay_place_count": int(manifest.get("overlay_place_count", 0) or 0),
        "readiness_status": readiness.get("status"),
        "comparative_status": comparative.get("status"),
        "rollback_verified": comparative.get("rollback_verified") is True,
        "files": file_plan,
        "production_changed": False,
        "public_user_web_switched": False,
    }


def commit_production_switch(
    repo_root: str | Path,
    database_path: str | Path,
    staging_root: str | Path,
    *,
    backup_root: str | Path | None = None,
    audit_root: str | Path | None = None,
):
    root = Path(repo_root).resolve()
    db = Path(database_path).resolve()
    staging = Path(staging_root).resolve()
    plan = plan_production_switch(root, db, staging)
    if plan["status"] != "READY_TO_SWITCH":
        raise RuntimeError("controlled production switch blocked: " + "; ".join(plan["blockers"]))

    release_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    backup_base = Path(backup_root).resolve() if backup_root else root / "data/v2/production_switch_backups"
    backup_dir = backup_base / release_id
    backup_dir.mkdir(parents=True, exist_ok=False)
    audit_base = Path(audit_root).resolve() if audit_root else root / "data/v2/discovery_reports"
    audit_base.mkdir(parents=True, exist_ok=True)

    backup_manifest = _backup_manifest(root, backup_dir, release_id)
    production_before = {filename: _sha256(root / filename) for filename in FILES}

    rolled_back = False
    try:
        for filename in FILES:
            _copy_atomic(staging / filename, root / filename)

        checks, blockers = _validate_promoted_files(
            root,
            staging,
            int(plan["overlay_place_count"]),
        )
        if blockers:
            raise RuntimeError("post-switch smoke failed: " + "; ".join(blockers))

        production_after = {filename: _sha256(root / filename) for filename in FILES}
        report = {
            "mode": "COMMIT",
            "policy_version": POLICY_VERSION,
            "status": "SWITCHED",
            "release_id": release_id,
            "switched_at": datetime.now(timezone.utc).isoformat(),
            "eligible_place_count": plan["eligible_place_count"],
            "overlay_place_count": plan["overlay_place_count"],
            "backup_dir": str(backup_dir),
            "production_sha256_before": production_before,
            "production_sha256_after": production_after,
            "staging_sha256": {filename: _sha256(staging / filename) for filename in FILES},
            "smoke_checks": checks,
            "rollback_available": True,
            "automatic_rollback_performed": False,
            "public_user_web_switched": True,
            "database_changed": False,
        }
        _write_json_atomic(audit_base / "v2_production_switch_current.json", report)
        _write_json_atomic(audit_base / f"v2_production_switch_{release_id}.json", report)
        return report
    except Exception:
        for filename in FILES:
            _copy_atomic(backup_dir / filename, root / filename)
        rolled_back = True
        restored = {
            filename: _sha256(root / filename) == backup_manifest["files"][filename]["sha256"]
            for filename in FILES
        }
        failure = {
            "mode": "COMMIT",
            "policy_version": POLICY_VERSION,
            "status": "ROLLED_BACK_AFTER_FAILURE",
            "release_id": release_id,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "backup_dir": str(backup_dir),
            "automatic_rollback_performed": True,
            "rollback_hashes_verified": all(restored.values()),
            "restored_files": restored,
            "public_user_web_switched": False,
            "database_changed": False,
        }
        _write_json_atomic(audit_base / "v2_production_switch_current.json", failure)
        _write_json_atomic(audit_base / f"v2_production_switch_{release_id}.json", failure)
        raise


def rollback_production_switch(
    repo_root: str | Path,
    release_id: str,
    *,
    backup_root: str | Path | None = None,
    audit_root: str | Path | None = None,
):
    root = Path(repo_root).resolve()
    backup_base = Path(backup_root).resolve() if backup_root else root / "data/v2/production_switch_backups"
    backup_dir = backup_base / release_id
    manifest_path = backup_dir / "backup_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = _load(manifest_path)

    for filename in FILES:
        _copy_atomic(backup_dir / filename, root / filename)
    restored = {
        filename: _sha256(root / filename) == manifest["files"][filename]["sha256"]
        for filename in FILES
    }
    if not all(restored.values()):
        raise RuntimeError("rollback hash verification failed")

    report = {
        "mode": "ROLLBACK",
        "policy_version": POLICY_VERSION,
        "status": "ROLLED_BACK",
        "release_id": release_id,
        "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        "restored_files": restored,
        "rollback_hashes_verified": True,
        "public_user_web_switched": False,
        "database_changed": False,
    }
    audit_base = Path(audit_root).resolve() if audit_root else root / "data/v2/discovery_reports"
    audit_base.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(audit_base / "v2_production_switch_current.json", report)
    _write_json_atomic(audit_base / f"v2_production_rollback_{release_id}.json", report)
    return report
