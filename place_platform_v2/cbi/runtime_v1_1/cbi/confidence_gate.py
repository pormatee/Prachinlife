def apply_confidence_gate(semantic, reference_result=None):
    result = dict(semantic)

    status = result.get("status")

    if status in (
        "INVALID_REQUEST",
        "STALE_STATE",
        "INCOMPATIBLE_CONTRACT"
    ):
        return result

    if reference_result:
        if reference_result.get("status") == "NEEDS_CLARIFICATION":
            result["status"] = "NEEDS_CLARIFICATION"
            result["confidence"] = {"band": "LOW"}

            ambiguity = list(result.get("ambiguity", []))

            reason = reference_result.get(
                "ambiguity",
                "ambiguous_reference"
            )

            if reason not in ambiguity:
                ambiguity.append(reason)

            result["ambiguity"] = ambiguity
            return result

    if result.get("ambiguity"):
        result["status"] = "NEEDS_CLARIFICATION"
        return result

    if result.get("missing_information"):
        result["status"] = "NEEDS_CLARIFICATION"
        return result

    if status == "ESCALATION_CANDIDATE":
        return result

    confidence = result.get(
        "confidence",
        {"band": "LOW"}
    ).get("band", "LOW")

    if status == "UNDERSTOOD" and confidence == "HIGH":
        return result

    result["status"] = "NEEDS_CLARIFICATION"
    return result
