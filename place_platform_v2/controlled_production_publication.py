from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .comparative_release_gate import audit_fresh_comparative_release
from .production_readiness_gate import audit_production_readiness
from .publication_impact_preview import (
    FILES,
    _production_mapping,
    _public_enrichment_rows,
    _revision_scope,
)

POLICY_VERSION = "3.9-controlled-production-publication-v2"
STAGING_REL = Path("data/v2/staging/user_web")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-phase3-9")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _target_scope(db):
    revs = _revision_scope(db)
    by_place = {}
    for rev in revs:
        by_place.setdefault(rev["place_id"], set()).add(rev["field_name"])
    return revs, by_place


def _trusted_links(enrichment):
    links = enrichment.get("external_links") or []
    out = []
    seen = set()
    for item in links:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(copy.deepcopy(item))
    return out


def _patch_record(record, *, fields, enrichment):
    """Apply only approved additive contact/trusted-link fields.

    This deliberately preserves production identity/category/location and does not add
    staging-preview marker fields (v2_preview_overlay etc.).
    """
    out = copy.deepcopy(record)
    metadata = dict(out.get("metadata") or {})
    for field in sorted(fields):
        value = enrichment.get(field)
        if value in (None, ""):
            continue
        before = metadata.get(field)
        if before not in (None, "", value):
            raise ValueError(f"contact overwrite blocked:{field}")
        metadata[field] = value
    out["metadata"] = metadata

    links = _trusted_links(enrichment)
    if links:
        before_links = out.get("external_links") or []
        if before_links not in ([], links):
            before_urls = {x.get("url") for x in before_links if isinstance(x, dict)}
            new_urls = {x.get("url") for x in links if isinstance(x, dict)}
            if not before_urls.issubset(new_urls):
                raise ValueError("external link destructive overwrite blocked")
        out["external_links"] = links
    return out


def _expected(repo_root, db):
    root = Path(repo_root).resolve()
    revs, fields_by_place = _target_scope(db)
    pids = set(fields_by_place)
    enrich = _public_enrichment_rows(db, pids)
    mapping = _production_mapping(db, pids)

    prod = {fn: _load(root / fn) for fn in FILES}
    stage = {fn: _load(root / STAGING_REL / fn) for fn in FILES}
    prod_idx = {fn: {str(r.get("id", "")): i for i, r in enumerate(prod[fn]) if isinstance(r, dict)} for fn in FILES}
    stage_idx = {fn: {str(r.get("id", "")): i for i, r in enumerate(stage[fn]) if isinstance(r, dict)} for fn in FILES}

    touched = []
    blockers = []
    for pid in sorted(pids):
        mapped = mapping.get(pid) or []
        if not mapped:
            blockers.append(f"production_mapping_missing:{pid}")
            continue
        for fn, rid in mapped:
            if rid not in prod_idx.get(fn, {}) or rid not in stage_idx.get(fn, {}):
                blockers.append(f"production_or_staging_record_missing:{fn}#{rid}:{pid}")
                continue
            try:
                prod[fn][prod_idx[fn][rid]] = _patch_record(
                    prod[fn][prod_idx[fn][rid]], fields=fields_by_place[pid], enrichment=enrich.get(pid) or {}
                )
                stage[fn][stage_idx[fn][rid]] = _patch_record(
                    stage[fn][stage_idx[fn][rid]], fields=fields_by_place[pid], enrichment=enrich.get(pid) or {}
                )
            except ValueError as exc:
                blockers.append(f"{fn}#{rid}:{pid}:{exc}")
                continue
            touched.append((fn, rid, pid))
    return prod, stage, touched, blockers, revs


def _state_counts(root, prod_expected, stage_expected):
    prod_changed = [fn for fn in FILES if _load(root / fn) != prod_expected[fn]]
    stage_changed = [fn for fn in FILES if _load(root / STAGING_REL / fn) != stage_expected[fn]]
    return prod_changed, stage_changed


