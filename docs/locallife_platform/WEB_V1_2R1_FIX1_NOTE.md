# Web V1.2R.1 FIX1

Root cause:
The V1.2R legacy visual test still asserted that the regional preview JavaScript
must contain no POST request at all. That assertion became obsolete once the
approved PrachinLife AI assistant was intentionally restored.

The runtime itself is correct:
- GET is used for Regional Context.
- POST is allowed only to the LocalLife Decision API endpoint obtained from Regional Context.
- PUT/DELETE remain forbidden.
- Direct OpenAI/DeepSeek/provider calls remain forbidden.

This FIX1 updates only the stale test contract and re-runs all targeted checks.
