REQUIRED = {
    "project_id": str,
    "user_id": str,
    "session_id": str,
    "request_id": str,
    "turn": int,
    "state_version": int,
    "message": str,
}

def validate_request(req):
    if not isinstance(req, dict):
        return False, "INVALID_REQUEST"

    for field, typ in REQUIRED.items():
        if field not in req or not isinstance(req[field], typ):
            return False, "INVALID_REQUEST"

    for field in ("project_id", "user_id", "session_id", "request_id", "message"):
        if not req[field].strip():
            return False, "INVALID_REQUEST"

    if req["turn"] < 1 or req["state_version"] < 0:
        return False, "INVALID_REQUEST"

    return True, "OK"
