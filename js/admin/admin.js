(() => {
  "use strict";

  const EXPORT_URL = "data/v2/exports/prachinlife_places_v2.json";
  const CONTRACT_VERSION = "2U.3-v1";
  const DRAFT_API_URL = "/api/admin/evidence-drafts";
  const MEDIA_API_URL = "/api/admin/media";
  const LEGACY_HANDOFF_KEY = "prachinlife_admin_legacy_handoff_v1";
  const ALLOWED_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]", ""]);
  const ALLOWED_FIELDS = new Set([
    "canonical_name", "location", "address_text", "province", "district",
    "subdistrict", "area", "categories", "phone", "website", "opening_hours",
    "real_image", "description"
  ]);
  const DETAIL_FIELDS = ["district", "subdistrict", "area", "opening_hours", "phone", "website", "real_image", "description"];
  const DETAIL_LABELS = {
    district: "อำเภอ", subdistrict: "ตำบล", area: "พื้นที่", opening_hours: "เวลาเปิด",
    phone: "โทร", website: "เว็บไซต์", real_image: "รูปจริง", description: "รายละเอียด"
  };
  const PAGE_SIZE = 12;

  let allPlaces = [];
  let filteredPlaces = [];
  let selectedPlace = null;
  let currentDraft = null;
  let createMode = false;
  let legacySeedPlace = null;
  let visibleCount = PAGE_SIZE;
  let uploadedMedia = null;
  let imageUploadInFlight = null;

  const byId = id => document.getElementById(id);
  const text = value => String(value ?? "").trim();
  const isHttpUrl = value => /^https?:\/\//i.test(text(value));

  function internalRuntimeAllowed() {
    return location.protocol === "file:" || ALLOWED_HOSTS.has(location.hostname);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function setStatus(message, isError = false) {
    const node = byId("adminStatus");
    if (!node) return;
    node.textContent = message;
    node.style.color = isError ? "#9b2c2c" : "";
  }

  function renderLiveImagePreview(url = "", label = "รูปที่จะใช้ใน Preview") {
    const box = byId("adminImageUploadPreview");
    if (!box) return;
    const value = text(url);
    box.innerHTML = value
      ? `<img src="${escapeHtml(value)}" alt="${escapeHtml(label)}">`
      : "<span>ยังไม่ได้เลือกรูปใหม่</span>";
  }

  const MAX_MEDIA_BYTES = 8 * 1024 * 1024;
  const MOBILE_UPLOAD_TARGET_BYTES = Math.floor(7.5 * 1024 * 1024);
  const SUPPORTED_MEDIA_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

  function setImageUploadStatus(message, state = "") {
    const node = byId("adminImageUploadStatus");
    if (!node) return;
    node.textContent = message;
    node.classList.remove("is-uploading", "is-success", "is-error");
    if (state) node.classList.add(`is-${state}`);
  }

  function inferImageType(file) {
    const declared = text(file?.type).toLowerCase();
    if (SUPPORTED_MEDIA_TYPES.has(declared)) return declared;
    const name = text(file?.name).toLowerCase();
    if (/\.jpe?g$/.test(name)) return "image/jpeg";
    if (/\.png$/.test(name)) return "image/png";
    if (/\.webp$/.test(name)) return "image/webp";
    return declared;
  }

  async function canvasBlob(canvas, type, quality) {
    return await new Promise(resolve => canvas.toBlob(resolve, type, quality));
  }

  async function prepareMobileImage(file) {
    const inferredType = inferImageType(file);
    if (!SUPPORTED_MEDIA_TYPES.has(inferredType)) {
      throw new Error("รองรับเฉพาะ JPEG / PNG / WebP กรุณาเลือกรูปชนิดอื่น");
    }
    if (file.size <= MAX_MEDIA_BYTES && file.type === inferredType) {
      return { blob: file, contentType: inferredType, originalName: file.name, resized: false };
    }
    if (file.size <= MAX_MEDIA_BYTES) {
      return { blob: file, contentType: inferredType, originalName: file.name, resized: false };
    }

    setImageUploadStatus("รูปมีขนาดใหญ่ กำลังย่อรูปสำหรับอัปโหลดจากมือถือ...", "uploading");
    let bitmap;
    try {
      bitmap = await createImageBitmap(file);
    } catch {
      throw new Error("รูปมีขนาดเกิน 8 MB และเบราว์เซอร์ไม่สามารถย่อรูปนี้ได้ กรุณาเลือกรูปที่เล็กกว่า");
    }
    const maxDimension = 2200;
    const scale = Math.min(1, maxDimension / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    if (bitmap.close) bitmap.close();

    let blob = null;
    for (const quality of [0.88, 0.78, 0.68, 0.58, 0.48]) {
      blob = await canvasBlob(canvas, "image/jpeg", quality);
      if (blob && blob.size <= MOBILE_UPLOAD_TARGET_BYTES) break;
    }
    if (!blob || blob.size > MAX_MEDIA_BYTES) {
      throw new Error("ไม่สามารถย่อรูปให้ต่ำกว่า 8 MB ได้ กรุณาเลือกรูปที่เล็กกว่า");
    }
    const baseName = text(file.name).replace(/\.[^.]+$/, "") || "mobile-photo";
    return { blob, contentType: "image/jpeg", originalName: `${baseName}-mobile.jpg`, resized: true };
  }

  async function uploadMediaRequest(prepared, attempt = 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);
    try {
      // Phase 2U.3.3 compatibility: legacy uploader used `body: file`; prepared.blob is the validated/mobile-normalized binary.
      const response = await fetch(MEDIA_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": prepared.contentType,
          "X-Filename": encodeURIComponent(prepared.originalName)
        },
        cache: "no-store",
        body: prepared.blob,
        signal: controller.signal
      });
      let payload = null;
      try { payload = await response.json(); } catch { payload = {}; }
      if (!response.ok || payload?.status !== "ok") {
        const error = new Error(payload?.error || `อัปโหลดรูปไม่สำเร็จ (${response.status})`);
        error.retryable = response.status >= 500 || response.status === 408 || response.status === 429;
        throw error;
      }
      return payload;
    } catch (error) {
      const retryable = error?.name === "AbortError" || error?.retryable || error instanceof TypeError;
      if (attempt < 2 && retryable) {
        setImageUploadStatus("การเชื่อมต่อสะดุด กำลังลองอัปโหลดอีกครั้ง...", "uploading");
        await new Promise(resolve => setTimeout(resolve, 450));
        return uploadMediaRequest(prepared, attempt + 1);
      }
      if (error?.name === "AbortError") throw new Error("อัปโหลดรูปใช้เวลานานเกินไป กรุณากดลองอัปโหลดอีกครั้ง");
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  async function uploadSelectedImage() {
    const input = byId("fieldRealImageUpload");
    const file = input?.files?.[0];
    if (!file) throw new Error("กรุณาเลือกรูปก่อนอัปโหลด");
    const button = byId("adminUploadImageBtn");
    if (button) { button.disabled = true; button.textContent = "กำลังอัปโหลด..."; }
    setImageUploadStatus(`กำลังเตรียมรูป ${file.name}...`, "uploading");
    try {
      const prepared = await prepareMobileImage(file);
      setImageUploadStatus(prepared.resized ? "ย่อรูปแล้ว กำลังอัปโหลด..." : "กำลังอัปโหลดรูป...", "uploading");
      const payload = await uploadMediaRequest(prepared);
      uploadedMedia = payload.media;
      const absoluteUrl = new URL(payload.media.url, location.origin).href;
      byId("fieldRealImage").value = absoluteUrl;
      byId("fieldRealImage").dataset.mediaId = payload.media.media_id || "";
      renderLiveImagePreview(absoluteUrl, prepared.originalName);
      resetDraftPreview();
      setImageUploadStatus(`✓ อัปโหลดสำเร็จ • ${prepared.originalName}${prepared.resized ? " • ย่อรูปอัตโนมัติ" : ""}`, "success");
      setStatus(`อัปโหลดรูปแล้ว • ${prepared.originalName} • ยังอยู่ใน Internal Media Store และยังไม่ Publish`);
      return payload.media;
    } catch (error) {
      uploadedMedia = null;
      delete byId("fieldRealImage")?.dataset?.mediaId;
      setImageUploadStatus(`อัปโหลดไม่สำเร็จ: ${error.message || String(error)} • กด “ลองอัปโหลดอีกครั้ง”`, "error");
      if (button) button.textContent = "ลองอัปโหลดอีกครั้ง";
      throw error;
    } finally {
      if (button) { button.disabled = false; if (button.textContent === "กำลังอัปโหลด...") button.textContent = "อัปโหลดรูป"; }
    }
  }

  function readCommerceFoundation() {
    const mode = text(byId("merchantMode")?.value || "normal") || "normal";
    const urls = {
      line_url: text(byId("merchantLineUrl")?.value),
      facebook_url: text(byId("merchantFacebookUrl")?.value),
      menu_url: text(byId("merchantMenuUrl")?.value),
      booking_url: text(byId("merchantBookingUrl")?.value)
    };
    Object.entries(urls).forEach(([key, value]) => {
      if (value && !isHttpUrl(value)) throw new Error(`${key} ต้องเป็น http(s) URL`);
    });
    const gallery = text(byId("merchantGallery")?.value).split(",").map(v => v.trim()).filter(Boolean);
    if (gallery.length > 20) throw new Error("Gallery รองรับสูงสุด 20 รูป");
    const startRaw = text(byId("vipContractStart")?.value);
    const endRaw = text(byId("vipContractEnd")?.value);
    if (mode === "vip" && (!startRaw || !endRaw)) throw new Error("VIP ต้องกำหนดวันเริ่มและวันหมดสัญญา");
    if (startRaw && endRaw && new Date(endRaw) <= new Date(startRaw)) throw new Error("วันหมดสัญญาต้องหลังวันเริ่มสัญญา");
    return {
      merchant_content: {
        gallery_media_ids: [...new Set(gallery)],
        line_url: urls.line_url || null,
        facebook_url: urls.facebook_url || null,
        menu_url: urls.menu_url || null,
        booking_url: urls.booking_url || null,
        highlight_text: text(byId("merchantHighlight")?.value) || null,
        uploaded_media_id: uploadedMedia?.media_id || byId("fieldRealImage")?.dataset?.mediaId || null
      },
      sponsor_entitlement: {
        mode,
        plan: text(byId("vipPlan")?.value) || null,
        contract_start_at: startRaw ? new Date(startRaw).toISOString() : null,
        contract_end_at: endRaw ? new Date(endRaw).toISOString() : null,
        auto_expire: true,
        contract_reference: text(byId("vipContractReference")?.value) || null
      },
      public_effect: false,
      ranking_effect: false
    };
  }

  function placeLabel(place) {
    const category = Array.isArray(place.categories) ? place.categories.join(", ") : "";
    return [place.name || "ไม่ระบุชื่อ", place.province || "", category].filter(Boolean).join(" — ");
  }

  function categoryLabel(place) {
    const values = Array.isArray(place?.categories) ? place.categories : [];
    const labels = {
      restaurant: "ร้านอาหาร", cafe: "คาเฟ่", fast_food: "อาหารจานด่วน",
      vegetarian: "เจ / มังสวิรัติ", vegan: "เจ / มังสวิรัติ",
      attraction: "สถานที่น่าเที่ยว", tourism: "สถานที่น่าเที่ยว", temple: "วัด / ศาสนสถาน",
      fuel: "ปั๊มน้ำมัน", pharmacy: "ร้านยา", clinic: "คลินิก", car_repair: "ซ่อมรถ", laundry: "ซักรีด"
    };
    for (const value of values) if (labels[value]) return labels[value];
    return values[0] || "สถานที่";
  }

  function fallbackGroup(place) {
    const values = new Set(Array.isArray(place?.categories) ? place.categories : []);
    if (values.has("vegetarian") || values.has("vegan") || values.has("jay")) return "vegetarian";
    if (["fuel", "pharmacy", "clinic", "car_repair", "laundry"].some(v => values.has(v))) return "service";
    if (["attraction", "tourism", "temple", "museum", "park"].some(v => values.has(v))) return "go";
    return "eat";
  }

  function detailValue(place, field) {
    if (!place) return "";
    if (field === "real_image") return place.real_image || place.image_url || place.image || "";
    if (field === "description") return place.description || "";
    return place[field] ?? "";
  }

  function completeness(place) {
    const present = DETAIL_FIELDS.filter(field => text(detailValue(place, field))).length;
    return {
      present,
      total: DETAIL_FIELDS.length,
      percent: Math.round((present / DETAIL_FIELDS.length) * 100),
      missing: DETAIL_FIELDS.filter(field => !text(detailValue(place, field)))
    };
  }

  function placeImageHtml(place) {
    const imageContract = window.PrachinLife?.core?.placeImage;
    if (imageContract && typeof imageContract.renderPlaceImage === "function") {
      return window.PrachinLife.core.placeImage.renderPlaceImage(
        place, fallbackGroup(place), place?.name || "สถานที่"
      );
    }
    return `<img class="place-card-image" src="assets/images/place-masters/eat-master.png" alt="${escapeHtml(place?.name || "สถานที่")}">`;
  }

  function renderPlaceCard(place) {
    const quality = completeness(place);
    const missing = quality.missing.slice(0, 3).map(field =>
      `<span class="admin-missing-chip">ขาด ${escapeHtml(DETAIL_LABELS[field] || field)}</span>`
    ).join("");
    const extra = quality.missing.length > 3
      ? `<span class="admin-missing-chip">+${quality.missing.length - 3}</span>` : "";
    const chips = quality.missing.length
      ? missing + extra
      : '<span class="admin-complete-chip">ข้อมูลสำคัญครบ</span>';
    const location = place.address || place.district || place.province || "ยังไม่มีข้อมูลพื้นที่";

    return `
      <article class="admin-place-card" data-place-id="${escapeHtml(place.id)}">
        <div class="admin-place-media">
          ${placeImageHtml(place)}
          <span class="admin-category-pill">${escapeHtml(categoryLabel(place))}</span>
        </div>
        <div class="admin-place-body">
          <h3 class="admin-place-title">${escapeHtml(place.name || "ไม่ระบุชื่อ")}</h3>
          <p class="admin-place-location">📍 ${escapeHtml(location)}</p>
          <div class="admin-completeness">
            <strong>ข้อมูล ${quality.percent}%</strong>
            <div class="admin-missing-chips">${chips}</div>
          </div>
          <div class="admin-card-actions">
            <button class="admin-edit-place-btn" type="button" data-admin-edit-id="${escapeHtml(place.id)}">✏️ แก้ไขข้อมูล</button>
          </div>
        </div>
      </article>`;
  }

  function renderCards() {
    const container = byId("adminPlaceCards");
    if (!container) return;
    const visible = filteredPlaces.slice(0, visibleCount);
    container.innerHTML = visible.length
      ? visible.map(renderPlaceCard).join("")
      : '<p class="admin-muted">ไม่พบสถานที่ตรงกับคำค้น</p>';
    byId("adminPlaceCount").textContent = `${filteredPlaces.length} สถานที่`;
    byId("adminShowMoreBtn").classList.toggle("hidden", visibleCount >= filteredPlaces.length);
  }

  function applySearch(query = "") {
    const q = text(query).toLowerCase();
    filteredPlaces = allPlaces.filter(place => {
      if (!q) return true;
      const haystack = [place.name, place.province, place.address, ...(place.categories || [])]
        .filter(Boolean).join(" ").toLowerCase();
      return haystack.includes(q);
    });
    visibleCount = PAGE_SIZE;
    renderPlaceOptions(q);
    renderCards();
  }

  function renderPlaceOptions(query = "") {
    const select = byId("adminPlaceSelect");
    if (!select) return;
    const matches = query ? filteredPlaces : allPlaces;
    select.innerHTML = '<option value="">เลือกสถานที่...</option>' + matches.slice(0, 250).map(place =>
      `<option value="${escapeHtml(place.id)}">${escapeHtml(placeLabel(place))}</option>`
    ).join("");
    if (selectedPlace && matches.some(p => p.id === selectedPlace.id)) select.value = selectedPlace.id;
  }

  function clearFormValues() {
    [
      "fieldCanonicalName", "fieldProvince", "fieldDistrict", "fieldSubdistrict", "fieldArea", "fieldAddress",
      "fieldLatitude", "fieldLongitude", "fieldOpeningHours", "fieldPhone", "fieldWebsite", "fieldRealImage",
      "fieldCategories", "fieldDescription", "adminSourceName", "adminSourceUrl", "adminNote",
      "vipPlan", "vipContractStart", "vipContractEnd", "vipContractReference", "merchantGallery",
      "merchantLineUrl", "merchantFacebookUrl", "merchantMenuUrl", "merchantBookingUrl", "merchantHighlight"
    ].forEach(id => { const node = byId(id); if (node) node.value = ""; });
    if (byId("merchantMode")) byId("merchantMode").value = "normal";
    if (byId("fieldRealImageUpload")) byId("fieldRealImageUpload").value = "";
    uploadedMedia = null;
    renderLiveImagePreview();
  }

  function resetDraftPreview() {
    currentDraft = null;
    byId("adminDraftPreview").textContent = "ยังไม่มี draft";
    byId("adminCopyDraftBtn").disabled = true;
    byId("adminSaveDraftBtn").disabled = true;
    const preview = byId("adminBeforeAfterPreview");
    if (preview) preview.innerHTML = '<p class="admin-muted">สร้าง Evidence Draft เพื่อดู Preview ก่อน / หลัง</p>';
  }

  function populateSelectedPlace(place, scroll = false) {
    createMode = false;
    legacySeedPlace = null;
    selectedPlace = place || null;
    resetDraftPreview();
    if (!place) {
      byId("adminPlaceSummary").textContent = "ยังไม่ได้เลือกสถานที่";
      byId("adminFormTitle").textContent = "เลือกสถานที่จาก Card เพื่อแก้ไข";
      byId("adminFormMode").textContent = "ยังไม่ได้เลือก";
      return;
    }
    byId("adminPlaceSummary").textContent = `กำลังแก้: ${place.name} • ID: ${place.id}`;
    byId("adminFormTitle").textContent = `แก้ไข: ${place.name || "สถานที่"}`;
    byId("adminFormMode").textContent = "แก้สถานที่เดิม";
    byId("adminFormMode").classList.remove("is-new");
    byId("fieldCanonicalName").value = place.name || "";
    byId("fieldProvince").value = place.province || "";
    byId("fieldDistrict").value = place.district || "";
    byId("fieldSubdistrict").value = place.subdistrict || "";
    byId("fieldArea").value = place.area || "";
    byId("fieldAddress").value = place.address || "";
    byId("fieldLatitude").value = place.latitude ?? "";
    byId("fieldLongitude").value = place.longitude ?? "";
    byId("fieldOpeningHours").value = place.opening_hours || "";
    byId("fieldPhone").value = place.phone || "";
    byId("fieldWebsite").value = place.website || "";
    byId("fieldRealImage").value = place.real_image || place.image_url || "";
    uploadedMedia = null;
    renderLiveImagePreview(byId("fieldRealImage").value, place.name || "รูปปัจจุบัน");
    byId("fieldCategories").value = Array.isArray(place.categories) ? place.categories.join(",") : "";
    byId("fieldDescription").value = place.description || "";
    byId("adminSourceName").value = place.source_name || "";
    byId("adminSourceUrl").value = place.source_url || "";
    if (byId("adminPlaceSelect")) byId("adminPlaceSelect").value = place.id;
    if (scroll) byId("adminEditPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function startNewPlace() {
    createMode = true;
    legacySeedPlace = null;
    selectedPlace = null;
    clearFormValues();
    resetDraftPreview();
    byId("adminPlaceSummary").textContent = "โหมดเพิ่มสถานที่ใหม่ — ยังไม่ได้สร้าง Canonical Place";
    byId("adminFormTitle").textContent = "เพิ่มสถานที่ใหม่";
    byId("adminFormHint").textContent = "กรอกข้อมูลที่มีหลักฐานรองรับ ระบบจะสร้าง create-place evidence draft เท่านั้น";
    byId("adminFormMode").textContent = "สถานที่ใหม่";
    byId("adminFormMode").classList.add("is-new");
    byId("adminPlaceSelect").value = "";
    byId("adminEditPanel").scrollIntoView({ behavior: "smooth", block: "start" });
    setStatus("เริ่มเพิ่มสถานที่ใหม่ — ต้องระบุชื่อ จังหวัด พิกัด หมวด และแหล่งข้อมูล");
  }

  function populateLegacyPlace(place) {
    if (!place || typeof place !== "object") throw new Error("Legacy handoff ไม่ถูกต้อง");
    createMode = true;
    selectedPlace = null;
    legacySeedPlace = place;
    resetDraftPreview();
    clearFormValues();

    byId("adminPlaceSummary").textContent = `นำเข้าปรับปรุงจากข้อมูลเดิม: ${place.name || "สถานที่"} • Legacy ID: ${place.legacy_reference_id || place.id || "-"}`;
    byId("adminFormTitle").textContent = `เพิ่ม / ปรับปรุงเข้าสู่ V2: ${place.name || "สถานที่"}`;
    byId("adminFormHint").textContent = "ข้อมูลเดิมถูก preload เพื่อช่วยกรอก แต่ผลลัพธ์จะเป็น create-place evidence draft และยังไม่เขียน Canonical DB";
    byId("adminFormMode").textContent = "นำเข้าจากข้อมูลเดิม";
    byId("adminFormMode").classList.add("is-new");

    byId("fieldCanonicalName").value = place.name || "";
    byId("fieldProvince").value = place.province || "";
    byId("fieldDistrict").value = place.district || "";
    byId("fieldSubdistrict").value = place.subdistrict || "";
    byId("fieldArea").value = place.area || "";
    byId("fieldAddress").value = place.address || "";
    byId("fieldLatitude").value = place.latitude ?? "";
    byId("fieldLongitude").value = place.longitude ?? "";
    byId("fieldOpeningHours").value = place.opening_hours || "";
    byId("fieldPhone").value = place.phone || "";
    byId("fieldWebsite").value = place.website || "";
    byId("fieldRealImage").value = place.real_image || place.image_url || "";
    uploadedMedia = null;
    renderLiveImagePreview(byId("fieldRealImage").value, place.name || "รูปปัจจุบัน");
    byId("fieldCategories").value = Array.isArray(place.categories) ? place.categories.join(",") : "";
    byId("fieldDescription").value = place.description || "";
    byId("adminSourceName").value = place.source_name || "";
    byId("adminSourceUrl").value = place.source_url || "";
    if (byId("adminPlaceSelect")) byId("adminPlaceSelect").value = "";

    byId("adminEditPanel").scrollIntoView({ behavior: "smooth", block: "start" });
    setStatus("โหลดข้อมูลเดิมเข้า Form แล้ว — ตรวจสอบ/เติมข้อมูลและ provenance ก่อนสร้าง Evidence Draft");
  }

  function readLegacyHandoff(expectedId) {
    let raw = "";
    try {
      raw = sessionStorage.getItem(LEGACY_HANDOFF_KEY) || "";
    } catch {
      return null;
    }
    if (!raw) return null;
    try {
      const place = JSON.parse(raw);
      const actualId = text(place?.legacy_reference_id || place?.id);
      if (expectedId && actualId !== expectedId) return null;
      return place;
    } catch {
      return null;
    }
  }

  function changedText(fieldName, elementId, originalValue = "") {
    const value = text(byId(elementId).value);
    if (!value || value === text(originalValue)) return null;
    return { field_name: fieldName, value };
  }

  function readLocation(original = null, required = false) {
    const lat = text(byId("fieldLatitude").value);
    const lng = text(byId("fieldLongitude").value);
    if (!lat && !lng && !required) return null;
    const latitude = Number(lat), longitude = Number(lng);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      throw new Error("พิกัดไม่ถูกต้อง");
    }
    if (original && latitude === Number(original.latitude) && longitude === Number(original.longitude)) return null;
    return { field_name: "location", value: { latitude, longitude } };
  }

  function readCategories(required = false, original = []) {
    const categories = text(byId("fieldCategories").value).split(",").map(v => v.trim()).filter(Boolean);
    const normalized = [...new Set(categories)].sort();
    if (required && !normalized.length) throw new Error("สถานที่ใหม่ต้องมีอย่างน้อย 1 หมวด");
    const originalNormalized = Array.isArray(original) ? [...new Set(original)].sort() : [];
    if (!normalized.length || JSON.stringify(normalized) === JSON.stringify(originalNormalized)) return null;
    return { field_name: "categories", value: normalized };
  }

  function buildChanges() {
    if (!selectedPlace && !createMode) throw new Error("กรุณาเลือกสถานที่ หรือกดเพิ่มสถานที่ใหม่ก่อน");
    const seed = legacySeedPlace || {};
    const base = selectedPlace || seed;
    const compareBase = createMode ? {} : base;
    const changes = [];
    const mappings = [
      ["canonical_name", "fieldCanonicalName", compareBase.name], ["province", "fieldProvince", compareBase.province],
      ["district", "fieldDistrict", compareBase.district], ["subdistrict", "fieldSubdistrict", compareBase.subdistrict],
      ["area", "fieldArea", compareBase.area], ["address_text", "fieldAddress", compareBase.address],
      ["opening_hours", "fieldOpeningHours", compareBase.opening_hours], ["phone", "fieldPhone", compareBase.phone],
      ["website", "fieldWebsite", compareBase.website], ["real_image", "fieldRealImage", compareBase.real_image || compareBase.image_url],
      ["description", "fieldDescription", compareBase.description]
    ];
    for (const [field, id, original] of mappings) {
      const change = changedText(field, id, original || "");
      if (change) changes.push(change);
    }
    const location = readLocation(createMode ? null : base, createMode);
    if (location) changes.push(location);
    const categories = readCategories(createMode, createMode ? [] : (base.categories || []));
    if (categories) changes.push(categories);

    if (createMode) {
      if (!text(byId("fieldCanonicalName").value)) throw new Error("สถานที่ใหม่ต้องมีชื่อสถานที่");
      if (!text(byId("fieldProvince").value)) throw new Error("สถานที่ใหม่ต้องระบุจังหวัด");
    }
    return changes;
  }

  function validateChange(change) {
    if (!ALLOWED_FIELDS.has(change.field_name)) throw new Error(`field ไม่ได้รับอนุญาต: ${change.field_name}`);
    if (["website", "real_image"].includes(change.field_name) && !isHttpUrl(change.value)) {
      throw new Error(`${change.field_name} ต้องเป็น http(s) URL`);
    }
  }



  function snapshotPlace(place = {}) {
    return {
      name: text(place.name || place.title || place.canonical_name),
      province: text(place.province),
      district: text(place.district),
      subdistrict: text(place.subdistrict),
      area: text(place.area),
      address: text(place.address || place.address_text),
      latitude: place.latitude ?? place.location?.latitude ?? null,
      longitude: place.longitude ?? place.location?.longitude ?? null,
      opening_hours: text(place.opening_hours),
      phone: text(place.phone),
      website: text(place.website),
      real_image: text(place.real_image || place.image_url),
      description: text(place.description),
      categories: Array.isArray(place.categories) ? [...place.categories] : []
    };
  }

  function buildOperatorChanges(seed = {}) {
    const changes = [];
    const mappings = [
      ["canonical_name", "fieldCanonicalName", seed.name], ["province", "fieldProvince", seed.province],
      ["district", "fieldDistrict", seed.district], ["subdistrict", "fieldSubdistrict", seed.subdistrict],
      ["area", "fieldArea", seed.area], ["address_text", "fieldAddress", seed.address],
      ["opening_hours", "fieldOpeningHours", seed.opening_hours], ["phone", "fieldPhone", seed.phone],
      ["website", "fieldWebsite", seed.website], ["real_image", "fieldRealImage", seed.real_image || seed.image_url],
      ["description", "fieldDescription", seed.description]
    ];
    for (const [field, id, original] of mappings) {
      const change = changedText(field, id, original || "");
      if (change) changes.push(change);
    }
    const location = readLocation(seed && (seed.latitude != null || seed.longitude != null) ? seed : null, false);
    if (location) changes.push(location);
    const categories = readCategories(false, seed.categories || []);
    if (categories) changes.push(categories);
    return changes;
  }

  function buildEvidenceDraft() {
    const sourceName = text(byId("adminSourceName").value);
    const sourceUrl = text(byId("adminSourceUrl").value);
    if (!sourceName) throw new Error("กรุณาระบุชื่อแหล่งข้อมูล");
    if (!isHttpUrl(sourceUrl)) throw new Error("กรุณาระบุ URL แหล่งข้อมูลแบบ http(s)");
    const changes = buildChanges();
    if (!changes.length) throw new Error("ยังไม่มีข้อมูลที่เปลี่ยนแปลง");
    changes.forEach(validateChange);
    const note = text(byId("adminNote").value);
    return {
      schema_version: CONTRACT_VERSION,
      intake: "admin_web",
      mode: "evidence_draft_only",
      operation: createMode ? "create_place_candidate" : "update_place_candidate",
      place_id: selectedPlace?.id || null,
      legacy_context: legacySeedPlace ? {
        reference_id: legacySeedPlace.legacy_reference_id || legacySeedPlace.id || null,
        dataset: legacySeedPlace.legacy_dataset || null
      } : null,
      source: { source_name: sourceName, source_url: sourceUrl },
      note: note || null,
      changes,
      review_context: {
        baseline_kind: legacySeedPlace ? "legacy_seed" : (createMode ? "new_blank" : "canonical"),
        seed_snapshot: legacySeedPlace ? snapshotPlace(legacySeedPlace) : null,
        operator_changes: createMode && legacySeedPlace ? buildOperatorChanges(snapshotPlace(legacySeedPlace)) : changes
      },
      commerce_foundation: readCommerceFoundation()
    };
  }

  async function loadPlaces() {
    const response = await fetch(EXPORT_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`โหลด V2 export ไม่สำเร็จ (${response.status})`);
    const payload = await response.json();
    if (!payload || !Array.isArray(payload.places)) throw new Error("V2 export schema ไม่ถูกต้อง");
    allPlaces = payload.places;
    filteredPlaces = [...allPlaces];
    renderPlaceOptions();
    renderCards();

    const params = new URLSearchParams(location.search);
    const requestedPlaceId = text(params.get("place_id"));
    const requestedMode = text(params.get("mode"));

    if (requestedMode === "legacy") {
      const expectedLegacyId = text(params.get("legacy_id"));
      const legacyPlace = readLegacyHandoff(expectedLegacyId);
      if (legacyPlace) {
        populateLegacyPlace(legacyPlace);
        return;
      }
      setStatus("ไม่พบข้อมูล handoff จาก Card เดิม กรุณากลับไปเลือก Card ใหม่", true);
      return;
    }

    if (requestedMode === "new") {
      startNewPlace();
      return;
    }

    if (requestedPlaceId) {
      const requestedPlace = allPlaces.find(place => String(place.id) === requestedPlaceId);
      if (requestedPlace) {
        populateSelectedPlace(requestedPlace, true);
        setStatus(`โหลดข้อมูลปัจจุบันของ ${requestedPlace.name || "สถานที่"} เข้า Form แล้ว`);
        return;
      }
      setStatus("ไม่พบ place_id นี้ใน V2 Admin export", true);
      return;
    }

    setStatus(`โหลดสถานที่ ${allPlaces.length} รายการแล้ว`);
  }

  function formPlaceSnapshot() {
    const cats = text(byId("fieldCategories").value).split(",").map(v => v.trim()).filter(Boolean);
    return {
      id: selectedPlace?.id || null,
      name: text(byId("fieldCanonicalName").value),
      province: text(byId("fieldProvince").value),
      district: text(byId("fieldDistrict").value),
      subdistrict: text(byId("fieldSubdistrict").value),
      area: text(byId("fieldArea").value),
      address: text(byId("fieldAddress").value),
      latitude: text(byId("fieldLatitude").value) ? Number(byId("fieldLatitude").value) : null,
      longitude: text(byId("fieldLongitude").value) ? Number(byId("fieldLongitude").value) : null,
      opening_hours: text(byId("fieldOpeningHours").value),
      phone: text(byId("fieldPhone").value),
      website: text(byId("fieldWebsite").value),
      real_image: text(byId("fieldRealImage").value),
      image_url: text(byId("fieldRealImage").value),
      categories: cats,
      description: text(byId("fieldDescription").value),
      source_url: text(byId("adminSourceUrl").value) || selectedPlace?.source_url || legacySeedPlace?.source_url || ""
    };
  }

  function renderEditorPreview(draft) {
    const previewApi = window.PrachinLifeAdminPreview;
    const container = byId("adminBeforeAfterPreview");
    if (!previewApi || !container) return;
    const base = selectedPlace || legacySeedPlace || {};
    const after = formPlaceSnapshot();
    const beforeHtml = createMode && !legacySeedPlace
      ? '<div class="admin-preview-column"><div class="admin-preview-caption">ก่อนปรับปรุง</div><div class="admin-preview-empty">สถานที่ใหม่ — ยังไม่มี Card เดิม</div></div>'
      : `<div class="admin-preview-column">${previewApi.renderCard(base, { caption: "ก่อนปรับปรุง" })}</div>`;
    const afterHtml = `<div class="admin-preview-column is-after">${previewApi.renderCard(after, { caption: "หลังปรับปรุง" })}</div>`;
    container.innerHTML = beforeHtml + afterHtml;
    byId("adminVisualPreviewPanel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function bindEvents() {
    byId("adminPlaceSearch").addEventListener("input", event => applySearch(event.target.value));
    byId("adminPlaceSelect").addEventListener("change", event => {
      populateSelectedPlace(allPlaces.find(place => place.id === event.target.value) || null, true);
    });
    byId("adminPlaceCards").addEventListener("click", event => {
      const button = event.target.closest("[data-admin-edit-id]");
      if (!button) return;
      const place = allPlaces.find(item => item.id === button.dataset.adminEditId);
      if (place) populateSelectedPlace(place, true);
    });
    byId("fieldRealImageUpload")?.addEventListener("change", event => {
      const file = event.target.files?.[0];
      if (!file) {
        renderLiveImagePreview(byId("fieldRealImage").value);
        return;
      }
      const localUrl = URL.createObjectURL(file);
      renderLiveImagePreview(localUrl, `${file.name} · กำลังอัปโหลด`);
      resetDraftPreview();
      setImageUploadStatus(`เลือกรูปแล้ว • ${file.name} • กำลังอัปโหลดอัตโนมัติ`, "uploading");
      imageUploadInFlight = uploadSelectedImage()
        .catch(error => {
          setStatus(error.message || String(error), true);
          return null;
        })
        .finally(() => { imageUploadInFlight = null; });
    });
    byId("adminUploadImageBtn")?.addEventListener("click", async () => {
      try {
        if (imageUploadInFlight) await imageUploadInFlight;
        else await uploadSelectedImage();
      }
      catch (error) { setStatus(error.message || String(error), true); }
    });
    byId("fieldRealImage")?.addEventListener("input", event => {
      uploadedMedia = null;
      delete event.target.dataset.mediaId;
      renderLiveImagePreview(event.target.value);
      resetDraftPreview();
    });
    ["merchantMode","vipPlan","vipContractStart","vipContractEnd","vipContractReference","merchantGallery","merchantLineUrl","merchantFacebookUrl","merchantMenuUrl","merchantBookingUrl","merchantHighlight"].forEach(id => {
      byId(id)?.addEventListener("input", resetDraftPreview);
      byId(id)?.addEventListener("change", resetDraftPreview);
    });
    byId("adminAddPlaceBtn").addEventListener("click", startNewPlace);
    byId("adminShowMoreBtn").addEventListener("click", () => { visibleCount += PAGE_SIZE; renderCards(); });
    byId("adminBuildDraftBtn").addEventListener("click", async () => {
      try {
        if (imageUploadInFlight) {
          setStatus("กำลังอัปโหลดรูป กรุณารอสักครู่...");
          await imageUploadInFlight;
        }
        const selectedFile = byId("fieldRealImageUpload")?.files?.[0];
        if (selectedFile && !byId("fieldRealImage")?.dataset?.mediaId) {
          setImageUploadStatus("ยังไม่มี media reference กำลังลองอัปโหลดรูปอีกครั้งก่อนสร้าง Draft...", "uploading");
          await uploadSelectedImage();
        }
        if (selectedFile && !byId("fieldRealImage")?.dataset?.mediaId) {
          throw new Error("รูปที่เลือกยังอัปโหลดไม่สำเร็จ กรุณากด “ลองอัปโหลดอีกครั้ง”");
        }
        currentDraft = buildEvidenceDraft();
        byId("adminDraftPreview").textContent = JSON.stringify(currentDraft, null, 2);
        renderEditorPreview(currentDraft);
        byId("adminCopyDraftBtn").disabled = false;
        byId("adminSaveDraftBtn").disabled = false;
        setStatus(`สร้าง ${currentDraft.operation} draft ${currentDraft.changes.length} field สำเร็จ — ตรวจ Preview แล้วจึงบันทึกเข้าคิวตรวจสอบ`);
      } catch (error) {
        currentDraft = null;
        byId("adminCopyDraftBtn").disabled = true;
        byId("adminSaveDraftBtn").disabled = true;
        setStatus(error.message || String(error), true);
      }
    });
    byId("adminClearBtn").addEventListener("click", () => {
      if (createMode) startNewPlace();
      else populateSelectedPlace(selectedPlace);
    });
    byId("adminCopyDraftBtn").addEventListener("click", async () => {
      if (!currentDraft) return;
      try { await navigator.clipboard.writeText(JSON.stringify(currentDraft, null, 2)); setStatus("คัดลอก Evidence Draft แล้ว"); }
      catch { setStatus("คัดลอกอัตโนมัติไม่ได้ กรุณาคัดลอกจาก Preview", true); }
    });
    byId("adminSaveDraftBtn").addEventListener("click", async () => {
      if (!currentDraft) return;
      const button = byId("adminSaveDraftBtn");
      button.disabled = true;
      try {
        const response = await fetch(DRAFT_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          cache: "no-store",
          body: JSON.stringify(currentDraft)
        });
        const payload = await response.json();
        if (!response.ok || payload?.status !== "ok") {
          throw new Error(payload?.error || `บันทึก Draft ไม่สำเร็จ (${response.status})`);
        }
        const saved = payload.draft || {};
        setStatus(`บันทึก Draft ${saved.draft_id || ""} แล้ว • สถานะ ${saved.review_status || "pending_review"} • หน้า User ยังไม่เปลี่ยน`);
        byId("adminDraftPreview").textContent = JSON.stringify({
          ...currentDraft,
          persistence: saved,
          canonical_write: false,
          publication: false
        }, null, 2);
      } catch (error) {
        setStatus(`${error.message || String(error)} — ให้เปิด scripts/admin_internal_server.py แทน python -m http.server`, true);
        button.disabled = false;
      }
    });
  }

  async function init() {
    if (!internalRuntimeAllowed()) {
      byId("adminAccessWarning").classList.remove("hidden");
      document.querySelectorAll("input,select,textarea,button").forEach(node => { node.disabled = true; });
      return;
    }
    bindEvents();
    try { await loadPlaces(); }
    catch (error) { setStatus(error.message || String(error), true); }
  }

  window.PrachinLifeAdmin = Object.freeze({
    contractVersion: CONTRACT_VERSION,
    allowedFields: ALLOWED_FIELDS,
    detailFields: DETAIL_FIELDS,
    buildEvidenceDraft,
    completeness,
    internalRuntimeAllowed,
    uploadSelectedImage,
    readCommerceFoundation,
    renderLiveImagePreview
  });

  document.addEventListener("DOMContentLoaded", init, { once: true });
})();
