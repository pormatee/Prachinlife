(function (global) {
  "use strict";
  const P = global.PrachinLife = global.PrachinLife || {};
  P.core = P.core || {};
  const KEY = "prachinlife_usage_v1";
  const allowed = new Set(["category_view","search","near_me","decision_view","decision_select","place_detail","map_action","decision_feedback_helpful","decision_feedback_not_helpful"]);
  function enabled() { return String(global.navigator?.doNotTrack || "") !== "1"; }
  function read() {
    try { return JSON.parse(global.sessionStorage.getItem(KEY) || "{}"); } catch (_) { return {}; }
  }
  function write(value) { try { global.sessionStorage.setItem(KEY, JSON.stringify(value)); } catch (_) {} }
  function track(name) {
    if (!enabled() || !allowed.has(name)) return false;
    const data = read(); data[name] = (Number(data[name]) || 0) + 1; write(data); return true;
  }
  function summary() { return Object.freeze({...read()}); }
  P.core.usageAnalytics = Object.freeze({track, summary, enabled});
})(window);
