(() => {
  "use strict";

  window.PrachinLife = window.PrachinLife || {};
  window.PrachinLife.core = window.PrachinLife.core || {};

  const registry = new Map();
  let generatedKey = 0;
  let previousFocus = null;

  function clean(value) {
    if (value === null || value === undefined) return "";
    return String(value).trim();
  }

  function metadata(place) {
    return place?.metadata && typeof place.metadata === "object" ? place.metadata : {};
  }

  function first(place, paths) {
    const meta = metadata(place);
    const values = {
      opening_hours: [meta.opening_hours, place?.opening_hours, place?.hours],
      description: [meta.description, place?.description, place?.summary],
    };
    for (const value of values[paths] || []) {
      const result = clean(value);
      if (result) return result;
    }
    return "";
  }

  function getOpeningHours(place) {
    return first(place, "opening_hours");
  }

  function getDescription(place) {
    return first(place, "description");
  }

  function normalizedCategories(place) {
    const values = [
      ...(Array.isArray(place?.categories) ? place.categories : []),
      place?.main_category,
      place?.category,
      place?.type,
      place?.place_type,
      place?.eat_type,
    ];
    return [...new Set(values.map((value) => clean(value).toLowerCase()).filter(Boolean))];
  }

  function inferGroup(place) {
    const categories = normalizedCategories(place);
    if (categories.some((value) => ["vegetarian", "vegan", "jay"].includes(value))) return "vegetarian";
    if (categories.some((value) => ["cafe"].includes(value))) return "cafe";
    if (categories.some((value) => ["eat", "food", "restaurant", "fast_food", "food_court", "ice_cream"].includes(value))) return "eat";
    if (categories.some((value) => value === "go" || value === "travel" || value.startsWith("tourism:"))) return "go";
    if (categories.some((value) => value === "service" || value.startsWith("healthcare:") || ["hospital", "clinic", "pharmacy", "bank", "atm", "fuel", "laundry", "car_repair"].includes(value))) return "service";
    return "default";
  }

  function getCategoryLabel(place) {
    const metaLabel = clean(metadata(place).category_label);
    if (metaLabel) return metaLabel;

    const group = inferGroup(place);
    const labels = {
      vegetarian: "เจ / มังสวิรัติ",
      cafe: "คาเฟ่",
      eat: "ร้านอาหาร",
      go: "เที่ยว / สถานที่",
      service: "บริการใกล้ตัว",
      default: "สถานที่",
    };
    return labels[group] || labels.default;
  }

  function getDistance(place) {
    if (!Number.isFinite(place?._distance)) return "";
    const formatter = window.PrachinLife.core.formatDistance;
    return typeof formatter === "function"
      ? clean(formatter(place._distance))
      : `${Math.round(place._distance)} ม.`;
  }

  function getDetail(place, fallbackProvince = "") {
    const card = window.PrachinLife.core.placeCard;
    return Object.freeze({
      title: clean(place?.title || place?.name) || "ไม่ระบุชื่อสถานที่",
      categoryLabel: getCategoryLabel(place),
      distance: getDistance(place),
      location: card.getLocationLabel(place, fallbackProvince),
      openingHours: getOpeningHours(place),
      phone: card.getPhone(place),
      website: card.getWebsite(place),
      sourceName: card.getSourceName(place),
      sourceUrl: card.getSourceUrl(place),
      description: getDescription(place),
      hasCoordinates: card.hasCoordinates(place),
    });
  }

  function renderFacts(place, fallbackProvince = "") {
    const detail = getDetail(place, fallbackProvince);
    const escapeHtml = window.PrachinLife.core.escapeHtml;
    const rows = [];
    if (detail.location) rows.push(`📍 ${escapeHtml(detail.location)}`);
    if (detail.openingHours) rows.push(`🕒 เวลาเปิด: ${escapeHtml(detail.openingHours)}`);
    if (detail.description) rows.push(escapeHtml(detail.description));
    return rows.map(value => `<p class="promotion-description place-detail-fact">${value}</p>`).join("");
  }

  function placeKey(place) {
    const id = clean(place?.id);
    if (id) return `id:${id}`;
    generatedKey += 1;
    return `generated:${generatedKey}`;
  }

  function register(place) {
    if (!place || typeof place !== "object") return "";
    const existing = clean(place.__prachinLifeDetailKey);
    if (existing && registry.has(existing)) return existing;
    const key = placeKey(place);
    registry.set(key, place);
    try {
      Object.defineProperty(place, "__prachinLifeDetailKey", {
        value: key,
        enumerable: false,
        configurable: true,
      });
    } catch (_) {
      // Frozen input is still supported through the registry key returned here.
    }
    return key;
  }

  function renderOpenButton(place) {
    const key = register(place);
    if (!key) return "";
    const escape = window.PrachinLife.core.escapeAttribute;
    return `
      <button class="source-button place-card-action place-card-action-detail"
        type="button" data-place-detail-key="${escape(key)}">
        ดูรายละเอียด
      </button>
    `;
  }

  function renderInfoRow(label, value, className = "") {
    if (!value) return "";
    const escapeHtml = window.PrachinLife.core.escapeHtml;
    return `
      <div class="place-detail-row ${className}">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
    `;
  }

  function websiteLabel(url) {
    if (!url) return "";
    try {
      return new URL(url).hostname.replace(/^www\./i, "");
    } catch (_) {
      return url;
    }
  }

  function renderDetailMarkup(place, fallbackProvince = "ปราจีนบุรี") {
    const card = window.PrachinLife.core.placeCard;
    const placeImage = window.PrachinLife.core.placeImage;
    const escapeHtml = window.PrachinLife.core.escapeHtml;
    const escape = window.PrachinLife.core.escapeAttribute;
    const detail = getDetail(place, fallbackProvince);
    const group = inferGroup(place);
    const safeSourceUrl = card.safeHttpUrl(detail.sourceUrl);
    const phoneHref = card.getPhoneHref(place);
    const website = detail.website;

    const sourceLink = safeSourceUrl
      ? `<a class="place-detail-source-link" href="${escape(safeSourceUrl)}" target="_blank" rel="noopener noreferrer">ดูแหล่งข้อมูลต้นทาง</a>`
      : "";

    return `
      <section class="place-detail-sheet" role="document">
        <button class="place-detail-close" type="button" data-place-detail-close aria-label="ปิดรายละเอียดสถานที่">×</button>

        <div class="place-detail-hero">
          ${placeImage.renderPlaceImage(place, group, detail.title)}
        </div>

        <div class="place-detail-content">
          <div class="place-detail-heading">
            <span class="place-detail-category">${escapeHtml(detail.categoryLabel)}</span>
            <h2 id="placeDetailTitle">${escapeHtml(detail.title)}</h2>
            ${detail.distance ? `<p class="place-detail-distance">📍 ${escapeHtml(detail.distance)} จากตำแหน่งของคุณ</p>` : ""}
          </div>

          <div class="place-detail-grid">
            ${renderInfoRow("พื้นที่ / ที่อยู่", detail.location)}
            ${renderInfoRow("เวลาเปิด", detail.openingHours)}
            ${detail.phone && phoneHref ? `
              <div class="place-detail-row">
                <span>โทรศัพท์</span>
                <strong><a href="tel:${escape(phoneHref)}">${escapeHtml(detail.phone)}</a></strong>
              </div>
            ` : ""}
            ${website ? `
              <div class="place-detail-row">
                <span>เว็บไซต์</span>
                <strong><a href="${escape(website)}" target="_blank" rel="noopener noreferrer">${escapeHtml(websiteLabel(website))}</a></strong>
              </div>
            ` : ""}
          </div>

          ${detail.description ? `
            <div class="place-detail-description">
              <h3>รายละเอียด</h3>
              <p>${escapeHtml(detail.description)}</p>
            </div>
          ` : ""}

          ${card.renderActions(place, { includeDetail: false })}

          <div class="place-detail-provenance">
            <span>แหล่งข้อมูล</span>
            <strong>${escapeHtml(detail.sourceName)}</strong>
            ${sourceLink}
            <p>ข้อมูลบางรายการอาจเปลี่ยนแปลงได้ ควรตรวจสอบกับแหล่งต้นทางก่อนเดินทางหรือตัดสินใจ</p>
          </div>
        </div>
      </section>
    `;
  }

  function ensureSurface() {
    let backdrop = document.getElementById("placeDetailBackdrop");
    if (backdrop) return backdrop;

    backdrop = document.createElement("div");
    backdrop.id = "placeDetailBackdrop";
    backdrop.className = "place-detail-backdrop hidden";
    backdrop.setAttribute("role", "dialog");
    backdrop.setAttribute("aria-modal", "true");
    backdrop.setAttribute("aria-labelledby", "placeDetailTitle");
    backdrop.innerHTML = `<div class="place-detail-host"></div>`;
    document.body.appendChild(backdrop);

    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop || event.target.closest("[data-place-detail-close]")) {
        closePlaceDetail();
      }
    });

    return backdrop;
  }

  function openPlaceDetail(place, fallbackProvince = "ปราจีนบุรี") {
    if (!place) return false;
    const backdrop = ensureSurface();
    const host = backdrop.querySelector(".place-detail-host");
    if (!host) return false;

    previousFocus = document.activeElement;
    host.innerHTML = renderDetailMarkup(place, fallbackProvince);
    backdrop.classList.remove("hidden");
    document.body.classList.add("place-detail-open");

    const closeButton = backdrop.querySelector(".place-detail-close");
    closeButton?.focus({ preventScroll: true });
    return true;
  }

  function closePlaceDetail() {
    const backdrop = document.getElementById("placeDetailBackdrop");
    if (!backdrop || backdrop.classList.contains("hidden")) return;
    backdrop.classList.add("hidden");
    document.body.classList.remove("place-detail-open");
    const focusTarget = previousFocus;
    previousFocus = null;
    if (focusTarget && typeof focusTarget.focus === "function") {
      focusTarget.focus({ preventScroll: true });
    }
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest?.("[data-place-detail-key]");
    if (!trigger) return;
    const place = registry.get(clean(trigger.dataset.placeDetailKey));
    if (place) openPlaceDetail(place);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePlaceDetail();
  });

  window.PrachinLife.core.placeDetail = Object.freeze({
    getOpeningHours,
    getDescription,
    getCategoryLabel,
    getDetail,
    renderFacts,
    renderOpenButton,
    renderDetailMarkup,
    openPlaceDetail,
    closePlaceDetail,
  });
})();
