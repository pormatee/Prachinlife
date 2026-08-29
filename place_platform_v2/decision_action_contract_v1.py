from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

ACTION_CONTRACT_VERSION = "v1"

_ALLOWED_ACTION_TYPES = frozenset({
    "OPEN_PLACE_CARD",
    "SHOW_ALTERNATIVES",
    "COMPARE_PLACES",
    "OPEN_MAP",
    "REQUEST_LOCATION",
    "ASK_ONE_QUESTION",
})


def _place_id(place: Mapping[str, Any] | None) -> str | None:
    if not place:
        return None
    for key in ("place_id", "id", "canonical_place_id"):
        value = place.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _coordinates(place: Mapping[str, Any] | None) -> dict[str, float] | None:
    if not place:
        return None

    candidates = [
        (place.get("lat"), place.get("lng")),
        (place.get("latitude"), place.get("longitude")),
    ]
    coords = place.get("coordinates")
    if isinstance(coords, Mapping):
        candidates.extend([
            (coords.get("lat"), coords.get("lng")),
            (coords.get("latitude"), coords.get("longitude")),
        ])

    for lat, lng in candidates:
        try:
            if lat is not None and lng is not None:
                return {"lat": float(lat), "lng": float(lng)}
        except (TypeError, ValueError):
            continue
    return None


def _decision(result: Mapping[str, Any]) -> Mapping[str, Any]:
    value = result.get("decision")
    return value if isinstance(value, Mapping) else result


def _best_fit(result: Mapping[str, Any], decision: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for source in (decision, result):
        for key in ("best_fit", "recommendation", "primary_recommendation"):
            value = source.get(key)
            if isinstance(value, Mapping):
                return value
    return None


def _alternatives(result: Mapping[str, Any], decision: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for source in (decision, result):
        value = source.get("alternatives")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _question(result: Mapping[str, Any], decision: Mapping[str, Any]) -> str | None:
    for source in (decision, result):
        for key in ("highest_value_question", "question", "follow_up_question"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    explanation = result.get("explanation")
    if isinstance(explanation, Mapping):
        for key in ("highest_value_question", "question", "follow_up_question"):
            value = explanation.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _uncertainty_tokens(result: Mapping[str, Any], decision: Mapping[str, Any]) -> set[str]:
    raw: list[Any] = []
    for source in (decision, result):
        for key in ("uncertainties", "uncertainty"):
            value = source.get(key)
            if isinstance(value, list):
                raw.extend(value)
            elif value is not None:
                raw.append(value)

    explanation = result.get("explanation")
    if isinstance(explanation, Mapping):
        value = explanation.get("uncertainties")
        if isinstance(value, list):
            raw.extend(value)

    tokens: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            tokens.add(item.strip().lower())
        elif isinstance(item, Mapping):
            for key in ("type", "code", "field", "name"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    tokens.add(value.strip().lower())
    return tokens


def _action(
    action_type: str,
    *,
    target: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
    requires_user_confirmation: bool = False,
) -> dict[str, Any]:
    if action_type not in _ALLOWED_ACTION_TYPES:
        raise ValueError(f"unsupported action type: {action_type}")

    action: dict[str, Any] = {
        "type": action_type,
        "requires_user_confirmation": bool(requires_user_confirmation),
    }
    if target:
        action["target"] = dict(target)
    if params:
        action["params"] = dict(params)
    return action


def build_decision_actions_v1(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build allow-listed declarative actions from an existing brain decision."""
    if not isinstance(result, Mapping):
        raise TypeError("result must be a mapping")

    decision = _decision(result)
    status = str(result.get("status") or decision.get("status") or "").strip().lower()
    best = _best_fit(result, decision)
    alternatives = _alternatives(result, decision)
    question = _question(result, decision)
    uncertainty = _uncertainty_tokens(result, decision)

    if status == "needs_user_input":
        if question:
            return [_action(
                "ASK_ONE_QUESTION",
                params={"question": question},
                requires_user_confirmation=True,
            )]
        if {"location", "distance", "distance_norm"} & uncertainty:
            return [_action("REQUEST_LOCATION", requires_user_confirmation=True)]
        return []

    actions: list[dict[str, Any]] = []
    best_id = _place_id(best)

    if best_id:
        actions.append(_action("OPEN_PLACE_CARD", target={"place_id": best_id}))

    alt_ids = [pid for pid in (_place_id(item) for item in alternatives) if pid]
    if alt_ids:
        actions.append(_action(
            "SHOW_ALTERNATIVES",
            params={"place_ids": alt_ids[:2]},
        ))

    compare_ids = list(dict.fromkeys(([best_id] if best_id else []) + alt_ids))
    if len(compare_ids) >= 2:
        actions.append(_action(
            "COMPARE_PLACES",
            params={"place_ids": compare_ids[:3]},
            requires_user_confirmation=True,
        ))

    coords = _coordinates(best)
    if best_id and coords:
        actions.append(_action(
            "OPEN_MAP",
            target={"place_id": best_id},
            params=coords,
            requires_user_confirmation=True,
        ))

    if question:
        actions.append(_action(
            "ASK_ONE_QUESTION",
            params={"question": question},
            requires_user_confirmation=True,
        ))
    elif {"location", "distance", "distance_norm"} & uncertainty:
        actions.append(_action(
            "REQUEST_LOCATION",
            requires_user_confirmation=True,
        ))

    return actions


def attach_decision_actions_v1(result: Mapping[str, Any]) -> dict[str, Any]:
    """Copy the brain result and attach Action Contract V1 without executing it."""
    if not isinstance(result, Mapping):
        raise TypeError("result must be a mapping")
    enriched = deepcopy(dict(result))
    enriched["action_contract_version"] = ACTION_CONTRACT_VERSION
    enriched["actions"] = build_decision_actions_v1(enriched)
    return enriched
