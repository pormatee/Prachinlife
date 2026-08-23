from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .contracts import EvidenceStatus, SourceRef, SourceType
from .models import EvidenceKind, PlaceEvidence

POLICY_VERSION = "3.4-independent-web-evidence-acquisition-v1"
TARGET_FIELDS = ("phone", "website")
_NAME_CLEAN_RE = re.compile(r"[^0-9a-zก-๙]+", re.I)
_GENERIC_WORDS = {
    "restaurant", "cafe", "café", "food", "vegetarian", "vegan", "station",
    "ร้าน", "อาหาร", "มังสวิรัติ", "เจ",
}


@dataclass(frozen=True)
class WebObservation:
    target_rank: int
    place_id: str
    observed_name: str
    province: str
    source_name: str
    source_url: str
    source_record_id: str
    phone: str | None = None
    website: str | None = None


@dataclass(frozen=True)
class WebCandidateClaim:
    target_rank: int
    place_id: str
    canonical_name: str
    field_name: str
    value: str
    evidence_id: str
    source_name: str
    source_record_id: str
    source_url: str
    status: str


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _http_url(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        return None
    return raw


def _name_tokens(value: str | None) -> tuple[str, ...]:
    raw = str(value or "").casefold().replace("&", " and ")
    cleaned = _NAME_CLEAN_RE.sub(" ", raw)
    return tuple(x for x in cleaned.split() if x and x not in _GENERIC_WORDS)


def _name_similarity(left: str | None, right: str | None) -> float:
    a_tokens = _name_tokens(left)
    b_tokens = _name_tokens(right)
    a = "".join(a_tokens)
    b = "".join(b_tokens)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) >= 5 and (a in b or b in a):
        return 0.95
    token_overlap = len(set(a_tokens) & set(b_tokens)) / max(1, len(set(a_tokens) | set(b_tokens)))
    return max(SequenceMatcher(None, a, b).ratio(), token_overlap)


