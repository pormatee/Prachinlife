from __future__ import annotations

from .clarification_builder import build_clarification
from .confidence_gate import apply_confidence_gate
from .core import CBICore
from .result_builder import build_result


CBI_V11_RUNTIME_VERSION = "1.1.0"

_FORBIDDEN_FIELDS = {
    "candidate_id",
    "candidate_ids",
    "place_id",
    "winner",
    "recommendation",
    "recommended",
    "ranking",
    "rank",
    "ranking_score",
    "score",
    "business_decision",
    "publication_state",
    "canonical_write",
    "projection_write",
    "sponsor",
    "sponsored",
}


def _contains_forbidden(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN_FIELDS:
                return True

            if _contains_forbidden(child):
                return True

    elif isinstance(value, (list, tuple)):
        return any(
            _contains_forbidden(item)
            for item in value
        )

    return False


def _short_list(value, limit=8):
    if not isinstance(value, list):
        return []

    out = []

    for item in value[:limit]:
        if isinstance(item, str):
            item = item.strip()

            if item:
                out.append(item[:120])

    return out


class CBICoreV11(CBICore):
    def __init__(
        self,
        runtime_version=CBI_V11_RUNTIME_VERSION,
        semantic_contract_version="1.0",
        state_schema_version=1,
        provider_port=None,
    ):
        super().__init__(
            runtime_version=runtime_version,
            semantic_contract_version=(
                semantic_contract_version
            ),
            state_schema_version=(
                state_schema_version
            ),
            provider_port=provider_port,
        )

    @staticmethod
    def _should_escalate(
        base_output,
        previous_state,
    ):
        result = base_output.get(
            "semantic_result",
            {},
        )

        status = result.get("status")

        if status == "ESCALATION_CANDIDATE":
            return True

        return (
            status == "NEEDS_CLARIFICATION"
            and previous_state is not None
            and bool(
                previous_state.get(
                    "pending_clarification"
                )
            )
        )

    @staticmethod
    def _provider_payload(
        request,
        domain_pack,
        previous_state,
        base_output,
    ):
        return {
            "task":
                "resolve_semantic_after_clarification",

            "current_user_text":
                request["message"],

            "conversation_context": {
                "active_intent":
                    (
                        previous_state or {}
                    ).get("active_intent"),

                "active_topic":
                    (
                        previous_state or {}
                    ).get("active_topic"),

                "resolved_slots":
                    (
                        previous_state or {}
                    ).get(
                        "resolved_slots",
                        {},
                    ),

                "pending_clarification":
                    (
                        previous_state or {}
                    ).get(
                        "pending_clarification"
                    ),
            },

            "local_result":
                base_output.get(
                    "semantic_result",
                    {},
                ),

            "allowed_semantics": {
                "domain_id":
                    domain_pack.get(
                        "domain_id"
                    ),

                "intents":
                    sorted(
                        domain_pack.get(
                            "intent_topics",
                            {},
                        ).keys()
                    ),

                "categories":
                    sorted(
                        domain_pack.get(
                            "categories",
                            {},
                        ).keys()
                    ),

                "provinces":
                    sorted(
                        domain_pack.get(
                            "provinces",
                            {},
                        ).keys()
                    ),

                "districts":
                    sorted(
                        domain_pack.get(
                            "districts",
                            {},
                        ).keys()
                    ),

                "location_modes":
                    sorted(
                        domain_pack.get(
                            "location_modes",
                            {},
                        ).keys()
                    ),
            },
        }

    @staticmethod
    def _confidence_band(value):
        if not isinstance(
            value,
            (int, float),
        ) or isinstance(value, bool):
            return "LOW"

        value = max(
            0.0,
            min(1.0, float(value)),
        )

        if value >= 0.80:
            return "HIGH"

        if value >= 0.55:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _normalize_slots(
        raw_slots,
        domain_pack,
    ):
        if not isinstance(raw_slots, dict):
            return {}

        slots = {}

        category = raw_slots.get("category")

        if category in domain_pack.get(
            "categories",
            {},
        ):
            slots["category"] = category

        province = raw_slots.get("province")

        if province in domain_pack.get(
            "provinces",
            {},
        ):
            slots["province"] = province

        district = raw_slots.get("district")

        if district in domain_pack.get(
            "districts",
            {},
        ):
            slots["district"] = district

            cfg = domain_pack[
                "districts"
            ][district]

            if isinstance(cfg, dict):
                linked_province = cfg.get(
                    "province"
                )

                if linked_province:
                    slots["province"] = (
                        linked_province
                    )

        location_mode = raw_slots.get(
            "location_mode"
        )

        if location_mode in domain_pack.get(
            "location_modes",
            {},
        ):
            slots["location_mode"] = (
                location_mode
            )

            if location_mode == "near_me":
                slots.pop("province", None)
                slots.pop("district", None)

        return slots

    def _normalize_proposal(
        self,
        proposal,
        domain_pack,
    ):
        if not isinstance(proposal, dict):
            return None

        if _contains_forbidden(proposal):
            return None

        status = proposal.get("status")

        if status not in {
            "UNDERSTOOD",
            "NEEDS_CLARIFICATION",
        }:
            return None

        intent_name = proposal.get("intent")

        allowed_intents = set(
            domain_pack.get(
                "intent_topics",
                {},
            ).keys()
        )

        if (
            intent_name is not None
            and intent_name not in allowed_intents
        ):
            return None

        slots = self._normalize_slots(
            proposal.get("slots"),
            domain_pack,
        )

        missing = _short_list(
            proposal.get(
                "missing_information"
            )
        )

        ambiguity = _short_list(
            proposal.get("ambiguity")
        )

        if intent_name is None:
            if "intent" not in missing:
                missing.append("intent")

        if intent_name:
            required = domain_pack.get(
                "required_slots",
                {},
            ).get(
                intent_name,
                [],
            )

            for key in required:
                if (
                    key not in slots
                    and key not in missing
                ):
                    missing.append(key)

        semantic = {
            "status": status,

            "intent": (
                {
                    "name": intent_name,
                    "domain":
                        domain_pack.get(
                            "domain_id"
                        ),
                }
                if intent_name
                else None
            ),

            "slots": slots,

            "confidence": {
                "band":
                    self._confidence_band(
                        proposal.get(
                            "confidence"
                        )
                    )
            },

            "missing_information":
                missing,

            "ambiguity":
                ambiguity,

            "diagnostics": {
                "provider_escalation": {
                    "attempted": True,
                    "used": True,
                    "provider_mode":
                        "AI_HUB",
                    "trusted": False,
                }
            },
        }

        return apply_confidence_gate(
            semantic
        )

    @staticmethod
    def _with_provider_diagnostic(
        base_output,
        status,
    ):
        out = dict(base_output)

        result = dict(
            out.get(
                "semantic_result",
                {},
            )
        )

        diagnostics = dict(
            result.get(
                "diagnostics",
                {},
            )
        )

        diagnostics[
            "provider_escalation"
        ] = {
            "attempted": True,
            "used": False,
            "provider_mode": "AI_HUB",
            "trusted": False,
            "status": status,
        }

        result["diagnostics"] = diagnostics
        out["semantic_result"] = result

        return out

    def process(
        self,
        request,
        domain_pack,
        previous_state=None,
    ):
        base_output = super().process(
            request,
            domain_pack,
            previous_state,
        )

        if not self._should_escalate(
            base_output,
            previous_state,
        ):
            return base_output

        if not self.provider_port.available:
            return self._with_provider_diagnostic(
                base_output,
                "PROVIDER_UNAVAILABLE",
            )

        provider_result = (
            self.provider_port.escalate(
                self._provider_payload(
                    request,
                    domain_pack,
                    previous_state,
                    base_output,
                )
            )
        )

        if (
            not isinstance(
                provider_result,
                dict,
            )
            or provider_result.get(
                "status"
            ) != "PROPOSAL"
            or provider_result.get(
                "trusted"
            ) is not False
        ):
            status = (
                provider_result.get(
                    "status",
                    "INVALID_PROPOSAL",
                )
                if isinstance(
                    provider_result,
                    dict,
                )
                else "INVALID_PROPOSAL"
            )

            return self._with_provider_diagnostic(
                base_output,
                status,
            )

        semantic = self._normalize_proposal(
            provider_result.get(
                "proposal"
            ),
            domain_pack,
        )

        if semantic is None:
            return self._with_provider_diagnostic(
                base_output,
                "INVALID_PROPOSAL",
            )

        clarification = build_clarification(
            semantic
        )

        intent_name = None

        if isinstance(
            semantic.get("intent"),
            dict,
        ):
            intent_name = semantic[
                "intent"
            ].get("name")

        topic = domain_pack.get(
            "intent_topics",
            {},
        ).get(intent_name)

        base_result = base_output.get(
            "semantic_result",
            {},
        )

        result = build_result(
            semantic,
            clarification=clarification,
            references=base_result.get(
                "references",
                [],
            ),
            topic=topic,
            state_transition=base_result.get(
                "state_transition"
            ),
        )

        next_state = dict(
            base_output.get(
                "next_state"
            ) or {}
        )

        if next_state:
            next_state[
                "active_intent"
            ] = intent_name

            next_state[
                "active_topic"
            ] = topic

            next_state[
                "resolved_slots"
            ] = semantic.get(
                "slots",
                {},
            )

            next_state[
                "pending_clarification"
            ] = clarification

            next_state[
                "runtime_version"
            ] = self.runtime_version

        return {
            "semantic_result": result,
            "next_state": next_state,
        }
