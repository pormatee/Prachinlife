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

window.PrachinLife.modules.go.renderCard = function (
  place
) {
  const title =
    window.PrachinLife.core.escapeHtml(
      place?.title || "ไม่ระบุชื่อสถานที่"
    );

  const categoryLabel =
    window.PrachinLife.core.escapeHtml(
      place?.metadata?.category_label
      || "สถานที่น่าสนใจ"
    );

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
          📍
        </div>

        <span class="source-pill">
          ${categoryLabel}
        </span>

      </div>

      <div class="promotion-body">

        <h3 class="promotion-title">
          ${title}
        </h3>

        <p class="promotion-description">
          📍 ${window.PrachinLife.core.escapeHtml(
            window.PrachinLife.modules.go.getProvince(
              place
            )
          )}
        </p>

        <p class="promotion-description">
          ข้อมูลจาก OpenStreetMap
          โปรดตรวจสอบข้อมูลล่าสุดก่อนเดินทาง
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
