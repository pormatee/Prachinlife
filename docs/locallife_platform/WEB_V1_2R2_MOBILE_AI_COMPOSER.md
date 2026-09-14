# Web V1.2R.2 — Mobile AI Composer UX

Problem observed on Android:
the AI chat panel could occupy normal page flow / exceed the visible browser viewport,
forcing the user to scroll the page before reaching the text composer.

Fix:
- Treat AI chat as a true mobile overlay up to 900px viewport width.
- Keep header and composer outside the scrolling message area.
- Scroll only messages.
- Use VisualViewport resize/scroll events so Android's on-screen keyboard cannot push
  the composer below the visible area.
- Lock background page scrolling while AI chat is open.
- Preserve safe-area padding.
- Keep the LocalLife Decision API / Regional Context architecture unchanged.

Safety:
- No direct provider API calls.
- No automatic geolocation.
- Production root remains unchanged.
- Production cutover remains FALSE.
