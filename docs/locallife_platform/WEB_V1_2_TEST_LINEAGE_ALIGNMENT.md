# PrachinLife Web V1.2 — Test Lineage Alignment

Status: TEST_ONLY_ALIGNMENT

Purpose: keep historical R2/R3/R5 requirements while allowing the current R6
implementation to supersede obsolete implementation-specific assertions.

Classification:

- R2 `--ai-vv-height` / `--ai-vv-top` assertions:
  VALID_REQUIREMENT_WRONG_ASSERTION.
  R6 preserves Android keyboard/VisualViewport behavior using direct
  `viewport.height` and `viewport.offsetTop` measurements plus resize/scroll
  listeners.

- R3 exact legacy asset version `12r3` assertions:
  SUPERSEDED_TEST.
  Cache busting remains required, while the current assets have advanced to
  CSS `12r5` and JS `12r6`.

- R3 VisualViewport CSS-variable assertions:
  VALID_REQUIREMENT_WRONG_ASSERTION.
  R6 uses direct VisualViewport measurements.

- R5 exact JS/title version assertions:
  SUPERSEDED_TEST.
  R6 body-portal is the successor to the R5 forced-layout implementation.

No PrachinLife runtime file, LocalLife runtime file, database, canonical data,
published data, or production root is changed by this alignment.
