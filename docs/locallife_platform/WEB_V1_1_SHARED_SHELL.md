# LocalLife Web V1.1 — Shared Regional Shell

Status target: `REGRESSION_NEUTRAL_VERIFIED` after installation on the audited branch.

## Scope

Web V1.1 adds a mobile-first, additive regional shell for the five routes declared by `locallife.regional-web/v1`:

- `/prachinburi/`
- `/prachinburi/search/`
- `/prachinburi/eat/`
- `/prachinburi/go/`
- `/prachinburi/services/`

The existing production root `/index.html` is not modified.

## Boundary

The shell obtains brand, navigation, route and capability context only from `GET /v1/regions/{region_slug}/context`. It does not embed place records, read the canonical database, or write domain data. Context mismatch or an unavailable API fails closed and displays no guessed regional data.

The shared JavaScript and CSS contain no named Prachinburi/PrachinLife business logic. The regional HTML wrapper carries only the region slug, active view, and regional-context endpoint needed to bootstrap the generic shell.

## Local preview

Run the LocalLife API and a static server separately, then open the static page with a loopback-only API override:

`http://127.0.0.1:8080/prachinburi/?apiBase=http://127.0.0.1:8000`

The `apiBase` override accepts only loopback or same-origin HTTP(S). Production uses the same-origin regional-context path by default.

## Not included

- no production `/` cutover
- no place/search read-model integration yet
- no canonical direct read
- no write API
- no placeholder place records

Next milestone after verification: Web V1.2 Published Read Model integration for actual place/search cards while keeping the same regional shell contract.
