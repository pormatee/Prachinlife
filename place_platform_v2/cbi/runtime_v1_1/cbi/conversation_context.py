from .semantic_interpreter import interpret

def _partial_slots(text, pack):
    slots = {}
    text = text.lower()

    for category, aliases in pack["categories"].items():
        if any(a in text for a in aliases):
            slots["category"] = category
            break

    for mode, aliases in pack["location_modes"].items():
        if any(a in text for a in aliases):
            slots["location_mode"] = mode
            break

    for district, cfg in pack["districts"].items():
        if any(a in text for a in cfg["aliases"]):
            slots["district"] = district
            slots["province"] = cfg["province"]
            break

    return slots

def interpret_with_context(message, previous_state, pack):
    base = interpret(message, pack)
    partial = _partial_slots(message, pack)

    if not previous_state:
        base["context_action"] = "NEW"
        return base

    old = dict(previous_state.get("resolved_slots", {}))
    old_category = old.get("category")
    new_category = partial.get("category")

    if new_category and new_category != old_category:
        base["context_action"] = "TOPIC_CHANGE"
        return base

    merged = dict(old)
    merged.update(partial)

    if partial.get("location_mode") == "near_me":
        merged.pop("province", None)
        merged.pop("district", None)

    base["slots"] = merged

    if merged.get("category"):
        base["intent"] = {
            "name": "search_place",
            "domain": pack["domain_id"]
        }
        base["status"] = "UNDERSTOOD"
        base["confidence"] = {"band": "HIGH"}

    base["context_action"] = "CARRY"
    return base
