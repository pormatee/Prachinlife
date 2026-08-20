from __future__ import annotations


SOURCE_SCORES = {
    "user_firsthand": 40,
    "verified_business_listing": 35,
    "official_website": 35,
    "osm_diet_only": 35,
    "osm_diet_yes": 20,
    "web_listing": 20,
    "community_submission": 10,
}


COORDINATE_SCORES = {
    "exact": 30,
    "address": 25,
    "market": 18,
    "area": 8,
    "unknown": 0,
}


def get_coordinate_precision(
    item,
):
    metadata = (
        item.get("metadata")
        or {}
    )

    value = metadata.get(
        "coordinate_precision"
    )

    if value in COORDINATE_SCORES:
        return value

    location = (
        item.get("location")
        or {}
    )

    lat = location.get("latitude")
    lon = location.get("longitude")

    if (
        isinstance(lat, (int, float))
        and
        isinstance(lon, (int, float))
    ):
        return "unknown"

    return "unknown"


def get_source_score(
    item,
):
    metadata = (
        item.get("metadata")
        or {}
    )

    source_type = metadata.get(
        "verification_source"
    )

    if source_type in SOURCE_SCORES:
        return SOURCE_SCORES[
            source_type
        ]

    evidence_reason = (
        metadata.get(
            "evidence_reason"
        )
        or ""
    ).lower()

    if "firsthand" in evidence_reason:
        return SOURCE_SCORES[
            "user_firsthand"
        ]

    if "verified" in evidence_reason:
        return SOURCE_SCORES[
            "verified_business_listing"
        ]

    if (
        "diet_only"
        in evidence_reason
    ):
        return SOURCE_SCORES[
            "osm_diet_only"
        ]

    if (
        "diet_yes"
        in evidence_reason
    ):
        return SOURCE_SCORES[
            "osm_diet_yes"
        ]

    if item.get("source_url"):
        return SOURCE_SCORES[
            "web_listing"
        ]

    return 0


def calculate_confidence(
    item,
):
    metadata = (
        item.get("metadata")
        or {}
    )

    score = 0
    reasons = []

    source_score = (
        get_source_score(
            item
        )
    )

    score += source_score

    if source_score:
        reasons.append(
            f"source:{source_score}"
        )

    precision = (
        get_coordinate_precision(
            item
        )
    )

    coordinate_score = (
        COORDINATE_SCORES.get(
            precision,
            0,
        )
    )

    score += coordinate_score

    if coordinate_score:
        reasons.append(
            f"coordinate:{coordinate_score}"
        )

    tier = metadata.get(
        "display_tier"
    )

    if tier == "dedicated":
        score += 20
        reasons.append(
            "tier:20"
        )

    elif tier == "named_candidate":
        score += 10
        reasons.append(
            "tier:10"
        )

    elif tier == "option_available":
        score += 5
        reasons.append(
            "tier:5"
        )

    if (
        metadata.get(
            "needs_review"
        )
        is True
    ):
        score -= 25
        reasons.append(
            "review:-25"
        )

    score = max(
        0,
        min(
            score,
            100,
        ),
    )

    if score >= 75:
        level = "high"

    elif score >= 50:
        level = "medium"

    else:
        level = "low"

    return {
        "score":
            score,
        "level":
            level,
        "reasons":
            reasons,
        "coordinate_precision":
            precision,
    }


def get_verification_decision(
    item,
):
    confidence = (
        calculate_confidence(
            item
        )
    )

    metadata = (
        item.get("metadata")
        or {}
    )

    if (
        confidence["level"]
        == "high"
        and
        metadata.get(
            "needs_review"
        )
        is not True
    ):
        status = "verified"

    elif (
        confidence["level"]
        == "medium"
    ):
        status = "review"

    else:
        status = "insufficient"

    return {
        "status":
            status,
        "confidence":
            confidence,
    }
