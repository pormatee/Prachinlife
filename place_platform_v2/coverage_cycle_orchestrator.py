from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .new_place_adoption_machine import evaluate_new_place_adoption, run_controlled_new_place_adoption
from .phase4_coverage_reaudit import audit_phase4_coverage

POLICY_VERSION = "5.1-coverage-cycle-orchestrator-v1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_coverage_cycle(
    *,
    root_dir: str | Path = ".",
    database_path: str | Path = "data/v2/place_platform_v2.sqlite3",
    reports_dir: str | Path = "data/v2/discovery_reports",
    province: str = "ปราจีนบุรี",
    category: str = "vegetarian",
    commit_adoption: bool = False,
) -> dict[str, Any]:
    """Run one safe operational pass over the Phase-4 coverage machine.

    This orchestrator does not invent observations or resolve human blockers.  It
    reconciles the current state, routes work to the correct next queue, and may
    invoke the already-controlled adoption commit only when explicitly requested.
    """
    root = Path(root_dir)
    db = root / Path(database_path)
    rd = root / Path(reports_dir)
    before = _sha256(db)

    coverage = audit_phase4_coverage(database_path=db, reports_dir=rd, province=province)
    adoption_eval = evaluate_new_place_adoption(database_path=db)

    followup = _load(rd / "identity_evidence_followup_v2.json")
    scope = _load(rd / "candidate_scope_verification_v2.json")

    work_items: list[dict[str, Any]] = []
    for d in adoption_eval["decisions"]:
        blockers = list(d["blockers"])
        if d["outcome"] == "READY":
            queue = "controlled_adoption"
            action = "controlled_commit" if commit_adoption else "review_ready_candidate"
        elif "unresolved_lifecycle_conflict" in blockers:
            queue, action = "manual_confirmation", "resolve_lifecycle_conflict"
        elif "pending_manual_or_coordinate_confirmation" in blockers or "exact_candidate_coordinates_not_verified" in blockers:
            queue, action = "coordinate_or_manual_confirmation", "supply_valid_direct_confirmation"
        elif "insufficient_independent_identity_sources" in blockers or "identity_not_verified" in blockers:
            queue, action = "identity_evidence", "acquire_truly_independent_source"
        else:
            queue, action = "verification", "review_adoption_blockers"
        work_items.append({"candidate_id": d["candidate_id"], "name": d["name"], "queue": queue,
                           "next_action": action, "blockers": blockers})

    # Preserve useful non-precanonical follow-up work surfaced by Phase 4 reports.
    seen_names = {x["name"] for x in work_items}
    for item in followup.get("results", []):
        name = item.get("name")
        if name and name not in seen_names and item.get("outcome") != "VERIFIED_IDENTITY":
            work_items.append({"candidate_id": item.get("candidate_id"), "name": name,
                               "queue": "identity_evidence", "next_action": item.get("next_step", "acquire_truly_independent_source"),
                               "blockers": ["identity_not_verified"]})
            seen_names.add(name)

    for item in scope.get("results", []):
        name = item.get("name")
        if name and name not in seen_names and item.get("outcome") == "GENERAL_OR_MIXED_SCOPE":
            work_items.append({"candidate_id": item.get("candidate_id"), "name": name,
                               "queue": "excluded_non_primary", "next_action": "keep_as_option_evidence",
                               "blockers": ["not_primary_directory_scope"]})
            seen_names.add(name)

    adoption_result = None
    if commit_adoption and adoption_eval.get("ready_count", 0):
        adoption_result = run_controlled_new_place_adoption(database_path=db, commit=True)

    after = _sha256(db)
    queues = Counter(x["queue"] for x in work_items)
    ready = adoption_eval.get("ready_count", 0)
    status = "PASS"
    return {
        "status": status,
        "policy_version": POLICY_VERSION,
        "mode": "CONTROLLED_COMMIT" if commit_adoption else "DRY_RUN",
        "scope": {"province": province, "category": category},
        "cycle": {
            "coverage_audit": coverage.get("status") == "PASS",
            "candidate_routing": True,
            "controlled_adoption_evaluated": True,
            "controlled_adoption_requested": commit_adoption,
            "controlled_adoption_executed": adoption_result is not None,
            "discovery_continues": True,
        },
        "summary": {
            "canonical_primary": coverage["canonical"]["primary_category_count"],
            "accounted_unique": coverage["funnel"]["accounted_unique_count"],
            "precanonical_candidates": adoption_eval["candidate_count"],
            "ready_for_adoption": ready,
            "work_item_count": len(work_items),
            "queue_counts": dict(sorted(queues.items())),
            "coverage_work_remains": coverage["closure_assessment"]["coverage_work_remains"],
        },
        "work_items": work_items,
        "adoption": adoption_result or {"eligible_count": ready, "commit_performed": False},
        "safety": {
            "database_unchanged": before == after,
            "database_writes": adoption_result is not None,
            "production_json_writes": False,
            "automatic_publication": False,
            "automatic_evidence_fabrication": False,
            "automatic_conflict_resolution": False,
            "explicit_commit_required": True,
            "trust_policy_lowered": False,
        },
    }
