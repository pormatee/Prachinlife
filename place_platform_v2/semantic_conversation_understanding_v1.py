"""Semantic Conversational Understanding V1.

Multi-turn conversation-state resolver for PrachinLife.
A validated Generic Semantic Language Brain interpretation is authoritative for
language meaning when supplied; deterministic phrase rules remain compatibility
fallback only. This layer never ranks, selects, scores, or mutates data.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Mapping

from .intent_context_understanding_v1 import understand_user_request

SEMANTIC_CONVERSATION_STATE_VERSION = "SEMANTIC-CONVERSATION-STATE-V1"
MAX_CANDIDATE_IDS = 3
MAX_REFINEMENTS = 8
_REFERENCE_FACT_KEYS = {"hours", "parking", "address", "phone", "website", "price"}
_COMPARISON_CRITERIA = {"overall", "distance"}
_EXPLANATION_REQUESTS = {"why", "tradeoffs", "risks", "uncertainty"}

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
    reference_fact: str | None = None
    comparison_criterion: str | None = None
    explanation_request: str | None = None
    language_act: str | None = None
    semantic_criteria: tuple[str, ...] = ()
    language_confidence: float | None = None
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
            "reference_fact": self.reference_fact,
            "comparison_criterion": self.comparison_criterion,
            "explanation_request": self.explanation_request,
            "language_act": self.language_act,
            "semantic_criteria": list(self.semantic_criteria),
            "language_confidence": self.language_confidence,
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
    reference_fact = _clean_string(raw.get("reference_fact"), 40)
    if reference_fact not in _REFERENCE_FACT_KEYS:
        reference_fact = None
    comparison_criterion = _clean_string(raw.get("comparison_criterion"), 40)
    if comparison_criterion not in _COMPARISON_CRITERIA:
        comparison_criterion = None
    explanation_request = _clean_string(raw.get("explanation_request"), 40)
    if explanation_request not in _EXPLANATION_REQUESTS:
        explanation_request = None
    language_act = _clean_string(raw.get("language_act"), 40)
    semantic_criteria_raw = raw.get("semantic_criteria", ())
    if not isinstance(semantic_criteria_raw, (list, tuple)):
        semantic_criteria_raw = ()
    semantic_criteria = []
    for item in semantic_criteria_raw[:MAX_REFINEMENTS]:
        value = _clean_string(item, 120)
        if value and value not in semantic_criteria:
            semantic_criteria.append(value)
    language_confidence = raw.get("language_confidence")
    if not isinstance(language_confidence, (int, float)) or isinstance(language_confidence, bool):
        language_confidence = None
    elif not 0.0 <= float(language_confidence) <= 1.0:
        language_confidence = None
    else:
        language_confidence = float(language_confidence)
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
        reference_fact=reference_fact,
        comparison_criterion=comparison_criterion,
        explanation_request=explanation_request,
        language_act=language_act,
        semantic_criteria=tuple(semantic_criteria),
        language_confidence=language_confidence,
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






def _meaning_string(raw: Mapping[str, Any], key: str, max_len: int = 200) -> str | None:
    value = raw.get(key)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value[:max_len] if value else None


def _criterion_key_to_refinement(key: str, value: str) -> str | None:
    key = str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")
    value = str(value or "").strip().casefold()
    if key in {"budget", "budget_sensitive", "price", "affordability", "value"}:
        return "budget_sensitive"
    if key in {"parking", "car_parking"}:
        return "parking"
    if key in {"family", "family_suitability", "elderly", "children", "group_suitability", "accessibility"}:
        return "family"
    if key in {"open_now", "time_now"}:
        return "time_now"
    if key in {"time_today"}:
        return "time_today"
    if key in {"time_tomorrow"}:
        return "time_tomorrow"
    if key in {"time_tonight"}:
        return "time_tonight"
    if key in {"time_lunch"}:
        return "time_lunch"
    if key in {"time_dinner"}:
        return "time_dinner"
    return None


def _language_reference_id(
    meaning: Mapping[str, Any],
    candidate_ids: tuple[str, ...],
    previous: SemanticConversationStateV1 | None,
) -> str | None:
    reference = meaning.get("reference")
    if not isinstance(reference, Mapping):
        return None
    kind = reference.get("kind")
    if kind == "candidate_ordinal":
        ordinal = reference.get("ordinal")
        if isinstance(ordinal, int) and not isinstance(ordinal, bool) and 1 <= ordinal <= len(candidate_ids):
            return candidate_ids[ordinal - 1]
        return None
    if kind == "previous_selection":
        if previous and previous.referenced_candidate_id in candidate_ids:
            return previous.referenced_candidate_id
        return candidate_ids[0] if candidate_ids else None
    # candidate_name is resolved by the provider to an ordinal whenever the
    # runtime supplied candidate references. Never fuzzy-match names here.
    return None


def _resolve_from_language_brain_v1(
    user_text: str,
    context: dict[str, Any],
    previous: SemanticConversationStateV1 | None,
    meaning: Mapping[str, Any],
) -> SemanticTurnResolutionV1 | None:
    if meaning.get("schema_version") != "GENERIC-SEMANTIC-MEANING-V1":
        return None
    confidence = meaning.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or float(confidence) < 0.45:
        return None
    act = _meaning_string(meaning, "conversation_act", 40)
    if not act or act == "other":
        return None

    category = previous.category if previous else None
    decision_object = previous.decision_object if previous else None
    province = previous.province if previous else None
    near_me = previous.near_me if previous else False
    refinements = list(previous.refinements if previous else ())
    candidate_ids = previous.candidate_ids if previous else ()
    referenced_candidate_id = previous.referenced_candidate_id if previous else None
    comparison_criterion = previous.comparison_criterion if previous else None
    explanation_request = None
    reference_fact = None
    active_request_text = previous.active_request_text if previous else user_text.strip()
    semantic_criteria = list(previous.semantic_criteria if previous else ())
    mode = "refine"

    supplied_category = _meaning_string(meaning, "category", 80)
    supplied_object = _meaning_string(meaning, "decision_object", 80)
    supplied_province = _meaning_string(meaning, "province", 120)
    supplied_location = _meaning_string(meaning, "location_text", 200)
    supplied_near = meaning.get("near_me")

    if act == "new_request":
        category = supplied_category
        decision_object = supplied_object
        province = supplied_province
        near_me = bool(supplied_near) if isinstance(supplied_near, bool) else False
        refinements = []
        candidate_ids = ()
        referenced_candidate_id = None
        comparison_criterion = None
        active_request_text = user_text.strip()
        semantic_criteria = []
        mode = "new"
    else:
        if supplied_category:
            if category and supplied_category != category:
                candidate_ids = ()
            category = supplied_category
        if supplied_object:
            if decision_object and supplied_object != decision_object:
                candidate_ids = ()
            decision_object = supplied_object
        if supplied_province:
            if supplied_province != province:
                candidate_ids = ()
            province = supplied_province
        if isinstance(supplied_near, bool):
            if supplied_near != near_me and act not in {"compare", "explain_decision"}:
                candidate_ids = ()
            near_me = supplied_near

    if supplied_location:
        context["location_text"] = supplied_location
        if act in {"change_context", "clarification_answer", "new_request"}:
            context.pop("current_location", None)
    elif supplied_province and act in {"change_context", "clarification_answer", "new_request"}:
        context["location_text"] = supplied_province
        context.pop("current_location", None)

    criteria = meaning.get("criteria")
    if isinstance(criteria, list):
        for item in criteria[:MAX_REFINEMENTS]:
            if not isinstance(item, Mapping):
                continue
            key = str(item.get("key") or "").strip()
            value = str(item.get("value") or "").strip()
            polarity = str(item.get("polarity") or "prefer").strip()
            refinement = _criterion_key_to_refinement(key, value)
            diagnostic = f"{polarity}:{key}={value}"[:120]
            if diagnostic and diagnostic not in semantic_criteria:
                semantic_criteria.append(diagnostic)
            if not refinement:
                continue
            if polarity == "remove":
                refinements = [x for x in refinements if x != refinement]
            elif refinement not in refinements:
                if refinement.startswith("time_"):
                    refinements = [x for x in refinements if not x.startswith("time_")]
                refinements.append(refinement)

    temporal = _meaning_string(meaning, "temporal_context", 40)
    if temporal:
        time_ref = f"time_{temporal}"
        if time_ref in _REFINEMENT_TEXT:
            refinements = [x for x in refinements if not x.startswith("time_")]
            refinements.append(time_ref)

    referenced_candidate_id = _language_reference_id(meaning, candidate_ids, previous)
    fact_key = _meaning_string(meaning, "fact_key", 80)
    raw_criterion = _meaning_string(meaning, "comparison_criterion", 80)
    explanation_focus = _meaning_string(meaning, "explanation_focus", 40)

    if act == "reference_fact":
        comparison_criterion = None
        if fact_key in _REFERENCE_FACT_KEYS and referenced_candidate_id:
            reference_fact = fact_key
            mode = "reference_fact"
        else:
            reference_fact = fact_key if fact_key in _REFERENCE_FACT_KEYS else None
            mode = "reference_unresolved"
    elif act == "select_reference":
        mode = "reference" if referenced_candidate_id else "reference_unresolved"
    elif act == "compare":
        referenced_candidate_id = None
        reference_fact = None
        comparison_criterion = "distance" if raw_criterion == "distance" else "overall"
        if comparison_criterion == "distance":
            near_me = True
        mode = "comparison" if len(candidate_ids) >= 2 else "comparison_unresolved"
    elif act == "explain_decision":
        referenced_candidate_id = None
        reference_fact = None
        explanation_request = explanation_focus if explanation_focus in _EXPLANATION_REQUESTS else "why"
        # Keep prior comparison criterion so explanation re-evaluates the same frame.
        comparison_criterion = previous.comparison_criterion if previous else comparison_criterion
        mode = "decision_explanation" if candidate_ids else "decision_explanation_unresolved"
    elif act in {"change_context", "clarification_answer"}:
        if act == "change_context":
            candidate_ids = ()
        mode = "location_change" if supplied_location or supplied_province else "refine"
    elif act == "refine":
        # Refinements may materially change ranking; new candidates must be produced by Brain.
        candidate_ids = ()
        mode = "refine"

    clarification = meaning.get("clarification")
    if isinstance(clarification, Mapping) and clarification.get("needed") is True:
        mode = "language_clarification"

    state = SemanticConversationStateV1(
        turn_index=(previous.turn_index + 1) if previous else 1,
        active_request_text=active_request_text,
        category=category,
        decision_object=decision_object,
        province=province,
        near_me=near_me,
        refinements=tuple(refinements[:MAX_REFINEMENTS]),
        candidate_ids=tuple(candidate_ids[:MAX_CANDIDATE_IDS]),
        referenced_candidate_id=referenced_candidate_id,
        reference_fact=reference_fact,
        comparison_criterion=comparison_criterion,
        explanation_request=explanation_request,
        language_act=act,
        semantic_criteria=tuple(semantic_criteria[:MAX_REFINEMENTS]),
        language_confidence=float(confidence),
        last_user_text=user_text.strip(),
    )
    return SemanticTurnResolutionV1(_canonical_query(state), context, state, mode)


def _detect_comparison(text: str) -> str | None:
    t = re.sub(r"\s+", "", str(text or "").casefold())
    distance_terms = (
        "ร้านไหนใกล้กว่า", "อันไหนใกล้กว่า", "ตัวไหนใกล้กว่า",
        "ไหนใกล้กว่า", "ใกล้ที่สุด", "ใกล้กว่ากัน",
    )
    if any(term in t for term in distance_terms):
        return "distance"

    overall_terms = (
        "ร้านไหนดีกว่า", "อันไหนดีกว่า", "ตัวไหนดีกว่า", "ไหนดีกว่า",
        "ร้านไหนเหมาะกว่า", "อันไหนเหมาะกว่า", "ไหนเหมาะกว่า",
        "ร้านไหนดี", "เลือกอันไหน", "เลือกร้านไหน", "ควรเลือกร้านไหน",
        "ร้านไหนดีที่สุด", "อันไหนดีที่สุด",
    )
    if any(term in t for term in overall_terms):
        return "overall"
    return None


def _detect_reference_fact(text: str) -> str | None:
    t = re.sub(r"\s+", "", str(text or "").casefold())
    groups = (
        ("hours", ("เปิดกี่โมง", "ปิดกี่โมง", "เวลาเปิด", "เวลาปิด", "เวลาทำการ", "เปิดไหม", "เปิดหรือยัง", "เปิดอยู่ไหม", "openinghours", "hours")),
        ("parking", ("มีที่จอด", "ที่จอดรถ", "จอดรถ", "parking")),
        ("phone", ("เบอร์โทร", "เบอร์", "โทรศัพท์", "โทรหา", "phone", "telephone")),
        ("website", ("เว็บไซต์", "เวบไซต์", "เว็บ", "web", "website")),
        ("address", ("ที่อยู่", "อยู่ตรงไหน", "อยู่ที่ไหน", "อยู่ไหน", "พิกัดร้าน", "address")),
    )
    for key, terms in groups:
        if any(re.sub(r"\s+", "", term.casefold()) in t for term in terms):
            return key
    return None


def _implicit_reference_index(text: str) -> int | None:
    t = re.sub(r"\s+", "", str(text or "").casefold())
    if any(term in t for term in ("ร้านนี้", "ร้านนั้น", "อันนี้", "อันนั้น", "ตัวนี้", "ตัวนั้น")):
        return 0
    return None


def _place_value(place: Any, *names: str) -> Any:
    if isinstance(place, Mapping):
        for name in names:
            if name in place:
                return place.get(name)
        return None
    for name in names:
        if hasattr(place, name):
            return getattr(place, name)
    return None


def _display_fact_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "มี" if value else "ไม่มี"
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, Mapping):
        parts = [f"{k}: {v}" for k, v in value.items() if v not in (None, "", (), [], {})]
        return ", ".join(parts) or None
    if isinstance(value, (list, tuple)):
        parts = [str(x).strip() for x in value if str(x).strip()]
        return ", ".join(parts) or None
    return str(value).strip() or None


def build_reference_fact_answer_v1(
    state: SemanticConversationStateV1,
    repository: Any,
) -> dict[str, Any] | None:
    """Read a referenced candidate fact from Published Projection only."""
    candidate_id = state.referenced_candidate_id
    fact = state.reference_fact
    if not candidate_id or fact not in _REFERENCE_FACT_KEYS:
        return None

    getter = getattr(repository, "get_published", None)
    place = getter(candidate_id) if callable(getter) else None
    if place is None:
        return {
            "candidate_id": candidate_id,
            "fact": fact,
            "status": "candidate_not_available",
            "answer": "ตอนนี้ยังอ่านข้อมูลของร้านที่อ้างถึงจาก Published Projection ไม่ได้ครับ",
            "source": "published_projection",
        }

    name = _display_fact_value(_place_value(place, "name")) or "ร้านที่เลือก"
    field_names = {
        "hours": ("opening_hours_text", "opening_hours", "hours_text", "hours"),
        "parking": ("parking_text", "parking", "has_parking"),
        "address": ("address_text", "address"),
        "phone": ("phone", "telephone"),
        "website": ("website", "url"),
        "price": ("price_text", "price"),
    }
    value = _display_fact_value(_place_value(place, *field_names[fact]))

    if value is None:
        labels = {
            "hours": "เวลาทำการ",
            "parking": "ที่จอดรถ",
            "address": "ที่อยู่",
            "phone": "เบอร์โทร",
            "website": "เว็บไซต์",
            "price": "ราคา",
        }
        return {
            "candidate_id": candidate_id,
            "fact": fact,
            "status": "unknown",
            "answer": f"ตอนนี้ข้อมูล{labels[fact]}ของ {name} ยังไม่มีในข้อมูลที่เผยแพร่ซึ่งระบบยืนยันครับ",
            "source": "published_projection",
        }

    if fact == "hours":
        answer = f"{name} มีข้อมูลเวลาทำการว่า {value} ครับ"
    elif fact == "parking":
        answer = f"ข้อมูลที่จอดรถของ {name}: {value} ครับ"
    elif fact == "address":
        answer = f"{name} อยู่ที่ {value} ครับ"
    elif fact == "phone":
        answer = f"เบอร์โทรของ {name}: {value} ครับ"
    elif fact == "website":
        answer = f"เว็บไซต์ของ {name}: {value} ครับ"
    else:
        answer = f"ข้อมูลราคาของ {name}: {value} ครับ"

    return {
        "candidate_id": candidate_id,
        "fact": fact,
        "status": "known",
        "answer": answer,
        "source": "published_projection",
    }


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


def resolve_semantic_turn_v1(
    user_text: str,
    context: Mapping[str, Any] | None = None,
    language_interpretation: Mapping[str, Any] | None = None,
) -> SemanticTurnResolutionV1:
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("user_text required")
    context = dict(context or {})
    previous = state_from_payload(context.pop("conversation_state", None))
    if isinstance(language_interpretation, Mapping):
        resolved = _resolve_from_language_brain_v1(
            user_text.strip(), context, previous, language_interpretation
        )
        if resolved is not None:
            return resolved
    # Deterministic phrase interpretation below is compatibility fallback only.
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
            reference_fact=None,
            comparison_criterion=None,
            explanation_request=None,
            language_act=None,
            semantic_criteria=(),
            language_confidence=None,
            last_user_text=user_text.strip(),
        )
        return SemanticTurnResolutionV1(user_text.strip(), context, state, "new")

    direct = direct_text
    explanation_request = None
    comparison_criterion = _detect_comparison(user_text)
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
    referenced_candidate_id = previous.referenced_candidate_id
    reference_fact = _detect_reference_fact(user_text)
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
        referenced_candidate_id = None
        reference_fact = None
        comparison_criterion = None
        explanation_request = None
        if direct.province:
            context["location_text"] = user_text.strip()
        mode = "new_intent"
    else:
        if direct.category:
            category = direct.category
        if direct.decision_object:
            decision_object = direct.decision_object
        if (add or remove) and comparison_criterion is None and explanation_request is None:
            candidate_ids = ()
        if near_update is not None:
            if near_update != near_me and comparison_criterion is None and explanation_request is None:
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
    if ref_index is None:
        ref_index = _implicit_reference_index(user_text)
    if ref_index is not None:
        if ref_index < len(candidate_ids):
            referenced_candidate_id = candidate_ids[ref_index]
            mode = "reference"
        else:
            referenced_candidate_id = None
            mode = "reference_unresolved"

    if reference_fact:
        comparison_criterion = None
        explanation_request = None
        if referenced_candidate_id:
            mode = "reference_fact"
        else:
            mode = "reference_unresolved"
    elif explanation_request:
        reference_fact = None
        referenced_candidate_id = None
        # Keep the last comparison criterion so "เพราะอะไร" after a distance
        # comparison re-evaluates the same decision frame through DQE.
        comparison_criterion = previous.comparison_criterion
        mode = "decision_explanation" if candidate_ids else "decision_explanation_unresolved"
    elif comparison_criterion:
        reference_fact = None
        explanation_request = None
        referenced_candidate_id = None
        if comparison_criterion == "distance":
            near_me = True
        mode = "comparison" if len(candidate_ids) >= 2 else "comparison_unresolved"
    elif mode != "reference":
        reference_fact = None
        comparison_criterion = None
        explanation_request = None

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
        reference_fact=reference_fact,
        comparison_criterion=comparison_criterion,
        explanation_request=explanation_request,
        language_act=None,
        semantic_criteria=previous.semantic_criteria,
        language_confidence=None,
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
    if state.reference_fact and state.referenced_candidate_id:
        candidate_ids = state.candidate_ids
        referenced = state.referenced_candidate_id
    else:
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
