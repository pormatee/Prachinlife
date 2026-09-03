"""Semantic Conversational Understanding V1.

Deterministic multi-turn conversation-state resolver for PrachinLife.
This layer understands/refines user intent and references only. It never ranks,
selects, scores, or mutates published/canonical data.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Mapping

from .intent_context_understanding_v1 import understand_user_request

SEMANTIC_CONVERSATION_STATE_VERSION = "SEMANTIC-CONVERSATION-STATE-V1"
MAX_CANDIDATE_IDS = 3
MAX_REFINEMENTS = 8

_BASE_QUERY_BY_CATEGORY = {
    "vegetarian": "หาร้านเจ",
    "eat": "หาร้านอาหาร",
    "shopping": "หาที่ซื้อของ",
    "go": "หาที่เที่ยว",
    "service": "หาบริการ",
}
_BASE_QUERY_BY_OBJECT = {
    "fuel_station": "หาปั๊ม",
    "restaurant": "หาร้านอาหาร",
    "shop": "หาที่ซื้อของ",
    "destination": "หาที่เที่ยว",
    "service_place": "หาบริการ",
}
_REFINEMENT_TEXT = {
    "budget_sensitive": "ราคาไม่แพง",
    "parking": "มีที่จอดรถ",
    "family": "เหมาะกับครอบครัว",
    "time_now": "ตอนนี้",
    "time_today": "วันนี้",
    "time_tomorrow": "พรุ่งนี้",
    "time_tonight": "คืนนี้",
    "time_lunch": "มื้อเที่ยง",
    "time_dinner": "มื้อเย็น",
}
_TIME_KEYS = tuple(k for k in _REFINEMENT_TEXT if k.startswith("time_"))


@dataclass(frozen=True)
class SemanticConversationStateV1:
    schema_version: str = SEMANTIC_CONVERSATION_STATE_VERSION
    turn_index: int = 0
    active_request_text: str | None = None
    category: str | None = None
    decision_object: str | None = None
    province: str | None = None
    near_me: bool = False
    refinements: tuple[str, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    referenced_candidate_id: str | None = None
    last_user_text: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "turn_index": self.turn_index,
            "active_request_text": self.active_request_text,
            "category": self.category,
            "decision_object": self.decision_object,
            "province": self.province,
            "near_me": self.near_me,
            "refinements": list(self.refinements),
            "candidate_ids": list(self.candidate_ids),
            "referenced_candidate_id": self.referenced_candidate_id,
            "last_user_text": self.last_user_text,
        }


@dataclass(frozen=True)
class SemanticTurnResolutionV1:
    effective_text: str
    brain_context: Mapping[str, Any]
    state: SemanticConversationStateV1
    mode: str


def _clean_string(value: Any, max_len: int = 500) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("conversation_state string field invalid")
    value = value.strip()
    if len(value) > max_len:
        raise ValueError("conversation_state string field too long")
    return value or None


def state_from_payload(raw: Any) -> SemanticConversationStateV1 | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("conversation_state must be an object")
    if raw.get("schema_version") != SEMANTIC_CONVERSATION_STATE_VERSION:
        raise ValueError("conversation_state schema_version invalid")
    turn_index = raw.get("turn_index", 0)
    if not isinstance(turn_index, int) or isinstance(turn_index, bool) or not (0 <= turn_index <= 10000):
        raise ValueError("conversation_state turn_index invalid")
    near_me = raw.get("near_me", False)
    if not isinstance(near_me, bool):
        raise ValueError("conversation_state near_me invalid")
    refinements_raw = raw.get("refinements", ())
    candidate_raw = raw.get("candidate_ids", ())
    if not isinstance(refinements_raw, (list, tuple)) or not isinstance(candidate_raw, (list, tuple)):
        raise ValueError("conversation_state list field invalid")
    refinements = []
    for item in refinements_raw[:MAX_REFINEMENTS]:
        value = _clean_string(item, 80)
        if value and value in _REFINEMENT_TEXT and value not in refinements:
            refinements.append(value)
    candidate_ids = []
    for item in candidate_raw[:MAX_CANDIDATE_IDS]:
        value = _clean_string(item, 200)
        if value and value not in candidate_ids:
            candidate_ids.append(value)
    referenced = _clean_string(raw.get("referenced_candidate_id"), 200)
    if referenced and referenced not in candidate_ids:
        referenced = None
    return SemanticConversationStateV1(
        turn_index=turn_index,
        active_request_text=_clean_string(raw.get("active_request_text"), 1000),
        category=_clean_string(raw.get("category"), 80),
        decision_object=_clean_string(raw.get("decision_object"), 80),
        province=_clean_string(raw.get("province"), 120),
        near_me=near_me,
        refinements=tuple(refinements),
        candidate_ids=tuple(candidate_ids),
        referenced_candidate_id=referenced,
        last_user_text=_clean_string(raw.get("last_user_text"), 1000),
    )


def _dedupe(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(x for x in values if x))


def _detect_refinements(text: str) -> tuple[tuple[str, ...], tuple[str, ...], bool | None]:
    t = str(text or "").strip().casefold()
    add: list[str] = []
    remove: list[str] = []
    near_me: bool | None = None

    if any(x in t for x in ("ไม่แพง", "ราคาถูก", "ประหยัด", "งบน้อย", "คุ้ม", "ถูกหน่อย")):
        add.append("budget_sensitive")
    if any(x in t for x in ("ไม่เน้นราคา", "ราคาอะไรก็ได้", "ไม่ซีเรียสเรื่องราคา")):
        remove.append("budget_sensitive")

    if any(x in t for x in ("ที่จอดรถ", "จอดรถสะดวก", "parking")):
        add.append("parking")
    if any(x in t for x in ("ไม่ต้องมีที่จอดรถ", "ไม่ซีเรียสที่จอดรถ")):
        remove.append("parking")

    if any(x in t for x in ("พาแม่", "พาพ่อ", "ครอบครัว", "มีเด็ก", "พาลูก", "ผู้สูงอายุ", "พ่อแม่")):
        add.append("family")

    if any(x in t for x in ("ใกล้กว่านี้", "ใกล้กว่า", "เอาใกล้", "ใกล้ฉัน", "แถวนี้", "ใกล้ ๆ", "ใกล้ๆ")):
        near_me = True
    if any(x in t for x in ("ไกลได้", "ไม่ต้องใกล้", "ไม่เน้นใกล้")):
        near_me = False

    time_map = (
        ("time_tomorrow", ("พรุ่งนี้", "tomorrow")),
        ("time_today", ("วันนี้", "today")),
        ("time_now", ("ตอนนี้", "เดี๋ยวนี้", "now")),
        ("time_tonight", ("คืนนี้", "tonight")),
        ("time_lunch", ("มื้อเที่ยง", "เที่ยง", "lunch")),
        ("time_dinner", ("มื้อเย็น", "เย็นนี้", "dinner")),
    )
    for key, terms in time_map:
        if any(term in t for term in terms):
            remove.extend(k for k in _TIME_KEYS if k != key)
            add.append(key)
            break

    return _dedupe(add), _dedupe(remove), near_me


def _reference_index(text: str) -> int | None:
    t = re.sub(r"\s+", "", str(text or "").casefold())
    groups = (
        (0, ("ร้านแรก", "ร้านที่1", "ร้านที่หนึ่ง", "อันแรก", "ตัวแรก", "ตัวที่1", "ตัวที่หนึ่ง")),
        (1, ("ร้านที่2", "ร้านที่สอง", "ร้านสอง", "อันที่2", "อันที่สอง", "ตัวที่2", "ตัวที่สอง")),
        (2, ("ร้านที่3", "ร้านที่สาม", "ร้านสาม", "อันที่3", "อันที่สาม", "ตัวที่3", "ตัวที่สาม")),
    )
    for index, terms in groups:
        if any(term.replace(" ", "") in t for term in terms):
            return index
    return None


def _looks_like_location_change(text: str, direct_province: str | None) -> bool:
    if not direct_province:
        return False
    t = str(text or "").strip().casefold()
    return any(x in t for x in ("เปลี่ยนเป็น", "เปลี่ยนไป", "แถว", "ที่", "จังหวัด", "ไป")) or len(t) <= 40


def _canonical_query(state: SemanticConversationStateV1) -> str:
    if state.category == "vegetarian":
        base = "หาร้านเจ"
    else:
        base = _BASE_QUERY_BY_OBJECT.get(state.decision_object) or _BASE_QUERY_BY_CATEGORY.get(state.category) or state.active_request_text or "ช่วยหาสถานที่"
    parts = [base]
    if state.near_me:
        parts.append("ใกล้ฉัน")
    elif state.province:
        parts.append(state.province)
    for key in state.refinements:
        text = _REFINEMENT_TEXT.get(key)
        if text:
            parts.append(text)
    return " ".join(dict.fromkeys(parts))


def resolve_semantic_turn_v1(user_text: str, context: Mapping[str, Any] | None = None) -> SemanticTurnResolutionV1:
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("user_text required")
    context = dict(context or {})
    previous = state_from_payload(context.pop("conversation_state", None))
    # Distinguish facts explicitly present in the latest utterance from values
    # merely carried in trusted context. This prevents an old location_text
    # from making an unrelated follow-up look like a new location command.
    direct_text = understand_user_request(user_text, context={})

    if previous is None:
        direct = understand_user_request(user_text, context=context)
        state = SemanticConversationStateV1(
            turn_index=1,
            active_request_text=user_text.strip(),
            category=direct.category,
            decision_object=direct.decision_object,
            province=direct.province,
            near_me=bool(direct.near_me),
            refinements=(),
            candidate_ids=(),
            referenced_candidate_id=None,
            last_user_text=user_text.strip(),
        )
        return SemanticTurnResolutionV1(user_text.strip(), context, state, "new")

    direct = direct_text
    add, remove, near_update = _detect_refinements(user_text)
    refinements = [x for x in previous.refinements if x not in set(remove)]
    for item in add:
        if item not in refinements:
            refinements.append(item)

    category = previous.category
    decision_object = previous.decision_object
    province = previous.province
    near_me = previous.near_me
    active_request_text = previous.active_request_text or user_text.strip()
    candidate_ids = previous.candidate_ids
    referenced_candidate_id = None
    mode = "refine"

    category_changed = bool(direct.category and direct.category != previous.category)
    explicit_new_object = bool(direct.decision_object and direct.decision_object != previous.decision_object)
    if category_changed or explicit_new_object:
        category = direct.category or category
        decision_object = direct.decision_object or decision_object
        province = direct.province
        near_me = bool(direct.near_me)
        refinements = list(add)
        active_request_text = user_text.strip()
        candidate_ids = ()
        if direct.province:
            context["location_text"] = user_text.strip()
        mode = "new_intent"
    else:
        if direct.category:
            category = direct.category
        if direct.decision_object:
            decision_object = direct.decision_object
        if add or remove:
            candidate_ids = ()
        if near_update is not None:
            if near_update != near_me:
                candidate_ids = ()
            near_me = near_update
        if _looks_like_location_change(user_text, direct.province):
            province = direct.province
            if not direct.near_me:
                near_me = False
                context.pop("current_location", None)
            context["location_text"] = user_text.strip()
            candidate_ids = ()
            mode = "location_change"

    ref_index = _reference_index(user_text)
    if ref_index is not None and ref_index < len(candidate_ids):
        referenced_candidate_id = candidate_ids[ref_index]
        mode = "reference"

    state = SemanticConversationStateV1(
        turn_index=previous.turn_index + 1,
        active_request_text=active_request_text,
        category=category,
        decision_object=decision_object,
        province=province,
        near_me=near_me,
        refinements=tuple(refinements[:MAX_REFINEMENTS]),
        candidate_ids=tuple(candidate_ids[:MAX_CANDIDATE_IDS]),
        referenced_candidate_id=referenced_candidate_id,
        last_user_text=user_text.strip(),
    )
    return SemanticTurnResolutionV1(_canonical_query(state), context, state, mode)


def finalize_semantic_state_v1(state: SemanticConversationStateV1, result: Mapping[str, Any]) -> SemanticConversationStateV1:
    understanding = result.get("understanding") if isinstance(result, Mapping) else None
    if not isinstance(understanding, Mapping):
        understanding = {}
    explanation = result.get("explanation") if isinstance(result, Mapping) else None
    if not isinstance(explanation, Mapping):
        explanation = {}

    category = understanding.get("category") or state.category
    decision_object = understanding.get("decision_object") or state.decision_object
    province = understanding.get("province") or state.province
    near_me = bool(understanding.get("near_me")) if "near_me" in understanding else state.near_me

    best = str(explanation.get("best_fit_candidate_id") or "").strip()
    alternatives_raw = explanation.get("alternatives")
    alternatives = alternatives_raw if isinstance(alternatives_raw, (list, tuple)) else ()
    ids = []
    for raw in (best, *alternatives):
        value = str(raw or "").strip()
        if value and value not in ids:
            ids.append(value)
        if len(ids) >= MAX_CANDIDATE_IDS:
            break
    candidate_ids = tuple(ids) if ids else state.candidate_ids
    referenced = state.referenced_candidate_id if state.referenced_candidate_id in candidate_ids else None

    return replace(
        state,
        category=category,
        decision_object=decision_object,
        province=province,
        near_me=near_me,
        candidate_ids=candidate_ids,
        referenced_candidate_id=referenced,
    )
