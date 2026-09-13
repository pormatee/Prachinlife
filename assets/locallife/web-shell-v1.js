(() => {
  "use strict";

  const CONTRACT = "locallife.regional-web-context/v1";
  const VIEW_IDS = ["home", "search", "eat", "go", "services"];
  const ICONS = { home: "⌂", search: "⌕", eat: "ช", go: "↗", services: "✓" };
  const COPY = {
    home: {
      eyebrow: "LOCAL EVERYDAY ASSISTANT",
      title: "ชีวิตท้องถิ่น ง่ายขึ้นในที่เดียว",
      subtitle: "เลือกสิ่งที่ต้องการ แล้วไปยังบริการของพื้นที่นี้ได้อย่างรวดเร็ว"
    },
    search: {
      eyebrow: "ค้นหา",
      title: "ค้นหาสิ่งที่ต้องการใกล้ตัว",
      subtitle: "โครงหน้าเว็บพร้อมแล้ว และจะอ่านเฉพาะข้อมูลที่ผ่านขอบเขต Published Read Model"
    },
    eat: {
      eyebrow: "กิน",
      title: "หาร้านและเรื่องกินได้ง่ายขึ้น",
      subtitle: "หน้านี้พร้อมเชื่อมข้อมูลอาหาร ร้าน คาเฟ่ และตัวเลือกที่เกี่ยวข้องของพื้นที่"
    },
    go: {
      eyebrow: "เที่ยว",
      title: "ค้นหาที่ไปและสิ่งที่น่าสนใจ",
      subtitle: "หน้านี้พร้อมเชื่อมสถานที่และกิจกรรมจากข้อมูลที่เผยแพร่แล้ว"
    },
    services: {
      eyebrow: "บริการ",
      title: "หาบริการที่ต้องใช้ในชีวิตประจำวัน",
      subtitle: "หน้านี้พร้อมเชื่อมบริการท้องถิ่นโดยไม่อ่านข้อมูล Canonical โดยตรง"
    }
  };

  const body = document.body;
  const region = String(body.dataset.region || "").trim();
  const view = VIEW_IDS.includes(body.dataset.view) ? body.dataset.view : "home";
  const contextPath = String(body.dataset.contextEndpoint || "").trim();

  const byId = (id) => document.getElementById(id);
  const els = {
    brandName: byId("brandName"),
    brandTagline: byId("brandTagline"),
    eyebrow: byId("pageEyebrow"),
    title: byId("pageTitle"),
    subtitle: byId("pageSubtitle"),
    status: byId("connectionStatus"),
    nav: byId("bottomNav"),
    quick: byId("quickLinks"),
    quickSection: byId("quickSection"),
    error: byId("contextError"),
    errorMessage: byId("contextErrorMessage"),
    retry: byId("retryContext"),
    viewPanel: byId("viewPanel"),
    viewPanelTitle: byId("viewPanelTitle"),
    viewPanelCopy: byId("viewPanelCopy")
  };

  function safeInternalRoute(value) {
    return typeof value === "string" && value.startsWith("/") && !value.startsWith("//") && !value.includes("\\");
  }

  function allowedApiBase(raw) {
    if (!raw) return null;
    try {
      const parsed = new URL(raw, window.location.origin);
      const loopback = parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost" || parsed.hostname === "[::1]";
      const sameOrigin = parsed.origin === window.location.origin;
      if ((parsed.protocol === "http:" || parsed.protocol === "https:") && (loopback || sameOrigin)) {
        return parsed.origin;
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  function apiUrl() {
    if (!region || !contextPath || !safeInternalRoute(contextPath)) {
      throw new Error("invalid regional bootstrap");
    }
    const requestedBase = new URLSearchParams(window.location.search).get("apiBase");
    if (requestedBase && !allowedApiBase(requestedBase)) {
      throw new Error("apiBase is not allowed");
    }
    const base = allowedApiBase(requestedBase) || window.location.origin;
    return new URL(contextPath, base).toString();
  }

  function validateContext(payload) {
    if (!payload || payload.ok !== true || !payload.result || typeof payload.result !== "object") {
      throw new Error("regional context unavailable");
    }
    const ctx = payload.result;
    if (ctx.contract_version !== CONTRACT || ctx.region_slug !== region) {
      throw new Error("regional context mismatch");
    }
    if (typeof ctx.brand !== "string" || !ctx.brand.trim()) {
      throw new Error("invalid brand context");
    }
    if (!ctx.routes || typeof ctx.routes !== "object" || !Array.isArray(ctx.navigation)) {
      throw new Error("invalid navigation context");
    }
    for (const id of VIEW_IDS) {
      if (!safeInternalRoute(ctx.routes[id])) throw new Error("invalid route context");
    }
    const navIds = new Set(ctx.navigation.map((item) => item && item.id));
    for (const id of VIEW_IDS) {
      if (!navIds.has(id)) throw new Error("incomplete navigation context");
    }
    return ctx;
  }

  function setStatus(text, state) {
    els.status.dataset.state = state;
    els.status.lastElementChild.textContent = text;
  }

  function routeHref(route) {
    if (!safeInternalRoute(route)) return "#";
    const requestedBase = new URLSearchParams(window.location.search).get("apiBase");
    const approvedBase = allowedApiBase(requestedBase);
    if (!requestedBase || !approvedBase) return route;
    const url = new URL(route, window.location.origin);
    url.searchParams.set("apiBase", approvedBase);
    return `${url.pathname}${url.search}`;
  }

  function bootstrapHomeRoute() {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(region)) return null;
    return `/${region}/`;
  }

  function enableBootstrapHomeEscape() {
    const route = bootstrapHomeRoute();
    if (!route || !els.nav) return;
    const homeLink = els.nav.querySelector("a");
    if (!homeLink) return;
    homeLink.href = routeHref(route);
    homeLink.dataset.viewId = "home";
    homeLink.removeAttribute("aria-disabled");
    if (view === "home") homeLink.setAttribute("aria-current", "page");
  }

  function installPageActions() {
    if (view === "home") return;
    const route = bootstrapHomeRoute();
    const main = document.querySelector(".ll-main");
    if (!route || !main) return;

    const actions = document.createElement("div");
    actions.className = "ll-page-actions";
    actions.setAttribute("aria-label", "การนำทางหน้า");

    const back = document.createElement("button");
    back.type = "button";
    back.className = "ll-page-back";
    back.textContent = "← ย้อนกลับ";
    back.addEventListener("click", () => {
      let canUseHistory = false;
      try {
        if (document.referrer) {
          const ref = new URL(document.referrer);
          canUseHistory = ref.origin === window.location.origin && window.history.length > 1;
        }
      } catch (_) {
        canUseHistory = false;
      }
      if (canUseHistory) {
        window.history.back();
      } else {
        window.location.assign(routeHref(route));
      }
    });

    const home = document.createElement("a");
    home.className = "ll-page-home";
    home.href = routeHref(route);
    home.textContent = "⌂ หน้าหลัก";

    actions.append(back, home);
    main.prepend(actions);
  }

  function makeNavLink(item, route) {
    const link = document.createElement("a");
    link.className = "ll-nav-link";
    link.href = routeHref(route);
    link.dataset.viewId = item.id;
    if (item.id === view) link.setAttribute("aria-current", "page");

    const icon = document.createElement("span");
    icon.className = "ll-nav-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = ICONS[item.id] || "•";

    const label = document.createElement("span");
    label.textContent = String(item.label || item.id).slice(0, 30);
    link.append(icon, label);
    return link;
  }

  function renderNavigation(ctx) {
    els.nav.replaceChildren();
    for (const id of VIEW_IDS) {
      const item = ctx.navigation.find((entry) => entry && entry.id === id);
      els.nav.appendChild(makeNavLink(item, ctx.routes[id]));
    }
  }

  function renderQuickLinks(ctx) {
    if (view !== "home") {
      els.quickSection.hidden = true;
      return;
    }
    els.quick.replaceChildren();
    for (const id of VIEW_IDS.filter((x) => x !== "home")) {
      const item = ctx.navigation.find((entry) => entry && entry.id === id);
      const card = document.createElement("a");
      card.className = "ll-card";
      card.href = routeHref(ctx.routes[id]);

      const icon = document.createElement("div");
      icon.className = "ll-card-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = ICONS[id] || "•";

      const title = document.createElement("div");
      title.className = "ll-card-title";
      title.textContent = String(item.label || id).slice(0, 30);

      const copy = document.createElement("p");
      copy.className = "ll-card-copy";
      copy.textContent = id === "search" ? "เริ่มจากสิ่งที่คุณต้องการ" : "เปิดหมวดนี้";
      card.append(icon, title, copy);
      els.quick.appendChild(card);
    }
    els.quickSection.hidden = false;
  }

  function renderViewCopy(ctx) {
    const copy = COPY[view] || COPY.home;
    els.eyebrow.textContent = copy.eyebrow;
    els.title.textContent = view === "home" ? ctx.brand : copy.title;
    els.subtitle.textContent = copy.subtitle;
    document.title = `${view === "home" ? ctx.brand : copy.eyebrow + " · " + ctx.brand}`;

    if (view === "home") {
      els.viewPanel.hidden = true;
    } else {
      const label = ctx.navigation.find((entry) => entry && entry.id === view);
      els.viewPanelTitle.textContent = label ? String(label.label).slice(0, 30) : copy.eyebrow;
      els.viewPanelCopy.textContent = "Web V1.1 แสดงเฉพาะโครงหน้าที่ได้รับ Regional Context แล้ว ยังไม่ฝังข้อมูลสถานที่ตัวอย่างหรืออ่าน Canonical โดยตรง";
      els.viewPanel.hidden = false;
    }
  }

  function showError(err) {
    setStatus("ยังเชื่อมไม่ได้", "error");
    els.errorMessage.textContent = "ไม่สามารถโหลดบริบทของพื้นที่ได้ จึงไม่แสดงข้อมูลหรือเส้นทางที่เดาเอง";
    els.error.hidden = false;
    els.quickSection.hidden = true;
    els.viewPanel.hidden = true;
    for (const link of els.nav.querySelectorAll("a")) {
      if (link.dataset.viewId === "home") {
        link.removeAttribute("aria-disabled");
      } else {
        link.setAttribute("aria-disabled", "true");
        link.removeAttribute("href");
      }
    }
    enableBootstrapHomeEscape();
    console.warn("Regional web context blocked:", err instanceof Error ? err.message : "unknown error");
  }

  async function load() {
    els.error.hidden = true;
    setStatus("กำลังเชื่อมข้อมูลพื้นที่", "loading");
    try {
      const response = await fetch(apiUrl(), { method: "GET", cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`context http ${response.status}`);
      const ctx = validateContext(await response.json());
      els.brandName.textContent = ctx.brand;
      els.brandTagline.textContent = COPY.home.subtitle;
      renderNavigation(ctx);
      renderQuickLinks(ctx);
      renderViewCopy(ctx);
      setStatus("พร้อมใช้งาน", "ready");
    } catch (err) {
      showError(err);
    }
  }

  installPageActions();
  enableBootstrapHomeEscape();
  els.retry.addEventListener("click", load);
  load();
})();
