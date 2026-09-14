# Web V1.2R.4 — Critical Mobile Composer Fix

Observed repeatedly on Android:
AI responses rendered, but the text composer remained outside the visible viewport,
so the user could not continue the conversation without awkward page scrolling.

This fix is deliberately minimal and deterministic:
- critical mobile chat layout is embedded directly in `/prachinburi/index.html`;
- while the AI panel is open on a touch/small-screen device, the panel is forced
  to a full-viewport fixed overlay;
- the composer is independently fixed to the viewport bottom;
- the message list reserves bottom space and scrolls internally;
- this no longer depends on external CSS cache order or a JS-added modal class.

Architecture and safety remain unchanged:
- AI still posts only to LocalLife Decision API;
- no provider API is called from the browser;
- no automatic geolocation;
- production root is untouched;
- production cutover remains FALSE.
