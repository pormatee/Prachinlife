def build_clarification(semantic):
    missing = semantic.get("missing_information", [])
    ambiguity = semantic.get("ambiguity", [])

    if "category" in missing:
        return "ต้องการค้นหาสถานที่ประเภทไหนครับ"

    if (
        "ambiguous_reference" in ambiguity
        or "unresolved_reference" in ambiguity
        or "no_reference_context" in ambiguity
    ):
        return "หมายถึงรายการไหนครับ"

    if "intent" in missing:
        return "ต้องการให้ช่วยค้นหาอะไรครับ"

    if semantic.get("status") == "NEEDS_CLARIFICATION":
        existing = semantic.get("clarification")

        if existing:
            return existing

        return "ขอรายละเอียดเพิ่มอีกนิดครับ"

    return None
