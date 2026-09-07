
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

POLICY_VERSION = "SEMANTIC-CATEGORY-VOCABULARY-ALIGNMENT-POLICY-EXTENSION-CHALLENGE-V1"

class VocabularyKind(str, Enum):
    LEAF_CATEGORY="LEAF_CATEGORY"
    DOMAIN_TOKEN="DOMAIN_TOKEN"
    ROUTER_TOKEN="ROUTER_TOKEN"
    GOAL_TOKEN="GOAL_TOKEN"
    UNKNOWN="UNKNOWN"

class AlignmentDecision(str, Enum):
    PRESERVE_SAME_KIND="PRESERVE_SAME_KIND"
    LEAF_WITH_DOMAIN_CONTEXT="LEAF_WITH_DOMAIN_CONTEXT"
    LEGACY_CONTEXT_ONLY="LEGACY_CONTEXT_ONLY"
    GOAL_NOT_CATEGORY="GOAL_NOT_CATEGORY"
    CONFLICT="CONFLICT"
    UNKNOWN="UNKNOWN"

# Single targeted delta from prior policy:
#   fuel becomes a LEAF_CATEGORY.
# fuel_station remains a ROUTER_TOKEN.
LEAF_CATEGORIES=frozenset({
    "vegetarian","vegan","restaurant","cafe","fuel","attraction","park","temple",
    "laundry","car_repair","clinic","pharmacy","nature",
})
DOMAIN_TOKENS=frozenset({"eat","go","service"})
ROUTER_TOKENS=frozenset({"fuel_station","service_place"})
GOAL_TOKENS=frozenset({
    "find_local_option","find_place_to_eat","find_place_to_go","find_service","find_fuel_station",
})
LEAF_TO_DOMAIN={
    "vegetarian":"eat","vegan":"eat","restaurant":"eat","cafe":"eat",
    "fuel":"service",
    "attraction":"go","park":"go","temple":"go","nature":"go",
    "laundry":"service","car_repair":"service","clinic":"service","pharmacy":"service",
}
ROUTER_TO_DOMAIN={"fuel_station":"service","service_place":"service"}

@dataclass(frozen=True)
class AlignmentResult:
    existing_token:str|None
    existing_kind:VocabularyKind
    semantic_leaf:str|None
    leaf_category:str|None
    domain_context:str|None
    decision:AlignmentDecision
    leaf_authority_preserved:bool
    goal_used_as_category:bool
    reason:str

def classify_token(token:str|None)->VocabularyKind:
    if token is None or not str(token).strip():
        return VocabularyKind.UNKNOWN
    t=str(token).strip()
    if t in LEAF_CATEGORIES:
        return VocabularyKind.LEAF_CATEGORY
    if t in DOMAIN_TOKENS:
        return VocabularyKind.DOMAIN_TOKEN
    if t in ROUTER_TOKENS:
        return VocabularyKind.ROUTER_TOKEN
    if t in GOAL_TOKENS:
        return VocabularyKind.GOAL_TOKEN
    return VocabularyKind.UNKNOWN

def align_existing_and_leaf(existing_token:str|None, semantic_leaf:str|None)->AlignmentResult:
    ek=classify_token(existing_token)
    lk=classify_token(semantic_leaf)

    if semantic_leaf is not None and lk != VocabularyKind.LEAF_CATEGORY:
        return AlignmentResult(
            existing_token,ek,semantic_leaf,None,None,
            AlignmentDecision.CONFLICT,False,False,
            "semantic leaf input is not leaf category"
        )

    if ek==VocabularyKind.GOAL_TOKEN:
        return AlignmentResult(
            existing_token,ek,semantic_leaf,semantic_leaf,
            LEAF_TO_DOMAIN.get(semantic_leaf),
            AlignmentDecision.GOAL_NOT_CATEGORY,True,False,
            "goal token is never category authority"
        )

    if ek==VocabularyKind.LEAF_CATEGORY:
        if semantic_leaf is None or existing_token==semantic_leaf:
            leaf=existing_token
            return AlignmentResult(
                existing_token,ek,semantic_leaf,leaf,LEAF_TO_DOMAIN.get(leaf),
                AlignmentDecision.PRESERVE_SAME_KIND,True,False,
                "existing leaf preserved"
            )
        return AlignmentResult(
            existing_token,ek,semantic_leaf,None,None,
            AlignmentDecision.CONFLICT,False,False,
            "leaf category conflict"
        )

    if ek in {VocabularyKind.DOMAIN_TOKEN,VocabularyKind.ROUTER_TOKEN}:
        actual_domain=(
            existing_token if ek==VocabularyKind.DOMAIN_TOKEN
            else ROUTER_TO_DOMAIN.get(existing_token)
        )
        if semantic_leaf is None:
            return AlignmentResult(
                existing_token,ek,None,None,actual_domain,
                AlignmentDecision.LEGACY_CONTEXT_ONLY,True,False,
                "legacy token retained only as routing/domain context"
            )
        expected=LEAF_TO_DOMAIN.get(semantic_leaf)
        if expected and actual_domain and expected!=actual_domain:
            return AlignmentResult(
                existing_token,ek,semantic_leaf,None,actual_domain,
                AlignmentDecision.CONFLICT,False,False,
                "legacy domain conflicts with semantic leaf"
            )
        return AlignmentResult(
            existing_token,ek,semantic_leaf,semantic_leaf,actual_domain or expected,
            AlignmentDecision.LEAF_WITH_DOMAIN_CONTEXT,True,False,
            "leaf preserved; legacy token is context only"
        )

    if ek==VocabularyKind.UNKNOWN:
        if semantic_leaf is not None:
            return AlignmentResult(
                existing_token,ek,semantic_leaf,semantic_leaf,
                LEAF_TO_DOMAIN.get(semantic_leaf),
                AlignmentDecision.LEAF_WITH_DOMAIN_CONTEXT,True,False,
                "unknown existing token is not authority"
            )
        return AlignmentResult(
            existing_token,ek,None,None,None,
            AlignmentDecision.UNKNOWN,True,False,
            "no known vocabulary evidence"
        )

    return AlignmentResult(
        existing_token,ek,semantic_leaf,None,None,
        AlignmentDecision.UNKNOWN,True,False,
        "unhandled state"
    )
