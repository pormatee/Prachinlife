from __future__ import annotations
import json, sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

POLICY = "phase11-official-web-enrichment-v1"
ALLOWED_FIELDS = {"address","area","district","subdistrict","opening_hours","phone","website","description","real_image"}
ALLOWED_HOSTS = {"finearts.go.th", "www.finearts.go.th"}

@dataclass(frozen=True)
class WebClaim:
    place_id: str
    field_name: str
    value: str
    source_name: str
    source_url: str
    source_record_id: str
    observed_at: str
    metadata: dict

def _text(v):
    return str(v or "").strip()

def _host(url):
    try: return (urlparse(url).hostname or "").casefold()
    except Exception: return ""

def _kind(field):
    if field in {"address","area","district","subdistrict"}: return "address"
    if field in {"phone","website"}: return "contact"
    if field == "opening_hours": return "opening_status"
    return "other"

def collect_official_web_claims(database_path, manifest_path):
    manifest=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("policy_version") != POLICY:
        raise ValueError("unexpected policy_version")
    con=sqlite3.connect(database_path); con.row_factory=sqlite3.Row
    claims=[]; accepted=0
    try:
        for obs in manifest.get("observations",[]):
            pid=_text(obs.get("place_id")); name=_text(obs.get("canonical_name")); province=_text(obs.get("province"))
            row=con.execute("SELECT canonical_name,province FROM places WHERE place_id=?",(pid,)).fetchone()
            if not row: raise ValueError(f"unknown place_id: {pid}")
            if _text(row["canonical_name"]) != name or _text(row["province"]) != province:
                raise ValueError(f"identity mismatch: {pid}")
            source_url=_text(obs.get("source_url"))
            if not source_url.startswith("https://") or _host(source_url) not in ALLOWED_HOSTS:
                raise ValueError(f"untrusted source URL: {source_url}")
            fields=obs.get("fields") or {}
            if not isinstance(fields,dict) or not fields: raise ValueError(f"empty fields: {pid}")
            accepted += 1
            for field,value in fields.items():
                if field not in ALLOWED_FIELDS: raise ValueError(f"unsupported field: {field}")
                value=_text(value)
                if not value: raise ValueError(f"empty value: {pid}/{field}")
                if field in {"website","real_image"} and not value.startswith("https://"):
                    raise ValueError(f"non-https public URL: {pid}/{field}")
                claims.append(WebClaim(pid,field,value,_text(obs.get("source_name")),source_url,_text(obs.get("source_record_id")),_text(obs.get("observed_at")),{
                    "policy_version": POLICY,
                    "provenance_origin": "official_web_manual_observation",
                    "source_host": _host(source_url),
                    "canonical_identity_checked": True,
                    "automatic_canonical_adoption": False,
                }))
    finally: con.close()
    return claims,{"observation_count":len(manifest.get("observations",[])),"accepted_observations":accepted,"claim_count":len(claims)}

def persist_official_web_claims(database_path, claims):
    con=sqlite3.connect(database_path); inserted=0
    try:
        places_before=con.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        for c in claims:
            evid=str(uuid5(NAMESPACE_URL,f"{POLICY}|{c.place_id}|{c.field_name}|{c.source_record_id}|{c.value}"))
            cur=con.execute("INSERT OR IGNORE INTO place_evidence (evidence_id,place_id,source_type,source_name,source_record_id,source_url,source_observed_at,kind,field_name,value_json,status,observed_at,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (evid,c.place_id,"official",c.source_name,c.source_record_id,c.source_url,c.observed_at,_kind(c.field_name),c.field_name,json.dumps(c.value,ensure_ascii=False),"supported",c.observed_at,json.dumps(c.metadata,ensure_ascii=False,sort_keys=True)))
            inserted += cur.rowcount
        if con.execute("SELECT COUNT(*) FROM places").fetchone()[0] != places_before:
            raise RuntimeError("canonical places changed")
        con.commit(); return inserted
    finally: con.close()
