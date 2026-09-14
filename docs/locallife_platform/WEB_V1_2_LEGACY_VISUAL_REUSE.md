# Web V1.2R — PrachinLife Legacy Visual Reuse

Decision: PrachinLife's already-approved visual/UX direction remains the regional presentation reference.

This checkpoint does **not** redesign PrachinLife from scratch. It reuses the existing production visual system (`style.css` and approved brand/category assets) in the additive `/prachinburi/` preview route while keeping the LocalLife regional contract/API boundary underneath it.

## Boundaries

- Production root `index.html` remains untouched.
- Generic LocalLife Web V1.1.2 shell assets remain generic.
- PrachinLife-specific presentation lives in `regional_products/prachinburi/web/`.
- The preview reads only Regional Context with GET.
- No direct Canonical/Published writes.
- No embedded place/index data.
- Near Me does not request geolocation in this visual checkpoint.
- Production cutover remains FALSE.

## Next

After mobile visual acceptance, connect the approved presentation to Published Read Model through the regional/product boundary rather than restoring legacy direct-data coupling.
