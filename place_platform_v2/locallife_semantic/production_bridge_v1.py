
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from typing import Any

from place_platform_v2.intent_context_understanding_v1 import (
    understand_user_request as _baseline_understand_user_request,
)
from .local_engine_v1 import understand_local
from .category_mapping_policy_v1 import MappingDecision, decide_category_mapping
from .vocabulary_alignment_policy_v1 import (
    AlignmentDecision,
    VocabularyKind,
    LEAF_CATEGORIES,
    align_existing_and_leaf,
    classify_token,
)

BRIDGE_VERSION = "LOCALLIFE-SEMANTIC-PRODUCTION-SHADOW-BRIDGE-V1"

FORBIDDEN_AUTHORITY_FIELDS = frozenset({
    "ranking_score","organic_score","best_fit_candidate_id","candidate_id",
    "candidate_ids","winner","recommended","recommendation","sponsor_weight",
    "publication_write","canonical_write","projection_write","place_id",
    "publication_state",
})

CATEGORY_LIKE_NAMES = frozenset({
    "category","categories","category_hint","category_hints",
    "domain_category","place_category","target_category",
})

_LAST_TRACE: dict[str, Any] | None = None

def _is_near_me(local) -> bool:
    kind = getattr(getattr(local, "location_intent", None), "kind", None)
    return getattr(kind, "value", None) == "NEAR_ME"

def _local_time_signal(local) -> str | None:
    kind = getattr(getattr(local, "time_context", None), "kind", None)
    value = getattr(kind, "value", None)
    if value and value not in {"NONE","UNKNOWN","UNSPECIFIED"}:
        return str(value)
    return None

def _merge_sequence_like(current, additions: list[str]):
    additions = [x for x in additions if x]
    if not additions:
        return current
    if current is None:
        return tuple(dict.fromkeys(additions))
    if isinstance(current, tuple):
        return tuple(dict.fromkeys(list(current) + additions))
    if isinstance(current, list):
        return list(dict.fromkeys(list(current) + additions))
    if isinstance(current, set):
        return set(current).union(additions)
    return current

def _safe_overlay(existing, local):
    if not is_dataclass(existing):
        raise TypeError("StructuredDecisionRequest must remain a dataclass")

    available = {f.name for f in fields(existing)}
    updates = {}

    if "unresolved_context" in available:
        current = getattr(existing, "unresolved_context")
        additions = list(getattr(local, "unresolved_ambiguities", ()) or ())
        merged = _merge_sequence_like(current, additions)
        if merged is not current or current is None:
            updates["unresolved_context"] = merged

    for name in list(updates):
        if name.lower() in FORBIDDEN_AUTHORITY_FIELDS:
            updates.pop(name, None)

    out = replace(existing, **updates)
    if type(out) is not type(existing):
        raise TypeError("semantic bridge changed StructuredDecisionRequest type")
    return out

def _nested_category_signal(obj: Any) -> dict:
    if obj is None:
        return {"present": False, "value": None}

    if isinstance(obj, dict):
        for key in CATEGORY_LIKE_NAMES:
            if key in obj:
                return {"present": True, "value": obj.get(key)}
        return {"present": False, "value": None}

    if is_dataclass(obj):
        names = {f.name for f in fields(obj)}
        for key in CATEGORY_LIKE_NAMES:
            if key in names:
                return {"present": True, "value": getattr(obj, key)}
        return {"present": False, "value": None}

    for key in CATEGORY_LIKE_NAMES:
        if hasattr(obj, key):
            return {"present": True, "value": getattr(obj, key)}

    return {"present": False, "value": None}

def _resolved(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (tuple, list, set, dict)):
        return bool(value)
    return True

