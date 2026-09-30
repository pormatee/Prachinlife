from .request_validator import validate_request

class StateManager:
    def __init__(self):
        self.states = {}
        self.requests = {}

    def _state_key(self, r):
        return (r["project_id"], r["user_id"], r["session_id"])

    def process(self, r):
        valid, status = validate_request(r)
        if not valid:
            return {"status": status}

        state_key = self._state_key(r)
        request_key = (r["project_id"], r["request_id"])

        if request_key in self.requests:
            old = self.requests[request_key]

            if old["state_key"] != state_key:
                return {"status": "REQUEST_ID_CONFLICT"}

            return {
                "status": "DUPLICATE_REQUEST",
                "state_version": old["state_version"],
                "turn": old["turn"],
            }

        current = self.states.get(state_key)

        if current is None:
            if r["state_version"] != 0 or r["turn"] != 1:
                return {"status": "STALE_STATE"}
        else:
            if r["state_version"] != current["state_version"]:
                return {"status": "STALE_STATE"}

            if r["turn"] != current["turn"] + 1:
                return {"status": "INVALID_TURN"}

        new_state = {
            "turn": r["turn"],
            "state_version": r["state_version"] + 1,
        }

        self.states[state_key] = new_state

        self.requests[request_key] = {
            "state_key": state_key,
            **new_state,
        }

        return {
            "status": "ACCEPTED",
            **new_state,
        }

    def get_state(self, project_id, user_id, session_id):
        return self.states.get((project_id, user_id, session_id))
