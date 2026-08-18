window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.modules = window.PrachinLife.modules || {};
window.PrachinLife.modules.vegetarian =
  window.PrachinLife.modules.vegetarian || {};

window.PrachinLife.modules.vegetarian.getProvince = function (
  place
) {
  return (
    place?.location?.province
    || ""
  );
};

window.PrachinLife.modules.vegetarian.updateNearMeState = function (
  active
) {
  const button =
    document.getElementById(
      "vegetarianNearMeBtn"
    );

  if (button) {
    button.classList.toggle(
      "active",
      active
    );
  }
};

window.PrachinLife.modules.vegetarian.updateProvinceButtons = function (
  currentProvince
) {
  document
    .querySelectorAll(
      "[data-vegetarian-province]"
    )
    .forEach(
      button => {
        button.classList.toggle(
          "active",
          button.dataset
            .vegetarianProvince
            ===
            currentProvince
        );
      }
    );
};

window.PrachinLife.modules.vegetarian.getProvinces = function (
  places
) {
  return [
    ...new Set(
      (places || [])
        .map(
          window.PrachinLife.modules.vegetarian.getProvince
        )
        .filter(Boolean)
    )
  ].sort(
    (a, b) =>
      String(a).localeCompare(
        String(b),
        "th"
      )
  );
};

window.PrachinLife.modules.vegetarian.buildProvinceButtonsHtml = function (
  provinces
) {
  const buttons = [
    `
      <button
        type="button"
        class="filter-button active"
        data-vegetarian-province="all"
      >
        ทุกจังหวัด
      </button>
    `
  ];

  for (const province of provinces || []) {
    buttons.push(
      `
        <button
          type="button"
          class="filter-button"
          data-vegetarian-province="${window.PrachinLife.core.escapeAttribute(province)}"
        >
          ${window.PrachinLife.core.escapeHtml(province)}
        </button>
      `
    );
  }

  return buttons.join("");
};

window.PrachinLife.modules.vegetarian.filterAndSortPlaces = function (
  places,
  currentProvince,
  userLocation,
  calculateDistance,
  compareDistance,
  compareTitle
) {
  let result =
    (places || []).filter(
      place => {
        if (currentProvince === "all") {
          return true;
        }

        return (
          window.PrachinLife.modules.vegetarian.getProvince(
            place
          )
          ===
          currentProvince
        );
      }
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
      .sort(
        compareDistance
      );
  }

  else {
    result.sort(
      compareTitle
    );
  }

  return result;
};

window.PrachinLife.modules.vegetarian.bindProvinceEvents = function (
  onProvinceSelect
) {
  document
    .querySelectorAll(
      "[data-vegetarian-province]"
    )
    .forEach(
      button => {
        button.addEventListener(
          "click",
          () => {
            const province =
              button.dataset
                .vegetarianProvince
              || "all";

            if (
              typeof onProvinceSelect
              === "function"
            ) {
              onProvinceSelect(
                province
              );
            }
          }
        );
      }
    );
};

window.PrachinLife.modules.vegetarian.bindMainEvents = function (
  onNearMe,
  onProvinceSelect
) {
  const nearMeBtn =
    document.getElementById(
      "vegetarianNearMeBtn"
    );

  if (
    nearMeBtn
    &&
    typeof onNearMe === "function"
  ) {
    nearMeBtn.addEventListener(
      "click",
      onNearMe
    );
  }

  window.PrachinLife.modules.vegetarian.bindProvinceEvents(
    onProvinceSelect
  );
};

window.PrachinLife.modules.vegetarian.getLocationLabel = function (
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
    return unique.join(
      " · "
    );
  }

  const latitude =
    Number(
      location.latitude
    );

  const longitude =
    Number(
      location.longitude
    );

  if (
    Number.isFinite(latitude)
    &&
    Number.isFinite(longitude)
  ) {
    return "ดูตำแหน่งจากแผนที่";
  }

  return "ไม่ระบุพื้นที่";
};

window.PrachinLife.modules.vegetarian.renderCard = function (
  place
) {
  const title =
    window.PrachinLife.core.escapeHtml(
      place?.title
      || "ไม่ระบุชื่อร้าน"
    );

  const location =
    window.PrachinLife.core.escapeHtml(
      window.PrachinLife.modules.vegetarian.getLocationLabel(
        place
      )
    );

  const distance =
    Number.isFinite(
      place?._distance
    )
      ? window.PrachinLife.core.formatDistance(
          place._distance
        )
      : "";

  const openingHours =
    place?.metadata?.opening_hours
      ? window.PrachinLife.core.escapeHtml(
          place.metadata.opening_hours
        )
      : "";

  const displayTier =
    place?.metadata?.display_tier
    || "";

  const tierLabel =
    displayTier === "dedicated"
      ? "✓ ร้านเฉพาะทาง"
      : displayTier === "named_candidate"
        ? "◌ พบจากชื่อร้าน"
        : "";

  const mapUrl =
    window.PrachinLife.core.buildMapUrl(
      place
    );

  const sourceUrl =
    place?.source_url
    ||
    place?.metadata?.source_url
    ||
    "";

  return `
    <article class="promotion-card eat-card">

      <div class="promotion-image-wrap eat-image-wrap">

        <div class="image-placeholder eat-placeholder">
          🥬
        </div>

        <span class="source-pill">
          เจ / มังสวิรัติ
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
              </div>
            `
            : ""
        }

        <h3 class="promotion-title">
          ${title}
        </h3>

        <p class="promotion-description">
          🥬 เจ / มังสวิรัติ
        </p>

        ${
          tierLabel
            ? `
              <p class="promotion-description vegetarian-tier">
                ${window.PrachinLife.core.escapeHtml(
                  tierLabel
                )}
              </p>
            `
            : ""
        }

        <p class="promotion-description">
          📍 ${location}
        </p>

        ${
          openingHours
            ? `
              <p class="promotion-description">
                🕒 ${openingHours}
              </p>
            `
            : ""
        }

        <p class="promotion-description">
          ข้อมูลจาก OpenStreetMap
          โปรดตรวจสอบรายละเอียดล่าสุดกับร้านก่อนเดินทาง
        </p>

        <div class="promotion-actions">

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
                  เปิดแผนที่ →
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
                  ดูแหล่งข้อมูล →
                </a>
              `
              : ""
          }

        </div>

      </div>

    </article>
  `;
};

window.PrachinLife.modules.vegetarian.renderPlaces = function (
  places,
  currentPage,
  pageSize
) {
  const list =
    document.getElementById(
      "vegetarianList"
    );

  const loadMoreBtn =
    document.getElementById(
      "vegetarianLoadMoreBtn"
    );

  if (!list) {
    return;
  }

  const safePlaces =
    places || [];

  if (safePlaces.length === 0) {
    list.innerHTML = "";

    window.PrachinLife.ui.showElement(
      "vegetarianEmptyState"
    );

    if (loadMoreBtn) {
      loadMoreBtn.classList.add(
        "hidden"
      );
    }

    return;
  }

  window.PrachinLife.ui.hideElement(
    "vegetarianEmptyState"
  );

  const visibleCount =
    currentPage * pageSize;

  const visibleItems =
    safePlaces.slice(
      0,
      visibleCount
    );

  list.innerHTML =
    visibleItems
      .map(
        window.PrachinLife.modules.vegetarian.renderCard
      )
      .join("");

  if (loadMoreBtn) {
    loadMoreBtn.classList.toggle(
      "hidden",
      visibleCount >= safePlaces.length
    );
  }
};
