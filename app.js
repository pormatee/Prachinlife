const DATA_URL = "promotions.json";
const PAGE_SIZE = 8;

let allPromotions = [];
let filteredPromotions = [];
let currentPage = 1;
let currentSearch = "";
let currentMerchant = "all";
let currentType = "all";
let toastTimer = null;


document.addEventListener(
  "DOMContentLoaded",
  init
);


async function init() {
  bindEvents();
  await loadPromotions();
}


/* =====================================================
EVENTS
===================================================== */

function bindEvents() {

  const searchInput =
    document.getElementById("searchInput");

  const searchBtn =
    document.getElementById("searchBtn");

  const refreshBtn =
    document.getElementById("refreshBtn");

  const resetBtn =
    document.getElementById("resetBtn");

  const loadMoreBtn =
    document.getElementById("loadMoreBtn");


  if (searchInput) {

    searchInput.addEventListener(
      "input",
      event => {

        currentSearch =
          event.target.value
            .trim()
            .toLowerCase();

        currentPage = 1;

        applyFilters();
      }
    );


    searchInput.addEventListener(
      "keydown",
      event => {

        if (event.key === "Enter") {
          applySearchFromInput();
        }
      }
    );
  }


  if (searchBtn) {

    searchBtn.addEventListener(
      "click",
      applySearchFromInput
    );
  }


  if (refreshBtn) {

    refreshBtn.addEventListener(
      "click",
      async () => {

        showToast(
          "กำลังโหลดข้อมูลล่าสุด..."
        );

        await loadPromotions(
          true
        );
      }
    );
  }


  if (resetBtn) {

    resetBtn.addEventListener(
      "click",
      resetSearch
    );
  }


  if (loadMoreBtn) {

    loadMoreBtn.addEventListener(
      "click",
      () => {

        currentPage++;

        renderPromotions();
      }
    );
  }


  document
    .querySelectorAll("[data-search]")
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            const value =
              button.dataset.search || "";

            setSearch(
              value
            );
          }
        );
      }
    );


  document
    .querySelectorAll("[data-quick]")
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            handleQuickAction(
              button.dataset.quick
            );
          }
        );
      }
    );
  document
    .querySelectorAll("[data-merchant]")
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentMerchant =
              button.dataset.merchant
              || "all";

            // เมื่อเปลี่ยนร้าน ให้เริ่มจากทุกประเภท
            // ป้องกัน filter เดิมค้างจนดูเหมือนไม่มีข้อมูล
            currentType = "all";

            currentPage = 1;

            updateActiveFilterButtons(
              "merchant"
            );

            updateActiveFilterButtons(
              "type"
            );

            applyFilters();
          }
        );
      }
    );


  document
    .querySelectorAll("[data-type]")
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            currentType =
              button.dataset.type
              || "all";

            currentPage = 1;

            updateActiveFilterButtons(
              "type"
            );

            applyFilters();
          }
        );
      }
    );
}


/* =====================================================
LOAD
===================================================== */

