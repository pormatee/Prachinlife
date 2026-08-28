"""Real Decision Integration V1.

Pure orchestration boundary:
PublishedPlaceView -> DecisionCandidate -> Consumer tri-state gate -> DQE -> outcome.

No database writes, no network/provider calls, and no direct canonical/evidence access.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .consumer_decision_contract_v1 import (
    CandidateDecisionView, ConsumerDecisionRequest, MaterialEvidence,
    ConstraintResolution, resolve_hard_constraints, material_uncertainty,
    decision_effort_questions,
)
from .master_super_brain_v1 import DecisionConstraint, DecisionPreference, DecisionRequest
from .decision_quality_engine_v1 import evaluate_decision_quality
from .publication import PublishedPlaceView
from .real_candidate_mapping_v1 import published_place_to_decision_candidate
from .contracts import GeoPoint

@dataclass(frozen=True)
class RealDecisionIntegrationResult:
    request_id: str
    status: str
    best_fit_candidate_id: str | None
    alternative_candidate_ids: tuple[str, ...]
    rejected_candidate_ids: tuple[str, ...]
    unresolved_candidate_ids: tuple[str, ...]
    uncertainty_fields: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    regret_risks: tuple[str, ...]
    needs_user_input: bool
    highest_value_question: str | None
    human_final_decision: bool
    dqe_result: object

def _consumer_view(c):
    evidence=[]
    for e in c.evidence:
        state={"supported":"supported_inference"}.get(e.status,e.status)
        if state not in {"verified","supported_inference","user_preference","policy","missing","stale","conflicting","unknown"}:
            state="unknown"
        evidence.append(MaterialEvidence(e.field,state,e.value,e.observed_at,e.source_ref,e.confidence))
    return CandidateDecisionView(c.candidate_id,c.attributes,tuple(evidence),c.is_sponsored,(() if not c.promotion_ref else (c.promotion_ref,)))

def _to_dqe_request(req: ConsumerDecisionRequest) -> DecisionRequest:
    constraints=tuple(DecisionConstraint(c.key,c.operator,c.value,"hard",c.weight) for c in req.hard_constraints)
    prefs=[]
    for p in req.preferences:
        direction = "prefer_match"
        if p.operator in {"lte"}: direction="prefer_low"
        elif p.operator in {"gte"}: direction="prefer_high"
        prefs.append(DecisionPreference(p.key,direction,p.weight,p.value))
    return DecisionRequest(req.request_id,req.goal,category=req.category,constraints=constraints,preferences=tuple(prefs))

def evaluate_published_decision(
    request: ConsumerDecisionRequest,
    places: Iterable[PublishedPlaceView],
    *,
    origin: GeoPoint | None = None,
    limit: int = 3,
    highest_value_question: str | None = None,
) -> RealDecisionIntegrationResult:
    candidates=tuple(published_place_to_decision_candidate(p,origin=origin) for p in places)
    satisfied=[]; rejected=[]; unresolved=[]; uncertainty=set()
    material_fields=tuple(c.key for c in request.hard_constraints)+tuple(p.key for p in request.preferences)

    for c in candidates:
        view=_consumer_view(c)
        resolutions=resolve_hard_constraints(request,view)
        if any(x.resolution is ConstraintResolution.VIOLATED for x in resolutions):
            rejected.append(c.candidate_id); continue
        if any(x.resolution is ConstraintResolution.UNRESOLVED for x in resolutions):
            unresolved.append(c.candidate_id)
            uncertainty.update(x.key for x in resolutions if x.resolution is ConstraintResolution.UNRESOLVED)
            continue
        uncertainty.update(material_uncertainty(view,material_fields))
        satisfied.append(c)

    dqe=evaluate_decision_quality(_to_dqe_request(request),satisfied,domain=request.category,limit=limit)
    recommended=tuple(dqe.recommended)
    best=recommended[0].candidate_id if recommended else None
    alts=tuple(x.candidate_id for x in recommended[1:])
    uncertainty.update(dqe.missing_information)

    # Minimum Decision Effort: only ask when one answer can materially improve
    # personal relevance. Never ask merely to hide missing system evidence.
    can_change=bool(highest_value_question) and (len(recommended)>1 or best is None)
    qcount=decision_effort_questions(
        decision_can_materially_change=can_change,
        enough_for_useful_answer=best is not None,
    )
    question=highest_value_question if qcount else None

    status=dqe.status
    if not satisfied and unresolved:
        status="insufficient_data"
    elif best and dqe.status=="insufficient_data":
        status="qualified_with_uncertainty"
    if best and question:
        status="useful_answer_with_one_question"

    tradeoffs=tuple(dict.fromkeys(t for x in recommended for t in x.tradeoffs))
    regrets=tuple(f"{x.candidate_id}:regret={x.regret_risk:.3f}" for x in recommended)
    return RealDecisionIntegrationResult(
        request_id=request.request_id,status=status,best_fit_candidate_id=best,
        alternative_candidate_ids=alts,rejected_candidate_ids=tuple(rejected),
        unresolved_candidate_ids=tuple(unresolved),uncertainty_fields=tuple(sorted(uncertainty)),
        tradeoffs=tradeoffs,regret_risks=regrets,needs_user_input=bool(question),
        highest_value_question=question,human_final_decision=bool(dqe.decision_boundary.human_decides),
        dqe_result=dqe,
    )
