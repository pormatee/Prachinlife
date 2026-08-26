(() => {
  "use strict";

  const SCHEMA = "prachinlife-contribution-v1";
  const ALLOWED_FIELDS = Object.freeze([
    "address_text",
    "district",
    "subdistrict",
    "area",
    "opening_hours",
    "phone",
    "website",
    "description",
    "real_image"
  ]);

  const text = value => String(value ?? "").trim();
  const esc = value => text(value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  function validHttpUrl(value) {
    try {
      const u = new URL(text(value));
      return u.protocol === "http:" || u.protocol === "https:";
    } catch (_) {
      return false;
    }
  }

  function normalizeChange(fieldName, value) {
    if (!ALLOWED_FIELDS.includes(fieldName)) {
      throw new Error("field not allowed");
    }
    const v = text(value);
    if (!v) return null;
    if (["website", "real_image"].includes(fieldName) && !validHttpUrl(v)) {
      throw new Error(`${fieldName} ต้องเป็น URL http(s)`);
    }
    return { field_name: fieldName, value: v };
  }

  function buildEnvelope(input) {
    const placeId = text(input?.place_id);
    const sourceName = text(input?.source_name);
    const sourceUrl = text(input?.source_url);
    if (!placeId) throw new Error("place_id is required");
    if (!sourceName) throw new Error("source_name is required");
    if (!validHttpUrl(sourceUrl)) throw new Error("source_url must be http(s)");

    const changes = [];
    for (const [fieldName, raw] of Object.entries(input?.fields || {})) {
      const item = normalizeChange(fieldName, raw);
      if (item) changes.push(item);
    }
    if (!changes.length) throw new Error("กรุณาเสนอแก้ไขอย่างน้อย 1 รายการ");

    return {
      schema_version: SCHEMA,
      mode: "evidence_draft_only",
      operation: "update_place_candidate",
      place_id: placeId,
      source: {
        source_name: sourceName,
        source_url: sourceUrl
      },
      note: text(input?.note) || "Public Suggest Edit contribution",
      changes,
      contribution_metadata: {
        origin: "public_suggest_edit",
        handoff: "manual_admin_import",
        canonical_write: false,
        publication: false,
        trust_tier: "untrusted_community_report",
        adoption_eligible: false,
        admin_approval_eligible: false,
        requires_independent_verification: true,
        created_at: new Date().toISOString()
      }
    };
  }

  function downloadEnvelope(envelope) {
    const blob = new Blob(
      [JSON.stringify(envelope, null, 2)],
      { type: "application/json;charset=utf-8" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `prachinlife-suggest-edit-${envelope.place_id}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function ensureStyles() {
    if (document.getElementById("prachinlifeContributionStyles")) return;
    const style = document.createElement("style");
    style.id = "prachinlifeContributionStyles";
    style.textContent = `
      .place-contribution-button{margin-top:8px;border:1px solid #d8e5dc;background:#fff;color:#17633b;border-radius:999px;padding:8px 12px;font:inherit;font-weight:700;cursor:pointer}
      .place-contribution-button:hover{background:#f3faf5}
      .place-contribution-dialog{border:0;border-radius:18px;padding:0;max-width:min(560px,calc(100vw - 24px));width:100%;box-shadow:0 22px 70px rgba(0,0,0,.24)}
      .place-contribution-dialog::backdrop{background:rgba(0,0,0,.46)}
      .place-contribution-form{padding:20px;display:grid;gap:12px}
      .place-contribution-form h3{margin:0}.place-contribution-help{margin:0;color:#66746b;font-size:.92rem}
      .place-contribution-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
      .place-contribution-grid label,.place-contribution-source label{display:grid;gap:5px;font-size:.9rem;font-weight:700}
      .place-contribution-form input,.place-contribution-form textarea{width:100%;box-sizing:border-box;border:1px solid #d8dfda;border-radius:10px;padding:10px;font:inherit}
      .place-contribution-form textarea{min-height:84px;resize:vertical}
      .place-contribution-source{display:grid;gap:10px;padding-top:6px;border-top:1px solid #edf1ee}
      .place-contribution-actions{display:flex;gap:8px;justify-content:flex-end}
      .place-contribution-actions button{border:0;border-radius:999px;padding:10px 14px;font:inherit;font-weight:700;cursor:pointer}
      .place-contribution-submit{background:#17633b;color:#fff}.place-contribution-cancel{background:#eef3ef;color:#294034}
      .place-contribution-status{min-height:20px;color:#17633b;font-size:.9rem}
      @media(max-width:560px){.place-contribution-grid{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }

  function fieldInputs() {
    return `
      <div class="place-contribution-grid">
        <label>ที่อยู่<input name="address_text"></label>
        <label>อำเภอ<input name="district"></label>
        <label>ตำบล<input name="subdistrict"></label>
        <label>พื้นที่ / จุดสังเกต<input name="area"></label>
        <label>เวลาเปิด<input name="opening_hours" placeholder="เช่น 08:00-17:00"></label>
        <label>โทรศัพท์<input name="phone"></label>
        <label>เว็บไซต์<input name="website" type="url" placeholder="https://..."></label>
        <label>URL รูปจริง<input name="real_image" type="url" placeholder="https://..."></label>
      </div>
      <label>รายละเอียด<textarea name="description"></textarea></label>
    `;
  }

  function openDialog(placeId, placeName) {
    ensureStyles();
    const old = document.getElementById("placeContributionDialog");
    if (old) old.remove();

    const dialog = document.createElement("dialog");
    dialog.id = "placeContributionDialog";
    dialog.className = "place-contribution-dialog";
    dialog.innerHTML = `
      <form method="dialog" class="place-contribution-form">
        <h3>แจ้งข้อมูล / เสนอข้อมูล</h3>
        <p class="place-contribution-help">
          ${esc(placeName || "สถานที่")} — ข้อมูลจะยังไม่เปลี่ยนบน PrachinLife
          จนกว่าจะผ่านการตรวจสอบหลักฐาน
        </p>
        ${fieldInputs()}
        <div class="place-contribution-source">
          <label>ชื่อแหล่งข้อมูล *<input name="source_name" required placeholder="เว็บไซต์ร้าน / Facebook ทางการ / หน่วยงาน"></label>
          <label>URL หลักฐาน *<input name="source_url" type="url" required placeholder="https://..."></label>
          <label>หมายเหตุ<textarea name="note" placeholder="ข้อมูลเพิ่มเติมสำหรับผู้ตรวจ"></textarea></label>
        </div>
        <div class="place-contribution-status" aria-live="polite"></div>
        <div class="place-contribution-actions">
          <button class="place-contribution-cancel" value="cancel">ยกเลิก</button>
          <button class="place-contribution-submit" value="default">สร้างไฟล์ข้อเสนอ</button>
        </div>
      </form>
    `;
    document.body.appendChild(dialog);

    const form = dialog.querySelector("form");
    const status = dialog.querySelector(".place-contribution-status");
    form.addEventListener("submit", event => {
      const submitter = event.submitter;
      if (submitter?.value === "cancel") return;
      event.preventDefault();
      try {
        const fd = new FormData(form);
        const fields = {};
        for (const name of ALLOWED_FIELDS) fields[name] = fd.get(name);
        const envelope = buildEnvelope({
          place_id: placeId,
          source_name: fd.get("source_name"),
          source_url: fd.get("source_url"),
          note: fd.get("note"),
          fields
        });
        downloadEnvelope(envelope);
        status.textContent = "สร้างไฟล์ข้อเสนอแล้ว ข้อมูลยังไม่ถูกเผยแพร่จนกว่าจะผ่านการตรวจสอบ";
      } catch (error) {
        status.textContent = error.message || "ไม่สามารถสร้างข้อเสนอได้";
      }
    });
    dialog.addEventListener("close", () => dialog.remove(), { once: true });
    dialog.showModal();
  }

  function cardPlaceName(card) {
    return text(
      card.querySelector(".promotion-title")?.textContent ||
      card.querySelector("h3")?.textContent
    );
  }

  function attachButton(card) {
    if (!(card instanceof HTMLElement)) return;
    const placeId = text(card.dataset.v2PlaceId || card.dataset.placeId);
    if (!placeId || card.querySelector(".place-contribution-button")) return;
    const body = card.querySelector(".promotion-body") || card;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "place-contribution-button";
    button.textContent =
      card.querySelector(".pending-human-notice")
        ? "ช่วยยืนยันข้อมูล"
        : "แจ้งข้อมูล / เสนอข้อมูล";
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      openDialog(placeId, cardPlaceName(card));
    });
    body.appendChild(button);
  }

  function scan(root = document) {
    root.querySelectorAll?.("[data-place-id]").forEach(attachButton);
  }

  function start() {
    ensureStyles();
    scan();
    const observer = new MutationObserver(records => {
      for (const record of records) {
        for (const node of record.addedNodes) {
          if (!(node instanceof HTMLElement)) continue;
          if (node.matches?.("[data-place-id]")) attachButton(node);
          scan(node);
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  window.PrachinLife = window.PrachinLife || {};
  window.PrachinLife.core = window.PrachinLife.core || {};
  window.PrachinLife.core.placeContribution = Object.freeze({
    schemaVersion: SCHEMA,
    allowedFields: ALLOWED_FIELDS,
    buildEnvelope,
    validHttpUrl
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
