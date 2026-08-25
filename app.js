"use strict";

/* =====================================================
PRACHINLIFE
app.js - Stable Rebuild + Vegetarian

รองรับ:
- แนะนำ
- ช้อปคุ้ม
- กินอะไร
- เจ / มังสวิรัติ
- ค้นหา
- ใกล้ฉัน
===================================================== */


/* =====================================================
CONFIG
===================================================== */

const DATA_URL = "promotions.json";
const V2_STAGED_PREVIEW = new URLSearchParams(window.location.search).get("v2preview") === "1";
const V2_STAGED_ROOT = "data/v2/staging/user_web";
const INDEX_URL = V2_STAGED_PREVIEW ? `${V2_STAGED_ROOT}/prachinlife_index.json` : "prachinlife_index.json";
const VEGETARIAN_URL = V2_STAGED_PREVIEW ? `${V2_STAGED_ROOT}/vegetarian_index.json` : "vegetarian_index.json";
const GO_URL = V2_STAGED_PREVIEW ? `${V2_STAGED_ROOT}/go_index.json` : "go_index.json";
const SERVICE_URL = V2_STAGED_PREVIEW ? `${V2_STAGED_ROOT}/service_index.json` : "service_index.json";

const PAGE_SIZE = 8;
const EAT_PAGE_SIZE = 8;
const VEGETARIAN_PAGE_SIZE = 8;
const SERVICE_PAGE_SIZE = 8;
const RECOMMENDED_LIMIT = 8;


/* =====================================================
STATE
===================================================== */

let allPromotions = [];
let filteredPromotions = [];

let allContent = [];

let allEatPlaces = [];
let filteredEatPlaces = [];

let allVegetarianPlaces = [];
let primaryVegetarianPlaces = [];
let filteredVegetarianPlaces = [];

let allGoPlaces = [];
let primaryGoPlaces = [];
let filteredGoPlaces = [];

let allServicePlaces = [];
let primaryServicePlaces = [];
let filteredServicePlaces = [];


let currentPage = 1;
let currentEatPage = 1;
let currentVegetarianPage = 1;
let currentServicePage = 1;

let currentMerchant = "all";
let currentType = "all";
let currentSmart = "recommended";

let currentEatType = "all";

let currentVegetarianProvince = "all";
let currentServiceCategory = "all";

let currentLocalProvince = "";

let currentMainCategory = "recommended";

let userLocation = null;

let toastTimer = null;


/* =====================================================
START
===================================================== */

document.addEventListener(
  "DOMContentLoaded",
  init
);



/* ===== PRACHINLIFE V2 DATA BRIDGE ===== */

let prachinLifeV2Places = [];
let prachinLifeV2DataStatus = "not_loaded";

async function loadPrachinLifeV2Data() {
  if (
    !window.PrachinLifeV2 ||
    typeof window.PrachinLifeV2.loadV2Places !== "function"
  ) {
    prachinLifeV2DataStatus = "adapter_missing";
    return [];
  }

  try {
    const places = await window.PrachinLifeV2.loadV2Places();
    prachinLifeV2Places = places;
    prachinLifeV2DataStatus = "ready";

    console.info(
      "[PrachinLife V2] loaded",
      places.length,
      "places"
    );

    return places;
  } catch (error) {
    prachinLifeV2Places = [];
    prachinLifeV2DataStatus = "fallback_v1";

    console.warn(
      "[PrachinLife V2] load failed; V1 remains active",
      error
    );

    return [];
  }
}

function getPrachinLifeV2Places(category = null) {
  if (!category) return [...prachinLifeV2Places];

  return prachinLifeV2Places.filter(
    (place) =>
      place.main_category === category ||
      place.category === category
  );
}

window.PrachinLifeV2Runtime = Object.freeze({
  load: loadPrachinLifeV2Data,
  getPlaces: getPrachinLifeV2Places,
  getStatus: () => prachinLifeV2DataStatus
});

/* ===== END PRACHINLIFE V2 DATA BRIDGE ===== */


/* ===== PRACHINLIFE V2 CATEGORY DATA BRIDGE ===== */

function getPreferredPlaceDataset(
  category,
  fallbackDataset = []
) {
  const supportedCategories = new Set([
    "eat",
    "vegetarian",
    "go",
    "service",
  ]);

  if (!supportedCategories.has(category)) {
    return fallbackDataset;
  }

  if (
    !window.PrachinLifeV2Runtime ||
    typeof window.PrachinLifeV2Runtime.getPlaces !== "function" ||
    typeof window.PrachinLifeV2Runtime.getStatus !== "function" ||
    window.PrachinLifeV2Runtime.getStatus() !== "ready"
  ) {
    return fallbackDataset;
  }

  const v2Places =
    window.PrachinLifeV2Runtime.getPlaces(category);

  if (!v2Places.length) {
    return fallbackDataset;
  }

  const fallbackCount = Array.isArray(fallbackDataset)
    ? fallbackDataset.length
    : 0;

  /*
   * Quality-aware rollout:
   * - If V1 has meaningful coverage, V2 must retain at least 80%.
   * - Avoid switching a mature category to only 1-2 V2 records.
   * - If there is no V1 coverage, V2 remains usable.
   */
  if (fallbackCount >= 5) {
    const coverageRatio = v2Places.length / fallbackCount;

    if (
      v2Places.length < 3 ||
      coverageRatio < 0.80
    ) {
      console.info(
        "[PrachinLife V2] smart fallback",
        category,
        {
          v2: v2Places.length,
          v1: fallbackCount,
          ratio: coverageRatio,
        }
      );

      return fallbackDataset;
    }
  }

  return v2Places;
}

function getEatDatasetV2First() {
  return getPreferredPlaceDataset(
    "eat",
    Array.isArray(allEatPlaces) ? allEatPlaces : []
  );
}

function getVegetarianDatasetV2First() {
  const primaryFallback =
    (
      typeof primaryVegetarianPlaces !== "undefined" &&
      Array.isArray(primaryVegetarianPlaces) &&
      primaryVegetarianPlaces.length
    )
      ? primaryVegetarianPlaces
      : (
          Array.isArray(allVegetarianPlaces)
            ? allVegetarianPlaces
            : []
        );

  return getPreferredPlaceDataset(
    "vegetarian",
    primaryFallback
  );
}

function getGoDatasetV2First() {
  return getPreferredPlaceDataset(
    "go",
    Array.isArray(allGoPlaces) ? allGoPlaces : []
  );
}

function getServiceDatasetV2First() {
  return getPreferredPlaceDataset(
    "service",
    Array.isArray(allServicePlaces)
      ? allServicePlaces
      : []
  );
}

/* ===== END PRACHINLIFE V2 CATEGORY DATA BRIDGE ===== */


/* ===== PRACHINLIFE V2 SEARCH + NEAR ME BRIDGE ===== */

function normalizeSearchTextV2(value) {
  return String(value || "")
    .trim()
    .toLocaleLowerCase("th-TH");
}

