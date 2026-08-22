from pathlib import Path

p = Path("app.js")
s = p.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    n = s.count(old)

    if n != 1:
        raise SystemExit(
            f"STOP {label}: expected 1, found {n}"
        )

    s = s.replace(old, new, 1)


once(
    'const GO_URL = "go_index.json";',
    '''const GO_URL = "go_index.json";
const SERVICE_URL = "service_index.json";''',
    "SERVICE_URL",
)

once(
    '''const VEGETARIAN_PAGE_SIZE = 8;
const RECOMMENDED_LIMIT = 8;''',
    '''const VEGETARIAN_PAGE_SIZE = 8;
const SERVICE_PAGE_SIZE = 8;
const RECOMMENDED_LIMIT = 8;''',
    "PAGE_SIZE",
)

once(
    "let filteredGoPlaces = [];",
    '''let filteredGoPlaces = [];

let allServicePlaces = [];
let primaryServicePlaces = [];
let filteredServicePlaces = [];''',
    "service arrays",
)

once(
    "let currentVegetarianPage = 1;",
    '''let currentVegetarianPage = 1;
let currentServicePage = 1;''',
    "service page",
)

once(
    'let currentVegetarianProvince = "all";',
    '''let currentVegetarianProvince = "all";
let currentServiceCategory = "all";''',
    "service category",
)

once(
    '''      loadGoIndex(),
    ]);''',
    '''      loadGoIndex(),
      loadServiceIndex(),
    ]);''',
    "init load",
)

once(
    '''    prepareGoPlaces();


    buildVegetarianProvinceFilters();''',
    '''    prepareGoPlaces();

    prepareServicePlaces();


    buildVegetarianProvinceFilters();''',
    "init prepare",
)

once(
    '''    applyVegetarianFilters();

    setMainCategory(''',
    '''    applyVegetarianFilters();

    applyServiceFilters();

    setMainCategory(''',
    "init filter",
)

once(
    '''  bindGoEvents();

  bindLoadMoreEvents();''',
    '''  bindGoEvents();

  bindServiceEvents();

  bindLoadMoreEvents();''',
    "bind service",
)

once(
    '''          loadGoIndex(true),
        ]);''',
    '''          loadGoIndex(true),
          loadServiceIndex(true),
        ]);''',
    "refresh load",
)

once(
    '''        prepareGoPlaces();


        buildVegetarianProvinceFilters();''',
    '''        prepareGoPlaces();

        prepareServicePlaces();


        buildVegetarianProvinceFilters();''',
    "refresh prepare",
)

once(
    '''        applyVegetarianFilters();


        if (''',
    '''        applyVegetarianFilters();

        applyServiceFilters();


        if (''',
    "refresh filter",
)

old = '''  else if (
    category ===
    "services"
  ) {

    window.PrachinLife.ui.showElement(
      "servicesOptions"
    );

    window.PrachinLife.ui.showElement(
      "comingSoonResultSection"
    );

    setComingSoonContent(
      "🔧",
      "บริการใกล้ตัว",
      "กำลังเตรียมข้อมูลร้าน ช่าง และบริการที่ใช้ในชีวิตประจำวัน"
    );
  }'''

new = '''  else if (
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
  }'''

once(old, new, "service branch")


anchor = '''/* =====================================================
LOAD VEGETARIAN INDEX
===================================================== */'''

block = '''/* =====================================================
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
        { cache: "no-store" }
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
  }

  catch (error) {
    console.error(
      "PrachinLife service index error:",
      error
    );

    allServicePlaces = [];
    primaryServicePlaces = [];
    filteredServicePlaces = [];
  }
}


'''

s = s.replace(anchor, block + anchor, 1)


anchor = '''/* =====================================================
PREPARE GO
===================================================== */'''

block = '''/* =====================================================
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
          metadata.show_in_primary_directory === true
          &&
          metadata.needs_review !== true
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


'''

s = s.replace(anchor, block + anchor, 1)


anchor = '''/* =====================================================
VEGETARIAN FILTER ENGINE
===================================================== */'''

block = '''/* =====================================================
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


'''

s = s.replace(anchor, block + anchor, 1)


anchor = '''/* =====================================================
LOAD MORE
===================================================== */'''

block = '''/* =====================================================
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
  currentMainCategory = "services";

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


function updateServiceNearMeState(active) {
  const button =
    document.getElementById(
      "serviceNearMeBtn"
    );

  if (!button) return;

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
  if (userLocation) {
    userLocation = null;
    currentServicePage = 1;

    updateServiceNearMeState(false);

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
      userLocation = position;
      currentServicePage = 1;

      updateServiceNearMeState(true);

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


'''

s = s.replace(anchor, block + anchor, 1)


once(
    '''  const vegetarianLoadMoreBtn =
    document.getElementById(
      "vegetarianLoadMoreBtn"
    );''',
    '''  const vegetarianLoadMoreBtn =
    document.getElementById(
      "vegetarianLoadMoreBtn"
    );

  const serviceLoadMoreBtn =
    document.getElementById(
      "serviceLoadMoreBtn"
    );''',
    "loadmore var",
)

once(
    '''  if (vegetarianLoadMoreBtn) {

    vegetarianLoadMoreBtn.addEventListener(
      "click",
      () => {

        currentVegetarianPage++;

        renderVegetarianPlaces();
      }
    );
  }
}''',
    '''  if (vegetarianLoadMoreBtn) {

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
}''',
    "loadmore binding",
)

once(
    '''    "goResultSection",
    "comingSoonResultSection",''',
    '''    "goResultSection",
    "serviceResultSection",
    "comingSoonResultSection",''',
    "hide result",
)

p.write_text(
    s,
    encoding="utf-8"
)

print("PASS: Service V1 app wiring restored")
