from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from place_platform_v2.completeness import audit_places


DEFAULT_EXPORT = Path("data/v2/exports/prachinlife_places_v2.json")
DEFAULT_DB = Path("data/v2/place_platform_v2.sqlite3")
DEFAULT_JSON = Path("data/v2/discovery_reports/place_detail_completeness_v2.json")
DEFAULT_MD = Path("data/v2/discovery_reports/place_detail_completeness_v2.md")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def evidence_inventory(db_path: Path) -> dict[str, int]:
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT field_name, COUNT(*) FROM place_evidence GROUP BY field_name"
        ).fetchall()
        return {str(name): int(count) for name, count in rows}
    finally:
        con.close()


def load_places(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("places", [])
    if not isinstance(data, list):
        raise ValueError("V2 export must contain a places list")
    return [item for item in data if isinstance(item, dict)]


def render_markdown(report: dict) -> str:
    lines = [
        "# PrachinLife V2 Place Detail Completeness Audit",
        "",
        f"Places audited: **{report['place_count']}**",
        "",
        "## Detail-field coverage",
        "",
        "| Field | Present | Missing | Coverage | Admin priority |",
        "|---|---:|---:|---:|---|",
    ]
    priority_by_field = {p["field"]: p["priority"] for p in report["admin_priority"]}
    for field, stats in report["detail_fields"].items():
        lines.append(
            f"| {field} | {stats['present']} | {stats['missing']} | "
            f"{stats['coverage_percent']:.1f}% | {priority_by_field[field]} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "This report measures only evidence-backed fields already present in the V2 export. "
        "Missing values must not be invented; they should be supplied through Admin/source evidence "
        "and the existing verification/adoption/publication pipeline.",
        "",
        "## Evidence inventory in Central DB",
        "",
    ]
    for name, count in sorted(report.get("evidence_inventory", {}).items()):
        lines.append(f"- `{name}`: {count}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    db_hash_before = sha256(args.db)
    report = audit_places(load_places(args.export))
    report["evidence_inventory"] = evidence_inventory(args.db)
    report["central_db_sha256"] = db_hash_before
    report["mode"] = "read_only_audit"

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report), encoding="utf-8")

    db_hash_after = sha256(args.db)
    if db_hash_after != db_hash_before:
        raise SystemExit("FAIL: Central DB changed during read-only audit")

    print(f"PLACE_COUNT={report['place_count']}")
    for field, stats in report["detail_fields"].items():
        print(
            f"{field}: present={stats['present']} missing={stats['missing']} "
            f"coverage={stats['coverage_percent']:.1f}%"
        )
    print(f"CENTRAL_DB_SHA256={db_hash_after}")
    print("RESULT=PASS")


if __name__ == "__main__":
    main()
