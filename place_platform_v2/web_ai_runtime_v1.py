from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from place_platform_v2.production_published_place_repository_adapter_v1 import ProductionPublishedPlaceRepositoryAdapterV1
from place_platform_v2.end_to_end_real_decision_flow_v1 import run_end_to_end_real_decision_flow_v1
from place_platform_v2.candidate_comparison_brain_v1 import evaluate_prior_candidate_comparison_v1
from place_platform_v2.semantic_conversation_understanding_v1 import (
    build_reference_fact_answer_v1,
    finalize_semantic_state_v1,
    resolve_semantic_turn_v1,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORIGIN = "https://pormatee.github.io"
MAX_BODY_BYTES = 16 * 1024
_RUNTIME_LOCK = threading.Lock()
_RUNTIME_REPO = None

def _conv(v: Any) -> Any:
    if is_dataclass(v):
        return {k: _conv(x) for k, x in asdict(v).items()}
    if isinstance(v, dict):
        return {str(k): _conv(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_conv(x) for x in v]
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return repr(v)

def _allowed_origins() -> set[str]:
    raw = os.environ.get("PRACHINLIFE_ALLOWED_ORIGINS", DEFAULT_ORIGIN)
    return {x.strip().rstrip("/") for x in raw.split(",") if x.strip()}

def _origin_ok(origin: str | None) -> bool:
    if not origin:
        return True  # CLI/health/server-to-server
    return origin.rstrip("/") in _allowed_origins()

def _build_runtime_repository():
    global _RUNTIME_REPO
    with _RUNTIME_LOCK:
        if _RUNTIME_REPO is not None:
            return _RUNTIME_REPO

        projection = ROOT / "data/v2/decision_published_places_v1.sqlite3"
        if not projection.exists():
            raise FileNotFoundError(
                f"authoritative persisted projection is not available: {projection}"
            )

        _RUNTIME_REPO = ProductionPublishedPlaceRepositoryAdapterV1(
            ROOT,
            projection_path=projection,
        )
        return _RUNTIME_REPO


def _candidate_summaries(repository: Any, candidate_ids) -> list[dict[str, str]]:
    getter = getattr(repository, "get_published", None)
    if not callable(getter):
        return []
    out = []
    for candidate_id in candidate_ids:
        candidate_id = str(candidate_id or "").strip()
        if not candidate_id:
            continue
        place = getter(candidate_id)
        if place is None:
            continue
        name = str(getattr(place, "name", "") or "").strip()
        out.append({"candidate_id": candidate_id, "name": name or candidate_id})
    return out


def _comparison_answer(criterion: str, decision: Any, summaries: list[dict[str, str]]) -> str:
    if decision is None:
        return ""
    best_id = str(getattr(decision, "best_fit_candidate_id", "") or "").strip()
    names = {x["candidate_id"]: x["name"] for x in summaries}
    best_name = names.get(best_id, best_id)
    if not best_id:
        return "ข้อมูลที่ยืนยันตอนนี้ยังไม่พอให้ระบบตัดสินว่าแต่ละตัวเลือกไหนเหมาะกว่าครับ"
    if criterion == "distance":
        return f"เมื่อเทียบตัวเลือกเดิมโดยเน้นความใกล้จากตำแหน่งปัจจุบัน ระบบตัดสินใจให้ {best_name} เหมาะสุดครับ"
    return f"จากเงื่อนไขที่คุยกันตอนนี้ ระบบตัดสินใจให้ {best_name} เหมาะสุดครับ"


def health_payload() -> dict[str, Any]:
    repo = _build_runtime_repository()
    return {
        "ok": True,
        "service": "prachinlife-web-ai-runtime-v1",
        "brain": "decision-behavior-v1",
        "publication_projection": "authoritative-persisted-read-model",
        "canonical_write": False,
        "human_final_decision": True,
        "repository_ready": repo is not None,
    }

def run_decision(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text is required")
    if len(text) > 4000:
        raise ValueError("text too long")

    request_id = payload.get("request_id") or "web-runtime"
    if not isinstance(request_id, str):
        request_id = str(request_id)

    context = payload.get("context")
    if context is None:
        context = {}
    if not isinstance(context, dict):
        raise ValueError("context must be an object")

    radius_km = payload.get("radius_km", 20.0)
    candidate_limit = payload.get("candidate_limit", 50)
    recommendation_limit = payload.get("recommendation_limit", 3)

    try:
        radius_km = float(radius_km)
        candidate_limit = int(candidate_limit)
        recommendation_limit = int(recommendation_limit)
    except Exception as e:
        raise ValueError("invalid numeric option") from e

    radius_km = min(max(radius_km, 0.1), 100.0)
    candidate_limit = min(max(candidate_limit, 1), 100)
    recommendation_limit = min(max(recommendation_limit, 1), 10)

    semantic_turn = resolve_semantic_turn_v1(text.strip(), context)
    repository = _build_runtime_repository()


    if semantic_turn.mode == "comparison_unresolved":
        state = semantic_turn.state
        return {
            "request_id": request_id,
            "status": "needs_user_input",
            "understanding": {
                "category": state.category,
                "decision_object": state.decision_object,
                "province": state.province,
                "near_me": state.near_me,
                "unresolved_context": ["comparison_candidates"],
            },
            "published_candidate_ids": list(state.candidate_ids),
            "compatible_candidate_ids": list(state.candidate_ids),
            "decision": None,
            "explanation": {
                "best_fit_candidate_id": None,
                "best_fit_name": None,
                "why_fit": [],
                "alternatives": [],
                "uncertainty_fields": ["comparison_candidates"],
                "tradeoffs": [],
                "regret_risks": [],
                "human_final_decision": True,
            },
            "needs_user_input": True,
            "highest_value_question": "ตอนนี้มีตัวเลือกที่จำไว้ไม่ถึงสองร้าน จึงยังเปรียบเทียบกันไม่ได้ครับ",
            "human_final_decision": True,
            "candidate_summaries": _candidate_summaries(repository, state.candidate_ids),
            "conversation_state": state.to_payload(),
        }

    if semantic_turn.mode == "comparison":
        state = semantic_turn.state
        comparison = evaluate_prior_candidate_comparison_v1(
            request_id=request_id,
            effective_text=semantic_turn.effective_text,
            candidate_ids=state.candidate_ids,
            criterion=state.comparison_criterion or "overall",
            repository=repository,
            context=semantic_turn.brain_context,
            recommendation_limit=recommendation_limit,
        )
        if comparison.needs_location:
            understanding = _conv(comparison.understanding)
            unresolved = list(understanding.get("unresolved_context") or [])
            if "current_location" not in unresolved:
                unresolved.append("current_location")
            understanding["unresolved_context"] = unresolved
            understanding["near_me"] = True
            return {
                "request_id": request_id,
                "status": "needs_user_input",
                "understanding": understanding,
                "published_candidate_ids": list(state.candidate_ids),
                "compatible_candidate_ids": list(state.candidate_ids),
                "decision": None,
                "explanation": {
                    "best_fit_candidate_id": None,
                    "best_fit_name": None,
                    "why_fit": [],
                    "alternatives": [],
                    "uncertainty_fields": ["current_location"],
                    "tradeoffs": [],
                    "regret_risks": [],
                    "human_final_decision": True,
                },
                "needs_user_input": True,
                "highest_value_question": "ขอใช้ตำแหน่งปัจจุบันเพื่อเปรียบเทียบว่าร้านไหนใกล้กว่าครับ",
                "human_final_decision": True,
                "candidate_summaries": _candidate_summaries(repository, state.candidate_ids),
                "conversation_state": state.to_payload(),
            }

        decision = comparison.decision
        summaries = _candidate_summaries(repository, comparison.candidate_ids)
        names = {x["candidate_id"]: x["name"] for x in summaries}
        best_id = str(getattr(decision, "best_fit_candidate_id", "") or "")
        alternatives = list(getattr(decision, "alternative_candidate_ids", ()) or ())
        result = {
            "request_id": request_id,
            "status": getattr(decision, "status", "insufficient_data"),
            "understanding": _conv(comparison.understanding),
            "published_candidate_ids": list(comparison.candidate_ids),
            "compatible_candidate_ids": list(comparison.candidate_ids),
            "decision": _conv(decision),
            "explanation": {
                "best_fit_candidate_id": best_id or None,
                "best_fit_name": names.get(best_id),
                "why_fit": [],
                "alternatives": alternatives,
                "uncertainty_fields": list(getattr(decision, "uncertainty_fields", ()) or ()),
                "tradeoffs": list(getattr(decision, "tradeoffs", ()) or ()),
                "regret_risks": list(getattr(decision, "regret_risks", ()) or ()),
                "human_final_decision": True,
            },
            "needs_user_input": False,
            "highest_value_question": None,
            "human_final_decision": True,
            "candidate_summaries": summaries,
            "comparison_answer": _comparison_answer(
                state.comparison_criterion or "overall",
                decision,
                summaries,
            ),
        }
        final_state = finalize_semantic_state_v1(state, result)
        result["conversation_state"] = final_state.to_payload()
        result["candidate_summaries"] = _candidate_summaries(repository, final_state.candidate_ids)
        return result

    if semantic_turn.mode == "reference_unresolved":
        state = semantic_turn.state
        return {
            "request_id": request_id,
            "status": "needs_user_input",
            "understanding": {
                "category": state.category,
                "decision_object": state.decision_object,
                "province": state.province,
                "near_me": state.near_me,
                "unresolved_context": ["candidate_reference"],
            },
            "published_candidate_ids": list(state.candidate_ids),
            "compatible_candidate_ids": list(state.candidate_ids),
            "decision": None,
            "explanation": {
                "best_fit_candidate_id": None,
                "best_fit_name": None,
                "why_fit": [],
                "alternatives": [],
                "uncertainty_fields": ["candidate_reference"],
                "tradeoffs": [],
                "regret_risks": [],
                "human_final_decision": True,
            },
            "needs_user_input": True,
            "highest_value_question": "หมายถึงร้านไหนครับ เช่น ร้านแรก ร้านที่สอง หรือร้านที่สาม?",
            "human_final_decision": True,
            "conversation_state": state.to_payload(),
        }

    if semantic_turn.mode == "reference_fact":
        state = semantic_turn.state
        answer = build_reference_fact_answer_v1(state, repository)
        return {
            "request_id": request_id,
            "status": "reference_fact",
            "understanding": {
                "category": state.category,
                "decision_object": state.decision_object,
                "province": state.province,
                "near_me": state.near_me,
                "unresolved_context": [],
            },
            "published_candidate_ids": list(state.candidate_ids),
            "compatible_candidate_ids": list(state.candidate_ids),
            "decision": None,
            "explanation": {
                "best_fit_candidate_id": None,
                "best_fit_name": None,
                "why_fit": [],
                "alternatives": [],
                "uncertainty_fields": [],
                "tradeoffs": [],
                "regret_risks": [],
                "human_final_decision": True,
            },
            "needs_user_input": False,
            "highest_value_question": None,
            "human_final_decision": True,
            "reference_answer": answer,
            "conversation_state": state.to_payload(),
        }

    result = run_end_to_end_real_decision_flow_v1(
        request_id=request_id,
        user_text=semantic_turn.effective_text,
        repository=repository,
        context=semantic_turn.brain_context,
        radius_km=radius_km,
        candidate_limit=candidate_limit,
        recommendation_limit=recommendation_limit,
    )
    converted = _conv(result)
    final_state = finalize_semantic_state_v1(semantic_turn.state, converted)
    converted["conversation_state"] = final_state.to_payload()
    converted["candidate_summaries"] = _candidate_summaries(repository, final_state.candidate_ids)
    return converted

class Handler(BaseHTTPRequestHandler):
    server_version = "PrachinLifeWebAIRuntimeV1"

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin and _origin_ok(origin):
            self.send_header("Access-Control-Allow-Origin", origin.rstrip("/"))
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")

    def _json(self, status: int, payload: dict[str, Any]):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        if not _origin_ok(self.headers.get("Origin")):
            self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "origin_not_allowed"})
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/healthz":
            try:
                self._json(HTTPStatus.OK, health_payload())
            except Exception:
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False, "error": "runtime_not_ready"})
            return
        self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if not _origin_ok(self.headers.get("Origin")):
            self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "origin_not_allowed"})
            return

        path = urlparse(self.path).path
        if path != "/v1/decision":
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "bad_content_length"})
            return
        if n <= 0 or n > MAX_BODY_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": "body_size_invalid"})
            return

        try:
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            result = run_decision(payload)
            self._json(HTTPStatus.OK, {"ok": True, "result": result})
        except ValueError as e:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(e)})
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "decision_runtime_error"})

    def log_message(self, fmt: str, *args: Any) -> None:
        # Avoid logging full query text/body; standard request line only.
        super().log_message(fmt, *args)

def serve() -> None:
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")
    _build_runtime_repository()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"PrachinLife Web AI Runtime V1 listening on {host}:{port}", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    serve()
