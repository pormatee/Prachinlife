"""Phase 2V.3 controlled adoption for approved create_place_candidate drafts.

New canonical creation is deliberately stricter than draft approval alone:
- the latest review-group version must be APPROVED;
- deterministic entity resolution must classify the candidate as NEW;
- required identity fields must have active source support;
- commit is atomic and records evidence, a creation revision, an idempotency
  receipt, and a structured resolution audit;
- publication/export is never performed here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from typing import Any, Mapping
from uuid import uuid4

from .admin_drafts import AdminDraftStatus, AdminDraftStore
from .adoption import ADOPTABLE_FIELDS, PlaceRevision
from .contracts import GeoPoint, SourcePlaceCandidate
from .controlled_adoption import _draft_evidence, file_sha256
from .discovery_readonly import load_canonical_places_readonly
from .discovery_resolution import CanonicalResolutionOrchestrator, DiscoveryResolutionOutcome, canonical_observation
from .entity_resolution import EntityResolutionEngine, ResolutionOutcome
from .ingestion import IngestionObservation, build_claims, normalize_candidate
from .models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from .sqlite_store import SQLitePlaceRepository
from .verification import VerificationOutcome, VerificationPolicy, verify_field

CREATE_POLICY_VERSION = "2V.3-create-candidate-v1"
REQUIRED_CREATE_FIELDS = ("canonical_name", "location", "province", "categories")
CANONICAL_CREATE_FIELDS = tuple(sorted(ADOPTABLE_FIELDS))


@dataclass(frozen=True)
class CreateFieldAssessment:
    field_name: str
    verification_outcome: str
    selected_value: Any
    required: bool
    acceptable: bool
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class CreateCandidateAssessment:
    mode: str
    policy_version: str
    draft_id: str
    candidate_place_id: str | None
    result: str
    reason: str
    resolution_outcome: str | None
    resolution_reason: str | None
    comparison_count: int
    fields: tuple[CreateFieldAssessment, ...]
    missing_required_fields: tuple[str, ...]
    noncanonical_evidence_fields: tuple[str, ...]
    canonical_hash_before: str
    canonical_hash_after: str
    canonical_unchanged: bool
    target_place_id: str | None = None
    exact_match_count: int = 0
    review_candidate_count: int = 0
    publication_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CreateCandidateCommitResult:
    mode: str
    policy_version: str
    draft_id: str
    place_id: str | None
    result: str
    reason: str
    resolution_outcome: str | None
    comparison_count: int
    changed_fields: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    revision_ids: tuple[str, ...]
    canonical_hash_before: str
    canonical_hash_after: str
    publication_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _latest_approved_create(store: AdminDraftStore, draft_id: str) -> dict[str, Any] | None:
    for item in store.list_review_groups(AdminDraftStatus.APPROVED, limit=10000):
        if str(item.get("draft_id")) == draft_id and item.get("operation") == "create_place_candidate":
            return item
    return None


def _value_by_field(evidence) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in evidence:
        if item.field_name in values and values[item.field_name] != item.value:
            # Conflicting values from one draft are unsafe even before normal verification.
            raise ValueError(f"draft contains conflicting values for {item.field_name}")
        values[item.field_name] = item.value
    return values


def _candidate_observation(item: Mapping[str, Any], evidence) -> IngestionObservation:
    values = _value_by_field(evidence)
    name = values.get("canonical_name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("create candidate requires canonical_name evidence")
    categories = values.get("categories") or ()
    if isinstance(categories, list):
        categories = tuple(categories)
    source = evidence[0].source if evidence else None
    if source is None:
        raise ValueError("create candidate requires evidence")
    candidate = normalize_candidate(
        SourcePlaceCandidate(
            source=source,
            name=name,
            location=values.get("location"),
            address_text=values.get("address_text"),
            province=values.get("province"),
            categories=tuple(categories),
            phone=values.get("phone"),
            website=values.get("website"),
            raw_attributes={
                "intake": "admin_approved_create_candidate",
                "draft_id": str(item["draft_id"]),
            },
        )
    )
    return IngestionObservation(candidate=candidate, claims=build_claims(candidate))


def _assess_fields(place_id: str, evidence, policy: VerificationPolicy) -> tuple[tuple[CreateFieldAssessment, ...], tuple[str, ...], tuple[str, ...]]:
    fields: list[CreateFieldAssessment] = []
    missing: list[str] = []
    present = {item.field_name for item in evidence}
    noncanonical = tuple(sorted(present - ADOPTABLE_FIELDS))

    for field_name in CANONICAL_CREATE_FIELDS:
        if field_name not in present:
            if field_name in REQUIRED_CREATE_FIELDS:
                missing.append(field_name)
            continue
        verification = verify_field(
            place_id=place_id,
            field_name=field_name,
            evidence=evidence,
            policy=policy,
        )
        acceptable = verification.outcome in {
            VerificationOutcome.SUPPORTED,
            VerificationOutcome.VERIFIED,
        }
        if field_name in REQUIRED_CREATE_FIELDS and not acceptable:
            missing.append(field_name)
        fields.append(
            CreateFieldAssessment(
                field_name=field_name,
                verification_outcome=verification.outcome.value,
                selected_value=verification.selected_value,
                required=field_name in REQUIRED_CREATE_FIELDS,
                acceptable=acceptable,
                evidence_ids=tuple(
                    item.evidence_id for item in evidence if item.field_name == field_name
                ),
            )
        )
    return tuple(fields), tuple(sorted(set(missing))), noncanonical


def _classify_existing_matches(observation: IngestionObservation, canonical_places):
    engine = EntityResolutionEngine()
    same: list[str] = []
    review: list[str] = []
    for place in sorted(canonical_places, key=lambda x: x.identity.place_id):
        decision = engine.compare(observation, canonical_observation(place))
        if decision.outcome is ResolutionOutcome.SAME_ENTITY:
            same.append(place.identity.place_id)
        elif decision.outcome is ResolutionOutcome.REVIEW:
            review.append(place.identity.place_id)
    return tuple(same), tuple(review)


def assess_approved_create_candidate(
    *,
    canonical_database: str | Path,
    draft_database: str | Path,
    draft_id: str,
    verification_policy: VerificationPolicy = VerificationPolicy(),
) -> CreateCandidateAssessment:
    """Read-only Phase 2V.3 gate for one approved create-place draft."""
    canonical_database = Path(canonical_database)
    before_hash = file_sha256(canonical_database)
    with AdminDraftStore(draft_database) as drafts:
        item = _latest_approved_create(drafts, draft_id)
        if item is None:
            raise ValueError("draft must be the latest approved create_place_candidate version")
        candidate_place_id = str(item.get("candidate_place_id") or "")
        if not candidate_place_id:
            raise ValueError("approved create candidate has no candidate_place_id")
        evidence = _draft_evidence(item)

    observation = _candidate_observation(item, evidence)
    canonical_places = load_canonical_places_readonly(canonical_database)
    resolution = CanonicalResolutionOrchestrator().resolve_one(observation, canonical_places)
    same_ids, review_ids = _classify_existing_matches(observation, canonical_places)
    fields, missing, noncanonical = _assess_fields(candidate_place_id, evidence, verification_policy)

    target_place_id = same_ids[0] if len(same_ids) == 1 else None
    if len(same_ids) == 1:
        result = "reconcilable_existing"
        reason = "one deterministic SAME_ENTITY canonical match; reconcile provenance without creating or overwriting canonical fields"
        effective_outcome = DiscoveryResolutionOutcome.MATCHED.value
        effective_reason = "one deterministic same-entity canonical match; nearby review candidates retained in audit"
    elif len(same_ids) > 1:
        result = "blocked_duplicate_or_review"
        reason = "multiple deterministic SAME_ENTITY canonical matches require manual review"
        effective_outcome = DiscoveryResolutionOutcome.REVIEW.value
        effective_reason = "multiple deterministic canonical matches"
    elif resolution.outcome is not DiscoveryResolutionOutcome.NEW:
        result = "blocked_duplicate_or_review"
        reason = "entity resolution did not classify candidate as NEW"
        effective_outcome = resolution.outcome.value
        effective_reason = resolution.reason
    elif missing:
        result = "blocked_verification"
        reason = "required canonical creation fields lack supported evidence"
        effective_outcome = resolution.outcome.value
        effective_reason = resolution.reason
    else:
        result = "adoptable"
        reason = "approved candidate is NEW and required identity fields are supported"
        effective_outcome = resolution.outcome.value
        effective_reason = resolution.reason

    after_hash = file_sha256(canonical_database)
    return CreateCandidateAssessment(
        mode="DRY_RUN",
        policy_version=CREATE_POLICY_VERSION,
        draft_id=draft_id,
        candidate_place_id=candidate_place_id,
        result=result,
        reason=reason,
        resolution_outcome=effective_outcome,
        resolution_reason=effective_reason,
        comparison_count=resolution.comparison_count,
        fields=fields,
        missing_required_fields=missing,
        noncanonical_evidence_fields=noncanonical,
        canonical_hash_before=before_hash,
        canonical_hash_after=after_hash,
        canonical_unchanged=before_hash == after_hash,
        target_place_id=target_place_id,
        exact_match_count=len(same_ids),
        review_candidate_count=len(review_ids),
    )


def _canonical_from_assessment(
    *, place_id: str, fields: tuple[CreateFieldAssessment, ...], created_at: datetime
) -> CanonicalPlace:
    selected = {
        field.field_name: field.selected_value
        for field in fields
        if field.acceptable and field.selected_value is not None
    }
    categories = selected.get("categories") or ()
    if isinstance(categories, list):
        categories = tuple(categories)
    lifecycle = selected.get("lifecycle", PlaceLifecycle.UNKNOWN)
    if not isinstance(lifecycle, PlaceLifecycle):
        lifecycle = PlaceLifecycle(str(lifecycle))
    return CanonicalPlace(
        identity=PlaceIdentity(place_id),
        canonical_name=str(selected["canonical_name"]),
        location=selected.get("location"),
        address_text=selected.get("address_text"),
        province=selected.get("province"),
        categories=tuple(categories),
        phone=selected.get("phone"),
        website=selected.get("website"),
        lifecycle=lifecycle,
        created_at=created_at,
        updated_at=created_at,
    )


def _admin_receipt_readonly(database: Path, draft_id: str) -> dict[str, Any] | None:
    uri = f"file:{database.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='admin_adoption_receipts'"
        ).fetchone()
        if table is None:
            return None
        row = connection.execute(
            "SELECT * FROM admin_adoption_receipts WHERE draft_id = ?", (draft_id,)
        ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["revision_ids"] = tuple(json.loads(item.pop("revision_ids_json")))
        item["evidence_ids"] = tuple(json.loads(item.pop("evidence_ids_json")))
        return item
    finally:
        connection.close()


def _rebind_evidence_to_existing(evidence, *, target_place_id: str, candidate_place_id: str, draft_id: str):
    rebound = []
    for item in evidence:
        metadata = dict(item.metadata)
        metadata.update({
            "admin_candidate_original_place_id": candidate_place_id,
            "admin_candidate_draft_id": draft_id,
            "admin_candidate_reconciliation": "deterministic_same_entity",
        })
        rebound.append(type(item)(
            evidence_id=item.evidence_id,
            place_id=target_place_id,
            source=item.source,
            kind=item.kind,
            field_name=item.field_name,
            value=item.value,
            status=item.status,
            observed_at=item.observed_at,
            metadata=metadata,
        ))
    return tuple(rebound)


def commit_approved_create_candidate(
    *,
    canonical_database: str | Path,
    draft_database: str | Path,
    draft_id: str,
    verification_policy: VerificationPolicy = VerificationPolicy(),
    committed_at: datetime | None = None,
) -> CreateCandidateCommitResult:
    canonical_database = Path(canonical_database)
    before_hash = file_sha256(canonical_database)
    when = committed_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError("committed_at must be timezone-aware")

    # Fast idempotency check must be byte-for-byte read-only. SQLitePlaceRepository
    # initializes schema metadata on open, so preflight uses a read-only URI.
    existing = _admin_receipt_readonly(canonical_database, draft_id)
    if existing is not None:
        after_hash = file_sha256(canonical_database)
        return CreateCandidateCommitResult(
            mode="COMMIT", policy_version=CREATE_POLICY_VERSION, draft_id=draft_id,
            place_id=existing["place_id"], result="already_committed",
            reason="idempotent adoption receipt already exists", resolution_outcome=None,
            comparison_count=0, changed_fields=(), evidence_ids=tuple(existing["evidence_ids"]),
            revision_ids=tuple(existing["revision_ids"]), canonical_hash_before=before_hash,
            canonical_hash_after=after_hash,
        )

    assessment = assess_approved_create_candidate(
        canonical_database=canonical_database,
        draft_database=draft_database,
        draft_id=draft_id,
        verification_policy=verification_policy,
    )
    if assessment.result == "reconcilable_existing":
        target_place_id = str(assessment.target_place_id or "")
        if not target_place_id:
            raise ValueError("reconciliation target is missing")
        with AdminDraftStore(draft_database) as drafts:
            item = _latest_approved_create(drafts, draft_id)
            if item is None:
                raise ValueError("draft approval changed before commit")
            original_evidence = _draft_evidence(item)
        rebound = _rebind_evidence_to_existing(
            original_evidence, target_place_id=target_place_id,
            candidate_place_id=str(assessment.candidate_place_id), draft_id=draft_id,
        )
        audit = {
            "draft_id": draft_id,
            "operation": "create_place_candidate",
            "candidate_place_id": assessment.candidate_place_id,
            "resolved_existing_place_id": target_place_id,
            "resolution_outcome": "matched",
            "resolution_reason": assessment.resolution_reason,
            "comparison_count": assessment.comparison_count,
            "exact_match_count": assessment.exact_match_count,
            "review_candidate_count": assessment.review_candidate_count,
            "action": "reconcile_evidence_only",
            "canonical_field_overwrite": False,
            "publication_performed": False,
        }
        with SQLitePlaceRepository(canonical_database) as repo:
            receipt = repo.commit_admin_candidate_reconciliation(
                draft_id=draft_id, place_id=target_place_id, evidence=rebound,
                policy_version=CREATE_POLICY_VERSION, decision=audit, committed_at=when,
            )
        after_hash = file_sha256(canonical_database)
        return CreateCandidateCommitResult(
            mode="COMMIT", policy_version=CREATE_POLICY_VERSION, draft_id=draft_id,
            place_id=target_place_id, result="reconciled_existing",
            reason="approved create candidate reconciled to deterministic existing canonical; evidence and audit preserved without canonical field overwrite",
            resolution_outcome="matched", comparison_count=assessment.comparison_count,
            changed_fields=(), evidence_ids=tuple(receipt.get("evidence_ids") or ()),
            revision_ids=tuple(receipt.get("revision_ids") or ()),
            canonical_hash_before=before_hash, canonical_hash_after=after_hash,
        )

    if assessment.result != "adoptable":
        after_hash = file_sha256(canonical_database)
        return CreateCandidateCommitResult(
            mode="COMMIT", policy_version=CREATE_POLICY_VERSION, draft_id=draft_id,
            place_id=assessment.candidate_place_id, result="blocked", reason=assessment.reason,
            resolution_outcome=assessment.resolution_outcome,
            comparison_count=assessment.comparison_count, changed_fields=(), evidence_ids=(),
            revision_ids=(), canonical_hash_before=before_hash, canonical_hash_after=after_hash,
        )

    with AdminDraftStore(draft_database) as drafts:
        item = _latest_approved_create(drafts, draft_id)
        if item is None:
            raise ValueError("draft approval changed before commit")
        evidence = _draft_evidence(item)
    place_id = str(assessment.candidate_place_id)
    if any(item.place_id != place_id for item in evidence):
        raise ValueError("draft evidence place_id does not match candidate_place_id")

    place = _canonical_from_assessment(place_id=place_id, fields=assessment.fields, created_at=when)
    selected_fields = tuple(
        field.field_name for field in assessment.fields
        if field.acceptable and field.selected_value is not None
    )
    before_values = {
        field: (() if field == "categories" else None) for field in selected_fields
    }
    after_values = {field: getattr(place, field) for field in selected_fields}
    canonical_evidence_ids = tuple(
        evidence_id
        for field in assessment.fields if field.field_name in selected_fields
        for evidence_id in field.evidence_ids
    )
    revision = PlaceRevision(
        revision_id=str(uuid4()),
        place_id=place_id,
        changed_fields=selected_fields,
        before_values=before_values,
        after_values=after_values,
        reason=(
            f"canonical created from approved admin draft {draft_id}; "
            f"entity resolution={assessment.resolution_outcome}; comparisons={assessment.comparison_count}; "
            "publication disabled"
        ),
        evidence_ids=canonical_evidence_ids,
        policy_version=CREATE_POLICY_VERSION,
        created_at=when,
    )
    audit = {
        "draft_id": draft_id,
        "operation": "create_place_candidate",
        "candidate_place_id": place_id,
        "resolution_outcome": assessment.resolution_outcome,
        "resolution_reason": assessment.resolution_reason,
        "comparison_count": assessment.comparison_count,
        "required_fields": list(REQUIRED_CREATE_FIELDS),
        "field_assessments": [asdict(field) for field in assessment.fields],
        "noncanonical_evidence_fields": list(assessment.noncanonical_evidence_fields),
        "publication_performed": False,
    }
    with SQLitePlaceRepository(canonical_database) as repo:
        receipt = repo.commit_admin_candidate_creation(
            draft_id=draft_id,
            place=place,
            revision=revision,
            evidence=evidence,
            policy_version=CREATE_POLICY_VERSION,
            decision=audit,
            committed_at=when,
        )

    after_hash = file_sha256(canonical_database)
    return CreateCandidateCommitResult(
        mode="COMMIT", policy_version=CREATE_POLICY_VERSION, draft_id=draft_id,
        place_id=place_id, result="committed",
        reason="canonical place, evidence, creation revision, receipt, and resolution audit committed atomically; publication not performed",
        resolution_outcome=assessment.resolution_outcome,
        comparison_count=assessment.comparison_count, changed_fields=selected_fields,
        evidence_ids=tuple(receipt.get("evidence_ids") or ()),
        revision_ids=tuple(receipt.get("revision_ids") or ()),
        canonical_hash_before=before_hash, canonical_hash_after=after_hash,
    )
