(() => {
  "use strict";

  const CONTRACT = "locallife.regional-web-context/v1";
  const body = document.body;
  const region = String(body.dataset.region || "").trim();
  const contextPath = String(body.dataset.contextEndpoint || "").trim();

  const brandName = document.getElementById("brandName");
  const runtimeStatus = document.getElementById("runtimeStatus");
  const runtimeRow = runtimeStatus ? runtimeStatus.closest(".legacy-runtime-row") : null;
  const searchInput = document.getElementById("searchInput");
  const searchBtn = document.getElementById("searchBtn");
  const previewTitle = document.getElementById("previewTitle");
  const previewCopy = document.getElementById("previewCopy");
  const nearMeBtn = document.getElementById("nearMeBtn");

  const aiOpen = document.getElementById("aiAssistantOpen");
  const aiPanel = document.getElementById("robotAssistPanel");
  const aiClose = document.getElementById("robotAssistClose");
  const aiReset = document.getElementById("robotAssistReset");
  const aiMessages = document.getElementById("robotAssistMessages");
  const aiInput = document.getElementById("robotAssistInput");
  const aiSend = document.getElementById("robotAssistSend");
  const aiStatus = document.getElementById("robotAssistStatus");
  const aiPanelHome = document.createComment("prachinlife-ai-panel-home");
  aiPanel.parentNode.insertBefore(aiPanelHome, aiPanel);

  let decisionEndpoint = null;
  let conversationState = null;
  let sending = false;

  function safeInternalRoute(value) {
    return typeof value === "string" &&
      value.startsWith("/") &&
      !value.startsWith("//") &&
      !value.includes("\\");
  }

  function allowedApiBase(raw) {
    if (!raw) return null;
    try {
      const parsed = new URL(raw, window.location.origin);
      const loopback =
        parsed.hostname === "127.0.0.1" ||
        parsed.hostname === "localhost" ||
        parsed.hostname === "[::1]";
      const sameOrigin = parsed.origin === window.location.origin;
      if ((parsed.protocol === "http:" || parsed.protocol === "https:") &&
          (loopback || sameOrigin)) {
        return parsed.origin;
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  function apiBase() {
    const requestedBase = new URLSearchParams(window.location.search).get("apiBase");
    if (requestedBase && !allowedApiBase(requestedBase)) {
      throw new Error("apiBase is not allowed");
    }
    return allowedApiBase(requestedBase) || window.location.origin;
  }

  function apiUrl(path) {
    if (!safeInternalRoute(path)) {
      throw new Error("invalid API route");
    }
    return new URL(path, apiBase()).toString();
  }

  function contextUrl() {
    if (!region || !safeInternalRoute(contextPath)) {
      throw new Error("invalid regional bootstrap");
    }
    return apiUrl(contextPath);
  }

  function setRuntime(text, state) {
    runtimeStatus.textContent = text;
    if (runtimeRow) runtimeRow.dataset.state = state;
  }

  function setAiReady(ready, text) {
    aiOpen.disabled = !ready;
    aiStatus.textContent = text;
    aiStatus.classList.toggle("robot-assist-status-error", !ready);
  }

  async function loadContext() {
    setRuntime("กำลังเชื่อม Regional Context...", "loading");
    setAiReady(false, "กำลังเชื่อม LocalLife Decision API...");
    try {
      const response = await fetch(contextUrl(), {
        method: "GET",
        cache: "no-store",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error(`context http ${response.status}`);
      const payload = await response.json();
      const ctx = payload && payload.result;
      if (!payload || payload.ok !== true || !ctx ||
          ctx.contract_version !== CONTRACT ||
          ctx.region_slug !== region ||
          typeof ctx.brand !== "string" ||
          !ctx.brand.trim()) {
        throw new Error("regional context mismatch");
      }
      if (!ctx.endpoints || !safeInternalRoute(ctx.endpoints.decision)) {
        throw new Error("decision endpoint unavailable");
      }
      brandName.textContent = ctx.brand;
      decisionEndpoint = ctx.endpoints.decision;
      setRuntime("เชื่อม LocalLife Core แล้ว • Preview แบบ Read-only", "ready");
      setAiReady(true, "พร้อมใช้งาน • ผ่าน LocalLife Decision API");
    } catch (err) {
      decisionEndpoint = null;
      setRuntime("ยังเชื่อมข้อมูลพื้นที่ไม่ได้ • ไม่แสดงข้อมูลที่เดาเอง", "error");
      setAiReady(false, "AI ยังไม่พร้อม เพราะ Regional Context เชื่อมไม่ได้");
      console.warn("Regional context blocked:", err instanceof Error ? err.message : "unknown");
    }
  }

  const categoryCopy = {
    recommended: ["แนะนำสำหรับวันนี้", "เมื่อเชื่อม Published Read Model แล้ว จุดนี้จะแสดงสิ่งที่เหมาะกับบริบทของผู้ใช้"],
    shopping: ["ช้อปและโปรโมชั่น", "เตรียมเชื่อมโปรโมชั่นและสิทธิ์ที่ผ่าน Published Read Model"],
    eat: ["กินอะไรดี", "เตรียมเชื่อมร้านอาหาร คาเฟ่ และตัวเลือกใกล้ตัว"],
    vegetarian: ["เจ / มังสวิรัติ", "เตรียมเชื่อมร้านและตัวเลือกอาหารเจ มังสวิรัติ และ Vegan"],
    go: ["เที่ยวและสถานที่", "เตรียมเชื่อมสถานที่ กิจกรรม และจุดที่น่าสนใจ"],
    services: ["บริการใกล้ตัว", "เตรียมเชื่อมบริการที่ใช้ในชีวิตประจำวัน"]
  };

  for (const button of document.querySelectorAll("[data-preview-category]")) {
    button.addEventListener("click", () => {
      for (const other of document.querySelectorAll("[data-preview-category]")) {
        other.classList.toggle("active", other === button);
      }
      const key = button.dataset.previewCategory;
      const copy = categoryCopy[key] || categoryCopy.recommended;
      previewTitle.textContent = copy[0];
      previewCopy.textContent = copy[1];
      document.getElementById("previewResults").scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    });
  }

  for (const chip of document.querySelectorAll("[data-preview-chip]")) {
    chip.addEventListener("click", () => {
      for (const other of document.querySelectorAll("[data-preview-chip]")) {
        other.classList.toggle("active", other === chip);
      }
      previewTitle.textContent = chip.dataset.previewChip || "แนะนำ";
      previewCopy.textContent =
        "ตัวกรองหน้าตาพร้อมแล้ว ข้อมูลจริงจะเข้าผ่าน Published Read Model เท่านั้น";
    });
  }

  function previewSearch() {
    const value = String(searchInput.value || "").trim();
    previewTitle.textContent = value ? `ค้นหา: ${value}` : "ค้นหา";
    previewCopy.textContent =
      "ช่องค้นหากลับมาในรูปแบบ PrachinLife เดิมแล้ว ขั้นนี้ยังไม่ยิงคำค้นไปยังข้อมูล Canonical โดยตรง";
    document.getElementById("previewResults").scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }

  searchBtn.addEventListener("click", previewSearch);
  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      previewSearch();
    }
  });

  nearMeBtn.addEventListener("click", () => {
    previewTitle.textContent = "ใกล้ฉัน";
    previewCopy.textContent =
      "หน้าตาใกล้ฉันพร้อมแล้ว แต่ Preview นี้ยังไม่ร้องขอตำแหน่งและยังไม่อ่านข้อมูลสถานที่จริง";
    document.getElementById("previewResults").scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  });

  function addMessage(role, text) {
    const node = document.createElement("div");
    node.className = `robot-assist-message ${role}`;
    node.textContent = String(text || "").trim();
    aiMessages.appendChild(node);
    aiMessages.scrollTop = aiMessages.scrollHeight;
  }

  function mobileAssistantMode() {
    const touchDevice = Number(navigator.maxTouchPoints || 0) > 0;
    const smallViewport = Math.min(window.innerWidth || 9999, window.screen.width || 9999) <= 900;
    return touchDevice || smallViewport || window.matchMedia("(max-width: 900px)").matches;
  }

  function setImportant(element, property, value) {
    element.style.setProperty(property, value, "important");
  }

  function mountAssistantPortal() {
    if (aiPanel.parentNode !== document.body) {
      document.body.appendChild(aiPanel);
    }
  }

  function restoreAssistantHome() {
    if (aiPanelHome.parentNode) {
      aiPanelHome.parentNode.insertBefore(aiPanel, aiPanelHome.nextSibling);
    }
  }

  function forceMobileAssistantLayout() {
    if (!mobileAssistantMode() || aiPanel.hidden) return;

    const viewport = window.visualViewport;
    const top = viewport ? Math.max(0, viewport.offsetTop) : 0;
    const height = viewport ? Math.max(260, viewport.height) : window.innerHeight;

    setImportant(aiPanel, "position", "fixed");
    setImportant(aiPanel, "left", "0");
    setImportant(aiPanel, "right", "0");
    setImportant(aiPanel, "top", `${Math.round(top)}px`);
    setImportant(aiPanel, "bottom", "auto");
    setImportant(aiPanel, "width", "100vw");
    setImportant(aiPanel, "max-width", "none");
    setImportant(aiPanel, "height", `${Math.round(height)}px`);
    setImportant(aiPanel, "max-height", "none");
    setImportant(aiPanel, "margin", "0");
    setImportant(aiPanel, "z-index", "99999");
    setImportant(aiPanel, "display", "flex");
    setImportant(aiPanel, "flex-direction", "column");
    setImportant(aiPanel, "overflow", "hidden");
    setImportant(aiPanel, "background", "#fff");
    setImportant(aiPanel, "border-radius", "0");

    setImportant(aiMessages, "flex", "1 1 auto");
    setImportant(aiMessages, "min-height", "0");
    setImportant(aiMessages, "max-height", "none");
    setImportant(aiMessages, "overflow-y", "auto");

    const composer = aiPanel.querySelector(".robot-assist-composer");
    if (composer) {
      setImportant(composer, "position", "relative");
      setImportant(composer, "left", "auto");
      setImportant(composer, "right", "auto");
      setImportant(composer, "bottom", "auto");
      setImportant(composer, "flex", "0 0 auto");
      setImportant(composer, "display", "grid");
      setImportant(composer, "grid-template-columns", "minmax(0,1fr) auto");
      setImportant(composer, "background", "#fff");
      setImportant(composer, "z-index", "100000");
    }

    setImportant(aiInput, "min-height", "50px");
    setImportant(aiInput, "max-height", "96px");
    setImportant(aiInput, "width", "100%");
    setImportant(aiInput, "resize", "none");

    setImportant(aiSend, "min-height", "50px");
  }

  function clearForcedMobileAssistantLayout() {
    const nodes = [aiPanel, aiMessages, aiInput, aiSend, aiPanel.querySelector(".robot-assist-composer")];
    for (const node of nodes) {
      if (node) node.removeAttribute("style");
    }
  }

  function syncAssistantViewport() {
    if (!aiPanel || aiPanel.hidden) return;
    forceMobileAssistantLayout();
  }

  function lockAssistantPage() {
    document.documentElement.classList.add("ai-chat-open");
    document.body.classList.add("ai-chat-open");
    if (mobileAssistantMode()) {
      aiPanel.classList.add("ai-chat-modal");
      forceMobileAssistantLayout();
    }
  }

  function unlockAssistantPage() {
    document.documentElement.classList.remove("ai-chat-open");
    document.body.classList.remove("ai-chat-open");
    aiPanel.classList.remove("ai-chat-modal");
    clearForcedMobileAssistantLayout();
  }

  function openAssistant() {
    if (!decisionEndpoint) return;
    mountAssistantPortal();
    aiPanel.hidden = false;
    lockAssistantPage();
    syncAssistantViewport();

    window.requestAnimationFrame(() => {
      syncAssistantViewport();
      try {
        aiInput.focus({ preventScroll: true });
      } catch (_) {
        aiInput.focus();
      }
      window.setTimeout(syncAssistantViewport, 80);
    });
  }

  function closeAssistant() {
    aiPanel.hidden = true;
    unlockAssistantPage();
    restoreAssistantHome();
    aiOpen.focus();
  }

  function resetAssistant() {
    conversationState = null;
    aiMessages.replaceChildren();
    addMessage("assistant", "เริ่มใหม่ได้เลยครับ บอกสิ่งที่อยากให้ PrachinLife ช่วยหาได้เลย");
    aiInput.value = "";
    aiInput.focus();
  }

  function responseText(result) {
    if (!result || typeof result !== "object") {
      return "ระบบยังไม่สามารถอ่านคำตอบได้ครับ";
    }

    const question =
      typeof result.highest_value_question === "string"
        ? result.highest_value_question.trim()
        : "";
    if (question) return question;

    const explanation =
      result.explanation && typeof result.explanation === "object"
        ? result.explanation
        : {};
    const bestName =
      typeof explanation.best_fit_name === "string"
        ? explanation.best_fit_name.trim()
        : "";
    const why = Array.isArray(explanation.why_fit)
      ? explanation.why_fit.map((x) => String(x || "").trim()).filter(Boolean)
      : [];
    const tradeoffs = Array.isArray(explanation.tradeoffs)
      ? explanation.tradeoffs.map((x) => String(x || "").trim()).filter(Boolean)
      : [];

    if (bestName && why.length) {
      return `แนะนำ ${bestName} ครับ • ${why.slice(0, 3).join(" • ")}`;
    }
    if (bestName) {
      return `จากข้อมูลที่ยืนยันได้ตอนนี้ ระบบแนะนำ ${bestName} ครับ`;
    }
    if (why.length) {
      return why.slice(0, 3).join(" • ");
    }
    if (tradeoffs.length) {
      return tradeoffs.slice(0, 3).join(" • ");
    }

    const status = typeof result.status === "string" ? result.status : "";
    if (status === "needs_user_input") {
      return "ขอข้อมูลเพิ่มอีกนิดเพื่อช่วยหาให้ตรงครับ";
    }
    return "ตอนนี้ระบบยังไม่มีข้อมูลที่ยืนยันได้พอให้ตอบโดยไม่เดาครับ";
  }

  async function sendAssistant() {
    if (sending || !decisionEndpoint) return;
    const text = String(aiInput.value || "").trim();
    if (!text) return;

    sending = true;
    aiSend.disabled = true;
    aiReset.disabled = true;
    aiInput.disabled = true;
    addMessage("user", text);
    aiInput.value = "";
    setAiReady(true, "กำลังให้ LocalLife Brain ประเมิน...");

    try {
      const context = conversationState
        ? { conversation_state: conversationState }
        : {};
      const response = await fetch(apiUrl(decisionEndpoint), {
        method: "POST",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text,
          request_id: `prachinlife-web-${Date.now()}`,
          context
        })
      });
      const payload = await response.json();
      if (!response.ok || !payload || payload.ok !== true || !payload.result) {
        throw new Error(`decision http ${response.status}`);
      }
      if (payload.result.conversation_state &&
          typeof payload.result.conversation_state === "object") {
        conversationState = payload.result.conversation_state;
      }
      addMessage("assistant", responseText(payload.result));
      setAiReady(true, "พร้อมใช้งาน • ผ่าน LocalLife Decision API");
    } catch (err) {
      addMessage(
        "assistant",
        "ตอนนี้เชื่อมผู้ช่วย AI ไม่สำเร็จครับ ระบบจะไม่เดาคำตอบให้ ลองใหม่อีกครั้งเมื่อ API พร้อม"
      );
      setAiReady(Boolean(decisionEndpoint), "การตอบครั้งล่าสุดเชื่อมไม่สำเร็จ");
      console.warn("Decision API blocked:", err instanceof Error ? err.message : "unknown");
    } finally {
      sending = false;
      aiSend.disabled = false;
      aiReset.disabled = false;
      aiInput.disabled = false;
      try {
        aiInput.focus({ preventScroll: true });
      } catch (_) {
        aiInput.focus();
      }
      window.setTimeout(syncAssistantViewport, 50);
    }
  }

  aiOpen.addEventListener("click", openAssistant);
  aiClose.addEventListener("click", closeAssistant);
  aiReset.addEventListener("click", resetAssistant);
  aiSend.addEventListener("click", sendAssistant);
  aiInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendAssistant();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !aiPanel.hidden) {
      event.preventDefault();
      closeAssistant();
    }
  });

  window.addEventListener("resize", syncAssistantViewport);
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", syncAssistantViewport);
    window.visualViewport.addEventListener("scroll", syncAssistantViewport);
  }

  loadContext();
})();
