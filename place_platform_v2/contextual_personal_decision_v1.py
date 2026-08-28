"""Contextual Personal Decision Assistant V1.

Read-only L4 adapter. It turns trusted situational context into transparent
hard/soft decision criteria and overlays provenance-carrying decision-time facts
onto already-published places before the existing tri-state gate + DQE.

It does not mutate PublishedPlaceView, canonical storage, evidence tables, or
publication state, and it never fabricates missing dynamic facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .consumer_decision_contract_v1 import (
    CandidateDecisionView,
    ConsumerCondition,
    ConsumerDecisionRequest,
    ConstraintResolution,
    MaterialEvidence,
    decision_effort_questions,
    material_uncertainty,
    resolve_hard_constraints,
)
from .contracts import GeoPoint
from .decision_quality_engine_v1 import evaluate_decision_quality
from .end_to_end_real_decision_flow_v1 import (
    _candidate_compatible,
    _fetch_published_places,
    _origin_from_context,
    _question_for,
)
from .intent_context_understanding_v1 import StructuredDecisionRequest, understand_user_request
from .master_super_brain_v1 import DecisionCandidate, DecisionConstraint, DecisionPreference, DecisionRequest, EvidenceItem
from .publication import PublishedPlaceView
from .read_model import PublishedPlaceRepository
from .real_candidate_mapping_v1 import published_place_to_decision_candidate

CONTEXTUAL_POLICY_VERSION = "CPDA-V1"
_ALLOWED_FACT_STATES = {"verified", "supported_inference", "missing", "stale", "conflicting", "unknown"}
_BAD_STATES = {"missing", "stale", "conflicting", "unknown"}
_NOVELTY_TERMS = ("อยากลองร้านใหม่", "ลองร้านใหม่", "ร้านใหม่", "ที่ใหม่", "ไม่เคยไป", "new place")


@dataclass(frozen=True)
class DecisionTimeFact:
    place_id: str
    field: str
    value: Any
    state: str
    source_ref: str
    observed_at: str | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.place_id or not self.field:
            raise ValueError("place_id and field are required")
        if self.state not in _ALLOWED_FACT_STATES:
            raise ValueError("unsupported decision-time fact state")
        if not self.source_ref:
            raise ValueError("source_ref required")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ContextPolicyProfile:
    hard_constraints: tuple[ConsumerCondition, ...]
    preferences: tuple[ConsumerCondition, ...]
    material_fields: tuple[str, ...]
    applied_rules: tuple[str, ...]
    policy_version: str = CONTEXTUAL_POLICY_VERSION


@dataclass(frozen=True)
class ContextualPersonalDecisionResult:
    request_id: str
    status: str
    understanding: StructuredDecisionRequest
    profile: ContextPolicyProfile
    best_fit_candidate_id: str | None
    alternative_candidate_ids: tuple[str, ...]
    rejected_candidate_ids: tuple[str, ...]
    unresolved_candidate_ids: tuple[str, ...]
    uncertainty_fields: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    regret_risks: tuple[str, ...]
    applied_fact_refs: tuple[str, ...]
    needs_user_input: bool
    highest_value_question: str | None
    human_final_decision: bool = True


def _dedupe_conditions(items: Iterable[ConsumerCondition]) -> tuple[ConsumerCondition, ...]:
    out=[]; seen=set()
    for item in items:
        key=(item.key,item.operator,repr(item.value),item.strength)
        if key not in seen:
            seen.add(key); out.append(item)
    return tuple(out)


def build_context_policy_profile(
    understanding: StructuredDecisionRequest,
    *,
    trusted_context: Mapping[str, Any] | None = None,
) -> ContextPolicyProfile:
    """Turn explicit user/situational context into decision criteria.

    The policy only changes *what matters*. It never asserts candidate facts.
    Candidate facts must arrive separately as DecisionTimeFact evidence.
    """
    context=dict(trusted_context or {})
    hard=list(understanding.hard_constraints)
    prefs=list(understanding.preferences)
    rules=[]

    # "ตอนนี้" / explicit urgent-now means being open is necessary, not merely nice.
    urgency=str(context.get("urgency") or "").casefold()
    if understanding.temporal_context == "now" or urgency in {"now", "immediate", "urgent"}:
        hard.append(ConsumerCondition("open_now", True, strength="hard", operator="eq", source="context_policy"))
        rules.append("urgent_now_requires_open_now")

    # Family context affects suitability; it does not silently become a hard gate.
    family = bool(understanding.inferred_context.get("family_context")) or bool(context.get("family_context"))
    if family or context.get("with_children") is True or context.get("with_elderly") is True:
        prefs.append(ConsumerCondition("family_suitability", True, strength="soft", weight=1.0, operator="eq", source="context_policy"))
        prefs.append(ConsumerCondition("parking", True, strength="soft", weight=0.7, operator="eq", source="context_policy"))
        rules.append("family_prefers_suitability_and_parking")

    # Budget sensitivity remains a preference unless the user supplied a numeric hard cap.
    budget_sensitive = bool(understanding.inferred_context.get("budget_sensitive")) or str(context.get("budget_sensitivity") or "").casefold() in {"high","tight","limited"}
    if budget_sensitive and not any(p.key == "price" for p in prefs):
        prefs.append(ConsumerCondition("price", None, strength="soft", weight=1.0, operator="lte", source="context_policy"))
    if budget_sensitive:
        rules.append("budget_prefers_lower_price")

    budget_max=context.get("budget_max")
    if budget_max is not None:
        hard.append(ConsumerCondition("price_amount", float(budget_max), strength="hard", operator="lte", source="user_context"))
        rules.append("explicit_budget_cap_is_hard")

    normalized=understanding.user_text.casefold()
    if any(term.casefold() in normalized for term in _NOVELTY_TERMS) or context.get("prefer_new") is True:
        prefs.append(ConsumerCondition("novelty", True, strength="soft", weight=0.8, operator="eq", source="context_policy"))
        rules.append("prefer_unvisited_option")

    hard=_dedupe_conditions(hard)
    prefs=_dedupe_conditions(prefs)
    material=tuple(dict.fromkeys([c.key for c in hard] + [p.key for p in prefs]))
    return ContextPolicyProfile(hard, prefs, material, tuple(dict.fromkeys(rules)))


def _overlay_candidate(
    place: PublishedPlaceView,
    facts_by_place: Mapping[str, tuple[DecisionTimeFact, ...]],
    *,
    origin: GeoPoint | None,
    visited_candidate_ids: frozenset[str],
) -> tuple[DecisionCandidate, tuple[str, ...]]:
    base=published_place_to_decision_candidate(place, origin=origin)
    attrs=dict(base.attributes)
    evidence=list(base.evidence)
    refs=[]

    for fact in facts_by_place.get(place.place_id, ()):
        # unresolved states are evidence about uncertainty, not candidate truth.
        if fact.state not in _BAD_STATES:
            attrs[fact.field]=fact.value
        evidence.append(EvidenceItem(fact.field, fact.value, fact.state, fact.confidence, fact.observed_at, fact.source_ref))
        refs.append(fact.source_ref)

    # Novelty is derived only from trusted visit history supplied by the caller.
    if visited_candidate_ids:
        novelty=place.place_id not in visited_candidate_ids
        attrs["novelty"]=novelty
        ref="user-context:visited-history"
        evidence.append(EvidenceItem("novelty", novelty, "user_preference", 1.0, None, ref))
        refs.append(ref)

    return DecisionCandidate(base.candidate_id,base.entity_type,attrs,tuple(evidence),base.is_sponsored,base.promotion_ref), tuple(refs)


def _consumer_view(candidate: DecisionCandidate) -> CandidateDecisionView:
    evidence=[]
    for e in candidate.evidence:
        state={"supported":"supported_inference"}.get(e.status,e.status)
        if state not in {"verified","supported_inference","user_preference","policy","missing","stale","conflicting","unknown"}:
            state="unknown"
        evidence.append(MaterialEvidence(e.field,state,e.value,e.observed_at,e.source_ref,e.confidence))
    return CandidateDecisionView(candidate.candidate_id,candidate.attributes,tuple(evidence),candidate.is_sponsored,(() if not candidate.promotion_ref else (candidate.promotion_ref,)))


def _to_dqe_request(req: ConsumerDecisionRequest) -> DecisionRequest:
    constraints=tuple(DecisionConstraint(c.key,c.operator,c.value,"hard",c.weight) for c in req.hard_constraints)
    prefs=[]
    for p in req.preferences:
        direction="prefer_match"
        if p.operator=="lte": direction="prefer_low"
        elif p.operator=="gte": direction="prefer_high"
        prefs.append(DecisionPreference(p.key,direction,p.weight,p.value))
    return DecisionRequest(req.request_id,req.goal,category=req.category,constraints=constraints,preferences=tuple(prefs))


def run_contextual_personal_decision_v1(
    *,
    request_id: str,
    user_text: str,
    repository: PublishedPlaceRepository,
    context: Mapping[str, Any] | None = None,
    decision_time_facts: Iterable[DecisionTimeFact] = (),
    visited_candidate_ids: Iterable[str] = (),
    radius_km: float = 20.0,
    candidate_limit: int = 50,
    recommendation_limit: int = 3,
) -> ContextualPersonalDecisionResult:
    """Run contextual L4 decisioning over published places + explicit overlay facts."""
    understanding=understand_user_request(user_text, context=context)
    question=_question_for(understanding)
    empty_profile=ContextPolicyProfile((),(),(),())

    if understanding.category is None or understanding.decision_object is None:
        return ContextualPersonalDecisionResult(request_id,"needs_user_input",understanding,empty_profile,None,(),(),(),(),(),(),(),True,question,True)

    origin=_origin_from_context(context)
    if understanding.near_me and origin is None:
        return ContextualPersonalDecisionResult(request_id,"needs_user_input",understanding,empty_profile,None,(),(),(),(),(),(),(),True,question,True)

    profile=build_context_policy_profile(understanding,trusted_context=context)
    request=ConsumerDecisionRequest(
        request_id=request_id,
        goal=understanding.goal,
        category=understanding.category,
        hard_constraints=profile.hard_constraints,
        preferences=profile.preferences,
        context=understanding.to_consumer_request(request_id).context,
    )
    published=_fetch_published_places(repository,understanding,origin=origin,radius_km=radius_km,limit=candidate_limit)
    compatible=tuple(p for p in published if _candidate_compatible(p,understanding))

    by_place={}
    for fact in decision_time_facts:
        by_place.setdefault(fact.place_id,[]).append(fact)
    facts_by_place={k:tuple(v) for k,v in by_place.items()}
    visited=frozenset(str(x) for x in visited_candidate_ids)

    candidates=[]; applied=[]
    for place in compatible:
        c,refs=_overlay_candidate(place,facts_by_place,origin=origin,visited_candidate_ids=visited)
        candidates.append(c); applied.extend(refs)

    satisfied=[]; rejected=[]; unresolved=[]; uncertainty=set()
    for c in candidates:
        view=_consumer_view(c)
        resolutions=resolve_hard_constraints(request,view)
        if any(x.resolution is ConstraintResolution.VIOLATED for x in resolutions):
            rejected.append(c.candidate_id); continue
        if any(x.resolution is ConstraintResolution.UNRESOLVED for x in resolutions):
            unresolved.append(c.candidate_id)
            uncertainty.update(x.key for x in resolutions if x.resolution is ConstraintResolution.UNRESOLVED)
            continue
        uncertainty.update(material_uncertainty(view,profile.material_fields))
        satisfied.append(c)

    dqe=evaluate_decision_quality(_to_dqe_request(request),satisfied,domain=request.category,limit=recommendation_limit)
    recommended=tuple(dqe.recommended)
    best=recommended[0].candidate_id if recommended else None
    alts=tuple(x.candidate_id for x in recommended[1:])
    uncertainty.update(dqe.missing_information)

    # Ask at most one question, and only about missing user context, never to hide missing system evidence.
    can_change=bool(question) and (len(recommended)>1 or best is None)
    qcount=decision_effort_questions(decision_can_materially_change=can_change,enough_for_useful_answer=best is not None)
    ask=question if qcount else None

    status=dqe.status
    if not satisfied and unresolved: status="insufficient_data"
    elif best and dqe.status=="insufficient_data": status="qualified_with_uncertainty"
    if best and ask: status="useful_answer_with_one_question"

    tradeoffs=tuple(dict.fromkeys(t for x in recommended for t in x.tradeoffs))
    regrets=tuple(f"{x.candidate_id}:regret={x.regret_risk:.3f}" for x in recommended)
    return ContextualPersonalDecisionResult(
        request_id,status,understanding,profile,best,alts,tuple(rejected),tuple(unresolved),
        tuple(sorted(uncertainty)),tradeoffs,regrets,tuple(dict.fromkeys(applied)),bool(ask),ask,True,
    )