async function loadPromotions(
  forceRefresh = false
) {

  setLoading();

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
        `HTTP ${response.status}`
      );
    }


    const data =
      await response.json();


    if (Array.isArray(data)) {

      allPromotions =
        normalizeClientData(
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
        normalizeClientData(
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


    filteredPromotions =
      [...allPromotions];


    currentPage = 1;

    applyFilters();

    updateMeta();


    if (forceRefresh) {

      showToast(
        "โหลดข้อมูลล่าสุดแล้ว"
      );
    }
  }

  catch (error) {

    console.error(
      "PrachinLife load error:",
      error
    );

    allPromotions = [];
    filteredPromotions = [];

    renderAll();

    setText(
      "resultCount",
      "โหลดข้อมูลไม่สำเร็จ"
    );

    showToast(
      "ไม่สามารถโหลดข้อมูลได้"
    );
  }
}


/* =====================================================
CLIENT NORMALIZATION
===================================================== */

function normalizeClientData(data) {

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

        const imageUrl =
          item.image_url
          || item.image
          || "";

        const promotionType =
          item.promotion_type
          || "campaign";

        return {
          ...item,

          title,
          merchant,
          image_url: imageUrl,
          promotion_type:
            promotionType,

          source:
            item.source
            || merchant,

          source_url:
            item.source_url
            || "",

          verified:
            item.verified === true,

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
SEARCH
===================================================== */

function applySearchFromInput() {

  const input =
    document.getElementById(
      "searchInput"
    );

  currentSearch =
    input
      ? input.value
          .trim()
          .toLowerCase()
      : "";

  currentPage = 1;

  applyFilters();

  scrollToDeals();
}


function setSearch(value) {

  const input =
    document.getElementById(
      "searchInput"
    );

  if (input) {
    input.value = value;
  }

  currentSearch =
    value
      .trim()
      .toLowerCase();

  currentPage = 1;

  applyFilters();

  scrollToDeals();
}


function resetSearch() {

  const input =
    document.getElementById(
      "searchInput"
    );

  if (input) {
    input.value = "";
  }

  currentSearch = "";
  currentMerchant = "all";
  currentType = "all";
  currentPage = 1;

  updateActiveFilterButtons(
    "merchant"
  );

  updateActiveFilterButtons(
    "type"
  );

  applyFilters();
}


function applyFilters() {

  filteredPromotions =
    allPromotions.filter(
      promotion => {

        const searchableText = [
          promotion.title,
          promotion.merchant,
          promotion.source,
          promotion.promotion_type,
          promotion.category,
          promotion.branch,
          promotion.source_type,
          promotion.location_scope,
          promotion.province,
          promotion.district,
          promotion.subdistrict,
          promotion.branch_name,
          getLocationLabel(promotion)
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        const matchesSearch =
          !currentSearch ||
          searchableText.includes(currentSearch);

        const matchesMerchant =
          currentMerchant === "all" ||
          promotion.merchant === currentMerchant;

        const matchesType =
          currentType === "all" ||
          promotion.promotion_type === currentType;

        return (
          matchesSearch &&
          matchesMerchant &&
          matchesType
        );
      }
    );

  const useSmartMix =
    !currentSearch
    &&
    currentMerchant === "all"
    &&
    currentType === "all";

  filteredPromotions =
    useSmartMix
      ? smartMixPromotions(
          filteredPromotions
        )
      : sortLatest(
          filteredPromotions
        );

  currentPage = 1;

  renderAll();
}


function updateActiveFilterButtons(filterType) {

  if (filterType === "merchant") {

    document
      .querySelectorAll("[data-merchant]")
      .forEach(
        button => {

          button.classList.toggle(
            "active",
            button.dataset.merchant === currentMerchant
          );
        }
      );
  }

  if (filterType === "type") {

    document
      .querySelectorAll("[data-type]")
      .forEach(
        button => {

          button.classList.toggle(
            "active",
            button.dataset.type === currentType
          );
        }
      );
  }
}


/* =====================================================
QUICK ACTIONS
===================================================== */

function handleQuickAction(type) {

  if (type === "all") {

    setSearch("");

    return;
  }


  if (type === "bigc") {

    setSearch("Big C");

    return;
  }


  if (type === "latest") {

    currentSearch = "";

    const input =
      document.getElementById(
        "searchInput"
      );

    if (input) {
      input.value = "";
    }

    filteredPromotions =
      sortLatest(
        [...allPromotions]
      );

    currentPage = 1;

    renderAll();

    scrollToDeals();
  }
}


/* =====================================================
LOCATION
===================================================== */

function getLocationLabel(
  promotion
) {

  const scope =
    promotion.location_scope
    || "national";


  if (scope === "national") {

    return "ทั่วประเทศ";
  }


  if (scope === "province") {

    return promotion.province
      || "ระดับจังหวัด";
  }


  if (scope === "district") {

    const district =
      promotion.district
      || "";

    const province =
      promotion.province
      || "";

    return [
      district,
      province
    ]
      .filter(Boolean)
      .join(" · ");
  }


  if (scope === "branch") {

    return (
      promotion.branch_name
      || [
        promotion.district,
        promotion.province
      ]
        .filter(Boolean)
        .join(" · ")
      || "เฉพาะสาขา"
    );
  }


  return "ไม่ระบุพื้นที่";
}


function getPromotionTypeLabel(promotion) {

  if (promotion.promotion_type === "coupon") {
    return "คูปอง";
  }

  if (promotion.promotion_type === "member_offer") {
    return "สิทธิสมาชิก";
  }

  if (promotion.promotion_type === "product_deal") {
    return "ดีลสินค้า";
  }

  return "แคมเปญ";
}


function getPromotionTypeClass(promotion) {

  if (promotion.promotion_type === "coupon") {
    return "coupon";
  }

  if (promotion.promotion_type === "member_offer") {
    return "member-offer";
  }

  return "campaign";
}


/* =====================================================
SORT
===================================================== */

function getInterestingScore(promotion) {

  let score = 0;

  if (promotion.promotion_type === "coupon") {
    score += 30;
  }

  else if (promotion.promotion_type === "member_offer") {
    score += 20;
  }

  else if (promotion.promotion_type === "product_deal") {
    score += 20;
  }

  else {
    score += 10;
  }


  if (promotion.image_url) {
    score += 5;
  }


  if (promotion.location_scope === "province") {
    score += 40;
  }

  else if (promotion.location_scope === "district") {
    score += 50;
  }

  else if (promotion.location_scope === "branch") {
    score += 60;
  }


  return score;
}


function rankInteresting(data) {

  return [...data].sort(
    (a, b) => {

      const scoreA =
        getInterestingScore(a);

      const scoreB =
        getInterestingScore(b);

      if (scoreB !== scoreA) {
        return scoreB - scoreA;
      }

      return (
        parseDateValue(b.collected_at)
        -
        parseDateValue(a.collected_at)
      );
    }
  );
}


function smartMixPromotions(data) {

  const sorted =
    rankInteresting(data);

  const merchantBuckets =
    new Map();

  for (const item of sorted) {

    const merchant =
      item.merchant
      || "Unknown";

    if (!merchantBuckets.has(merchant)) {
      merchantBuckets.set(
        merchant,
        []
      );
    }

    merchantBuckets
      .get(merchant)
      .push(item);
  }


  const merchants =
    [...merchantBuckets.keys()];


  const selectedTypeCounts = {
    campaign: 0,
    coupon: 0,
    member_offer: 0,
    product_deal: 0,
  };


  const result = [];


  function takeBestItem(bucket) {

    if (!bucket.length) {
      return null;
    }

    let bestIndex = 0;
    let bestCount = Infinity;

    for (
      let i = 0;
      i < bucket.length;
      i++
    ) {

      const type =
        bucket[i].promotion_type
        || "campaign";

      const count =
        selectedTypeCounts[type]
        ?? 0;

      if (count < bestCount) {

        bestCount = count;
        bestIndex = i;
      }
    }


    const [item] =
      bucket.splice(
        bestIndex,
        1
      );


    const type =
      item.promotion_type
      || "campaign";

    selectedTypeCounts[type] =
      (
        selectedTypeCounts[type]
        ?? 0
      )
      + 1;


    return item;
  }


  let remaining = sorted.length;


  while (remaining > 0) {

    let addedThisRound = false;


    for (const merchant of merchants) {

      const bucket =
        merchantBuckets.get(
          merchant
        );

      if (!bucket || !bucket.length) {
        continue;
      }


      const item =
        takeBestItem(
          bucket
        );


      if (item) {

        result.push(item);

        remaining--;

        addedThisRound = true;
      }
    }


    if (!addedThisRound) {
      break;
    }
  }


  return result;
}


function sortLatest(data) {

  return [...data].sort(
    (a, b) => {

      const timeA =
        parseDateValue(
          a.collected_at
        );

      const timeB =
        parseDateValue(
          b.collected_at
        );

      return timeB - timeA;
    }
  );
}


function parseDateValue(value) {

  if (!value) {
    return 0;
  }

  const date =
    new Date(value);

  const timestamp =
    date.getTime();

  return Number.isFinite(
    timestamp
  )
    ? timestamp
    : 0;
}


/* =====================================================
RENDER
===================================================== */

function renderAll() {

  renderPromotions();

  setText(
    "resultCount",
    `${filteredPromotions.length} รายการ`
  );
}


function renderPromotions() {

  const list =
    document.getElementById(
      "promotionList"
    );

  const emptyState =
    document.getElementById(
      "emptyState"
    );

  const loadMoreBtn =
    document.getElementById(
      "loadMoreBtn"
    );


  if (!list) {
    return;
  }


  if (
    filteredPromotions.length === 0
  ) {

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
    currentPage
    * PAGE_SIZE;


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

    if (
      visibleCount
      < filteredPromotions.length
    ) {

      loadMoreBtn.classList.remove(
        "hidden"
      );
    }

    else {

      loadMoreBtn.classList.add(
        "hidden"
      );
    }
  }
}


function renderPromotionCard(
  promotion
) {

  const title =
    escapeHtml(
      promotion.title
    );

  const merchant =
    escapeHtml(
      promotion.merchant
    );

  const source =
    escapeHtml(
      promotion.source
    );

  const locationLabel =
    escapeHtml(
      getLocationLabel(
        promotion
      )
    );

  const category =
    promotion.promotion_type ===
    "product_deal"
      ? "ดีลสินค้า"
      : "แคมเปญโปรโมชั่น";


  const typeLabel =
    escapeHtml(
      getPromotionTypeLabel(promotion)
    );


  const typeClass =
    escapeHtml(
      getPromotionTypeClass(promotion)
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
          onerror="this.parentElement.innerHTML='<div class=&quot;image-placeholder&quot;>🛒</div>'"
        >
      `
      : `
        <div class="image-placeholder">
          🛒
        </div>
      `;


  const verifiedLabel =
    promotion.verified
      ? "✓ แหล่งข้อมูลต้นทาง"
      : "ข้อมูลจากต้นทาง";


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
          ดูรายละเอียดต้นทาง
          <span aria-hidden="true">→</span>
        </a>
      `
      : `
        <span class="source-button">
          ยังไม่มีลิงก์ต้นทาง
        </span>
      `;


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

          <span>
            •
          </span>

          <span>
            ${escapeHtml(category)}
          </span>

        </div>


        <div
          class="promotion-type-badge ${typeClass}"
        >
          ${typeLabel}
        </div>

        <div class="promotion-location">
          📍 ${locationLabel}
        </div>


        <h3 class="promotion-title">
          ${title}
        </h3>


        <p class="promotion-description">
          ${escapeHtml(
            verifiedLabel
          )}
          ·
          ${source}
        </p>


        <div class="promotion-actions">
          ${sourceButton}
        </div>

      </div>

    </article>
  `;
}


/* =====================================================
META
===================================================== */

function updateMeta() {

  setText(
    "totalCount",
    `${allPromotions.length} รายการ`
  );


  const latest =
    getLatestCollectedAt(
      allPromotions
    );


  setText(
    "lastUpdate",
    latest
      ? formatThaiDateTime(
          latest
        )
      : "ยังไม่มีข้อมูล"
  );
}


function getLatestCollectedAt(data) {

  const dates =
    data
      .map(
        item =>
          item.collected_at
      )
      .filter(Boolean)
      .map(
        value =>
          new Date(value)
      )
      .filter(
        date =>
          Number.isFinite(
            date.getTime()
          )
      );


  if (dates.length === 0) {
    return null;
  }


  return new Date(
    Math.max(
      ...dates.map(
        date =>
          date.getTime()
      )
    )
  );
}


function formatThaiDateTime(date) {

  try {

    return new Intl.DateTimeFormat(
      "th-TH",
      {
        dateStyle: "medium",
        timeStyle: "short",
      }
    ).format(date);
  }

  catch {

    return date.toLocaleString();
  }
}


/* =====================================================
LOADING
===================================================== */

function setLoading() {

  const list =
    document.getElementById(
      "promotionList"
    );

  if (list) {

    list.innerHTML = `
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
    `;
  }


  setText(
    "resultCount",
    "กำลังโหลด..."
  );
}


/* =====================================================
UI HELPERS
===================================================== */

function scrollToDeals() {

  const deals =
    document.getElementById(
      "deals"
    );

  if (deals) {

    deals.scrollIntoView(
      {
        behavior: "smooth",
        block: "start",
      }
    );
  }
}


function setText(
  id,
  value
) {

  const element =
    document.getElementById(id);

  if (element) {
    element.textContent = value;
  }
}


function showToast(message) {

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
SECURITY HELPERS
===================================================== */

function escapeHtml(value) {

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


function escapeAttribute(value) {

  return escapeHtml(
    value
  );
}
