const DATA_URL = "promotions.json";
const INDEX_URL = "prachinlife_index.json";

const PAGE_SIZE = 8;
const EAT_PAGE_SIZE = 8;
const RECOMMENDED_LIMIT = 8;


let allPromotions = [];
let filteredPromotions = [];

let allContent = [];

let allEatPlaces = [];
let filteredEatPlaces = [];

let currentPage = 1;

let currentSearch = "";

let currentMerchant = "all";
let currentType = "all";
let currentSmart = "recommended";

let currentEatType = "all";
let currentEatArea = "all";
let currentEatPage = 1;

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
      "กำลังเริ่มระบบ..."
    );

    bindEvents();

    setText(
      "recommendedResultCount",
      "กำลังโหลดข้อมูล..."
    );

    await Promise.all([
      loadPromotions(),
      loadCommonIndex(),
    ]);

    prepareEatPlaces();

    buildEatAreaFilters();

    updateMeta();

    applyFilters();

    applyEatFilters();

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
      "ERROR: " + error.message
    );
  }
}


/* =====================================================
EVENTS
===================================================== */

function bindEvents() {

  bindSearchEvents();

  bindRefreshEvent();

  bindMainCategoryEvents();

  bindRecommendedEvents();

  bindShoppingEvents();

  bindEatEvents();

  bindLoadMoreEvents();

  bindResetEvent();
}


/* =====================================================
SEARCH EVENTS
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

        if (
          event.key === "Enter"
        ) {

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

      showToast(
        "กำลังโหลดข้อมูลล่าสุด..."
      );

      await Promise.all([
        loadPromotions(true),
        loadCommonIndex(true),
      ]);

      prepareEatPlaces();

      buildEatAreaFilters();

      updateMeta();

      applyFilters();

      applyEatFilters();

      renderRecommended();

      showToast(
        "โหลดข้อมูลล่าสุดแล้ว"
      );
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
    category === "recommended"
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
    category === "shopping"
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
    category === "eat"
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
    category === "go"
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
      "กำลังเตรียมข้อมูลสถานที่ท่องเที่ยว กิจกรรม และที่น่าแวะในปราจีนบุรี"
    );
  }


  else if (
    category === "services"
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
RECOMMENDED
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
              button.dataset
                .recommendedAction
              || "all";


            updateRecommendedButtons(
              action
            );


            if (
              action === "shopping"
            ) {

              setMainCategory(
                "shopping",
                true
              );

              return;
            }


            if (
              action === "eat"
            ) {

              setMainCategory(
                "eat",
                true
              );

              return;
            }


            if (
              action === "latest"
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
          button.dataset
            .recommendedAction
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

            currentType =
              "all";

            currentPage =
              1;

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

            currentPage =
              1;

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

            currentPage =
              1;

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
          (
            currentType === "all"
            &&
            button.dataset.smart
            === currentSmart
          )
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
          () =>
