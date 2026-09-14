from __future__ import annotations

from typing import Any, Callable

DecisionRunnerV1 = Callable[[dict[str, Any]], dict[str, Any]]
DecisionActionAttacherV1 = Callable[[dict[str, Any]], dict[str, Any]]


def decision_payload(
    payload: dict[str, Any],
    *,
    run_decision: DecisionRunnerV1,
) -> dict[str, Any]:
    """Validate the API decision request shape and invoke decision runtime."""

    if not isinstance(payload, dict):
        raise ValueError("request_body_must_be_object")
    return run_decision(payload)


def decision_response_payload(
    payload: dict[str, Any],
    *,
    decide: DecisionRunnerV1,
    attach_actions: DecisionActionAttacherV1,
) -> dict[str, Any]:
    """Decorate a decision result with the existing decision-action contract."""

    return attach_actions(decide(payload))
