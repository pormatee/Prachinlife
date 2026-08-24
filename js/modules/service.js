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
  return (
    window.PrachinLife.core.placeCard.getLocationLabel(
      place
    )
    || "ไม่ระบุพื้นที่"
  );
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
  const detail =
    window.PrachinLife.core.placeDetail.getDetail(
      place,
      "ปราจีนบุรี"
    );

  const title =
    window.PrachinLife.core.escapeHtml(
      detail.title || "ไม่ระบุชื่อบริการ"
    );

  const categoryLabel =
    window.PrachinLife.core.escapeHtml(
      window.PrachinLife.modules.service
        .CATEGORY_LABELS[
          place?.category
        ]
      || "บริการ"
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
    <article class="promotion-card eat-card service-v1-card" data-place-id="${window.PrachinLife.core.escapeAttribute(place?.id || "")}" data-v2-place-id="${window.PrachinLife.core.escapeAttribute(place?.metadata?.v2_place_id || "")}">

      <div class="promotion-image-wrap eat-image-wrap">

        ${window.PrachinLife.core.placeImage.renderPlaceImage(
          place,
          "service",
          place?.title || "บริการ"
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
