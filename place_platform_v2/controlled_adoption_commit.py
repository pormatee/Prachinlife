"""Phase 2V.2 controlled canonical commit for approved admin drafts.

Only existing canonical places are eligible. The commit is explicit, atomic in
SQLite (approved evidence + canonical revisions + idempotency receipt), and does
not publish or regenerate any public export.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .admin_drafts import AdminDraftStatus, AdminDraftStore
from .adoption import AdoptionOutcome, AdoptionPolicy, apply_adoption, propose_adoption
from .controlled_adoption import _draft_evidence, _underlying_source_key, file_sha256
from .sqlite_store import SQLitePlaceRepository
from .verification import VerificationPolicy, verify_field

COMMIT_POLICY_VERSION = "2V.2-controlled-commit-v1"


@dataclass(frozen=True)
class ControlledCommitResult:
    mode: str
    draft_id: str
    target_place_id: str | None
    result: str
    reason: str
    changed_fields: tuple[str, ...]
    blocked_fields: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    revision_ids: tuple[str, ...]
    canonical_hash_before: str
    canonical_hash_after: str
    publication_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _latest_approved(store: AdminDraftStore, draft_id: str) -> dict[str, Any] | None:
    for item in store.list_review_groups(AdminDraftStatus.APPROVED, limit=10000):
        if str(item.get("draft_id")) == draft_id:
            return item
    return None


def commit_approved_draft(
    *,
    canonical_database: str | Path,
    draft_database: str | Path,
    draft_id: str,
    verification_policy: VerificationPolicy = VerificationPolicy(),
    adoption_policy: AdoptionPolicy = AdoptionPolicy(),
    committed_at: datetime | None = None,
) -> ControlledCommitResult:
    canonical_database = Path(canonical_database)
    draft_database = Path(draft_database)
    before_hash = file_sha256(canonical_database)
    when = committed_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError("committed_at must be timezone-aware")

    with AdminDraftStore(draft_database) as drafts, SQLitePlaceRepository(canonical_database) as repo:
        existing = repo.get_admin_adoption_receipt(draft_id)
        if existing is not None:
            after_hash = file_sha256(canonical_database)
            return ControlledCommitResult(
                mode="COMMIT", draft_id=draft_id, target_place_id=existing["place_id"],
                result="already_committed", reason="idempotent adoption receipt already exists",
                changed_fields=(), blocked_fields=(), evidence_ids=tuple(existing["evidence_ids"]),
                revision_ids=tuple(existing["revision_ids"]), canonical_hash_before=before_hash,
                canonical_hash_after=after_hash,
            )

        item = _latest_approved(drafts, draft_id)
        if item is None:
            raise ValueError("draft must be the latest approved version of its review group")
        operation = str(item.get("operation") or "")
        target = item.get("target_place_id")
        if operation != "update_place_candidate" or not target:
            raise ValueError("Phase 2V.2 commits existing canonical updates only")
        place = repo.get_place(str(target))
        if place is None:
            raise ValueError("target canonical place does not exist")

        admin_evidence = _draft_evidence(item)
        stored = repo.list_evidence(str(target))
        draft_source_keys = {_underlying_source_key(e) for e in admin_evidence}
        independent_stored = tuple(e for e in stored if _underlying_source_key(e) not in draft_source_keys)
        combined = (*independent_stored, *admin_evidence)

        proposals = []
        blocked_fields: list[str] = []
        seen_fields: set[str] = set()
        for evidence_item in admin_evidence:
            field = evidence_item.field_name
            if field in seen_fields:
                continue
            seen_fields.add(field)
            try:
                current_value = getattr(place, field)
            except AttributeError:
                blocked_fields.append(field)
                continue
            verification = verify_field(
                place_id=str(target), field_name=field, evidence=combined, policy=verification_policy,
            )
            proposal = propose_adoption(
                place=place, verification=verification, policy=adoption_policy,
                evidence_ids=tuple(e.evidence_id for e in combined if e.field_name == field),
            )
            if proposal.outcome is AdoptionOutcome.PROPOSED:
                proposals.append(proposal)
            elif proposal.outcome is AdoptionOutcome.BLOCKED:
                blocked_fields.append(field)
            elif proposal.current_value != current_value:
                blocked_fields.append(field)

        if not proposals:
            after_hash = file_sha256(canonical_database)
            return ControlledCommitResult(
                mode="COMMIT", draft_id=draft_id, target_place_id=str(target), result="blocked",
                reason="no approved field satisfies canonical adoption policy",
                changed_fields=(), blocked_fields=tuple(sorted(set(blocked_fields))), evidence_ids=(),
                revision_ids=(), canonical_hash_before=before_hash, canonical_hash_after=after_hash,
            )

        updated = place
        revisions = []
        for proposal in proposals:
            # Rebuild against the progressively updated place so each immutable
            # revision has the actual before value at its point in the batch.
            proposal = proposal.__class__(
                place_id=proposal.place_id, field_name=proposal.field_name,
                outcome=proposal.outcome, current_value=getattr(updated, proposal.field_name),
                proposed_value=proposal.proposed_value,
                verification_outcome=proposal.verification_outcome,
                evidence_ids=proposal.evidence_ids, policy_version=proposal.policy_version,
                reason=f"{proposal.reason}; admin draft {draft_id}",
            )
            updated, revision = apply_adoption(place=updated, proposal=proposal, applied_at=when)
            revisions.append(revision)

        receipt = repo.commit_admin_adoption_batch(
            draft_id=draft_id, place=updated, revisions=tuple(revisions), evidence=admin_evidence,
            policy_version=COMMIT_POLICY_VERSION, committed_at=when,
        )

    after_hash = file_sha256(canonical_database)
    return ControlledCommitResult(
        mode="COMMIT", draft_id=draft_id, target_place_id=str(target), result="committed",
        reason="approved evidence and canonical revisions committed atomically; publication not performed",
        changed_fields=tuple(r.changed_fields[0] for r in revisions),
        blocked_fields=tuple(sorted(set(blocked_fields))),
        evidence_ids=tuple(receipt.get("evidence_ids") or ()),
        revision_ids=tuple(receipt.get("revision_ids") or ()),
        canonical_hash_before=before_hash, canonical_hash_after=after_hash,
    )
