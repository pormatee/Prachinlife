from __future__ import annotations

import re
import unicodedata

THAI_QUERY_NORMALIZATION_VERSION = "THAI-QUERY-NORMALIZATION-V1"

# Conservative, explainable phrase corrections only.
# This is NOT fuzzy place-identity matching and MUST NOT be used for canonical resolution.
_PHRASE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"รานอาหารเจ"), "ร้านอาหารเจ"),
    (re.compile(r"รานเจ"), "ร้านเจ"),
    (re.compile(r"ไปเทียว(?=(?:ไหนดี|ไหน|ที่|แถว|ใกล้|กัน|$))"), "ไปเที่ยว"),
    (re.compile(r"(?<![\u0E00-\u0E7F])เทียว(?=(?:ไหนดี|ไหน|ที่|แถว|ใกล้|กัน|$))"), "เที่ยว"),
    (re.compile(r"ไกล้(?=(?:ฉัน|ๆ|หน่อย|กว่านี้|ที่สุด|บ้าน|แถว|$))"), "ใกล้"),
    (re.compile(r"มีเดก(?=(?:ด้วย|ไป|$))"), "มีเด็ก"),
    (re.compile(r"พาเดก(?=(?:ไป|เที่ยว|กิน|$))"), "พาเด็ก"),
    (re.compile(r"ไปกับเดก(?=(?:$|\s))"), "ไปกับเด็ก"),
    (re.compile(r"(?<![\u0E00-\u0E7F])ปาจีน(?![\u0E00-\u0E7F])"), "ปราจีนบุรี"),
    (re.compile(r"แถวปาจีน"), "แถวปราจีนบุรี"),
)

def normalize_thai_query_v1(text: str) -> str:
    """Normalize a small allowlist of high-value Thai user-input errors.

    Safety boundary:
    - phrase-level user-language normalization only;
    - no edit-distance/fuzzy matching;
    - no canonical place resolution;
    - no sponsor/provider/ranking behavior;
    - original text should be retained by the caller for audit/display.
    """
    value = unicodedata.normalize("NFKC", str(text))
    value = " ".join(value.split())
    for pattern, replacement in _PHRASE_RULES:
        value = pattern.sub(replacement, value)
    return value
