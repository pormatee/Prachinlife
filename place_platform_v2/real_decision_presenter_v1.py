"""Real Decision Presenter V1.

Deterministic, provider-independent presentation layer for PrachinLife decision
results. It may summarize and format an already-computed decision, but it has no
authority to fetch candidates, rank them, change policy, reinterpret evidence, or
invent facts.

Supported inputs:
- EndToEndRealDecisionResultV1
- ContextualPersonalDecisionResult

The caller may supply candidate_labels solely for display. Missing labels fall
back to the candidate id; names are never guessed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence, runtime_checkable

PRESENTER_POLICY_VERSION = "RDP-V1"


@dataclass(frozen=True)
class PresentedCandidateV1:
    candidate_id: str
    display_name: str


@dataclass(frozen=True)
class DecisionPresentationV1:
    request_id: str
    source_kind: str
    source_status: str
    presentation_status: str
    headline: str
    summary: str
    recommendation: PresentedCandidateV1 | None
    alternatives: tuple[PresentedCandidateV1, ...]
    uncertainty_items: tuple[str, ...]
    tradeoff_items: tuple[str, ...]
    regret_items: tuple[str, ...]
    highest_value_question: str | None
    human_boundary: str
    human_final_decision: bool
    policy_version: str = PRESENTER_POLICY_VERSION


@runtime_checkable
class _E2ELike(Protocol):
    request_id: str
    status: str
    needs_user_input: bool
    highest_value_question: str | None
    human_final_decision: bool


@runtime_checkable
class _ContextualLike(Protocol):
    request_id: str
    status: str
    best_fit_candidate_id: str | None
    alternative_candidate_ids: tuple[str, ...]
    uncertainty_fields: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    regret_risks: tuple[str, ...]
    needs_user_input: bool
    highest_value_question: str | None
    human_final_decision: bool


def _dedupe(items: Sequence[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        value = str(raw).strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


def _candidate(candidate_id: str | None, labels: Mapping[str, str]) -> PresentedCandidateV1 | None:
    if not candidate_id:
        return None
    display = str(labels.get(candidate_id) or candidate_id).strip() or candidate_id
    return PresentedCandidateV1(candidate_id=candidate_id, display_name=display)


def _alternatives(ids: Sequence[str], labels: Mapping[str, str]) -> tuple[PresentedCandidateV1, ...]:
    out: list[PresentedCandidateV1] = []
    seen: set[str] = set()
    for cid in ids:
        cid = str(cid).strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        item = _candidate(cid, labels)
        if item is not None:
            out.append(item)
    return tuple(out)


def _headline_and_summary(
    *,
    source_status: str,
    recommendation: PresentedCandidateV1 | None,
    needs_user_input: bool,
    question: str | None,
    uncertainty: Sequence[str],
) -> tuple[str, str, str]:
    if recommendation is not None:
        if uncertainty:
            return (
                "มีตัวเลือกที่เหมาะ แต่ยังมีข้อมูลที่ควรระวัง",
                f"จากผลการตัดสินใจที่ผ่านเงื่อนไขแล้ว {recommendation.display_name} เหมาะที่สุดในข้อมูลที่มีตอนนี้ โดยยังมีความไม่แน่นอนที่ควรดูประกอบ",
                "recommendation_with_uncertainty",
            )
        return (
            "มีตัวเลือกที่เหมาะที่สุดในข้อมูลปัจจุบัน",
            f"จากผลการตัดสินใจที่ผ่านเงื่อนไขแล้ว {recommendation.display_name} เหมาะที่สุดในข้อมูลที่มีตอนนี้",
            "recommendation",
        )

    if needs_user_input and question:
        return (
            "ต้องการข้อมูลจากคุณอีกเล็กน้อย",
            "ระบบยังไม่ควรเลือกแทน เพราะข้อมูลจากผู้ใช้ที่จำเป็นต่อการตัดสินใจยังไม่ครบ",
            "needs_user_input",
        )

    if source_status in {"insufficient_data", "qualified_with_uncertainty"}:
        return (
            "ข้อมูลยังไม่พอสำหรับคำแนะนำที่มั่นใจ",
            "ระบบยังไม่ควรยกตัวเลือกใดเป็นตัวเลือกที่เหมาะที่สุดจากหลักฐานที่มี",
            "insufficient_data",
        )

    if source_status in {"no_valid_candidate", "no_compatible_published_candidate"}:
        return (
            "ยังไม่มีตัวเลือกที่ผ่านเงื่อนไข",
            "จากตัวเลือกที่ระบบประเมิน ยังไม่มีตัวเลือกที่ควรถูกยกเป็นคำแนะนำในตอนนี้",
            "no_valid_candidate",
        )

    return (
        "ยังสรุปคำแนะนำไม่ได้",
        "ผลการตัดสินใจปัจจุบันยังไม่มีตัวเลือกที่ควรถูกนำเสนอเป็นคำแนะนำ",
        "no_recommendation",
    )


def present_end_to_end_decision_v1(
    result: _E2ELike,
    *,
    candidate_labels: Mapping[str, str] | None = None,
) -> DecisionPresentationV1:
    """Present an EndToEndRealDecisionResultV1 without changing its decision."""
    labels = dict(candidate_labels or {})
    explanation = getattr(result, "explanation", None)

    best_id = getattr(explanation, "best_fit_candidate_id", None)
    best_name = getattr(explanation, "best_fit_name", None)
    if best_id and best_name and best_id not in labels:
        labels[best_id] = str(best_name)

    alt_ids = tuple(getattr(explanation, "alternatives", ()) or ())
    uncertainty = _dedupe(tuple(getattr(explanation, "uncertainty_fields", ()) or ()))
    tradeoffs = _dedupe(tuple(getattr(explanation, "tradeoffs", ()) or ()))
    regrets = _dedupe(tuple(getattr(explanation, "regret_risks", ()) or ()))

    recommendation = _candidate(best_id, labels)
    alternatives = tuple(
        item for item in _alternatives(alt_ids, labels)
        if recommendation is None or item.candidate_id != recommendation.candidate_id
    )
    question = getattr(result, "highest_value_question", None)
    headline, summary, presentation_status = _headline_and_summary(
        source_status=str(result.status),
        recommendation=recommendation,
        needs_user_input=bool(result.needs_user_input),
        question=question,
        uncertainty=uncertainty,
    )

    return DecisionPresentationV1(
        request_id=str(result.request_id),
        source_kind="end_to_end",
        source_status=str(result.status),
        presentation_status=presentation_status,
        headline=headline,
        summary=summary,
        recommendation=recommendation,
        alternatives=alternatives,
        uncertainty_items=uncertainty,
        tradeoff_items=tradeoffs,
        regret_items=regrets,
        highest_value_question=question if bool(result.needs_user_input) else None,
        human_boundary="คำแนะนำนี้ช่วยประกอบการตัดสินใจ โดยผู้ใช้เป็นผู้ตัดสินใจสุดท้าย",
        human_final_decision=bool(result.human_final_decision),
    )


def present_contextual_personal_decision_v1(
    result: _ContextualLike,
    *,
    candidate_labels: Mapping[str, str] | None = None,
) -> DecisionPresentationV1:
    """Present a ContextualPersonalDecisionResult without re-evaluating it."""
    labels = dict(candidate_labels or {})
    best_id = result.best_fit_candidate_id
    recommendation = _candidate(best_id, labels)
    alternatives = tuple(
        item for item in _alternatives(result.alternative_candidate_ids, labels)
        if recommendation is None or item.candidate_id != recommendation.candidate_id
    )
    uncertainty = _dedupe(result.uncertainty_fields)
    tradeoffs = _dedupe(result.tradeoffs)
    regrets = _dedupe(result.regret_risks)
    question = result.highest_value_question

    headline, summary, presentation_status = _headline_and_summary(
        source_status=str(result.status),
        recommendation=recommendation,
        needs_user_input=bool(result.needs_user_input),
        question=question,
        uncertainty=uncertainty,
    )

    return DecisionPresentationV1(
        request_id=str(result.request_id),
        source_kind="contextual_personal",
        source_status=str(result.status),
        presentation_status=presentation_status,
        headline=headline,
        summary=summary,
        recommendation=recommendation,
        alternatives=alternatives,
        uncertainty_items=uncertainty,
        tradeoff_items=tradeoffs,
        regret_items=regrets,
        highest_value_question=question if bool(result.needs_user_input) else None,
        human_boundary="คำแนะนำนี้ช่วยประกอบการตัดสินใจ โดยผู้ใช้เป็นผู้ตัดสินใจสุดท้าย",
        human_final_decision=bool(result.human_final_decision),
    )
