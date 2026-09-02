"""Intent & Context Understanding V1.

Deterministic natural-language understanding boundary for PrachinLife.
It translates user language into a structured decision request without
ranking candidates, reading canonical storage, calling providers, or
fabricating missing facts.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Mapping, Any

from .consumer_decision_contract_v1 import (
    ConsumerCondition,
    ConsumerContext,
    ConsumerDecisionRequest,
)

UNDERSTANDING_VERSION = "ICU-V1.2"

_THAI_HIGH_CONFIDENCE_NORMALIZATION = {
    "ปั้ม": "ปั๊ม",
    "อาหาน": "อาหาร",
    "ปทุมทานี": "ปทุมธานี",
    "พุ่งนี้": "พรุ่งนี้",
    "มังสะวิรัติ": "มังสวิรัติ",
    "มังสวิรัด": "มังสวิรัติ",
    "รัาน": "ร้าน",
}

def normalize_noisy_input(text: str) -> str:
    """Normalize only high-confidence surface noise; never invent intent."""
    normalized = unicodedata.normalize("NFC", str(text or "")).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    for noisy, canonical in _THAI_HIGH_CONFIDENCE_NORMALIZATION.items():
        normalized = normalized.replace(noisy, canonical)
    return normalized


_PROVINCE_ALIASES = {
    "ปทุมธานี": ("ปทุมธานี", "ปทุม", "pathum thani", "pathum"),
    "ปราจีนบุรี": ("ปราจีนบุรี", "ปราจีน", "prachinburi", "prachin"),
    "กรุงเทพมหานคร": ("กรุงเทพมหานคร", "กรุงเทพ", "กทม", "bangkok"),
    "ฉะเชิงเทรา": ("ฉะเชิงเทรา", "แปดริ้ว", "chachoengsao"),
    "ชลบุรี": ("ชลบุรี", "chonburi"),
}

_CATEGORY_RULES = (
    ("vegetarian", ("อาหารเจ", "ร้านเจ", "กินเจ", "เจ", "มังสวิรัติ", "vegan", "vegetarian")),
    ("shopping", ("ซื้อของ", "ช้อป", "shopping", "ห้าง", "ซูเปอร์", "สินค้า", "ของใช้")),
    ("service", ("บริการ", "ซ่อม", "ร้านยา", "คลินิก", "คลีนิก", "ปั๊ม", "เติมน้ำมัน", "service")),
    ("go", ("เที่ยว", "ที่เที่ยว", "วัด", "สวน", "ไปไหนดี", "สถานที่", "attraction")),
    ("eat", ("กินอะไร", "กินข้าว", "ร้านอาหาร", "คาเฟ่", "กาแฟ", "อาหาร", "restaurant", "cafe")),
)


_DECISION_OBJECT_RULES = (
    ("fuel_station", "service", (
        r"(?:หา|เลือก|แนะนำ)?\s*(?:ปั๊ม|สถานีบริการน้ำมัน)(?:ไหนดี|ไหน|ใกล้|แถว|ที่)?",
        r"(?:เติมน้ำมัน).*?(?:ที่ไหนดี|ปั๊มไหน|ไหนดี)",
    )),
    ("restaurant", "vegetarian", (
        r"(?:หา|เลือกร้าน|แนะนำ)?\s*(?:ร้านเจ|ร้านอาหารเจ|ร้านมังสวิรัติ|อาหารเจ).*?(?:ไหนดี|ไหน|ใกล้|แถว|ที่)?",
    )),
    ("restaurant", "eat", (
        r"(?:หา|เลือกร้าน|แนะนำ)?\s*(?:ร้านอาหาร|ร้านข้าว|ร้านกิน|คาเฟ่|ร้านกาแฟ).*?(?:ไหนดี|ไหน|ใกล้|แถว|ที่)?",
        r"(?:กินข้าว|กินอะไร).*?(?:ไหนดี|ที่ไหน|แถวไหน)?",
    )),
    ("shop", "shopping", (
        r"(?:หา|เลือก|แนะนำ)?\s*(?:ร้านค้า|ห้าง|ซูเปอร์|ซูเปอร์มาร์เก็ต|ที่ซื้อของ).*?(?:ไหนดี|ไหน|ใกล้|แถว|ที่)?",
        r"(?:ซื้อของ|ช้อป).*?(?:ไหนดี|ที่ไหน|ไหน)?",
    )),
    ("destination", "go", (
        r"(?:หา|เลือก|แนะนำ)?\s*(?:ที่เที่ยว|สถานที่เที่ยว|วัด|สวน).*?(?:ไหนดี|ไหน|ใกล้|แถว|ที่)?",
        r"(?:เที่ยว|พา.*?เที่ยว).*?(?:ไหนดี|ที่ไหน|ไหน)?",
    )),
    ("service_place", "service", (
        r"(?:หา|เลือก|แนะนำ)?\s*(?:ร้านซ่อม|คลินิก|คลีนิก|ร้านยา|บริการ).*?(?:ไหนดี|ไหน|ใกล้|แถว|ที่)?",
    )),
)

_REFERENCE_PATTERNS = (
    ("fuel_station", (r"(?:แถว|ใกล้|ข้าง|ตรง|บริเวณ)\s*(?:ปั๊ม|สถานีบริการน้ำมัน)(?:\s*[\wก-๙.]+)?",)),
)

_FOOD_VARIETY_TERMS = ("อาหารเยอะ", "ของกินเยอะ", "ร้านอาหารเยอะ", "อาหารหลาย", "ของกินหลาย", "food variety")
_PARKING_TERMS = ("มีที่จอดรถ", "ที่จอดรถ", "จอดรถสะดวก", "parking")
_ROUTE_TERMS = ("ทางผ่าน", "ระหว่างทาง", "ตามทาง", "route")

_GOAL_BY_OBJECT = {
    "fuel_station": "find_fuel_station",
    "restaurant": "find_place_to_eat",
    "shop": "find_place_to_shop",
    "destination": "find_place_to_go",
    "service_place": "find_service",
}

_GOAL_BY_CATEGORY = {
    "vegetarian": "find_place_to_eat",
    "eat": "find_place_to_eat",
    "shopping": "find_place_to_shop",
    "go": "find_place_to_go",
    "service": "find_service",
}

_TIME_RULES = (
    ("tomorrow", ("พรุ่งนี้", "tomorrow")),
    ("today", ("วันนี้", "today")),
    ("now", ("ตอนนี้", "เดี๋ยวนี้", "ขณะนี้", "now")),
    ("tonight", ("คืนนี้", "tonight")),
    ("lunch", ("เที่ยง", "มื้อเที่ยง", "กลางวัน", "lunch")),
    ("dinner", ("เย็นนี้", "มื้อเย็น", "dinner")),
)

_NEAR_ME_TERMS = ("ใกล้ฉัน", "แถวนี้", "ใกล้ๆ", "ใกล้ ๆ", "ใกล้ที่สุด", "near me", "nearby")
_RECOMMEND_TERMS = ("ที่ไหนดี", "ไหนดี", "แนะนำ", "ช่วยเลือก", "ควรไป", "ควรกิน", "best")
_PRICE_TERMS = ("ประหยัด", "ถูก", "ราคาไม่แพง", "คุ้ม", "งบน้อย", "ปลายเดือน")
_FAMILY_TERMS = ("ครอบครัว", "เด็ก", "ลูก", "ผู้สูงอายุ", "พ่อแม่")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").strip().casefold()
    return re.sub(r"\s+", " ", text)


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(_norm(term) in text for term in terms)


def _extract_province(text: str) -> str | None:
    for canonical, aliases in _PROVINCE_ALIASES.items():
        if any(_norm(alias) in text for alias in aliases):
            return canonical
    return None



def _extract_decision_object(text: str) -> tuple[str | None, str | None]:
    """Return the entity being chosen, not every entity merely mentioned.

    Patterns are deliberately anchored to choice/search language.  This lets
    "หาร้านอาหารแถวปั๊ม" choose a restaurant while treating the fuel station
    as a reference, whereas "หาปั๊มไหนดีที่มีอาหารเยอะ" chooses a fuel station.
    """
    candidates=[]
    for object_type, category, patterns in _DECISION_OBJECT_RULES:
        for pattern in patterns:
            m=re.search(pattern, text)
            if m:
                candidates.append((m.start(), -(m.end()-m.start()), object_type, category))
    if not candidates:
        return None, None
    candidates.sort()
    _,_,obj,category=candidates[0]
    return obj,category


def _extract_references(text: str, decision_object: str | None) -> tuple[str, ...]:
    refs=[]
    for ref_type, patterns in _REFERENCE_PATTERNS:
        if ref_type == decision_object:
            continue
        if any(re.search(pattern,text) for pattern in patterns):
            refs.append(ref_type)
    return tuple(dict.fromkeys(refs))

def _extract_category(text: str) -> str | None:
    for category, terms in _CATEGORY_RULES:
        if _contains(text, terms):
            return category
    return None


def _extract_time_context(text: str) -> tuple[str | None, tuple[str, ...]]:
    found=[]
    for label, terms in _TIME_RULES:
        if _contains(text, terms):
            found.append(label)
    if not found:
        return None, ()
    # Preserve all recognized temporal signals for audit; first is primary.
    return found[0], tuple(dict.fromkeys(found))


@dataclass(frozen=True)
class StructuredDecisionRequest:
    user_text: str
    goal: str
    decision_type: str
    category: str | None
    decision_object: str | None
    references: tuple[str, ...]
    province: str | None
    temporal_context: str | None
    temporal_signals: tuple[str, ...]
    near_me: bool
    hard_constraints: tuple[ConsumerCondition, ...]
    preferences: tuple[ConsumerCondition, ...]
    inferred_context: Mapping[str, Any]
    unresolved_context: tuple[str, ...]
    confidence: float
    understanding_version: str = UNDERSTANDING_VERSION

    def to_consumer_request(self, request_id: str) -> ConsumerDecisionRequest:
        if self.category is None:
            raise ValueError("category unresolved; cannot create ConsumerDecisionRequest")
        return ConsumerDecisionRequest(
            request_id=request_id,
            goal=self.goal,
            category=self.category,
            hard_constraints=self.hard_constraints,
            preferences=self.preferences,
            context=ConsumerContext(
                budget_sensitivity=("high" if self.inferred_context.get("budget_sensitive") else None),
                with_children=self.inferred_context.get("with_children"),
                with_elderly=self.inferred_context.get("with_elderly"),
            ),
        )


def _understand_user_request_core(user_text: str, context: Mapping[str, Any] | None = None) -> StructuredDecisionRequest:
    """Translate user language into a deterministic decision request.

    This function only interprets the user's request. It does not search data,
    evaluate candidates, decide rankings, infer opening hours, or call an LLM.
    """
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("user_text required")

    normalized_user_text = normalize_noisy_input(user_text)
    text = _norm(normalized_user_text)

    decision_object, object_category=_extract_decision_object(text)
    category=object_category or _extract_category(text)
    references=_extract_references(text, decision_object)
    province=_extract_province(text)
    temporal_context, temporal_signals=_extract_time_context(text)
    near_me=_contains(text, _NEAR_ME_TERMS)
    wants_recommendation=_contains(text, _RECOMMEND_TERMS)

    goal=_GOAL_BY_OBJECT.get(decision_object, _GOAL_BY_CATEGORY.get(category, "find_local_option"))
    decision_type="select" if wants_recommendation or category else "clarify"

    hard=[]
    prefs=[]
    unresolved=[]
    inferred={}

    explicit_location_text = None
    if context and context.get("location_text") is not None:
        if not isinstance(context.get("location_text"), str):
            raise ValueError("location_text must be a string")
        explicit_location_text = context.get("location_text").strip() or None
        if explicit_location_text and len(explicit_location_text) > 200:
            raise ValueError("location_text too long")

    if province:
        hard.append(ConsumerCondition("province", province, strength="hard", operator="eq", source="user"))
    elif not near_me and not explicit_location_text:
        unresolved.append("location")

    if category == "vegetarian":
        # RealCandidateMapping exposes a supported vegetarian boolean derived
        # from published categories. Absence remains unresolved downstream.
        hard.append(ConsumerCondition("vegetarian", True, strength="hard", operator="eq", source="user"))

    if near_me:
        inferred["near_me"] = True
        # Exact origin must come from trusted runtime/user context. A user-
        # supplied location_text is an explicit area fallback, never invented
        # coordinates and never treated as distance evidence.
        if not context or (
            not context.get("current_location")
            and not explicit_location_text
        ):
            unresolved.append("current_location")

    if explicit_location_text:
        inferred["location_text"] = explicit_location_text

    if temporal_context:
        inferred["temporal_context"] = temporal_context
        # Time phrases are context, not proof that a candidate is open.
        if temporal_context in {"tomorrow","today","now","tonight","lunch","dinner"}:
            unresolved.append("open_status_for_requested_time")

    if _contains(text, _PRICE_TERMS):
        inferred["budget_sensitive"] = True
        prefs.append(ConsumerCondition("price", None, strength="soft", weight=1.0, operator="lte", source="user"))
        unresolved.append("price")

    if _contains(text, _FAMILY_TERMS):
        inferred["family_context"] = True
        inferred["with_children"] = "เด็ก" in text or "ลูก" in text
        inferred["with_elderly"] = "ผู้สูงอายุ" in text or "พ่อแม่" in text
        unresolved.append("family_suitability")

    # Criteria describe what makes the chosen object better; they are not goals.
    if _contains(text, _FOOD_VARIETY_TERMS):
        prefs.append(ConsumerCondition("food_variety", "high", strength="soft", weight=1.0, operator="eq", source="user"))
        unresolved.append("food_variety")
    if _contains(text, _PARKING_TERMS):
        strength="hard" if _contains(text,("ต้องมีที่จอดรถ","ต้องมี parking")) else "soft"
        condition=ConsumerCondition("parking", True, strength=strength, weight=1.0, operator="eq", source="user")
        if strength=="hard": hard.append(condition)
        else: prefs.append(condition)
        unresolved.append("parking")
    if _contains(text, _ROUTE_TERMS):
        prefs.append(ConsumerCondition("route_fit", True, strength="soft", weight=1.0, operator="eq", source="user"))
        unresolved.append("route_fit")

    # Exact area is often the highest-value missing personal context for a
    # province-level recommendation, but it is not a hard failure by itself.
    if province and not near_me:
        unresolved.append("exact_area_or_route")

    # Preserve context supplied by trusted caller without interpreting it as
    # evidence about candidates.
    if context:
        for key in ("current_location","transport_mode","group_size","budget_sensitivity"):
            if key in context and context[key] is not None:
                inferred[key]=context[key]

    unresolved=tuple(dict.fromkeys(unresolved))
    confidence=0.35
    if category: confidence += 0.30
    if province or near_me: confidence += 0.20
    if wants_recommendation: confidence += 0.10
    if temporal_context: confidence += 0.05
    confidence=min(1.0, confidence)

    return StructuredDecisionRequest(
        user_text=user_text,
        goal=goal,
        decision_type=decision_type,
        category=category,
        decision_object=decision_object,
        references=references,
        province=province,
        temporal_context=temporal_context,
        temporal_signals=temporal_signals,
        near_me=near_me,
        hard_constraints=tuple(hard),
        preferences=tuple(prefs),
        inferred_context=inferred,
        unresolved_context=unresolved,
        confidence=confidence,
    )


def build_consumer_decision_request(
    user_text: str,
    request_id: str,
    context: Mapping[str, Any] | None = None,
) -> tuple[StructuredDecisionRequest, ConsumerDecisionRequest]:
    """Understand natural language and build the contract consumed by the Brain pipeline."""
    understood = understand_user_request(user_text, context)
    return understood, understood.to_consumer_request(request_id)

# THAI_QUERY_NORMALIZATION_V1_WRAPPER
def understand_user_request(user_text, *args, **kwargs):
    """Public ICU entry point with conservative Thai user-language normalization.

    The original user text is restored on the structured result for audit/display.
    Normalization affects intent understanding only; it is not canonical identity matching.
    """
    from dataclasses import replace as _dc_replace
    from .thai_query_normalization_v1 import normalize_thai_query_v1 as _normalize_thai_query_v1

    _original_user_text = user_text
    _normalized_user_text = _normalize_thai_query_v1(user_text)
    _result = _understand_user_request_core(_normalized_user_text, *args, **kwargs)

    if hasattr(_result, "user_text"):
        try:
            _result = _dc_replace(_result, user_text=_original_user_text)
        except (TypeError, ValueError):
            pass
    return _result


try:
    import inspect as _inspect
    understand_user_request.__signature__ = _inspect.signature(_understand_user_request_core)
except (TypeError, ValueError):
    pass

