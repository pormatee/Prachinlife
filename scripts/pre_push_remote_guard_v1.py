#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

SCHEMA_VERSION = "PRACHIN-PRE-PUSH-REMOTE-GUARD-V1"
DEFAULT_BRANCH = "main"


def run_git(args: Sequence[str], *, check: bool = True) -> str:
    cp = subprocess.run(
        ["git", *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return cp.stdout.strip()


def tracked_clean() -> bool:
    unstaged = subprocess.run(["git", "diff", "--quiet"]).returncode == 0
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0
    return unstaged and staged


def count_range(rev_range: str) -> int:
    return int(run_git(["rev-list", "--count", rev_range]))


def current_state(branch: str = DEFAULT_BRANCH) -> dict:
    local = run_git(["rev-parse", "HEAD"])
    remote_ref = f"origin/{branch}"
    remote = run_git(["rev-parse", remote_ref])
    branch_now = run_git(["branch", "--show-current"])
    ahead = count_range(f"{remote_ref}..HEAD")
    behind = count_range(f"HEAD..{remote_ref}")
    return {
        "branch": branch_now,
        "local_head": local,
        "remote_head": remote,
        "ahead": ahead,
        "behind": behind,
        "tracked_clean": tracked_clean(),
    }


def snapshot_path() -> Path:
    p = run_git(["rev-parse", "--git-path", "prachinlife_pre_push_guard_v1.json"])
    return Path(p)


def evaluate_pre_push(snapshot: dict, current: dict, expected_branch: str = DEFAULT_BRANCH) -> list[str]:
    reasons: list[str] = []
    if not current.get("tracked_clean", False):
        reasons.append("TRACKED_WORKTREE_NOT_CLEAN")
    if current.get("branch") != expected_branch:
        reasons.append("WRONG_BRANCH")
    if snapshot.get("branch") != expected_branch:
        reasons.append("SNAPSHOT_WRONG_BRANCH")
    if current.get("local_head") != snapshot.get("local_head"):
        reasons.append("LOCAL_HEAD_CHANGED_AFTER_VALIDATION")
    if current.get("remote_head") != snapshot.get("remote_head"):
        reasons.append("REMOTE_MOVED_AFTER_VALIDATION")
    if int(current.get("behind", -1)) != 0:
        reasons.append("LOCAL_BEHIND_REMOTE")
    if int(current.get("ahead", 0)) <= 0:
        reasons.append("NO_LOCAL_COMMITS_TO_PUSH")
    return reasons


def record(branch: str) -> int:
    if not tracked_clean():
        print("CLASSIFICATION=BLOCKED")
        print("REASON=TRACKED_WORKTREE_NOT_CLEAN")
        return 2

    run_git(["fetch", "origin"])
    state = current_state(branch)
    if state["branch"] != branch:
        print("CLASSIFICATION=BLOCKED")
        print("REASON=WRONG_BRANCH")
        return 3
    if state["behind"] != 0:
        print("CLASSIFICATION=BLOCKED")
        print("REASON=LOCAL_BEHIND_REMOTE")
        return 4
    if state["ahead"] <= 0:
        print("CLASSIFICATION=BLOCKED")
        print("REASON=NO_LOCAL_COMMITS_TO_PUSH")
        return 5

    payload = {
        "schema_version": SCHEMA_VERSION,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        **state,
    }
    path = snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"SNAPSHOT={path}")
    print(f"LOCAL_HEAD={state['local_head']}")
    print(f"REMOTE_HEAD={state['remote_head']}")
    print(f"AHEAD={state['ahead']}")
    print(f"BEHIND={state['behind']}")
    print("CLASSIFICATION=VALIDATION_SNAPSHOT_RECORDED")
    return 0


def check(branch: str) -> int:
    path = snapshot_path()
    if not path.exists():
        print("CLASSIFICATION=BLOCKED")
        print("REASON=VALIDATION_SNAPSHOT_MISSING")
        return 10

    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        print("CLASSIFICATION=BLOCKED")
        print("REASON=VALIDATION_SNAPSHOT_INVALID")
        return 11

    if snapshot.get("schema_version") != SCHEMA_VERSION:
        print("CLASSIFICATION=BLOCKED")
        print("REASON=VALIDATION_SNAPSHOT_SCHEMA_MISMATCH")
        return 12

    run_git(["fetch", "origin"])
    current = current_state(branch)
    reasons = evaluate_pre_push(snapshot, current, branch)

    print(f"VALIDATED_LOCAL_HEAD={snapshot.get('local_head','')}")
    print(f"VALIDATED_REMOTE_HEAD={snapshot.get('remote_head','')}")
    print(f"CURRENT_LOCAL_HEAD={current['local_head']}")
    print(f"CURRENT_REMOTE_HEAD={current['remote_head']}")
    print(f"AHEAD={current['ahead']}")
    print(f"BEHIND={current['behind']}")
    print(f"TRACKED_CLEAN={'TRUE' if current['tracked_clean'] else 'FALSE'}")

    if reasons:
        print("CLASSIFICATION=BLOCKED")
        for reason in reasons:
            print(f"REASON={reason}")
        return 20

    print("CLASSIFICATION=READY_FOR_NORMAL_PUSH")
    print("PUSH_EXECUTED=FALSE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PrachinLife pre-push remote guard. "
            "It records the Git state that was validated after regression, then later checks "
            "that local HEAD and origin/main have not moved before a normal push. "
            "This tool never runs git push."
        )
    )
    parser.add_argument("action", choices=("record", "check"))
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    args = parser.parse_args()
    return record(args.branch) if args.action == "record" else check(args.branch)


if __name__ == "__main__":
    raise SystemExit(main())
