#!/usr/bin/env python3
"""Blind probe for the deployed Generic Semantic Language Brain V1.

No prompt cases are embedded here. Pass a fresh question on the command line.
"""
from __future__ import annotations

import json
import os
import sys
from urllib import request as urlrequest

DEFAULT_BASE = "https://locallife-api.onrender.com"


def main() -> int:
    if len(sys.argv) < 2:
        print('USAGE=python tools/semantic_language_blind_probe_v1.py "<fresh user question>"')
        return 2
    text = " ".join(sys.argv[1:]).strip()
    base = os.environ.get("PRACHINLIFE_API_BASE", DEFAULT_BASE).rstrip("/")
    body = json.dumps({"text": text, "context": {}}, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        base + "/v1/semantic",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urlrequest.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        print("SEMANTIC_PROBE=INVALID_RESPONSE")
        return 1
    brain = result.get("language_brain") or {}
    meaning = result.get("meaning") or {}
    print("SEMANTIC_PROBE=PASS")
    print("MODEL_USED=" + str(brain.get("used_model")))
    print("PROVIDER=" + str(brain.get("provider")))
    print("MODEL=" + str(brain.get("model")))
    print("ACT=" + str(meaning.get("conversation_act")))
    print("CATEGORY=" + str(meaning.get("category")))
    print("OBJECT=" + str(meaning.get("decision_object")))
    print("CRITERIA=" + json.dumps(meaning.get("criteria") or [], ensure_ascii=False))
    print("REFERENCE=" + json.dumps(meaning.get("reference") or {}, ensure_ascii=False))
    print("COMPARE=" + str(meaning.get("comparison_criterion")))
    print("EXPLAIN=" + str(meaning.get("explanation_focus")))
    print("CONFIDENCE=" + str(meaning.get("confidence")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
