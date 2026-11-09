# Weather integration implementation plan

> Execute sequentially in the maintained checkout. Preserve unrelated edits. Do not delegate or publish an application release from this feature task.

**Goal:** Integrate the approved weather experience in both Home editions, extend the typed theme contract, prepare weather-aware theme updates and update the author toolkit.

**Spec:** `docs/superpowers/specs/2026-11-09-weather-formats-design.md`

**Architecture:** One trusted Home weather store, renderer and settings category. Typed `layout.weather` controls supported formats, scale, padding and bundled icon style; existing typed CSS properties style approved weather parts. Presets own measured reservations and separate header/weather occlusion. Existing theme packages remain valid. New packages opt into `weather-v1`, which older Home rejects safely.

**Constraints:** Chromium 38 / existing webOS 2 prefix profile; no fetch, AbortController, ResizeObserver, CSS grid/custom-property or new Intl API dependency. XHR with deadlines and generation cancellation. Weather is off by default; external requests only after opt-in and a selected city/Auto. No author code, remote icons or arbitrary positioning. Keep immutable published packages intact. Root and No-root share source. No physical-TV acceptance may be inferred from browser checks.

## 1. Contract and layout
- [x] Add red policy/compiler tests for `weather-v1`, strict weather schema, safe CSS parts and legacy compatibility.
- [x] Extend `launcher/theme-policy.js`, `theme-api/compile.cjs`, `theme-api/contract.json` and runtime capability admission.
- [x] Add shared weather geometry/reservations without replacing `HomeLayout.geometry` at runtime; test presets, Inputs shelf and independent visibility.

## 2. Data and settings
- [x] Add `launcher/weather-data.js`: injectable XHR, persistence, canonical units, explicit manual/Auto, localized search, cancellation, freshness/stale/backoff and bounded response validation.
- [x] Verify no calls when disabled, before location selection or under Ribbon; test race/error/cache/missing-value scenarios.
- [x] Add `launcher/weather.js`, `weather.css`, `weather-locales.js` and licensed bundled icons. Use built-in date/number formatting with legacy fallbacks.
- [x] Implement the approved two-column settings and separate city dialog through the shared SettingsCategories contract, with remote focus and Off hiding.
- [x] Wire Root/No-root HTML, preview/package allowlists, profiles/settings cleanup and attribution.

## 3. Verification and documentation
- [x] Run the compatibility compiler, focused theme/store/geometry tests, browser coverage for both editions, all eight themes and 13 locales, offline/cache and real public-city API smoke checks.
- [x] Update theme API/author documentation and all localized practical guides without release banners or developer details in user guides.
- [x] Record browser evidence and explicitly outstanding TV TLS/CORS, remote and readability acceptance.

## 4. Theme and author-tool updates
- [x] Update source-owned Alpine, Craciun, Liquid Glass and Ribbon declarations/styles; build new versioned packages from committed source, preserving old distributions.
- [x] Prepare focused upstream updates for third-party Minimal, Retro and Atmosphere rather than rewriting their signed historical packages or claiming ownership.
- [x] Update the local `clean-your-tv-lg-theme` author repository: contract docs, examples, new-weather preview controls, tests and exact candidate runtime provenance.
- [x] Export a matching candidate runtime only after main-source commit; keep candidate status until normal release gates are met.
- [x] Create reviewable PRs targeting the correct integration branches, link #353, verify CI and reconcile issue labels. Publish theme artifacts only against compatible Home/runtime evidence; report any ownership/release dependency explicitly.

Sources attribution placement was subsequently approved in the Weather heading; see the production refinement in the spec. Legacy profiles deliberately do not export/enable weather or transfer location. Final TV acceptance remains with the application release coordinator.

Main PR: #463. Paired author-tools PR: Razdva122/clean-your-tv-lg-theme#9, pinned to clean runtime source afc8586955802270167daed6cd3a445fc31ff364. Local source/browser/toolkit and remote package-hash checks passed; remote CI was still running at handoff. Public application delivery and physical acceptance are deliberately outside this feature branch.
