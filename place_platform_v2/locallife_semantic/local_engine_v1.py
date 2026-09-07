from __future__ import annotations
import re
from typing import Iterable, Tuple
from .contract_v1 import (
    LOCAL_CONFIDENCE_GATE, LocationIntent, LocationKind, SemanticConstraint,
    SemanticEntity, SemanticIntent, SemanticPreference, SemanticResult,
    TimeContext, TimeKind,
)

TYPO_MAP = {
    "ไกล้ฉัน": "ใกล้ฉัน", "ไกล้ๆ": "ใกล้ๆ", "ไกล้ผม": "ใกล้ผม",
    "รคา": "ราคา", "มังสวิรัต": "มังสวิรัติ", "มังสวิรัตติ": "มังสวิรัติ",
    "ปทุมธานีี": "ปทุมธานี", "ปราจีนบุรึ": "ปราจีนบุรี", "คาเฟ": "คาเฟ่",
    "เทียบกันหนอ่ย": "เทียบกันหน่อย", "เปิดยุ": "เปิดอยู่", "ตอนนี": "ตอนนี้",
}

CATEGORY_RULES = (
    ("vegetarian", ("อาหารเจ", "ร้านเจ", "กินเจ", "มังสวิรัติ", "vegetarian")),
    ("vegan", ("vegan", "วีแกน")),
    ("restaurant", ("ร้านอาหาร", "ที่กิน", "กินอะไร", "ของกิน", "อาหารอร่อย")),
    ("cafe", ("คาเฟ่", "กาแฟ", "coffee")),
    ("fuel", ("ปั๊ม", "ปตท", "ปตท.", "ptt", "น้ำมัน")),
    ("temple", ("วัด", "ทำบุญ")),
    ("attraction", ("ที่เที่ยว", "เที่ยว", "แหล่งท่องเที่ยว")),
    ("park", ("สวนสาธารณะ", "สวนพักผ่อน")),
    ("nature", ("ธรรมชาติ", "น้ำตก", "ภูเขา")),
    ("laundry", ("ซักผ้า", "ร้านซักรีด", "laundry")),
    ("car_repair", ("ซ่อมรถ", "อู่รถ", "อู่ซ่อม")),
    ("clinic", ("คลินิก",)),
    ("pharmacy", ("ร้านยา", "เภสัช")),
)

PROVINCE_ALIASES = {
    "กรุงเทพ": "กรุงเทพมหานคร", "กทม": "กรุงเทพมหานคร", "กทม.": "กรุงเทพมหานคร",
    "โคราช": "นครราชสีมา", "อยุธยา": "พระนครศรีอยุธยา",
}
PROVINCES = (
    "กรุงเทพมหานคร","กระบี่","กาญจนบุรี","กาฬสินธุ์","กำแพงเพชร","ขอนแก่น","จันทบุรี","ฉะเชิงเทรา",
    "ชลบุรี","ชัยนาท","ชัยภูมิ","ชุมพร","เชียงราย","เชียงใหม่","ตรัง","ตราด","ตาก","นครนายก",
    "นครปฐม","นครพนม","นครราชสีมา","นครศรีธรรมราช","นครสวรรค์","นนทบุรี","นราธิวาส","น่าน",
    "บึงกาฬ","บุรีรัมย์","ปทุมธานี","ประจวบคีรีขันธ์","ปราจีนบุรี","ปัตตานี","พระนครศรีอยุธยา",
    "พังงา","พัทลุง","พิจิตร","พิษณุโลก","เพชรบุรี","เพชรบูรณ์","แพร่","พะเยา","ภูเก็ต",
    "มหาสารคาม","มุกดาหาร","แม่ฮ่องสอน","ยโสธร","ยะลา","ร้อยเอ็ด","ระนอง","ระยอง","ราชบุรี",
    "ลพบุรี","ลำปาง","ลำพูน","เลย","ศรีสะเกษ","สกลนคร","สงขลา","สตูล","สมุทรปราการ","สมุทรสงคราม",
    "สมุทรสาคร","สระแก้ว","สระบุรี","สิงห์บุรี","สุโขทัย","สุพรรณบุรี","สุราษฎร์ธานี","สุรินทร์",
    "หนองคาย","หนองบัวลำภู","อ่างทอง","อำนาจเจริญ","อุดรธานี","อุตรดิตถ์","อุทัยธานี","อุบลราชธานี",
)

