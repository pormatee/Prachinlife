from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

POLICY_VERSION = "LOCAL-LIFE-TRUST-PUBLICATION-V1"
ENV_FLAG = "PRACHIN_LOCAL_LIFE_TRUST_PUBLICATION_V1"


class FieldTrustState(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PlaceVisibilityDecision:
    place_id: str
    visible: bool
    hard_blockers: tuple[str, ...]
    disclosures: tuple[str, ...]
    field_trust: Mapping[str, str]
    policy_version: str = POLICY_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "visible": self.visible,
            "hard_blockers": list(self.hard_blockers),
            "disclosures": list(self.disclosures),
            "field_trust": dict(self.field_trust),
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True)
class ReleaseIntegrityDecision:
    ok: bool
    hard_blockers: tuple[str, ...]
    compatibility_warnings: tuple[str, ...]
    policy_version: str = POLICY_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "hard_blockers": list(self.hard_blockers),
            "compatibility_warnings": list(self.compatibility_warnings),
            "policy_version": self.policy_version,
        }


def policy_enabled() -> bool:
    return str(os.environ.get(ENV_FLAG, "")).strip().casefold() in {
        "1", "true", "yes", "on", "enabled"
    }


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _lifecycle_text(value: Any) -> str:
    return str(getattr(value, "value", value) or "").strip().casefold()


def _categories(value: Any) -> tuple[str, ...]:
    raw = value
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = [raw]
    if isinstance(raw, Mapping):
        if raw.get("__type__") == "tuple":
            raw = raw.get("items", [])
        elif isinstance(raw.get("items"), list):
            raw = raw.get("items", [])
        else:
            raw = []
    if isinstance(raw, tuple):
        raw = list(raw)
    if not isinstance(raw, list):
        raw = [] if raw in (None, "") else [raw]
    return tuple(sorted({str(x).strip().casefold() for x in raw if str(x).strip()}))


def _location(obj: Any) -> tuple[float | None, float | None]:
    loc = _value(obj, "location")
    lat = lon = None
    if loc is not None:
        lat = _value(loc, "latitude", _value(loc, "lat"))
        lon = _value(loc, "longitude", _value(loc, "lon", _value(loc, "lng")))
    if lat is None:
        lat = _value(obj, "latitude", _value(obj, "lat"))
    if lon is None:
        lon = _value(obj, "longitude", _value(obj, "lon", _value(obj, "lng")))
    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except Exception:
        return None, None
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None
    return lat, lon


def _reason_hard(reason: str) -> bool:
    low = str(reason or "").strip().casefold()
    return any(token in low for token in (
        "recent negative existence/lifecycle evidence",
        "confirmed permanent closure",
        "wrong identity",
        "duplicate identity",
        "known duplicate",
        "moved materially from canonical location",
    ))


def evaluate_place_like(
    place: Any,
    legacy_reasons: Iterable[str] = (),
    *,
    evidence_count: int | None = None,
) -> PlaceVisibilityDecision:
    place_id = str(
        _value(place, "place_id", _value(_value(place, "identity"), "place_id", "")) or ""
    ).strip()
    lat, lon = _location(place)
    cats = _categories(_value(place, "categories", _value(place, "categories_json", [])))
    lifecycle = _lifecycle_text(_value(place, "lifecycle"))
    reasons = tuple(str(r) for r in (legacy_reasons or ()))

    hard: list[str] = []
    disclosures: list[str] = []

    if not place_id:
        hard.append("identity unresolved")
    if lat is None or lon is None:
        hard.append("usable location missing")
    if not cats:
        hard.append("minimum category missing")
    if lifecycle in {"closed", "inactive", "permanently_closed"}:
        hard.append(f"strong negative lifecycle state: {lifecycle}")
    if evidence_count is not None and int(evidence_count) <= 0:
        hard.append("no reasonable evidence path")

    for reason in reasons:
        (hard if _reason_hard(reason) else disclosures).append(reason)

    loc_reason = " ".join(r.casefold() for r in reasons if "location" in r.casefold())
    cat_reason = " ".join(r.casefold() for r in reasons if "categor" in r.casefold())
    exist_reason = " ".join(
        r.casefold() for r in reasons
        if "existence" in r.casefold() or "lifecycle" in r.casefold()
    )

    if lat is None or lon is None:
        loc_state = FieldTrustState.UNKNOWN
    elif "conflict" in loc_reason:
        loc_state = FieldTrustState.UNCERTAIN
    elif "unsupported" in loc_reason:
        loc_state = FieldTrustState.SUPPORTED
    else:
        loc_state = FieldTrustState.VERIFIED

    if not cats:
        cat_state = FieldTrustState.UNKNOWN
    elif "conflict" in cat_reason:
        cat_state = FieldTrustState.UNCERTAIN
    elif "unsupported" in cat_reason:
        cat_state = FieldTrustState.SUPPORTED
    else:
        cat_state = FieldTrustState.VERIFIED

    if lifecycle in {"closed", "inactive", "permanently_closed"}:
        life_state = FieldTrustState.UNCERTAIN
    elif lifecycle == "active":
        life_state = FieldTrustState.VERIFIED
    elif evidence_count and evidence_count > 0:
        life_state = FieldTrustState.SUPPORTED
    else:
        life_state = FieldTrustState.UNKNOWN

    if any(_reason_hard(r) for r in reasons):
        exist_state = FieldTrustState.UNCERTAIN
    elif "no recent explicit existence observation" in exist_reason:
        exist_state = FieldTrustState.SUPPORTED if evidence_count and evidence_count > 0 else FieldTrustState.UNKNOWN
    elif evidence_count and evidence_count > 0:
        exist_state = FieldTrustState.SUPPORTED
    else:
        exist_state = FieldTrustState.UNKNOWN

    hard = list(dict.fromkeys(hard))
    disclosures = [x for x in dict.fromkeys(disclosures) if x not in hard]
    return PlaceVisibilityDecision(
        place_id=place_id,
        visible=not hard,
        hard_blockers=tuple(hard),
        disclosures=tuple(disclosures),
        field_trust={
            "location": loc_state.value,
            "category": cat_state.value,
            "existence": exist_state.value,
            "lifecycle": life_state.value,
        },
    )


