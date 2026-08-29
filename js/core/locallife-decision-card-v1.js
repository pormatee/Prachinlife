(function (global) {
  "use strict";

  const DECISION_TIMEOUT_MS = 90000;
  const MAX_ALTERNATIVES = 2;

  const LABELS = Object.freeze({
    opening_hours: "เวลาเปิด-ปิด",
    phone: "เบอร์โทร",
    address: "ที่อยู่",
    coordinates: "ตำแหน่ง",
    price: "ราคา",
    parking: "ที่จอดรถ",
  });

  function core() {
    return global.PrachinLife?.core || {};
  }

  function resultPayload(input) {
    if (!input || typeof input !== "object" || Array.isArray(input)) return null;
    if (input.result && typeof input.result === "object" && !Array.isArray(input.result)) {
      return input.result;
    }
    return input;
  }

  function placeId(place) {
    return String(place?.id ?? place?.place_id ?? place?.metadata?.v2_place_id ?? "").trim();
  }

  function allPlaces() {
    const runtime = global.PrachinLifeV2Runtime;
    if (!runtime || typeof runtime.getPlaces !== "function") return [];
    const places = runtime.getPlaces();
    return Array.isArray(places) ? places : [];
  }

  function resolvePlace(id) {
    const wanted = String(id || "").trim();
    if (!wanted) return null;
    return allPlaces().find((place) => placeId(place) === wanted) || null;
  }

  function placeName(id, fallback) {
    const place = resolvePlace(id);
    return String(place?.title ?? place?.name ?? fallback ?? "").trim();
  }

  function actionOf(result, type) {
    const actions = Array.isArray(result?.actions) ? result.actions : [];
    return actions.find((action) => action?.type === type) || null;
  }

  function textNode(tag, className, value) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = String(value || "");
    return el;
  }

  function cardBody() {
    return document.getElementById("localLifeDecisionCardBody");
  }

  function section() {
    return document.getElementById("localLifeDecisionCardSection");
  }

  function setVisible(visible) {
    const el = section();
    if (el) el.hidden = !visible;
  }

  function setStatus(message) {
    const el = document.getElementById("localLifeDecisionCardStatus");
    if (el) el.textContent = String(message || "");
  }

  function clearBody() {
    const body = cardBody();
    if (body) body.replaceChildren();
    return body;
  }

  function renderLoading() {
    const body = clearBody();
    if (!body) return;
    setVisible(true);
    setStatus("กำลังช่วยคิดจากข้อมูลที่เผยแพร่แล้ว");
    body.appendChild(textNode("p", "local-life-decision-loading", "กำลังประมวลผล... ครั้งแรกอาจใช้เวลาสักครู่"));
  }

  function renderError(message) {
    const body = clearBody();
    if (!body) return;
    setVisible(true);
    setStatus("ยังตอบไม่ได้");
    body.appendChild(textNode("p", "local-life-decision-error", message || "เชื่อมต่อผู้ช่วยไม่สำเร็จ ลองใหม่อีกครั้งได้"));
  }

  function renderQuestion(result) {
    const body = clearBody();
    if (!body) return;
    setVisible(true);
    setStatus("ขอข้อมูลเพิ่มอีกนิด");

    const question = String(result?.highest_value_question || "").trim();
    body.appendChild(textNode("p", "local-life-decision-question", question || "ช่วยระบุสิ่งที่ต้องการให้ชัดขึ้นอีกนิด"));
    body.appendChild(textNode("p", "local-life-decision-hint", "พิมพ์คำตอบต่อในช่องด้านบน แล้วกด “ช่วยคิด” อีกครั้ง"));
  }

  function uncertaintyLabels(result) {
    const raw = Array.isArray(result?.explanation?.uncertainty_fields)
      ? result.explanation.uncertainty_fields
      : [];
    const out = [];
    raw.forEach((field) => {
      const key = String(field || "").trim();
      if (!key || out.includes(key)) return;
      out.push(key);
    });
    return out.slice(0, 3).map((key) => LABELS[key] || key.replaceAll("_", " "));
  }

  function executeFromUserClick(action) {
    const executor = core().actionExecutorV1;
    if (!action || !executor || typeof executor.execute !== "function") {
      return { status: "not_available" };
    }
    return executor.execute(action, { userConfirmed: true });
  }

  function actionButton(label, action, variant) {
    if (!action) return null;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "local-life-decision-action" + (variant ? " " + variant : "");
    button.textContent = label;
    button.addEventListener("click", function () {
      const outcome = executeFromUserClick(action);
      if (outcome?.status === "not_available") {
        setStatus("รายการนี้ยังเปิดจากหน้าเว็บไม่ได้");
      } else if (outcome?.status === "blocked") {
        setStatus("เบราว์เซอร์บล็อกการเปิดหน้าต่างใหม่");
      }
    });
    return button;
  }

  function appendAlternatives(body, result) {
    const ids = Array.isArray(result?.explanation?.alternatives)
      ? result.explanation.alternatives.slice(0, MAX_ALTERNATIVES)
      : [];
    if (!ids.length) return;

    const names = ids
      .map((id, index) => placeName(id, "ตัวเลือกสำรอง " + (index + 1)))
      .filter(Boolean);
    if (!names.length) return;

    const wrap = document.createElement("div");
    wrap.className = "local-life-decision-alternatives";
    wrap.appendChild(textNode("strong", "", "ตัวเลือกสำรอง"));
    const list = document.createElement("ul");
    names.forEach((name) => list.appendChild(textNode("li", "", name)));
    wrap.appendChild(list);
    body.appendChild(wrap);
  }

  function appendUncertainty(body, result) {
    const labels = uncertaintyLabels(result);
    if (!labels.length) return;
    body.appendChild(textNode(
      "p",
      "local-life-decision-uncertainty",
      "ข้อมูลที่ยังควรตรวจสอบ: " + labels.join(" • ")
    ));
  }

  function renderRecommendation(result) {
    const body = clearBody();
    if (!body) return;
    setVisible(true);

    const bestId = String(
      result?.explanation?.best_fit_candidate_id ??
      result?.decision?.best_fit_candidate_id ??
      ""
    ).trim();

    const bestName = String(
      result?.explanation?.best_fit_name ??
      placeName(bestId, "ตัวเลือกที่เหมาะที่สุด")
    ).trim();

    setStatus("คำแนะนำจาก Master Super Brain");

    const hero = document.createElement("div");
    hero.className = "local-life-decision-primary";
    hero.appendChild(textNode("span", "local-life-decision-kicker", "เหมาะที่สุดจากข้อมูลที่มี"));
    hero.appendChild(textNode("h3", "", bestName || "ตัวเลือกที่เหมาะที่สุด"));
    hero.appendChild(textNode("p", "local-life-decision-reason", "ผ่านเงื่อนไขที่ระบบตรวจสอบได้จากข้อมูลที่เผยแพร่แล้ว"));
    body.appendChild(hero);

    appendAlternatives(body, result);
    appendUncertainty(body, result);

    const actions = document.createElement("div");
    actions.className = "local-life-decision-actions";

    [
      actionButton("ดูร้าน", actionOf(result, "OPEN_PLACE_CARD"), "primary"),
      actionButton("แผนที่", actionOf(result, "OPEN_MAP")),
      actionButton("เปรียบเทียบ", actionOf(result, "COMPARE_PLACES")),
      actionButton("ใช้ตำแหน่งของฉัน", actionOf(result, "REQUEST_LOCATION")),
    ].filter(Boolean).forEach((button) => actions.appendChild(button));

    if (actions.childElementCount) body.appendChild(actions);

    body.appendChild(textNode(
      "p",
      "local-life-decision-human-note",
      "ข้อมูลนี้ช่วยประกอบการตัดสินใจ คุณเป็นผู้ตัดสินใจสุดท้าย"
    ));
  }

  function renderResponse(envelope) {
    const result = resultPayload(envelope);
    if (!result) {
      renderError("รูปแบบคำตอบจากระบบไม่ถูกต้อง");
      return;
    }

    const status = String(result.status || "").trim();
    const bestId = String(
      result?.explanation?.best_fit_candidate_id ??
      result?.decision?.best_fit_candidate_id ??
      ""
    ).trim();

    if (status === "needs_user_input" || (!bestId && result.highest_value_question)) {
      renderQuestion(result);
      return;
    }

    if (bestId) {
      renderRecommendation(result);
      return;
    }

    renderError("ยังไม่มีข้อมูลพอให้แนะนำตัวเลือกที่เหมาะสม");
  }

  async function requestDecision() {
    const input = document.getElementById("searchInput");
    const button = document.getElementById("decisionAssistBtn");
    const query = String(input?.value || "").trim();

    if (!query) {
      setVisible(true);
      setStatus("พิมพ์สิ่งที่ต้องการก่อน");
      const body = clearBody();
      if (body) {
        body.appendChild(textNode("p", "local-life-decision-hint", "เช่น “หาร้านเจในปทุมธานี”"));
      }
      input?.focus();
      return;
    }

    const api = core().localLifeApiV1;
    if (!api || typeof api.decision !== "function") {
      renderError("LocalLife API ยังไม่พร้อมใช้งาน");
      return;
    }

    if (button) button.disabled = true;
    renderLoading();

    try {
      const response = await api.decision(
        {
          text: query,
          request_id: "web-decision-card-v1-" + Date.now(),
          recommendation_limit: 3,
        },
        { timeoutMs: DECISION_TIMEOUT_MS }
      );
      renderResponse(response);
    } catch (error) {
      const isAbort = error?.name === "AbortError";
      renderError(
        isAbort
          ? "ระบบใช้เวลานานเกินไป ลองกด “ช่วยคิด” อีกครั้ง"
          : "เชื่อมต่อผู้ช่วยไม่สำเร็จ ลองใหม่อีกครั้งได้"
      );
    } finally {
      if (button) button.disabled = false;
    }
  }

  function createSection() {
    if (section()) return section();

    const controlCenter = document.getElementById("controlCenter");
    if (!controlCenter?.parentNode) return null;

    const el = document.createElement("section");
    el.id = "localLifeDecisionCardSection";
    el.className = "local-life-decision-section";
    el.hidden = true;
    el.setAttribute("aria-live", "polite");

    const container = document.createElement("div");
    container.className = "container";

    const card = document.createElement("div");
    card.className = "local-life-decision-card";

    const header = document.createElement("div");
    header.className = "local-life-decision-header";
    header.appendChild(textNode("span", "eyebrow", "LOCAL LIFE DECISION"));
    const status = textNode("h2", "", "เพื่อนช่วยคิด");
    status.id = "localLifeDecisionCardStatus";
    header.appendChild(status);

    const body = document.createElement("div");
    body.id = "localLifeDecisionCardBody";

    card.appendChild(header);
    card.appendChild(body);
    container.appendChild(card);
    el.appendChild(container);

    controlCenter.parentNode.insertBefore(el, controlCenter);
    return el;
  }

  function createAssistButton() {
    if (document.getElementById("decisionAssistBtn")) {
      return document.getElementById("decisionAssistBtn");
    }

    const searchButton = document.getElementById("searchBtn");
    if (!searchButton?.parentNode) return null;

    const button = document.createElement("button");
    button.id = "decisionAssistBtn";
    button.className = "secondary-button local-life-decision-trigger";
    button.type = "button";
    button.textContent = "ช่วยคิด";
    button.setAttribute("aria-label", "ให้ LocalLife ช่วยคิดจากคำค้นนี้");
    searchButton.insertAdjacentElement("afterend", button);
    return button;
  }

  function init() {
    createSection();
    const button = createAssistButton();
    if (!button || button.dataset.bound === "1") return;
    button.dataset.bound = "1";
    button.addEventListener("click", requestDecision);
  }

  global.PrachinLife = global.PrachinLife || {};
  global.PrachinLife.core = global.PrachinLife.core || {};
  global.PrachinLife.core.decisionCardV1 = Object.freeze({
    init,
    requestDecision,
    renderResponse,
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})(window);
