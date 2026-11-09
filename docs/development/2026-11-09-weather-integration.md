# Weather integration — browser and source evidence, 2026-11-09

Feature integration: [PR #463](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/463), issue #353.
This is focused development evidence, not a frozen application release or physical
TV acceptance record. No TV was contacted. Model, firmware/webOS, remote and TV
edition installation results: unknown/untested. Installer platform: macOS host;
no installer run in this task. Browser: Playwright Chromium, 1920×1080.

## Scope and observed results

- `npm run test:weather`: typed capability/schema/parts, opt-in data state,
  canonical units, malformed responses/cache, cancellation, stale/expiry/backoff,
  local restore, preset reservations and Inputs shelf passed.
- `source .venv-cytv/bin/activate && npm run test:themes`: complete existing theme
  unit suite passed, including receiver HTTP, transport/hash checks, startup,
  capability rejection, builtin regeneration, catalog, runtime/compile and media.
- `node scripts/check-theme-submissions.cjs`: 13 reviewed records validated;
  eight active catalog themes. Old entries and immutable package bytes retained.
- `node scripts/check-tv-web.cjs`: all four frontend compatibility profiles passed.
- `npm run test:weather:browser`: both editions' real settings/navigation paths
  passed. The preview build was transformed by the packaged TV web compiler before
  testing. Off issued no provider requests; Berlin search/selection and canonical
  metric/imperial controls worked. Forecast showed four rows. Weather hid after
  one Down while the header remained; Up restored it. Back returned city-dialog
  focus and Off hid subordinate settings/preview.
- Full matrix: 832 cases = eight catalog themes × four requested formats × 13
  languages × two editions. All passed supported-format fallback, weather
  visibility, header/hero/Inputs separation, on-screen bounds and row overflow.
  Screenshots cover Russian settings; additional full-screen visual inspection
  covers theme surfaces. Data was synthetic, no private inventory/location.
- Live production XHR smoke against Open-Meteo: manual Berlin search returned
  Germany, current data and four daily ranges, status ready. No API key or real
  user location was used. GeoJS auto behavior used controlled city/failure
  responses; live host egress sometimes has no city, handled as not determined.

## Findings and resolution

The full matrix found overflow in Korean Crăciun forecast temperatures. Canvas
text measurement selected different locale/font fallback than the rendered DOM.
The shared renderer now measures actual glyph ranges, preserving theme type and
TV text size. The Korean case and subsequent complete matrix passed. Malformed
network/cache values are sanitized and invalid preference batches do not partly
mutate the state. After comparison with other projects and the Open-Meteo maintainer guidance,
attribution lives in a Data sources dialog from the Weather heading. Widget
footers and the verbose Weather settings block remain absent.

## Theme provenance and author handoff

Own source weather commit: `5052717b1d436b385d01f067976c2362fb401c08`.
Liquid Glass 1.1.0 and Ribbon 1.4.0 compiled snapshots pin that source.
Alpine 1.6.0 and Crăciun 1.3.0 source pins
`f84ca319566743f3f4e777259ce1ba2e01470a34`; package commit `78ed8cd6`.
Build validation reports pin the complete clean candidate runtime inventory.

Temporary fork distribution branches are separate from upstream-compatible
source branches. Upstream authors were notified through focused PRs:

- [Minimal](https://github.com/invrnt/tv-themes/pull/1): all formats, monochrome.
- [Retro](https://github.com/xandymelo/clean-your-tv-lg-retro-theme/pull/1): all
  formats, square neon appearance.
- [Atmosphere](https://github.com/Luigy-Lemon/atmosphere-theme/pull/1): Ribbon
  suppression; the source builder also requires a weather-capable runtime.

Catalog replacement is in the feature branch. It has not shipped in stable Home.
Fork identity, original author, upstream repository and original asset/license
credits are explicit; no existing upstream installation is silently migrated.

## Outstanding release acceptance

Actual TV TLS/certificates/CORS for each provider; visual legibility from TV
viewing distance; native remote navigation, wake, standby, cold boot; live/offline
transition on a TV; final Home OTA/rollback and application candidate checks are
untested. Earlier theme device reports do not establish acceptance of the new
packages. Do not mark #353 released or announce application delivery on this
browser evidence. The author runtime and theme artifacts remain candidates until
normal release gates are completed.

## Final source review and edge cases

Independent read-only review confirmed a one-column channel-list overlap: the
app focus handler overwrote the renderer's weather offset. The shared focus path
now derives its title position from the measured weather reservation; competing
renderer writes are removed. A browser regression covers Down/Up focus updates
and resetting the layout. Expiration now emits immediately even during offline
retry backoff, so data older than the cap cannot remain painted. The new unit
regression failed before this fix and passed after. A proposed stale/status
footer was rejected against the user's later explicit removal of that block.
Sources dialog mounting uses the supplied settings card before Root inserts it
into the document. Both editions test links, Escape/Back focus and no widget
footer; the locale matrix checks heading/dialog bounds.

Fork candidate artifacts are published as explicit prereleases, not app releases:
[Minimal](https://github.com/Razdva122/tv-themes/releases/tag/weather-v1.1.0-candidate.1),
[Retro](https://github.com/Razdva122/clean-your-tv-lg-retro-theme/releases/tag/weather-v1.1.0-candidate.1),
[Atmosphere](https://github.com/Razdva122/atmosphere-theme/releases/tag/weather-v1.1.0-candidate.1).

## Paired author toolkit

[Author tools PR #9](https://github.com/Razdva122/clean-your-tv-lg-theme/pull/9)
contains the contract guards, updated examples/docs and synthetic preview controls.
Its lock pins clean main source `afc8586955802270167daed6cd3a445fc31ff364`;
all 71 tests passed against that complete compiled export in both browser editions,
with zero outgoing weather/geolocation provider requests. The local reviewed
export is retained in the author checkout's ignored `.runtime/weather-candidate`;
CI recreates the complete export from the exact lock, never a floating branch.
The runtime remains candidate. Main and toolkit PRs are ready for review; remote
CI was still running at handoff, with no failure observed at that check.

Published fork archive SHA-256 values (also attached to their prereleases):

- Minimal: `68637d10548c6d22af35e5bee5510e29b18f99411ddedf44e3088391ee00e03a`
- Retro: `43e0c93a807d2523f49b43a0089378e69c07421aab9e34057f422675f3c46a61`
- Atmosphere: `6c41027938ce00d11540e0ed9972f9022d6ebe90328bd7412b1ac498bc1c9526`

A further focused regression runs `WEATHER_LANGS=ko WEATHER_WIDTH=1280
WEATHER_SCALE=0.85 node tests/weather/matrix.cjs` (64 cases, both editions).
Rendered glyph measurement now removes the combined theme/viewport transform
scale before assigning logical CSS widths. The regression failed before the fix
and passed after it; the normal both-edition UI regression and compatibility
profiles also passed. These are developer/theme sizing controls, not user settings.
