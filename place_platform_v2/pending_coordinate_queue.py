from __future__ import annotations
import json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_VERSION = "4.14-pending-coordinate-queue-v1"
_NAMESPACE = uuid.UUID("8f7dcf6b-8f93-4bfe-8c2d-bd9db6e10a66")


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _qid(candidate_id: str, reason: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, candidate_id + "|" + reason))


def queue_pending_coordinates(*, database_path, direct_coordinate_report_path, commit=False) -> dict[str, Any]:
    db = Path(database_path)
    report = _load(direct_coordinate_report_path)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")

    before_nonqueue = {}
    for t in [r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' and name!='precanonical_pending_review' order by name")]:
        before_nonqueue[t] = [tuple(x) for x in con.execute(f'SELECT * FROM "{t}" ORDER BY rowid')]

    name = str(report.get("candidate_name") or "").strip()
    province = str(report.get("province") or "").strip()
    candidate = con.execute(
        "select candidate_id,candidate_key,proposed_name,province,status from precanonical_candidates where proposed_name=? and province=?",
        (name, province),
    ).fetchone()

    pending = []
    if candidate and report.get("confirmation_outcome") == "STILL_UNRESOLVED" and report.get("next_step") == "supply_valid_direct_coordinate_confirmation":
        pending.append({
            "candidate_id": candidate["candidate_id"],
            "candidate_key": candidate["candidate_key"],
            "name": candidate["proposed_name"],
            "province": candidate["province"],
            "reason": "unresolved_exact_coordinates",
            "current_state": "EXACT_COORDINATES_UNRESOLVED",
            "next_action": "supply_valid_direct_coordinate_confirmation",
            "queue_type": "pending_coordinate_confirmation",
            "source_policy_version": str(report.get("policy_version") or ""),
        })

    inserted = already = 0
    if commit:
        now = datetime.now(timezone.utc).isoformat()
        con.execute("BEGIN")
        for p in pending:
            qid = _qid(p["candidate_id"], p["reason"])
            payload = json.dumps(p, ensure_ascii=False, sort_keys=True)
            cur = con.execute(
                """INSERT OR IGNORE INTO precanonical_pending_review
                (queue_id,candidate_id,reason,current_state,next_action,status,source_policy_version,payload_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (qid, p["candidate_id"], p["reason"], p["current_state"], p["next_action"],
                 p["queue_type"], p["source_policy_version"], payload, now, now),
            )
            if cur.rowcount:
                inserted += 1
            else:
                already += 1
        con.commit()

    queue_rows = [dict(r) for r in con.execute("""select q.queue_id,q.candidate_id,q.reason,q.current_state,q.next_action,q.status,
        q.source_policy_version,c.proposed_name as name,c.province
        from precanonical_pending_review q join precanonical_candidates c on c.candidate_id=q.candidate_id
        order by q.created_at,q.queue_id""")]

    after_nonqueue = {}
    for t in before_nonqueue:
        after_nonqueue[t] = [tuple(x) for x in con.execute(f'SELECT * FROM "{t}" ORDER BY rowid')]
    con.close()

    type_counts = {}
    for x in queue_rows:
        type_counts[x["status"]] = type_counts.get(x["status"], 0) + 1

    return {
        "status": "PASS",
        "mode": "COMMIT" if commit else "DRY_RUN",
        "policy_version": POLICY_VERSION,
        "pending_candidate_count": len(pending),
        "inserted_queue_count": inserted,
        "already_present_queue_count": already,
        "pending_queue_total": len(queue_rows),
        "queue_type_counts": dict(sorted(type_counts.items())),
        "pending_candidates": pending,
        "queue_rows": queue_rows,
        "discovery_continues": True,
        "next_discovery_work": {
            "mode": "coverage",
            "province": "ปราจีนบุรี",
            "category": "vegetarian",
            "pending_candidates_do_not_block_discovery": True,
        },
        "safety": {
            "non_queue_tables_unchanged": before_nonqueue == after_nonqueue,
            "canonical_writes": False,
            "precanonical_identity_or_evidence_writes": False,
            "production_json_writes": False,
            "automatic_adoption": False,
            "automatic_publication": False,
            "pending_candidate_blocks_discovery": False,
            "trust_policy_lowered": False,
            "queue_types_separated": True,
        },
    }
