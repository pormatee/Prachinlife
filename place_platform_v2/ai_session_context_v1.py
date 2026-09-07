from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Tuple

SESSION_CONTEXT_SCHEMA_VERSION = "AI-SESSION-CONTEXT-V1"
MAX_HIGH_VALUE_QUESTIONS = 1


def _dedupe(values: Tuple[str, ...]) -> Tuple[str, ...]:
    seen = set()
    out = []
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return tuple(out)


@dataclass(frozen=True)
class AiSessionContextV1:
    """Explicit, structured, ephemeral AI conversation context.

    This object stores only decision-relevant conversational state.
    It is not a ranking model, not a publication authority, and not a fact store.
    """

    schema_version: str = SESSION_CONTEXT_SCHEMA_VERSION
    turn_index: int = 0

    # Current user intent/context.
    goal: Optional[str] = None
    category: Optional[str] = None
    province: Optional[str] = None
    location_text: Optional[str] = None

    # User-provided decision context.
    hard_constraints: Tuple[str, ...] = ()
    preferences: Tuple[str, ...] = ()

    # Candidate identity context only. Order is preserved exactly as supplied.
    candidate_ids: Tuple[str, ...] = ()
    comparison_candidate_ids: Tuple[str, ...] = ()

    # Conversation bookkeeping. We store the latest message, not concatenated history.
    last_user_message: Optional[str] = None
    pending_high_value_question: Optional[str] = None


@dataclass(frozen=True)
class AiTurnUpdateV1:
    """One turn of structured updates produced by the understanding layer."""

    user_message: str

    goal: Optional[str] = None
    category: Optional[str] = None
    province: Optional[str] = None
    location_text: Optional[str] = None

    add_hard_constraints: Tuple[str, ...] = ()
    remove_hard_constraints: Tuple[str, ...] = ()
    add_preferences: Tuple[str, ...] = ()
    remove_preferences: Tuple[str, ...] = ()

    candidate_ids: Optional[Tuple[str, ...]] = None
    comparison_candidate_ids: Optional[Tuple[str, ...]] = None

    high_value_questions: Tuple[str, ...] = ()


def _remove(values: Tuple[str, ...], removals: Tuple[str, ...]) -> Tuple[str, ...]:
    remove_set = {str(x).strip() for x in removals if str(x).strip()}
    return tuple(x for x in values if x not in remove_set)


def apply_turn_update(
    context: AiSessionContextV1,
    update: AiTurnUpdateV1,
) -> AiSessionContextV1:
    """Merge a structured turn into session context without free-text concatenation."""

    hard_constraints = _remove(
        _dedupe(context.hard_constraints + update.add_hard_constraints),
        update.remove_hard_constraints,
    )
    preferences = _remove(
        _dedupe(context.preferences + update.add_preferences),
        update.remove_preferences,
    )

    candidate_ids = (
        context.candidate_ids
        if update.candidate_ids is None
        else _dedupe(update.candidate_ids)
    )
    comparison_candidate_ids = (
        context.comparison_candidate_ids
        if update.comparison_candidate_ids is None
        else _dedupe(update.comparison_candidate_ids)
    )

    questions = _dedupe(update.high_value_questions)
    pending_question = questions[0] if questions else None

    return replace(
        context,
        turn_index=context.turn_index + 1,
        goal=context.goal if update.goal is None else update.goal,
        category=context.category if update.category is None else update.category,
        province=context.province if update.province is None else update.province,
        location_text=context.location_text if update.location_text is None else update.location_text,
        hard_constraints=hard_constraints,
        preferences=preferences,
        candidate_ids=candidate_ids,
        comparison_candidate_ids=comparison_candidate_ids,
        last_user_message=update.user_message.strip() or None,
        pending_high_value_question=pending_question,
    )


def decision_context_payload(context: AiSessionContextV1) -> dict:
    """Return only decision-safe context.

    Deliberately contains no sponsor/provider/ranking fields and fabricates no facts.
    """
    return {
        "schema_version": context.schema_version,
        "turn_index": context.turn_index,
        "goal": context.goal,
        "category": context.category,
        "province": context.province,
        "location_text": context.location_text,
        "hard_constraints": list(context.hard_constraints),
        "preferences": list(context.preferences),
        "candidate_ids": list(context.candidate_ids),
        "comparison_candidate_ids": list(context.comparison_candidate_ids),
        "pending_high_value_question": context.pending_high_value_question,
    }
