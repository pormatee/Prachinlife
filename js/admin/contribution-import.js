(() => {
  "use strict";

  const ALLOWED_FIELDS = new Set([
    "address_text","district","subdistrict","area","opening_hours",
    "phone","website","description","real_image"
  ]);

  const el = id => document.getElementById(id);
  const text = value => String(value ?? "").trim();

  function validHttpUrl(value) {
    try {
      const u = new URL(text(value));
      return u.protocol === "http:" || u.protocol === "https:";
    } catch (_) {
      return false;
    }
  }

  function validate(payload) {
    if (!payload || typeof payload !== "object") throw new Error("ไฟล์ต้องเป็น JSON object");
    if (payload.schema_version !== "prachinlife-contribution-v1") throw new Error("schema_version ไม่รองรับ");
    if (payload.mode !== "evidence_draft_only") throw new Error("mode ไม่ปลอดภัย");
    if (payload.operation !== "update_place_candidate") throw new Error("รองรับเฉพาะการเสนอแก้สถานที่เดิม");
    if (!text(payload.place_id)) throw new Error("ไม่มี place_id");
    if (!payload.source || !text(payload.source.source_name)) throw new Error("ไม่มี source_name");
    if (!validHttpUrl(payload.source.source_url)) throw new Error("source_url ไม่ถูกต้อง");
    if (!Array.isArray(payload.changes) || !payload.changes.length) throw new Error("ไม่มี changes");
    for (const change of payload.changes) {
      if (!change || !ALLOWED_FIELDS.has(text(change.field_name))) {
        throw new Error(`field ไม่อนุญาต: ${text(change?.field_name)}`);
      }
      if (!text(change.value)) throw new Error(`value ว่าง: ${change.field_name}`);
      if (["website","real_image"].includes(change.field_name) && !validHttpUrl(change.value)) {
        throw new Error(`${change.field_name} ต้องเป็น URL http(s)`);
      }
    }
    return payload;
  }

  async function readFile(file) {
    if (!file) throw new Error("กรุณาเลือกไฟล์");
    if (file.size > 256 * 1024) throw new Error("ไฟล์ใหญ่เกินไป");
    return JSON.parse(await file.text());
  }

  function render(payload) {
    el("contributionPreview").textContent = JSON.stringify(payload, null, 2);
    el("contributionImportBtn").disabled = false;
  }

  async function loadSelected() {
    try {
      const payload = validate(await readFile(el("contributionFile").files[0]));
      window.__prachinlifeContributionPayload = payload;
      render(payload);
      el("contributionStatus").textContent = "ตรวจรูปแบบแล้ว พร้อมนำเข้าคิวตรวจสอบ";
    } catch (error) {
      window.__prachinlifeContributionPayload = null;
      el("contributionImportBtn").disabled = true;
      el("contributionPreview").textContent = "";
      el("contributionStatus").textContent = error.message || "ไฟล์ไม่ถูกต้อง";
    }
  }

  async function importDraft() {
    const payload = validate(window.__prachinlifeContributionPayload);
    el("contributionImportBtn").disabled = true;
    try {
      const response = await fetch("/api/admin/evidence-drafts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      el("contributionStatus").textContent =
        `นำเข้าแล้ว Draft ${result.draft.draft_id} — สถานะ ${result.draft.review_status}`;
    } catch (error) {
      el("contributionStatus").textContent = error.message || "นำเข้าไม่สำเร็จ";
      el("contributionImportBtn").disabled = false;
    }
  }

  function start() {
    el("contributionFile").addEventListener("change", loadSelected);
    el("contributionImportBtn").addEventListener("click", importDraft);
  }

  window.PrachinLifeContributionImport = Object.freeze({ validate, validHttpUrl });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
