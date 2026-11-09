# Maintainer-approved weather provider integration

The maintainer requested maximum candidate QA, completion of planned cases before
batch fixes, multiple weather APIs with manual selection plus Auto, and specifically
approved trying MET Norway through the trusted service. A full replacement RC must
wait until real API operation has been checked on the TV. This scope follows the
completed case/failure inventory in `docs/history/2026-11-09-release-1.15.0-qa.md`.

## Observed baseline

Open-Meteo forecast TCP connectivity fails on the direct TV/Mac route and succeeds
through the host tunnel. Geocoding and GeoJS work on the C3. This is not proof of an
official nationwide Russian ban. MET Norway's compact endpoint returns HTTP200 on
native C3 HTTPS with a truthful identifying User-Agent and normal certificate
validation; the browser cannot set that header. That is transport feasibility,
not installed integration acceptance. 7Timer works from the browser but has coarser
fields; wttr.in times out. The initial implementation selects MET Norway and
Open-Meteo, not untested sources or public proxies.

## Product contract

- Provider IDs: `auto`, `met-no`, `open-meteo`. Explicit manual selection never
  falls back. Auto starts with MET Norway, then tries Open-Meteo once if transport,
  HTTP or normalized-data validation fails. Remember the last successful source
  for subsequent refresh/cache use; avoid repeatedly paying a known failure.
- Existing saved settings without a provider remain Open-Meteo. Fresh empty
  settings default to Auto. Weather remains off by default; Ribbon, Off, hidden
  state and destruction cancel work and must not start fallback requests.
- `WeatherData.create({metRequest})` accepts a native MET transport function:
  `metRequest(place) -> {promise, cancel}`, resolving the raw MET forecast object.
  Existing `env.request(url)` remains the XHR transport for geocoding, GeoJS and
  Open-Meteo. Keep generation/cancellation fencing across both transports.
- `WeatherData.normalizeMet(body, place, nowMs)` returns the existing Celsius/m/s
  canonical weather shape. Add `state().provider` (selection) and `state().source`
  (actual producer). Preserve supported optional timezone metadata on locations.
  Validate units, finite ranges, dates and freshness. Use real wind/humidity;
  keep missing apparent temperature and precipitation probability null rather
  than inventing them. Aggregate up to four local-calendar forecast days from
  timestamped points; document their forecast nature. Handle timezones/DST with
  available Intl and honest UTC fallback if unavailable.
- Cache records are bound to canonical location and actual source, with at most
  two same-location source entries. Preserve legacy single-cache loading only as
  Open-Meteo. Provider changes cancel pending work and cannot display another
  manually selected source's cache. MET refresh interval is at least three hours;
  Open-Meteo retains its existing interval; existing six-hour maximum cache age
  remains. Switching/reloading must reuse fresh source entries, not hammer MET.
  Persist one last MET attempt key/timestamp before transport, independent of
  successful cache data, to honor the interval after failure, cancellation,
  force, source changes and reload. Match native four-decimal request rounding;
  a genuinely different request location may replace that single record. Reuse
  fresh matching source cache during Auto fallback without extending its age.
  MET model metadata may be at most twelve hours old (two global six-hour model
  cycles, allowing one missed cycle); the current forecast point must remain
  within three hours. These validity bounds are independent of polling and
  display-cache expiry and do not promise upstream freshness.
- UI provides three labeled keyboard/remote-accessible choices and actual-source
  feedback, in the existing Weather settings. Preserve focus/Back and all13
  locales. Add source/terms attribution in Data sources; update practical guides
  without release/version/QA news in `docs/i18n/`.

## Trusted service contract

- Home LS2 service: `com.gathin.tvhome.renewal`; Root LS2 service:
  `com.cleanyourtv.root.preview.service`. Only the respective actual Home app
  caller is authorized (follow existing LS2 identity checks).
- `weatherForecast` takes exactly `{id,latitude,longitude}`. ID matches
  `^[a-zA-Z0-9-]{1,64}$`; coordinates are finite numbers within WGS84 bounds.
  `weatherForecastCancel` takes exactly `{id}`. Reject extra fields and all
  caller-supplied URLs, hosts, headers, files and commands.
- Fetch only `https://api.met.no/weatherapi/locationforecast/2.0/compact`, with
  coordinates rounded to at most four decimal places and a truthful project
  User-Agent containing its public repository contact. Use existing Mozilla CA
  material, hostname/certificate verification, no redirects or credentials.
- Deadline 12 seconds, JSON body limit 256KiB, no more than two pending requests.
  Hold/release a webos-service activity for pending work; release on every exit.
  Explicit cancellation destroys HTTP work, suppresses late effects and handles
  cancellation arriving before its forecast call. Memory is bounded. No network
  on module load and no backend location/history persistence or raw logging.
- Success: `{returnValue:true,forecast:object}`. Failure: fixed safe errorCode,
  never raw provider errors/URLs/body. Client `HomeWeatherTransport.met(place)`
  exposes the metRequest interface above, selects the correct service at call
  time, rejects unavailable bridges promptly, and performs explicit cancellation.
- The shared implementation lives in `renewal-service/weather.js` (the Home
  service, not Home Helper). Root bundles that closure and its existing CA/license
  material into the already owned `service.js`, following existing immutable
  inventory bundling. Do not expand retained System/private service inventory.
  Helper0.8.0 stays exact published bytes; retained System1.2.5 is not replaced.

## Verification and release boundary

Use TDD on fixed-host transport/caller limits/cancel/timeout, canonical provider
normalization and Auto/cache/race behavior. Run generated code on current and exact
Node0.10.15/0.10.25/0.12.2. Test both compiled UI editions, all13 locales, existing
832-case matrix and package closures. Fix the completed PR CI floating-point
budget fixture without changing the production boot deadline. Independent review
covers spec and quality before integration. Keep public evidence redacted.

Use a supported scoped/preliminary Root route if new service delivery is needed
before a full RC; never force equal-version installation or change trust/receipts.
Preserve recovery and actual profile/Home Off. Preliminary transport/UI evidence
is not final full-candidate acceptance. After real API operation and all correction
inputs pass, integrate the batch, refresh inventory/versions/docs, clear the old
product-incompatible pin and dispatch one complete replacement candidate. Retest
actual selected artifacts; stable publication is outside the current task.
