from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping, Sequence

from .master_super_brain_v1 import (
    DecisionCandidate,
    DecisionConstraint,
    DecisionPreference,
    DecisionRequest,
    DecisionReason,
    EvaluatedCandidate,
    DecisionResult,
    DecisionAudit,
    DecisionBoundary,
    EvidenceItem,
)

POLICY_VERSION = "MSB-V1-DQE1"


@dataclass(frozen=True)
class DomainPolicy:
    name: str
    regret_weights: Mapping[str, float] = field(default_factory=dict)
    material_fields: tuple[str, ...] = ()


DOMAIN_POLICIES = {
    "eat": DomainPolicy(
        "eat",
        regret_weights={"open_now": 1.4, "distance_norm": 1.0, "diet_match": 1.3},
        material_fields=("open_now", "distance_norm", "diet_match"),
    ),
    "vegetarian": DomainPolicy(
        "vegetarian",
        regret_weights={"open_now": 1.4, "distance_norm": 1.0, "vegetarian": 1.6},
        material_fields=("open_now", "distance_norm", "vegetarian"),
    ),
    "shopping": DomainPolicy(
        "shopping",
        regret_weights={"in_stock": 1.5, "price_norm": 1.0, "distance_norm": .8},
        material_fields=("in_stock", "price_norm", "distance_norm"),
    ),
    "go": DomainPolicy(
        "go",
        regret_weights={"open_now": 1.2, "weather_fit": 1.2, "travel_time_norm": 1.0},
        material_fields=("open_now", "weather_fit", "travel_time_norm"),
    ),
    "service": DomainPolicy(
        "service",
        regret_weights={"available_now": 1.5, "capability_match": 1.5, "distance_norm": .8},
        material_fields=("available_now", "capability_match", "distance_norm"),
    ),
}


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
    raise ValueError(f"unsupported operator: {operator}")


def _evidence_by_field(candidate: DecisionCandidate) -> dict[str, list[EvidenceItem]]:
    out: dict[str, list[EvidenceItem]] = {}
    for item in candidate.evidence:
        out.setdefault(item.field, []).append(item)
    return out


def _status_multiplier(status: str) -> float:
    return {
        "verified": 1.0,
        "supported": 0.85,
        "stale": 0.45,
        "conflicting": 0.25,
        "unknown": 0.0,
    }.get(status.casefold(), 0.0)


def _field_confidence(items: Sequence[EvidenceItem]) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    if not items:
        return 0.0, ("unknown",), ()
    scores = []
    uncertainties = []
    refs = []
    for item in items:
        score = _clamp(item.confidence) * _status_multiplier(item.status)
        scores.append(score)
        st = item.status.casefold()
        if st in {"stale", "conflicting", "unknown"}:
            uncertainties.append(st)
        if item.source_ref:
            refs.append(item.source_ref)
    return max(scores), tuple(sorted(set(uncertainties))), tuple(sorted(set(refs)))


def _constraint_fit(
    request: DecisionRequest, candidate: DecisionCandidate
) -> tuple[bool, float, list[DecisionReason], list[str], list[str]]:
    if not request.constraints:
        return True, 1.0, [], [], []
    total = 0.0
    hit = 0.0
    hard_fail = False
    reasons: list[DecisionReason] = []
    tradeoffs: list[str] = []
    fields: list[str] = []
    for c in request.constraints:
        w = max(0.0, float(c.priority))
        total += w
        fields.append(c.key)
        ok = _matches(candidate.attributes.get(c.key), c.operator, c.value)
        if ok:
            hit += w
            reasons.append(DecisionReason("policy", f"constraint_met:{c.key}"))
        else:
            if c.strength == "hard":
                hard_fail = True
                tradeoffs.append(f"hard_constraint_failed:{c.key}")
            else:
                tradeoffs.append(f"soft_constraint_missed:{c.key}")
    fit = 1.0 if total == 0 else _clamp(hit / total)
    return (not hard_fail), fit, reasons, tradeoffs, fields


