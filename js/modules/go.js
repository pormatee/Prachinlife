window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.modules = window.PrachinLife.modules || {};
window.PrachinLife.modules.go =
  window.PrachinLife.modules.go || {};

window.PrachinLife.modules.go.getProvince = function (
  place
) {
  return (
    place?.location?.province
    || ""
  );
};

window.PrachinLife.modules.go.getPrimaryPlaces = function (
  places,
  currentProvince
) {
  return (places || []).filter(
    place => {
      const metadata =
        place?.metadata || {};

      if (
        metadata.show_in_primary_directory
        !== true
      ) {
        return false;
      }

      if (!currentProvince) {
        return true;
      }

      return (
        window.PrachinLife.modules.go.getProvince(
          place
        )
        ===
        currentProvince
      );
    }
  );
};

window.PrachinLife.modules.go.getLocationLabel = function (
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


window.PrachinLife.modules.go.renderCard = function (
  place
) {
  const title =
    window.PrachinLife.core.escapeHtml(
      place?.title
      || "ไม่ระบุชื่อสถานที่"
    );

  const categoryLabel =
    window.PrachinLife.core.escapeHtml(
      place?.metadata?.category_label
      || "สถานที่น่าสนใจ"
    );

  const location =
    window.PrachinLife.core.escapeHtml(
      window.PrachinLife.modules.go.getLocationLabel(
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

  const verified =
    place?.metadata?.verified === true;

  const statusLabel =
    verified
      ? "มีข้อมูลสถานที่ที่ผ่านการยืนยันแหล่งข้อมูล"
      : "มีข้อมูลสถานที่จากแหล่งข้อมูลสาธารณะ";

  const mapUrl =
    window.PrachinLife.core.buildMapUrl(
      place
    );

  const sourceName =
    window.PrachinLife.core.escapeHtml(
      place?.metadata?.source_name
      || place?.source
      || "แหล่งข้อมูลสาธารณะ"
    );

  const sourceUrl =
    place?.source_url
    || place?.metadata?.source_url
    || "";

  return `
    <article class="promotion-card eat-card go-v1-card">

      <div class="promotion-image-wrap eat-image-wrap">

        <div class="image-placeholder eat-placeholder">
          🗺️
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

        <p class="go-v1-status">
          ${window.PrachinLife.core.escapeHtml(
            statusLabel
          )}
        </p>

        <p class="promotion-description go-v1-data-note">
          แหล่งข้อมูล: ${sourceName}
          · ควรตรวจสอบรายละเอียดล่าสุดก่อนเดินทาง
        </p>

        <div class="promotion-actions go-v1-actions">

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
            sourceUrl
              ? `
                <a
                  class="source-button go-v1-source-link"
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


window.PrachinLife.modules.go.renderPlaces = function (
  places
) {
  const list =
    document.getElementById(
      "goList"
    );

  const emptyState =
    document.getElementById(
      "goEmptyState"
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

    return;
  }

  if (emptyState) {
    emptyState.classList.add(
      "hidden"
    );
  }

  list.innerHTML =
    safePlaces
      .map(
        window.PrachinLife.modules.go.renderCard
      )
      .join("");
};
