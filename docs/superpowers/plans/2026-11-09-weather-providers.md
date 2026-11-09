# Weather Providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make weather work through MET Norway with manual provider selection and bounded Auto fallback before rebuilding the release candidate.

**Architecture:** A fixed-host MET client is shared by the existing Home and Root services. The data store normalizes provider responses and binds two bounded source caches to one location; the existing Weather panel selects the provider and shows the actual source.

**Tech Stack:** Existing ES5-compatible JavaScript, Node HTTPS/LS2, PalmServiceBridge, Python package builders, Playwright, core-js/Babel. No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-09-weather-providers-design.md`.

## Global Constraints

- Provider IDs: `auto`, `met-no`, `open-meteo`.
- Existing saved settings without a provider remain Open-Meteo; fresh empty settings default to Auto; weather stays off by default.
- Deadline12 seconds, body256KiB, at most2 pending service requests, no arbitrary URLs/headers and no raw logs/location history.
- MET refresh interval at least3 hours; cache expires after6 hours. At most2 source entries for the current location.
- Helper0.8.0 remains exact published bytes; retained System/private inventory and Home Off are preserved.
- User explicitly requires API correction/real-TV verification before a full replacement RC; stable publication is outside scope.
- Subagents inherit the main model/reasoning. Do not override models, spawn nested workers, change branches or touch original untracked files.

### Task 1: Trusted MET service transport and immutable packaging

**Files:** Create `renewal-service/weather.js`, `root-edition/service/weather.js`, `tests/weather/service.cjs`; modify `renewal-service/service.js`, `root-edition/service/service.js`, `root-edition/build.py`, `root-edition/runtime/cli.py`, `root-edition/install_device.py`, `root-edition/service/package.json`, `theme-receiver/register.js`, `package.json` and narrowly required package tests.

**Interfaces:** Register `weatherForecast({id,latitude,longitude})` and `weatherForecastCancel({id})`; success is `{returnValue:true,forecast:object}`. Root wrapper points at the shared Home implementation for source use; builder inlines it with existing CA/license into `service.js`. Export the existing theme-receiver `activityHold` helper for reuse, without changing its behavior.

- [x] Write real transport/registration tests with injected HTTPS EventEmitter fixtures: unauthorized caller and extra fields do not open a socket; exact host/path/verified CA/User-Agent; two-request cap; timeout/body/error/invalid JSON; cancel before/after start and late callbacks; hold released on every terminal path.
  ```js
  assert.equal(options.hostname, 'api.met.no');
  assert.equal(options.rejectUnauthorized, true);
  assert.match(options.headers['User-Agent'], /CleanYourTV.*github\.com/);
  assert.equal(response.returnValue, true);
  ```
- [x] Run `node tests/weather/service.cjs` and capture a meaningful red result before writing implementation.
- [x] Implement the fixed endpoint only. Validate all payload fields before starting HTTP. Return a cancelable operation internally and keep bounded pending/cancellation records; register both caller-bound methods. Reuse activityHold; no network starts at import.
  ```js
  service.register('weatherForecast', function (message) {
    // Authenticate actual LS2 applicationID; validate id/coordinates/keys;
    // hold activity; start only the fixed verified-TLS MET operation;
    // respond once and release on success/error/cancel.
  });
  ```
- [x] Inline Root closure/CA/license before legacy compilation, preserving exact private inventory. Add Home registration and its test command to `test:weather`; verify both real package closures.
- [x] Run current/generated exact Node0.10.15/0.10.25/0.12.2 transport cases and affected Root/package tests, format owned JS, commit only this task's files. Report commands/red/green evidence and commit range to this plan's task report.

### Task 2: Provider normalization, bounded Auto and source caches

**Files:** Modify `launcher/weather-data.js`; create `tests/weather/providers.cjs`; modify `tests/weather/data.cjs`, `package.json` only if the new command needs wiring.

**Interfaces:** `WeatherData.create({metRequest})`, where `metRequest(place)` returns `{promise,cancel}` resolving raw MET compact JSON. Existing request(url) is unchanged. Export `normalizeMet(body,place,nowMs)`. State exposes provider selection and actual source using the exact IDs above.

- [x] Add failing tests for actual MET-shaped timestamped data with Celsius/m/s/percent units, supported symbols and missing optional metrics; invalid/stale/unit/range data; local calendar/DST/UTC fallback. Use a fixed test clock and real parser behavior.
  ```js
  const value = Weather.normalizeMet(body, place, nowMs);
  assert.equal(value.wind, 1.4);
  assert.equal(value.feels, null);
  assert.equal(value.precip, null);
  ```
- [x] Add failing lifecycle tests: fresh/legacy defaults; manual never falls back; Auto MET first then one Open-Meteo attempt on failure; last-good source/cache reuse; source-switch cancellation; Off/Ribbon/destroy cancel without fallback; obsolete completions ignored; malformed responses follow same fallback; two-entry/one-location cache bound and legacy migration.
- [x] Run `node tests/weather/providers.cjs` and retain meaningful red evidence.
- [x] Implement the smallest source adapter/selection/cache changes in the existing store. Preserve geocoding/GeoJS independence, generation fences, original canonical units and6-hour expiry. Preserve optional IANA timezone from geocoding/GeoJS. Derive daily ranges only from real timestamped forecasts; never synthesize missing feels/probability.
- [x] Run providers/data/contract/layout tests, format owned JS, commit only these files. Record source compatibility and all test evidence in the report.

### Task 3: Native browser bridge and provider settings

**Files:** Create `launcher/weather-transport.js`; modify `launcher/index.html`, `scripts/home_assets.py`, `launcher/weather.js`, `launcher/weather.css`, `launcher/weather-locales.js`, `tests/weather/ui.cjs`, `tests/weather/matrix.cjs` as needed; add a focused transport test if needed and wire it into `test:weather`.

**Interfaces:** `HomeWeatherTransport.met(place)` implements the Task2 metRequest contract, using Task1 LS2 methods. Choose Root versus Home service at call time. Existing weather store is created with that function; brand IDs match Task2 exactly.

- [x] Add failing bridge tests for unavailable PalmServiceBridge, both service URIs, JSON validation, deadline, explicit cancel and late callbacks; no request while Off.
- [x] Add failing compiled UI cases with a test LS2 fixture resolving MET data: manual/Auto choices, actual source, no silent manual fallback, remote focus/Back, source attribution and Compact preview containment.
- [x] Implement deadline-bound bridge with unique bounded request ID; cancel original call and send weatherForecastCancel for the same ID. Do not override browser User-Agent or expose arbitrary request parameters.
- [x] Add labeled source choices/actual-source feedback to current Weather layout, adapting existing remote navigation and all13 translations. Add MET terms/license attribution. Preserve current panel hierarchy, typography and unsupported-theme behavior; use ui-ux-pro-max for targeted focus/layout QA.
- [x] Run compiled UI both editions, all832 theme/locale cases plus source/HD bounds cases, formatting and package resource checks; commit owned files and report evidence. No full candidate dispatch.

### Task 4: Completed PR verification failure and practical documentation

**Files:** Modify `root-edition/tests/test_boot_continuation.py`, `docs/THEMES.md`, relevant source/developer references, all affected practical `docs/i18n/` guides and canonical QA record.

- [x] Reproduce completed CI42632520469's floating-point `10.000000000000014 <= 10` failure with a controlled starting monotonic value; finish/record its whole14-job inventory before correcting it. Change only the fixture to an exact fixed clock origin, preserving budget/deadline assertions and all production code.
- [x] Run the affected boot continuation suite and controlled model green; no production budget/deadline change.
- [x] Document provider selection, Auto/caches/availability, accurate field limitations, privacy endpoints and proper credit. Localized guides contain no project release/component versions, RC banners or QA news; retain anchors. Do not state a nationwide Russian ban without authoritative evidence.
- [x] Complete formatting/metadata/whitespace checks and commit only task files. Record the completed correction batch and limitations in QA.

### Task 5: Coordinator validation and next candidate

**Files:** Canonical release QA, release-plan/README metadata, release PR generated/human record.

- [ ] Read fresh reviews/comments, perform independent spec/quality task reviews and one whole-branch review; resolve findings in their implementing task before integration. Run affected PR CI on the final batch.
- [ ] Verify exact package inventory, published Helper byte identity, all runtime closures and actual source/header/CA behavior. Obtain scoped signed preliminary Root delivery if required for the new service, using documented workflows only. Original rollback/profile/Off protections remain mandatory.
- [ ] Demonstrate MET manual and Auto real forecast/rendering from the selected C3, source-switch/cache/cancellation and restored preferences. Mark physical/native-offline and other-device scope honestly; no preliminary result substitutes for final acceptance.
- [ ] After successful API correction, merge focused PR into release/next, reconcile issue353 status and frozen inventory, clear the old product-incompatible pin, finish all version/docs/approval inputs and dispatch exactly one full replacement candidate.
- [ ] Pin actual successful full run, independently verify/sign exact artifacts, perform affected actual-artifact acceptance, update compact release PR/evidence and verify all seven issue labels. Keep draft/stable-publication limits explicit and clean only task-owned temporary resources.
