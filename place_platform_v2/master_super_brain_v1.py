from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

POLICY_VERSION = "MSB-V1"
MATERIAL_BAD_EVIDENCE = {"unknown", "conflicting", "stale"}
VALID_REASON_KINDS = {"fact", "inference", "user_preference", "policy"}


@dataclass(frozen=True)
class DecisionConstraint:
    key: str
    operator: str
    value: Any
    strength: str = "soft"
    priority: float = 1.0


@dataclass(frozen=True)
class DecisionPreference:
    key: str
    direction: str
    weight: float = 1.0
    value: Any = None


@dataclass(frozen=True)
class EvidenceItem:
    field: str
    value: Any
    status: str = "unknown"
    confidence: float = 0.0
    observed_at: str | None = None
    source_ref: str | None = None


@dataclass(frozen=True)
class DecisionCandidate:
    candidate_id: str
    entity_type: str
    attributes: Mapping[str, Any]
    evidence: tuple[EvidenceItem, ...] = ()
    is_sponsored: bool = False
    promotion_ref: str | None = None


@dataclass(frozen=True)
class DecisionRequest:
    request_id: str
    goal: str
    decision_type: str = "select"
    category: str | None = None
    constraints: tuple[DecisionConstraint, ...] = ()
    preferences: tuple[DecisionPreference, ...] = ()
    provider: str | None = None
    provider_model: str | None = None


@dataclass(frozen=True)
class DecisionReason:
    kind: str
    text: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluatedCandidate:
    candidate_id: str
    role: str
    constraint_fit: float
    preference_fit: float
    evidence_confidence: float
    tradeoff_cost: float
    uncertainty_cost: float
    regret_risk: float
    reasons: tuple[DecisionReason, ...]
    tradeoffs: tuple[str, ...]
    uncertainties: tuple[str, ...]
    organic_score: float


@dataclass(frozen=True)
class DecisionAudit:
    policy_version: str = POLICY_VERSION
    provider_influenced_policy: bool = False


@dataclass(frozen=True)
class DecisionBoundary:
    human_decides: bool = True


