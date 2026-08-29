(function (global) {
  "use strict";

  const CONTRACT_VERSION = "v1";
  const ALLOWED_ACTION_TYPES = Object.freeze([
    "OPEN_PLACE_CARD",
    "SHOW_ALTERNATIVES",
    "COMPARE_PLACES",
    "OPEN_MAP",
    "REQUEST_LOCATION",
    "ASK_ONE_QUESTION",
  ]);
  const ALLOWED = new Set(ALLOWED_ACTION_TYPES);

  function resultPayload(input) {
    if (!input || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("Decision result must be an object");
    }
    if (
      input.result &&
      typeof input.result === "object" &&
      !Array.isArray(input.result)
    ) {
      return input.result;
    }
    return input;
  }

  function validateAction(action) {
    if (!action || typeof action !== "object" || Array.isArray(action)) {
      return { ok: false, reason: "invalid_action" };
    }
    if (!ALLOWED.has(action.type)) {
      return { ok: false, reason: "action_not_allowlisted" };
    }
    return { ok: true };
  }

  function allPlaces() {
    const runtime = global.PrachinLifeV2Runtime;
    if (!runtime || typeof runtime.getPlaces !== "function") return [];
    const places = runtime.getPlaces();
    return Array.isArray(places) ? places : [];
  }

  function findPlace(placeId) {
    const id = String(placeId || "").trim();
    if (!id) return null;
    return allPlaces().find((place) =>
      String(
        place?.id ??
        place?.place_id ??
        place?.metadata?.v2_place_id ??
        ""
      ).trim() === id
    ) || null;
  }

  function emit(name, detail) {
    if (
      typeof global.CustomEvent !== "function" ||
      typeof global.dispatchEvent !== "function"
    ) {
      return false;
    }
    global.dispatchEvent(new CustomEvent(name, { detail }));
    return true;
  }

  function needsConfirmation(action, options) {
    if (!action.requires_user_confirmation) return false;
    return !(options && options.userConfirmed === true);
  }

  function executeOpenPlaceCard(action) {
    const placeId = action?.target?.place_id;
    const place = findPlace(placeId);
    const detail = global.PrachinLife?.core?.placeDetail;
    if (!place || !detail || typeof detail.openPlaceDetail !== "function") {
      return { status: "not_available", action_type: action.type };
    }
    const opened = detail.openPlaceDetail(place);
    return {
      status: opened ? "executed" : "not_available",
      action_type: action.type,
      place_id: String(placeId || ""),
    };
  }

  function executeShowAlternatives(action) {
    const ids = Array.isArray(action?.params?.place_ids)
      ? action.params.place_ids.map(String).filter(Boolean)
      : [];
    const places = ids.map(findPlace).filter(Boolean);
    emit("prachinlife:show-alternatives", {
      action_type: action.type,
      place_ids: ids,
      places,
    });
    return {
      status: "dispatched",
      action_type: action.type,
      place_ids: ids,
    };
  }

  function executeComparePlaces(action) {
    const ids = Array.isArray(action?.params?.place_ids)
      ? action.params.place_ids.map(String).filter(Boolean)
      : [];
    const places = ids.map(findPlace).filter(Boolean);
    emit("prachinlife:compare-places", {
      action_type: action.type,
      place_ids: ids,
      places,
    });
    return {
      status: "dispatched",
      action_type: action.type,
      place_ids: ids,
    };
  }

  function executeOpenMap(action) {
    const placeId = action?.target?.place_id;
    const place = findPlace(placeId);
    const buildMapUrl = global.PrachinLife?.core?.buildMapUrl;
    if (!place || typeof buildMapUrl !== "function") {
      return { status: "not_available", action_type: action.type };
    }
    const url = buildMapUrl(place);
    if (!url) return { status: "not_available", action_type: action.type };

    const opened = global.open(url, "_blank", "noopener,noreferrer");
    return {
      status: opened === null ? "blocked" : "executed",
      action_type: action.type,
      place_id: String(placeId || ""),
    };
  }

  function executeRequestLocation(action) {
    if (!global.navigator?.geolocation) {
      return { status: "not_available", action_type: action.type };
    }

    emit("prachinlife:request-location", {
      action_type: action.type,
    });

    global.navigator.geolocation.getCurrentPosition(
      (position) => {
        emit("prachinlife:location-ready", {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
      },
      (error) => {
        emit("prachinlife:location-error", {
          code: error?.code ?? null,
        });
      },
      {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 300000,
      }
    );

    return { status: "requested", action_type: action.type };
  }

  function executeAskOneQuestion(action) {
    const question = String(action?.params?.question || "").trim();
    if (!question) {
      return { status: "invalid_action", action_type: action.type };
    }
    emit("prachinlife:ask-one-question", {
      action_type: action.type,
      question,
    });
    return {
      status: "dispatched",
      action_type: action.type,
      question,
    };
  }

  function execute(action, options) {
    const validation = validateAction(action);
    if (!validation.ok) {
      return {
        status: "rejected",
        action_type: action?.type || null,
        reason: validation.reason,
      };
    }

    if (needsConfirmation(action, options)) {
      return {
        status: "requires_user_confirmation",
        action_type: action.type,
      };
    }

    switch (action.type) {
      case "OPEN_PLACE_CARD":
        return executeOpenPlaceCard(action);
      case "SHOW_ALTERNATIVES":
        return executeShowAlternatives(action);
      case "COMPARE_PLACES":
        return executeComparePlaces(action);
      case "OPEN_MAP":
        return executeOpenMap(action);
      case "REQUEST_LOCATION":
        return executeRequestLocation(action);
      case "ASK_ONE_QUESTION":
        return executeAskOneQuestion(action);
      default:
        return {
          status: "rejected",
          action_type: action.type,
          reason: "action_not_allowlisted",
        };
    }
  }

  function executeAll(input, options) {
    const result = resultPayload(input);
    if (result.action_contract_version !== CONTRACT_VERSION) {
      return {
        ok: false,
        reason: "unsupported_action_contract_version",
        results: [],
      };
    }

    const actions = Array.isArray(result.actions) ? result.actions : [];
    return {
      ok: true,
      action_contract_version: CONTRACT_VERSION,
      results: actions.map((action) => execute(action, options)),
    };
  }

  global.PrachinLife = global.PrachinLife || {};
  global.PrachinLife.core = global.PrachinLife.core || {};
  global.PrachinLife.core.actionExecutorV1 = Object.freeze({
    contractVersion: CONTRACT_VERSION,
    allowedActionTypes: ALLOWED_ACTION_TYPES,
    validateAction,
    execute,
    executeAll,
  });
})(window);
