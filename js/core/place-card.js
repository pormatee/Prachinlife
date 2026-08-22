(() => {
  "use strict";

  window.PrachinLife = window.PrachinLife || {};
  window.PrachinLife.core = window.PrachinLife.core || {};

  const TECHNICAL_SOURCE_NAMES = new Set([
    "place_platform_v2",
    "prachinlife-v1-json",
    "PrachinLife V2",
  ]);

  function text(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function metadata(place) {
    return place?.metadata && typeof place.metadata === "object"
      ? place.metadata
      : {};
  }

  function getPhone(place) {
    const meta = metadata(place);
    const raw =
      meta?.contact?.phone
      || meta.phone
      || place?.phone
      || "";

    if (Array.isArray(raw)) {
      return text(raw[0]);
    }

    const value = text(String(raw || ""));

    // Legacy migration may contain a stringified Python list.
    const listMatch = value.match(/^\[['\"]([^'\"]+)/);
    return listMatch ? listMatch[1] : value;
  }

  function getPhoneHref(place) {
    return getPhone(place).replace(/[^+\d]/g, "");
  }

  function getWebsite(place) {
    const meta = metadata(place);
    let value = text(
      meta?.contact?.website
      || meta.website
      || place?.website
      || ""
    );

    if (value && !/^https?:\/\//i.test(value)) {
      value = `https://${value}`;
    }

    return value;
  }

  function getSourceUrl(place) {
    const meta = metadata(place);
    return text(
      place?.source_url
      || meta.source_url
      || ""
    );
  }

  function getSourceName(place) {
    const meta = metadata(place);
    const raw = text(
      meta.source_name
      || (
        typeof place?.source === "string"
          ? place.source
          : place?.source?.name
      )
      || ""
    );

    if (!raw || TECHNICAL_SOURCE_NAMES.has(raw)) {
      return "แหล่งข้อมูลสาธารณะ";
    }

    return raw;
  }

  function getLocationLabel(place, fallbackProvince = "") {
    const loc = place?.location || {};
    const candidates = [
      loc.subdistrict,
      loc.district,
      loc.province,
      place?.subdistrict,
      place?.district,
      place?.area,
      place?.address,
      place?.province,
      fallbackProvince,
    ];

    const seen = new Set();
    const parts = [];

    for (const candidate of candidates) {
      const value = text(candidate);
      if (!value || value === "ไม่ระบุพื้นที่" || seen.has(value)) {
        continue;
      }
      seen.add(value);
      parts.push(value);
      if (parts.length >= 3) break;
    }

    return parts.join(" · ");
  }

  function hasCoordinates(place) {
    const lat = Number(
      place?.location?.latitude
      ?? place?.latitude
      ?? place?.lat
    );
    const lng = Number(
      place?.location?.longitude
      ?? place?.longitude
      ?? place?.lng
    );
    return Number.isFinite(lat) && Number.isFinite(lng);
  }

  function getMapUrl(place) {
    const built = window.PrachinLife.core.buildMapUrl?.(place) || "";
    return text(
      built
      || place?.maps_url
      || place?.map_url
      || place?.google_maps_url
      || ""
    );
  }

  function renderActions(place) {
    const escape = window.PrachinLife.core.escapeAttribute;
    const actions = [];

    const mapUrl = getMapUrl(place);
    const phoneHref = getPhoneHref(place);
    const website = getWebsite(place);
    const sourceUrl = getSourceUrl(place);

    if (mapUrl && hasCoordinates(place)) {
      actions.push(`
        <a class="source-button place-card-action place-card-action-map"
          href="${escape(mapUrl)}" target="_blank" rel="noopener noreferrer">
          📍 เปิดแผนที่
        </a>
      `);
    }

    if (phoneHref) {
      actions.push(`
        <a class="source-button place-card-action place-card-action-phone"
          href="tel:${escape(phoneHref)}">
          📞 โทร
        </a>
      `);
    }

    if (website) {
      actions.push(`
        <a class="source-button place-card-action place-card-action-website"
          href="${escape(website)}" target="_blank" rel="noopener noreferrer">
          🌐 เว็บไซต์
        </a>
      `);
    }

    if (sourceUrl) {
      actions.push(`
        <a class="source-button place-card-action place-card-action-source"
          href="${escape(sourceUrl)}" target="_blank" rel="noopener noreferrer">
          ดูแหล่งข้อมูล
        </a>
      `);
    }

    if (!actions.length) return "";

    return `
      <div class="promotion-actions place-card-actions">
        ${actions.join("")}
      </div>
    `;
  }

  function renderDataNote(place) {
    const sourceName = window.PrachinLife.core.escapeHtml(
      getSourceName(place)
    );
    return `
      <p class="promotion-description place-card-data-note">
        แหล่งข้อมูล: ${sourceName}
        · ควรตรวจสอบรายละเอียดล่าสุดก่อนเดินทาง
      </p>
    `;
  }

  window.PrachinLife.core.placeCard = Object.freeze({
    getPhone,
    getPhoneHref,
    getWebsite,
    getSourceUrl,
    getSourceName,
    getLocationLabel,
    hasCoordinates,
    getMapUrl,
    renderActions,
    renderDataNote,
  });
})();