@dataclass(frozen=True)
class DecisionResult:
    request_id: str
    status: str
    decision_summary: str
    recommended: tuple[EvaluatedCandidate, ...]
    material_dimensions: tuple[str, ...]
    comparison_notes: tuple[str, ...]
    main_failure_modes: tuple[str, ...]
    lower_regret_candidate_id: str | None
    upside_candidate_id: str | None
    missing_information: tuple[str, ...]
    clarifying_question: str | None
    decision_boundary: DecisionBoundary = field(default_factory=DecisionBoundary)
    audit: DecisionAudit = field(default_factory=DecisionAudit)


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _matches(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "lte":
        return actual is not None and actual <= expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "in":
        return actual in expected
    if operator == "contains":
        if actual is None:
            return False
        if isinstance(actual, str):
            return str(expected).casefold() in actual.casefold()
        try:
            return expected in actual
        except TypeError:
            return False
    if operator == "required":
        return actual is not None and actual != "" and actual != ()
    raise ValueError(f"unsupported constraint operator: {operator}")


def _evidence_for(candidate: DecisionCandidate, field_name: str) -> tuple[EvidenceItem, ...]:
    return tuple(x for x in candidate.evidence if x.field == field_name)


def _field_confidence(candidate: DecisionCandidate, field_name: str) -> tuple[float, tuple[str, ...]]:
    items = _evidence_for(candidate, field_name)
    if not items:
        return 0.0, (f"{field_name}:unknown",)
    uncertainties = []
    usable = []
    for item in items:
        status = item.status.casefold()
        conf = _clamp(item.confidence)
        if status == "verified":
            usable.append(conf)
        elif status == "supported":
            usable.append(conf * 0.85)
        elif status == "stale":
            usable.append(conf * 0.45)
            uncertainties.append(f"{field_name}:stale")
        elif status == "conflicting":
            usable.append(conf * 0.25)
            uncertainties.append(f"{field_name}:conflicting")
        else:
            usable.append(0.0)
            uncertainties.append(f"{field_name}:unknown")
    return (max(usable) if usable else 0.0), tuple(sorted(set(uncertainties)))


def _constraint_evaluation(
    request: DecisionRequest, candidate: DecisionCandidate
) -> tuple[bool, float, tuple[str, ...], tuple[str, ...]]:
    if not request.constraints:
        return True, 1.0, (), ()
    total_weight = 0.0
    satisfied_weight = 0.0
    hard_failures = []
    material_fields = []
    for c in request.constraints:
        weight = max(0.0, float(c.priority))
        total_weight += weight
        material_fields.append(c.key)
        ok = _matches(candidate.attributes.get(c.key), c.operator, c.value)
        if ok:
            satisfied_weight += weight
        elif c.strength == "hard":
            hard_failures.append(c.key)
    fit = 1.0 if total_weight == 0 else satisfied_weight / total_weight
    return not hard_failures, _clamp(fit), tuple(hard_failures), tuple(material_fields)


def _preference_fit(request: DecisionRequest, candidate: DecisionCandidate) -> tuple[float, tuple[str, ...]]:
    if not request.preferences:
        return 0.5, ()
    total = 0.0
    achieved = 0.0
    dimensions = []
    for p in request.preferences:
        w = max(0.0, float(p.weight))
        total += w
        dimensions.append(p.key)
        actual = candidate.attributes.get(p.key)
        if actual is None:
            continue
        if p.direction == "prefer_match":
            achieved += w if actual == p.value else 0.0
        elif p.direction == "prefer_low":
            # Generic normalized inverse utility when values are already in [0,1].
            try:
                achieved += w * (1.0 - _clamp(float(actual)))
            except (TypeError, ValueError):
                pass
        elif p.direction == "prefer_high":
            try:
                achieved += w * _clamp(float(actual))
            except (TypeError, ValueError):
                pass
        else:
            raise ValueError(f"unsupported preference direction: {p.direction}")
    return (0.5 if total == 0 else _clamp(achieved / total)), tuple(dimensions)


def _evidence_quality(candidate: DecisionCandidate, material_fields: Sequence[str]) -> tuple[float, tuple[str, ...]]:
    fields = tuple(dict.fromkeys(material_fields))
    if not fields:
        return 0.5, ()
    values = []
    uncertainties = []
    for f in fields:
        conf, notes = _field_confidence(candidate, f)
        values.append(conf)
        uncertainties.extend(notes)
    # Weakest-link confidence for material decision fields.
    return min(values), tuple(sorted(set(uncertainties)))


def _regret_risk(
    constraint_fit: float,
    evidence_confidence: float,
    preference_fit: float,
    uncertainty_cost: float,
) -> float:
    return _clamp(
        (1.0 - constraint_fit) * 0.35
        + (1.0 - evidence_confidence) * 0.35
        + (1.0 - preference_fit) * 0.15
        + uncertainty_cost * 0.15
    )


def evaluate_candidates(
    request: DecisionRequest,
    candidates: Iterable[DecisionCandidate],
    *,
    limit: int = 8,
) -> DecisionResult:
    if not request.goal.strip():
        raise ValueError("goal is required")
    if limit <= 0:
        raise ValueError("limit must be positive")

    evaluated = []
    rejected_hard = []
    global_material_dimensions = []

    for c in candidates:
        hard_ok, constraint_fit, hard_failures, constraint_dims = _constraint_evaluation(request, c)
        preference_fit, pref_dims = _preference_fit(request, c)
        material_dims = tuple(dict.fromkeys((*constraint_dims, *pref_dims)))
        global_material_dimensions.extend(material_dims)
        evidence_confidence, uncertainties = _evidence_quality(c, material_dims)

        if not hard_ok:
            rejected_hard.append((c.candidate_id, hard_failures))
            continue

        uncertainty_cost = _clamp(len(uncertainties) / max(1, len(material_dims)))
        tradeoff_cost = _clamp((1.0 - constraint_fit) * 0.6 + (1.0 - preference_fit) * 0.4)
        regret_risk = _regret_risk(
            constraint_fit, evidence_confidence, preference_fit, uncertainty_cost
        )

        # Sponsorship is deliberately absent from the organic score.
        organic_score = _clamp(
            constraint_fit * 0.35
            + preference_fit * 0.25
            + evidence_confidence * 0.25
            + (1.0 - regret_risk) * 0.15
        )

        evidence_refs = tuple(
            sorted(
                {
                    e.source_ref
                    for e in c.evidence
                    if e.source_ref and e.field in material_dims
                }
            )
        )
        reasons = (
            DecisionReason(
                "fact",
                f"constraint_fit={constraint_fit:.3f}",
                evidence_refs,
            ),
            DecisionReason(
                "inference",
                f"evidence_confidence={evidence_confidence:.3f}; regret_risk={regret_risk:.3f}",
                evidence_refs,
            ),
        )
        tradeoffs = ()
        if preference_fit < 0.999:
            tradeoffs = (f"preference_fit={preference_fit:.3f}",)

        evaluated.append(
            EvaluatedCandidate(
                candidate_id=c.candidate_id,
                role="alternative",
                constraint_fit=constraint_fit,
                preference_fit=preference_fit,
                evidence_confidence=evidence_confidence,
                tradeoff_cost=tradeoff_cost,
                uncertainty_cost=uncertainty_cost,
                regret_risk=regret_risk,
                reasons=reasons,
                tradeoffs=tradeoffs,
                uncertainties=uncertainties,
                organic_score=organic_score,
            )
        )

    if not evaluated:
        status = "no_valid_candidate" if rejected_hard else "insufficient_data"
        return DecisionResult(
            request_id=request.request_id,
            status=status,
            decision_summary="No valid candidate can be recommended under the current contract.",
            recommended=(),
            material_dimensions=tuple(dict.fromkeys(global_material_dimensions)),
            comparison_notes=(),
            main_failure_modes=tuple(
                f"{cid}:hard_constraint:{','.join(fails)}" for cid, fails in rejected_hard
            ),
            lower_regret_candidate_id=None,
            upside_candidate_id=None,
            missing_information=(),
            clarifying_question=None,
        )

    # Deterministic ordering; provider metadata is never consulted.
    evaluated.sort(key=lambda x: (-x.organic_score, x.regret_risk, x.candidate_id))
    lower_regret = min(evaluated, key=lambda x: (x.regret_risk, -x.organic_score, x.candidate_id))
    upside = max(evaluated, key=lambda x: (x.preference_fit, x.organic_score, x.candidate_id))

    out = []
    for index, e in enumerate(evaluated[:limit]):
        role = "best_fit" if index == 0 else "alternative"
        if e.candidate_id == lower_regret.candidate_id and index != 0:
            role = "lower_regret"
        if e.candidate_id == upside.candidate_id and index != 0 and role == "alternative":
            role = "upside"
        out.append(
            EvaluatedCandidate(
                candidate_id=e.candidate_id,
                role=role,
                constraint_fit=e.constraint_fit,
                preference_fit=e.preference_fit,
                evidence_confidence=e.evidence_confidence,
                tradeoff_cost=e.tradeoff_cost,
                uncertainty_cost=e.uncertainty_cost,
                regret_risk=e.regret_risk,
                reasons=e.reasons,
                tradeoffs=e.tradeoffs,
                uncertainties=e.uncertainties,
                organic_score=e.organic_score,
            )
        )

    missing = sorted(
        {
            u.split(":", 1)[0]
            for e in out
            for u in e.uncertainties
            if u.endswith(":unknown")
        }
    )
    status = "ok"
    if out and all(e.evidence_confidence <= 0.0 for e in out):
        status = "insufficient_data"

    return DecisionResult(
        request_id=request.request_id,
        status=status,
        decision_summary="Structured decision produced under MSB-V1.",
        recommended=tuple(out),
        material_dimensions=tuple(dict.fromkeys(global_material_dimensions)),
        comparison_notes=tuple(
            f"{e.candidate_id}:score={e.organic_score:.3f},regret={e.regret_risk:.3f}"
            for e in out
        ),
        main_failure_modes=tuple(
            f"{e.candidate_id}:{u}" for e in out for u in e.uncertainties
        ),
        lower_regret_candidate_id=lower_regret.candidate_id,
        upside_candidate_id=upside.candidate_id,
        missing_information=tuple(missing),
        clarifying_question=(
            "Some material decision information is unknown."
            if missing else None
        ),
    )