def plan_controlled_production_publication(*, repo_root, database_path):
    root = Path(repo_root).resolve()
    db = Path(database_path).resolve()
    prod, stage, touched, blockers, revs = _expected(root, db)
    prod_changed, stage_changed = _state_counts(root, prod, stage)
    already = not prod_changed and not stage_changed

    field_counts = {}
    for rev in revs:
        field_counts[rev["field_name"]] = field_counts.get(rev["field_name"], 0) + 1
    link_count = 0
    pids = {rev["place_id"] for rev in revs}
    for payload in _public_enrichment_rows(db, pids).values():
        link_count += len(_trusted_links(payload))

    status = "ALREADY_PUBLISHED" if already else ("BLOCKED" if blockers else "READY_TO_PUBLISH")
    return {
        "policy_version": POLICY_VERSION,
        "mode": "DRY_RUN",
        "status": status,
        "changed_record_count": 0 if already else len({(f, rid) for f, rid, _ in touched}),
        "targeted_record_count": len({(f, rid) for f, rid, _ in touched}),
        "targeted_field_impact_counts": dict(sorted(field_counts.items())),
        "external_link_addition_count": link_count,
        "production_files_pending": prod_changed,
        "staging_files_pending": stage_changed,
        "blockers": blockers,
        "safety": {
            "database_unchanged": True,
            "trust_policy_lowered": False,
            "province_agnostic": True,
            "preserves_production_shape": True,
            "staging_synchronized": True,
        },
    }


def _backup_snapshot(root, bdir):
    (bdir / "production").mkdir(parents=True, exist_ok=False)
    (bdir / "staging").mkdir(parents=True, exist_ok=False)
    manifest = {"production": {}, "staging": {}}
    for fn in FILES:
        shutil.copy2(root / fn, bdir / "production" / fn)
        shutil.copy2(root / STAGING_REL / fn, bdir / "staging" / fn)
        manifest["production"][fn] = _sha(root / fn)
        manifest["staging"][fn] = _sha(root / STAGING_REL / fn)
    _write_atomic(bdir / "backup_manifest.json", manifest)
    return manifest


def _restore_snapshot(root, bdir):
    for fn in FILES:
        for src, dst in [
            (bdir / "production" / fn, root / fn),
            (bdir / "staging" / fn, root / STAGING_REL / fn),
        ]:
            if not src.exists():
                raise FileNotFoundError(src)
            tmp = dst.with_name(dst.name + ".tmp-phase3-9-rollback")
            shutil.copy2(src, tmp)
            os.replace(tmp, dst)


def _snapshot_verified(root, bdir):
    return all(
        _sha(root / fn) == _sha(bdir / "production" / fn)
        and _sha(root / STAGING_REL / fn) == _sha(bdir / "staging" / fn)
        for fn in FILES
    )


def commit_controlled_production_publication(*, repo_root, database_path, backup_root=None, audit_root=None):
    root = Path(repo_root).resolve()
    db = Path(database_path).resolve()
    plan = plan_controlled_production_publication(repo_root=root, database_path=db)
    if plan["status"] == "ALREADY_PUBLISHED":
        return {
            **plan,
            "mode": "COMMIT",
            "published_record_count": 0,
            "already_published": True,
            "production_json_writes": False,
        }
    if plan["status"] != "READY_TO_PUBLISH":
        raise RuntimeError("publication blocked: " + "; ".join(plan["blockers"]))

    prod, stage, _, blockers, _ = _expected(root, db)
    if blockers:
        raise RuntimeError("publication blocked: " + "; ".join(blockers))

    db_before = _sha(db)
    rid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    bbase = Path(backup_root).resolve() if backup_root else root / "data/v2/phase3_9_publication_backups"
    bdir = bbase / rid
    bdir.mkdir(parents=True, exist_ok=False)
    backup_manifest = _backup_snapshot(root, bdir)

    automatic_rollback = False
    try:
        for fn in FILES:
            if _load(root / fn) != prod[fn]:
                _write_atomic(root / fn, prod[fn])
            if _load(root / STAGING_REL / fn) != stage[fn]:
                _write_atomic(root / STAGING_REL / fn, stage[fn])

        post = plan_controlled_production_publication(repo_root=root, database_path=db)
        if post["status"] != "ALREADY_PUBLISHED":
            raise RuntimeError("post publication idempotency validation failed")
        if _sha(db) != db_before:
            raise RuntimeError("database changed during publication")

        comparative = audit_fresh_comparative_release(root, db, root / STAGING_REL)
        readiness = audit_production_readiness(root, db, root / STAGING_REL)
        if comparative["status"] != "PASS":
            raise RuntimeError("post publication comparative validation failed")
        if readiness["status"] != "READY":
            raise RuntimeError("post publication readiness validation failed")

        report = {
            "policy_version": POLICY_VERSION,
            "mode": "COMMIT",
            "status": "PUBLISHED",
            "release_id": rid,
            "published_record_count": plan["changed_record_count"],
            "targeted_record_count": plan["targeted_record_count"],
            "targeted_field_impact_counts": plan.get("targeted_field_impact_counts", {}),
            "external_link_addition_count": plan.get("external_link_addition_count", 0),
            "backup_dir": str(bdir),
            "rollback_available": True,
            "automatic_rollback_performed": False,
            "post_comparative_status": comparative["status"],
            "post_readiness_status": readiness["status"],
            "backup_manifest": backup_manifest,
            "safety": {
                "database_unchanged": True,
                "atomic_writes": True,
                "scope_limited_to_preview": True,
                "trust_policy_lowered": False,
                "province_agnostic": True,
                "production_shape_preserved": True,
                "staging_synchronized": True,
            },
        }
        abase = Path(audit_root).resolve() if audit_root else root / "data/v2/discovery_reports"
        abase.mkdir(parents=True, exist_ok=True)
        _write_atomic(abase / "controlled_production_publication_v2.json", report)
        return report
    except Exception:
        automatic_rollback = True
        _restore_snapshot(root, bdir)
        if not _snapshot_verified(root, bdir):
            raise RuntimeError("automatic rollback hash verification failed")
        raise


