from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from place_platform_v2.controlled_publication_bundle_adapter_v1 import BUNDLE_FILES, build_projection_database
from place_platform_v2.production_published_place_repository_adapter_v1 import ProductionPublishedPlaceRepositoryAdapterV1
from place_platform_v2.end_to_end_real_decision_flow_v1 import run_end_to_end_real_decision_flow_v1

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORIGIN = "https://pormatee.github.io"
MAX_BODY_BYTES = 16 * 1024
_RUNTIME_LOCK = threading.Lock()
_RUNTIME_REPO = None
_RUNTIME_TMP = None

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
    global _RUNTIME_REPO, _RUNTIME_TMP
    with _RUNTIME_LOCK:
        if _RUNTIME_REPO is not None:
            return _RUNTIME_REPO

        tmp = tempfile.TemporaryDirectory(prefix="prachinlife-web-ai-runtime-")
        tr = Path(tmp.name)
        for rel in BUNDLE_FILES:
            src = ROOT / rel
            if not src.exists():
                tmp.cleanup()
                raise FileNotFoundError(f"publication bundle file missing: {rel}")
            dst = tr / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        projection = tr / "data/v2/decision_published_places_v1.sqlite3"
        projection.parent.mkdir(parents=True, exist_ok=True)
        build_projection_database(tr, projection)

        _RUNTIME_REPO = ProductionPublishedPlaceRepositoryAdapterV1(
            ROOT,
            projection_path=projection,
        )
        _RUNTIME_TMP = tmp
        return _RUNTIME_REPO

def health_payload() -> dict[str, Any]:
    repo = _build_runtime_repository()
    return {
        "ok": True,
        "service": "prachinlife-web-ai-runtime-v1",
        "brain": "decision-behavior-v1",
        "publication_projection": "ephemeral-read-model",
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

    result = run_end_to_end_real_decision_flow_v1(
        request_id=request_id,
        user_text=text.strip(),
        repository=_build_runtime_repository(),
        context=context,
        radius_km=radius_km,
        candidate_limit=candidate_limit,
        recommendation_limit=recommendation_limit,
    )
    return _conv(result)

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
