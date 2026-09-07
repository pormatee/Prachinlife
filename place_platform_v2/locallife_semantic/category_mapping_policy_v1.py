
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import unicodedata
from typing import Iterable

POLICY_VERSION = "LOCALLIFE-SEMANTIC-CATEGORY-MAPPING-POLICY-CHALLENGE-V1"

class MappingDecision(str, Enum):
    PROMOTE = "PROMOTE"
    PRESERVE_EXISTING = "PRESERVE_EXISTING"
    BROAD_DOMAIN_ONLY = "BROAD_DOMAIN_ONLY"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"
    UNSUPPORTED = "UNSUPPORTED"

class EvidenceTier(str, Enum):
    EXACT = "EXACT"
    SAFE_ALIAS = "SAFE_ALIAS"
    BROAD = "BROAD"
    NONE = "NONE"
    CONFLICT = "CONFLICT"

@dataclass(frozen=True)
class CategoryEvidence:
    category: str
    tier: EvidenceTier
    matched_terms: tuple[str, ...] = ()

@dataclass(frozen=True)
class CategoryMappingResult:
    decision: MappingDecision
    promoted_category: str | None
    evidence: tuple[CategoryEvidence, ...]
    reason: str
    local_hint_used_as_authority: bool = False

# The mapping vocabulary is deliberately small and explicit.
# It is a semantic compatibility vocabulary, NOT a canonical-place authority.
CATEGORY_TERMS = {
    "vegetarian": {
        "exact": ("ร้านเจ", "อาหารเจ", "มังสวิรัติ", "ร้านมังสวิรัติ", "vegetarian"),
        "safe_alias": ("กินเจ", "เจล้วน", "อาหารมังสวิรัติ"),
    },
    "vegan": {
        "exact": ("วีแกน", "vegan", "ร้านวีแกน"),
        "safe_alias": ("อาหารวีแกน",),
    },
    "restaurant": {
        "exact": ("ร้านอาหาร", "restaurant"),
        "safe_alias": ("ภัตตาคาร",),
    },
    "cafe": {
        "exact": ("คาเฟ่", "cafe", "coffee shop"),
        "safe_alias": ("ร้านกาแฟ",),
    },
    "fuel": {
        "exact": ("ปั๊มน้ำมัน", "สถานีบริการน้ำมัน", "fuel station", "gas station"),
        "safe_alias": ("ปั๊ม ปตท.", "ปั๊มptt", "ปั๊มบางจาก", "ปั๊มเชลล์", "ปั๊มเอสโซ่"),
    },
    "temple": {
        "exact": ("วัด", "temple"),
        "safe_alias": (),
    },
    "park": {
        "exact": ("สวนสาธารณะ", "park"),
        "safe_alias": (),
    },
    "attraction": {
        "exact": ("สถานที่ท่องเที่ยว", "แหล่งท่องเที่ยว", "attraction"),
        "safe_alias": (),
    },
    "laundry": {
        "exact": ("ร้านซักรีด", "laundry"),
        "safe_alias": ("ซักอบรีด",),
    },
    "car_repair": {
        "exact": ("อู่ซ่อมรถ", "ร้านซ่อมรถ", "car repair"),
        "safe_alias": ("อู่รถ",),
    },
    "clinic": {
        "exact": ("คลินิก", "clinic"),
        "safe_alias": (),
    },
    "pharmacy": {
        "exact": ("ร้านยา", "เภสัช", "pharmacy"),
        "safe_alias": ("ร้านขายยา",),
    },
    "nature": {
        "exact": ("แหล่งธรรมชาติ", "nature"),
        "safe_alias": (),
    },
}

# Broad goals are useful context but are NOT category authority.
BROAD_TERMS = {
    "food": ("หาที่กิน", "หาอะไรกิน", "กินอะไรดี", "ของกิน", "กินข้าว", "หาของกิน"),
    "travel": ("ที่เที่ยว", "เที่ยวไหนดี", "ไปเที่ยว", "หาอะไรทำ"),
    "service": ("บริการใกล้ฉัน", "หาร้านบริการ", "ช่วยหาบริการ"),
    "shopping": ("ช้อปปิ้ง", "shopping", "ซื้อของ"),
}

MUTATION_TERMS = ("publish", "canonical", "อนุมัติ", "ลงฐานข้อมูล", "เพิ่มเข้าฐาน", "แก้ production")

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\u200b", "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def _contains_term(text: str, term: str) -> bool:
    return normalize_text(term) in text

def collect_evidence(text: str) -> tuple[CategoryEvidence, ...]:
    norm = normalize_text(text)
    found = []
    for category, tiers in CATEGORY_TERMS.items():
        exact = tuple(t for t in tiers["exact"] if _contains_term(norm, t))
        aliases = tuple(t for t in tiers["safe_alias"] if _contains_term(norm, t))
        if exact:
            found.append(CategoryEvidence(category, EvidenceTier.EXACT, exact))
        elif aliases:
            found.append(CategoryEvidence(category, EvidenceTier.SAFE_ALIAS, aliases))
    return tuple(found)

def detect_broad_domain(text: str) -> tuple[str, ...]:
    norm = normalize_text(text)
    domains = []
    for domain, terms in BROAD_TERMS.items():
        if any(_contains_term(norm, t) for t in terms):
            domains.append(domain)
    return tuple(domains)

def decide_category_mapping(
    text: str,
    existing_category: str | None = None,
    local_category_hints: Iterable[str] = (),
) -> CategoryMappingResult:
    norm = normalize_text(text)
    hints = tuple(dict.fromkeys(str(x).strip() for x in local_category_hints if str(x).strip()))

    # Safety: mutation instructions are never semantic category promotion evidence.
    if any(term in norm for term in MUTATION_TERMS):
        return CategoryMappingResult(
            MappingDecision.UNSUPPORTED,
            None,
            (),
            "mutation_or_publication_instruction_not_category_authority",
            False,
        )

    evidence = collect_evidence(norm)
    categories = tuple(dict.fromkeys(e.category for e in evidence))
    broad_domains = detect_broad_domain(norm)

    # Existing resolved category remains authoritative in challenge V1.
    if existing_category is not None and str(existing_category).strip():
        return CategoryMappingResult(
            MappingDecision.PRESERVE_EXISTING,
            str(existing_category).strip(),
            evidence,
            "existing_category_preserved",
            False,
        )

    if len(categories) > 1:
        return CategoryMappingResult(
            MappingDecision.CONFLICT,
            None,
            evidence,
            "multiple_explicit_category_signals",
            False,
        )

    if len(categories) == 1:
        # Local hint may agree/disagree diagnostically, but is never the authority.
        return CategoryMappingResult(
            MappingDecision.PROMOTE,
            categories[0],
            evidence,
            "explicit_or_safe_alias_evidence",
            False,
        )

    if broad_domains:
        return CategoryMappingResult(
            MappingDecision.BROAD_DOMAIN_ONLY,
            None,
            (),
            "broad_goal_not_specific_category",
            False,
        )

    if hints:
        return CategoryMappingResult(
            MappingDecision.AMBIGUOUS,
            None,
            (),
            "local_hint_without_textual_category_evidence",
            False,
        )

    return CategoryMappingResult(
        MappingDecision.AMBIGUOUS,
        None,
        (),
        "no_supported_category_evidence",
        False,
    )