def _resolve_category(existing, overlaid, local, text: str):
    field_names = {f.name for f in fields(overlaid)}
    if "category" not in field_names:
        return overlaid, {
            "status":"NO_CATEGORY_FIELD",
            "existing_category":None,
            "final_category":None,
        }

    existing_category = getattr(existing, "category", None)
    existing_kind = classify_token(existing_category)
    local_hints = tuple(getattr(local, "category_hints", ()) or ())

    # Safety veto first: mutation/publication instructions and multiple explicit
    # categories must fail closed before a legacy baseline leaf can be preserved.
    safety_mapping = decide_category_mapping(
        text,
        existing_category=None,
        local_category_hints=local_hints,
    )
    if safety_mapping.decision in {MappingDecision.UNSUPPORTED, MappingDecision.CONFLICT}:
        blocked = replace(overlaid, category=None)
        return blocked, {
            "status":(
                "FAIL_CLOSED_MUTATION_OR_UNSUPPORTED"
                if safety_mapping.decision == MappingDecision.UNSUPPORTED
                else "FAIL_CLOSED_EXPLICIT_CATEGORY_CONFLICT"
            ),
            "existing_category":existing_category,
            "existing_kind":existing_kind.value,
            "mapping_decision":safety_mapping.decision.value,
            "final_category":None,
            "local_hints":list(local_hints),
        }

    # Existing proven semantic leaf remains authoritative only after safety vetoes.
    if existing_kind == VocabularyKind.LEAF_CATEGORY:
        return overlaid, {
            "status":"PRESERVE_EXISTING_LEAF",
            "existing_category":existing_category,
            "existing_kind":existing_kind.value,
            "mapping_decision":safety_mapping.decision.value,
            "final_category":existing_category,
            "local_hints":list(local_hints),
        }

    # Domain/router/goal/unknown tokens are never leaf authority.
    mapping = safety_mapping

    if mapping.decision != MappingDecision.PROMOTE or not mapping.promoted_category:
        return overlaid, {
            "status":"FAIL_CLOSED_NO_EXPLICIT_LEAF",
            "existing_category":existing_category,
            "existing_kind":existing_kind.value,
            "mapping_decision":mapping.decision.value,
            "final_category":getattr(overlaid, "category", None),
            "local_hints":list(local_hints),
        }

    leaf = mapping.promoted_category
    alignment = align_existing_and_leaf(existing_category, leaf)

    if alignment.decision not in {
        AlignmentDecision.LEAF_WITH_DOMAIN_CONTEXT,
        AlignmentDecision.GOAL_NOT_CATEGORY,
        AlignmentDecision.PRESERVE_SAME_KIND,
    } or not alignment.leaf_category:
        return overlaid, {
            "status":"FAIL_CLOSED_VOCABULARY_CONFLICT",
            "existing_category":existing_category,
            "existing_kind":existing_kind.value,
            "mapping_decision":mapping.decision.value,
            "alignment_decision":alignment.decision.value,
            "final_category":getattr(overlaid, "category", None),
            "local_hints":list(local_hints),
        }

    target = alignment.leaf_category

    decision_object = getattr(overlaid, "decision_object", None) if "decision_object" in field_names else None
    nested = _nested_category_signal(decision_object)

    # Preserve prior coherence safety: never partially update a duplicated
    # unresolved/conflicting category signal inside decision_object.
    if nested["present"]:
        if not _resolved(nested["value"]):
            return overlaid, {
                "status":"FAIL_CLOSED_DECISION_OBJECT_SYNC_REQUIRED",
                "existing_category":existing_category,
                "existing_kind":existing_kind.value,
                "mapping_decision":mapping.decision.value,
                "alignment_decision":alignment.decision.value,
                "final_category":getattr(overlaid, "category", None),
                "local_hints":list(local_hints),
            }
        if str(nested["value"]).strip() != str(target).strip():
            return overlaid, {
                "status":"FAIL_CLOSED_DECISION_OBJECT_CONFLICT",
                "existing_category":existing_category,
                "existing_kind":existing_kind.value,
                "mapping_decision":mapping.decision.value,
                "alignment_decision":alignment.decision.value,
                "final_category":getattr(overlaid, "category", None),
                "local_hints":list(local_hints),
            }

    promoted = replace(overlaid, category=target)
    return promoted, {
        "status":"PROMOTION_APPLIED",
        "existing_category":existing_category,
        "existing_kind":existing_kind.value,
        "mapping_decision":mapping.decision.value,
        "alignment_decision":alignment.decision.value,
        "aligned_domain_context":alignment.domain_context,
        "final_category":target,
        "local_hints":list(local_hints),
    }

def understand_user_request_with_semantics(text: str, *baseline_args, **baseline_kwargs):
    global _LAST_TRACE

    baseline = _baseline_understand_user_request(text, *baseline_args, **baseline_kwargs)
    local = understand_local(text)
    overlaid = _safe_overlay(baseline, local)
    integrated, category_meta = _resolve_category(baseline, overlaid, local, text)

    if type(integrated) is not type(baseline):
        raise TypeError("semantic wrapper changed baseline request type")

    result_fields = {f.name for f in fields(integrated)} if is_dataclass(integrated) else set()
    forbidden = sorted(x for x in result_fields if x.lower() in FORBIDDEN_AUTHORITY_FIELDS)
    if forbidden:
        raise ValueError("semantic wrapper exposed forbidden authority fields: " + ",".join(forbidden))

    _LAST_TRACE = {
        "bridge_version": BRIDGE_VERSION,
        "text": text,
        "baseline_positional_arg_count": len(baseline_args),
        "baseline_keyword_names": sorted(str(k) for k in baseline_kwargs.keys()),
        "local_category_hints": list(getattr(local, "category_hints", ()) or ()),
        "baseline_category": getattr(baseline, "category", None),
        "final_category": getattr(integrated, "category", None),
        "same_exact_type": type(integrated) is type(baseline),
        "category_meta": category_meta,
        "forbidden_authority_fields": forbidden,
    }
    return integrated

def get_last_semantic_trace() -> dict | None:
    if _LAST_TRACE is None:
        return None
    return dict(_LAST_TRACE)