def rollback_controlled_production_publication(*, repo_root, release_id, backup_root=None, audit_root=None):
    root = Path(repo_root).resolve()
    bbase = Path(backup_root).resolve() if backup_root else root / "data/v2/phase3_9_publication_backups"
    bdir = bbase / release_id
    if not bdir.exists():
        raise FileNotFoundError(bdir)
    _restore_snapshot(root, bdir)
    verified = _snapshot_verified(root, bdir)
    report = {
        "policy_version": POLICY_VERSION,
        "mode": "ROLLBACK",
        "status": "ROLLED_BACK",
        "release_id": release_id,
        "restored_production_files": {fn: True for fn in FILES},
        "restored_staging_files": {fn: True for fn in FILES},
        "rollback_hashes_verified": verified,
        "safety": {"database_unchanged": True, "trust_policy_lowered": False},
    }
    abase = Path(audit_root).resolve() if audit_root else root / "data/v2/discovery_reports"
    abase.mkdir(parents=True, exist_ok=True)
    _write_atomic(abase / "controlled_production_publication_v2.json", report)
    return report

# === DEDICATED PERSISTED PROJECTION WIRING V1 ===
from .controlled_production_projection_wiring_v1 import (
    sync_dedicated_projection_after_commit as _sync_dedicated_projection_after_commit_v1,
    rollback_dedicated_projection as _rollback_dedicated_projection_v1,
)

_commit_controlled_production_publication_without_projection_v1 = commit_controlled_production_publication
_rollback_controlled_production_publication_without_projection_v1 = rollback_controlled_production_publication

def commit_controlled_production_publication(*args, **kwargs):
    result = _commit_controlled_production_publication_without_projection_v1(*args, **kwargs)
    repo_root = kwargs.get("repo_root")
    if repo_root is None and len(args) >= 1:
        repo_root = args[0]
    if repo_root is None:
        raise RuntimeError("repo_root required for projection wiring")
    projection = _sync_dedicated_projection_after_commit_v1(
        repo_root=repo_root,
        publication_result=result,
    )
    if isinstance(result, dict):
        result = dict(result)
        result["persisted_projection_v1"] = projection
    return result

def rollback_controlled_production_publication(*args, **kwargs):
    repo_root = kwargs.get("repo_root")
    release_id = kwargs.get("release_id")
    if repo_root is None and len(args) >= 1:
        repo_root = args[0]
    if release_id is None and len(args) >= 2:
        release_id = args[1]
    result = _rollback_controlled_production_publication_without_projection_v1(*args, **kwargs)
    projection = _rollback_dedicated_projection_v1(
        repo_root=repo_root,
        release_id=release_id,
    )
    if isinstance(result, dict):
        result = dict(result)
        result["persisted_projection_v1"] = projection
    return result

