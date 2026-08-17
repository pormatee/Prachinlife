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
const INDEX_URL = "prachinlife_index.json";
const VEGETARIAN_URL = "vegetarian_index.json";

const PAGE_SIZE = 8;
const EAT_PAGE_SIZE = 8;
const VEGETARIAN_PAGE_SIZE = 8;
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
let filteredVegetarianPlaces = [];


let currentPage = 1;
let currentEatPage = 1;
let currentVegetarianPage = 1;

let currentMerchant = "all";
let currentType = "all";
let currentSmart = "recommended";

let currentEatType = "all";
let currentEatArea = "all";

let currentVegetarianProvince = "all";

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


async function init() {

  try {

    setText(
      "recommendedResultCount",
      "กำลังโหลดข้อมูล..."
    );


    bindEvents();


    await Promise.all([
      loadPromotions(),
      loadCommonIndex(),
      loadVegetarianIndex(),
    ]);


    prepareEatPlaces();

    prepareVegetarianPlaces();


    buildEatAreaFilters();

    buildVegetarianProvinceFilters();


    updateMeta();

    applyFilters();

    applyEatFilters();

    applyVegetarianFilters();


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


    setText(
      "recommendedResultCount",
      "เกิดข้อผิดพลาดในการโหลดข้อมูล"
    );
  }
}


/* =====================================================
EVENT BINDING
===================================================== */

function bindEvents() {

  bindSearchEvents();

  bindRefreshEvent();

  bindMainCategoryEvents();

  bindRecommendedEvents();

  bindShoppingEvents();

  bindEatEvents();

  bindVegetarianEvents();

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
        ]);


        prepareEatPlaces();

        prepareVegetarianPlaces();


        buildEatAreaFilters();

        buildVegetarianProvinceFilters();


        updateMeta();

        applyFilters();

        applyEatFilters();

        applyVegetarianFilters();


        if (
          currentMainCategory ===
          "recommended"
        ) {

          renderRecommended();
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


function setMainCategory(
  category,
  scrollToResult = true
) {

  currentMainCategory =
    category;


  updateMainCategoryButtons();

  hideAllOptionGroups();

  hideAllResultSections();


  if (
    category ===
    "recommended"
  ) {

    showElement(
      "recommendedOptions"
    );

    showElement(
      "recommendedResultSection"
    );

    renderRecommended();
  }


  else if (
    category ===
    "shopping"
  ) {

    showElement(
      "shoppingOptions"
    );

    showElement(
      "shoppingResultSection"
    );

    applyFilters();
  }


  else if (
    category ===
    "eat"
  ) {

    showElement(
      "eatOptions"
    );

    showElement(
      "eatResultSection"
    );

    applyEatFilters();
  }


  else if (
    category ===
    "vegetarian"
  ) {

    showElement(
      "vegetarianOptions"
    );

    showElement(
      "vegetarianResultSection"
    );

    applyVegetarianFilters();
  }


  else if (
    category ===
    "go"
  ) {

    showElement(
      "goOptions"
    );

    showElement(
      "comingSoonResultSection"
    );


    setComingSoonContent(
      "📍",
      "เที่ยวไหนดี",
      "กำลังเตรียมข้อมูลสถานที่ท่องเที่ยว กิจกรรม และที่น่าแวะ"
    );
  }


  else if (
    category ===
    "services"
  ) {

    showElement(
      "servicesOptions"
    );

    showElement(
      "comingSoonResultSection"
    );


    setComingSoonContent(
      "🔧",
      "บริการใกล้ตัว",
      "กำลังเตรียมข้อมูลร้าน ช่าง และบริการที่ใช้ในชีวิตประจำวัน"
    );
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


  document
    .querySelectorAll(
      "[data-merchant]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentMerchant =
              button.dataset.merchant
              || "all";

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


  showElement(
    "shoppingOptions"
  );

  showElement(
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


function bindDynamicEatAreaEvents() {

  document
    .querySelectorAll(
      "[data-eat-area]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentEatArea =
              button.dataset.eatArea
              || "all";

            currentEatPage = 1;

            userLocation = null;


            updateNearMeState(
              false
            );

            updateEatButtons();

            applyEatFilters();

            showEatResult();
          }
        );
      }
    );
}


function showEatResult() {

  currentMainCategory =
    "eat";


  updateMainCategoryButtons();

  hideAllOptionGroups();

  hideAllResultSections();


  showElement(
    "eatOptions"
  );

  showElement(
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


  document
    .querySelectorAll(
      "[data-eat-area]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          button.dataset.eatArea
            === currentEatArea
        );
      }
    );
}


/* =====================================================
VEGETARIAN EVENTS
===================================================== */

function bindVegetarianEvents() {

  const nearMeBtn =
    document.getElementById(
      "vegetarianNearMeBtn"
    );


  if (nearMeBtn) {

    nearMeBtn.addEventListener(
      "click",
      activateVegetarianNearMe
    );
  }


  bindDynamicVegetarianProvinceEvents();
}


function bindDynamicVegetarianProvinceEvents() {

  document
    .querySelectorAll(
      "[data-vegetarian-province]"
    )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentVegetarianProvince =
              button.dataset
                .vegetarianProvince
              || "all";

            currentVegetarianPage = 1;

            userLocation = null;


            updateVegetarianNearMeState(
              false
            );


            updateVegetarianProvinceButtons();

            applyVegetarianFilters();

            showVegetarianResult();
          }
        );
      }
    );
}


