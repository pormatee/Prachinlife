"""Generic Semantic Language Brain V1.

Provider-neutral natural-language interpretation boundary for PrachinLife.
The language model may structure user meaning but may not search places,
rank/select candidates, invent place facts, or own decision policy.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json
import os
import socket
from typing import Any, Mapping, Sequence
from urllib import error as urlerror
from urllib import request as urlrequest

SEMANTIC_LANGUAGE_BRAIN_VERSION = "GENERIC-SEMANTIC-LANGUAGE-BRAIN-V1"
SEMANTIC_MEANING_SCHEMA_VERSION = "GENERIC-SEMANTIC-MEANING-V1"
DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"
DEFAULT_OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/responses"
MAX_USER_TEXT = 4000
MAX_CONTEXT_TEXT = 200
MAX_CRITERIA = 8
MAX_CANDIDATES = 3

_CONVERSATION_ACTS = {
    "new_request",
    "refine",
    "change_context",
    "compare",
    "reference_fact",
    "explain_decision",
    "select_reference",
    "clarification_answer",
    "other",
}
_CATEGORIES = {"vegetarian", "eat", "shopping", "go", "service"}
_DECISION_OBJECTS = {"restaurant", "shop", "destination", "service_place", "fuel_station"}
_TEMPORAL = {"now", "today", "tomorrow", "tonight", "lunch", "dinner"}
_EXPLANATION_FOCUS = {"why", "tradeoffs", "risks", "uncertainty"}
_REFERENCE_KINDS = {"candidate_ordinal", "candidate_name", "previous_selection", "none"}
_POLARITIES = {"require", "prefer", "avoid", "remove"}
_IMPORTANCE = {"hard", "soft"}


SEMANTIC_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "conversation_act": {"type": "string", "enum": sorted(_CONVERSATION_ACTS)},
        "goal": {"type": "string", "maxLength": 240},
        "category": {"enum": [None, "vegetarian", "eat", "shopping", "go", "service"]},
        "decision_object": {"enum": [None, "restaurant", "shop", "destination", "service_place", "fuel_station"]},
        "location_text": {"type": ["string", "null"], "maxLength": 200},
        "province": {"type": ["string", "null"], "maxLength": 120},
        "near_me": {"type": ["boolean", "null"]},
        "temporal_context": {"enum": [None, "now", "today", "tomorrow", "tonight", "lunch", "dinner"]},
        "criteria": {
            "type": "array",
            "maxItems": MAX_CRITERIA,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "key": {"type": "string", "maxLength": 80},
                    "value": {"type": "string", "maxLength": 160},
                    "polarity": {"type": "string", "enum": sorted(_POLARITIES)},
                    "importance": {"type": "string", "enum": sorted(_IMPORTANCE)},
                },
                "required": ["key", "value", "polarity", "importance"],
            },
        },
        "reference": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "kind": {"type": "string", "enum": sorted(_REFERENCE_KINDS)},
                "ordinal": {"type": ["integer", "null"], "minimum": 1, "maximum": MAX_CANDIDATES},
                "name": {"type": ["string", "null"], "maxLength": 200},
            },
            "required": ["kind", "ordinal", "name"],
        },
        "fact_key": {"type": ["string", "null"], "maxLength": 80},
        "comparison_criterion": {"type": ["string", "null"], "maxLength": 80},
        "explanation_focus": {"enum": [None, "why", "tradeoffs", "risks", "uncertainty"]},
        "clarification": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "needed": {"type": "boolean"},
                "field": {"type": ["string", "null"], "maxLength": 80},
                "question": {"type": ["string", "null"], "maxLength": 300},
            },
            "required": ["needed", "field", "question"],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": [
        "conversation_act", "goal", "category", "decision_object",
        "location_text", "province", "near_me", "temporal_context",
        "criteria", "reference", "fact_key", "comparison_criterion",
        "explanation_focus", "clarification", "confidence",
    ],
}


_SYSTEM_INSTRUCTIONS = """You are PrachinLife Generic Semantic Language Brain V1.
Your only job is to interpret the meaning of the CURRENT user utterance relative to the supplied conversation state.
Return the requested structured semantic object. Do not answer the user.

