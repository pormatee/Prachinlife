"""Decision Explanation Brain V1.

Explains the latest decision by re-evaluating only the prior Brain-supplied
candidate identities through the existing DQE path. No explanation text from
client conversation state is trusted as evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping

from .candidate_comparison_brain_v1 import evaluate_prior_candidate_comparison_v1


@dataclass(frozen=True)
class DecisionExplanationBrainResultV1:
    candidate_ids: tuple[str, ...]
    best_fit_candidate_id: str | None
    request_kind: str
    why_fit: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    uncertainty_fields: tuple[str, ...]
    regret_risks: tuple[str, ...]
    needs_location: bool = False


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {str(k): _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _short_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text[:300] if text else None
    if isinstance(value, Mapping):
        parts = []
        for key, item in value.items():
            text = _short_text(item)
            if text:
                parts.append(f"{key}: {text}")
            if len(parts) >= 4:
                break
        joined = " • ".join(parts).strip()
        return joined[:500] if joined else None
    if isinstance(value, (list, tuple)):
        parts = [_short_text(v) for v in value]
        joined = " • ".join(v for v in parts if v)
        return joined[:500] if joined else None
    text = str(value).strip()
    return text[:300] if text else None


def _sequence_from(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if value is None:
        return ()
    raw = value if isinstance(value, (list, tuple)) else (value,)
    out = []
    for item in raw:
        text = _short_text(item)
        if text and text not in out:
            out.append(text)
        if len(out) >= 5:
            break
    return tuple(out)


def _recursive_sequence(payload: Any, keys: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(payload, Mapping):
        for key in keys:
            if key in payload:
                found = _sequence_from(payload, key)
                if found:
                    return found
        for value in payload.values():
            found = _recursive_sequence(value, keys)
            if found:
                return found
    elif isinstance(payload, (list, tuple)):
        for value in payload:
            found = _recursive_sequence(value, keys)
            if found:
                return found
    return ()


def evaluate_decision_explanation_v1(
    *,
    request_id: str,
    effective_text: str,
    candidate_ids: tuple[str, ...],
    request_kind: str,
    criterion: str | None,
    repository: Any,
    context: Mapping[str, Any] | None,
    recommendation_limit: int = 3,
) -> DecisionExplanationBrainResultV1:
    if request_kind not in {"why", "tradeoffs", "risks", "uncertainty"}:
        raise ValueError("unsupported explanation request")
    if not candidate_ids:
        raise ValueError("explanation requires prior candidate identities")

    reevaluated = evaluate_prior_candidate_comparison_v1(
        request_id=request_id,
        effective_text=effective_text,
        candidate_ids=candidate_ids,
        criterion=criterion or "overall",
        repository=repository,
        context=context,
        recommendation_limit=recommendation_limit,
    )
    if reevaluated.needs_location:
        return DecisionExplanationBrainResultV1(
            candidate_ids=reevaluated.candidate_ids,
            best_fit_candidate_id=None,
            request_kind=request_kind,
            why_fit=(),
            tradeoffs=(),
            uncertainty_fields=("current_location",),
            regret_risks=(),
            needs_location=True,
        )

    decision = reevaluated.decision
    payload = _plain(decision)
    if not isinstance(payload, Mapping):
        payload = {}

    best_id = str(payload.get("best_fit_candidate_id") or "").strip() or None
    why_fit = _recursive_sequence(
        payload,
        ("why_fit", "reasons", "reason_codes", "decision_reasons", "fit_reasons"),
    )
    tradeoffs = _recursive_sequence(payload, ("tradeoffs", "trade_offs"))
    uncertainty = _recursive_sequence(
        payload,
        ("uncertainty_fields", "uncertainties", "uncertainty"),
    )
    regret = _recursive_sequence(
        payload,
        ("regret_risks", "regret_risk", "risks"),
    )

    return DecisionExplanationBrainResultV1(
        candidate_ids=reevaluated.candidate_ids,
        best_fit_candidate_id=best_id,
        request_kind=request_kind,
        why_fit=why_fit,
        tradeoffs=tradeoffs,
        uncertainty_fields=uncertainty,
        regret_risks=regret,
        needs_location=False,
    )
