window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.modules =
  window.PrachinLife.modules || {};

window.PrachinLife.modules.service =
  window.PrachinLife.modules.service || {};


window.PrachinLife.modules.service.CATEGORY_LABELS = {
  pharmacy: "ร้านยา",
  clinic: "คลินิก",
  fuel: "ปั๊มน้ำมัน",
  car_repair: "ซ่อมรถ",
  laundry: "ซักรีด",
};


window.PrachinLife.modules.service.getLocationLabel = function (
  place
) {
  const location =
    place?.location || {};

  const parts = [
    location.subdistrict,
    location.district,
    location.province,
  ].filter(Boolean);

  const unique = [
    ...new Set(parts)
  ];

  if (unique.length > 0) {
    return unique.join(" · ");
  }

  return "ไม่ระบุพื้นที่";
};


window.PrachinLife.modules.service.filterAndSort = function (
  places,
  category,
  userLocation,
  calculateDistance,
  compareDistance,
  compareTitle
) {
  let result =
    (places || []).filter(
      place =>
        category === "all"
        ||
        place?.category === category
    );

  if (userLocation) {
    result = result
      .map(
        place => ({
          ...place,
          _distance:
            calculateDistance(place),
        })
      )
      .sort(compareDistance);
  }

  else {
    result.sort(compareTitle);
  }

  return result;
};


window.PrachinLife.modules.service.renderCard = function (
  place
) {
  const title =
    window.PrachinLife.core.escapeHtml(
      place?.title
      || "ไม่ระบุชื่อบริการ"
    );

  const categoryLabel =
    window.PrachinLife.core.escapeHtml(
      window.PrachinLife.modules.service
        .CATEGORY_LABELS[
          place?.category
        ]
      || "บริการ"
    );

  const location =
    window.PrachinLife.core.escapeHtml(
      window.PrachinLife.modules.service
        .getLocationLabel(place)
    );

  const distance =
    Number.isFinite(
      place?._distance
    )
      ? window.PrachinLife.core.formatDistance(
          place._distance
        )
      : "";

  const metadata =
    place?.metadata || {};

  const openingHours =
    metadata.opening_hours
      ? window.PrachinLife.core.escapeHtml(
          metadata.opening_hours
        )
      : "";

  const phoneRaw =
    metadata.phone || "";

  const phoneHref =
    String(phoneRaw).replace(
      /[^+\d]/g,
      ""
    );

  let websiteUrl =
    metadata.website || "";

  if (
    websiteUrl
    &&
    !/^https?:\/\//i.test(
      websiteUrl
    )
  ) {
    websiteUrl =
      `https://${websiteUrl}`;
  }

  const mapUrl =
    window.PrachinLife.core.buildMapUrl(
      place
    );

  const sourceUrl =
    place?.source_url || "";

  const sourceName =
    window.PrachinLife.core.escapeHtml(
      place?.source
      || "OpenStreetMap"
    );

  return `
    <article class="promotion-card eat-card service-v1-card">

      <div class="promotion-image-wrap eat-image-wrap">

        <div class="image-placeholder eat-placeholder">
          🔧
        </div>

        <span class="source-pill">
          ${categoryLabel}
        </span>

      </div>

      <div class="promotion-body">

        ${
          distance
            ? `
              <div class="promotion-meta">
                <strong>
                  📍 ${window.PrachinLife.core.escapeHtml(
                    distance
                  )}
                </strong>

                <span>
                  จากตำแหน่งของคุณ
                </span>
              </div>
            `
            : ""
        }

        <h3 class="promotion-title">
          ${title}
        </h3>

        <p class="promotion-description">
          📍 ${location}
        </p>

        ${
          openingHours
            ? `
              <p class="promotion-description">
                🕒 เวลาเปิด: ${openingHours}
              </p>
            `
            : ""
        }

        <p class="service-v1-status">
          มีข้อมูลตำแหน่งบริการจากแหล่งข้อมูลสาธารณะ
        </p>

        <p class="promotion-description service-v1-data-note">
          แหล่งข้อมูล: ${sourceName}
          · ควรตรวจสอบรายละเอียดล่าสุดก่อนเดินทาง
        </p>

        <div class="promotion-actions service-v1-actions">

          ${
            mapUrl
              ? `
                <a
                  class="source-button"
                  href="${window.PrachinLife.core.escapeAttribute(
                    mapUrl
                  )}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  📍 เปิดแผนที่
                </a>
              `
              : ""
          }

          ${
            phoneHref
              ? `
                <a
                  class="source-button"
                  href="tel:${window.PrachinLife.core.escapeAttribute(
                    phoneHref
                  )}"
                >
                  📞 โทร
                </a>
              `
              : ""
          }

          ${
            websiteUrl
              ? `
                <a
                  class="source-button"
                  href="${window.PrachinLife.core.escapeAttribute(
                    websiteUrl
                  )}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  🌐 เว็บไซต์
                </a>
              `
              : ""
          }

          ${
            sourceUrl
              ? `
                <a
                  class="source-button"
                  href="${window.PrachinLife.core.escapeAttribute(
                    sourceUrl
                  )}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  ดูแหล่งข้อมูล
                </a>
              `
              : ""
          }

        </div>

      </div>

    </article>
  `;
};


window.PrachinLife.modules.service.renderPlaces = function (
  places,
  currentPage,
  pageSize
) {
  const list =
    document.getElementById(
      "serviceList"
    );

  const emptyState =
    document.getElementById(
      "serviceEmptyState"
    );

  const loadMoreBtn =
    document.getElementById(
      "serviceLoadMoreBtn"
    );

  if (!list) {
    return;
  }

  const safePlaces =
    places || [];

  if (safePlaces.length === 0) {
    list.innerHTML = "";

    if (emptyState) {
      emptyState.classList.remove(
        "hidden"
      );
    }

    if (loadMoreBtn) {
      loadMoreBtn.classList.add(
        "hidden"
      );
    }

    return;
  }

  if (emptyState) {
    emptyState.classList.add(
      "hidden"
    );
  }

  const visibleCount =
    currentPage * pageSize;

  list.innerHTML =
    safePlaces
      .slice(
        0,
        visibleCount
      )
      .map(
        window.PrachinLife.modules.service
          .renderCard
      )
      .join("");

  if (loadMoreBtn) {
    loadMoreBtn.classList.toggle(
      "hidden",
      visibleCount >= safePlaces.length
    );
  }
};
