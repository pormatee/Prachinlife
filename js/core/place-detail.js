(() => {
  "use strict";
  window.PrachinLife = window.PrachinLife || {};
  window.PrachinLife.core = window.PrachinLife.core || {};

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

  function getDetail(place, fallbackProvince = "") {
    const card = window.PrachinLife.core.placeCard;
    return Object.freeze({
      title: clean(place?.title || place?.name) || "ไม่ระบุชื่อสถานที่",
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

  window.PrachinLife.core.placeDetail = Object.freeze({
    getOpeningHours,
    getDescription,
    getDetail,
    renderFacts,
  });
})();
