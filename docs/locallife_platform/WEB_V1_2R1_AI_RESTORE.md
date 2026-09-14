# Web V1.2R.1 — PrachinLife AI Assistant Restore

This checkpoint restores the approved PrachinLife AI assistant UI that was omitted
from the first legacy-visual reuse preview.

## Architecture

- UI remains PrachinLife regional presentation.
- Decision endpoint is obtained from Regional Context (`ctx.endpoints.decision`).
- Browser never calls OpenAI/DeepSeek/provider APIs directly.
- Conversation state is returned by LocalLife Decision API and passed back on later turns.
- No direct Canonical/Published write.
- No embedded place index files.
- If context or Decision API is unavailable, the assistant fails closed and explicitly avoids guessing.
- Near Me still does not auto-request geolocation in this checkpoint.
- Production root is unchanged; production cutover remains FALSE.