LOW_INFO_EXACT = {"หาที่กินหน่อย", "ช่วยหน่อย", "เอาไหนดี", "หาให้หน่อย", "มีอะไรบ้าง", "แนะนำหน่อย"}


def normalize_text(text: str) -> str:
    s = " ".join((text or "").strip().split())
    for bad, good in TYPO_MAP.items():
        s = s.replace(bad, good)
    s = re.sub(r"\s+", " ", s)
    return s


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    lower = text.lower()
    return any(t.lower() in lower for t in terms)


def _category_hints(text: str) -> Tuple[str, ...]:
    out = []
    for cat, terms in CATEGORY_RULES:
        if _contains_any(text, terms):
            out.append(cat)
    # Specific food identity outranks generic restaurant as a hint, but this is not candidate ranking.
    if ("vegetarian" in out or "vegan" in out) and "restaurant" in out:
        out.remove("restaurant")
    return tuple(dict.fromkeys(out))


def _location(text: str) -> LocationIntent:
    if _contains_any(text, ("ใกล้ฉัน", "ใกล้ๆ", "แถวนี้", "ใกล้ผม", "ใกล้เรา", "near me")):
        return LocationIntent(LocationKind.NEAR_ME, None)
    for alias, canonical in PROVINCE_ALIASES.items():
        if alias in text:
            return LocationIntent(LocationKind.EXPLICIT, canonical)
    for p in PROVINCES:
        if p in text:
            return LocationIntent(LocationKind.EXPLICIT, p)
    m = re.search(r"(?:แถว|ใกล้|ข้าง|รอบ|ตรง)\s*([^,?.]{2,50})", text, flags=re.IGNORECASE)
    if m:
        landmark = m.group(1).strip()
        landmark = re.split(r"\s+(?:ที่|ซึ่ง|ราคา|เปิด|ไม่เกิน|อยาก|และ)\b", landmark)[0].strip()
        if landmark and landmark not in {"ฉัน", "นี้", "ๆ", "ผม", "เรา"}:
            return LocationIntent(LocationKind.LANDMARK, landmark)
    return LocationIntent()


def _time(text: str) -> TimeContext:
    if _contains_any(text, ("ตอนนี้", "เดี๋ยวนี้", "เปิดอยู่ไหม", "เปิดไหมตอนนี้", "ตอนนี้เปิด", "now")):
        return TimeContext(TimeKind.NOW)
    if _contains_any(text, ("วันนี้", "เย็นนี้", "คืนนี้", "today", "tonight")):
        return TimeContext(TimeKind.TODAY)
    if _contains_any(text, ("พรุ่งนี้", "tomorrow")):
        return TimeContext(TimeKind.TOMORROW)
    return TimeContext()


def _intent(text: str) -> SemanticIntent:
    # Mutation/publication instructions are outside the semantic decision-intent surface.
    if _contains_any(text, ("canonical", "publish", "publication", "เขียนลงฐาน", "บันทึกลงฐาน")):
        return SemanticIntent.UNKNOWN
    if _contains_any(text, ("เทียบ", "เปรียบเทียบ", "อันไหนดีกว่า", "ไหนดีกว่า", "ต่างกันยังไง", "เทียบกัน")):
        return SemanticIntent.COMPARE_PLACES
    if _contains_any(text, ("ช่วยเลือก", "ควรเลือก", "เลือกไหนดี", "ไหนดี", "ควรไป", "แนะนำที่เหมาะ", "เลือกร้าน", "เลือกที่")):
        return SemanticIntent.DECIDE
    if _contains_any(text, ("ทำไม", "เพราะอะไร", "อธิบาย", "เหตุผล")):
        return SemanticIntent.EXPLAIN
    if _contains_any(text, ("หา", "ร้าน", "ที่กิน", "คาเฟ่", "วัด", "ปั๊ม", "คลินิก", "ร้านยา", "ใกล้ฉัน", "แถวนี้", "ที่เที่ยว", "ซักผ้า", "ซ่อมรถ", "coffee", "near me")):
        return SemanticIntent.FIND_PLACE
    return SemanticIntent.UNKNOWN


