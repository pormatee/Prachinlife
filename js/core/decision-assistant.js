(function (global) {
  "use strict";
  const P = global.PrachinLife = global.PrachinLife || {};
  P.core = P.core || {};

  function text(v) { return typeof v === "string" ? v.trim() : ""; }
  function categories(place) {
    return Array.isArray(place?.categories)
      ? place.categories.map(x => text(x).toLowerCase()).filter(Boolean)
      : [];
  }
  function completeness(place) {
    const fields = [place?.address, place?.phone, place?.website, place?.opening_hours, place?.description];
    return fields.reduce((n, v) => n + (text(v) ? 1 : 0), 0);
  }
  function distanceKm(place) {
    for (const v of [place?._distance, place?.distance_km, place?.distance, place?.distanceKm]) {
      const n = Number(v);
      if (Number.isFinite(n) && n >= 0) return n;
    }
    return null;
  }
  function lifecycleSafe(place) {
    const v = text(place?.lifecycle).toLowerCase();
    return !["closed", "inactive", "removed", "permanently_closed"].includes(v);
  }
  function categoryGroup(place) {
    const direct = text(place?.main_category).toLowerCase();
    if (direct) return direct;
    const category = text(place?.category).toLowerCase();
    if (category) {
      if (["restaurant", "cafe", "fast_food", "food_court"].includes(category)) return "eat";
      return category;
    }
    const set = new Set(categories(place));
    if ([...set].some(x => ["vegetarian", "vegan", "jay"].includes(x))) return "vegetarian";
    if ([...set].some(x => ["restaurant", "cafe", "fast_food", "food_court"].includes(x))) return "eat";
    if ([...set].some(x => ["go", "travel", "tourism", "attraction", "temple", "park", "nature"].includes(x) || x.startsWith("tourism:"))) return "go";
    if ([...set].some(x => ["service", "hospital", "clinic", "pharmacy", "bank", "atm", "fuel", "school", "laundry", "car_repair"].includes(x) || x.startsWith("healthcare:"))) return "service";
    if ([...set].some(x => x === "shopping" || x === "shop" || x.startsWith("shop:"))) return "shopping";
    return "other";
  }
  function decisionReasons(place, distance, complete) {
    const reasons = [];
    if (distance !== null) {
      if (distance <= 3) reasons.push("อยู่ใกล้คุณ");
      else if (distance <= 10) reasons.push("เดินทางไม่ไกล");
    }
    const contactSignals = [text(place?.phone), text(place?.website), text(place?.opening_hours)].filter(Boolean).length;
    if (contactSignals >= 2) reasons.push("มีข้อมูลติดต่อและเวลาให้เช็กก่อนเดินทาง");
    else if (complete >= 3) reasons.push("มีรายละเอียดช่วยตัดสินใจค่อนข้างครบ");
    else if (text(place?.address)) reasons.push("มีข้อมูลตำแหน่งช่วยวางแผนการเดินทาง");
    if (!reasons.length) reasons.push("มีข้อมูลสถานที่ที่ผ่านเข้าระบบ PrachinLife");
    return reasons.slice(0, 2);
  }
  function scorePlace(place, options = {}) {
    if (!place || !lifecycleSafe(place)) return null;
    let score = 0;
    const d = distanceKm(place);
    if (d !== null) score += Math.max(0, 45 - Math.min(d, 30) * 1.5);
    const c = completeness(place);
    score += c * 5;
    if (text(place?.real_image) || text(place?.image_url)) score += 3;
    if (text(place?.phone)) score += 2;
    if (text(place?.website)) score += 2;
    if (text(place?.opening_hours)) score += 3;
    const wanted = text(options.category).toLowerCase();
    const group = categoryGroup(place);
    if (wanted && (group === wanted || text(place?.category).toLowerCase() === wanted || categories(place).includes(wanted))) score += 12;
    return { place, score, reasons: decisionReasons(place, d, c), distance_km: d, completeness: c, category_group: group };
  }
  function deterministicSort(results) {
    return [...results].sort((a,b) =>
      (b.score-a.score) ||
      String(a.place?.title||a.place?.name||"").localeCompare(String(b.place?.title||b.place?.name||""), "th") ||
      String(a.place?.id||"").localeCompare(String(b.place?.id||""))
    );
  }
  function diversify(results, options = {}) {
    const limit = Number.isFinite(options.limit) ? options.limit : 8;
    const wanted = text(options.category).toLowerCase();
    if (wanted || options.diversity === false) return deterministicSort(results).slice(0, limit);
    const maxPerCategory = Number.isFinite(options.maxPerCategory) ? Math.max(1, Math.floor(options.maxPerCategory)) : 2;
    const ranked = deterministicSort(results);
    const selected = [], deferred = [], counts = new Map();
    for (const result of ranked) {
      const group = result.category_group || "other";
      const used = counts.get(group) || 0;
      if (used < maxPerCategory && selected.length < limit) {
        selected.push(result); counts.set(group, used + 1);
      } else deferred.push(result);
    }
    for (const result of deferred) {
      if (selected.length >= limit) break;
      selected.push(result);
    }
    return selected;
  }
  function recommend(places, options = {}) {
    return diversify((Array.isArray(places) ? places : []).map(p => scorePlace(p, options)).filter(Boolean), options);
  }
  function reasonText(result) { return result?.reasons?.join(" • ") || ""; }
  P.core.decisionAssistant = Object.freeze({ scorePlace, recommend, reasonText, lifecycleSafe, categoryGroup, diversify });
})(window);
