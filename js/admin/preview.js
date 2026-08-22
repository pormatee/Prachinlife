(() => {
  "use strict";

  window.PrachinLifeAdminPreview = window.PrachinLifeAdminPreview || {};

  const text = value => String(value ?? "").trim();
  const esc = value => String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

  function categories(place) {
    return Array.isArray(place?.categories) ? place.categories : [];
  }

  function categoryLabel(place) {
    const labels = {
      restaurant: "ร้านอาหาร", cafe: "คาเฟ่", fast_food: "อาหารจานด่วน",
      vegetarian: "เจ / มังสวิรัติ", vegan: "เจ / มังสวิรัติ", jay: "เจ / มังสวิรัติ",
      attraction: "สถานที่น่าเที่ยว", tourism: "สถานที่น่าเที่ยว", temple: "วัด / ศาสนสถาน",
      museum: "พิพิธภัณฑ์", park: "สวน / ธรรมชาติ",
      fuel: "ปั๊มน้ำมัน", pharmacy: "ร้านยา", clinic: "คลินิก", car_repair: "ซ่อมรถ", laundry: "ซักรีด"
    };
    for (const value of categories(place)) if (labels[value]) return labels[value];
    return categories(place)[0] || "สถานที่";
  }

  function fallbackGroup(place) {
    const values = new Set(categories(place));
    if (["vegetarian", "vegan", "jay"].some(v => values.has(v))) return "vegetarian";
    if (["fuel", "pharmacy", "clinic", "car_repair", "laundry"].some(v => values.has(v))) return "service";
    if (["attraction", "tourism", "temple", "museum", "park"].some(v => values.has(v))) return "go";
    return "eat";
  }

  function imageHtml(place) {
    const direct = text(place?.real_image || place?.image_url || place?.image);
    const group = fallbackGroup(place);
    const master = `assets/images/place-masters/${group === "go" ? "go" : group}-master.png`;
    if (direct) {
      return `<img class="promotion-image place-card-image" src="${esc(direct)}" alt="${esc(place?.name || "สถานที่")}" loading="lazy" data-master-image="${esc(master)}" onerror="this.onerror=null;this.src=this.dataset.masterImage;">`;
    }
    const imageContract = window.PrachinLife?.core?.placeImage;
    if (imageContract && typeof imageContract.renderPlaceImage === "function") {
      return imageContract.renderPlaceImage(place, group, place?.name || "สถานที่");
    }
    return `<img class="promotion-image place-card-image" src="${esc(master)}" alt="${esc(place?.name || "สถานที่")}" loading="lazy">`;
  }

  function applyChanges(basePlace, changes) {
    const next = { ...(basePlace || {}) };
    for (const change of (changes || [])) {
      if (!change || !change.field_name) continue;
      const value = change.value;
      switch (change.field_name) {
        case "canonical_name": next.name = value; break;
        case "address_text": next.address = value; break;
        case "location":
          if (value && typeof value === "object") {
            next.latitude = value.latitude;
            next.longitude = value.longitude;
          }
          break;
        case "real_image": next.real_image = value; next.image_url = value; break;
        default: next[change.field_name] = value;
      }
    }
    return next;
  }

  function localityLabel(place) {
    const parts = [place?.subdistrict, place?.district, place?.province]
      .map(text)
      .filter(Boolean);
    return [...new Set(parts)].join(" · ");
  }

  function locationLabel(place) {
    return text(place?.address || place?.area) || localityLabel(place) || "ยังไม่มีข้อมูลพื้นที่";
  }

  function detailRows(place) {
    const rows = [];
    const add = (label, value, kind = "text") => {
      const cleaned = text(value);
      if (!cleaned) return;
      rows.push(`<div class="admin-preview-detail-row"><span>${esc(label)}</span><strong class="${kind === "url" ? "is-url" : ""}">${esc(cleaned)}</strong></div>`);
    };
    add("อำเภอ", place?.district);
    add("ตำบล", place?.subdistrict);
    add("พื้นที่ / จุดสังเกต", place?.area);
    add("โทรศัพท์", place?.phone);
    add("เว็บไซต์", place?.website, "url");
    return rows.join("");
  }

  function actionHtml(place) {
    const actions = [];
    const lat = Number(place?.latitude), lng = Number(place?.longitude);
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      actions.push(`<span class="admin-preview-action">📍 เปิดแผนที่</span>`);
    }
    if (text(place?.phone)) actions.push(`<span class="admin-preview-action">📞 โทร</span>`);
    if (text(place?.website)) actions.push(`<span class="admin-preview-action">🌐 เว็บไซต์</span>`);
    if (text(place?.source_url)) actions.push(`<span class="admin-preview-action">ดูแหล่งข้อมูล</span>`);
    return actions.join("");
  }

  function renderCard(place, options = {}) {
    const caption = options.caption ? `<div class="admin-preview-caption">${esc(options.caption)}</div>` : "";
    const opening = text(place?.opening_hours)
      ? `<p class="admin-preview-line">🕒 ${esc(place.opening_hours)}</p>` : "";
    const description = text(place?.description)
      ? `<div class="admin-preview-description"><span>รายละเอียด</span><p>${esc(place.description)}</p></div>` : "";
    const locality = localityLabel(place);
    const localityLine = locality && locality !== locationLabel(place)
      ? `<p class="admin-preview-line admin-preview-locality">🏘 ${esc(locality)}</p>` : "";
    const details = detailRows(place);
    const actions = actionHtml(place);
    return `${caption}<article class="admin-user-preview-card">
      <div class="admin-user-preview-media">${imageHtml(place)}<span class="admin-category-pill">${esc(categoryLabel(place))}</span></div>
      <div class="admin-user-preview-body">
        <h3>${esc(place?.name || "ไม่ระบุชื่อ")}</h3>
        <p class="admin-preview-line">📍 ${esc(locationLabel(place))}</p>
        ${localityLine}${opening}
        ${details ? `<div class="admin-preview-detail-grid">${details}</div>` : ""}
        ${description}
        ${actions ? `<div class="admin-preview-actions">${actions}</div>` : ""}
      </div>
    </article>`;
  }

  Object.assign(window.PrachinLifeAdminPreview, {
    applyChanges,
    renderCard,
    categoryLabel,
    fallbackGroup
  });
})();
