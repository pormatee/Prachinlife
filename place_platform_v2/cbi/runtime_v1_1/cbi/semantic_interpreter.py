def match_any(text, values):
    return any(v in text for v in values)


def interpret(message, pack):
    text = message.strip().lower()
    slots = {}
    concept_intent = None

    # Semantic Concept Layer
    for _, concept in pack.get("semantic_concepts", {}).items():
        if match_any(text, concept.get("aliases", [])):
            concept_intent = concept.get("intent")
            slots.update(concept.get("slots", {}))
            break

    # Category Layer
    if "category" not in slots:
        for name, aliases in pack["categories"].items():
            if match_any(text, aliases):
                slots["category"] = name
                break

    # Location Mode
    for mode, aliases in pack["location_modes"].items():
        if match_any(text, aliases):
            slots["location_mode"] = mode

    # District
    for district, cfg in pack["districts"].items():
        if match_any(text, cfg["aliases"]):
            slots["district"] = district
            slots["province"] = cfg["province"]

    # Province
    if "province" not in slots:
        for province, aliases in pack["provinces"].items():
            if match_any(text, aliases):
                slots["province"] = province

    # Intent
    if concept_intent:
        intent = concept_intent
    elif match_any(text, pack["promotion_concepts"]):
        intent = "search_promotion"
    elif match_any(text, pack["search_concepts"]) or "category" in slots:
        intent = "search_place"
    else:
        return {
            "status": "NEEDS_CLARIFICATION",
            "intent": None,
            "slots": {},
            "confidence": {"band": "LOW"}
        }

    if intent == "search_place" and "category" not in slots:
        return {
            "status": "NEEDS_CLARIFICATION",
            "intent": {"name": intent, "domain": pack["domain_id"]},
            "slots": slots,
            "confidence": {"band": "MEDIUM"}
        }

    return {
        "status": "UNDERSTOOD",
        "intent": {"name": intent, "domain": pack["domain_id"]},
        "slots": slots,
        "confidence": {"band": "HIGH"}
    }
