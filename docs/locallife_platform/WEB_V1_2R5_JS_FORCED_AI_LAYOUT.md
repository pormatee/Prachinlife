# Web V1.2R.5 — JS-forced Mobile AI Layout

R4 was confirmed to be both present on disk and served by the local web server, yet
the Android browser still rendered the chat in normal document flow.

Therefore R5 stops relying on CSS matching for the critical layout.

When the AI panel opens on a touch/small-screen device, JavaScript applies inline
`!important` styles directly to:
- the chat panel (fixed full viewport);
- the messages area (internal scrolling);
- the composer (non-scrolling final flex item);
- the textarea and Send button.

VisualViewport height/offset is used so the panel follows the visible browser area
when the Android keyboard opens.

Architecture remains unchanged:
- Regional Context supplies the Decision endpoint;
- browser POSTs only to LocalLife Decision API;
- no direct provider calls;
- no automatic geolocation;
- production root untouched;
- production cutover FALSE.
