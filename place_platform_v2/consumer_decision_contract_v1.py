"""Consumer Decision Contract V1.1.

Deterministic contract for consumer decision quality.  Hard constraints are
tri-state: SATISFIED, VIOLATED, or UNRESOLVED.  Unknown is never silently
converted to either True or False.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence, Tuple

ALLOWED_CATEGORIES={"eat","vegetarian","shopping","go","service"}
ALLOWED_STRENGTHS={"hard","soft"}
ALLOWED_EVIDENCE_STATES={"verified","supported_inference","user_preference","policy","missing","stale","conflicting","unknown"}
MATERIAL_UNRESOLVED_STATES={"missing","stale","conflicting","unknown"}
ALLOWED_OPERATORS={"eq","neq","lte","gte","in","contains","required"}

class ConstraintResolution(str, Enum):
    SATISFIED="SATISFIED"
    VIOLATED="VIOLATED"
    UNRESOLVED="UNRESOLVED"

@dataclass(frozen=True)
class ConsumerCondition:
    key:str; value:Any=None; strength:str="soft"; weight:float=1.0; source:str="user"; operator:str="eq"
    def __post_init__(self):
        if not self.key: raise ValueError("condition key required")
        if self.strength not in ALLOWED_STRENGTHS: raise ValueError("invalid condition strength")
        if self.weight<0: raise ValueError("weight must be non-negative")
        if self.operator not in ALLOWED_OPERATORS: raise ValueError("unsupported condition operator")

@dataclass(frozen=True)
class ConsumerContext:
    current_time:str|None=None; current_location:tuple[float,float]|None=None; urgency:str|None=None; group_size:int|None=None; transport_mode:str|None=None; budget_sensitivity:str|None=None; duration_minutes:int|None=None; with_children:bool|None=None; with_elderly:bool|None=None

@dataclass(frozen=True)
class MaterialEvidence:
    field:str; state:str; value:Any=None; observed_at:str|None=None; source_ref:str|None=None; confidence:float|None=None
    def __post_init__(self):
        if not self.field: raise ValueError("evidence field required")
        if self.state not in ALLOWED_EVIDENCE_STATES: raise ValueError("invalid evidence state")
        if self.confidence is not None and not (0<=self.confidence<=1): raise ValueError("confidence must be between 0 and 1")

@dataclass(frozen=True)
class ConsumerDecisionRequest:
    request_id:str; goal:str; category:str; hard_constraints:Tuple[ConsumerCondition,...]=(); preferences:Tuple[ConsumerCondition,...]=(); context:ConsumerContext=field(default_factory=ConsumerContext)
    def __post_init__(self):
        if not self.request_id: raise ValueError("request_id required")
        if not self.goal: raise ValueError("goal required")
        if self.category not in ALLOWED_CATEGORIES: raise ValueError("unsupported category")
        if any(c.strength!="hard" for c in self.hard_constraints): raise ValueError("hard_constraints must all be hard")
        if any(c.strength!="soft" for c in self.preferences): raise ValueError("preferences must all be soft")

@dataclass(frozen=True)
class CandidateDecisionView:
    candidate_id:str; attributes:Mapping[str,Any]; evidence:Tuple[MaterialEvidence,...]=(); is_sponsored:bool=False; promotion_refs:Tuple[str,...]=()
    def evidence_for(self,field:str)->Tuple[MaterialEvidence,...]: return tuple(e for e in self.evidence if e.field==field)

@dataclass(frozen=True)
class HardConstraintAssessment:
    key:str; resolution:ConstraintResolution; reason:str

@dataclass(frozen=True)
class CandidateDecisionAssessment:
    candidate_id:str; hard_constraint_failures:Tuple[str,...]=(); hard_constraint_unresolved:Tuple[str,...]=(); material_tradeoffs:Tuple[str,...]=(); uncertainty_fields:Tuple[str,...]=(); regret_risks:Tuple[str,...]=(); organic_fit_eligible:bool=True

@dataclass(frozen=True)
class ConsumerDecisionOutcome:
    request_id:str; best_fit_candidate_id:str|None; alternative_candidate_ids:Tuple[str,...]; rejected_candidate_ids:Tuple[str,...]; needs_user_input:bool; highest_value_question:str|None; assessments:Tuple[CandidateDecisionAssessment,...]; human_final_decision:bool=True
    def __post_init__(self):
        if self.needs_user_input and not self.highest_value_question: raise ValueError("highest_value_question required when user input is needed")
        if not self.needs_user_input and self.highest_value_question: raise ValueError("question must be absent when user input is not needed")
        if not self.human_final_decision: raise ValueError("human_final_decision must remain true")


def _matches(actual:Any, operator:str, expected:Any)->bool:
    if operator=="eq": return actual==expected
    if operator=="neq": return actual!=expected
    if operator=="lte": return actual is not None and actual<=expected
    if operator=="gte": return actual is not None and actual>=expected
    if operator=="in": return actual in expected
    if operator=="contains":
        if actual is None: return False
        if isinstance(actual,str): return str(expected).casefold() in actual.casefold()
        try: return expected in actual
        except TypeError: return False
    if operator=="required": return actual is not None and actual!="" and actual!=()
    raise ValueError("unsupported condition operator")


def resolve_hard_constraint(condition:ConsumerCondition,candidate:CandidateDecisionView)->HardConstraintAssessment:
    """Resolve a hard condition without inventing a fact.

    A material field with absent/bad evidence is UNRESOLVED even when an
    attribute value happens to be present. This prevents stale/conflicting
    values from masquerading as proven satisfaction.
    """
    evidence=candidate.evidence_for(condition.key)
    if condition.key not in candidate.attributes:
        return HardConstraintAssessment(condition.key,ConstraintResolution.UNRESOLVED,"attribute_missing")
    if evidence and any(e.state in MATERIAL_UNRESOLVED_STATES for e in evidence):
        return HardConstraintAssessment(condition.key,ConstraintResolution.UNRESOLVED,"material_evidence_unresolved")
    actual=candidate.attributes.get(condition.key)
    if _matches(actual,condition.operator,condition.value):
        return HardConstraintAssessment(condition.key,ConstraintResolution.SATISFIED,"proven_match")
    return HardConstraintAssessment(condition.key,ConstraintResolution.VIOLATED,"proven_violation")


def resolve_hard_constraints(request:ConsumerDecisionRequest,candidate:CandidateDecisionView)->Tuple[HardConstraintAssessment,...]:
    return tuple(resolve_hard_constraint(c,candidate) for c in request.hard_constraints)


def hard_constraint_eligible(request:ConsumerDecisionRequest,candidate:CandidateDecisionView):
    """Compatibility helper. Eligible means every hard condition is SATISFIED.

    Returns (eligible, violated_keys). Use resolve_hard_constraints when the
    caller needs to distinguish VIOLATED from UNRESOLVED.
    """
    results=resolve_hard_constraints(request,candidate)
    failures=tuple(x.key for x in results if x.resolution is ConstraintResolution.VIOLATED)
    return (bool(all(x.resolution is ConstraintResolution.SATISFIED for x in results)),failures)


def material_uncertainty(candidate:CandidateDecisionView,fields:Sequence[str])->tuple[str,...]:
    out=[]
    for f in fields:
        items=candidate.evidence_for(f)
        if not items or any(e.state in MATERIAL_UNRESOLVED_STATES for e in items): out.append(f)
    return tuple(dict.fromkeys(out))

def promotion_can_affect_value(*,relevant:bool,valid:bool,eligible:bool,linked:bool)->bool: return bool(relevant and valid and eligible and linked)
def sponsorship_affects_organic_fit(candidate:CandidateDecisionView)->bool: return False

def should_ask_highest_value_question(*,decision_can_materially_change:bool,enough_for_useful_answer:bool)->bool:
    return bool(decision_can_materially_change)

def decision_effort_questions(*,decision_can_materially_change:bool,enough_for_useful_answer:bool)->int:
    """Minimum Decision Effort: zero questions when answer is already useful; otherwise at most one."""
    return 1 if should_ask_highest_value_question(decision_can_materially_change=decision_can_materially_change,enough_for_useful_answer=enough_for_useful_answer) else 0
