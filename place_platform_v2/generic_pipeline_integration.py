from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from place_platform_v2.province_category_pipeline import (
    PlaceDecision,
    ProvinceCategoryPipeline,
    PublicState,
    Scope,
)


@dataclass(frozen=True)
class PipelineStageStatus:
    discovery_ready: bool
    identity_ready: bool
    evidence_ready: bool
    verification_ready: bool
    human_confirmation_required: bool
    human_confirmation_complete: bool
    admin_approved: bool
    canonical_ready: bool
    coordinate_ready: bool


@dataclass(frozen=True)
class PipelineIntegrationResult:
    scope: Scope
    stages: PipelineStageStatus
    decision: PlaceDecision
    publication_allowed: bool
    automatic_canonical: bool = False
    automatic_approval: bool = False
    automatic_publication: bool = False
    trust_policy_lowered: bool = False


class GenericPipelineIntegration:
    """Composition layer between stages 1-8 and the generic public-state engine."""

    def __init__(self) -> None:
        self._state_engine = ProvinceCategoryPipeline()

    def evaluate(
        self,
        *,
        province: str,
        category: str,
        stages: PipelineStageStatus,
        record: Mapping[str, Any],
    ) -> PipelineIntegrationResult:
        scope = Scope(province=province, category=category)

        chain_ready = all(
            (
                stages.discovery_ready,
                stages.identity_ready,
                stages.evidence_ready,
                stages.verification_ready,
                stages.admin_approved,
                stages.canonical_ready,
            )
        )

        human_gate_complete = (
            not stages.human_confirmation_required
            or stages.human_confirmation_complete
        )

        verified_public_ready = (
            chain_ready
            and human_gate_complete
            and stages.coordinate_ready
        )

        pending_human_eligible = (
            stages.discovery_ready
            and stages.identity_ready
            and stages.evidence_ready
            and stages.human_confirmation_required
            and not stages.human_confirmation_complete
        )

        state_record = dict(record)
        state_record.update(
            {
                "ready_for_publication": verified_public_ready,
                "verified": stages.verification_ready,
                "human_confirmation_required": stages.human_confirmation_required,
                "human_confirmation_complete": stages.human_confirmation_complete,
                "public_limited_eligible": pending_human_eligible,
            }
        )

        if not stages.coordinate_ready:
            state_record["latitude"] = None
            state_record["longitude"] = None

        decision = self._state_engine.classify(scope, state_record)

        publication_allowed = (
            decision.state is PublicState.VERIFIED_PUBLIC
            and chain_ready
            and human_gate_complete
            and stages.coordinate_ready
        )

        return PipelineIntegrationResult(
            scope=scope,
            stages=stages,
            decision=decision,
            publication_allowed=publication_allowed,
        )
