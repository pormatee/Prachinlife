"""Phase 2V.1 controlled canonical-adoption dry-run.

Approved admin drafts are evaluated against existing canonical evidence and the
existing verification/adoption policies.  The dry-run is deliberately read-only:
it never inserts evidence, mutates canonical places, writes revisions, publishes,
or regenerates exports.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping
import shutil
import tempfile

from .admin_drafts import AdminDraftStatus, AdminDraftStore
from .adoption import ADOPTABLE_FIELDS, AdoptionOutcome, AdoptionPolicy, propose_adoption
from .contracts import EvidenceStatus, GeoPoint, SourceRef, SourceType
from .models import EvidenceKind, PlaceEvidence, PlaceLifecycle
from .sqlite_store import SQLitePlaceRepository
from .verification import VerificationPolicy, verify_field

DRY_RUN_POLICY_VERSION = "2V.1-dry-run-v1"


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decode_value(value: Any) -> Any:
    if isinstance(value, Mapping) and set(value) >= {"latitude", "longitude"}:
        return GeoPoint(float(value["latitude"]), float(value["longitude"]))
    return value


def _stable_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _operator_change_keys(item: Mapping[str, Any]) -> set[tuple[str, str]]:
    payload = item.get("payload") or {}
    review = payload.get("review_context") or {}
    changes = review.get("operator_changes") or []
    keys: set[tuple[str, str]] = set()
    for change in changes:
        if not isinstance(change, Mapping):
            continue
        field_name = str(change.get("field_name") or "").strip()
        if not field_name:
            continue
        keys.add((field_name, _stable_value(change.get("value"))))
    return keys


def _draft_evidence(item: Mapping[str, Any]) -> tuple[PlaceEvidence, ...]:
    evidence: list[PlaceEvidence] = []
    operator_keys = _operator_change_keys(item)
    draft_id = str(item.get("draft_id") or "")
    for raw in item.get("evidence") or ():
        source_raw = raw.get("source") or {}
        field_name = str(raw.get("field_name") or "")
        is_operator_change = (field_name, _stable_value(raw.get("value"))) in operator_keys
        from datetime import datetime
        observed_at = datetime.fromisoformat(str(raw["observed_at"]).replace("Z", "+00:00"))
        source_observed = datetime.fromisoformat(
            str(source_raw.get("observed_at") or raw["observed_at"]).replace("Z", "+00:00")
        )
        value = _decode_value(raw.get("value"))
        if raw.get("field_name") == "categories" and isinstance(value, list):
            value = tuple(value)
        if raw.get("field_name") == "lifecycle" and isinstance(value, str):
            value = PlaceLifecycle(value)
        metadata = dict(raw.get("metadata") or {})
        if is_operator_change:
            metadata.update({
                "provenance_origin": "operator_change",
                "admin_draft_id": draft_id,
                "underlying_seed_source_type": str(source_raw.get("source_type") or "manual"),
                "underlying_seed_source_name": str(source_raw.get("source_name") or item.get("source_name") or "Admin"),
                "underlying_seed_source_url": source_raw.get("source_url") or item.get("source_url"),
            })
            source = SourceRef(
                source_type=SourceType.MANUAL,
                source_name="PrachinLife Admin Operator",
                source_record_id=(f"admin-draft:{draft_id}:{field_name}" if draft_id else None),
                source_url=None,
                observed_at=source_observed,
            )
        else:
            metadata.setdefault("provenance_origin", "seed_or_declared_source")
            source = SourceRef(
                source_type=SourceType(str(source_raw.get("source_type") or "manual")),
                source_name=str(source_raw.get("source_name") or item.get("source_name") or "Admin"),
                source_record_id=source_raw.get("source_record_id"),
                source_url=source_raw.get("source_url") or item.get("source_url"),
                observed_at=source_observed,
            )
        evidence.append(
            PlaceEvidence(
                evidence_id=str(raw["evidence_id"]),
                place_id=str(raw["place_id"]),
                source=source,
                kind=EvidenceKind(str(raw.get("kind") or "other")),
                field_name=field_name,
                value=value,
                status=EvidenceStatus(str(raw.get("status") or "candidate")),
                observed_at=observed_at,
                metadata=metadata,
            )
        )
    return tuple(evidence)


@dataclass(frozen=True)
class FieldDryRun:
    field_name: str
    current_value: Any
    proposed_value: Any
    verification_outcome: str
    adoption_outcome: str
    reason: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class DraftDryRun:
    draft_id: str
    operation: str
    target_place_id: str | None
    status: str
    result: str
    fields: tuple[FieldDryRun, ...]
    blocked_fields: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ControlledAdoptionReport:
    mode: str
    policy_version: str
    canonical_hash_before: str
    canonical_hash_after: str
    canonical_unchanged: bool
    draft_hash_before: str | None
    draft_hash_after: str | None
    draft_unchanged: bool
    approved_groups: int
    adoptable_drafts: int
    blocked_drafts: int
    proposed_field_changes: int
    blocked_field_changes: int
    drafts: tuple[DraftDryRun, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _underlying_source_key(evidence: PlaceEvidence) -> tuple[str, str]:
    source = evidence.source
    return (
        (source.source_url or "").strip().casefold(),
        source.source_name.strip().casefold(),
    )


def build_controlled_adoption_dry_run(
    *,
    canonical_database: str | Path,
    draft_database: str | Path,
    verification_policy: VerificationPolicy = VerificationPolicy(),
    adoption_policy: AdoptionPolicy = AdoptionPolicy(),
) -> ControlledAdoptionReport:
    canonical_database = Path(canonical_database)
    before_hash = file_sha256(canonical_database)
    draft_database = Path(draft_database)
    draft_hash_before = file_sha256(draft_database) if draft_database.exists() else None
    draft_results: list[DraftDryRun] = []

    # SQLitePlaceRepository initializes schema metadata on open. Evaluate on a
    # temporary copy so a dry-run is byte-for-byte read-only on the real DB.
    with tempfile.TemporaryDirectory(prefix="prachinlife-2v1-") as temp_dir:
        temp_canonical = Path(temp_dir) / "canonical.sqlite3"
        temp_drafts = Path(temp_dir) / "drafts.sqlite3"
        shutil.copy2(canonical_database, temp_canonical)
        if draft_database.exists():
            shutil.copy2(draft_database, temp_drafts)
        with AdminDraftStore(temp_drafts) as drafts, SQLitePlaceRepository(temp_canonical) as repo:
            approved = drafts.list_review_groups(AdminDraftStatus.APPROVED, limit=10000)
            for item in approved:
                operation = str(item["operation"])
                target = item.get("target_place_id")
                if operation != "update_place_candidate" or not target:
                    draft_results.append(
                        DraftDryRun(
                            draft_id=str(item["draft_id"]), operation=operation, target_place_id=target,
                            status=str(item["status"]), result="blocked", fields=(), blocked_fields=(),
                            reason="new-place canonical creation is outside Phase 2V.1 dry-run scope",
                        )
                    )
                    continue
                place = repo.get_place(str(target))
                if place is None:
                    draft_results.append(
                        DraftDryRun(
                            draft_id=str(item["draft_id"]), operation=operation, target_place_id=str(target),
                            status=str(item["status"]), result="blocked", fields=(), blocked_fields=(),
                            reason="target canonical place does not exist",
                        )
                    )
                    continue

                draft_evidence = _draft_evidence(item)
                stored_evidence = repo.list_evidence(str(target))
                # An admin transcription of an already-stored source must not
                # manufacture a second independent source merely because its
                # SourceType is MANUAL. Deduplicate by underlying URL+name.
                draft_source_keys = {_underlying_source_key(e) for e in draft_evidence}
                independent_stored = tuple(
                    e for e in stored_evidence if _underlying_source_key(e) not in draft_source_keys
                )
                combined_evidence = (*independent_stored, *draft_evidence)

                fields: list[FieldDryRun] = []
                blocked_fields: list[str] = []
                for evidence_item in draft_evidence:
                    field = evidence_item.field_name
                    if field not in ADOPTABLE_FIELDS:
                        blocked_fields.append(field)
                        continue
                    verification = verify_field(
                        place_id=str(target), field_name=field,
                        evidence=combined_evidence, policy=verification_policy,
                    )
                    proposal = propose_adoption(
                        place=place, verification=verification, policy=adoption_policy,
                        evidence_ids=tuple(e.evidence_id for e in combined_evidence if e.field_name == field),
                    )
                    fields.append(
                        FieldDryRun(
                            field_name=field,
                            current_value=getattr(place, field),
                            proposed_value=evidence_item.value,
                            verification_outcome=verification.outcome.value,
                            adoption_outcome=proposal.outcome.value,
                            reason=proposal.reason,
                            evidence_ids=proposal.evidence_ids,
                        )
                    )
                proposed = sum(1 for f in fields if f.adoption_outcome == AdoptionOutcome.PROPOSED.value)
                draft_results.append(
                    DraftDryRun(
                        draft_id=str(item["draft_id"]), operation=operation, target_place_id=str(target),
                        status=str(item["status"]), result="adoptable" if proposed else "blocked",
                        fields=tuple(fields), blocked_fields=tuple(sorted(set(blocked_fields))),
                        reason=("dry-run produced canonical adoption proposals" if proposed
                                else "no field satisfies canonical adoption policy"),
                    )
                )

    after_hash = file_sha256(canonical_database)
    draft_hash_after = file_sha256(draft_database) if draft_database.exists() else None
    proposed_fields = sum(
        1 for draft in draft_results for field in draft.fields
        if field.adoption_outcome == AdoptionOutcome.PROPOSED.value
    )
    blocked_fields = sum(
        len(draft.blocked_fields)
        + sum(1 for field in draft.fields if field.adoption_outcome == AdoptionOutcome.BLOCKED.value)
        for draft in draft_results
    )
    return ControlledAdoptionReport(
        mode="DRY_RUN",
        policy_version=DRY_RUN_POLICY_VERSION,
        canonical_hash_before=before_hash,
        canonical_hash_after=after_hash,
        canonical_unchanged=before_hash == after_hash,
        draft_hash_before=draft_hash_before,
        draft_hash_after=draft_hash_after,
        draft_unchanged=draft_hash_before == draft_hash_after,
        approved_groups=len(draft_results),
        adoptable_drafts=sum(1 for draft in draft_results if draft.result == "adoptable"),
        blocked_drafts=sum(1 for draft in draft_results if draft.result == "blocked"),
        proposed_field_changes=proposed_fields,
        blocked_field_changes=blocked_fields,
        drafts=tuple(draft_results),
    )

def report_json(report: ControlledAdoptionReport) -> str:
    def encode(value: Any) -> Any:
        if isinstance(value, GeoPoint):
            return {"latitude": value.latitude, "longitude": value.longitude}
        if isinstance(value, PlaceLifecycle):
            return value.value
        if isinstance(value, tuple):
            return list(value)
        raise TypeError(type(value).__name__)
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=encode)
