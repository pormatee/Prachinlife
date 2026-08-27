from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

from .master_super_brain_v1 import DecisionResult


@dataclass(frozen=True)
class NormalizedIntent:
    goal: str
    decision_type: str
    category: str | None = None


class ConversationProvider(ABC):
    """Provider boundary only. Providers may interpret/present, not own decision policy."""

    name: str

    @abstractmethod
    def interpret(self, user_text: str, context: Mapping[str, Any] | None = None) -> NormalizedIntent:
        raise NotImplementedError

    @abstractmethod
    def present(self, decision_result: DecisionResult, context: Mapping[str, Any] | None = None) -> str:
        raise NotImplementedError


class ProviderUnavailable(RuntimeError):
    pass


class OpenAIProvider(ConversationProvider):
    name = "openai"

    def interpret(self, user_text: str, context: Mapping[str, Any] | None = None) -> NormalizedIntent:
        raise ProviderUnavailable("API integration intentionally not enabled in MSB-V1 skeleton")

    def present(self, decision_result: DecisionResult, context: Mapping[str, Any] | None = None) -> str:
        raise ProviderUnavailable("API integration intentionally not enabled in MSB-V1 skeleton")


class DeepSeekProvider(ConversationProvider):
    name = "deepseek"

    def interpret(self, user_text: str, context: Mapping[str, Any] | None = None) -> NormalizedIntent:
        raise ProviderUnavailable("API integration intentionally not enabled in MSB-V1 skeleton")

    def present(self, decision_result: DecisionResult, context: Mapping[str, Any] | None = None) -> str:
        raise ProviderUnavailable("API integration intentionally not enabled in MSB-V1 skeleton")