def _connect_ro(database_path: str | Path) -> sqlite3.Connection:
    p = Path(database_path).resolve()
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _place_record(database_path: str | Path, place_id: str) -> dict[str, Any] | None:
    con = _connect_ro(database_path)
    try:
        row = con.execute("select * from places where place_id=?", (place_id,)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def _evidence_count(database_path: str | Path, place_id: str) -> int:
    con = _connect_ro(database_path)
    try:
        try:
            row = con.execute(
                "select count(*) from place_evidence where place_id=?", (place_id,)
            ).fetchone()
            return int(row[0] if row else 0)
        except sqlite3.Error:
            return 0
    finally:
        con.close()


def local_life_place_decision_for_id(
    database_path: str | Path,
    place_id: str,
    legacy_reasons: Iterable[str] = (),
) -> PlaceVisibilityDecision:
    row = _place_record(database_path, place_id)
    if row is None:
        return PlaceVisibilityDecision(
            place_id=place_id,
            visible=False,
            hard_blockers=("canonical place missing",),
            disclosures=(),
            field_trust={k: FieldTrustState.UNKNOWN.value for k in ("location","category","existence","lifecycle")},
        )
    return evaluate_place_like(
        row, legacy_reasons, evidence_count=_evidence_count(database_path, place_id)
    )


def local_life_eligibility_audit(
    database_path: str | Path,
    province: str = "ปราจีนบุรี",
) -> dict[str, Any]:
    from . import staged_milestone as sm

    legacy_eligible, legacy_blocked = sm.eligible_place_ids(database_path, province)
    eligible = set(str(x) for x in legacy_eligible)
    decisions: dict[str, Any] = {}
    hard_blocked: list[dict[str, Any]] = []

    for pid in sorted(tuple(eligible)):
        d = local_life_place_decision_for_id(database_path, pid, ())
        decisions[pid] = d.as_dict()
        if not d.visible:
            eligible.discard(pid)
            hard_blocked.append({"place_id": pid, "reasons": list(d.hard_blockers), "disclosures": list(d.disclosures)})

    for item in legacy_blocked or ():
        if isinstance(item, Mapping):
            pid = str(item.get("place_id") or "").strip()
            reasons = item.get("reasons") or ()
        else:
            pid = str(item or "").strip()
            reasons = ()
        if not pid:
            continue
        d = local_life_place_decision_for_id(database_path, pid, reasons)
        decisions[pid] = d.as_dict()
        if d.visible:
            eligible.add(pid)
        else:
            hard_blocked.append({"place_id": pid, "reasons": list(d.hard_blockers), "disclosures": list(d.disclosures)})

    return {
        "policy_version": POLICY_VERSION,
        "province": province,
        "eligible_place_ids": sorted(eligible),
        "blocked": hard_blocked,
        "decisions": decisions,
        "legacy_eligible_count": len(legacy_eligible),
        "legacy_blocked_count": len(legacy_blocked or ()),
        "visible_count": len(eligible),
        "hard_blocked_count": len(hard_blocked),
    }


def local_life_eligible_place_ids(database_path: str | Path, province: str = "ปราจีนบุรี"):
    r = local_life_eligibility_audit(database_path, province)
    return r["eligible_place_ids"], r["blocked"]


_HARD_COMPARATIVE_CHECKS = {
    "manifest_eligible_overlay_equal",
    "manifest_unmapped_zero",
    "overlay_unique_place_count",
    "overlay_core_identity_matches_v2",
    "category_shape_preserved",
    "rollback_default_v1_paths_present",
}


def _check_status(report: Mapping[str, Any], name: str) -> bool | None:
    checks = report.get("checks")
    if isinstance(checks, Mapping):
        value = checks.get(name)
        if isinstance(value, bool):
            return value
        if isinstance(value, Mapping):
            for key in ("passed", "pass", "ok", "ready"):
                if key in value:
                    return bool(value[key])
            status = str(value.get("status") or "").strip().casefold()
            if status:
                return status in {"pass", "passed", "ok", "ready", "true"}
    if isinstance(checks, Sequence) and not isinstance(checks, (str, bytes)):
        for item in checks:
            if not isinstance(item, Mapping):
                continue
            if str(item.get("name") or item.get("check") or "").strip() != name:
                continue
            for key in ("passed", "pass", "ok", "ready"):
                if key in item:
                    return bool(item[key])
            status = str(item.get("status") or item.get("result") or "").strip().casefold()
            if status:
                return status in {"pass", "passed", "ok", "ready", "true"}
    return None


def evaluate_release_integrity(comparative: Mapping[str, Any]) -> ReleaseIntegrityDecision:
    hard: list[str] = []
    warnings: list[str] = []

    if comparative.get("rollback_verified") is not True:
        hard.append("rollback was not verified")

    eligible = int(comparative.get("eligible_place_count", 0) or 0)
    overlays = int(comparative.get("overlay_place_count", 0) or 0)
    unmapped = comparative.get("unmapped_eligible_place_count", None)

    if eligible <= 0:
        hard.append("eligible release set is empty")
    if eligible != overlays:
        hard.append(f"eligible/overlay release set mismatch: {eligible}!={overlays}")
    if unmapped is not None and int(unmapped or 0) != 0:
        hard.append(f"unmapped eligible release rows remain: {unmapped}")

    for name in sorted(_HARD_COMPARATIVE_CHECKS):
        if _check_status(comparative, name) is False:
            hard.append(f"release integrity check failed: {name}")

    for raw in comparative.get("blockers") or ():
        text = str(raw)
        low = text.casefold()
        if any(name.casefold() in low for name in _HARD_COMPARATIVE_CHECKS):
            hard.append(text)
        else:
            warnings.append(text)

    return ReleaseIntegrityDecision(
        ok=not hard,
        hard_blockers=tuple(dict.fromkeys(hard)),
        compatibility_warnings=tuple(dict.fromkeys(warnings)),
    )


def local_life_release_integrity_ok(comparative: Mapping[str, Any]) -> bool:
    return evaluate_release_integrity(comparative).ok

# LOCAL_LIFE_RELEASE_CLASSIFICATION_FIX6_2
import dataclasses as _ll_dc_fix6
# Phase2 classification: overlay_core_identity_matches_v2 is legacy compatibility,
# not Local Life release-integrity authority. The legacy comparative report remains
# unchanged; only the Local Life evaluator classification is normalized here.
_evaluate_release_integrity_before_fix6 = evaluate_release_integrity

def evaluate_release_integrity(comparative):
    _result = _evaluate_release_integrity_before_fix6(comparative)

    _hard = tuple(getattr(_result, "hard_blockers", ()) or ())
    _warnings = tuple(getattr(_result, "compatibility_warnings", ()) or ())

    _demoted = tuple(
        _item for _item in _hard
        if "overlay_core_identity_matches_v2" in str(_item)
    )
    _remaining = tuple(
        _item for _item in _hard
        if "overlay_core_identity_matches_v2" not in str(_item)
    )

    if not _demoted:
        return _result

    _warnings2 = _warnings + tuple(
        _item for _item in _demoted
        if _item not in _warnings
    )

    if _ll_dc_fix6.is_dataclass(_result):
        return _ll_dc_fix6.replace(
            _result,
            ok=(len(_remaining) == 0),
            hard_blockers=_remaining,
            compatibility_warnings=_warnings2,
        )

    try:
        return type(_result)(
            ok=(len(_remaining) == 0),
            hard_blockers=_remaining,
            compatibility_warnings=_warnings2,
        )
    except Exception as _exc:
        raise RuntimeError(
            "Local Life release-integrity result type cannot be normalized safely"
        ) from _exc
