(() => {
  "use strict";

  const EXPORT_URL = "data/v2/exports/prachinlife_places_v2.json";
  const LEGACY_URLS = Object.freeze({
    eat: "prachinlife_index.json",
    vegetarian: "vegetarian_index.json",
    go: "go_index.json",
    service: "service_index.json"
  });
  const LEGACY_HANDOFF_KEY = "prachinlife_admin_legacy_handoff_v1";
  const ALLOWED_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]", ""]);
  let editableIds = new Set();
  let legacyPlaces = new Map();

  function internalRuntimeAllowed() {
    return location.protocol === "file:" || ALLOWED_HOSTS.has(location.hostname);
  }

  function editUrl(placeId) {
    return `admin.html?place_id=${encodeURIComponent(placeId)}#adminEditPanel`;
  }

  function legacyEditUrl(placeId) {
    return `admin.html?mode=legacy&legacy_id=${encodeURIComponent(placeId)}#adminEditPanel`;
  }

  function text(value) {
    return String(value ?? "").trim();
  }

  function normalizeLegacyPlace(item, dataset) {
    if (!item || typeof item !== "object") return null;
    const id = text(item.id);
    const name = text(item.name || item.title);
    if (!id || !name) return null;

    const location = item.location && typeof item.location === "object" ? item.location : {};
    const metadata = item.metadata && typeof item.metadata === "object" ? item.metadata : {};
    const sourceObject = item.source && typeof item.source === "object" ? item.source : {};
    const sourceName = text(
      sourceObject.name || metadata.source_name || (typeof item.source === "string" ? item.source : "")
    );
    const sourceUrl = text(sourceObject.url || item.source_url || metadata.source_url);

    let categories = [];
    if (Array.isArray(item.categories)) categories.push(...item.categories);
    if (Array.isArray(item.food_types)) categories.push(...item.food_types);
    if (item.category) categories.push(item.category);
    if (dataset === "eat" && item.content_type === "eat" && item.original_type) categories.push(item.original_type);
    if (dataset === "vegetarian") categories.push("vegetarian");
    if (dataset === "go") categories.push(item.category || "go");
    if (dataset === "service") categories.push(item.category || "service");
    categories = [...new Set(categories.map(text).filter(Boolean))];

    return {
      id,
      name,
      province: text(location.province || item.province),
      district: text(location.district || item.district),
      subdistrict: text(location.subdistrict || item.subdistrict),
      area: text(location.place_name || item.area),
      address: text(item.address || metadata.address),
      latitude: location.latitude ?? item.latitude ?? item.lat ?? null,
      longitude: location.longitude ?? item.longitude ?? item.lng ?? null,
      opening_hours: text(metadata.opening_hours || item.opening_hours),
      phone: text(metadata.phone || metadata.contact?.phone || item.phone),
      website: text(metadata.website || metadata.contact?.website || item.website),
      real_image: text(item.real_image || item.image_url || item.image),
      description: text(item.description || item.summary),
      categories,
      source_name: sourceName,
      source_url: sourceUrl,
      legacy_dataset: dataset,
      legacy_reference_id: id
    };
  }

  async function fetchLegacyDataset(dataset, url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Legacy ${dataset} HTTP ${response.status}`);
    const payload = await response.json();
    if (!Array.isArray(payload)) throw new Error(`Legacy ${dataset} schema ไม่ถูกต้อง`);
    return payload.map(item => normalizeLegacyPlace(item, dataset)).filter(Boolean);
  }

  async function loadLegacyPlaces() {
    const results = await Promise.allSettled(
      Object.entries(LEGACY_URLS).map(async ([dataset, url]) => [dataset, await fetchLegacyDataset(dataset, url)])
    );
    const map = new Map();
    for (const result of results) {
      if (result.status !== "fulfilled") {
        console.warn("PrachinLife admin legacy load warning:", result.reason);
        continue;
      }
      const [, places] = result.value;
      for (const place of places) map.set(place.id, place);
    }
    legacyPlaces = map;
  }

  function decorateCard(card) {
    if (!card) return;
    const placeId = text(card.dataset.placeId);
    if (!placeId) return;

    card.querySelector(":scope > .admin-view-edit-wrap")?.remove();
    const wrap = document.createElement("div");
    wrap.className = "admin-view-edit-wrap";

    if (editableIds.has(placeId)) {
      const link = document.createElement("a");
      link.className = "admin-view-edit-button";
      link.href = editUrl(placeId);
      link.textContent = "✏️ แก้ไข / ปรับปรุงข้อมูล";
      wrap.appendChild(link);
    } else if (legacyPlaces.has(placeId)) {
      const link = document.createElement("a");
      link.className = "admin-view-edit-button admin-view-legacy-button";
      link.href = legacyEditUrl(placeId);
      link.dataset.adminLegacyEditId = placeId;
      link.textContent = "✏️ เพิ่ม / ปรับปรุงเข้าสู่ V2";
      wrap.appendChild(link);
    } else {
      const note = document.createElement("span");
      note.className = "admin-view-unavailable";
      note.textContent = "รายการนี้ยังไม่มีข้อมูลอ้างอิงสำหรับ Admin";
      wrap.appendChild(note);
    }

    card.appendChild(wrap);
    card.dataset.adminDecorated = "1";
  }

  function decorateAllCards(root = document) {
    root.querySelectorAll(".promotion-card[data-place-id]").forEach(decorateCard);
  }

  function observeCards() {
    const observer = new MutationObserver(mutations => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (!(node instanceof Element)) continue;
          if (node.matches?.(".promotion-card[data-place-id]")) decorateCard(node);
          decorateAllCards(node);
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return observer;
  }

  async function loadEditableIds() {
    const response = await fetch(EXPORT_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`Admin V2 export HTTP ${response.status}`);
    const payload = await response.json();
    if (!payload || !Array.isArray(payload.places)) throw new Error("Admin V2 export schema ไม่ถูกต้อง");
    editableIds = new Set(payload.places.map(place => text(place.id)).filter(Boolean));
  }

  function bindLegacyHandoff() {
    document.addEventListener("click", event => {
      const link = event.target.closest?.("[data-admin-legacy-edit-id]");
      if (!link) return;
      const placeId = text(link.dataset.adminLegacyEditId);
      const place = legacyPlaces.get(placeId);
      if (!place) return;
      try {
        sessionStorage.setItem(LEGACY_HANDOFF_KEY, JSON.stringify(place));
      } catch (error) {
        event.preventDefault();
        console.error("PrachinLife admin legacy handoff error:", error);
      }
    });
  }

  async function init() {
    if (!internalRuntimeAllowed()) {
      document.querySelectorAll("[data-place-id]").forEach(card => card.removeAttribute("data-place-id"));
      const toolbar = document.getElementById("adminViewToolbar");
      if (toolbar) toolbar.innerHTML = "<strong>ADMIN MODE DISABLED</strong><span>เปิดได้เฉพาะ local/internal runtime</span>";
      return;
    }

    bindLegacyHandoff();
    observeCards();
    try {
      await Promise.all([loadEditableIds(), loadLegacyPlaces()]);
      decorateAllCards();
    } catch (error) {
      console.error("PrachinLife admin-view error:", error);
    }
  }

  window.PrachinLifeAdminView = Object.freeze({
    internalRuntimeAllowed,
    editUrl,
    legacyEditUrl,
    normalizeLegacyPlace,
    decorateAllCards
  });
  document.addEventListener("DOMContentLoaded", init, { once: true });
})();
