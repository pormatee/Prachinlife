window.PrachinLife = window.PrachinLife || {};
window.PrachinLife.modules = window.PrachinLife.modules || {};
window.PrachinLife.modules.vegetarian =
  window.PrachinLife.modules.vegetarian || {};

window.PrachinLife.modules.vegetarian.TH_PROVINCES = [
  "กรุงเทพมหานคร",
  "กระบี่",
  "กาญจนบุรี",
  "กาฬสินธุ์",
  "กำแพงเพชร",
  "ขอนแก่น",
  "จันทบุรี",
  "ฉะเชิงเทรา",
  "ชลบุรี",
  "ชัยนาท",
  "ชัยภูมิ",
  "ชุมพร",
  "เชียงราย",
  "เชียงใหม่",
  "ตรัง",
  "ตราด",
  "ตาก",
  "นครนายก",
  "นครปฐม",
  "นครพนม",
  "นครราชสีมา",
  "นครศรีธรรมราช",
  "นครสวรรค์",
  "นนทบุรี",
  "นราธิวาส",
  "น่าน",
  "บึงกาฬ",
  "บุรีรัมย์",
  "ปทุมธานี",
  "ประจวบคีรีขันธ์",
  "ปราจีนบุรี",
  "ปัตตานี",
  "พระนครศรีอยุธยา",
  "พะเยา",
  "พังงา",
  "พัทลุง",
  "พิจิตร",
  "พิษณุโลก",
  "เพชรบุรี",
  "เพชรบูรณ์",
  "แพร่",
  "ภูเก็ต",
  "มหาสารคาม",
  "มุกดาหาร",
  "แม่ฮ่องสอน",
  "ยโสธร",
  "ยะลา",
  "ร้อยเอ็ด",
  "ระนอง",
  "ระยอง",
  "ราชบุรี",
  "ลพบุรี",
  "ลำปาง",
  "ลำพูน",
  "เลย",
  "ศรีสะเกษ",
  "สกลนคร",
  "สงขลา",
  "สตูล",
  "สมุทรปราการ",
  "สมุทรสงคราม",
  "สมุทรสาคร",
  "สระแก้ว",
  "สระบุรี",
  "สิงห์บุรี",
  "สุโขทัย",
  "สุพรรณบุรี",
  "สุราษฎร์ธานี",
  "สุรินทร์",
  "หนองคาย",
  "หนองบัวลำภู",
  "อ่างทอง",
  "อำนาจเจริญ",
  "อุดรธานี",
  "อุตรดิตถ์",
  "อุทัยธานี",
  "อุบลราชธานี"
];

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

    button.textContent =
      active
        ? "✓ ใกล้ฉัน"
        : "📍 ใกล้ฉัน";
  }
};

window.PrachinLife.modules.vegetarian.getProvinces = function () {
  return [
    ...window.PrachinLife.modules.vegetarian.TH_PROVINCES
  ];
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

    result =
      result
        .filter(place => window.PrachinLife.core.placeCard.isNearMeEligible(place))
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

    const getQualityScore = place => {

      const metadata =
        place?.metadata || {};

      let score = 0;

      if (
        metadata.show_in_primary_directory
        === true
      ) {
        score += 100;
      }

      if (
        metadata.display_tier
        === "dedicated"
      ) {
        score += 80;
      }

      else if (
        metadata.display_tier
        === "named_candidate"
      ) {
        score += 50;
      }

      else if (
        metadata.display_tier
        === "option_available"
      ) {
        score += 20;
      }

      if (
        metadata.diet_vegetarian
        === "yes"
      ) {
        score += 20;
      }

      if (
        metadata.diet_vegan
        === "yes"
      ) {
        score += 20;
      }

      return score;
    };

    result.sort(
      (a, b) => {

        const scoreDiff =
          getQualityScore(b)
          -
          getQualityScore(a);

        if (scoreDiff !== 0) {
          return scoreDiff;
        }

        return compareTitle(a, b);
      }
    );
  }

  return result;
};

window.PrachinLife.modules.vegetarian.bindProvinceEvents = function (
  onProvinceSelect
) {
  const select =
    document.getElementById(
      "vegetarianProvinceSelect"
    );

  if (
    !select
    ||
    typeof onProvinceSelect !== "function"
  ) {
    return;
  }

  select.addEventListener(
    "change",
    () => {
      onProvinceSelect(
        select.value || "all"
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
  return (
    window.PrachinLife.core.placeCard.getLocationLabel(
      place
    )
    || "ไม่ระบุพื้นที่"
  );
};


window.PrachinLife.modules.vegetarian.getUserStatus = function (
  place
) {
  const metadata =
    place?.metadata || {};

  const displayTier =
    metadata.display_tier || "";


  if (window.PrachinLife.core.placeCard.isPendingHuman(place)) {
    return {
      label: "รอการยืนยันเพิ่มเติม",
      className: "is-pending-human",
    };
  }

const verified =
    metadata.verified === true;

  if (
    displayTier === "dedicated"
    &&
    verified
  ) {
    return {
      label: "มีหลักฐานว่าเป็นร้านเจ / มังสวิรัติ",
      className: "is-confirmed",
    };
  }

  if (displayTier === "dedicated") {
    return {
      label: "พบข้อมูลว่าเป็นร้านเจ / มังสวิรัติ",
      className: "is-found",
    };
  }

  if (displayTier === "named_candidate") {
    return {
      label: "พบข้อมูลที่บ่งชี้ว่าเกี่ยวกับเจ / มังสวิรัติ",
      className: "is-candidate",
    };
  }

  return {
    label: "มีข้อมูลอาหารเจ / มังสวิรัติ",
    className: "is-found",
  };
};


window.PrachinLife.modules.vegetarian.renderCard = function (
  place
) {
  const detail =
    window.PrachinLife.core.placeDetail.getDetail(
      place
    );

  const title =
    window.PrachinLife.core.escapeHtml(
      detail.title || "ไม่ระบุชื่อร้าน"
    );

  const distance =
    Number.isFinite(place?._distance)
      ? window.PrachinLife.core.formatDistance(
          place._distance
        )
      : "";

  const status =
    window.PrachinLife.modules.vegetarian.getUserStatus(
      place
    );


  return `
    <article class="promotion-card eat-card vegetarian-card" data-place-id="${window.PrachinLife.core.escapeAttribute(place?.id || "")}" data-v2-place-id="${window.PrachinLife.core.escapeAttribute(place?.metadata?.v2_place_id || "")}">

      <div class="promotion-image-wrap eat-image-wrap">

        ${window.PrachinLife.core.placeImage.renderPlaceImage(
          place,
          "vegetarian",
          place?.title || "ร้านเจ / มังสวิรัติ"
        )}

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
                <span>จากตำแหน่งของคุณ</span>
              </div>
            `
            : ""
        }

        <h3 class="promotion-title">
          ${title}
        </h3>

        ${window.PrachinLife.core.placeDetail.renderFacts(
          place
        )}

        <p
          class="vegetarian-status ${window.PrachinLife.core.escapeAttribute(
            status.className
          )}"
        >
          ${window.PrachinLife.core.escapeHtml(
            status.label
          )}
        </p>

        ${window.PrachinLife.core.placeCard.renderPendingHumanNotice(place)}
        ${window.PrachinLife.core.placeCard.renderDataNote(place)}

        ${window.PrachinLife.core.placeCard.renderActions(place)}

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