def _normalize_phone(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not 8 <= len(digits) <= 15:
        return None
    return ("+" if plus else "") + digits


def _target_index(plan: dict[str, Any], repo_root: str | Path) -> dict[int, dict[str, Any]]:
    root = Path(repo_root)
    datasets: dict[str, list[dict[str, Any]]] = {}
    record_maps: dict[str, dict[str, dict[str, Any]]] = {}
    for item in plan.get("queue") or ():
        dataset = str(item.get("dataset") or "")
        if dataset not in datasets:
            rows = _load_json(root / dataset)
            datasets[dataset] = [x for x in rows if isinstance(x, dict)]
            record_maps[dataset] = {str(x.get("id") or ""): x for x in datasets[dataset]}
    out: dict[int, dict[str, Any]] = {}
    for item in plan.get("queue") or ():
        rank = int(item.get("rank") or 0)
        dataset = str(item.get("dataset") or "")
        record_id = str(item.get("record_id") or "")
        record = record_maps.get(dataset, {}).get(record_id) or {}
        location = record.get("location") if isinstance(record.get("location"), dict) else {}
        province = str(location.get("province") or record.get("province") or "").strip()
        out[rank] = {
            "rank": rank,
            "dataset": dataset,
            "record_id": record_id,
            "place_id": str(item.get("place_id") or ""),
            "name": str(item.get("name") or ""),
            "province": province,
        }
    return out


def _parse_observation(raw: dict[str, Any]) -> WebObservation:
    return WebObservation(
        target_rank=int(raw.get("target_rank") or 0),
        place_id=str(raw.get("place_id") or "").strip(),
        observed_name=str(raw.get("observed_name") or "").strip(),
        province=str(raw.get("province") or "").strip(),
        source_name=str(raw.get("source_name") or "").strip(),
        source_url=str(raw.get("source_url") or "").strip(),
        source_record_id=str(raw.get("source_record_id") or "").strip(),
        phone=str(raw.get("phone") or "").strip() or None,
        website=str(raw.get("website") or "").strip() or None,
    )


def _candidate_evidence(
    *, target: dict[str, Any], observation: WebObservation, field: str, value: str,
    observed_at: datetime,
) -> PlaceEvidence:
    return PlaceEvidence(
        place_id=target["place_id"],
        source=SourceRef(
            source_type=SourceType.WEB,
            source_name=observation.source_name,
            source_record_id=observation.source_record_id,
            source_url=observation.source_url,
            observed_at=observed_at,
        ),
        kind=EvidenceKind.CONTACT,
        field_name=field,
        value=value,
        status=EvidenceStatus.CANDIDATE,
        observed_at=observed_at,
        metadata={
            "acquisition": "phase3_4_independent_web_observation",
            "policy_version": POLICY_VERSION,
            "target_rank": target["rank"],
            "production_dataset": target["dataset"],
            "production_record_id": target["record_id"],
            "identity_name_similarity": round(_name_similarity(target["name"], observation.observed_name), 4),
        },
    )


def acquire_independent_web_evidence(
    *, database_path: str | Path, targeted_plan_path: str | Path, repo_root: str | Path,
    observation_manifest_path: str | Path, observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Validate externally discovered web observations and emit candidate evidence only.

    This phase never mutates SQLite or production JSON.  The observation manifest is an
    explicit provenance boundary: each row must identify its target, source URL, observed
    name, province and field values.  Candidate evidence still requires later verification
    and adoption before publication.
    """
    observed_at = observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")

    db_before = _sha256(database_path)
    plan = _load_json(targeted_plan_path)
    targets = _target_index(plan, repo_root)
    manifest = _load_json(observation_manifest_path)
    raw_observations = manifest.get("observations") if isinstance(manifest, dict) else None
    if not isinstance(raw_observations, list):
        raise ValueError("observation manifest must contain an observations list")

    claims: list[WebCandidateClaim] = []
    reviewed: list[dict[str, Any]] = []
    blocked = Counter()
    matched_observations = 0
    unique_sources: set[tuple[str, str]] = set()

    for raw in raw_observations:
        if not isinstance(raw, dict):
            blocked["invalid_observation"] += 1
            continue
        obs = _parse_observation(raw)
        target = targets.get(obs.target_rank)
        reason = None
        similarity = 0.0
        if target is None:
            reason = "unknown_target_rank"
        elif obs.place_id != target["place_id"]:
            reason = "place_id_mismatch"
        elif not obs.source_name or not obs.source_record_id or not _http_url(obs.source_url):
            reason = "invalid_source_provenance"
        elif "openstreetmap.org" in obs.source_url.casefold():
            reason = "source_is_not_independent_web"
        elif not obs.province or obs.province.casefold() != target["province"].casefold():
            reason = "province_conflict"
        else:
            similarity = _name_similarity(target["name"], obs.observed_name)
            if similarity < 0.72:
                reason = "identity_name_conflict"

        field_values: dict[str, str] = {}
        if reason is None:
            if obs.phone:
                phone = _normalize_phone(obs.phone)
                if phone:
                    field_values["phone"] = phone
                else:
                    reason = "invalid_phone"
            if reason is None and obs.website:
                website = _http_url(obs.website)
                if website and "openstreetmap.org" not in website.casefold():
                    field_values["website"] = website
                else:
                    reason = "invalid_website"
            if reason is None and not field_values:
                reason = "no_contact_claims"

        row = {
            "target_rank": obs.target_rank,
            "place_id": obs.place_id,
            "target_name": target.get("name") if target else None,
            "observed_name": obs.observed_name,
            "province": obs.province,
            "source_name": obs.source_name,
            "source_url": obs.source_url,
            "source_record_id": obs.source_record_id,
            "name_similarity": round(similarity, 4),
            "accepted": reason is None,
            "blocked_reason": reason,
            "candidate_fields": sorted(field_values),
        }
        reviewed.append(row)
        if reason is not None:
            blocked[reason] += 1
            continue

        matched_observations += 1
        unique_sources.add((obs.source_name.casefold(), obs.source_url.casefold()))
        for field, value in field_values.items():
            evidence = _candidate_evidence(
                target=target, observation=obs, field=field, value=value, observed_at=observed_at,
            )
            claims.append(WebCandidateClaim(
                target_rank=obs.target_rank,
                place_id=target["place_id"],
                canonical_name=target["name"],
                field_name=field,
                value=value,
                evidence_id=evidence.evidence_id,
                source_name=evidence.source.source_name,
                source_record_id=evidence.source.source_record_id or "",
                source_url=evidence.source.source_url or "",
                status=evidence.status.value,
            ))

    db_after = _sha256(database_path)
    field_counts = Counter(x.field_name for x in claims)
    place_counts = Counter(x.place_id for x in claims)
    return {
        "mode": "READ_ONLY_INDEPENDENT_WEB_EVIDENCE_ACQUISITION",
        "policy_version": POLICY_VERSION,
        "target_queue_count": len(targets),
        "observation_count": len(raw_observations),
        "matched_observation_count": matched_observations,
        "candidate_claim_count": len(claims),
        "candidate_place_count": len(place_counts),
        "candidate_field_counts": dict(sorted(field_counts.items())),
        "unique_source_count": len(unique_sources),
        "blocked_counts": dict(sorted(blocked.items())),
        "claims": [asdict(x) for x in claims],
        "observations": reviewed,
        "next_stage": "verification_and_controlled_adoption_required",
        "safety": {
            "canonical_writes": False,
            "evidence_writes": False,
            "production_json_writes": False,
            "trust_policy_lowered": False,
            "candidate_only": True,
            "database_unchanged": db_before == db_after,
            "database_sha256_before": db_before,
            "database_sha256_after": db_after,
        },
    }
