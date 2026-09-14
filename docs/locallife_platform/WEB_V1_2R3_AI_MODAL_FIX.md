# Web V1.2R.3 — AI Modal / Composer Fix

Observed issue:
after the first AI turn, the chat could still render in normal page flow on some Android/browser viewport configurations, which pushed the composer below the visible area and forced page scrolling.

Fix:
- cache-bust the regional AI CSS/JS references;
- on touch/small-screen devices, add an explicit `ai-chat-modal` class when chat opens;
- the modal class overrides every older responsive rule and forces a fixed full-viewport chat;
- only the messages area scrolls;
- composer stays as the final non-scrolling flex item;
- VisualViewport continues to follow the Android keyboard.

Architecture unchanged:
- AI endpoint comes from Regional Context;
- POST is only to LocalLife Decision API;
- no direct provider calls;
- no automatic geolocation;
- production root and production cutover unchanged.
