"""Phase 2U.1 admin evidence-draft persistence.

This store is intentionally separate from the canonical Place Platform database.
Admin submissions are validated into CANDIDATE evidence-shaped records and held
in a pending-review queue.  No canonical place, canonical evidence table,
revision, publication record, or export is mutated here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping
from uuid import uuid4

from .admin_fields import AdminEvidenceInput, build_admin_evidence
from .contracts import GeoPoint
from .models import PlaceEvidence, PlaceLifecycle
from .merchant_foundation import MerchantContentDraft, MerchantMode, SponsorEntitlement


DRAFT_SCHEMA_VERSION = "2U.3.3.2-v1"
ALLOWED_OPERATIONS = frozenset({"update_place_candidate", "create_place_candidate"})


class AdminDraftStatus:
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class PersistedAdminDraft:
    draft_id: str
    operation: str
    status: str
    target_place_id: str | None
    candidate_place_id: str
    source_name: str
    source_url: str
    changes_count: int
    created_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    if isinstance(value, GeoPoint):
        return {"latitude": value.latitude, "longitude": value.longitude}
    if isinstance(value, PlaceLifecycle):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _evidence_payload(evidence: PlaceEvidence) -> dict[str, Any]:
    return {
        "evidence_id": evidence.evidence_id,
        "place_id": evidence.place_id,
        "field_name": evidence.field_name,
        "kind": evidence.kind.value,
        "value": _jsonable(evidence.value),
        "status": evidence.status.value,
        "source": {
            "source_type": evidence.source.source_type.value,
            "source_name": evidence.source.source_name,
            "source_record_id": evidence.source.source_record_id,
            "source_url": evidence.source.source_url,
            "observed_at": evidence.source.observed_at.isoformat(),
        },
        "observed_at": evidence.observed_at.isoformat(),
        "metadata": dict(evidence.metadata),
    }



def _normalize_subject_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _changes_map(payload: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    changes = payload.get("changes") or []
    if not isinstance(changes, list):
        return result
    for change in changes:
        if isinstance(change, Mapping) and change.get("field_name"):
            result[str(change["field_name"])] = _jsonable(change.get("value"))
    return result


def _draft_subject_key(
    *,
    operation: str,
    target_place_id: str | None,
    payload: Mapping[str, Any],
    source_url: str,
) -> str:
    """Stable logical-place key used only by the admin draft queue.

    Canonical updates group by canonical place_id. New-place candidates have no
    canonical id yet, so use source URL + proposed name/province as a safe,
    deterministic review identity. This does not create or mutate canonical ids.
    """
    if operation == "update_place_candidate" and target_place_id:
        return f"canonical:{target_place_id}"
    changes = _changes_map(payload)
    name = changes.get("canonical_name") or payload.get("current_place_name") or ""
    province = changes.get("province") or ""
    return "candidate:" + "|".join(
        (_normalize_subject_text(source_url), _normalize_subject_text(name), _normalize_subject_text(province))
    )


def _version_diff(previous_payload: Mapping[str, Any] | None, current_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    previous = _changes_map(previous_payload or {})
    current = _changes_map(current_payload)
    diff: list[dict[str, Any]] = []
    for field_name in sorted(set(previous) | set(current)):
        before = previous.get(field_name)
        after = current.get(field_name)
        if before == after:
            continue
        if field_name not in previous:
            kind = "added"
        elif field_name not in current:
            kind = "removed"
        else:
            kind = "changed"
        diff.append({"field_name": field_name, "kind": kind, "before": before, "after": after})
    return diff


class AdminDraftStore:
    """SQLite queue for admin drafts, separate from the canonical DB."""

    def __init__(self, database: str | Path) -> None:
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path))
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS admin_evidence_drafts (
                draft_id TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                operation TEXT NOT NULL,
                status TEXT NOT NULL,
                target_place_id TEXT,
                candidate_place_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_admin_drafts_status
                ON admin_evidence_drafts(status, created_at);
            """
        )
        columns = {row[1] for row in self._connection.execute("PRAGMA table_info(admin_evidence_drafts)")}
        if "review_note" not in columns:
            self._connection.execute("ALTER TABLE admin_evidence_drafts ADD COLUMN review_note TEXT")
        if "reviewed_at" not in columns:
            self._connection.execute("ALTER TABLE admin_evidence_drafts ADD COLUMN reviewed_at TEXT")
        self._connection.commit()
        # Repair historical queue state from pre-2U.3.3.2 versions. Older
        # pending drafts that already have a later reviewed version are not
        # actionable anymore; keep them for audit but mark them superseded.
        self._reconcile_superseded_pending()

    def _all_review_items(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT draft_id, operation, status, target_place_id, candidate_place_id,
                   source_name, source_url, payload_json, evidence_json, created_at,
                   updated_at, review_note, reviewed_at
            FROM admin_evidence_drafts
            ORDER BY created_at ASC, draft_id ASC
            """
        ).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            item["evidence"] = json.loads(item.pop("evidence_json"))
            item["changes_count"] = len(item["evidence"])
            item["draft_subject_key"] = self._subject_key_for_item(item)
            items.append(item)
        return items

    def _reconcile_superseded_pending(self) -> int:
        """Close stale pending versions that are older than a reviewed version.

        This is a queue-state repair only. Rows are retained for audit; no
        canonical data or publication state is touched. A newer pending draft
        created after an approval/rejection remains actionable.
        """
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in self._all_review_items():
            groups.setdefault(item["draft_subject_key"], []).append(item)

        stale_ids: list[str] = []
        for versions in groups.values():
            latest_reviewed_index = -1
            for index, item in enumerate(versions):
                if item["status"] in {AdminDraftStatus.APPROVED, AdminDraftStatus.REJECTED}:
                    latest_reviewed_index = index
            if latest_reviewed_index < 0:
                continue
            stale_ids.extend(
                item["draft_id"]
                for index, item in enumerate(versions)
                if index < latest_reviewed_index
                and item["status"] == AdminDraftStatus.PENDING_REVIEW
            )

        if not stale_ids:
            return 0
        now = _now_iso()
        self._connection.executemany(
            """
            UPDATE admin_evidence_drafts
            SET status = ?, updated_at = ?
            WHERE draft_id = ? AND status = ?
            """,
            [
                (AdminDraftStatus.SUPERSEDED, now, draft_id, AdminDraftStatus.PENDING_REVIEW)
                for draft_id in stale_ids
            ],
        )
        self._connection.commit()
        return len(stale_ids)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def insert(
        self,
        *,
        draft_id: str,
        operation: str,
        target_place_id: str | None,
        candidate_place_id: str,
        source_name: str,
        source_url: str,
        payload: Mapping[str, Any],
        evidence: list[Mapping[str, Any]],
    ) -> PersistedAdminDraft:
        now = _now_iso()
        self._connection.execute(
            """
            INSERT INTO admin_evidence_drafts(
                draft_id, schema_version, operation, status, target_place_id,
                candidate_place_id, source_name, source_url, payload_json,
                evidence_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                DRAFT_SCHEMA_VERSION,
                operation,
                AdminDraftStatus.PENDING_REVIEW,
                target_place_id,
                candidate_place_id,
                source_name,
                source_url,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                now,
                now,
            ),
        )
        self._connection.commit()
        return PersistedAdminDraft(
            draft_id=draft_id,
            operation=operation,
            status=AdminDraftStatus.PENDING_REVIEW,
            target_place_id=target_place_id,
            candidate_place_id=candidate_place_id,
            source_name=source_name,
            source_url=source_url,
            changes_count=len(evidence),
            created_at=now,
        )

    def list_pending(self, limit: int = 100) -> tuple[dict[str, Any], ...]:
        rows = self._connection.execute(
            """
            SELECT draft_id, operation, status, target_place_id, candidate_place_id,
                   source_name, source_url, created_at, updated_at,
                   json_array_length(evidence_json) AS changes_count
            FROM admin_evidence_drafts
            WHERE status = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (AdminDraftStatus.PENDING_REVIEW, int(limit)),
        ).fetchall()
        return tuple(dict(row) for row in rows)

    def count(self) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) AS n FROM admin_evidence_drafts"
        ).fetchone()
        return int(row["n"])


    def find_pending_duplicate(
        self,
        *,
        operation: str,
        target_place_id: str | None,
        source_name: str,
        source_url: str,
        payload: Mapping[str, Any],
    ) -> PersistedAdminDraft | None:
        """Return an identical pending draft instead of inserting it twice.

        Server-generated fields such as candidate_place_id/status are ignored.  This
        protects the mobile Admin UI from accidental double taps / resubmits while
        preserving independently reviewed drafts.
        """
        wanted = {
            "operation": operation,
            "place_id": target_place_id,
            "source": {"source_name": source_name, "source_url": source_url},
            "note": str(payload.get("note") or "").strip(),
            "changes": payload.get("changes") or [],
        }
        rows = self._connection.execute(
            """
            SELECT draft_id, operation, status, target_place_id, candidate_place_id,
                   source_name, source_url, payload_json, evidence_json, created_at
            FROM admin_evidence_drafts
            WHERE status = ? AND operation = ?
              AND COALESCE(target_place_id, '') = COALESCE(?, '')
              AND source_name = ? AND source_url = ?
            ORDER BY created_at DESC
            """,
            (AdminDraftStatus.PENDING_REVIEW, operation, target_place_id, source_name, source_url),
        ).fetchall()
        for row in rows:
            saved = json.loads(row["payload_json"])
            have = {
                "operation": saved.get("operation"),
                "place_id": saved.get("place_id"),
                "source": {
                    "source_name": (saved.get("source") or {}).get("source_name"),
                    "source_url": (saved.get("source") or {}).get("source_url"),
                },
                "note": str(saved.get("note") or "").strip(),
                "changes": saved.get("changes") or [],
            }
            if have == wanted:
                evidence = json.loads(row["evidence_json"])
                return PersistedAdminDraft(
                    draft_id=row["draft_id"], operation=row["operation"], status=row["status"],
                    target_place_id=row["target_place_id"], candidate_place_id=row["candidate_place_id"],
                    source_name=row["source_name"], source_url=row["source_url"],
                    changes_count=len(evidence), created_at=row["created_at"],
                )
        return None

    def list_for_review(self, status: str = AdminDraftStatus.PENDING_REVIEW, limit: int = 100) -> tuple[dict[str, Any], ...]:
        if status not in {AdminDraftStatus.PENDING_REVIEW, AdminDraftStatus.APPROVED, AdminDraftStatus.REJECTED}:
            raise ValueError("unsupported review status")
        rows = self._connection.execute(
            """
            SELECT draft_id, operation, status, target_place_id, candidate_place_id,
                   source_name, source_url, payload_json, evidence_json, created_at,
                   updated_at, review_note, reviewed_at
            FROM admin_evidence_drafts
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (status, int(limit)),
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            item["evidence"] = json.loads(item.pop("evidence_json"))
            item["changes_count"] = len(item["evidence"])
            items.append(item)
        return tuple(items)

    @staticmethod
    def _subject_key_for_item(item: Mapping[str, Any]) -> str:
        payload = item.get("payload") or {}
        explicit = payload.get("draft_subject_key")
        if explicit:
            return str(explicit)
        return _draft_subject_key(
            operation=str(item.get("operation") or payload.get("operation") or ""),
            target_place_id=item.get("target_place_id"),
            payload=payload,
            source_url=str(item.get("source_url") or (payload.get("source") or {}).get("source_url") or ""),
        )

    def list_review_groups(self, status: str = AdminDraftStatus.PENDING_REVIEW, limit: int = 100) -> tuple[dict[str, Any], ...]:
        """Return one latest review item per logical place, with version history.

        Older drafts remain immutable audit records. A group appears in exactly
        one filter according to its latest version status, so reviewers never
        need to compare duplicate queue rows manually.
        """
        if status not in {AdminDraftStatus.PENDING_REVIEW, AdminDraftStatus.APPROVED, AdminDraftStatus.REJECTED}:
            raise ValueError("unsupported review status")
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in self._all_review_items():
            groups.setdefault(item["draft_subject_key"], []).append(item)

        output: list[dict[str, Any]] = []
        for versions in groups.values():
            latest = versions[-1]
            if latest["status"] != status:
                continue
            latest = dict(latest)
            latest["draft_version"] = len(versions)
            latest["versions_total"] = len(versions)
            previous = versions[-2] if len(versions) > 1 else None
            latest["version_diff"] = _version_diff(previous.get("payload") if previous else None, latest["payload"])
            latest["version_history"] = [
                {
                    "draft_id": v["draft_id"],
                    "version": index + 1,
                    "status": v["status"],
                    "created_at": v["created_at"],
                    "changes_count": v["changes_count"],
                    "is_latest": index == len(versions) - 1,
                }
                for index, v in enumerate(versions)
            ]
            output.append(latest)
        output.sort(key=lambda item: item["created_at"], reverse=True)
        return tuple(output[: int(limit)])

    def _latest_draft_id_for_subject(self, draft_id: str) -> str | None:
        rows = self._connection.execute(
            """
            SELECT draft_id, operation, target_place_id, source_url, payload_json, created_at
            FROM admin_evidence_drafts ORDER BY created_at ASC, draft_id ASC
            """
        ).fetchall()
        wanted_key = None
        keyed: list[tuple[str, str]] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            item = {"operation": row["operation"], "target_place_id": row["target_place_id"], "source_url": row["source_url"], "payload": payload}
            key = self._subject_key_for_item(item)
            keyed.append((key, row["draft_id"]))
            if row["draft_id"] == draft_id:
                wanted_key = key
        if wanted_key is None:
            return None
        matches = [row_id for key, row_id in keyed if key == wanted_key]
        return matches[-1] if matches else None

    def review(self, draft_id: str, decision: str, note: str = "") -> dict[str, Any]:
        if decision not in {AdminDraftStatus.APPROVED, AdminDraftStatus.REJECTED}:
            raise ValueError("decision must be approved or rejected")
        latest_id = self._latest_draft_id_for_subject(draft_id)
        if latest_id is not None and latest_id != draft_id:
            raise ValueError("only the latest draft version can be reviewed")
        now = _now_iso()
        cursor = self._connection.execute(
            """
            UPDATE admin_evidence_drafts
            SET status = ?, review_note = ?, reviewed_at = ?, updated_at = ?
            WHERE draft_id = ? AND status = ?
            """,
            (decision, note.strip(), now, now, draft_id, AdminDraftStatus.PENDING_REVIEW),
        )
        if cursor.rowcount != 1:
            self._connection.rollback()
            raise ValueError("draft is missing or already reviewed")
        self._connection.commit()
        # Reviewing the latest version closes any older pending versions of the
        # same logical place as superseded audit history.
        self._reconcile_superseded_pending()
        return {"draft_id": draft_id, "review_status": decision, "review_note": note.strip(), "reviewed_at": now}


def _parse_optional_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("contract dates must be timezone-aware")
    return parsed


def _validate_commerce_foundation(value: Any, place_id: str) -> dict[str, Any] | None:
    if value in (None, {}):
        return None
    if not isinstance(value, Mapping):
        raise ValueError("commerce_foundation must be an object")
    merchant = value.get("merchant_content") or {}
    sponsor = value.get("sponsor_entitlement") or {}
    if not isinstance(merchant, Mapping) or not isinstance(sponsor, Mapping):
        raise ValueError("merchant_content and sponsor_entitlement must be objects")
    content = MerchantContentDraft.create(
        place_id=place_id,
        gallery_media_ids=merchant.get("gallery_media_ids") or (),
        uploaded_media_id=str(merchant.get("uploaded_media_id")).strip() if merchant.get("uploaded_media_id") else None,
        line_url=merchant.get("line_url") or None,
        facebook_url=merchant.get("facebook_url") or None,
        menu_url=merchant.get("menu_url") or None,
        booking_url=merchant.get("booking_url") or None,
        highlight_text=str(merchant.get("highlight_text")).strip() if merchant.get("highlight_text") else None,
    )
    try:
        mode = MerchantMode(str(sponsor.get("mode") or "normal"))
    except ValueError as exc:
        raise ValueError("invalid sponsor mode") from exc
    entitlement = SponsorEntitlement(
        place_id=place_id,
        mode=mode,
        plan=str(sponsor.get("plan")).strip() if sponsor.get("plan") else None,
        contract_start_at=_parse_optional_datetime(sponsor.get("contract_start_at")),
        contract_end_at=_parse_optional_datetime(sponsor.get("contract_end_at")),
        auto_expire=bool(sponsor.get("auto_expire", True)),
        contract_reference=str(sponsor.get("contract_reference")).strip() if sponsor.get("contract_reference") else None,
    )
    return {
        "merchant_content": _jsonable(content.__dict__),
        "sponsor_entitlement": {
            "mode": entitlement.mode.value,
            "plan": entitlement.plan,
            "contract_start_at": entitlement.contract_start_at.isoformat() if entitlement.contract_start_at else None,
            "contract_end_at": entitlement.contract_end_at.isoformat() if entitlement.contract_end_at else None,
            "auto_expire": entitlement.auto_expire,
            "contract_reference": entitlement.contract_reference,
        },
        "public_effect": False,
        "ranking_effect": False,
    }


class AdminDraftService:
    """Server-side validation boundary for Admin Web draft submissions."""

    def __init__(self, canonical_database: str | Path, draft_database: str | Path) -> None:
        self.canonical_database = Path(canonical_database)
        self.draft_database = Path(draft_database)

    def _canonical_place_exists(self, place_id: str) -> bool:
        uri = f"file:{self.canonical_database.resolve()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            row = connection.execute(
                "SELECT 1 FROM places WHERE place_id = ? LIMIT 1", (place_id,)
            ).fetchone()
            return row is not None
        finally:
            connection.close()

    @staticmethod
    def _require_text(value: Any, label: str) -> str:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValueError(f"{label} is required")
        return text

    def persist(self, payload: Mapping[str, Any]) -> PersistedAdminDraft:
        if not isinstance(payload, Mapping):
            raise ValueError("draft payload must be an object")
        if payload.get("mode") != "evidence_draft_only":
            raise ValueError("admin persistence accepts evidence_draft_only payloads only")

        operation = self._require_text(payload.get("operation"), "operation")
        if operation not in ALLOWED_OPERATIONS:
            raise ValueError("unsupported admin draft operation")

        source = payload.get("source")
        if not isinstance(source, Mapping):
            raise ValueError("source is required")
        source_name = self._require_text(source.get("source_name"), "source_name")
        source_url = self._require_text(source.get("source_url"), "source_url")
        if not source_url.lower().startswith(("http://", "https://")):
            raise ValueError("source_url must be an http(s) URL")

        target_place_id = payload.get("place_id")
        normalized_target_for_lookup = str(target_place_id).strip() if target_place_id not in (None, "") else None
        with AdminDraftStore(self.draft_database) as store:
            duplicate = store.find_pending_duplicate(
                operation=operation,
                target_place_id=normalized_target_for_lookup,
                source_name=source_name,
                source_url=source_url,
                payload=payload,
            )
        if duplicate is not None:
            return duplicate

        if operation == "update_place_candidate":
            target_place_id = self._require_text(target_place_id, "place_id")
            if not self._canonical_place_exists(target_place_id):
                raise ValueError("place_id does not exist in canonical database")
            candidate_place_id = target_place_id
        else:
            if target_place_id not in (None, ""):
                raise ValueError("create_place_candidate must not target a canonical place_id")
            target_place_id = None
            candidate_place_id = str(uuid4())

        commerce_foundation = _validate_commerce_foundation(payload.get("commerce_foundation"), candidate_place_id)

        changes = payload.get("changes")
        if not isinstance(changes, list) or not changes:
            raise ValueError("changes must contain at least one field")

        note = payload.get("note")
        evidence_payloads: list[dict[str, Any]] = []
        for change in changes:
            if not isinstance(change, Mapping):
                raise ValueError("each change must be an object")
            field_name = self._require_text(change.get("field_name"), "field_name")
            evidence = build_admin_evidence(
                AdminEvidenceInput(
                    place_id=candidate_place_id,
                    field_name=field_name,
                    value=change.get("value"),
                    source_name=source_name,
                    source_url=source_url,
                    note=str(note).strip() if note else None,
                )
            )
            evidence_payloads.append(_evidence_payload(evidence))

        draft_id = str(uuid4())
        normalized_payload = dict(payload)
        normalized_payload["server_contract"] = DRAFT_SCHEMA_VERSION
        normalized_payload["candidate_place_id"] = candidate_place_id
        normalized_payload["status"] = AdminDraftStatus.PENDING_REVIEW
        if commerce_foundation is not None:
            normalized_payload["commerce_foundation"] = commerce_foundation
        subject_key = _draft_subject_key(
            operation=operation,
            target_place_id=target_place_id,
            payload=normalized_payload,
            source_url=source_url,
        )
        normalized_payload["draft_subject_key"] = subject_key
        with AdminDraftStore(self.draft_database) as store:
            existing_versions = [
                item for item in store.list_review_groups(AdminDraftStatus.PENDING_REVIEW, limit=10000)
                if item.get("draft_subject_key") == subject_key
            ]
            normalized_payload["draft_version_hint"] = (existing_versions[0].get("versions_total", 0) + 1) if existing_versions else 1
            return store.insert(
                draft_id=draft_id,
                operation=operation,
                target_place_id=target_place_id,
                candidate_place_id=candidate_place_id,
                source_name=source_name,
                source_url=source_url,
                payload=normalized_payload,
                evidence=evidence_payloads,
            )