Authority boundary:
- Never recommend, rank, score, choose, or reorder candidate places.
- Never invent or infer place facts such as hours, parking, price, distance, address, phone, or suitability.
- Never use sponsor/provider/commercial status as a decision criterion.
- Candidate names/order are references only; the downstream Master Super Brain/DQE owns all decisions.
- Preserve uncertainty. Ask for clarification only when the user's meaning itself cannot be resolved safely.

Semantic ontology:
- category: vegetarian/eat/shopping/go/service only when the user's requested domain clearly maps to one.
- decision_object: restaurant/shop/destination/service_place/fuel_station when clear.
- conversation_act describes what this turn DOES, not its wording.
- criteria keys should be short semantic concepts, not copied sentences. Prefer stable concepts such as budget_sensitive, parking, family, elderly, children, distance, route_fit, food_variety, accessibility, open_now, or another concise domain concept when necessary.
- reference ordinal is based only on the supplied candidate reference list.
- fact_key is a concise factual field requested about a referenced candidate, for example hours, parking, address, phone, website, price.
- comparison_criterion should be distance only for proximity comparison; use overall for a general 'which is better' comparison; otherwise use a concise semantic criterion.
- explanation_focus is why/tradeoffs/risks/uncertainty only when asking about the latest decision explanation.
- If the current utterance is a short answer to an earlier clarification, use clarification_answer.

