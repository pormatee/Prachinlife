from .request_validator import validate_request
from .semantic_interpreter import interpret
from .conversation_context import interpret_with_context
from .reference_resolver import resolve_reference
from .confidence_gate import apply_confidence_gate
from .clarification_builder import build_clarification
from .result_builder import build_result
from .version_guard import check_compatibility
from .provider_port import ProviderPort


REFERENCE_TERMS = (
    "ร้านแรก",
    "ร้านที่สอง",
    "ร้านสุดท้าย",
    "ร้านนั้น",
    "ร้านเดิม",
    "อันแรก",
    "อันที่สอง",
    "อันสุดท้าย",
    "อันนั้น",
    "อันเดิม",
)


class CBICore:
    def __init__(
        self,
        runtime_version="1.0.0",
        semantic_contract_version="1.0",
        state_schema_version=1,
        provider_port=None,
    ):
        self.runtime_version = runtime_version
        self.semantic_contract_version = semantic_contract_version
        self.state_schema_version = state_schema_version
        self.provider_port = (
            provider_port
            if provider_port is not None
            else ProviderPort("NONE")
        )

    def _invalid(self, status):
        semantic = {
            "status": status,
            "intent": None,
            "slots": {},
            "confidence": {"band": "LOW"},
            "missing_information": [],
            "ambiguity": [],
        }

        return {
            "semantic_result": build_result(semantic),
            "next_state": None,
        }

    def _check_state_scope(self, request, state):
        if state is None:
            return True

        return (
            state.get("project_id") == request["project_id"]
            and state.get("user_id") == request["user_id"]
            and state.get("session_id") == request["session_id"]
        )

    def _reference_requested(self, message):
        text = message.lower()
        return any(
            term in text
            for term in REFERENCE_TERMS
        )

    def process(
        self,
        request,
        domain_pack,
        previous_state=None,
    ):
        valid, status = validate_request(request)

        if not valid:
            return self._invalid(status)

        compatible, version_status = check_compatibility(
            self.runtime_version,
            self.semantic_contract_version,
            self.state_schema_version,
            domain_pack.get("version", "0.0.0"),
        )

        if not compatible:
            return self._invalid(version_status)

        if not self._check_state_scope(
            request,
            previous_state
        ):
            return self._invalid(
                "INVALID_STATE_SCOPE"
            )

        if previous_state is None:
            if request["state_version"] != 0:
                return self._invalid("STALE_STATE")

            if request["turn"] != 1:
                return self._invalid("INVALID_TURN")

        else:
            if request["state_version"] != previous_state.get(
                "state_version"
            ):
                return self._invalid("STALE_STATE")

            if request["turn"] != (
                previous_state.get("turn", 0) + 1
            ):
                return self._invalid("INVALID_TURN")

        if previous_state:
            semantic = interpret_with_context(
                request["message"],
                previous_state,
                domain_pack,
            )
        else:
            semantic = interpret(
                request["message"],
                domain_pack,
            )

        reference_result = None
        references = []

        if self._reference_requested(
            request["message"]
        ):
            reference_result = resolve_reference(
                request["message"],
                previous_state or {},
            )

            if reference_result.get(
                "status"
            ) == "RESOLVED":

                reference_id = reference_result.get(
                    "reference_id"
                )

                reference_type = None

                for ref in (
                    previous_state or {}
                ).get(
                    "recent_references",
                    []
                ):
                    if (
                        ref.get("reference_id")
                        == reference_id
                    ):
                        reference_type = ref.get(
                            "reference_type"
                        )
                        break

                references.append({
                    "reference_type": reference_type,
                    "reference_id": reference_id,
                })

        semantic = apply_confidence_gate(
            semantic,
            reference_result,
        )

        clarification = build_clarification(
            semantic
        )

        intent_name = None

        if isinstance(
            semantic.get("intent"),
            dict
        ):
            intent_name = semantic[
                "intent"
            ].get("name")

        topic = domain_pack.get(
            "intent_topics",
            {}
        ).get(intent_name)

        next_state = {
            "project_id": request["project_id"],
            "user_id": request["user_id"],
            "session_id": request["session_id"],

            "turn": request["turn"],
            "state_version": (
                request["state_version"] + 1
            ),

            "active_topic": topic,
            "active_intent": intent_name,

            "resolved_slots": semantic.get(
                "slots",
                {}
            ),

            "recent_references": (
                previous_state or {}
            ).get(
                "recent_references",
                []
            ),

            "pending_clarification": clarification,

            "runtime_version": self.runtime_version,
            "domain_pack_version": domain_pack.get(
                "version"
            ),
            "state_schema_version": self.state_schema_version,
        }

        if references:
            next_state[
                "active_reference_id"
            ] = references[0][
                "reference_id"
            ]
        else:
            next_state[
                "active_reference_id"
            ] = (
                previous_state or {}
            ).get(
                "active_reference_id"
            )

        transition = {
            "next_turn": (
                request["turn"] + 1
            ),
            "next_state_version": (
                request["state_version"] + 1
            ),
        }

        result = build_result(
            semantic,
            clarification=clarification,
            references=references,
            topic=topic,
            state_transition=transition,
        )

        return {
            "semantic_result": result,
            "next_state": next_state,
        }
