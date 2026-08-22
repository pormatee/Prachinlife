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

    return safeHttpUrl(value);
  }

  function getSourceUrl(place) {
    const meta = metadata(place);
    return text(
      place?.source_url
      || meta.source_url
      || ""
    );
  }

  function safeHttpUrl(value) {
    let url = text(value);
    if (!url) return "";
    if (!/^[a-z][a-z0-9+.-]*:/i.test(url)) url = `https://${url}`;
    return /^https?:\/\//i.test(url) ? url : "";
  }

  function safeVipUrl(value) {
    const url = text(value);
    if (url.startsWith("/") && !url.startsWith("//")) return url;
    return safeHttpUrl(url);
  }

  function normalizeExternalLink(item) {
    if (!item || typeof item !== "object") return null;
    const url = safeHttpUrl(item.url);
    if (!url) return null;
    return { type: text(item.type).toLowerCase() || "web", label: text(item.label), url };
  }

  function getAdditionalLinks(place) {
    const meta = metadata(place);
    const raw = Array.isArray(place?.external_links)
      ? place.external_links
      : (Array.isArray(meta.external_links) ? meta.external_links : []);
    const website = getWebsite(place);
    const mapUrl = getMapUrl(place);
    const seen = new Set();
    const priority = { prachinlife_vip: 0, official_website: 1, facebook: 2, wongnai: 3, google_maps: 4, web: 5, osm: 99 };
    return raw.map(normalizeExternalLink).filter(Boolean).filter((item) => {
      if (item.type === "osm" || /openstreetmap\.org/i.test(item.url)) return false;
      if (item.url === website || item.url === mapUrl || seen.has(item.url)) return false;
      seen.add(item.url);
      return true;
    }).sort((a, b) => (priority[a.type] ?? 50) - (priority[b.type] ?? 50));
  }

  function getBestAdditionalLink(place) {
    const vip = safeVipUrl(place?.prachinlife_page_url || metadata(place).prachinlife_page_url);
    if (vip) {
      return { type: "prachinlife_vip", label: "ข้อมูลเพิ่มเติม", url: vip };
    }
    return getAdditionalLinks(place)[0] || null;
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
    const additional = getBestAdditionalLink(place);

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

    if (additional) {
      actions.push(`
        <a class="source-button place-card-action place-card-action-source"
          href="${escape(additional.url)}" target="_blank" rel="noopener noreferrer">
          🔗 ข้อมูลเพิ่มเติม
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
    safeHttpUrl,
    safeVipUrl,
    getPhone,
    getPhoneHref,
    getWebsite,
    getSourceUrl,
    getSourceName,
    getAdditionalLinks,
    getBestAdditionalLink,
    getLocationLabel,
    hasCoordinates,
    getMapUrl,
    renderActions,
    renderDataNote,
  });
})();
