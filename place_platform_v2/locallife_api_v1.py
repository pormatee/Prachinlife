from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .decision_action_contract_v1 import attach_decision_actions_v1
from .web_ai_runtime_v1 import run_decision as _run_master_brain_decision
from .web_ai_runtime_v1 import health_payload as _brain_health_payload

API_NAME = "locallife-api"
API_VERSION = "v1"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_ALLOWED_ORIGINS = ("https://pormatee.github.io",)
MAX_BODY_BYTES = 64 * 1024

def _allowed_origins() -> set[str]:
    raw = os.getenv("LOCALLIFE_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return set(DEFAULT_ALLOWED_ORIGINS)
    return {item.strip() for item in raw.split(",") if item.strip()}

def _origin_ok(origin: str | None) -> bool:
    return True if not origin else origin in _allowed_origins()

def health_payload() -> dict[str, Any]:
    brain = _brain_health_payload()
    return {
        "ok": bool(brain.get("ok")),
        "service": API_NAME,
        "api_version": API_VERSION,
        "decision_authority": "master-super-brain",
        "brain_service": brain.get("service"),
        "publication_projection": brain.get("publication_projection"),
        "canonical_write": False,
        "human_final_decision": bool(brain.get("human_final_decision", True)),
        "repository_ready": bool(brain.get("repository_ready")),
    }

def decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("request_body_must_be_object")
    return _run_master_brain_decision(payload)

def decision_response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return attach_decision_actions_v1(decision_payload(payload))

class Handler(BaseHTTPRequestHandler):
    server_version = "LocalLifeAPIV1"
    def _cors(self):
        origin=self.headers.get("Origin")
        if origin and _origin_ok(origin):
            self.send_header("Access-Control-Allow-Origin",origin); self.send_header("Vary","Origin")
        self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
    def _json(self,status,payload):
        body=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self._cors(); self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self):
        if not _origin_ok(self.headers.get("Origin")):
            self._json(HTTPStatus.FORBIDDEN,{"ok":False,"error":"origin_not_allowed"}); return
        self.send_response(HTTPStatus.NO_CONTENT); self._cors(); self.end_headers()
    def do_GET(self):
        path=urlparse(self.path).path
        if path in {"/healthz","/v1/health"}:
            try:
                p=health_payload(); self._json(HTTPStatus.OK if p["ok"] else HTTPStatus.SERVICE_UNAVAILABLE,p)
            except Exception:
                self._json(HTTPStatus.SERVICE_UNAVAILABLE,{"ok":False,"service":API_NAME,"api_version":API_VERSION,"error":"runtime_not_ready"})
            return
        self._json(HTTPStatus.NOT_FOUND,{"ok":False,"error":"not_found"})
    def do_POST(self):
        if not _origin_ok(self.headers.get("Origin")):
            self._json(HTTPStatus.FORBIDDEN,{"ok":False,"error":"origin_not_allowed"}); return
        if urlparse(self.path).path != "/v1/decision":
            self._json(HTTPStatus.NOT_FOUND,{"ok":False,"error":"not_found"}); return
        try: n=int(self.headers.get("Content-Length","0"))
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST,{"ok":False,"error":"bad_content_length"}); return
        if n<=0 or n>MAX_BODY_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE,{"ok":False,"error":"body_size_invalid"}); return
        try:
            payload=json.loads(self.rfile.read(n).decode("utf-8")); result=decision_response_payload(payload); self._json(HTTPStatus.OK,{"ok":True,"api_version":API_VERSION,"result":result})
        except (UnicodeDecodeError,json.JSONDecodeError,ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST,{"ok":False,"error":str(exc)})
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR,{"ok":False,"error":"decision_runtime_error"})
    def log_message(self,fmt,*args):
        super().log_message(fmt,*args)

def serve():
    host=os.getenv("LOCALLIFE_HOST",DEFAULT_HOST); port=int(os.getenv("PORT",os.getenv("LOCALLIFE_PORT",str(DEFAULT_PORT))))
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__ == "__main__": serve()
