# Phase 4.7 — Direct / Operator Lifecycle Confirmation

Goal: provide an auditable human-confirmation path for lifecycle conflicts that web evidence cannot safely resolve.

The default packet intentionally contains NO fabricated confirmation.
Until an actual direct confirmation is supplied, the result is:
STILL_UNRESOLVED

Required provenance for a resolving confirmation:
- candidate name + province
- confirmer identity
- confirmer role
- method: phone / in_person / merchant / admin
- result: open / permanently_closed / unresolved
- timezone-aware confirmed_at
- contact/reference when resolving open/closed
- optional notes

A valid committed confirmation is written only to precanonical_direct_confirmations.
It does not mutate canonical lifecycle, create a canonical place, or publish anything.