def _preference_fit(
    request: DecisionRequest, candidate: DecisionCandidate
) -> tuple[float, list[DecisionReason], list[str], list[str]]:
    if not request.preferences:
        return 0.5, [], [], []
    total = 0.0
    utility = 0.0
    reasons: list[DecisionReason] = []
    tradeoffs: list[str] = []
    fields: list[str] = []
    for p in request.preferences:
        w = max(0.0, float(p.weight))
        total += w
        fields.append(p.key)
        actual = candidate.attributes.get(p.key)
        score = 0.0
        if p.direction == "prefer_match":
            score = 1.0 if actual == p.value else 0.0
        elif p.direction == "prefer_low":
            try:
                score = 1.0 - _clamp(float(actual))
            except (TypeError, ValueError):
                score = 0.0
        elif p.direction == "prefer_high":
            try:
                score = _clamp(float(actual))
            except (TypeError, ValueError):
                score = 0.0
        else:
            raise ValueError(f"unsupported preference direction: {p.direction}")
        utility += w * score
        if score >= .8:
            reasons.append(DecisionReason("user_preference", f"preference_strong:{p.key}"))
        elif score < .5:
            tradeoffs.append(f"preference_tradeoff:{p.key}")
    return (0.5 if total == 0 else _clamp(utility / total)), reasons, tradeoffs, fields


def _evidence_profile(
    candidate: DecisionCandidate,
    fields: Sequence[str],
) -> tuple[float, list[str], list[DecisionReason]]:
    by_field = _evidence_by_field(candidate)
    if not fields:
        return .5, [], []
    confidences = []
    uncertainties: list[str] = []
    reasons: list[DecisionReason] = []
    for field in dict.fromkeys(fields):
        conf, statuses, refs = _field_confidence(by_field.get(field, ()))
        confidences.append(conf)
        for status in statuses:
            uncertainties.append(f"{field}:{status}")
        if conf > 0:
            reasons.append(
                DecisionReason(
                    "fact",
                    f"evidence:{field}:confidence={conf:.3f}",
                    refs,
                )
            )
    # weakest material field governs decision confidence
    return min(confidences), sorted(set(uncertainties)), reasons


def _weighted_regret(
    candidate: DecisionCandidate,
    policy: DomainPolicy,
    evidence_confidence: float,
    constraint_fit: float,
    preference_fit: float,
    uncertainties: Sequence[str],
) -> float:
    risk = (1 - evidence_confidence) * .40 + (1 - constraint_fit) * .25 + (1 - preference_fit) * .15
    uncertainty_fields = {x.split(":", 1)[0] for x in uncertainties}
    if uncertainty_fields:
        weights = [policy.regret_weights.get(f, 1.0) for f in uncertainty_fields]
        risk += min(.2, sum(weights) / max(1, len(weights)) * .08)
    return _clamp(risk)


