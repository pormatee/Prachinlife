(function (global) {
  "use strict";

  const DECISION_TIMEOUT_MS = 90000;
  const MAX_ALTERNATIVES = 2;
  const CHAT_MEMORY_STORAGE_KEY = "prachinlife.ai_assistant.conversation.v1";
  const CHAT_MEMORY_SCHEMA_VERSION = 1;
  const CHAT_MEMORY_MAX_MESSAGES = 80;
  const CHAT_MEMORY_MAX_USER_TURNS = 8;
  const CHAT_MEMORY_MAX_TEXT_CHARS = 6000;

  // AI ASSISTANT FEATURE UX V2 + CONVERSATIONAL AI GATEWAY V1
  // The gateway carries explicit user/device context only. It never ranks,
  // selects candidates, or changes the decision returned by MSB/DQE.
  let robotAssistPendingBaseQuery = "";
  let robotAssistPendingContextField = "";
  let robotAssistConversationContext = Object.create(null);
  let robotAssistConversationAnchor = "";
  let robotAssistConversationUserTurns = [];
  let robotAssistStoredMessages = [];
  let robotAssistDeviceLocationState = "unknown";
  let robotAssistDeviceLocationAt = 0;
  let robotAssistSemanticState = null;


  function normalizedSemanticState(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
    if (raw.schema_version !== "SEMANTIC-CONVERSATION-STATE-V1") return null;
    const candidateIds = Array.isArray(raw.candidate_ids)
      ? raw.candidate_ids.map((value) => String(value || "").trim()).filter(Boolean).slice(0, 3)
      : [];
    const refinements = Array.isArray(raw.refinements)
      ? raw.refinements.map((value) => String(value || "").trim()).filter(Boolean).slice(0, 8)
      : [];
    const referenced = String(raw.referenced_candidate_id || "").trim();
    return {
      schema_version: "SEMANTIC-CONVERSATION-STATE-V1",
      turn_index: Math.max(0, Number(raw.turn_index || 0) || 0),
      active_request_text: String(raw.active_request_text || "").slice(0, 1000),
      category: String(raw.category || "").slice(0, 80),
      decision_object: String(raw.decision_object || "").slice(0, 80),
      province: String(raw.province || "").slice(0, 120),
      near_me: raw.near_me === true,
      refinements: refinements,
      candidate_ids: candidateIds,
      referenced_candidate_id: candidateIds.includes(referenced) ? referenced : "",
      reference_fact: ["hours", "parking", "address", "phone", "website"].includes(String(raw.reference_fact || ""))
        ? String(raw.reference_fact)
        : "",
      last_user_text: String(raw.last_user_text || "").slice(0, 1000),
    };
  }

  function captureSemanticState(result) {
    const nextState = normalizedSemanticState(result?.conversation_state);
    if (!nextState) return false;
    robotAssistSemanticState = nextState;
    saveConversationMemory();
    return true;
  }

  function chatStorage() {
    try {
      return global.localStorage || null;
    } catch (_) {
      return null;
    }
  }

  function persistentConversationContext() {
    const out = {};
    const locationText = String(
      robotAssistConversationContext.location_text || ""
    ).trim();
    if (locationText) out.location_text = locationText;
    // Exact device coordinates are deliberately ephemeral. A refresh must
    // reacquire GPS if the Brain still requires current_location.
    return out;
  }

  function normalizedStoredMessages(raw) {
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((item) => item && (item.role === "user" || item.role === "assistant"))
      .map((item) => ({
        role: item.role,
        text: String(item.text || "").slice(0, 1200),
      }))
      .filter((item) => item.text.trim())
      .slice(-CHAT_MEMORY_MAX_MESSAGES);
  }

  function normalizedUserTurns(raw) {
    if (!Array.isArray(raw)) return [];
    return raw
      .map((value) => String(value || "").trim().slice(0, 1000))
      .filter(Boolean)
      .slice(-CHAT_MEMORY_MAX_USER_TURNS);
  }

  function saveConversationMemory() {
    const storage = chatStorage();
    if (!storage) return false;
    const now = Date.now();
    const state = {
      schema_version: CHAT_MEMORY_SCHEMA_VERSION,
      saved_at: now,
      messages: robotAssistStoredMessages.slice(-CHAT_MEMORY_MAX_MESSAGES),
      user_turns: robotAssistConversationUserTurns.slice(-CHAT_MEMORY_MAX_USER_TURNS),
      conversation_anchor: String(robotAssistConversationAnchor || "").slice(
        0,
        CHAT_MEMORY_MAX_TEXT_CHARS
      ),
      pending_base_query: String(robotAssistPendingBaseQuery || "").slice(
        0,
        CHAT_MEMORY_MAX_TEXT_CHARS
      ),
      pending_context_field: String(robotAssistPendingContextField || ""),
      context: persistentConversationContext(),
      semantic_state: normalizedSemanticState(robotAssistSemanticState),
    };
    try {
      storage.setItem(CHAT_MEMORY_STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch (_) {
      return false;
    }
  }

  function clearConversationMemory() {
    const storage = chatStorage();
    if (!storage) return;
    try {
      storage.removeItem(CHAT_MEMORY_STORAGE_KEY);
    } catch (_) {
      // Storage failure must not block the assistant.
    }
  }

  function loadConversationMemory() {
    const storage = chatStorage();
    if (!storage) return false;
    let parsed = null;
    try {
      const raw = storage.getItem(CHAT_MEMORY_STORAGE_KEY);
      if (!raw) return false;
      parsed = JSON.parse(raw);
    } catch (_) {
      clearConversationMemory();
      return false;
    }

    if (
      !parsed
      || parsed.schema_version !== CHAT_MEMORY_SCHEMA_VERSION
    ) {
      clearConversationMemory();
      return false;
    }

    robotAssistStoredMessages = normalizedStoredMessages(parsed.messages);
    robotAssistConversationUserTurns = normalizedUserTurns(parsed.user_turns);
    robotAssistConversationAnchor = String(
      parsed.conversation_anchor || ""
    ).slice(0, CHAT_MEMORY_MAX_TEXT_CHARS);
    robotAssistPendingBaseQuery = String(
      parsed.pending_base_query || ""
    ).slice(0, CHAT_MEMORY_MAX_TEXT_CHARS);
    const restoredPendingField = String(
      parsed.pending_context_field || ""
    );
    robotAssistPendingContextField = (
      restoredPendingField === "current_location"
      || restoredPendingField === "location"
    ) ? restoredPendingField : "";

    robotAssistConversationContext = Object.create(null);
    const locationText = String(parsed?.context?.location_text || "").trim();
    if (locationText) {
      robotAssistConversationContext.location_text = locationText.slice(0, 200);
    }
    robotAssistSemanticState = normalizedSemanticState(parsed.semantic_state);

    // Device coordinates are never restored from browser storage.
    robotAssistDeviceLocationState = "unknown";
    robotAssistDeviceLocationAt = 0;
    return true;
  }

  function rememberUserTurn(query) {
    const value = String(query || "").trim();
    if (!value) return;
    robotAssistConversationUserTurns.push(value);
    robotAssistConversationUserTurns =
      robotAssistConversationUserTurns.slice(-CHAT_MEMORY_MAX_USER_TURNS);
    if (!robotAssistConversationAnchor) {
      robotAssistConversationAnchor = value;
    }
    saveConversationMemory();
  }

  function conversationDecisionText(query, pendingWasStructured) {
    const latest = String(query || "").trim();
    if (!latest) return "";
    // Multi-turn meaning now comes from server-issued structured semantic state.
    // Only a structured clarification answer replays the pending base request.
    if (robotAssistPendingBaseQuery && pendingWasStructured) {
      return robotAssistPendingBaseQuery;
    }
    return latest;
  }

  function resetConversationState() {
    robotAssistPendingBaseQuery = "";
    robotAssistPendingContextField = "";
    robotAssistConversationContext = Object.create(null);
    robotAssistConversationAnchor = "";
    robotAssistConversationUserTurns = [];
    robotAssistStoredMessages = [];
    robotAssistDeviceLocationState = "unknown";
    robotAssistDeviceLocationAt = 0;
    robotAssistSemanticState = null;
    clearConversationMemory();
  }

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

  function unresolvedContextFields(result) {
    const raw = result?.understanding?.unresolved_context;
    if (!Array.isArray(raw)) return [];
    return raw
      .map((value) => String(value || "").trim())
      .filter(Boolean);
  }

  function nextPendingContextField(result) {
    const unresolved = unresolvedContextFields(result);
    if (unresolved.includes("current_location")) return "current_location";
    if (unresolved.includes("location")) return "location";
    return "";
  }

  function resultNeedsLocationClarification(result) {
    const pending = nextPendingContextField(result);
    return pending === "current_location" || pending === "location";
  }

  function resultRequestsNearMe(result) {
    return result?.understanding?.near_me === true;
  }

  function decisionContextPayload() {
    const payload = {};
    const currentLocation = robotAssistConversationContext.current_location;
    const locationFresh =
      robotAssistDeviceLocationAt === 0
      || (Date.now() - robotAssistDeviceLocationAt) <= 300000;
    if (
      locationFresh
      && Array.isArray(currentLocation)
      && currentLocation.length === 2
      && Number.isFinite(Number(currentLocation[0]))
      && Number.isFinite(Number(currentLocation[1]))
    ) {
      payload.current_location = [
        Number(currentLocation[0]),
        Number(currentLocation[1]),
      ];
    }

    const locationText = String(
      robotAssistConversationContext.location_text || ""
    ).trim();
    if (locationText) payload.location_text = locationText;

    const semanticState = normalizedSemanticState(robotAssistSemanticState);
    if (semanticState) payload.conversation_state = semanticState;

    return payload;
  }

  function deviceLocation() {
    // Do not permanently trust an earlier denied/unavailable state. The user
    // may enable device location after the previous attempt, so every new
    // near-me request is allowed to ask the browser for the current position.
    if (!global.navigator?.geolocation) {
      robotAssistDeviceLocationState = "unavailable";
      return Promise.resolve(null);
    }

    return new Promise((resolve) => {
      global.navigator.geolocation.getCurrentPosition(
        (position) => {
          const latitude = Number(position?.coords?.latitude);
          const longitude = Number(position?.coords?.longitude);
          if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
            robotAssistDeviceLocationState = "unavailable";
            resolve(null);
            return;
          }
          robotAssistDeviceLocationState = "granted";
          robotAssistDeviceLocationAt = Date.now();
          robotAssistConversationContext.current_location = [latitude, longitude];
          delete robotAssistConversationContext.location_text;
          resolve([latitude, longitude]);
        },
        (error) => {
          robotAssistDeviceLocationState =
            Number(error?.code) === 1 ? "denied" : "unavailable";
          resolve(null);
        },
        {
          enableHighAccuracy: false,
          timeout: 7000,
          maximumAge: 300000,
        }
      );
    });
  }

  function applyPendingUserContext(query) {
    const value = String(query || "").trim();
    if (!value || !robotAssistPendingContextField) return false;

    if (
      robotAssistPendingContextField === "current_location"
      || robotAssistPendingContextField === "location"
    ) {
      robotAssistConversationContext.location_text = value;
      delete robotAssistConversationContext.current_location;
      robotAssistDeviceLocationAt = 0;
      robotAssistPendingContextField = "";
      saveConversationMemory();
      return true;
    }
    return false;
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
    if (action?.type) button.dataset.actionType = String(action.type);
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

  function orderedDecisionIds(result) {
    const bestId = String(
      result?.explanation?.best_fit_candidate_id ??
      result?.decision?.best_fit_candidate_id ??
      ""
    ).trim();
    const alternatives = Array.isArray(result?.explanation?.alternatives)
      ? result.explanation.alternatives.slice(0, MAX_ALTERNATIVES)
      : [];
    const ids = [bestId, ...alternatives.map((id) => String(id || "").trim())]
      .filter(Boolean);
    return ids.filter((id, index) => ids.indexOf(id) === index).slice(0, 3);
  }

  function resolveOrderedDecisionPlaces(result) {
    const ids = orderedDecisionIds(result);
    if (!ids.length) return null;
    const places = ids.map((id) => resolvePlace(id));
    if (places.some((place) => !place)) return null;
    return places;
  }

  function placeGroup(place) {
    const categories = Array.isArray(place?.categories) ? place.categories : [];
    return String(place?.main_category ?? place?.category ?? categories[0] ?? "").trim();
  }

  function renderDecisionPlaceCard(place, rank) {
    const article = document.createElement("article");
    article.className = "local-life-decision-place-card";
    article.dataset.placeId = placeId(place);
    article.dataset.decisionRank = String(rank);

    const image = core().placeImage;
    if (image && typeof image.renderPlaceImage === "function") {
      const media = document.createElement("div");
      media.className = "local-life-decision-place-media";
      media.innerHTML = image.renderPlaceImage(
        place, placeGroup(place), String(place?.title ?? place?.name ?? "สถานที่")
      );
      article.appendChild(media);
    }

    const content = document.createElement("div");
    content.className = "local-life-decision-place-content";
    content.appendChild(textNode(
      "span", "local-life-decision-place-rank",
      rank === 1 ? "A · เหมาะที่สุด" : (rank === 2 ? "B · ตัวเลือกสำรอง" : "C · ตัวเลือกสำรอง")
    ));
    content.appendChild(textNode("h4", "", String(place?.title ?? place?.name ?? "สถานที่")));

    const placeCard = core().placeCard;
    if (placeCard && typeof placeCard.getLocationLabel === "function") {
      const location = placeCard.getLocationLabel(place, place?.province || "");
      if (location) content.appendChild(textNode("p", "local-life-decision-place-location", location));
    }
    if (placeCard && typeof placeCard.renderActions === "function") {
      const actionWrap = document.createElement("div");
      actionWrap.className = "local-life-decision-place-actions";
      actionWrap.innerHTML = placeCard.renderActions(place);
      if (actionWrap.childElementCount) content.appendChild(actionWrap);
    }
    article.appendChild(content);
    return article;
  }

  function appendDecisionPlaceCards(body, result) {
    const places = resolveOrderedDecisionPlaces(result);
    if (!places) return false;
    const wrap = document.createElement("div");
    wrap.className = "local-life-decision-place-cards";
    wrap.setAttribute("aria-label", "สถานที่ที่ Master Super Brain แนะนำตามลำดับ");
    places.forEach((place, index) => wrap.appendChild(renderDecisionPlaceCard(place, index + 1)));
    body.appendChild(wrap);
    return true;
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

    const orderedPlaces = resolveOrderedDecisionPlaces(result);
    if (!orderedPlaces) {
      renderError("ไม่สามารถจับคู่คำแนะนำกับข้อมูลสถานที่ที่เผยแพร่แล้วได้");
      return;
    }

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

    if (!appendDecisionPlaceCards(body, result)) {
      renderError("ไม่สามารถแสดงสถานที่ที่แนะนำตามลำดับได้");
      return;
    }
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
    const input = document.getElementById("robotAssistInput");
    const button = document.getElementById("decisionAssistBtn");
    const query = String(input?.value || "").trim();

    if (!query) {
      openRobotAssist();
      addRobotMessage("assistant", "พิมพ์สิ่งที่อยากให้ช่วยคิดได้เลยครับ เช่น “เที่ยวปราจีนบุรีไหนดี”");
      input?.focus();
      return;
    }

    const api = core().localLifeApiV1;
    if (!api || typeof api.decision !== "function") {
      renderError("LocalLife API ยังไม่พร้อมใช้งาน");
      return;
    }

    const pendingWasStructured = applyPendingUserContext(query);
    const decisionText = conversationDecisionText(query, pendingWasStructured);

    if (button) button.disabled = true;
    addRobotMessage("user", query);
    rememberUserTurn(query);
    input.value = "";
    const thinking = addRobotMessage(
      "assistant",
      "กำลังช่วยคิดจากข้อมูลที่เผยแพร่แล้ว...",
      { persist: false }
    );

    try {
      let response = await api.decision(
        {
          text: decisionText,
          context: decisionContextPayload(),
          request_id: "web-decision-card-v1-" + Date.now(),
          recommendation_limit: 3,
        },
        { timeoutMs: DECISION_TIMEOUT_MS }
      );

      let result = resultPayload(response);

      // For every fresh near-me request, current device position has priority
      // over a location_text remembered from an earlier turn/session.
      // If the browser cannot provide current position, re-ask the Brain with
      // remembered area text removed so the Brain decides what clarification
      // is required. An explicit structured location answer in this turn is
      // respected and is not overridden by GPS.
      if (
        result
        && resultRequestsNearMe(result)
        && !pendingWasStructured
        && !decisionContextPayload().current_location
      ) {
        const location = await deviceLocation();
        if (location) {
          response = await api.decision(
            {
              text: decisionText,
              context: decisionContextPayload(),
              request_id: "web-decision-card-v1-location-" + Date.now(),
              recommendation_limit: 3,
            },
            { timeoutMs: DECISION_TIMEOUT_MS }
          );
          result = resultPayload(response);
        } else {
          const contextWithoutStaleArea = decisionContextPayload();
          delete contextWithoutStaleArea.location_text;
          response = await api.decision(
            {
              text: decisionText,
              context: contextWithoutStaleArea,
              request_id: "web-decision-card-v1-location-missing-" + Date.now(),
              recommendation_limit: 3,
            },
            { timeoutMs: DECISION_TIMEOUT_MS }
          );
          result = resultPayload(response);
        }
      }

      captureSemanticState(result);

      const referenceAnswer = String(result?.reference_answer?.answer || "").trim();
      if (referenceAnswer) {
        if (thinking) thinking.remove();
        robotAssistPendingBaseQuery = "";
        robotAssistPendingContextField = "";
        saveConversationMemory();
        addRobotMessage("assistant", referenceAnswer);
        openRobotAssist();
        input?.focus();
        return;
      }

      const bestId = String(
        result?.explanation?.best_fit_candidate_id ??
        result?.decision?.best_fit_candidate_id ??
        ""
      ).trim();

      if (thinking) thinking.remove();

      if (
        result
        && (
          result.status === "needs_user_input"
          || resultNeedsLocationClarification(result)
          || (!bestId && result.highest_value_question)
        )
      ) {
        robotAssistPendingBaseQuery = decisionText;
        robotAssistPendingContextField = nextPendingContextField(result);
        saveConversationMemory();
        addRobotMessage(
          "assistant",
          String(result.highest_value_question || "ขอข้อมูลเพิ่มอีกนิดครับ").trim()
        );
        input?.focus();
        return;
      }

      if (bestId) {
        robotAssistPendingContextField = "";
        robotAssistPendingBaseQuery = "";
        saveConversationMemory();
        addRobotMessage("assistant", "ได้เลยครับ ระบบตัดสินใจแสดงคำแนะนำให้แล้วครับ");
        renderResponse(response);

        const followUp = String(result?.highest_value_question || "").trim();
        if (followUp) {
          robotAssistPendingBaseQuery = decisionText;
          robotAssistPendingContextField = nextPendingContextField(result);
          saveConversationMemory();
          addRobotMessage("assistant", followUp);
        } else {
          robotAssistPendingBaseQuery = "";
          saveConversationMemory();
          addRobotMessage("assistant", "ถ้าอยากถามต่อหรือให้ช่วยเปรียบเทียบเพิ่มเติม พิมพ์ต่อได้เลยครับ");
        }

        // Keep the compact conversation available after recommendations.
        // It collapses only when the user explicitly closes it or enters place detail.
        openRobotAssist();

        window.setTimeout(function () {
          section()?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 120);
        return;
      }

      robotAssistPendingBaseQuery = "";
      robotAssistPendingContextField = "";
      saveConversationMemory();
      addRobotMessage("assistant", "ตอนนี้ข้อมูลยังไม่พอให้ระบบแนะนำตัวเลือกที่เหมาะสมครับ");
    } catch (error) {
      if (thinking) thinking.remove();
      const isAbort = error?.name === "AbortError";
      addRobotMessage(
        "assistant",
        isAbort
          ? "ระบบใช้เวลานานเกินไป ลองถามใหม่อีกครั้งได้ครับ"
          : "เชื่อมต่อผู้ช่วยไม่สำเร็จ ลองใหม่อีกครั้งได้ครับ"
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
    header.appendChild(textNode("span", "eyebrow", "ROBOT ASSIST"));
    const status = textNode("h2", "", "คำแนะนำจากผู้ช่วย");
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

  function robotPanel() {
    return document.getElementById("robotAssistPanel");
  }

  function robotMessages() {
    return document.getElementById("robotAssistMessages");
  }

  function appendRobotBubble(role, message) {
    const messages = robotMessages();
    if (!messages) return null;
    const bubble = textNode("div", "robot-assist-message " + role, message);
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  function addRobotMessage(role, message, options) {
    const bubble = appendRobotBubble(role, message);
    const persist = options?.persist !== false;
    if (persist && (role === "user" || role === "assistant")) {
      robotAssistStoredMessages.push({
        role,
        text: String(message || "").slice(0, 1200),
      });
      robotAssistStoredMessages =
        robotAssistStoredMessages.slice(-CHAT_MEMORY_MAX_MESSAGES);
      saveConversationMemory();
    }
    return bubble;
  }

  function renderConversationMessages() {
    const messages = robotMessages();
    if (!messages) return;
    messages.replaceChildren();

    if (!robotAssistStoredMessages.length) {
      appendRobotBubble(
        "assistant",
        "สวัสดีครับ อยากให้ช่วยคิดเรื่องกิน เที่ยว ช้อป หรือบริการอะไร?"
      );
      return;
    }

    robotAssistStoredMessages.forEach((item) => {
      appendRobotBubble(item.role, item.text);
    });
    messages.scrollTop = messages.scrollHeight;
  }

  function startNewConversation() {
    resetConversationState();
    renderConversationMessages();
    const input = document.getElementById("robotAssistInput");
    if (input) input.value = "";
    const decisionSection = section();
    if (decisionSection) decisionSection.hidden = true;
    clearBody();
    setStatus("");
    openRobotAssist();
  }

  function openRobotAssist() {
    const panel = robotPanel();
    const button = document.getElementById("decisionAssistBtn");
    if (!panel) return;
    panel.hidden = false;
    syncRobotAssistVisualViewport();
    panel.setAttribute("aria-hidden", "false");
    button?.setAttribute("aria-expanded", "true");
    window.setTimeout(function () {
      document.getElementById("robotAssistInput")?.focus();
    }, 50);
  }

  function closeRobotAssist() {
    const panel = robotPanel();
    const button = document.getElementById("decisionAssistBtn");
    if (!panel) return;
    panel.hidden = true;
    panel.setAttribute("aria-hidden", "true");
    button?.setAttribute("aria-expanded", "false");
  }

  function syncRobotAssistVisualViewport() {
    const panel = robotPanel();
    if (!panel) return;
    const viewport = global.visualViewport;
    const mobile = global.matchMedia?.("(max-width: 520px)")?.matches;
    if (!mobile || !viewport) {
      panel.style.removeProperty("--robot-assist-vv-top");
      panel.style.removeProperty("--robot-assist-vv-height");
      return;
    }

    const top = Math.max(8, Number(viewport.offsetTop || 0) + 8);
    const height = Math.max(
      260,
      Number(viewport.height || global.innerHeight || 0) - 16
    );
    panel.style.setProperty("--robot-assist-vv-top", top + "px");
    panel.style.setProperty("--robot-assist-vv-height", height + "px");
  }

  function bindRobotAssistVisualViewport() {
    if (document.documentElement.dataset.robotAssistVisualViewportBound === "1") return;
    document.documentElement.dataset.robotAssistVisualViewportBound = "1";
    const viewport = global.visualViewport;
    if (!viewport) return;
    viewport.addEventListener("resize", syncRobotAssistVisualViewport);
    viewport.addEventListener("scroll", syncRobotAssistVisualViewport);
    global.addEventListener("orientationchange", syncRobotAssistVisualViewport);
  }

  function createRobotPanel() {
    if (robotPanel()) return robotPanel();

    const panel = document.createElement("aside");
    panel.id = "robotAssistPanel";
    panel.className = "robot-assist-panel";
    panel.hidden = true;
    panel.setAttribute("aria-hidden", "true");
    panel.setAttribute("aria-label", "AI Assistant");

    const header = document.createElement("div");
    header.className = "robot-assist-header";

    const titleWrap = document.createElement("div");
    titleWrap.className = "robot-assist-title";
    titleWrap.appendChild(textNode("span", "robot-assist-avatar", "🤖"));

    const titleText = document.createElement("div");
    titleText.appendChild(textNode("strong", "", "AI Assistant"));
    titleText.appendChild(textNode("small", "", "เพื่อนช่วยคิดให้ตัดสินใจง่ายขึ้น"));
    titleWrap.appendChild(titleText);

    const headerActions = document.createElement("div");
    headerActions.className = "robot-assist-header-actions";

    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "robot-assist-reset";
    reset.textContent = "เริ่มใหม่";
    reset.setAttribute("aria-label", "เริ่มบทสนทนาใหม่");
    reset.addEventListener("click", startNewConversation);

    const close = document.createElement("button");
    close.type = "button";
    close.className = "robot-assist-close";
    close.setAttribute("aria-label", "ปิด Robot Assist");
    close.textContent = "×";
    close.addEventListener("click", closeRobotAssist);

    headerActions.appendChild(reset);
    headerActions.appendChild(close);
    header.appendChild(titleWrap);
    header.appendChild(headerActions);

    const messages = document.createElement("div");
    messages.id = "robotAssistMessages";
    messages.className = "robot-assist-messages";

    const composer = document.createElement("div");
    composer.className = "robot-assist-composer";

    const input = document.createElement("textarea");
    input.id = "robotAssistInput";
    input.rows = 1;
    input.autocomplete = "off";
    input.placeholder = "ถาม AI Assistant...";
    input.setAttribute("aria-label", "ข้อความถึง AI Assistant");

    const send = document.createElement("button");
    send.type = "button";
    send.className = "robot-assist-send";
    send.textContent = "ส่ง";
    send.addEventListener("click", requestDecision);

    input.addEventListener("focus", function () {
      window.setTimeout(syncRobotAssistVisualViewport, 40);
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        requestDecision();
      }
    });

    composer.appendChild(input);
    composer.appendChild(send);
    panel.appendChild(header);
    panel.appendChild(messages);
    panel.appendChild(composer);

    const feature = document.getElementById("robotAssistFeature");
    if (feature?.parentNode) {
      feature.insertAdjacentElement("afterend", panel);
    } else {
      const controlCenter = document.getElementById("controlCenter");
      if (controlCenter) {
        controlCenter.prepend(panel);
      } else {
        document.body.prepend(panel);
      }
    }
    renderConversationMessages();
    return panel;
  }

  function modernRobotIcon() {
    return `
      <svg class="ai-assistant-mark" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
        <rect x="7" y="10" width="34" height="27" rx="10" fill="none" stroke="currentColor" stroke-width="2.6"/>
        <path d="M24 10V6" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/>
        <circle cx="24" cy="4.5" r="2.3" fill="currentColor"/>
        <circle cx="18" cy="23" r="2.7" fill="currentColor"/>
        <circle cx="30" cy="23" r="2.7" fill="currentColor"/>
        <path d="M17.5 30c2 2 4.1 3 6.5 3s4.5-1 6.5-3" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>
        <path d="M4.5 18h3M40.5 18h3" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>
        <path d="M38 5l.8 2.2L41 8l-2.2.8L38 11l-.8-2.2L35 8l2.2-.8L38 5Z" fill="currentColor"/>
      </svg>`;
  }

  function createAssistButton() {
    if (document.getElementById("decisionAssistBtn")) {
      return document.getElementById("decisionAssistBtn");
    }

    const searchButton = document.getElementById("searchBtn");
    const controlCenter = document.getElementById("controlCenter");
    if (!searchButton && !controlCenter) return null;

    const feature = document.createElement("div");
    feature.id = "robotAssistFeature";
    feature.className = "ai-assistant-feature";

    const visual = document.createElement("div");
    visual.className = "ai-assistant-feature-visual";
    visual.innerHTML = modernRobotIcon();

    const copy = document.createElement("div");
    copy.className = "ai-assistant-feature-copy";
    copy.appendChild(textNode("strong", "", "AI Assistant"));
    copy.appendChild(textNode("span", "", "ให้ AI ช่วยคิด เปรียบเทียบ และแนะนำจากข้อมูลสถานที่"));

    const button = document.createElement("button");
    button.id = "decisionAssistBtn";
    button.className = "ai-assistant-feature-button";
    button.type = "button";
    button.textContent = "ถาม AI";
    button.setAttribute("aria-label", "เปิด AI Assistant");
    button.setAttribute("aria-controls", "robotAssistPanel");
    button.setAttribute("aria-expanded", "false");

    feature.appendChild(visual);
    feature.appendChild(copy);
    feature.appendChild(button);

    const searchRow = searchButton?.parentElement;
    if (searchRow?.parentNode) {
      searchRow.insertAdjacentElement("afterend", feature);
    } else if (controlCenter) {
      controlCenter.prepend(feature);
    } else {
      document.body.prepend(feature);
    }

    return button;
  }

  function bindDetailCollapse() {
    if (document.documentElement.dataset.robotAssistDetailCollapseBound === "1") return;
    document.documentElement.dataset.robotAssistDetailCollapseBound = "1";

    document.addEventListener("click", function (event) {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;

      const detailControl = target.closest(
        ".place-card-action-detail, [data-action-type='OPEN_PLACE_CARD']"
      );
      if (!detailControl) return;

      // Entering place detail gets visual priority, but chat history is preserved.
      closeRobotAssist();
    });
  }

  function init() {
    loadConversationMemory();
    createSection();
    createRobotPanel();
    bindRobotAssistVisualViewport();
    syncRobotAssistVisualViewport();
    bindDetailCollapse();
    const button = createAssistButton();
    if (!button || button.dataset.bound === "1") return;
    button.dataset.bound = "1";
    button.addEventListener("click", function () {
      if (robotPanel()?.hidden) {
        openRobotAssist();
      } else {
        closeRobotAssist();
      }
    });
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
