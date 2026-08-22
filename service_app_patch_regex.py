from pathlib import Path
import re

p = Path("app.js")
s = p.read_text(encoding="utf-8")

def sub_once(pattern, repl, label):
    global s

    s2, n = re.subn(
        pattern,
        repl,
        s,
        count=1,
        flags=re.MULTILINE,
    )

    if n != 1:
        raise SystemExit(
            f"STOP {label}: matched {n}"
        )

    s = s2


# CONFIG / STATE

sub_once(
    r'const GO_URL = "go_index\.json";',
    '''const GO_URL = "go_index.json";
const SERVICE_URL = "service_index.json";''',
    "SERVICE_URL",
)

sub_once(
    r'const VEGETARIAN_PAGE_SIZE = 8;\s*const RECOMMENDED_LIMIT = 8;',
    '''const VEGETARIAN_PAGE_SIZE = 8;
const SERVICE_PAGE_SIZE = 8;
const RECOMMENDED_LIMIT = 8;''',
    "PAGE_SIZE",
)

sub_once(
    r'let filteredGoPlaces = \[\];',
    '''let filteredGoPlaces = [];

let allServicePlaces = [];
let primaryServicePlaces = [];
let filteredServicePlaces = [];''',
    "SERVICE_STATE",
)

sub_once(
    r'let currentVegetarianPage = 1;',
    '''let currentVegetarianPage = 1;
let currentServicePage = 1;''',
    "SERVICE_PAGE_STATE",
)

sub_once(
    r'let currentVegetarianProvince = "all";',
    '''let currentVegetarianProvince = "all";
let currentServiceCategory = "all";''',
    "SERVICE_CATEGORY_STATE",
)


# INIT LOAD

sub_once(
    r'loadGoIndex\(\),\s*\]\);',
    '''loadGoIndex(),
      loadServiceIndex(),
    ]);''',
    "INIT_LOAD",
)


# INIT PREPARE

sub_once(
    r'prepareGoPlaces\(\);\s+buildVegetarianProvinceFilters\(\);',
    '''prepareGoPlaces();

    prepareServicePlaces();

    buildVegetarianProvinceFilters();''',
    "INIT_PREPARE",
)


# INIT FILTER

sub_once(
    r'applyVegetarianFilters\(\);\s+setMainCategory\(',
    '''applyVegetarianFilters();

    applyServiceFilters();

    setMainCategory(''',
    "INIT_FILTER",
)


# EVENT BIND

sub_once(
    r'bindGoEvents\(\);\s+bindLoadMoreEvents\(\);',
    '''bindGoEvents();

  bindServiceEvents();

  bindLoadMoreEvents();''',
    "EVENT_BIND",
)


# REFRESH LOAD

sub_once(
    r'loadGoIndex\(true\),\s*\]\);',
    '''loadGoIndex(true),
          loadServiceIndex(true),
        ]);''',
    "REFRESH_LOAD",
)


# REFRESH PREPARE

sub_once(
    r'prepareGoPlaces\(\);\s+buildVegetarianProvinceFilters\(\);',
    '''prepareGoPlaces();

        prepareServicePlaces();

        buildVegetarianProvinceFilters();''',
    "REFRESH_PREPARE",
)


# REFRESH FILTER

sub_once(
    r'applyVegetarianFilters\(\);\s+if \(',
    '''applyVegetarianFilters();

        applyServiceFilters();

        if (''',
    "REFRESH_FILTER",
)


# SERVICE MAIN CATEGORY BRANCH

pattern = r'''else if \(
\s*category ===
\s*"services"
\s*\) \{
.*?
\s*\}'''

replacement = '''else if (
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

s2, n = re.subn(
    pattern,
    replacement,
    s,
    count=1,
    flags=re.DOTALL,
)

if n != 1:
    raise SystemExit(
        f"STOP SERVICE_BRANCH: matched {n}"
    )

s = s2


# SERVICE LOADER

anchor = '''/* =====================================================
LOAD VEGETARIAN INDEX
===================================================== */'''

if anchor not in s:
    raise SystemExit(
        "STOP SERVICE_LOADER anchor"
    )

loader = '''/* =====================================================
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


'''

s = s.replace(
    anchor,
    loader + anchor,
    1,
)


# PREPARE SERVICE

anchor = '''/* =====================================================
PREPARE GO
===================================================== */'''

if anchor not in s:
    raise SystemExit(
        "STOP SERVICE_PREPARE anchor"
    )

prepare = '''/* =====================================================
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


'''

s = s.replace(
    anchor,
    prepare + anchor,
    1,
)


# FILTER / RENDER

anchor = '''/* =====================================================
VEGETARIAN FILTER ENGINE
===================================================== */'''

if anchor not in s:
    raise SystemExit(
        "STOP SERVICE_FILTER anchor"
    )

filter_block = '''/* =====================================================
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

s = s.replace(
    anchor,
    filter_block + anchor,
    1,
)


# EVENTS

anchor = '''/* =====================================================
LOAD MORE
===================================================== */'''

if anchor not in s:
    raise SystemExit(
        "STOP SERVICE_EVENTS anchor"
    )

events = '''/* =====================================================
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


'''

s = s.replace(
    anchor,
    events + anchor,
    1,
)


# LOAD MORE VAR

sub_once(
    r'''const vegetarianLoadMoreBtn =
\s*document\.getElementById\(
\s*"vegetarianLoadMoreBtn"
\s*\);''',
    '''const vegetarianLoadMoreBtn =
    document.getElementById(
      "vegetarianLoadMoreBtn"
    );

  const serviceLoadMoreBtn =
    document.getElementById(
      "serviceLoadMoreBtn"
    );''',
    "LOAD_MORE_VAR",
)


# LOAD MORE BIND

pattern = r'''if \(vegetarianLoadMoreBtn\) \{
.*?
\s*\}
\}'''

replacement = '''if (vegetarianLoadMoreBtn) {

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
}'''

s2, n = re.subn(
    pattern,
    replacement,
    s,
    count=1,
    flags=re.DOTALL,
)

if n != 1:
    raise SystemExit(
        f"STOP LOAD_MORE_BIND: matched {n}"
    )

s = s2


# HIDE RESULT

sub_once(
    r'''"goResultSection",\s*"comingSoonResultSection",''',
    '''"goResultSection",
    "serviceResultSection",
    "comingSoonResultSection",''',
    "HIDE_RESULT",
)


p.write_text(
    s,
    encoding="utf-8",
)

print(
    "PASS: Service V1 app regex patch applied"
)
