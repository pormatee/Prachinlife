def resolve_reference(message, state):
    text = message.strip().lower()
    refs = state.get("recent_references", []) if state else []
    active = state.get("active_reference_id") if state else None

    if not refs:
        return {
            "status": "NEEDS_CLARIFICATION",
            "reference_id": None,
            "ambiguity": "no_reference_context"
        }

    if "ร้านแรก" in text or "อันแรก" in text:
        return {
            "status": "RESOLVED",
            "reference_id": refs[0]["reference_id"]
        }

    if "ร้านที่สอง" in text or "อันที่สอง" in text:
        if len(refs) >= 2:
            return {
                "status": "RESOLVED",
                "reference_id": refs[1]["reference_id"]
            }

    if "ร้านสุดท้าย" in text or "อันสุดท้าย" in text:
        return {
            "status": "RESOLVED",
            "reference_id": refs[-1]["reference_id"]
        }

    vague_terms = (
        "ร้านนั้น",
        "อันนั้น",
        "อันเดิม",
        "ร้านเดิม",
    )

    if any(term in text for term in vague_terms):
        if active:
            return {
                "status": "RESOLVED",
                "reference_id": active
            }

        if len(refs) == 1:
            return {
                "status": "RESOLVED",
                "reference_id": refs[0]["reference_id"]
            }

        return {
            "status": "NEEDS_CLARIFICATION",
            "reference_id": None,
            "ambiguity": "ambiguous_reference"
        }

    return {
        "status": "NO_REFERENCE",
        "reference_id": None
    }