function searchPrachinLifeV2Places(query, category = null) {
  const normalizedQuery = normalizeSearchTextV2(query);

  const source = category
    ? getPrachinLifeV2Places(category)
    : getPrachinLifeV2Places();

  if (!normalizedQuery) {
    return [...source];
  }

  return source.filter((place) => {
    const haystack = [
      place.title,
      place.name,
      place.area,
      place.address,
      place.province,
      ...(Array.isArray(place.categories)
        ? place.categories
        : []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase("th-TH");

    return haystack.includes(normalizedQuery);
  });
}

function getPrachinLifeV2NearMe(
  userPoint,
  category = null,
  limit = 50
) {
  if (!userPoint) {
    return [];
  }

  const userLat = Number(
    userPoint.latitude ?? userPoint.lat
  );

  const userLng = Number(
    userPoint.longitude ?? userPoint.lng
  );

  if (
    !Number.isFinite(userLat) ||
    !Number.isFinite(userLng)
  ) {
    return [];
  }

  const source = category
    ? getPrachinLifeV2Places(category)
    : getPrachinLifeV2Places();

  return source
    .map((place) => {
      const placeLat = Number(
        place.latitude ?? place.lat
      );

      const placeLng = Number(
        place.longitude ?? place.lng
      );

      if (
        !Number.isFinite(placeLat) ||
        !Number.isFinite(placeLng)
      ) {
        return null;
      }

      const km = Number(
        calculatePlaceDistance(
          userLat,
          userLng,
          placeLat,
          placeLng
        )
      );

      if (!Number.isFinite(km)) {
        return null;
      }

      return {
        ...place,

        /*
         * V1 renderer compatibility.
         * Keep the canonical numeric distance in kilometres
         * under the common field names used by old UI code.
         */
        distance: km,
        distance_km: km,
        distanceKm: km,
        computedDistance: km,
        distance_text:
          km < 1
            ? `${Math.round(km * 1000)} ม.`
            : `${km.toFixed(1)} กม.`,
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.distance - b.distance)
    .slice(0, limit);
}

window.PrachinLifeV2Search = Object.freeze({
  search: searchPrachinLifeV2Places,
  nearMe: getPrachinLifeV2NearMe,
});

/* ===== END PRACHINLIFE V2 SEARCH + NEAR ME BRIDGE ===== */


/* ===== PRACHINLIFE V2 INTERNAL BETA SWITCH ===== */

window.PrachinLifeV2Beta = Object.freeze({
  mode: "internal_beta",
  v2First: true,
  v1Fallback: true,
  publicProduction: false
});

/* ===== END PRACHINLIFE V2 INTERNAL BETA SWITCH ===== */




async function init() {

  /* V2_PRELOAD_PHASE2D */
  await loadPrachinLifeV2Data();

  try {

    window.PrachinLife.context.apply();

    currentLocalProvince =
      window.PrachinLife.context.getCurrentProvince();

    window.PrachinLife.ui.setText(
      "recommendedResultCount",
      "กำลังโหลดข้อมูล..."
    );


    bindEvents();


    await Promise.all([
      loadPromotions(),
      loadCommonIndex(),
      loadVegetarianIndex(),
      loadGoIndex(),
      loadServiceIndex(),
    ]);


    prepareEatPlaces();

    prepareVegetarianPlaces();

    prepareGoPlaces();

    prepareServicePlaces();

    buildVegetarianProvinceFilters();

    buildShoppingMerchantFilters();


    updateMeta();

    applyFilters();

    applyEatFilters();

    applyVegetarianFilters();

    applyServiceFilters();

    setMainCategory(
      "recommended",
      false
    );


    renderRecommended();

  }

  catch (error) {

    console.error(
      "PrachinLife INIT ERROR:",
      error
    );


    window.PrachinLife.ui.setText(
      "recommendedResultCount",
      "เกิดข้อผิดพลาดในการโหลดข้อมูล"
    );
  }
}


/* =====================================================
EVENT BINDING
===================================================== */

function bindEvents() {

  if (
    !document.documentElement.dataset
      .pilotPlaceDetailBound
  ) {
    document.documentElement.dataset
      .pilotPlaceDetailBound = "1";

    document.addEventListener(
      "click",
      event => {
        const target = event.target;

        if (
          target instanceof Element &&
          target.closest("[data-place-detail-key]")
        ) {
          window.PrachinLife?.core?.usageAnalytics
            ?.track("place_detail");
        }
      }
    );
  }

  bindSearchEvents();

  bindRefreshEvent();

  bindMainCategoryEvents();

  bindRecommendedEvents();

  bindShoppingEvents();

  bindEatEvents();

  bindVegetarianEvents();

  bindGoEvents();

  bindServiceEvents();

  bindLoadMoreEvents();

  bindResetEvent();
}


/* =====================================================
SEARCH
===================================================== */

function bindSearchEvents() {

  const searchInput =
    document.getElementById(
      "searchInput"
    );


  const searchBtn =
    document.getElementById(
      "searchBtn"
    );


  if (searchInput) {

    searchInput.addEventListener(
      "keydown",
      event => {

        if (event.key === "Enter") {

          performSearch();
        }
      }
    );
  }


  if (searchBtn) {

    searchBtn.addEventListener(
      "click",
      performSearch
    );
  }
}


/* =====================================================
REFRESH
===================================================== */

function bindRefreshEvent() {

  const refreshBtn =
    document.getElementById(
      "refreshBtn"
    );


  if (!refreshBtn) {

    return;
  }


  refreshBtn.addEventListener(
    "click",
    async () => {

      try {

        showToast(
          "กำลังโหลดข้อมูลล่าสุด..."
        );


        await Promise.all([
          loadPromotions(true),
          loadCommonIndex(true),
          loadVegetarianIndex(true),
          loadGoIndex(true),
          loadServiceIndex(true),
        ]);


        prepareEatPlaces();

        prepareVegetarianPlaces();

        prepareGoPlaces();

        prepareServicePlaces();

        buildVegetarianProvinceFilters();


        updateMeta();

        applyFilters();

        applyEatFilters();

        applyVegetarianFilters();

        applyServiceFilters();

        if (
          currentMainCategory ===
          "recommended"
        ) {

          renderRecommended();
        }

        else if (
          currentMainCategory ===
          "go"
        ) {

          if (
            primaryGoPlaces.length > 0
          ) {
            filteredGoPlaces =
              [...primaryGoPlaces];

            renderGoPlaces();
          }
        }


        showToast(
          "โหลดข้อมูลล่าสุดแล้ว"
        );

      }

      catch (error) {

        console.error(
          "Refresh error:",
          error
        );


        showToast(
          "โหลดข้อมูลไม่สำเร็จ"
        );
      }
    }
  );
}


/* =====================================================
MAIN CATEGORY
===================================================== */

function bindMainCategoryEvents() {

  document
    .querySelectorAll(
      "[data-main-category]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            const category =
              button.dataset.mainCategory
              || "recommended";


            setMainCategory(
              category,
              true
            );
          }
        );
      }
    );
}


function resetNearMeForMainCategoryChange(
  nextCategory
) {

  if (
    nextCategory ===
    currentMainCategory
  ) {
    return;
  }

  userLocation = null;

  currentEatPage = 1;
  currentVegetarianPage = 1;
  currentServicePage = 1;

  updateNearMeState(false);
  updateServiceNearMeState(false);

  if (
    window.PrachinLife?.modules?.vegetarian
      ?.updateNearMeState
  ) {
    window.PrachinLife.modules.vegetarian.updateNearMeState(
      false
    );
  }

  const goNearMeBtn =
    document.getElementById(
      "goNearMeBtn"
    );

  if (goNearMeBtn) {
    goNearMeBtn.classList.remove(
      "active"
    );

    goNearMeBtn.textContent =
      "📍 ใกล้ฉัน";
  }

  window.PrachinLife.ui.setText(
    "nearMeStatus",
    "กด “ใกล้ฉัน” เพื่อเรียงร้านตามระยะทาง"
  );

  window.PrachinLife.ui.setText(
    "vegetarianNearMeStatus",
    "กด “ใกล้ฉัน” เพื่อเรียงร้านตามระยะทาง"
  );

  window.PrachinLife.ui.setText(
    "goNearMeStatus",
    "กด “ใกล้ฉัน” เพื่อเรียงสถานที่ตามระยะทาง"
  );

  window.PrachinLife.ui.setText(
    "serviceNearMeStatus",
    "กด “ใกล้ฉัน” เพื่อเรียงบริการตามระยะทาง"
  );

  filteredGoPlaces =
    [...primaryGoPlaces];
}


function setMainCategory(
  category,
  scrollToResult = true
) {

  window.PrachinLife?.core?.usageAnalytics?.track("category_view");

  resetNearMeForMainCategoryChange(
    category
  );

  currentMainCategory =
    category;


  updateMainCategoryButtons();

  hideAllOptionGroups();

  hideAllResultSections();


  if (
    category ===
    "recommended"
  ) {

    window.PrachinLife.ui.showElement(
      "recommendedOptions"
    );

    window.PrachinLife.ui.showElement(
      "recommendedResultSection"
    );

    renderRecommended();
  }


  else if (
    category ===
    "shopping"
  ) {

    window.PrachinLife.ui.showElement(
      "shoppingOptions"
    );

    window.PrachinLife.ui.showElement(
      "shoppingResultSection"
    );

    applyFilters();
  }


  else if (
    category ===
    "eat"
  ) {

    window.PrachinLife.ui.showElement(
      "eatOptions"
    );

    window.PrachinLife.ui.showElement(
      "eatResultSection"
    );

    applyEatFilters();
  }


  else if (
    category ===
    "vegetarian"
  ) {

    window.PrachinLife.ui.showElement(
      "vegetarianOptions"
    );

    window.PrachinLife.ui.showElement(
      "vegetarianResultSection"
    );

    applyVegetarianFilters();
  }


  else if (
    category ===
    "go"
  ) {

    window.PrachinLife.ui.showElement(
      "goOptions"
    );

    if (
      primaryGoPlaces.length > 0
    ) {

      filteredGoPlaces =
        [...primaryGoPlaces];

      window.PrachinLife.ui.showElement(
        "goResultSection"
      );

      renderGoPlaces();
    }

    else {

      window.PrachinLife.ui.showElement(
        "comingSoonResultSection"
      );

      setComingSoonContent(
        "📍",
        "เที่ยวไหนดี",
        "กำลังเตรียมข้อมูลสถานที่ท่องเที่ยว กิจกรรม และที่น่าแวะ"
      );
    }
  }


  else if (
    category ===
    "services"
  ) {

    window.PrachinLife.ui.showElement(
      "servicesOptions"
    );

    window.PrachinLife.ui.showElement(
      "serviceResultSection"
    );

    applyServiceFilters();
  }


  if (scrollToResult) {

    scrollToResults();
  }
}


function updateMainCategoryButtons() {

  document
    .querySelectorAll(
      "[data-main-category]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          button.dataset.mainCategory
            === currentMainCategory
        );
      }
    );
}


/* =====================================================
RECOMMENDED BUTTONS
===================================================== */

function bindRecommendedEvents() {

  const pilotRecommendedList =
    document.getElementById("recommendedList");

  if (
    pilotRecommendedList &&
    !pilotRecommendedList.dataset.pilotLearningBound
  ) {
    pilotRecommendedList.dataset.pilotLearningBound = "1";

    pilotRecommendedList.addEventListener(
      "click",
      event => {
        const target = event.target;

        if (!(target instanceof Element)) return;

        const feedback =
          target.closest("[data-pilot-feedback]");

        if (feedback) {
          const value =
            feedback.dataset.pilotFeedback;

          if (value === "helpful") {
            window.PrachinLife?.core?.usageAnalytics
              ?.track("decision_feedback_helpful");
          }

          if (value === "not_helpful") {
            window.PrachinLife?.core?.usageAnalytics
              ?.track("decision_feedback_not_helpful");
          }

          const actions =
            feedback.closest(".pilot-feedback-actions");

          if (actions) {
            actions
              .querySelectorAll("[data-pilot-feedback]")
              .forEach(button => {
                const selected =
                  button === feedback;

                button.classList.toggle(
                  "active",
                  selected
                );

                button.setAttribute(
                  "aria-pressed",
                  selected ? "true" : "false"
                );
              });

            let status =
              actions.querySelector(
                ".pilot-feedback-status"
              );

            if (!status) {
              status =
                document.createElement("span");

              status.className =
                "pilot-feedback-status";

              status.setAttribute(
                "role",
                "status"
              );

              actions.appendChild(status);
            }

            status.textContent =
              "ขอบคุณสำหรับความคิดเห็น";
          }

          return;
        }

        if (
          target.closest("[data-pilot-map-action]")
        ) {
          window.PrachinLife?.core?.usageAnalytics
            ?.track("map_action");

          window.PrachinLife?.core?.usageAnalytics
            ?.track("decision_select");
        }
      }
    );
  }

  document
    .querySelectorAll(
      "[data-recommended-action]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            const action =
              button.dataset.recommendedAction
              || "all";


            updateRecommendedButtons(
              action
            );


            if (
              action ===
              "shopping"
            ) {

              setMainCategory(
                "shopping",
                true
              );

              return;
            }


            if (
              action ===
              "eat"
            ) {

              setMainCategory(
                "eat",
                true
              );

              return;
            }


            if (
              action ===
              "vegetarian"
            ) {

              setMainCategory(
                "vegetarian",
                true
              );

              return;
            }


            if (
              action ===
              "latest"
            ) {

              renderRecommended(
                "latest"
              );

              scrollToResults();

              return;
            }


            renderRecommended(
              "all"
            );

            scrollToResults();
          }
        );
      }
    );
}


function updateRecommendedButtons(
  action
) {

  document
    .querySelectorAll(
      "[data-recommended-action]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          button.dataset.recommendedAction
            === action
        );
      }
    );
}


/* =====================================================
SHOPPING EVENTS
===================================================== */

function buildShoppingMerchantFilters() {

  const container =
    document.getElementById(
      "shoppingMerchantFilters"
    );

  if (!container) return;

  const merchants = [
    ...new Set(
      allPromotions
        .map(
          promotion =>
            String(
              promotion?.merchant || ""
            ).trim()
        )
        .filter(Boolean)
    ),
  ].sort(
    (a, b) =>
      a.localeCompare(
        b,
        "th",
        { sensitivity: "base" }
      )
  );

  container.innerHTML = "";

  const values = [
    ["all", "ทั้งหมด"],
    ...merchants.map(
      merchant => [merchant, merchant]
    ),
  ];

  for (const [value, label] of values) {
    const button =
      document.createElement("button");

    button.type = "button";
    button.className = "filter-button";
    button.dataset.merchant = value;
    button.textContent = label;

    button.addEventListener(
      "click",
      () => {
        currentMerchant =
          button.dataset.merchant || "all";
        currentPage = 1;
        updateShoppingButtons();
        applyFilters();
        showShoppingResult();
      }
    );

    container.appendChild(button);
  }

  if (
    currentMerchant !== "all"
    && !merchants.includes(currentMerchant)
  ) {
    currentMerchant = "all";
  }

  updateShoppingButtons();
}


function bindShoppingEvents() {

  document
    .querySelectorAll(
      "[data-smart]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentSmart =
              button.dataset.smart
              || "recommended";

            currentType = "all";

            currentPage = 1;


            updateShoppingButtons();

            applyFilters();

            showShoppingResult();
          }
        );
      }
    );


  document
    .querySelectorAll(
      "[data-type]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentType =
              button.dataset.type
              || "all";

            currentSmart =
              "recommended";

            currentPage = 1;


            updateShoppingButtons();

            applyFilters();

            showShoppingResult();
          }
        );
      }
    );

}


