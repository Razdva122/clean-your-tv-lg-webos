# Weather formats and theme integration

Date: 2026-11-09

Status: agreed product direction; not implemented or accepted on a TV.
Related request: https://github.com/Razdva122/clean-your-tv-lg-webos/issues/353

## Scope

One Home-owned weather component has four fixed formats. Themes declare supported
formats and bounded appearance settings; they do not supply weather JavaScript,
HTML, network endpoints, or independent rendering implementations. Root and
No-root share the component. The latest user decision supersedes the earlier
proposal to restrict most presets to a short format.

This document records the format and composition contract. It does not authorize
implementation, a release, or publication of another user's installation report.

## Formats

| Identifier | Settings label | Content |
| --- | --- | --- |
| `text` | Text | Inline icon, current temperature, condition, and today's high/low. No background container by default. Matches the latest Liquid Glass direction. |
| `current` | Current | City, current temperature, feels-like temperature, condition icon/text, and today's high/low. No wind, precipitation, humidity, or forecast. |
| `details` | Details | The complete `current` header plus wind, today's precipitation probability, and humidity. Matches the latest large Alpine direction. |
| `forecast` | Forecast | The complete `current` header plus today and the following three days, shown as rows with condition icons, low/high temperatures, and bars on a common temperature scale. |

`current`, `details`, and `forecast` share their header. `forecast` does not also
include the extra metrics from `details`. Missing optional provider values are
omitted rather than invented or displayed as zero. A missing forecast does not
produce misleading empty bars. The text format avoids repeating the city in the
Home header; its selected location remains visible in settings.

## Allowed combinations

| Composition or theme | Text | Current | Details | Forecast |
| --- | --- | --- | --- | --- |
| Any composition using `layout.ribbon` | No | No | No | No |
| Alpine without Ribbon mode | Yes | Yes | Yes | Yes |
| Liquid Glass | Yes | No | No | No |
| Classic | Yes | Yes | Yes | Yes |
| Other themes and presets, without Ribbon mode | Yes | Yes | Yes | Yes |

Ribbon is currently a mode within `scenic-grid`, not a separate preset. Its hard
prohibition overrides theme declarations, including a theme that displays a
clock. This also covers Atmosphere when it uses Ribbon mode.

Liquid Glass declares a text-only allowlist in its theme metadata. There must be
no runtime branch on its title or theme ID. Other non-Ribbon themes default to all
four formats and may explicitly declare a smaller allowlist. The Classic fallback
has the same explicit product policy as other supported non-Ribbon compositions.

The table is the intended support contract, not evidence that existing geometry
already accommodates every combination. In particular, large formats in
`dock-grid`, `icon-grid`, and `channel-list` still need shared layout design and
verification. Their implementation must allocate space, not shrink text until a
block happens to fit.

## Selection and theme changes

Weather remains opt-in. The user chooses the city, units, and preferred format.
Theme selection determines which format choices are available. Weather settings
have a dedicated tab with an enabled switch, a list of supported formats and a
preview of the selected format in the active theme. Unit choices are Celsius
with metres per second or Fahrenheit with miles per hour; they apply to current,
feels-like, all forecast temperatures and wind together.

All weather settings and displayed weather content follow the selected Home
language in all 13 supported locales. Translate condition codes and mock city
names rather than displaying provider text in a fixed language; format weekdays,
numbers and percentages for the locale. Required layout verification includes
long translated labels and Fahrenheit temperature widths.

Keep the preferred format separately from the effective format. If a new theme
does not support the preference, use `text` when available; otherwise use the
first supported format in the fixed order `current`, `details`, `forecast`.
An empty allowlist or Ribbon hides weather. Settings explain the restriction.
Switching back restores the user's preferred format without losing city, units,
or enabled state. The theme cannot enable networking on the user's behalf.

## Layout ownership

Each preset owns one weather region and the spacing of adjacent modules. Its
layout accounts for the effective format, declared scale, and enabled modules
such as the Inputs shelf. Reserving space can move neighbouring modules under a
shared preset rule; it must not require theme-specific renderer code.

Themes style and scale the shared weather content within that region. They do
not position individual forecast rows or hide required content to claim support
for a larger format. Weather refreshes never resize its region or move focus.
Theme/format changes can recalculate geometry through the normal layout path.

The latest full-screen mockups are composition studies, not a placement contract
for every preset. Their manually adjusted Liquid Glass shelf and Alpine weather
position must become shared layout behaviour before implementation is accepted.

## Independent scroll visibility

Weather and the clock/button header have separate occlusion thresholds. Hide
weather when scrolling applications approach its reserved region. Keep the
clock and buttons visible while their own region is clear; the height of a
Forecast or Details block must not make the entire header disappear early.
Restore each region independently when scrolling back. Layout measurements
must not include the header's animated hide/show transform.

## Theme appearance controls

These are developer parameters in theme metadata, not end-user settings. Users
choose weather location, units and format; they do not tune its scale, padding,
background or colors. Authors should make weather inherit the theme typography
and palette, including forecast bars and bundled icon treatment. A visible card
is theme-dependent: Classic and Minimal use transparent surfaces; Alpine uses
a translucent slate surface matching its buttons; Crăciun uses a warm dark
surface with a thin gold border; Retro uses an angular dark surface with an
accent border and offset shadow. Text stays container-free. Photographic themes
need sufficient surface opacity to keep every forecast row legible. Avoid applying the same generic
weather panel to every theme. All formats still use the common renderer.