def _extract_entities(text: str, intent: SemanticIntent) -> Tuple[SemanticEntity, ...]:
    out = []
    if intent == SemanticIntent.COMPARE_PLACES:
        cleaned = re.sub(r"(?:อันไหนดีกว่า|ไหนดีกว่า|ต่างกันยังไง|ช่วยเทียบ|เปรียบเทียบ|เทียบกันหน่อย|เทียบกัน)", "", text, flags=re.IGNORECASE).strip(" ?.,")
        parts = re.split(r"\s+(?:กับ|vs\.?|versus)\s+", cleaned, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            left = parts[0].strip(" ?.,")
            right = parts[1].strip(" ?.,")
            if 1 < len(left) <= 80:
                out.append(SemanticEntity("place_reference", left, 0.86))
            if 1 < len(right) <= 80:
                out.append(SemanticEntity("place_reference", right, 0.86))
    return tuple(out)


def understand_local(text: str) -> SemanticResult:
    raw = text or ""
    norm = normalize_text(raw)
    cats = _category_hints(norm)
    loc = _location(norm)
    tim = _time(norm)
    intent = _intent(norm)
    entities = _extract_entities(norm, intent)
    constraints = []
    preferences = []
    ambiguities = []

    if _contains_any(norm, ("ราคาไม่แรง", "ไม่แพง", "ราคาถูก", "ประหยัด", "งบไม่เยอะ")):
        preferences.append(SemanticPreference("price", "affordable", 0.90))
    if _contains_any(norm, ("ที่จอดรถ", "มีที่จอด", "จอดรถง่าย")):
        preferences.append(SemanticPreference("parking", True, 0.92))
    if _contains_any(norm, ("เปิดวันนี้", "วันนี้เปิด", "เปิดตอนนี้", "เปิดอยู่ไหม", "เปิด 24 ชั่วโมง", "24 ชั่วโมง", "24ชม")) or tim.kind == TimeKind.NOW:
        constraints.append(SemanticConstraint("open_at_requested_time", True, "hard", 0.88))
    if _contains_any(norm, ("เปิด 24 ชั่วโมง", "24 ชั่วโมง", "24ชม")):
        constraints.append(SemanticConstraint("open_24_hours", True, "hard", 0.94))
    m = re.search(r"(?:ไม่เกิน|ภายใน)\s*(\d+(?:\.\d+)?)\s*(?:กม|km)", norm, flags=re.IGNORECASE)
    if m:
        constraints.append(SemanticConstraint("distance_km_max", float(m.group(1)), "hard", 0.96))

    signals = 0.0
    signals += 1.0 if intent != SemanticIntent.UNKNOWN else 0.0
    signals += 1.0 if cats else 0.0
    signals += 1.0 if loc.kind != LocationKind.UNSPECIFIED else 0.0
    signals += 1.0 if tim.kind != TimeKind.UNSPECIFIED else 0.0
    signals += 1.0 if constraints or preferences else 0.0
    signals += 1.0 if len(entities) >= 2 else 0.0

    confidence = min(0.96, 0.24 + signals * 0.14)
    if intent == SemanticIntent.COMPARE_PLACES and len(entities) >= 2:
        confidence = max(confidence, 0.74)
    if len(norm) < 5:
        confidence = min(confidence, 0.28)
    if intent == SemanticIntent.UNKNOWN:
        ambiguities.append("primary_intent")
    if intent in (SemanticIntent.FIND_PLACE, SemanticIntent.DECIDE) and not cats:
        ambiguities.append("category")
    if intent == SemanticIntent.COMPARE_PLACES and len(entities) < 2:
        ambiguities.append("comparison_targets")
    if loc.kind == LocationKind.NEAR_ME:
        ambiguities.append("user_location_coordinates")
    if norm in LOW_INFO_EXACT:
        ambiguities.append("low_information_query")
        confidence = min(confidence, 0.45)

    fallback_eligible = confidence < LOCAL_CONFIDENCE_GATE or "low_information_query" in ambiguities
    return SemanticResult(
        raw_text=raw,
        normalized_text=norm,
        primary_intent=intent,
        entity_mentions=entities,
        category_hints=cats,
        constraints=tuple(constraints),
        preferences=tuple(preferences),
        location_intent=loc,
        time_context=tim,
        comparison_intent=intent == SemanticIntent.COMPARE_PLACES,
        confidence=round(confidence, 3),
        unresolved_ambiguities=tuple(dict.fromkeys(ambiguities)),
        fallback_eligible=fallback_eligible,
    )