function showVegetarianResult() {

  currentMainCategory =
    "vegetarian";


  updateMainCategoryButtons();

  hideAllOptionGroups();

  hideAllResultSections();


  showElement(
    "vegetarianOptions"
  );

  showElement(
    "vegetarianResultSection"
  );


  scrollToResults();
}


function updateVegetarianProvinceButtons() {

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
            currentVegetarianProvince
        );
      }
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


    setText(
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


    setText(
      "vegetarianResultCount",
      "โหลดข้อมูลไม่สำเร็จ"
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
      item =>
        item
        &&
        item.content_type
          === "eat"
    );


  filteredEatPlaces =
    [...allEatPlaces];


  currentEatPage = 1;
}


/* =====================================================
PREPARE VEGETARIAN
===================================================== */

function prepareVegetarianPlaces() {

  filteredVegetarianPlaces =
    [...allVegetarianPlaces];


  currentVegetarianPage = 1;
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


  const normalizedQuery =
    query.toLowerCase();


  const vegetarianMatches =
    allVegetarianPlaces.filter(
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


        return text.includes(
          normalizedQuery
        );
      }
    );


  if (
    vegetarianMatches.length > 0
    &&
    /เจ|มังสวิรัติ|vegetarian|vegan/i.test(
      query
    )
  ) {

    currentMainCategory =
      "vegetarian";


    filteredVegetarianPlaces =
      vegetarianMatches;


    currentVegetarianPage = 1;


    updateMainCategoryButtons();

    hideAllOptionGroups();

    hideAllResultSections();


    showElement(
      "vegetarianOptions"
    );

    showElement(
      "vegetarianResultSection"
    );


    renderVegetarianPlaces();


    setText(
      "vegetarianResultCount",
      `${filteredVegetarianPlaces.length} ร้าน`
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
      );


    currentPage = 1;


    updateMainCategoryButtons();

    hideAllOptionGroups();

    hideAllResultSections();


    showElement(
      "shoppingOptions"
    );

    showElement(
      "shoppingResultSection"
    );


    renderPromotions();


    setText(
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


    showElement(
      "eatOptions"
    );

    showElement(
      "eatResultSection"
    );


    renderEatPlaces();


    setText(
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


  showElement(
    "recommendedOptions"
  );

  showElement(
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


        return (
          matchesMerchant
          &&
          matchesType
          &&
          matchesSmart
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


  setText(
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
    allEatPlaces.filter(
      place => {

        const matchesType =
          currentEatType === "all"
          ||
          place.category
            === currentEatType
          ||
          place.original_type
            === currentEatType;


        const area =
          getEatAreaValue(
            place
          );


        const matchesArea =
          currentEatArea === "all"
          ||
          area
            === currentEatArea;


        return (
          matchesType
          &&
          matchesArea
        );
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
          compareDistance
        );
  }

  else {

    filteredEatPlaces.sort(
      compareTitle
    );
  }


  currentEatPage = 1;


  renderEatPlaces();


  setText(
    "eatResultCount",
    `${filteredEatPlaces.length} ร้าน`
  );
}


/* =====================================================
VEGETARIAN FILTER ENGINE
===================================================== */

function applyVegetarianFilters() {

  filteredVegetarianPlaces =
    allVegetarianPlaces.filter(
      place => {

        if (
          currentVegetarianProvince
          === "all"
        ) {

          return true;
        }


        return (
          getVegetarianProvince(
            place
          )
          ===
          currentVegetarianProvince
        );
      }
    );


  if (userLocation) {

    filteredVegetarianPlaces =
      filteredVegetarianPlaces
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
          compareDistance
        );
  }

  else {

    filteredVegetarianPlaces.sort(
      compareTitle
    );
  }


  currentVegetarianPage = 1;


  renderVegetarianPlaces();


  setText(
    "vegetarianResultCount",
    `${filteredVegetarianPlaces.length} ร้าน`
  );
}


/* =====================================================
SORT HELPERS
===================================================== */

function compareTitle(
  a,
  b
) {

  return String(
    a.title
    || ""
  ).localeCompare(
    String(
      b.title
      || ""
    ),
    "th"
  );
}


function compareDistance(
  a,
  b
) {

  const distanceA =
    Number.isFinite(
      a._distance
    )
      ? a._distance
      : Infinity;


  const distanceB =
    Number.isFinite(
      b._distance
    )
      ? b._distance
      : Infinity;


  if (
    distanceA !==
    distanceB
  ) {

    return (
      distanceA
      -
      distanceB
    );
  }


  return compareTitle(
    a,
    b
  );
}


/* =====================================================
EAT AREAS
===================================================== */

function getEatAreaValue(
  place
) {

  const location =
    place.location
    || {};


  return (
    location.district
    ||
    location.subdistrict
    ||
    "ไม่ระบุพื้นที่"
  );
}


function buildEatAreaFilters() {

  const container =
    document.getElementById(
      "eatAreaFilters"
    );


  if (!container) {

    return;
  }


  const areas =
    [
      ...new Set(
        allEatPlaces
          .map(
            getEatAreaValue
          )
          .filter(
            area =>
              area
              &&
              area !==
              "ไม่ระบุพื้นที่"
          )
      )
    ]
      .sort(
        (a, b) =>
          String(a)
            .localeCompare(
              String(b),
              "th"
            )
      );


  const buttons = [

    `
      <button
        type="button"
        class="filter-button active"
        data-eat-area="all"
      >
        ทุกพื้นที่
      </button>
    `

  ];


  for (
    const area
    of areas
  ) {

    buttons.push(
      `
        <button
          type="button"
          class="filter-button"
          data-eat-area="${escapeAttribute(area)}"
        >
          ${escapeHtml(area)}
        </button>
      `
    );
  }


  container.innerHTML =
    buttons.join("");


  bindDynamicEatAreaEvents();

  updateEatButtons();
}


/* =====================================================
VEGETARIAN PROVINCES
===================================================== */

function getVegetarianProvince(
  place
) {

  return (
    place.location
      ?.province
    ||
    ""
  );
}


function buildVegetarianProvinceFilters() {

  const container =
    document.getElementById(
      "vegetarianProvinceFilters"
    );


  if (!container) {

    return;
  }


  const provinces =
    [
      ...new Set(
        allVegetarianPlaces
          .map(
            getVegetarianProvince
          )
          .filter(Boolean)
      )
    ]
      .sort(
        (a, b) =>
          String(a)
            .localeCompare(
              String(b),
              "th"
            )
      );


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


  for (
    const province
    of provinces
  ) {

    buttons.push(
      `
        <button
          type="button"
          class="filter-button"
          data-vegetarian-province="${escapeAttribute(province)}"
        >
          ${escapeHtml(province)}
        </button>
      `
    );
  }


  container.innerHTML =
    buttons.join("");


  bindDynamicVegetarianProvinceEvents();

  updateVegetarianProvinceButtons();
}


/* =====================================================
NEAR ME - EAT
===================================================== */

function activateNearMe() {

  requestUserLocation(
    position => {

      userLocation =
        position;


      currentEatArea =
        "all";

      currentEatPage = 1;


      updateNearMeState(
        true
      );


      setText(
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
  }
}


/* =====================================================
NEAR ME - VEGETARIAN
===================================================== */

function activateVegetarianNearMe() {

  requestUserLocation(
    position => {

      userLocation =
        position;


      currentVegetarianProvince =
        "all";

      currentVegetarianPage = 1;


      updateVegetarianNearMeState(
        true
      );


      setText(
        "vegetarianNearMeStatus",
        "กำลังเรียงร้านเจ / มังสวิรัติจากใกล้ไปไกล"
      );


      updateVegetarianProvinceButtons();

      applyVegetarianFilters();

      showVegetarianResult();
    },

    "vegetarianNearMeStatus"
  );
}


function updateVegetarianNearMeState(
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

    setText(
      statusId,
      "อุปกรณ์นี้ไม่รองรับการใช้ตำแหน่ง"
    );

    return;
  }


  setText(
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

          setText(
            statusId,
            "ไม่ได้รับอนุญาตให้ใช้ตำแหน่ง"
          );
        }

        else {

          setText(
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


  const latitude =
    Number(
      place.location
        ?.latitude
    );


  const longitude =
    Number(
      place.location
        ?.longitude
    );


  if (
    !Number.isFinite(
      latitude
    )
    ||
    !Number.isFinite(
      longitude
    )
  ) {

    return null;
  }


  return haversineDistance(
    userLocation.latitude,
    userLocation.longitude,
    latitude,
    longitude
  );
}


function haversineDistance(
  lat1,
  lon1,
  lat2,
  lon2
) {

  const earthRadiusKm =
    6371;


  const toRadians =
    value =>
      value
      *
      Math.PI
      /
      180;


  const dLat =
    toRadians(
      lat2 - lat1
    );


  const dLon =
    toRadians(
      lon2 - lon1
    );


  const a =
    Math.sin(
      dLat / 2
    )
    ** 2

    +

    Math.cos(
      toRadians(lat1)
    )

    *

    Math.cos(
      toRadians(lat2)
    )

    *

    Math.sin(
      dLon / 2
    )
    ** 2;


  const c =
    2
    *
    Math.atan2(
      Math.sqrt(a),
      Math.sqrt(
        1 - a
      )
    );


  return (
    earthRadiusKm
    *
    c
  );
}


/* =====================================================
END PART 2
===================================================== */
/* =====================================================
RECOMMENDED RESULT
===================================================== */

function renderRecommended(
  mode = "all"
) {

  const list =
    document.getElementById(
      "recommendedList"
    );


  if (!list) {

    return;
  }


  const dealItems =
    rankInteresting(
      allPromotions
    )
      .slice(
        0,
        4
      )
      .map(
        item => ({
          kind:
            "deal",

          item,
        })
      );


  const eatItems =
    [...allEatPlaces]
      .sort(
        compareTitle
      )
      .slice(
        0,
        4
      )
      .map(
        item => ({
          kind:
            "eat",

          item,
        })
      );


  let items = [
    ...dealItems,
    ...eatItems,
  ];


  if (
    mode ===
    "latest"
  ) {

    items.sort(
      (a, b) => {

        return (
          parseDateValue(
            b.item
              .collected_at
          )
          -
          parseDateValue(
            a.item
              .collected_at
          )
        );
      }
    );
  }


  items =
    items.slice(
      0,
      RECOMMENDED_LIMIT
    );


  list.innerHTML =
    items
      .map(
        entry => {

          if (
            entry.kind ===
            "deal"
          ) {

            return renderPromotionCard(
              entry.item
            );
          }


          return renderEatCard(
            entry.item
          );
        }
      )
      .join("");


  setText(
    "recommendedResultCount",
    `${items.length} รายการ`
  );
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


    setText(
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


          return "";
        }
      )
      .join("");


  setText(
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


    showElement(
      "emptyState"
    );


    if (loadMoreBtn) {

      loadMoreBtn.classList.add(
        "hidden"
      );
    }


    return;
  }


  hideElement(
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
    escapeHtml(
      promotion.title
      || "ไม่มีชื่อ"
    );


  const merchant =
    escapeHtml(
      promotion.merchant
      || "ไม่ระบุแหล่ง"
    );


  const category =
    escapeHtml(
      getPromotionCategoryLabel(
        promotion
      )
    );


  const typeLabel =
    escapeHtml(
      getPromotionTypeLabel(
        promotion
      )
    );


  const locationLabel =
    escapeHtml(
      getPromotionLocationLabel(
        promotion
      )
    );


  const smartReason =
    escapeHtml(
      getPromotionReason(
        promotion
      )
    );


  const imageBlock =
    promotion.image_url
      ? `
        <img
          class="promotion-image"
          src="${escapeAttribute(
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
          href="${escapeAttribute(
            promotion.source_url
          )}"
          target="_blank"
          rel="noopener noreferrer"
        >
          ${escapeHtml(
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


    showElement(
      "eatEmptyState"
    );


    if (loadMoreBtn) {

      loadMoreBtn.classList.add(
        "hidden"
      );
    }


    return;
  }


  hideElement(
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


  if (
    filteredVegetarianPlaces.length
      === 0
  ) {

    list.innerHTML = "";


    showElement(
      "vegetarianEmptyState"
    );


    if (loadMoreBtn) {

      loadMoreBtn.classList.add(
        "hidden"
      );
    }


    return;
  }


  hideElement(
    "vegetarianEmptyState"
  );


  const visibleCount =
    currentVegetarianPage
    *
    VEGETARIAN_PAGE_SIZE;


  const visibleItems =
    filteredVegetarianPlaces.slice(
      0,
      visibleCount
    );


  list.innerHTML =
    visibleItems
      .map(
        renderVegetarianCard
      )
      .join("");


  if (loadMoreBtn) {

    loadMoreBtn.classList.toggle(
      "hidden",
      visibleCount
      >=
      filteredVegetarianPlaces.length
    );
  }
}


/* =====================================================
VEGETARIAN CARD
===================================================== */

function renderVegetarianCard(
  place
) {

  const title =
    escapeHtml(
      place.title
      || "ไม่ระบุชื่อร้าน"
    );


  const location =
    escapeHtml(
      getVegetarianLocationLabel(
        place
      )
    );


  const distance =
    Number.isFinite(
      place._distance
    )
      ? formatDistance(
          place._distance
        )
      : "";


  const openingHours =
    place.metadata
      ?.opening_hours
      ? escapeHtml(
          place.metadata
            .opening_hours
        )
      : "";


  const mapUrl =
    buildEatMapUrl(
      place
    );


  const sourceUrl =
    place.source_url
    ||
    place.metadata
      ?.source_url
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
                  📍 ${escapeHtml(
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
                  href="${escapeAttribute(
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
                  href="${escapeAttribute(
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
}


/* =====================================================
EAT CARD
===================================================== */

function renderEatCard(
  place
) {

  const title =
    escapeHtml(
      place.title
      || "ไม่ระบุชื่อ"
    );


  const category =
    escapeHtml(
      getEatCategoryLabel(
        place
      )
    );


  const location =
    escapeHtml(
      getEatLocationLabel(
        place
      )
    );


  const mapUrl =
    buildEatMapUrl(
      place
    );


  const distance =
    Number.isFinite(
      place._distance
    )
      ? formatDistance(
          place._distance
        )
      : "";


  const openingHours =
    place.metadata
      ?.opening_hours
      ? escapeHtml(
          place.metadata
            .opening_hours
        )
      : "";


  return `
    <article class="promotion-card eat-card">

      <div class="promotion-image-wrap eat-image-wrap">

        <div class="image-placeholder eat-placeholder">
          ${
            place.category === "cafe"
              ? "☕"
              : "🍜"
          }
        </div>


        <span class="source-pill">
          ${category}
        </span>

      </div>


      <div class="promotion-body">

        <div class="promotion-meta">

          <strong>
            ${category}
          </strong>

          ${
            distance
              ? `
                <span>•</span>
                <span>
                  📍 ${escapeHtml(
                    distance
                  )}
                </span>
              `
              : ""
          }

        </div>


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
                🕒 ${openingHours}
              </p>
            `
            : ""
        }


        ${
          mapUrl
            ? `
              <div class="promotion-actions">

                <a
                  class="source-button"
                  href="${escapeAttribute(
                    mapUrl
                  )}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  เปิดแผนที่ →
                </a>

              </div>
            `
            : ""
        }

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

function getVegetarianLocationLabel(
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
    unique.length > 0
  ) {

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
    Number.isFinite(
      latitude
    )
    &&
    Number.isFinite(
      longitude
    )
  ) {

    return "ดูตำแหน่งจากแผนที่";
  }


  return "ไม่ระบุพื้นที่";
}


/* =====================================================
MAP
===================================================== */

function buildEatMapUrl(
  place
) {

  const latitude =
    Number(
      place.location
        ?.latitude
    );


  const longitude =
    Number(
      place.location
        ?.longitude
    );


  if (
    Number.isFinite(
      latitude
    )
    &&
    Number.isFinite(
      longitude
    )
  ) {

    return (
      "https://www.google.com/maps/search/"
      +
      "?api=1&query="
      +
      encodeURIComponent(
        `${latitude},${longitude}`
      )
    );
  }


  const title =
    String(
      place.title
      || ""
    ).trim();


  if (!title) {

    return "";
  }


  return (
    "https://www.google.com/maps/search/"
    +
    "?api=1&query="
    +
    encodeURIComponent(
      title
    )
  );
}


/* =====================================================
DISTANCE FORMAT
===================================================== */

function formatDistance(
  distanceKm
) {

  if (
    distanceKm < 1
  ) {

    return (
      `${Math.round(
        distanceKm * 1000
      )} ม.`
    );
  }


  if (
    distanceKm < 10
  ) {

    return (
      `${distanceKm.toFixed(
        1
      )} กม.`
    );
  }


  return (
    `${Math.round(
      distanceKm
    )} กม.`
  );
}


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


  setText(
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

    setText(
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

    setText(
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

    setText(
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

  setText(
    "comingSoonResultIcon",
    icon
  );


  setText(
    "comingSoonResultTitle",
    title
  );


  setText(
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
      hideElement
    );
}


function hideAllResultSections() {

  [
    "recommendedResultSection",
    "shoppingResultSection",
    "eatResultSection",
    "vegetarianResultSection",
    "comingSoonResultSection",
  ]
    .forEach(
      hideElement
    );
}


function showElement(
  id
) {

  const element =
    document.getElementById(
      id
    );


  if (element) {

    element.classList.remove(
      "hidden"
    );
  }
}


function hideElement(
  id
) {

  const element =
    document.getElementById(
      id
    );


  if (element) {

    element.classList.add(
      "hidden"
    );
  }
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

function setText(
  id,
  value
) {

  const element =
    document.getElementById(
      id
    );


  if (element) {

    element.textContent =
      value;
  }
}


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

function escapeHtml(
  value
) {

  return String(
    value ?? ""
  )
    .replaceAll(
      "&",
      "&amp;"
    )
    .replaceAll(
      "<",
      "&lt;"
    )
    .replaceAll(
      ">",
      "&gt;"
    )
    .replaceAll(
      '"',
      "&quot;"
    )
    .replaceAll(
      "'",
      "&#039;"
    );
}


function escapeAttribute(
  value
) {

  return escapeHtml(
    value
  );
}


/* =====================================================
END APP.JS
===================================================== */
