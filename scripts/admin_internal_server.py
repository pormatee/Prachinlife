#!/usr/bin/env python3
"""Local-only Admin Web server with Phase 2U.3.3.4 mobile image upload reliability hotfix."""
from __future__ import annotations
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, unquote, urlparse
ROOT = Path(__file__).resolve().parents[1]


def _sniff_image_type(data: bytes, declared: str = "", filename: str = "") -> str:
    declared = str(declared or "").split(";",1)[0].strip().lower()
    head = data[:16]
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if declared in {"image/jpeg", "image/png", "image/webp"}:
        return declared
    lower = str(filename or "").lower()
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    raise ValueError("unsupported image type; use JPEG, PNG, or WebP")
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
from place_platform_v2.admin_verified_workflow import preview_verified_update, commit_verified_update
from place_platform_v2.admin_media import AdminMediaStore, MAX_UPLOAD_BYTES

class AdminHandler(SimpleHTTPRequestHandler):
    server_version = "PrachinLifeAdmin/2U.3.3.4"
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    @property
    def service(self): return self.server.admin_draft_service
    @property
    def draft_database(self): return self.server.admin_draft_database
    @property
    def media_database(self): return self.server.admin_media_database
    @property
    def media_directory(self): return self.server.admin_media_directory
    def _json(self,status,payload):
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8'); self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    def _payload(self):
        length=int(self.headers.get('Content-Length','0'))
        if length<=0 or length>1_000_000: raise ValueError('invalid request size')
        return json.loads(self.rfile.read(length).decode('utf-8'))
    def _serve_admin_media(self, path):
        prefix = "/data/v2/admin_media/"
        if not path.startswith(prefix):
            return False
        storage_name = Path(path[len(prefix):]).name
        if not storage_name or storage_name != path[len(prefix):]:
            self._json(404,{"status":"error","error":"media not found"}); return True
        target = self.media_directory / storage_name
        if not target.is_file():
            self._json(404,{"status":"error","error":"media not found"}); return True
        suffix = target.suffix.lower()
        content_type = {".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".webp":"image/webp"}.get(suffix,"application/octet-stream")
        data = target.read_bytes()
        self.send_response(200); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(data); return True
    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path
        if self._serve_admin_media(path): return
        if path=="/api/admin/evidence-drafts":
            try:
                status=parse_qs(parsed.query).get('status',[AdminDraftStatus.PENDING_REVIEW])[0]
                with AdminDraftStore(self.draft_database) as store: items=store.list_review_groups(status=status)
                self._json(200,{"status":"ok","items":items,"count":len(items),"canonical_write":False,"publication":False})
            except Exception as exc: self._json(400,{"status":"error","error":str(exc)})
            return
        if path=="/api/admin/health": self._json(200,{"status":"ok","phase":"2U.3.3.2","hotfix":"2U.3.3.4","canonical_write":False,"publication":False,"media_upload":True,"vip_foundation":True}); return
        super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        try:
            if path=="/api/admin/media":
                length=int(self.headers.get("Content-Length","0"))
                if length<=0 or length>MAX_UPLOAD_BYTES: raise ValueError("invalid image size")
                declared_type=str(self.headers.get("Content-Type","")).split(";",1)[0].strip().lower()
                original_name=unquote(str(self.headers.get("X-Filename","upload")).strip() or "upload")
                data=self.rfile.read(length)
                content_type=_sniff_image_type(data,declared_type,original_name)
                with AdminMediaStore(self.media_database,self.media_directory) as store:
                    asset=store.save(data=data,original_name=original_name,content_type=content_type)
                self._json(201,{"status":"ok","media":{"media_id":asset.media_id,"url":asset.url,"content_type":asset.content_type,"size_bytes":asset.size_bytes,"sha256":asset.sha256,"original_name":asset.original_name},"canonical_write":False,"publication":False}); return
            if path=="/api/admin/verified-update/preview":
                body=self._body_json()
                result=preview_verified_update(repo_root=ROOT,database_path=self.server.admin_canonical_database,payload=body)
                self._json(200,result); return
            if path=="/api/admin/verified-update/commit":
                body=self._body_json()
                result=commit_verified_update(repo_root=ROOT,database_path=self.server.admin_canonical_database,payload=body.get("payload") or {},confirm=str(body.get("confirm") or ""))
                self._json(200,{"status":"ok","result":result}); return
            if path=="/api/admin/evidence-drafts":
                result=self.service.persist(self._payload())
                self._json(201,{"status":"ok","draft":{"draft_id":result.draft_id,"operation":result.operation,"review_status":result.status,"target_place_id":result.target_place_id,"candidate_place_id":result.candidate_place_id,"changes_count":result.changes_count,"created_at":result.created_at},"canonical_write":False,"publication":False}); return
            if path.startswith("/api/admin/evidence-drafts/") and path.endswith("/review"):
                draft_id=path.split('/')[4]; payload=self._payload(); decision=str(payload.get('decision','')).strip(); note=str(payload.get('note','')).strip()
                with AdminDraftStore(self.draft_database) as store: result=store.review(draft_id,decision,note)
                self._json(200,{"status":"ok","review":result,"canonical_write":False,"publication":False}); return
            self._json(404,{"status":"error","error":"not found"})
        except (ValueError,KeyError,json.JSONDecodeError) as exc: self._json(400,{"status":"error","error":str(exc)})
        except Exception as exc: self._json(500,{"status":"error","error":str(exc)})

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--canonical-db',default=str(ROOT/'data/v2/place_platform_v2.sqlite3')); parser.add_argument('--draft-db',default=str(ROOT/'data/v2/admin_evidence_drafts.sqlite3')); parser.add_argument('--media-db',default=str(ROOT/'data/v2/admin_media.sqlite3')); parser.add_argument('--media-dir',default=str(ROOT/'data/v2/admin_media')); args=parser.parse_args()
    if args.host not in {'127.0.0.1','localhost','::1'}: parser.error('Admin server must bind to loopback only')
    service=AdminDraftService(args.canonical_db,args.draft_db); server=ThreadingHTTPServer((args.host,args.port),AdminHandler); server.admin_draft_service=service; server.admin_draft_database=Path(args.draft_db); server.admin_media_database=Path(args.media_db); server.admin_media_directory=Path(args.media_dir)
    print(f'PrachinLife Admin 2U.3.3.4: http://{args.host}:{args.port}/admin-view.html'); print(f'Review queue: http://{args.host}:{args.port}/admin-review.html'); print(f'Draft queue: {args.draft_db}'); print(f'Media store: {args.media_dir}'); print('VIP/Sponsor foundation: READY (not public)'); print('Canonical writes: DISABLED'); print('Publication: DISABLED')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0
if __name__=='__main__': raise SystemExit(main())
