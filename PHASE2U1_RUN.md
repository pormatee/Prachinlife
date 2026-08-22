# PrachinLife Phase 2U.1 — Admin Draft Persistence

Use the internal Admin server instead of `python -m http.server` when testing Admin persistence:

```bash
python scripts/admin_internal_server.py --port 8765
```

Then open:

- `http://127.0.0.1:8765/admin-view.html`
- Edit a place, build the Evidence Draft, then press **บันทึกเพื่อรอตรวจสอบ**.

Runtime drafts are stored in `data/v2/admin_evidence_drafts.sqlite3` and are intentionally separate from `data/v2/place_platform_v2.sqlite3`.
Canonical writes and publication are disabled in Phase 2U.1.
