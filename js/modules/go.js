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
  return (
    window.PrachinLife.core.placeCard.getLocationLabel(
      place
    )
    || "ไม่ระบุพื้นที่"
  );
};


window.PrachinLife.modules.go.renderCard = function (
  place
) {
  const detail =
    window.PrachinLife.core.placeDetail.getDetail(
      place,
      "ปราจีนบุรี"
    );

  const title =
    window.PrachinLife.core.escapeHtml(
      detail.title || "ไม่ระบุชื่อสถานที่"
    );

  const categoryLabel =
    window.PrachinLife.core.escapeHtml(
      place?.metadata?.category_label
      || "สถานที่น่าสนใจ"
    );

  const distance =
    Number.isFinite(
      place?._distance
    )
      ? window.PrachinLife.core.formatDistance(
          place._distance
        )
      : "";


  return `
    <article class="promotion-card eat-card go-v1-card" data-place-id="${window.PrachinLife.core.escapeAttribute(place?.id || "")}" data-v2-place-id="${window.PrachinLife.core.escapeAttribute(place?.metadata?.v2_place_id || "")}">

      <div class="promotion-image-wrap eat-image-wrap">

        ${window.PrachinLife.core.placeImage.renderPlaceImage(
          place,
          "go",
          place?.title || "สถานที่"
        )}

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

        ${window.PrachinLife.core.placeDetail.renderFacts(
          place,
          "ปราจีนบุรี"
        )}


        ${window.PrachinLife.core.placeCard.renderDataNote(place)}

        ${window.PrachinLife.core.placeCard.renderActions(place)}

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