Use existing typed Theme API properties where possible, extended with a small
set of weather parts. Proposed controls to validate during implementation:

- One overall scale, initially bounded to 0.85–1.25 of the format's baseline.
  The preset calculates layout from the scaled dimensions. Scale must not be a
  transform that leaves hit areas or reserved space at the original size.
- Primary/secondary text and condition-icon color; existing approved font family
  and weight settings. No independent tiny font overrides for forecast labels.
- Container background color/opacity, including transparent; border color/width,
  corner radius, and bounded shadow. Text mode has no container by default.
- Standard format padding and gaps through the same scale, not independent
  arbitrary offsets for every child.
- A bundled icon style: fill, flat, line, or monochrome. Keep standard fallback
  icons; remote icon URLs and theme scripts are not allowed.
- Forecast low/high bar colors, including a single-color appearance. Positions
  and lengths remain data-driven on one common scale.

The proposed scale bounds are an engineering starting point, not TV acceptance.
At a 1920x1080 logical canvas, essential secondary labels should target at least
28 px after scaling, with larger current-temperature numerals. Minimum readable
sizes and contrast take precedence over the declared scale. If a theme's chosen
format cannot fit at that floor, fix its declared region/scale or support list;
do not silently compress it below the floor or substitute another format on
each weather update. Test readability on a physical TV before claiming it.

Avoid a general widget engine, arbitrary absolute positioning, per-theme
JavaScript, configurable metric builders, or more forecast variants in this work.

## Compatibility and verification requirements

The component is packaged with Home, not downloaded from Home Assistant. Its
visual direction follows Clock Weather Card, with bundled licensed Meteocons
assets. This is an adaptation, not a commitment to importing Lit, Luxon, or the
Home Assistant runtime. Pin and inspect any reused source/assets and retain
their applicable notices.

Extend the compiler, policy, runtime, author tooling, and capability checks
together. Existing theme packages must not need a rebuild just to receive the
default weather appearance in an updated Home. New weather-aware packages must
declare the required Home capability/version; older Home must reject unsupported
packages safely. Do not rewrite immutable historical theme packages.

Verify every allowed preset/module/format combination, including the Inputs
shelf, long translated labels, extreme temperatures, missing values, theme
switches, user scale, different column counts, and Home scrolling. Verify Ribbon
always hides weather and Liquid Glass offers only text. Browser layout checks do
not establish TV readability, HTTPS availability, or device compatibility.

Data fetching, city search, cache/error policy, privacy disclosure, and settings
restoration must be specified before implementation. Previous research identifies
Open-Meteo as a candidate; this format decision does not establish its live TV
compatibility or waive its attribution and service terms.

## Historical browser prototype decisions

The local demo uses Open-Meteo forecast/geocoding, explicit manual city selection
or opt-in automatic city lookup through ipwho.is. IP lookup is approximate, not
GPS, and can follow VPN/provider routing. No city is inferred before Auto is
selected. The enabled switch hides the entire lower settings block when off and
cancels network activity. Location, units and format are restored locally.

Canonical data are Celsius/metres per second. Refresh policy is 15-minute fresh
reuse, at most six-hour stale display, five-minute automatic failure backoff and
a 12-second request timeout. Request generations reject stale results after
changing the location. Missing optional values remain absent. WMO codes are
localized in Home; daily labels use the city's calendar. Provider attribution
and update/stale status are visible in settings. These browser decisions still
need TV runtime, TLS/CORS and production service-term acceptance.

## Settings composition refinement

Use compact settings in the left column and a persistent selected-format preview
in the right. City search/mode controls open in a separate dialog from a summary
row rather than permanently occupying the settings page. The summary includes
the selected city for both manual and automatic modes. Automatic pending/failure
states fit that row. Back returns focus to the row. Left/right follow horizontal
unit choices; up/down follow visible settings rows.

User-facing format labels describe content: Compact, Now, In detail, 4 days.
The existing text/current/details/forecast identifiers and allowlists remain
unchanged. When live data are unavailable, the preview uses an explicitly labeled
example; Home never substitutes example weather.

## Production refinement approved after the prototype

Production uses opt-in GeoJS approximate city lookup; manual city search remains
the fallback when no city can be identified. The verbose status, privacy, refresh
and provider-link block was removed at the user's request. Keep the detected city
in the summary; do not reintroduce a diagnostic/status footer. Preview without
real data is explicitly marked Example and never appears on Home.

A Data sources button sits at the right of the Weather category heading, including
when weather is off. It opens a localized dialog with links to Open-Meteo, GeoNames,
GeoJS, Meteocons and the applicable licenses, plus a statement that values are
rounded/converted. No provider footer appears in any Home format or preview.
This placement follows the Open-Meteo maintainer's information-popup guidance:
https://github.com/open-meteo/open-meteo/discussions/2245. Back closes the dialog
and restores button focus; arrows/Tab stay within the dialog.
