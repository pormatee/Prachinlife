(function (global) {
  "use strict";
  const P = global.PrachinLife = global.PrachinLife || {};
  P.core = P.core || {};

  function text(v) { return typeof v === "string" ? v.trim() : ""; }
  function categories(place) {
    return Array.isArray(place?.categories) ? place.categories.map(x => text(x).toLowerCase()).filter(Boolean) : [];
  }
  function completeness(place) {
    const fields = [place?.address, place?.phone, place?.website, place?.opening_hours, place?.description];
    return fields.reduce((n, v) => n + (text(v) ? 1 : 0), 0);
  }
  function distanceKm(place) {
    for (const v of [place?._distance, place?.distance_km, place?.distance, place?.distanceKm]) {
      const n = Number(v); if (Number.isFinite(n) && n >= 0) return n;
    }
    return null;
  }
  function lifecycleSafe(place) {
    const v = text(place?.lifecycle).toLowerCase();
    return !["closed", "inactive", "removed", "permanently_closed"].includes(v);
  }
  function scorePlace(place, options = {}) {
    if (!place || !lifecycleSafe(place)) return null;
    let score = 0; const reasons = [];
    const d = distanceKm(place);
    if (d !== null) {
      score += Math.max(0, 45 - Math.min(d, 30) * 1.5);
      if (d <= 3) reasons.push("อยู่ใกล้คุณ");
      else if (d <= 10) reasons.push("เดินทางไม่ไกล");
    }
    const c = completeness(place);
    score += c * 5;
    if (c >= 3) reasons.push("มีข้อมูลช่วยตัดสินใจค่อนข้างครบ");
    if (text(place?.real_image) || text(place?.image_url)) score += 3;
    if (text(place?.phone)) score += 2;
    if (text(place?.website)) score += 2;
    if (text(place?.opening_hours)) score += 3;
    const wanted = text(options.category).toLowerCase();
    if (wanted && (place?.main_category === wanted || place?.category === wanted || categories(place).includes(wanted))) score += 12;
    if (!reasons.length) reasons.push("มีข้อมูลสถานที่ที่ผ่านเข้าระบบ PrachinLife");
    return { place, score, reasons: reasons.slice(0, 2), distance_km: d, completeness: c };
  }
  function recommend(places, options = {}) {
    return (Array.isArray(places) ? places : [])
      .map(p => scorePlace(p, options)).filter(Boolean)
      .sort((a,b) => (b.score-a.score) || String(a.place?.title||a.place?.name||"").localeCompare(String(b.place?.title||b.place?.name||""), "th"))
      .slice(0, Number.isFinite(options.limit) ? options.limit : 8);
  }
  function reasonText(result) { return result?.reasons?.join(" • ") || ""; }
  P.core.decisionAssistant = Object.freeze({ scorePlace, recommend, reasonText, lifecycleSafe });
})(window);