Interpret Thai colloquial language, misspellings, English/Thai mixtures, ellipsis, pronouns, changes of mind, and follow-up references by MEANING rather than keyword matching.
"""


class SemanticLanguageProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticLanguageResultV1:
    status: str
    provider: str
    model: str | None
    meaning: Mapping[str, Any] | None
    source_text_sha256: str
    error_code: str | None = None

    @property
    def used_model(self) -> bool:
        return self.status == "model" and self.meaning is not None

    def public_payload(self) -> dict[str, Any]:
        return {
            "brain_version": SEMANTIC_LANGUAGE_BRAIN_VERSION,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "used_model": self.used_model,
            "source_text_sha256": self.source_text_sha256,
            "error_code": self.error_code,
        }


class SemanticLanguageProviderV1(ABC):
    name: str
    model: str

    @abstractmethod
    def interpret(self, semantic_input: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError


def _short_string(value: Any, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value[:limit] if value else None


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sanitize_candidate_references(raw: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(raw or (), 1):
        if idx > MAX_CANDIDATES or not isinstance(item, Mapping):
            break
        name = _short_string(item.get("name"), 200)
        if name:
            out.append({"ordinal": idx, "name": name})
    return out


def _sanitize_conversation_state(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    out: dict[str, Any] = {}
    for key, limit in (
        ("active_request_text", 500),
        ("category", 80),
        ("decision_object", 80),
        ("province", 120),
        ("last_user_text", 500),
        ("comparison_criterion", 80),
    ):
        value = _short_string(raw.get(key), limit)
        if value:
            out[key] = value
    if isinstance(raw.get("near_me"), bool):
        out["near_me"] = raw["near_me"]
    refs = raw.get("refinements")
    if isinstance(refs, (list, tuple)):
        out["refinements"] = [str(x)[:80] for x in refs[:8] if str(x).strip()]
    turn = raw.get("turn_index")
    if isinstance(turn, int) and not isinstance(turn, bool):
        out["turn_index"] = min(max(turn, 0), 10000)
    # Candidate IDs and exact coordinates are intentionally omitted.
    return out or None


def build_semantic_input_v1(
    user_text: str,
    context: Mapping[str, Any] | None = None,
    candidate_references: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("user_text required")
    user_text = user_text.strip()
    if len(user_text) > MAX_USER_TEXT:
        raise ValueError("user_text too long")
    context = context or {}
    if not isinstance(context, Mapping):
        raise ValueError("context must be an object")

    runtime_context: dict[str, Any] = {
        "has_current_location": bool(context.get("current_location")),
    }
    location_text = _short_string(context.get("location_text"), MAX_CONTEXT_TEXT)
    if location_text:
        runtime_context["location_text"] = location_text
    for key in ("transport_mode", "budget_sensitivity"):
        value = _short_string(context.get(key), 80)
        if value:
            runtime_context[key] = value
    group_size = context.get("group_size")
    if isinstance(group_size, int) and not isinstance(group_size, bool) and 1 <= group_size <= 100:
        runtime_context["group_size"] = group_size

    return {
        "semantic_contract": SEMANTIC_MEANING_SCHEMA_VERSION,
        "current_user_text": user_text,
        "conversation_state": _sanitize_conversation_state(context.get("conversation_state")),
        "candidate_references": _sanitize_candidate_references(candidate_references),
        "runtime_context": runtime_context,
    }


def _validate_meaning(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise SemanticLanguageProviderError("semantic_output_not_object")
    act = raw.get("conversation_act")
    if act not in _CONVERSATION_ACTS:
        raise SemanticLanguageProviderError("semantic_output_bad_act")
    category = raw.get("category")
    if category is not None and category not in _CATEGORIES:
        raise SemanticLanguageProviderError("semantic_output_bad_category")
    decision_object = raw.get("decision_object")
    if decision_object is not None and decision_object not in _DECISION_OBJECTS:
        raise SemanticLanguageProviderError("semantic_output_bad_object")
    temporal = raw.get("temporal_context")
    if temporal is not None and temporal not in _TEMPORAL:
        raise SemanticLanguageProviderError("semantic_output_bad_time")
    explanation = raw.get("explanation_focus")
    if explanation is not None and explanation not in _EXPLANATION_FOCUS:
        raise SemanticLanguageProviderError("semantic_output_bad_explanation")

    reference = raw.get("reference")
    if not isinstance(reference, Mapping) or reference.get("kind") not in _REFERENCE_KINDS:
        raise SemanticLanguageProviderError("semantic_output_bad_reference")
    ordinal = reference.get("ordinal")
    if ordinal is not None and (not isinstance(ordinal, int) or isinstance(ordinal, bool) or not 1 <= ordinal <= MAX_CANDIDATES):
        raise SemanticLanguageProviderError("semantic_output_bad_reference_ordinal")

    criteria = raw.get("criteria")
    if not isinstance(criteria, list) or len(criteria) > MAX_CRITERIA:
        raise SemanticLanguageProviderError("semantic_output_bad_criteria")
    normalized_criteria = []
    for item in criteria:
        if not isinstance(item, Mapping):
            raise SemanticLanguageProviderError("semantic_output_bad_criterion")
        key = _short_string(item.get("key"), 80)
        value = _short_string(item.get("value"), 160) or "true"
        polarity = item.get("polarity")
        importance = item.get("importance")
        if not key or polarity not in _POLARITIES or importance not in _IMPORTANCE:
            raise SemanticLanguageProviderError("semantic_output_bad_criterion")
        normalized_criteria.append({
            "key": key,
            "value": value,
            "polarity": polarity,
            "importance": importance,
        })

    clarification = raw.get("clarification")
    if not isinstance(clarification, Mapping) or not isinstance(clarification.get("needed"), bool):
        raise SemanticLanguageProviderError("semantic_output_bad_clarification")

    confidence = raw.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0.0 <= float(confidence) <= 1.0:
        raise SemanticLanguageProviderError("semantic_output_bad_confidence")

    return {
        "schema_version": SEMANTIC_MEANING_SCHEMA_VERSION,
        "conversation_act": act,
        "goal": _short_string(raw.get("goal"), 240) or "",
        "category": category,
        "decision_object": decision_object,
        "location_text": _short_string(raw.get("location_text"), 200),
        "province": _short_string(raw.get("province"), 120),
        "near_me": raw.get("near_me") if isinstance(raw.get("near_me"), bool) else None,
        "temporal_context": temporal,
        "criteria": normalized_criteria,
        "reference": {
            "kind": reference.get("kind"),
            "ordinal": ordinal,
            "name": _short_string(reference.get("name"), 200),
        },
        "fact_key": _short_string(raw.get("fact_key"), 80),
        "comparison_criterion": _short_string(raw.get("comparison_criterion"), 80),
        "explanation_focus": explanation,
        "clarification": {
            "needed": clarification.get("needed"),
            "field": _short_string(clarification.get("field"), 80),
            "question": _short_string(clarification.get("question"), 300),
        },
        "confidence": float(confidence),
    }


class OpenAIResponsesSemanticProviderV1(SemanticLanguageProviderV1):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_OPENAI_MODEL,
        endpoint: str = DEFAULT_OPENAI_ENDPOINT,
        timeout_seconds: float = 8.0,
    ) -> None:
        api_key = str(api_key or "").strip()
        if not api_key:
            raise SemanticLanguageProviderError("openai_api_key_missing")
        self._api_key = api_key
        self.model = str(model or DEFAULT_OPENAI_MODEL).strip()
        self._endpoint = str(endpoint or DEFAULT_OPENAI_ENDPOINT).strip()
        self._timeout_seconds = min(max(float(timeout_seconds), 1.0), 30.0)

    def _request_payload(self, semantic_input: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model,
            "instructions": _SYSTEM_INSTRUCTIONS,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(semantic_input, ensure_ascii=False, separators=(",", ":")),
                        }
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "prachinlife_semantic_language_v1",
                    "strict": True,
                    "schema": SEMANTIC_OUTPUT_SCHEMA,
                }
            },
            "reasoning": {"effort": "none"},
            "max_output_tokens": 1400,
            "store": False,
        }

    @staticmethod
    def _extract_output_text(data: Mapping[str, Any]) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        output = data.get("output")
        if not isinstance(output, list):
            raise SemanticLanguageProviderError("openai_output_missing")
        for item in output:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, Mapping):
                    continue
                if part.get("type") == "refusal":
                    raise SemanticLanguageProviderError("openai_refusal")
                text = part.get("text")
                if part.get("type") == "output_text" and isinstance(text, str) and text.strip():
                    return text.strip()
        raise SemanticLanguageProviderError("openai_output_text_missing")

    def interpret(self, semantic_input: Mapping[str, Any]) -> Mapping[str, Any]:
        body = json.dumps(self._request_payload(semantic_input), ensure_ascii=False).encode("utf-8")
        req = urlrequest.Request(
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "PrachinLife-Semantic-Language-Brain-V1",
            },
        )
        try:
            with urlrequest.urlopen(req, timeout=self._timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urlerror.HTTPError as exc:
            # Never expose provider body or credentials to caller/logs.
            raise SemanticLanguageProviderError(f"provider_http_{exc.code}") from None
        except (urlerror.URLError, socket.timeout, TimeoutError):
            raise SemanticLanguageProviderError("provider_unavailable") from None
        except json.JSONDecodeError:
            raise SemanticLanguageProviderError("provider_invalid_json") from None
        if not isinstance(data, Mapping):
            raise SemanticLanguageProviderError("provider_invalid_response")
        output_text = self._extract_output_text(data)
        try:
            raw = json.loads(output_text)
        except json.JSONDecodeError:
            raise SemanticLanguageProviderError("provider_semantic_json_invalid") from None
        return _validate_meaning(raw)



class DeepSeekResponsesSemanticProviderV1(SemanticLanguageProviderV1):
    """DeepSeek Responses API adapter for semantic-only structured output.

    DeepSeek's Responses API currently supports deepseek-v4-flash. Thinking is
    disabled because this boundary performs language interpretation only; all
    place ranking and decision reasoning remains downstream in MSB/DQE.
    """
    name = "deepseek"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_DEEPSEEK_MODEL,
        endpoint: str = DEFAULT_DEEPSEEK_ENDPOINT,
        timeout_seconds: float = 8.0,
    ) -> None:
        api_key = str(api_key or "").strip()
        if not api_key:
            raise SemanticLanguageProviderError("deepseek_api_key_missing")
        self.model = str(model or DEFAULT_DEEPSEEK_MODEL).strip()
        if self.model != DEFAULT_DEEPSEEK_MODEL:
            raise SemanticLanguageProviderError("deepseek_responses_model_unsupported")
        self._api_key = api_key
        self._endpoint = str(endpoint or DEFAULT_DEEPSEEK_ENDPOINT).strip()
        self._timeout_seconds = min(max(float(timeout_seconds), 1.0), 30.0)

    def _request_payload(self, semantic_input: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model,
            "instructions": _SYSTEM_INSTRUCTIONS,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(semantic_input, ensure_ascii=False, separators=(",", ":")),
                        }
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "prachinlife_semantic_language_v1",
                    "schema": SEMANTIC_OUTPUT_SCHEMA,
                }
            },
            "reasoning": {"effort": "none"},
            "max_output_tokens": 1400,
            "stream": False,
        }

    @staticmethod
    def _extract_output_text(data: Mapping[str, Any]) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        output = data.get("output")
        if not isinstance(output, list):
            raise SemanticLanguageProviderError("deepseek_output_missing")
        for item in output:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, Mapping):
                    continue
                text = part.get("text")
                if part.get("type") == "output_text" and isinstance(text, str) and text.strip():
                    return text.strip()
        raise SemanticLanguageProviderError("deepseek_output_text_missing")

    def interpret(self, semantic_input: Mapping[str, Any]) -> Mapping[str, Any]:
        body = json.dumps(self._request_payload(semantic_input), ensure_ascii=False).encode("utf-8")
        req = urlrequest.Request(
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "PrachinLife-Semantic-Language-Brain-V1",
            },
        )
        try:
            with urlrequest.urlopen(req, timeout=self._timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urlerror.HTTPError as exc:
            raise SemanticLanguageProviderError(f"provider_http_{exc.code}") from None
        except (urlerror.URLError, socket.timeout, TimeoutError):
            raise SemanticLanguageProviderError("provider_unavailable") from None
        except json.JSONDecodeError:
            raise SemanticLanguageProviderError("provider_invalid_json") from None
        if not isinstance(data, Mapping):
            raise SemanticLanguageProviderError("provider_invalid_response")
        output_text = self._extract_output_text(data)
        try:
            raw = json.loads(output_text)
        except json.JSONDecodeError:
            raise SemanticLanguageProviderError("provider_semantic_json_invalid") from None
        return _validate_meaning(raw)

def _provider_from_environment() -> SemanticLanguageProviderV1 | None:
    mode = str(os.environ.get("PRACHINLIFE_SEMANTIC_PROVIDER", "auto") or "auto").strip().casefold()
    openai_key = str(os.environ.get("OPENAI_API_KEY", "") or "").strip()
    deepseek_key = str(os.environ.get("DEEPSEEK_API_KEY", "") or "").strip()
    if mode in {"off", "disabled", "none"}:
        return None
    if mode not in {"auto", "openai", "deepseek"}:
        raise SemanticLanguageProviderError("semantic_provider_unsupported")

    if mode == "auto":
        if openai_key:
            mode = "openai"
        elif deepseek_key:
            mode = "deepseek"
        else:
            return None

    try:
        timeout = float(os.environ.get("PRACHINLIFE_SEMANTIC_TIMEOUT_SECONDS", "8"))
    except ValueError:
        timeout = 8.0

    if mode == "deepseek":
        model = str(os.environ.get("PRACHINLIFE_SEMANTIC_MODEL", DEFAULT_DEEPSEEK_MODEL) or DEFAULT_DEEPSEEK_MODEL).strip()
        endpoint = str(os.environ.get("PRACHINLIFE_SEMANTIC_ENDPOINT", DEFAULT_DEEPSEEK_ENDPOINT) or DEFAULT_DEEPSEEK_ENDPOINT).strip()
        return DeepSeekResponsesSemanticProviderV1(
            api_key=deepseek_key,
            model=model,
            endpoint=endpoint,
            timeout_seconds=timeout,
        )

    model = str(os.environ.get("PRACHINLIFE_SEMANTIC_MODEL", DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL).strip()
    endpoint = str(os.environ.get("PRACHINLIFE_SEMANTIC_ENDPOINT", DEFAULT_OPENAI_ENDPOINT) or DEFAULT_OPENAI_ENDPOINT).strip()
    return OpenAIResponsesSemanticProviderV1(
        api_key=openai_key,
        model=model,
        endpoint=endpoint,
        timeout_seconds=timeout,
    )


def _bind_reference_name_to_ordinal(
    meaning: Mapping[str, Any],
    semantic_input: Mapping[str, Any],
) -> dict[str, Any]:
    out = dict(meaning)
    reference = out.get("reference")
    if not isinstance(reference, Mapping) or reference.get("kind") != "candidate_name":
        return out
    wanted = _short_string(reference.get("name"), 200)
    if not wanted:
        return out
    wanted_key = wanted.casefold()
    candidates = semantic_input.get("candidate_references")
    if not isinstance(candidates, list):
        return out
    for item in candidates:
        if not isinstance(item, Mapping):
            continue
        name = _short_string(item.get("name"), 200)
        ordinal = item.get("ordinal")
        if name and name.casefold() == wanted_key and isinstance(ordinal, int):
            out["reference"] = {"kind": "candidate_ordinal", "ordinal": ordinal, "name": name}
            return out
    return out


def interpret_semantic_language_v1(
    user_text: str,
    context: Mapping[str, Any] | None = None,
    candidate_references: Sequence[Mapping[str, Any]] | None = None,
    *,
    provider: SemanticLanguageProviderV1 | None = None,
) -> SemanticLanguageResultV1:
    semantic_input = build_semantic_input_v1(user_text, context, candidate_references)
    text_hash = _source_hash(user_text.strip())

    try:
        selected = provider if provider is not None else _provider_from_environment()
    except SemanticLanguageProviderError as exc:
        return SemanticLanguageResultV1(
            status="fallback_error",
            provider="configuration",
            model=None,
            meaning=None,
            source_text_sha256=text_hash,
            error_code=str(exc),
        )
    if selected is None:
        return SemanticLanguageResultV1(
            status="fallback_disabled",
            provider="none",
            model=None,
            meaning=None,
            source_text_sha256=text_hash,
        )

    try:
        meaning = _validate_meaning(selected.interpret(semantic_input))
        meaning = _bind_reference_name_to_ordinal(meaning, semantic_input)
        return SemanticLanguageResultV1(
            status="model",
            provider=selected.name,
            model=getattr(selected, "model", None),
            meaning=meaning,
            source_text_sha256=text_hash,
        )
    except SemanticLanguageProviderError as exc:
        return SemanticLanguageResultV1(
            status="fallback_error",
            provider=getattr(selected, "name", "unknown"),
            model=getattr(selected, "model", None),
            meaning=None,
            source_text_sha256=text_hash,
            error_code=str(exc),
        )
    except Exception:
        return SemanticLanguageResultV1(
            status="fallback_error",
            provider=getattr(selected, "name", "unknown"),
            model=getattr(selected, "model", None),
            meaning=None,
            source_text_sha256=text_hash,
            error_code="provider_internal_error",
        )


def semantic_provider_health_v1() -> dict[str, Any]:
    mode = str(os.environ.get("PRACHINLIFE_SEMANTIC_PROVIDER", "auto") or "auto").strip().casefold()
    openai_present = bool(str(os.environ.get("OPENAI_API_KEY", "") or "").strip())
    deepseek_present = bool(str(os.environ.get("DEEPSEEK_API_KEY", "") or "").strip())

    selected = "none"
    if mode == "openai" and openai_present:
        selected = "openai"
    elif mode == "deepseek" and deepseek_present:
        selected = "deepseek"
    elif mode == "auto":
        if openai_present:
            selected = "openai"
        elif deepseek_present:
            selected = "deepseek"

    if selected == "deepseek":
        default_model = DEFAULT_DEEPSEEK_MODEL
    else:
        default_model = DEFAULT_OPENAI_MODEL
    model = str(os.environ.get("PRACHINLIFE_SEMANTIC_MODEL", default_model) or default_model).strip()
    enabled = selected != "none"

    return {
        "brain_version": SEMANTIC_LANGUAGE_BRAIN_VERSION,
        "provider_mode": mode,
        "enabled": enabled,
        "provider": selected,
        "model": model if enabled else None,
        "api_key_present": (deepseek_present if selected == "deepseek" else openai_present if selected == "openai" else False),
        "provider_keys_present": {"openai": openai_present, "deepseek": deepseek_present},
        "exact_location_sent_to_language_model": False,
        "ranking_authority": False,
    }
