# Web V1.2R.6 — AI Body Portal

R5 was confirmed to be present both on disk and in the HTTP response. The AI JavaScript
was therefore not stale. Yet the panel still rendered like a normal-flow element.

The remaining structural risk was that the chat panel lived inside the legacy Hero
section. Legacy ancestors can create positioning/containing-block behavior that defeats
a fixed overlay on mobile browsers.

R6 removes that dependency:
- when AI opens, the existing chat panel DOM node is temporarily moved directly under
  `<body>`;
- the existing fixed full-viewport inline layout is then applied;
- when AI closes, the same node is restored to its original DOM location;
- no duplicate chat DOM is created and conversation state is preserved.

Architecture remains unchanged:
- Decision endpoint comes from Regional Context;
- browser POSTs only to LocalLife Decision API;
- no direct model-provider calls;
- no automatic geolocation;
- production root untouched;
- production cutover FALSE.
