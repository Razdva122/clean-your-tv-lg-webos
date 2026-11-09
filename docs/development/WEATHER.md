# Home weather and themes

Home owns location choice, networking, persistence, rendering, placement and remote
navigation. A theme only declares supported formats and styles approved parts.
The weather integration is prepared in a feature branch; publication of the Home
application follows the normal release candidate workflow.

## Format contract

| ID | User label | Content |
| --- | --- | --- |
| `text` | Compact | Icon, temperature, condition, daily high/low |
| `current` | Now | City, temperature, feels like when available, condition, daily high/low |
| `details` | In detail | Now plus available wind, precipitation probability, humidity |
| `forecast` | 4 days | Now plus today and the next three daily low/high ranges |

```json
"weather": {
  "formats": ["text", "current", "details", "forecast"],
  "scale": 1,
  "padding": 28,
  "icons": "fill"
}
```

Declare this inside `layout`. The compiler pairs it with `requires.capabilities`
containing `weather-v1`. Weather selectors automatically add the declaration and
capability when absent. Scale is 0.85–1.25; padding is an integer 0–32; icons are
bundled `fill` or `monochrome`. Defaults are all formats, scale 1, padding 24 and
fill icons. These are developer controls, never user settings. No custom offsets,
network sources, arbitrary icons or JavaScript are accepted.

Approved parts: `.ctv-weather`, `.ctv-weather-temp`, `.ctv-weather-secondary`,
`.ctv-weather-condition`, `.ctv-weather-bar`, `.ctv-weather-track`,
`.ctv-weather-day`, `.ctv-weather-icon`. Existing typed property restrictions
apply. Use color, font, background, edges and shadows to match the theme. Home
inherits the accepted Home/clock typography and colors first; explicit weather
rules override those defaults. Monochrome icons inherit currentColor. Position,
width, wrapping, forecast content and focus remain Home-owned. Compact always
has a transparent surface without border or shadow.

| Catalog composition | Formats | Treatment |
| --- | --- | --- |
| Classic | All four | Transparent, inherited header appearance |
| Liquid Glass | Compact | White glass-header typography, fill icons |
| Alpine | All four | Slate surface, cream type, restrained edges |
| Minimal | All four | Transparent monochrome, straight bars |
| Retro | All four | Square neon surface, yellow icons, offset pink shadow |
| Crăciun la Brașov | All four | Walnut, cream serif, gold edges |
| Ribbon, Atmosphere | None | Explicit empty formats, no requests |

Every `layout.ribbon` composition suppresses weather even if a manifest lists
formats. Legacy non-Ribbon packages remain valid with all four formats and
inherited transparent appearance. Unsupported preferences are preserved: Home
uses Compact or the first available format and restores the preferred format on
a compatible theme. Input shelf and app grids reserve measured weather space;
weather disappears on scroll before the header. Themes do not implement these
behaviors themselves.

## Data and settings

Settings → Weather follows Wallpapers. Off by default; Off cancels requests and hides city, units and format controls;
source selection remains available. Manual city search uses Open-Meteo geocoding;
Automatic city selection explicitly opts into approximate GeoJS IP lookup. A VPN
can change that result; missing city names are not invented. Manual search is the fallback.
Only the selected city/region/country/coordinates and lookup time are retained.
Fixed HTTPS endpoints are owned by Home, never a theme. XHR timeout is 12 seconds;
responses are bounded to 1 MiB and fields are validated. No provider key is shipped.

Forecast data stays in °C and m/s in storage. Metric/imperial presentation converts
without refetching. Open-Meteo refreshes after 15 minutes; MET Norway refreshes
no more often than every three hours. One last-attempt timestamp for the current
MET request location preserves this bound after failures, cancellation, source
changes and reload. Fresh source cache is reused during fallback. Source caches
are retained at most six hours; the general five-minute failure backoff cannot
override MET admission. Auto city refresh is at most daily.
Language changes localize condition codes, weekdays and supported city names.
Cancellation fences prevent old city/theme/enable responses from being applied.
Missing optional values are omitted. Preview without real data says Example;
examples never appear on Home. Data attribution and license links are in the clearly labeled Data sources dialog
in the Weather settings heading, and THIRD_PARTY_NOTICES.md. The Home widget has
no provider footer.

Forecast provider choices are exactly **Auto**, **MET Norway** and **Open-Meteo**
(`auto`, `met-no`, `open-meteo`). Empty settings default to Auto; existing saved
settings without a provider retain Open-Meteo. Auto starts with MET, tries
Open-Meteo once on failure, and remembers the last successful source. Manual
selection never falls back. Cache entries are tied to location and actual source;
a manual choice cannot display another source's cached forecast. Settings show
the actual source. MET has no apparent temperature or precipitation probability;
these remain absent. Daily ranges summarize forecast points for up to four local
calendar days, not observed daily extremes. Where Intl timezone support is
unavailable, grouping falls back to UTC.

MET transport uses the existing Home renewal service (`com.gathin.tvhome.renewal`)
or the Root private service (`com.cleanyourtv.root.preview.service`), never native
Home Helper. Only the corresponding Home caller may request it. It uses verified
TLS and a truthful project/contact User-Agent to the fixed endpoint
`https://api.met.no/weatherapi/locationforecast/2.0/compact`; coordinates are rounded
to at most four decimal places. Requests have a 12-second deadline and a 256 KiB
JSON limit. No API keys, proxy, caller-selected URL or backend location history
are introduced. XHR remains responsible for Open-Meteo and location lookup.

Privacy endpoints are `api.met.no` and `api.open-meteo.com` for forecast
coordinates, `geocoding-api.open-meteo.com` for city searches, and `get.geojs.io`
for explicitly requested approximate IP location. All use HTTPS. Local source
selection and cached forecasts stay with Home preferences. Credit MET data to
the Norwegian Meteorological Institute under CC BY 4.0, alongside Open-Meteo,
GeoNames and GeoJS credits and provider terms in Data sources and
THIRD_PARTY_NOTICES.md. Network unavailability does not establish a nationwide
ban; users can select another source without changing location mode.

`tvhome.weather.v1` is app-origin localStorage, like other appearance preferences.
It survives ordinary OTA updates. Existing legacy profile export/import does not
include weather or location; it neither transfers nor silently enables weather on
another device. Switching Off retains the selected city for a later return.

## Publishing and verification

Old Home rejects the new capability safely; it cannot gain weather by installing a
theme alone. Keep old packages immutable. Build new source commits with the matched
main-project compiler/runtime and publish a new theme version. Candidate runtime
status and browser coverage do not imply a stable Home release or TV acceptance.

Temporary maintainer forks use their own repository identity and commit-pinned
package URLs, retain original author/license/asset credits, and record the
`upstreamRepository` in the reviewed registry. Original entries remain as removed
history. Existing upstream installs are retained; this is not forced migration.
Authors receive an upstream-compatible source PR with the original theme ID.
When their compatible package is published, a reviewed catalog update can restore
the upstream URL. Do not rename old installed IDs or overwrite their packages.

Run `npm run test:weather`, the affected theme/showcase checks, compatibility build
and browser format/locale matrix. Physical TV TLS/CORS, readability at viewing
distance, remote behavior, wake/cold boot and offline recovery remain separate
release acceptance cases; browser rendering establishes none of them.
