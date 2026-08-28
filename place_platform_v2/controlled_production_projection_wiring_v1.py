from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .controlled_publication_bundle_adapter_v1 import BUNDLE_FILES, build_projection_database

DEFAULT_PROJECTION_REL = Path("data/v2/decision_published_places_v1.sqlite3")
DEFAULT_BACKUP_REL = Path("data/v2/decision_projection_backups_v1")
MANIFEST = "projection_manifest_v1.json"


def _sha(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _bundle_fingerprint(root: Path) -> str:
    h = hashlib.sha256()
    for filename in BUNDLE_FILES:
        p = root / filename
        h.update(filename.encode("utf-8"))
        h.update(b"\0")
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        h.update(b"\0")
    return h.hexdigest()


def _release_id(publication_result: Any, root: Path) -> tuple[str, str]:
    if isinstance(publication_result, dict):
        for key in ("release_id", "publication_release_id", "id"):
            value = publication_result.get(key)
            if value:
                return str(value), "CONTROLLED_PUBLICATION_RELEASE"
    return "bundle-" + _bundle_fingerprint(root)[:24], "BUNDLE_FINGERPRINT"


def sync_dedicated_projection_after_commit(
    *,
    repo_root: str | Path,
    publication_result: dict[str, Any],
    projection_path: str | Path | None = None,
    backup_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    target = Path(projection_path) if projection_path else root / DEFAULT_PROJECTION_REL
    backups = Path(backup_root) if backup_root else root / DEFAULT_BACKUP_REL
    release_id, release_id_source = _release_id(publication_result, root)

    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.unlink(missing_ok=True)
        adapter_report = build_projection_database(root, tmp)

        con = sqlite3.connect(tmp)
        try:
            count = con.execute("SELECT COUNT(*) FROM decision_published_places_v1").fetchone()[0]
        finally:
            con.close()

        if count != adapter_report["projection_count"]:
            raise RuntimeError("projection count mismatch before atomic replace")

        candidate_sha = _sha(tmp)
        current_sha = _sha(target)

        if current_sha is not None and current_sha == candidate_sha:
            tmp.unlink(missing_ok=True)
            return {
                "status": "PASS",
                "release_id": release_id,
                "release_id_source": release_id_source,
                "projection_path": str(target),
                "projection_count": adapter_report["projection_count"],
                "source_total_records": adapter_report["total_records"],
                "rejected_record_count": adapter_report["rejected_record_count"],
                "duplicate_record_count": adapter_report["duplicate_record_count"],
                "projection_backup_created": False,
                "atomic_replace": False,
                "idempotent": True,
                "consumer_switched": False,
            }

        release_backup = backups / release_id
        if release_backup.exists():
            raise RuntimeError("projection release fingerprint collision or non-idempotent source")

        release_backup.mkdir(parents=True, exist_ok=False)
        before_exists = target.exists()
        before_sha = current_sha
        if before_exists:
            shutil.copy2(target, release_backup / target.name)

        manifest = {
            "release_id": release_id,
            "release_id_source": release_id_source,
            "projection_path": str(target),
            "before_exists": before_exists,
            "before_sha256": before_sha,
            "candidate_sha256": candidate_sha,
        }
        (release_backup / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    return {
        "status": "PASS",
        "release_id": release_id,
        "release_id_source": release_id_source,
        "projection_path": str(target),
        "projection_count": adapter_report["projection_count"],
        "source_total_records": adapter_report["total_records"],
        "rejected_record_count": adapter_report["rejected_record_count"],
        "duplicate_record_count": adapter_report["duplicate_record_count"],
        "projection_backup_created": True,
        "atomic_replace": True,
        "idempotent": False,
        "consumer_switched": False,
    }


def rollback_dedicated_projection(
    *,
    repo_root: str | Path,
    release_id: str,
    projection_path: str | Path | None = None,
    backup_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    target = Path(projection_path) if projection_path else root / DEFAULT_PROJECTION_REL
    backups = Path(backup_root) if backup_root else root / DEFAULT_BACKUP_REL
    release_backup = backups / str(release_id)
    manifest_path = release_backup / MANIFEST
    if not manifest_path.exists():
        return {"status": "NO_PROJECTION_BACKUP", "release_id": str(release_id), "projection_restored": False}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("before_exists"):
        backup_file = release_backup / target.name
        if not backup_file.exists():
            raise RuntimeError("projection rollback backup missing")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, target)
    else:
        target.unlink(missing_ok=True)

    expected = manifest.get("before_sha256")
    actual = _sha(target)
    if expected != actual:
        raise RuntimeError("projection rollback hash mismatch")

    return {"status": "PASS", "release_id": str(release_id), "projection_restored": True, "restored_sha256": actual}
