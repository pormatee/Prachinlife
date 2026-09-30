ALLOWED_FIELDS = (
    "status",
    "intent",
    "slots",
    "references",
    "topic",
    "confidence",
    "missing_information",
    "ambiguity",
    "clarification",
    "state_transition",
    "diagnostics"
)


def build_result(
    semantic,
    clarification=None,
    references=None,
    topic=None,
    state_transition=None,
):
    result = {
        "status": semantic.get(
            "status",
            "NEEDS_CLARIFICATION"
        ),

        "intent": semantic.get("intent"),

        "slots": semantic.get(
            "slots",
            {}
        ),

        "references": references or [],

        "topic": (
            topic
            if topic is not None
            else semantic.get("topic")
        ),

        "confidence": semantic.get(
            "confidence",
            {"band": "LOW"}
        ),

        "missing_information": semantic.get(
            "missing_information",
            []
        ),

        "ambiguity": semantic.get(
            "ambiguity",
            []
        ),

        "clarification": clarification,

        "state_transition": state_transition,

        "diagnostics": semantic.get(
            "diagnostics",
            {}
        ),
    }

    # Safety: output เฉพาะ Semantic Contract
    return {
        key: result[key]
        for key in ALLOWED_FIELDS
    }