def evaluate_decision_quality(
    request: DecisionRequest,
    candidates: Iterable[DecisionCandidate],
    *,
    domain: str | None = None,
    limit: int = 8,
) -> DecisionResult:
    if not request.goal.strip():
        raise ValueError("goal is required")
    if limit <= 0:
        raise ValueError("limit must be positive")

    domain_key = (domain or request.category or "eat").casefold()
    policy = DOMAIN_POLICIES.get(domain_key, DomainPolicy(domain_key))
    valid: list[EvaluatedCandidate] = []
    hard_rejected: list[str] = []
    dimensions: list[str] = []

    for c in candidates:
        hard_ok, cfit, creasons, ctrade, cfields = _constraint_fit(request, c)
        pfit, preasons, ptrade, pfields = _preference_fit(request, c)
        material_fields = list(dict.fromkeys([*cfields, *pfields, *policy.material_fields]))
        dimensions.extend(material_fields)

        if not hard_ok:
            hard_rejected.append(c.candidate_id)
            continue

        econf, uncertainties, ereasons = _evidence_profile(c, material_fields)
        uncertainty_cost = _clamp(len(uncertainties) / max(1, len(material_fields)))
        regret = _weighted_regret(c, policy, econf, cfit, pfit, uncertainties)
        tradeoff_cost = _clamp((1 - cfit) * .55 + (1 - pfit) * .45)

        # Organic decision quality. Sponsorship is intentionally excluded.
        organic_score = _clamp(
            cfit * .32 +
            pfit * .24 +
            econf * .24 +
            (1 - regret) * .20
        )

        reasons = tuple(creasons + preasons + ereasons + [
            DecisionReason("inference", f"regret_risk={regret:.3f}"),
            DecisionReason("inference", f"organic_score={organic_score:.3f}"),
        ])
        tradeoffs = tuple(dict.fromkeys([*ctrade, *ptrade]))

        valid.append(
            EvaluatedCandidate(
                candidate_id=c.candidate_id,
                role="alternative",
                constraint_fit=cfit,
                preference_fit=pfit,
                evidence_confidence=econf,
                tradeoff_cost=tradeoff_cost,
                uncertainty_cost=uncertainty_cost,
                regret_risk=regret,
                reasons=reasons,
                tradeoffs=tradeoffs,
                uncertainties=tuple(uncertainties),
                organic_score=organic_score,
            )
        )

    if not valid:
        return DecisionResult(
            request_id=request.request_id,
            status="no_valid_candidate" if hard_rejected else "insufficient_data",
            decision_summary="No candidate satisfies the current decision contract.",
            recommended=(),
            material_dimensions=tuple(dict.fromkeys(dimensions)),
            comparison_notes=(),
            main_failure_modes=tuple(f"{x}:hard_constraint" for x in hard_rejected),
            lower_regret_candidate_id=None,
            upside_candidate_id=None,
            missing_information=(),
            clarifying_question=None,
            decision_boundary=DecisionBoundary(True),
            audit=DecisionAudit(POLICY_VERSION, False),
        )

    valid.sort(key=lambda x: (-x.organic_score, x.regret_risk, x.candidate_id))
    lower_regret = min(valid, key=lambda x: (x.regret_risk, -x.organic_score, x.candidate_id))
    upside = max(valid, key=lambda x: (x.preference_fit, x.organic_score, x.candidate_id))

    selected: list[EvaluatedCandidate] = []
    for idx, e in enumerate(valid[:limit]):
        role = "best_fit" if idx == 0 else "alternative"
        if idx != 0 and e.candidate_id == lower_regret.candidate_id:
            role = "lower_regret"
        elif idx != 0 and e.candidate_id == upside.candidate_id:
            role = "upside"
        selected.append(replace(e, role=role))

    unknown_fields = sorted({
        u.split(":", 1)[0]
        for e in selected for u in e.uncertainties
        if u.endswith(":unknown")
    })
    status = "ok"
    if selected and all(x.evidence_confidence <= 0 for x in selected):
        status = "insufficient_data"

    notes = tuple(
        f"{x.candidate_id}:fit={x.constraint_fit:.3f},pref={x.preference_fit:.3f},"
        f"evidence={x.evidence_confidence:.3f},regret={x.regret_risk:.3f}"
        for x in selected
    )

    return DecisionResult(
        request_id=request.request_id,
        status=status,
        decision_summary="Decision Quality Engine V1 evaluated fit, trade-offs, evidence, uncertainty and regret.",
        recommended=tuple(selected),
        material_dimensions=tuple(dict.fromkeys(dimensions)),
        comparison_notes=notes,
        main_failure_modes=tuple(
            f"{x.candidate_id}:{u}" for x in selected for u in x.uncertainties
        ),
        lower_regret_candidate_id=lower_regret.candidate_id,
        upside_candidate_id=upside.candidate_id,
        missing_information=tuple(unknown_fields),
        clarifying_question=(
            "Some material information is unknown; more evidence may change the recommendation."
            if unknown_fields else None
        ),
        decision_boundary=DecisionBoundary(True),
        audit=DecisionAudit(POLICY_VERSION, False),
    )
