(function (global) {
  "use strict";

  const API_BASE = "https://locallife-api.onrender.com";
  const DEFAULT_TIMEOUT_MS = 20000;

  function timeoutSignal(timeoutMs) {
    if (typeof AbortController === "undefined") {
      return { signal: undefined, cancel: function () {} };
    }
    const controller = new AbortController();
    const timer = setTimeout(function () { controller.abort(); }, timeoutMs);
    return {
      signal: controller.signal,
      cancel: function () { clearTimeout(timer); }
    };
  }

  async function requestJson(path, options) {
    const cfg = options || {};
    const timeoutMs = Number.isFinite(cfg.timeoutMs) ? cfg.timeoutMs : DEFAULT_TIMEOUT_MS;
    const t = timeoutSignal(timeoutMs);

    try {
      const response = await fetch(API_BASE + path, {
        method: cfg.method || "GET",
        headers: cfg.headers || {},
        body: cfg.body,
        signal: t.signal
      });

      let payload = null;
      try {
        payload = await response.json();
      } catch (_) {
        payload = null;
      }

      if (!response.ok) {
        const error = new Error(
          (payload && payload.error) || ("LocalLife API HTTP " + response.status)
        );
        error.status = response.status;
        error.payload = payload;
        throw error;
      }

      return payload;
    } finally {
      t.cancel();
    }
  }

  async function health(options) {
    return requestJson("/v1/health", {
      method: "GET",
      timeoutMs: options && options.timeoutMs
    });
  }

  async function decision(input, options) {
    if (!input || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("LocalLife decision input must be an object");
    }

    return requestJson("/v1/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      timeoutMs: options && options.timeoutMs
    });
  }

  global.PrachinLife = global.PrachinLife || {};
  global.PrachinLife.core = global.PrachinLife.core || {};
  global.PrachinLife.core.localLifeApiV1 = Object.freeze({
    apiBase: API_BASE,
    health: health,
    decision: decision
  });
})(window);
