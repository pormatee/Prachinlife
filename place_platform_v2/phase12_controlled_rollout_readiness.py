from __future__ import annotations

import hashlib
import json
from pathlib import Path

FILES = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
)

def sha256(path: str | Path) -> str:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def staged_public_diff(repo_root: str | Path, staging_root: str | Path):
    root = Path(repo_root)
    staging = Path(staging_root)
    result = {}
    for name in FILES:
        prod = root / name
        stage = staging / name
        result[name] = {
            "production_exists": prod.exists(),
            "staging_exists": stage.exists(),
            "production_sha256": sha256(prod) if prod.exists() else None,
            "staging_sha256": sha256(stage) if stage.exists() else None,
            "will_change": (
                prod.exists()
                and stage.exists()
                and sha256(prod) != sha256(stage)
            ),
            "staged_count": (
                len(load_json(stage))
                if stage.exists() and isinstance(load_json(stage), list)
                else None
            ),
        }
    return result

def assert_post_switch(repo_root: str | Path, staging_root: str | Path):
    root = Path(repo_root)
    staging = Path(staging_root)
    errors = []
    for name in FILES:
        prod = root / name
        stage = staging / name
        if not prod.exists() or not stage.exists():
            errors.append(f"missing file: {name}")
            continue
        if sha256(prod) != sha256(stage):
            errors.append(f"hash mismatch: {name}")
        try:
            rows = load_json(prod)
        except Exception as exc:
            errors.append(f"invalid json {name}: {exc!r}")
            continue
        if not isinstance(rows, list):
            errors.append(f"not json array: {name}")
    if errors:
        raise RuntimeError("; ".join(errors))
    return {
        "status": "PASS",
        "files": list(FILES),
        "production_matches_staging": True,
    }

def read_current_switch_report(repo_root: str | Path):
    p = Path(repo_root) / "data/v2/discovery_reports/v2_production_switch_current.json"
    if not p.exists():
        raise FileNotFoundError(p)
    return load_json(p)