function showShoppingResult() {

  currentMainCategory =
    "shopping";


  updateMainCategoryButtons();

  hideAllOptionGroups();

  hideAllResultSections();


  window.PrachinLife.ui.showElement(
    "shoppingOptions"
  );

  window.PrachinLife.ui.showElement(
    "shoppingResultSection"
  );


  scrollToResults();
}


function updateShoppingButtons() {

  document
    .querySelectorAll(
      "[data-smart]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          currentType === "all"
          &&
          button.dataset.smart
            === currentSmart
        );
      }
    );


  document
    .querySelectorAll(
      "[data-type]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          button.dataset.type
            === currentType
        );
      }
    );


  document
    .querySelectorAll(
      "[data-merchant]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          button.dataset.merchant
            === currentMerchant
        );
      }
    );
}


/* =====================================================
EAT EVENTS
===================================================== */

function bindEatEvents() {

  document
    .querySelectorAll(
      "[data-eat-type]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentEatType =
              button.dataset.eatType
              || "all";

            currentEatPage = 1;


            updateEatButtons();

            applyEatFilters();

            showEatResult();
          }
        );
      }
    );


  const nearMeBtn =
    document.getElementById(
      "nearMeBtn"
    );


  if (nearMeBtn) {

    nearMeBtn.addEventListener(
      "click",
      activateNearMe
    );
  }
}


function showEatResult() {

  currentMainCategory =
    "eat";


  updateMainCategoryButtons();

  hideAllOptionGroups();

  hideAllResultSections();


  window.PrachinLife.ui.showElement(
    "eatOptions"
  );

  window.PrachinLife.ui.showElement(
    "eatResultSection"
  );


  scrollToResults();
}


function updateEatButtons() {

  document
    .querySelectorAll(
      "[data-eat-type]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          button.dataset.eatType
            === currentEatType
        );
      }
    );



}


/* =====================================================
VEGETARIAN EVENTS
===================================================== */

function handleVegetarianProvinceSelect(
  province
) {

  currentVegetarianProvince =
    province;

  currentVegetarianPage = 1;

  userLocation = null;

  window.PrachinLife.modules.vegetarian.updateNearMeState(
    false
  );

  const provinceSelect =
    document.getElementById(
      "vegetarianProvinceSelect"
    );

  if (provinceSelect) {
    provinceSelect.value =
      currentVegetarianProvince;
  }

  applyVegetarianFilters();

  showVegetarianResult();
}


function bindVegetarianEvents() {

  window.PrachinLife.modules.vegetarian.bindMainEvents(
    activateVegetarianNearMe,
    handleVegetarianProvinceSelect
  );
}


function bindDynamicVegetarianProvinceEvents() {

  window.PrachinLife.modules.vegetarian.bindProvinceEvents(
    handleVegetarianProvinceSelect
  );
}


function showVegetarianResult() {

  currentMainCategory =
    "vegetarian";


  updateMainCategoryButtons();

  hideAllOptionGroups();

  hideAllResultSections();


  window.PrachinLife.ui.showElement(
    "vegetarianOptions"
  );

  window.PrachinLife.ui.showElement(
    "vegetarianResultSection"
  );


  scrollToResults();
}



/* =====================================================
SERVICE EVENTS
===================================================== */

function bindServiceEvents() {

  document
    .querySelectorAll(
      "[data-service-category]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentServiceCategory =
              button.dataset.serviceCategory
              || "all";

            currentServicePage = 1;

            updateServiceButtons();
            applyServiceFilters();
            showServiceResult();
          }
        );
      }
    );

  const nearMeBtn =
    document.getElementById(
      "serviceNearMeBtn"
    );

  if (nearMeBtn) {
    nearMeBtn.addEventListener(
      "click",
      activateServiceNearMe
    );
  }
}


function updateServiceButtons() {

  document
    .querySelectorAll(
      "[data-service-category]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          button.dataset.serviceCategory
            === currentServiceCategory
        );
      }
    );
}


function showServiceResult() {

  currentMainCategory =
    "services";

  updateMainCategoryButtons();

  hideAllOptionGroups();
  hideAllResultSections();

  window.PrachinLife.ui.showElement(
    "servicesOptions"
  );

  window.PrachinLife.ui.showElement(
    "serviceResultSection"
  );

  scrollToResults();
}


function updateServiceNearMeState(
  active
) {

  const button =
    document.getElementById(
      "serviceNearMeBtn"
    );

  if (!button) {
    return;
  }

  button.classList.toggle(
    "active",
    active
  );

  button.textContent =
    active
      ? "✓ ใกล้ฉัน"
      : "📍 ใกล้ฉัน";
}


function activateServiceNearMe() {

  window.PrachinLife?.core?.usageAnalytics?.track("near_me");

  if (userLocation) {

    userLocation = null;
    currentServicePage = 1;

    updateServiceNearMeState(
      false
    );

    window.PrachinLife.ui.setText(
      "serviceNearMeStatus",
      "กด “ใกล้ฉัน” เพื่อเรียงบริการตามระยะทาง"
    );

    applyServiceFilters();
    showServiceResult();

    return;
  }

  requestUserLocation(
    position => {

      userLocation =
        position;

      currentServicePage = 1;

      updateServiceNearMeState(
        true
      );

      window.PrachinLife.ui.setText(
        "serviceNearMeStatus",
        "กำลังเรียงบริการจากใกล้ไปไกล"
      );

      applyServiceFilters();
      showServiceResult();
    },
    "serviceNearMeStatus"
  );
}


/* =====================================================
LOAD MORE
===================================================== */

function bindLoadMoreEvents() {

  const loadMoreBtn =
    document.getElementById(
      "loadMoreBtn"
    );


  const eatLoadMoreBtn =
    document.getElementById(
      "eatLoadMoreBtn"
    );


  const vegetarianLoadMoreBtn =
    document.getElementById(
      "vegetarianLoadMoreBtn"
    );

  const serviceLoadMoreBtn =
    document.getElementById(
      "serviceLoadMoreBtn"
    );


  if (loadMoreBtn) {

    loadMoreBtn.addEventListener(
      "click",
      () => {

        currentPage++;

        renderPromotions();
      }
    );
  }


  if (eatLoadMoreBtn) {

    eatLoadMoreBtn.addEventListener(
      "click",
      () => {

        currentEatPage++;

        renderEatPlaces();
      }
    );
  }


  if (vegetarianLoadMoreBtn) {

    vegetarianLoadMoreBtn.addEventListener(
      "click",
      () => {

        currentVegetarianPage++;

        renderVegetarianPlaces();
      }
    );
  }

  if (serviceLoadMoreBtn) {

    serviceLoadMoreBtn.addEventListener(
      "click",
      () => {

        currentServicePage++;

        renderServicePlaces();
      }
    );
  }
}


/* =====================================================
RESET SHOPPING
===================================================== */

function bindResetEvent() {

  const resetBtn =
    document.getElementById(
      "resetBtn"
    );


  if (!resetBtn) {

    return;
  }


  resetBtn.addEventListener(
    "click",
    resetShoppingFilters
  );
}


function resetShoppingFilters() {

  currentMerchant = "all";

  currentType = "all";

  currentSmart = "recommended";

  currentPage = 1;


  updateShoppingButtons();

  applyFilters();
}


/* =====================================================
END PART 1
===================================================== */
/* =====================================================
LOAD PROMOTIONS
===================================================== */

async function loadPromotions(
  forceRefresh = false
) {

  try {

    const url =
      forceRefresh
        ? `${DATA_URL}?t=${Date.now()}`
        : DATA_URL;


    const response =
      await fetch(
        url,
        {
          cache: "no-store",
        }
      );


    if (!response.ok) {

      throw new Error(
        `Promotion HTTP ${response.status}`
      );
    }


    const data =
      await response.json();


    if (Array.isArray(data)) {

      allPromotions =
        normalizePromotionData(
          data
        );
    }

    else if (
      data
      &&
      Array.isArray(
        data.promotions
      )
    ) {

      allPromotions =
        normalizePromotionData(
          data.promotions
        );
    }

    else {

      allPromotions = [];
    }


    allPromotions =
      sortLatest(
        allPromotions
      );

  }

  catch (error) {

    console.error(
      "PrachinLife promotion load error:",
      error
    );


    allPromotions = [];

    filteredPromotions = [];


    window.PrachinLife.ui.setText(
      "resultCount",
      "โหลดข้อมูลไม่สำเร็จ"
    );
  }
}


/* =====================================================
LOAD COMMON INDEX
===================================================== */

async function loadCommonIndex(
  forceRefresh = false
) {

  try {

    const url =
      forceRefresh
        ? `${INDEX_URL}?t=${Date.now()}`
        : INDEX_URL;


    const response =
      await fetch(
        url,
        {
          cache: "no-store",
        }
      );


    if (!response.ok) {

      throw new Error(
        `Common index HTTP ${response.status}`
      );
    }


    const data =
      await response.json();


    if (!Array.isArray(data)) {

      throw new Error(
        "Common index must be an array"
      );
    }


    allContent = data;


    console.log(
      "PrachinLife common index:",
      allContent.length
    );

  }

  catch (error) {

    console.error(
      "PrachinLife common index error:",
      error
    );


    allContent = [];
  }
}


/* =====================================================
LOAD GO INDEX
===================================================== */

async function loadGoIndex(
  forceRefresh = false
) {

  try {

    const url =
      forceRefresh
        ? `${GO_URL}?t=${Date.now()}`
        : GO_URL;

    const response =
      await fetch(
        url,
        {
          cache: "no-store",
        }
      );

    if (!response.ok) {
      throw new Error(
        `Go index HTTP ${response.status}`
      );
    }

    const data =
      await response.json();

    if (!Array.isArray(data)) {
      throw new Error(
        "Go index must be an array"
      );
    }

    allGoPlaces =
      data.filter(
        item =>
          item
          &&
          typeof item === "object"
      );

    console.log(
      "PrachinLife go index:",
      allGoPlaces.length
    );
  }

  catch (error) {

    console.error(
      "PrachinLife go index error:",
      error
    );

    allGoPlaces = [];
    primaryGoPlaces = [];
    filteredGoPlaces = [];
  }
}


/* =====================================================
LOAD SERVICE INDEX
===================================================== */

async function loadServiceIndex(
  forceRefresh = false
) {
  try {

    const url =
      forceRefresh
        ? `${SERVICE_URL}?t=${Date.now()}`
        : SERVICE_URL;

    const response =
      await fetch(
        url,
        {
          cache: "no-store",
        }
      );

    if (!response.ok) {
      throw new Error(
        `Service index HTTP ${response.status}`
      );
    }

    const data =
      await response.json();

    if (!Array.isArray(data)) {
      throw new Error(
        "Service index must be an array"
      );
    }

    allServicePlaces =
      data.filter(
        item =>
          item &&
          typeof item === "object"
      );

    console.log(
      "PrachinLife service index:",
      allServicePlaces.length
    );
  }

  catch (error) {

    console.error(
      "PrachinLife service index error:",
      error
    );

    allServicePlaces = [];
    primaryServicePlaces = [];
    filteredServicePlaces = [];

    window.PrachinLife.ui.setText(
      "serviceResultCount",
      "ไม่สามารถโหลดข้อมูลบริการได้"
    );
  }
}


/* =====================================================
LOAD VEGETARIAN INDEX
===================================================== */

async function loadVegetarianIndex(
  forceRefresh = false
) {

  try {

    const url =
      forceRefresh
        ? `${VEGETARIAN_URL}?t=${Date.now()}`
        : VEGETARIAN_URL;


    const response =
      await fetch(
        url,
        {
          cache: "no-store",
        }
      );


    if (!response.ok) {

      throw new Error(
        `Vegetarian index HTTP ${response.status}`
      );
    }


    const data =
      await response.json();


    if (!Array.isArray(data)) {

      throw new Error(
        "Vegetarian index must be an array"
      );
    }


    allVegetarianPlaces =
      data.filter(
        item =>
          item
          &&
          typeof item === "object"
      );


    console.log(
      "PrachinLife vegetarian index:",
      allVegetarianPlaces.length
    );

  }

  catch (error) {

    console.error(
      "PrachinLife vegetarian index error:",
      error
    );


    allVegetarianPlaces = [];

    filteredVegetarianPlaces = [];


    window.PrachinLife.ui.setText(
      "vegetarianResultCount",
      "ไม่สามารถโหลดข้อมูลร้านได้"
    );
  }
}


/* =====================================================
NORMALIZE PROMOTIONS
===================================================== */

function normalizePromotionData(
  data
) {

  return data
    .filter(
      item =>
        item
        &&
        typeof item === "object"
    )
    .map(
      item => {

        const title =
          item.title
          || item.product
          || "ไม่มีชื่อ";


        const merchant =
          item.merchant
          || item.store
          || "ไม่ระบุแหล่ง";


        return {

          ...item,

          title,

          merchant,

          image_url:
            item.image_url
            || item.image
            || "",

          promotion_type:
            item.promotion_type
            || "campaign",

          source:
            item.source
            || merchant,

          source_url:
            item.source_url
            || "",

          verified:
            item.verified
            === true,

          location_scope:
            item.location_scope
            || "national",

          country:
            item.country
            || "TH",

          province:
            item.province
            || null,

          district:
            item.district
            || null,

          subdistrict:
            item.subdistrict
            || null,

          branch_name:
            item.branch_name
            || null,
        };
      }
    );
}


/* =====================================================
PREPARE EAT
===================================================== */

function prepareEatPlaces() {

  allEatPlaces =
    allContent.filter(
      item => {
        if (
          !item
          ||
          item.content_type !== "eat"
        ) {
          return false;
        }

        const province =
          item.location?.province
          || "";

        return (
          !currentLocalProvince
          ||
          province === currentLocalProvince
        );
      }
    );


  filteredEatPlaces =
    [...allEatPlaces];


  currentEatPage = 1;
}


/* =====================================================
PREPARE VEGETARIAN
===================================================== */

function prepareVegetarianPlaces() {

  primaryVegetarianPlaces =
    allVegetarianPlaces.filter(
      place => {

        const metadata =
          place?.metadata || {};

        const displayTier =
          metadata.display_tier || "";

        const isPrimary =
          metadata.show_in_primary_directory
          === true;

        const isDedicated =
          displayTier === "dedicated";

        const isNamedCandidate =
          displayTier === "named_candidate";

        return (
          metadata.needs_review !== true
          &&
          (
            isPrimary
            ||
            isDedicated
            ||
            isNamedCandidate
          )
        );
      }
    );

  filteredVegetarianPlaces =
    [...primaryVegetarianPlaces];

  currentVegetarianPage = 1;

  console.log(
    "PrachinLife vegetarian primary directory:",
    primaryVegetarianPlaces.length,
    "/",
    allVegetarianPlaces.length
  );
}


/* =====================================================
PREPARE SERVICE
===================================================== */

function prepareServicePlaces() {

  primaryServicePlaces =
    allServicePlaces.filter(
      place => {

        const metadata =
          place?.metadata || {};

        const province =
          place?.location?.province || "";

        return (
          metadata.show_in_primary_directory
            === true
          &&
          metadata.needs_review
            !== true
          &&
          (
            !currentLocalProvince
            ||
            province === currentLocalProvince
          )
        );
      }
    );

  filteredServicePlaces =
    [...primaryServicePlaces];

  currentServicePage = 1;
}


/* =====================================================
PREPARE GO
===================================================== */

function prepareGoPlaces() {

  primaryGoPlaces =
    window.PrachinLife.modules.go.getPrimaryPlaces(
      allGoPlaces,
      currentLocalProvince
    );

  filteredGoPlaces =
    [...primaryGoPlaces];
}


/* =====================================================
RENDER GO
===================================================== */

function renderGoPlaces() {

  window.PrachinLife.modules.go.renderPlaces(
    filteredGoPlaces
  );

  window.PrachinLife.ui.setText(
    "goResultCount",
    `${filteredGoPlaces.length} สถานที่`
  );
}


/* =====================================================
GLOBAL SEARCH
===================================================== */

function performSearch() {

  const input =
    document.getElementById(
      "searchInput"
    );


  const query =
    input
      ? input.value.trim()
      : "";


  if (!query) {

    showToast(
      "พิมพ์สิ่งที่ต้องการค้นหาก่อน"
    );

    return;
  }


  window.PrachinLife?.core?.usageAnalytics?.track("search");

  const normalizedQuery =
    query.toLowerCase();

  const searchIntentEngine =
    window.PrachinLife?.core?.searchIntentV1;

  const searchIntent =
    searchIntentEngine
      ? searchIntentEngine.parse(query)
      : {
          group: null,
          category: null,
          province: null,
          near_me: false,
          residual: normalizedQuery
        };


  const isVegetarianIntent =
    searchIntent.group === "vegetarian";

  const vegetarianSearchSource =
    isVegetarianIntent
      ? primaryVegetarianPlaces
      : allVegetarianPlaces;

  const vegetarianMatches =
    vegetarianSearchSource.filter(
      place => {

        const text = [
          place.title,
          place.location?.subdistrict,
          place.location?.district,
          place.location?.province,
          ...(Array.isArray(
            place.food_types
          )
            ? place.food_types
            : [])
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        if (searchIntent.group === "vegetarian") {
          if (
            searchIntent.province
            &&
            place.location?.province !== searchIntent.province
          ) {
            return false;
          }

          if (!searchIntent.residual) {
            return true;
          }

          return text.includes(
            searchIntent.residual
          );
        }

        return text.includes(
          normalizedQuery
        );
      }
    );


  if (
    vegetarianMatches.length > 0
    &&
    isVegetarianIntent
  ) {

    currentMainCategory =
      "vegetarian";


    filteredVegetarianPlaces =
      vegetarianMatches;


    currentVegetarianPage = 1;


    updateMainCategoryButtons();

    hideAllOptionGroups();

    hideAllResultSections();


    window.PrachinLife.ui.showElement(
      "vegetarianOptions"
    );

    window.PrachinLife.ui.showElement(
      "vegetarianResultSection"
    );


    renderVegetarianPlaces();


    window.PrachinLife.ui.setText(
      "vegetarianResultCount",
      `${filteredVegetarianPlaces.length} ร้าน`
    );


    scrollToResults();

    return;
  }


  /*
   * =====================================================
   * PILOT V1 - SERVICE SEARCH / INTENT ROUTER V0
   *
   * Known service intent must be resolved against the
   * trusted primary service directory before falling back
   * to generic cross-content search.
   * =====================================================
   */

  const serviceIntentCategory =
    searchIntent.group === "services"
      ? searchIntent.category
      : null;

  if (serviceIntentCategory) {
    const serviceMatches =
      primaryServicePlaces.filter(
        place => {
          if (
            String(place?.category || "").toLowerCase()
              !== serviceIntentCategory
          ) {
            return false;
          }

          if (
            searchIntent.province
            &&
            place?.location?.province !== searchIntent.province
          ) {
            return false;
          }

          if (!searchIntent.residual) {
            return true;
          }

          const searchableText = [
            place?.title,
            place?.name,
            place?.metadata?.category_label,
            place?.location?.subdistrict,
            place?.location?.district,
            place?.location?.province
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

          return searchableText.includes(
            searchIntent.residual
          );
        }
      );

    if (serviceMatches.length > 0) {
      currentMainCategory = "services";
      currentServiceCategory = serviceIntentCategory;
      filteredServicePlaces = serviceMatches;
      currentServicePage = 1;

      updateMainCategoryButtons();
      hideAllOptionGroups();
      hideAllResultSections();

      window.PrachinLife.ui.showElement(
        "servicesOptions"
      );

      window.PrachinLife.ui.showElement(
        "serviceResultSection"
      );

      updateServiceButtons();
      renderServicePlaces();

      window.PrachinLife.ui.setText(
        "serviceResultCount",
        `${filteredServicePlaces.length} แห่ง`
      );

      scrollToResults();
      return;
    }
  }


  /*
   * Explicit Go-category search may use safe non-review
   * local places without promoting them into Primary.
   *
   * Broad Go browse/search continues to use primaryGoPlaces.
   */
  const explicitGoCategorySearch =
    searchIntent.group === "go"
    &&
    searchIntent.category
    &&
    searchIntent.category !== "go";

  const goSearchSource =
    explicitGoCategorySearch
      ? allGoPlaces.filter(
          place =>
            place?.metadata?.needs_review !== true
        )
      : primaryGoPlaces;

  const goMatches =
    goSearchSource.filter(
      place => {
        if (searchIntent.group === "go") {
          if (
            explicitGoCategorySearch
            &&
            String(place?.category || "").toLowerCase()
              !== searchIntent.category
          ) {
            return false;
          }

          if (
            searchIntent.province
            &&
            place?.location?.province !== searchIntent.province
          ) {
            return false;
          }

          if (!searchIntent.residual) {
            return true;
          }
        }

        const text = [
          place?.title,
          place?.name,
          place?.category,
          place?.metadata?.category_label,
          place?.location?.district,
          place?.location?.province
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return text.includes(
          searchIntent.group === "go"
            ? searchIntent.residual
            : normalizedQuery
        );
      }
    );


  if (
    goMatches.length > 0
  ) {

    currentMainCategory =
      "go";

    filteredGoPlaces =
      goMatches;

    updateMainCategoryButtons();

    hideAllOptionGroups();

    hideAllResultSections();

    window.PrachinLife.ui.showElement(
      "goOptions"
    );

    window.PrachinLife.ui.showElement(
      "goResultSection"
    );

    renderGoPlaces();

    scrollToResults();

    return;
  }


  /*
   * =====================================================
   * PILOT V1 - KNOWN INTENT FAIL CLOSED
   *
   * Once a trusted intent is understood, never fall back
   * to unrelated cross-category results.
   * =====================================================
   */

  if (searchIntent.group === "go") {
    currentMainCategory = "go";
    filteredGoPlaces = [];

    updateMainCategoryButtons();
    hideAllOptionGroups();
    hideAllResultSections();

    window.PrachinLife.ui.showElement(
      "goOptions"
    );

    window.PrachinLife.ui.showElement(
      "goResultSection"
    );

    renderGoPlaces();

    window.PrachinLife.ui.setText(
      "goResultCount",
      searchIntent.category === "temple"
        ? "ยังไม่มีวัดที่พร้อมแสดงในรายการหลัก"
        : "ยังไม่มีสถานที่ตรงกับคำค้นนี้"
    );

    scrollToResults();
    return;
  }

  if (searchIntent.group === "services") {
    currentMainCategory = "services";
    currentServiceCategory =
      searchIntent.category || "all";

    filteredServicePlaces = [];
    currentServicePage = 1;

    updateMainCategoryButtons();
    hideAllOptionGroups();
    hideAllResultSections();

    window.PrachinLife.ui.showElement(
      "servicesOptions"
    );

    window.PrachinLife.ui.showElement(
      "serviceResultSection"
    );

    updateServiceButtons();
    renderServicePlaces();

    window.PrachinLife.ui.setText(
      "serviceResultCount",
      "ยังไม่มีบริการตรงกับคำค้นนี้"
    );

    scrollToResults();
    return;
  }

  if (searchIntent.group === "vegetarian") {
    currentMainCategory = "vegetarian";
    filteredVegetarianPlaces = [];
    currentVegetarianPage = 1;

    updateMainCategoryButtons();
    hideAllOptionGroups();
    hideAllResultSections();

    window.PrachinLife.ui.showElement(
      "vegetarianOptions"
    );

    window.PrachinLife.ui.showElement(
      "vegetarianResultSection"
    );

    renderVegetarianPlaces();

    window.PrachinLife.ui.setText(
      "vegetarianResultCount",
      "ยังไม่มีร้านตรงกับคำค้นนี้"
    );

    scrollToResults();
    return;
  }


  if (
    !window.PrachinLifeSearch
    ||
    typeof window
      .PrachinLifeSearch
      .search
      !== "function"
  ) {

    showToast(
      "ระบบค้นหายังไม่พร้อม"
    );

    return;
  }


  const result =
    window.PrachinLifeSearch.search(
      allContent,
      query,
      {
        limit: 100,
      }
    );


  const dealIds =
    new Set(
      result.items
        .filter(
          item =>
            item.content_type
              === "deal"
        )
        .map(
          item =>
            item.id
        )
    );


  const eatIds =
    new Set(
      result.items
        .filter(
          item =>
            item.content_type
              === "eat"
        )
        .map(
          item =>
            item.id
        )
    );


  if (
    dealIds.size > 0
    &&
    eatIds.size === 0
  ) {

    currentMainCategory =
      "shopping";


    filteredPromotions =
      allPromotions.filter(
        item =>
          dealIds.has(
            item.id
          )
          &&
          window.PrachinLife.core.matchesLocalScope(
            item,
            currentLocalProvince
          )
      );


    currentPage = 1;


    updateMainCategoryButtons();

    hideAllOptionGroups();

    hideAllResultSections();


    window.PrachinLife.ui.showElement(
      "shoppingOptions"
    );

    window.PrachinLife.ui.showElement(
      "shoppingResultSection"
    );


    renderPromotions();


    window.PrachinLife.ui.setText(
      "resultCount",
      `${filteredPromotions.length} รายการ`
    );


    scrollToResults();

    return;
  }


  if (
    eatIds.size > 0
    &&
    dealIds.size === 0
  ) {

    currentMainCategory =
      "eat";


    filteredEatPlaces =
      allEatPlaces.filter(
        item =>
          eatIds.has(
            item.id
          )
      );


    currentEatPage = 1;


    updateMainCategoryButtons();

    hideAllOptionGroups();

    hideAllResultSections();


    window.PrachinLife.ui.showElement(
      "eatOptions"
    );

    window.PrachinLife.ui.showElement(
      "eatResultSection"
    );


    renderEatPlaces();


    window.PrachinLife.ui.setText(
      "eatResultCount",
      `${filteredEatPlaces.length} ร้าน`
    );


    scrollToResults();

    return;
  }


  currentMainCategory =
    "recommended";


  updateMainCategoryButtons();

  hideAllOptionGroups();

  hideAllResultSections();


  window.PrachinLife.ui.showElement(
    "recommendedOptions"
  );

  window.PrachinLife.ui.showElement(
    "recommendedResultSection"
  );


  renderRecommendedSearch(
    result.items
  );


  scrollToResults();
}


/* =====================================================
SHOPPING FILTER ENGINE
===================================================== */

function applyFilters() {

  filteredPromotions =
    allPromotions.filter(
      promotion => {

        const matchesMerchant =
          currentMerchant === "all"
          ||
          promotion.merchant
            === currentMerchant;


        const matchesType =
          currentType === "all"
          ||
          promotion.promotion_type
            === currentType;


        const matchesSmart =
          matchesSmartFilter(
            promotion
          );

        const matchesLocal =
          window.PrachinLife.core.matchesLocalScope(
            promotion,
            currentLocalProvince
          );


        return (
          matchesMerchant
          &&
          matchesType
          &&
          matchesSmart
          &&
          matchesLocal
        );
      }
    );


  if (
    currentSmart === "latest"
  ) {

    filteredPromotions =
      sortLatest(
        filteredPromotions
      );
  }

  else {

    filteredPromotions =
      rankInteresting(
        filteredPromotions
      );
  }


  currentPage = 1;


  renderPromotions();


  window.PrachinLife.ui.setText(
    "resultCount",
    `${filteredPromotions.length} รายการ`
  );
}


function matchesSmartFilter(
  promotion
) {

  if (
    currentSmart ===
    "recommended"
  ) {

    return true;
  }


  if (
    currentSmart ===
    "saving"
  ) {

    return (
      promotion.promotion_type
        === "coupon"

      ||

      promotion.promotion_type
        === "member_offer"

      ||

      promotion.promotion_type
        === "product_deal"

      ||

      /ส่วนลด|คุ้ม|คูปอง|\d+\s*บาท/.test(
        String(
          promotion.title
          || ""
        )
      )
    );
  }


  if (
    currentSmart ===
    "catalogue"
  ) {

    return isCataloguePromotion(
      promotion
    );
  }


  if (
    currentSmart ===
    "activity"
  ) {

    return (
      promotion.promotion_type
        === "campaign"
      &&
      !isCataloguePromotion(
        promotion
      )
    );
  }


  return true;
}


/* =====================================================
SHOPPING RANKING
===================================================== */

function getInterestingScore(
  promotion
) {

  let score = 0;


  if (
    promotion.promotion_type
      === "coupon"
  ) {

    score += 40;
  }

  else if (
    promotion.promotion_type
      === "member_offer"
  ) {

    score += 25;
  }

  else if (
    promotion.promotion_type
      === "product_deal"
  ) {

    score += 35;
  }

  else {

    score += 10;
  }


  if (
    isCataloguePromotion(
      promotion
    )
  ) {

    score += 20;
  }


  if (
    promotion.verified
      === true
  ) {

    score += 10;
  }


  if (
    promotion.image_url
  ) {

    score += 5;
  }


  return score;
}


function rankInteresting(
  data
) {

  return [
    ...data
  ].sort(
    (a, b) => {

      const scoreDiff =
        getInterestingScore(b)
        -
        getInterestingScore(a);


      if (scoreDiff !== 0) {

        return scoreDiff;
      }


      return (
        parseDateValue(
          b.collected_at
        )
        -
        parseDateValue(
          a.collected_at
        )
      );
    }
  );
}


/* =====================================================
EAT FILTER ENGINE
===================================================== */

function applyEatFilters() {

  filteredEatPlaces =
    getEatDatasetV2First().filter(
      place => {

        const matchesType =
          currentEatType === "all"
          ||
          place.category
            === currentEatType
          ||
          place.original_type
            === currentEatType;


        return matchesType;
      }
    );


  if (userLocation) {

    filteredEatPlaces =
      filteredEatPlaces
        .map(
          place => ({
            ...place,

            _distance:
              calculatePlaceDistance(
                place
              ),
          })
        )
        .sort(
          window.PrachinLife.core.compareDistance
        );
  }

  else {

    filteredEatPlaces.sort(
      window.PrachinLife.core.compareTitle
    );
  }


  currentEatPage = 1;


  renderEatPlaces();


  window.PrachinLife.ui.setText(
    "eatResultCount",
    `${filteredEatPlaces.length} ร้าน`
  );
}


/* =====================================================
SERVICE FILTER ENGINE
===================================================== */

function applyServiceFilters() {

  filteredServicePlaces =
    window.PrachinLife.modules.service
      .filterAndSort(
        primaryServicePlaces,
        currentServiceCategory,
        userLocation,
        calculatePlaceDistance,
        window.PrachinLife.core.compareDistance,
        window.PrachinLife.core.compareTitle
      );

  currentServicePage = 1;

  renderServicePlaces();

  window.PrachinLife.ui.setText(
    "serviceResultCount",
    `${filteredServicePlaces.length} แห่ง`
  );
}


function renderServicePlaces() {

  window.PrachinLife.modules.service
    .renderPlaces(
      filteredServicePlaces,
      currentServicePage,
      SERVICE_PAGE_SIZE
    );
}


/* =====================================================
VEGETARIAN FILTER ENGINE
===================================================== */


function applyVegetarianFilters() {

  filteredVegetarianPlaces =
    window.PrachinLife.modules.vegetarian.filterAndSortPlaces(
      getVegetarianDatasetV2First(),
      currentVegetarianProvince,
      userLocation,
      calculatePlaceDistance,
      window.PrachinLife.core.compareDistance,
      window.PrachinLife.core.compareTitle
    );

  currentVegetarianPage = 1;

  renderVegetarianPlaces();

  window.PrachinLife.ui.setText(
    "vegetarianResultCount",
    `${filteredVegetarianPlaces.length} ร้าน`
  );
}


/* =====================================================
SORT HELPERS
===================================================== */


/* =====================================================
EAT AREAS
===================================================== */

/* =====================================================
VEGETARIAN PROVINCES
===================================================== */

function buildVegetarianProvinceFilters() {

  const select =
    document.getElementById(
      "vegetarianProvinceSelect"
    );

  if (!select) {
    return;
  }

  const provinces =
    window.PrachinLife.modules.vegetarian.getProvinces(
      primaryVegetarianPlaces
    );

  select.innerHTML =
    '<option value="all">ทุกจังหวัด</option>'
    +
    provinces
      .map(
        province =>
          `<option value="${window.PrachinLife.core.escapeAttribute(province)}">${window.PrachinLife.core.escapeHtml(province)}</option>`
      )
      .join("");

  select.value =
    currentVegetarianProvince;
}


/* =====================================================
NEAR ME - EAT
===================================================== */

function activateNearMe() {

  window.PrachinLife?.core?.usageAnalytics?.track("near_me");

  if (userLocation) {

    userLocation = null;

    currentEatPage = 1;

    updateNearMeState(
      false
    );

    window.PrachinLife.ui.setText(
      "nearMeStatus",
      "กด “ใกล้ฉัน” เพื่อเรียงร้านตามระยะทาง"
    );

    updateEatButtons();

    applyEatFilters();

    showEatResult();

    return;
  }

  requestUserLocation(
    position => {

      userLocation =
        position;

      currentEatPage = 1;

      updateNearMeState(
        true
      );

      window.PrachinLife.ui.setText(
        "nearMeStatus",
        "กำลังเรียงร้านจากใกล้ไปไกล"
      );

      updateEatButtons();

      applyEatFilters();

      showEatResult();
    },

    "nearMeStatus"
  );
}


function updateNearMeState(
  active
) {

  const button =
    document.getElementById(
      "nearMeBtn"
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
}


/* =====================================================
NEAR ME - VEGETARIAN
===================================================== */

function activateVegetarianNearMe() {

  window.PrachinLife?.core?.usageAnalytics?.track("near_me");

  if (userLocation) {

    userLocation = null;

    currentVegetarianProvince =
      "all";

    currentVegetarianPage = 1;

    window.PrachinLife.modules.vegetarian.updateNearMeState(
      false
    );

    window.PrachinLife.ui.setText(
      "vegetarianNearMeStatus",
      "กด “ใกล้ฉัน” เพื่อเรียงร้านตามระยะทาง"
    );

    const provinceSelect =
      document.getElementById(
        "vegetarianProvinceSelect"
      );

    if (provinceSelect) {
      provinceSelect.value =
        currentVegetarianProvince;
    }

    applyVegetarianFilters();

    showVegetarianResult();

    return;
  }

  requestUserLocation(
    position => {

      userLocation =
        position;

      currentVegetarianProvince =
        "all";

      currentVegetarianPage = 1;

      window.PrachinLife.modules.vegetarian.updateNearMeState(
        true
      );

      window.PrachinLife.ui.setText(
        "vegetarianNearMeStatus",
        "กำลังเรียงร้านเจ / มังสวิรัติจากใกล้ไปไกล"
      );

      const provinceSelect =
        document.getElementById(
          "vegetarianProvinceSelect"
        );

      if (provinceSelect) {
        provinceSelect.value =
          currentVegetarianProvince;
      }

      applyVegetarianFilters();

      showVegetarianResult();
    },

    "vegetarianNearMeStatus"
  );
}


/* =====================================================
GO NEAR ME
===================================================== */

function bindGoEvents() {

  const button =
    document.getElementById(
      "goNearMeBtn"
    );

  if (button) {
    button.addEventListener(
      "click",
      activateGoNearMe
    );
  }
}


function activateGoNearMe() {

  window.PrachinLife?.core?.usageAnalytics?.track("near_me");

  if (userLocation) {

    userLocation = null;

    filteredGoPlaces =
      [...primaryGoPlaces];

    const button =
      document.getElementById(
        "goNearMeBtn"
      );

    if (button) {
      button.classList.remove(
        "active"
      );

      button.textContent =
        "📍 ใกล้ฉัน";
    }

    window.PrachinLife.ui.setText(
      "goNearMeStatus",
      "กด “ใกล้ฉัน” เพื่อเรียงสถานที่ตามระยะทาง"
    );

    renderGoPlaces();

    return;
  }

  requestUserLocation(
    position => {

      userLocation =
        position;

      filteredGoPlaces =
        primaryGoPlaces
          .map(
            place => ({
              ...place,

              _distance:
                calculatePlaceDistance(
                  place
                ),
            })
          )
          .sort(
            window.PrachinLife.core.compareDistance
          );

      const button =
        document.getElementById(
          "goNearMeBtn"
        );

      if (button) {
        button.classList.add(
          "active"
        );

        button.textContent =
          "✓ ใกล้ฉัน";
      }

      window.PrachinLife.ui.setText(
        "goNearMeStatus",
        "กำลังเรียงสถานที่จากใกล้ไปไกล"
      );

      renderGoPlaces();

    },
    "goNearMeStatus"
  );
}


/* =====================================================
REQUEST GEOLOCATION
===================================================== */

function requestUserLocation(
  onSuccess,
  statusId
) {

  if (
    !navigator.geolocation
  ) {

    window.PrachinLife.ui.setText(
      statusId,
      "อุปกรณ์นี้ไม่รองรับการใช้ตำแหน่ง"
    );

    return;
  }


  window.PrachinLife.ui.setText(
    statusId,
    "กำลังขอตำแหน่งของคุณ..."
  );


  navigator.geolocation
    .getCurrentPosition(

      position => {

        onSuccess({

          latitude:
            position.coords.latitude,

          longitude:
            position.coords.longitude,
        });
      },


      error => {

        console.warn(
          "Geolocation error:",
          error
        );


        userLocation = null;


        if (
          error.code === 1
        ) {

          window.PrachinLife.ui.setText(
            statusId,
            "ไม่ได้รับอนุญาตให้ใช้ตำแหน่ง"
          );
        }

        else {

          window.PrachinLife.ui.setText(
            statusId,
            "ไม่สามารถหาตำแหน่งได้ในขณะนี้"
          );
        }
      },


      {
        enableHighAccuracy:
          false,

        timeout:
          10000,

        maximumAge:
          300000,
      }
    );
}


/* =====================================================
DISTANCE
===================================================== */

function calculatePlaceDistance(
  place
) {
  if (!userLocation) {
    return null;
  }

  const latitude = Number(
    place?.location?.latitude
    ?? place?.latitude
    ?? place?.lat
  );

  const longitude = Number(
    place?.location?.longitude
    ?? place?.longitude
    ?? place?.lng
  );

  const userLatitude = Number(
    userLocation?.latitude
    ?? userLocation?.lat
  );

  const userLongitude = Number(
    userLocation?.longitude
    ?? userLocation?.lng
  );

  if (
    !Number.isFinite(latitude)
    || !Number.isFinite(longitude)
    || !Number.isFinite(userLatitude)
    || !Number.isFinite(userLongitude)
  ) {
    return null;
  }

  return window.PrachinLife.core.haversineDistance(
    userLatitude,
    userLongitude,
    latitude,
    longitude
  );
}



/* =====================================================
END PART 2
===================================================== */
/* =====================================================
RECOMMENDED RESULT
===================================================== */

function getDecisionAssistantPlaces() {
  const groups = [
    getEatDatasetV2First(),
    getVegetarianDatasetV2First(),
    getGoDatasetV2First(),
    getServiceDatasetV2First(),
  ];
  const seen = new Set();
  return groups.flat().filter(place => {
    const key = String(place?.id || `${place?.title || place?.name}|${place?.latitude || place?.lat}|${place?.longitude || place?.lng}`);
    if (seen.has(key)) return false;
    seen.add(key); return true;
  }).map(place => {
    if (!userLocation) return place;
    const d = calculatePlaceDistance(place);
    return Number.isFinite(d) ? {...place, _distance:d, distance_km:d} : place;
  });
}

function renderRecommended(
  mode = "all"
) {
  renderRecommendedDealRail();
  const list = document.getElementById("recommendedList");
  if (!list) return;

  const dealItems = rankInteresting(
    allPromotions.filter(promotion =>
      window.PrachinLife.core.matchesLocalScope(promotion,currentLocalProvince)
    )
  ).slice(0, 3).map(item => ({kind:"deal",item}));

  const engine = window.PrachinLife?.core?.decisionAssistant;
  const decisionResults = engine
    ? engine.recommend(getDecisionAssistantPlaces(), {limit:5})
    : [];
  if (decisionResults.length) window.PrachinLife?.core?.usageAnalytics?.track("decision_view");

  const pilotBrain =
    window.PrachinLife?.core?.pilotBrainV0;

  const pilotDecisionResults =
    pilotBrain
      ? pilotBrain.build(decisionResults)
      : decisionResults;
  const recommendedPlaceIdentityKey = place => {
    const contentType = String(
      place?.content_type
        || place?.main_category
        || "place"
    ).toLowerCase();

    const category = String(
      place?.category || ""
    ).toLowerCase();

    const title = String(
      place?.title || place?.name || ""
    )
      .toLocaleLowerCase("th-TH")
      .replace(/\b(?:service\s+station|gas\s+station|station)\b/g, " ")
      .replace(/ปั๊มน้ำมัน|ปั้มน้ำมัน|ปั๊ม|ปั้ม/g, " ")
      .replace(/[^0-9a-zก-๙]+/g, "")
      .trim();

    return `${contentType}|${category}|${title}`;
  };

  const seenRecommendedPlaces = new Set();

  const placeItems = pilotDecisionResults
    .filter(result => {
      const key = recommendedPlaceIdentityKey(
        result?.place
      );

      if (!key || seenRecommendedPlaces.has(key)) {
        return false;
      }

      seenRecommendedPlaces.add(key);
      return true;
    })
    .map(result => ({
      kind:"place", item:result.place, decision:result
    }));

  let items = [...placeItems, ...dealItems];
  if (mode === "latest") {
    items.sort((a,b) => parseDateValue(b.item.collected_at)-parseDateValue(a.item.collected_at));
  }
  items = items.slice(0, RECOMMENDED_LIMIT);
  list.innerHTML = items.map(renderRecommendedDetailedCard).join("");
  window.PrachinLife.ui.setText("recommendedResultCount", `${items.length} รายการ`);
}

/* =====================================================
RECOMMENDED DEAL RAIL - INDEX V1 STEP 2
===================================================== */

function renderRecommendedDealRail() {

  const rail =
    document.getElementById(
      "recommendedDealRail"
    );

  if (!rail) {
    return;
  }

  const deals =
    rankInteresting(
      allPromotions
    )
      .slice(
        0,
        8
      );

  if (deals.length === 0) {

    rail.innerHTML = `
      <div class="recommended-deal-empty">
        ยังไม่มีดีลหรือโปรโมชั่นในขณะนี้
      </div>
    `;

    return;
  }

  rail.innerHTML =
    deals
      .map(
        renderCompactDealCard
      )
      .join("");
}

/* =====================================================
INDEX V1 STEP 2.1 - COMPACT DEAL CARD
Presentation only
===================================================== */

function renderCompactDealCard(
  promotion
) {

  const title =
    window.PrachinLife.core.escapeHtml(
      promotion.title
      || promotion.product
      || "โปรโมชั่น"
    );

  const merchant =
    window.PrachinLife.core.escapeHtml(
      promotion.merchant
      || promotion.store
      || promotion.source
      || "โปรโมชั่น"
    );

  const typeLabel =
    window.PrachinLife.core.escapeHtml(
      getPromotionTypeLabel(
        promotion
      )
    );

  const actionLabel =
    window.PrachinLife.core.escapeHtml(
      getActionLabel(
        promotion
      )
    );

  const image =
    promotion.image_url
    || promotion.image
    || "";

  const imageBlock =
    image
      ? `
        <img
          class="compact-deal-image"
          src="${window.PrachinLife.core.escapeAttribute(image)}"
          alt="${title}"
          loading="lazy"
          onerror="this.parentElement.innerHTML='<div class=&quot;compact-deal-placeholder&quot;>🛍️</div>'"
        >
      `
      : `
        <div class="compact-deal-placeholder">
          🛍️
        </div>
      `;

  const sourceButton =
    promotion.source_url
      ? `
        <a
          class="compact-deal-button"
          href="${window.PrachinLife.core.escapeAttribute(promotion.source_url)}"
          target="_blank"
          rel="noopener noreferrer"
        >
          ${actionLabel}
          <span aria-hidden="true">→</span>
        </a>
      `
      : "";

  return `
    <article class="compact-deal-card">

      <div class="compact-deal-image-wrap">
        ${imageBlock}

        <span class="compact-deal-merchant">
          ${merchant}
        </span>
      </div>

      <div class="compact-deal-body">

        <div class="compact-deal-type">
          ${typeLabel}
        </div>

        <h4 class="compact-deal-title">
          ${title}
        </h4>

        ${
          sourceButton
            ? `
              <div class="compact-deal-actions">
                ${sourceButton}
              </div>
            `
            : ""
        }

      </div>

    </article>
  `;
}


/* =====================================================
INDEX V1 STEP 2.1 - RECOMMENDED DETAILED CARD
Presentation only
===================================================== */

function renderRecommendedDetailedCard(
  entry
) {

  if (!entry || !entry.item) {
    return "";
  }

  if (entry.kind === "deal") {

    const promotion =
      entry.item;

    const title =
      window.PrachinLife.core.escapeHtml(
        promotion.title
        || promotion.product
        || "โปรโมชั่น"
      );

    const merchant =
      window.PrachinLife.core.escapeHtml(
        promotion.merchant
        || promotion.store
        || promotion.source
        || "โปรโมชั่น"
      );

    const location =
      window.PrachinLife.core.escapeHtml(
        getPromotionLocationLabel(
          promotion
        )
      );

    const reason =
      window.PrachinLife.core.escapeHtml(
        getPromotionReason(
          promotion
        )
      );

    const image =
      promotion.image_url
      || promotion.image
      || "";

    const imageBlock =
      image
        ? `
          <img
            class="recommended-detail-image"
            src="${window.PrachinLife.core.escapeAttribute(image)}"
            alt="${title}"
            loading="lazy"
            onerror="this.parentElement.innerHTML='<div class=&quot;recommended-detail-placeholder&quot;>🛍️</div>'"
          >
        `
        : `
          <div class="recommended-detail-placeholder">
            🛍️
          </div>
        `;

    const action =
      promotion.source_url
        ? `
          <a
            class="recommended-detail-button"
            href="${window.PrachinLife.core.escapeAttribute(promotion.source_url)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            ${window.PrachinLife.core.escapeHtml(getActionLabel(promotion))}
            <span aria-hidden="true">→</span>
          </a>
        `
        : "";

    return `
      <article class="recommended-detail-card">

        <div class="recommended-detail-media">
          ${imageBlock}
        </div>

        <div class="recommended-detail-body">

          <div class="recommended-detail-kicker">
            ${merchant}
          </div>

          <h3>
            ${title}
          </h3>

          <div class="recommended-detail-meta">
            <span>
              📍 ${location}
            </span>

            ${
              promotion.verified
                ? `
                  <span>
                    ✓ จากแหล่งต้นทาง
                  </span>
                `
                : ""
            }
          </div>

          ${
            reason
              ? `
                <p>
                  ${reason}
                </p>
              `
              : ""
          }

          ${
            action
              ? `
                <div class="recommended-detail-actions">
                  ${action}
                </div>
              `
              : ""
          }

        </div>

      </article>
    `;
  }

  const place =
    entry.item;

  const contentType =
    String(
      place?.content_type
        || place?.main_category
        || ""
    ).toLowerCase();

  const isServicePlace =
    contentType === "service";

  const isVegetarianPlace =
    contentType === "vegetarian";

  const isGoPlace =
    contentType === "go";

  const title =
    window.PrachinLife.core.escapeHtml(
      place.title
      || place.name
      || "ไม่ระบุชื่อ"
    );

  let categoryLabel = "";

  if (isServicePlace) {
    categoryLabel =
      window.PrachinLife.modules.service
        ?.CATEGORY_LABELS?.[
          place?.category
        ]
      || place?.metadata?.category_label
      || "บริการ";
  }
  else if (isVegetarianPlace) {
    categoryLabel =
      place?.metadata?.category_label
      || "เจ / มังสวิรัติ";
  }
  else if (isGoPlace) {
    categoryLabel =
      place?.metadata?.category_label
      || "สถานที่น่าสนใจ";
  }
  else {
    categoryLabel =
      getEatCategoryLabel(
        place
      );
  }

  const category =
    window.PrachinLife.core.escapeHtml(
      categoryLabel
    );

  let locationLabel = "";

  if (isServicePlace) {
    locationLabel =
      window.PrachinLife.modules.service
        ?.getLocationLabel?.(
          place
        )
      || "";
  }

  if (!locationLabel) {
    locationLabel =
      getEatLocationLabel(
        place
      );
  }

  const location =
    window.PrachinLife.core.escapeHtml(
      locationLabel
      || "ไม่ระบุพื้นที่"
    );

  const mapUrl =
    window.PrachinLife.core.buildMapUrl(
      place
    );

  const distance =
    Number.isFinite(
      place._distance
    )
      ? window.PrachinLife.core.formatDistance(
          place._distance
        )
      : "";

  const imageGroup =
    isServicePlace
      ? "service"
      : isVegetarianPlace
        ? "vegetarian"
        : isGoPlace
          ? "go"
          : "eat";

  const imageBlock =
    window.PrachinLife.core.placeImage
      .renderPlaceImage(
        place,
        imageGroup,
        place?.title
        || place?.name
        || categoryLabel
      );

  return `
    <article class="recommended-detail-card">

      <div class="recommended-detail-media">
        ${imageBlock}
      </div>

      <div class="recommended-detail-body">

        <div class="recommended-detail-kicker">
          ${category}
        </div>

        <h3>
          ${title}
        </h3>

        <div class="recommended-detail-meta">

          <span>
            📍 ${location}
          </span>

          ${
            distance
              ? `
                <span>
                  ${window.PrachinLife.core.escapeHtml(distance)}
                </span>
              `
              : ""
          }

        </div>

        <p>
          ${window.PrachinLife.core.escapeHtml(
            entry.decision && window.PrachinLife?.core?.pilotBrainV0
              ? (
                  window.PrachinLife.core.pilotBrainV0.explain(entry.decision)
                  || window.PrachinLife.core.decisionAssistant?.reasonText(entry.decision)
                  || "สถานที่ที่ PrachinLife มีข้อมูลอยู่ในระบบ"
                )
              : (
                  entry.decision && window.PrachinLife?.core?.decisionAssistant
                    ? window.PrachinLife.core.decisionAssistant.reasonText(entry.decision)
                    : "สถานที่ที่ PrachinLife มีข้อมูลอยู่ในระบบ"
                )
          )}
        </p>

        ${
          entry.decision && window.PrachinLife?.core?.pilotBrainV0
            ? `
              <div class="recommended-detail-actions pilot-feedback-actions">
                <button
                  type="button"
                  class="recommended-detail-button"
                  data-pilot-feedback="helpful"
                  aria-pressed="false"
                >
                  ช่วยตัดสินใจได้
                </button>

                <button
                  type="button"
                  class="recommended-detail-button"
                  data-pilot-feedback="not_helpful"
                  aria-pressed="false"
                >
                  ยังไม่ค่อยช่วย
                </button>
              </div>
            `
            : ""
        }

        ${
          mapUrl
            ? `
              <div class="recommended-detail-actions">

                <a
                  class="recommended-detail-button"
                  data-pilot-map-action="1"
                  href="${window.PrachinLife.core.escapeAttribute(mapUrl)}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  เปิดแผนที่
                  <span aria-hidden="true">→</span>
                </a>

              </div>
            `
            : ""
        }

      </div>

    </article>
  `;
}

function renderRecommendedSearch(
  items
) {

  const list =
    document.getElementById(
      "recommendedList"
    );


  if (!list) {

    return;
  }


  const visible =
    items.slice(
      0,
      RECOMMENDED_LIMIT
    );


  if (
    visible.length === 0
  ) {

    list.innerHTML = `
      <div class="empty-state">

        <div class="empty-icon">
          🔎
        </div>

        <h3>
          ยังไม่พบข้อมูล
        </h3>

        <p>
          ลองใช้คำค้นอื่น
          หรือเลือกจากหมวดด้านบน
        </p>

      </div>
    `;


    window.PrachinLife.ui.setText(
      "recommendedResultCount",
      "0 รายการ"
    );


    return;
  }


  list.innerHTML =
    visible
      .map(
        item => {

          if (
            item.content_type
              === "deal"
          ) {

            const sourcePromotion =
              allPromotions.find(
                promotion =>
                  promotion.id
                    === item.id
              );


            return sourcePromotion
              ? renderPromotionCard(
                  sourcePromotion
                )
              : "";
          }


          if (
            item.content_type
              === "eat"
          ) {

            return renderEatCard(
              item
            );
          }


          if (
            item.content_type
              === "service"
          ) {

            return window.PrachinLife.modules.service
              ?.renderCard?.(item)
              || "";
          }


          return "";
        }
      )
      .join("");


  window.PrachinLife.ui.setText(
    "recommendedResultCount",
    `${visible.length} รายการ`
  );
}


/* =====================================================
RENDER SHOPPING
===================================================== */

function renderPromotions() {

  const list =
    document.getElementById(
      "promotionList"
    );


  const loadMoreBtn =
    document.getElementById(
      "loadMoreBtn"
    );


  if (!list) {

    return;
  }


  if (
    filteredPromotions.length
      === 0
  ) {

    list.innerHTML = "";


    window.PrachinLife.ui.showElement(
      "emptyState"
    );


    if (loadMoreBtn) {

      loadMoreBtn.classList.add(
        "hidden"
      );
    }


    return;
  }


  window.PrachinLife.ui.hideElement(
    "emptyState"
  );


  const visibleCount =
    currentPage
    *
    PAGE_SIZE;


  const visibleItems =
    filteredPromotions.slice(
      0,
      visibleCount
    );


  list.innerHTML =
    visibleItems
      .map(
        renderPromotionCard
      )
      .join("");


  if (loadMoreBtn) {

    loadMoreBtn.classList.toggle(
      "hidden",
      visibleCount
      >=
      filteredPromotions.length
    );
  }
}


/* =====================================================
SHOPPING CARD
===================================================== */

function renderPromotionCard(
  promotion
) {

  const title =
    window.PrachinLife.core.escapeHtml(
      promotion.title
      || "ไม่มีชื่อ"
    );


  const merchant =
    window.PrachinLife.core.escapeHtml(
      promotion.merchant
      || "ไม่ระบุแหล่ง"
    );


  const category =
    window.PrachinLife.core.escapeHtml(
      getPromotionCategoryLabel(
        promotion
      )
    );


  const typeLabel =
    window.PrachinLife.core.escapeHtml(
      getPromotionTypeLabel(
        promotion
      )
    );


  const locationLabel =
    window.PrachinLife.core.escapeHtml(
      getPromotionLocationLabel(
        promotion
      )
    );


  const smartReason =
    window.PrachinLife.core.escapeHtml(
      getPromotionReason(
        promotion
      )
    );


  const imageBlock =
    promotion.image_url
      ? `
        <img
          class="promotion-image"
          src="${window.PrachinLife.core.escapeAttribute(
            promotion.image_url
          )}"
          alt="${title}"
          loading="lazy"
        >
      `
      : `
        <div class="image-placeholder">
          🛒
        </div>
      `;


  const sourceButton =
    promotion.source_url
      ? `
        <a
          class="source-button"
          href="${window.PrachinLife.core.escapeAttribute(
            promotion.source_url
          )}"
          target="_blank"
          rel="noopener noreferrer"
        >
          ${window.PrachinLife.core.escapeHtml(
            getActionLabel(
              promotion
            )
          )}
          →
        </a>
      `
      : "";


  return `
    <article class="promotion-card">

      <div class="promotion-image-wrap">

        ${imageBlock}

        <span class="source-pill">
          ${merchant}
        </span>

      </div>


      <div class="promotion-body">

        <div class="promotion-meta">

          <strong>
            ${merchant}
          </strong>

          <span>•</span>

          <span>
            ${category}
          </span>

        </div>


        <div class="promotion-type-badge">
          ${typeLabel}
        </div>


        <div class="promotion-location">
          📍 ${locationLabel}
        </div>


        <h3 class="promotion-title">
          ${title}
        </h3>


        <p class="promotion-description">
          ${smartReason}
        </p>


        ${
          sourceButton
            ? `
              <div class="promotion-actions">
                ${sourceButton}
              </div>
            `
            : ""
        }

      </div>

    </article>
  `;
}


/* =====================================================
RENDER EAT
===================================================== */

function renderEatPlaces() {

  const list =
    document.getElementById(
      "eatList"
    );


  const loadMoreBtn =
    document.getElementById(
      "eatLoadMoreBtn"
    );


  if (!list) {

    return;
  }


  if (
    filteredEatPlaces.length
      === 0
  ) {

    list.innerHTML = "";


    window.PrachinLife.ui.showElement(
      "eatEmptyState"
    );


    if (loadMoreBtn) {

      loadMoreBtn.classList.add(
        "hidden"
      );
    }


    return;
  }


  window.PrachinLife.ui.hideElement(
    "eatEmptyState"
  );


  const visibleCount =
    currentEatPage
    *
    EAT_PAGE_SIZE;


  const visibleItems =
    filteredEatPlaces.slice(
      0,
      visibleCount
    );


  list.innerHTML =
    visibleItems
      .map(
        renderEatCard
      )
      .join("");


  if (loadMoreBtn) {

    loadMoreBtn.classList.toggle(
      "hidden",
      visibleCount
      >=
      filteredEatPlaces.length
    );
  }
}


/* =====================================================
RENDER VEGETARIAN
===================================================== */


function renderVegetarianPlaces() {

  window.PrachinLife.modules.vegetarian.renderPlaces(
    filteredVegetarianPlaces,
    currentVegetarianPage,
    VEGETARIAN_PAGE_SIZE
  );
}


/* =====================================================
EAT CARD
===================================================== */



function renderEatCard(
  place
) {
  const detail =
    window.PrachinLife.core.placeDetail.getDetail(
      place,
      "ปราจีนบุรี"
    );

  const title =
    window.PrachinLife.core.escapeHtml(
      detail.title || "ไม่ระบุชื่อร้าน"
    );

  const category =
    window.PrachinLife.core.escapeHtml(
      getEatCategoryLabel(place)
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
    <article class="promotion-card eat-card eat-v1-card" data-place-id="${window.PrachinLife.core.escapeAttribute(place?.id || "")}" data-v2-place-id="${window.PrachinLife.core.escapeAttribute(place?.metadata?.v2_place_id || "")}">
      <div class="promotion-image-wrap eat-image-wrap">

        ${window.PrachinLife.core.placeImage.renderPlaceImage(
          place,
          "eat",
          place?.title || place?.name || "ร้านอาหาร"
        )}

        <span class="source-pill">
          ${category}
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
}


/* =====================================================
EAT HELPERS
===================================================== */

function getEatCategoryLabel(
  place
) {

  const label =
    place.metadata
      ?.category_label;


  if (label) {

    return String(
      label
    );
  }


  const mapping = {

    restaurant:
      "ร้านอาหาร",

    cafe:
      "คาเฟ่",

    fast_food:
      "อาหารจานด่วน",

    food_court:
      "ศูนย์อาหาร",
  };


  return (
    mapping[
      place.category
    ]
    ||
    "อาหารและเครื่องดื่ม"
  );
}


function getEatLocationLabel(
  place
) {

  const location =
    place.location
    || {};


  const parts = [

    location.subdistrict,

    location.district,

    location.province,

  ]
    .filter(Boolean);


  const unique = [
    ...new Set(
      parts
    )
  ];


  if (
    unique.length === 0
  ) {

    return "ไม่ระบุพื้นที่";
  }


  return unique.join(
    " · "
  );
}


/* =====================================================
VEGETARIAN LOCATION
===================================================== */


/* =====================================================
MAP
===================================================== */


/* =====================================================
DISTANCE FORMAT
===================================================== */


/* =====================================================
PROMOTION HELPERS
===================================================== */

function getPromotionTypeLabel(
  promotion
) {

  if (
    promotion.promotion_type
      === "coupon"
  ) {

    return "คูปอง";
  }


  if (
    promotion.promotion_type
      === "member_offer"
  ) {

    return "สิทธิสมาชิก";
  }


  if (
    promotion.promotion_type
      === "product_deal"
  ) {

    return "ดีลสินค้า";
  }


  if (
    isCataloguePromotion(
      promotion
    )
  ) {

    return "แคตตาล็อก";
  }


  return "โปรโมชั่น";
}


function getPromotionCategoryLabel(
  promotion
) {

  if (
    promotion.promotion_type
      === "coupon"
  ) {

    return "ช่วยประหยัด";
  }


  if (
    promotion.promotion_type
      === "member_offer"
  ) {

    return "สิทธิสมาชิก";
  }


  if (
    isCataloguePromotion(
      promotion
    )
  ) {

    return "แคตตาล็อก";
  }


  return (
    promotion.category
    ||
    "โปรโมชั่น"
  );
}


function getPromotionReason(
  promotion
) {

  if (
    promotion.promotion_type
      === "coupon"
  ) {

    return (
      "คูปองหรือสิทธิ์ส่วนลด "
      +
      "ควรตรวจสอบเงื่อนไขก่อนใช้"
    );
  }


  if (
    promotion.promotion_type
      === "member_offer"
  ) {

    return (
      "สิทธิสำหรับสมาชิก "
      +
      "ที่อาจช่วยเพิ่มความคุ้มค่า"
    );
  }


  if (
    isCataloguePromotion(
      promotion
    )
  ) {

    return (
      "เปิดดูรายการโปรโมชั่น "
      +
      "จากแคตตาล็อกต้นทาง"
    );
  }


  return (
    "โปรโมชั่นจากแหล่งต้นทาง "
    +
    "กรุณาตรวจสอบรายละเอียด"
  );
}


function getPromotionLocationLabel(
  promotion
) {

  const scope =
    promotion.location_scope
    || "national";


  if (
    scope === "national"
  ) {

    return "ทั่วประเทศ";
  }


  if (
    scope === "province"
  ) {

    return (
      promotion.province
      ||
      "ระดับจังหวัด"
    );
  }


  if (
    scope === "district"
  ) {

    return [
      promotion.district,
      promotion.province,
    ]
      .filter(Boolean)
      .join(" · ");
  }


  if (
    scope === "branch"
  ) {

    return (
      promotion.branch_name
      ||
      "เฉพาะสาขา"
    );
  }


  return "ไม่ระบุพื้นที่";
}


function getActionLabel(
  promotion
) {

  if (
    promotion.promotion_type
      === "coupon"
  ) {

    return "ดูคูปอง";
  }


  if (
    promotion.promotion_type
      === "member_offer"
  ) {

    return "ดูสิทธิสมาชิก";
  }


  if (
    isCataloguePromotion(
      promotion
    )
  ) {

    return "เปิดแคตตาล็อก";
  }


  return "ดูรายละเอียด";
}


function isCataloguePromotion(
  promotion
) {

  const url =
    String(
      promotion.source_url
      || ""
    )
      .toLowerCase();


  const title =
    String(
      promotion.title
      || ""
    )
      .toLowerCase();


  return (
    url.includes(
      "/catalog/"
    )
    ||
    url.includes(
      "e-catalogue"
    )
    ||
    title.includes(
      "แคตตาล็อก"
    )
  );
}


/* =====================================================
DATE
===================================================== */

function sortLatest(
  data
) {

  return [
    ...data
  ].sort(
    (a, b) => {

      return (
        parseDateValue(
          b.collected_at
        )
        -
        parseDateValue(
          a.collected_at
        )
      );
    }
  );
}


function parseDateValue(
  value
) {

  if (!value) {

    return 0;
  }


  const date =
    new Date(
      value
    );


  const timestamp =
    date.getTime();


  return Number.isFinite(
    timestamp
  )
    ? timestamp
    : 0;
}


/* =====================================================
META
===================================================== */

function updateMeta() {

  const total =
    allContent.length
    +
    allVegetarianPlaces.length;


  window.PrachinLife.ui.setText(
    "totalCount",
    `${total} รายการ`
  );


  const sourceData = [
    ...allContent,
    ...allVegetarianPlaces,
  ];


  const dates =
    sourceData
      .map(
        item =>
          item.collected_at
      )
      .filter(Boolean)
      .map(
        value =>
          new Date(
            value
          )
      )
      .filter(
        date =>
          Number.isFinite(
            date.getTime()
          )
      );


  if (
    dates.length === 0
  ) {

    window.PrachinLife.ui.setText(
      "lastUpdate",
      "ยังไม่มีข้อมูล"
    );

    return;
  }


  const latest =
    new Date(
      Math.max(
        ...dates.map(
          date =>
            date.getTime()
        )
      )
    );


  try {

    window.PrachinLife.ui.setText(
      "lastUpdate",

      new Intl.DateTimeFormat(
        "th-TH",
        {
          dateStyle:
            "medium",

          timeStyle:
            "short",
        }
      ).format(
        latest
      )
    );

  }

  catch {

    window.PrachinLife.ui.setText(
      "lastUpdate",
      latest.toLocaleString()
    );
  }
}


/* =====================================================
COMING SOON
===================================================== */

function setComingSoonContent(
  icon,
  title,
  description
) {

  window.PrachinLife.ui.setText(
    "comingSoonResultIcon",
    icon
  );


  window.PrachinLife.ui.setText(
    "comingSoonResultTitle",
    title
  );


  window.PrachinLife.ui.setText(
    "comingSoonResultDescription",
    description
  );
}


/* =====================================================
SHOW / HIDE
===================================================== */

function hideAllOptionGroups() {

  [
    "recommendedOptions",
    "shoppingOptions",
    "eatOptions",
    "vegetarianOptions",
    "goOptions",
    "servicesOptions",
  ]
    .forEach(
      window.PrachinLife.ui.hideElement
    );
}


function hideAllResultSections() {

  [
    "recommendedResultSection",
    "shoppingResultSection",
    "eatResultSection",
    "vegetarianResultSection",
    "goResultSection",
    "serviceResultSection",
    "comingSoonResultSection",
  ]
    .forEach(
      window.PrachinLife.ui.hideElement
    );
}


/* =====================================================
SCROLL
===================================================== */

function scrollToResults() {

  const section =
    document.getElementById(
      "results"
    );


  if (!section) {

    return;
  }


  setTimeout(
    () => {

      section.scrollIntoView(
        {
          behavior:
            "smooth",

          block:
            "start",
        }
      );
    },
    50
  );
}


/* =====================================================
TEXT
===================================================== */

/* =====================================================
TOAST
===================================================== */

function showToast(
  message
) {

  const toast =
    document.getElementById(
      "toast"
    );


  if (!toast) {

    return;
  }


  toast.textContent =
    message;


  toast.classList.add(
    "show"
  );


  if (toastTimer) {

    clearTimeout(
      toastTimer
    );
  }


  toastTimer =
    setTimeout(
      () => {

        toast.classList.remove(
          "show"
        );
      },
      2200
    );
}


/* =====================================================
SECURITY
===================================================== */


/* =====================================================
END APP.JS
===================================================== */
