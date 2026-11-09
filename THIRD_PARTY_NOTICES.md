# Third-party notices

- Launcher: derived from OmkarK97/webos-vibehack, MIT. Original Gathin and OmkarK97
  notices are retained in LICENSE. The font license is retained at launcher/fonts/OFL.txt.
- Outfit: SIL Open Font License 1.1, retained alongside the font.
- ws: bundled Node WebSocket dependency; license in native/app/vendor/ws/LICENSE.
- Legacy Helper uses ws 6.2.4, the UTF-8 validator from ws 7.5.11 and
  async-limiter 1.0.1 (MIT); sources, local changes and licenses are retained in
  `native/app/vendor/ws-legacy/`. Modern TV Node continues to use ws 8.21.0.
- webos-service: supplied by the TV runtime, not redistributed here.
- Zig, Python and LG's webOS CLI are external build/setup prerequisites.
- The optional Root TV runtime is CPython 3.13.17 from python-build-standalone
  release 20261021 (`armv7-unknown-linux-gnueabi`). It is downloaded separately
  only when required; ordinary installers do not embed the archive. Upstream
  Python and dependency license files accompany that runtime. Pin, provenance,
  checksum and update procedure: [optional Python](docs/OPTIONAL-PYTHON.md).
- Outbound HTTPS services bundle the Mozilla CA store converted by curl, under MPL 2.0.
  The snapshot, source, SHA-256 and refresh instructions are recorded in
  `docs/TLS-TRUST.md`; each service ships `ca-LICENSE.txt` alongside `ca-bundle.crt`.
- Compiled TV web apps include core-js (MIT) for ECMAScript compatibility and may
  include Babel helpers (MIT). Their license texts are retained in each web app's
  `compat-LICENSE.txt`. Babel and PostCSS are build tools, pinned by package-lock.json.
- Compiled Helper app and service include core-js, safe-buffer and Babel helpers
  (MIT), with licenses in each package directory's `compat-LICENSE.txt`.

TV app icons are downloaded only for a user's local app inventory. They are not
included in a clean public checkout or generic release package.

## Desktop wizard: Qt for Python

The optional windowed cytv distributions include PySide6 Essentials and Shiboken6
(Qt for Python), distributed under LGPL-3.0 (with applicable Qt exceptions) or
commercial terms. cytv uses the LGPL distribution with dynamically linked Qt
libraries. This does not change the license of cytv itself.

- Project and source: https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt source: https://code.qt.io/cgit/qt/
- License: https://www.gnu.org/licenses/lgpl-3.0.html

The LGPL-3.0 and accompanying GPL-3.0 license texts are included in the payload's
`licenses/Qt` directory. The pinned desktop runtime is Qt for Python 6.10.2;
its corresponding source is available under tag `v6.10.2` in the repositories above. Desktop packages use an unpacked application directory so
users can replace the dynamically linked libraries with compatible builds.

## Noto language fonts

Noto Sans, Noto Sans Devanagari and Noto Sans KR from the Google Fonts repository (https://github.com/google/fonts), distributed under the SIL Open Font License 1.1. Static regular subsets for Latin, Cyrillic, Devanagari and Hangul are bundled locally in `launcher/fonts/`; original copyright and license texts are included as `NotoSans-OFL.txt`, `NotoSansDevanagari-OFL.txt`, and `NotoSansKR-OFL.txt`.


The independent System Updater bundles Mozilla CA root certificates from the
curl CA Extract bundle. The certificate data and MPL 2.0 license are distributed
as `updater-service/ca-bundle.crt` and `updater-service/ca-LICENSE.txt`, and copied
into the supervisor bootstrap bundle.

## LG Developer Mode reference screenshots

The installer setup examples are screenshots from LG Electronics' official
[Developer Mode guide](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app).
Copyright LG Electronics; these third-party reference images are not covered by
CYTV's MIT license. Original URLs and provenance are included with the images in
`setup-guide/README.md` (Android: `ui/guide/README.md`). The screenshots show an
example LG UI, not a tested CYTV device or the user's credentials.

## Black Hole wallpaper video

Video author: **Xecutioner**. Original: [4K SCI-FI Black Hole](https://steamcommunity.com/sharedfiles/filedetails/?id=2981249186). The maintainer confirmed permission on 2026-11-04 for non-commercial use and inclusion in free CYTV distributions with explicit author attribution. The video, streaming copy and derived stills are not covered by CYTV’s MIT license. See [the artwork terms](themes/ribbon/LICENSE.txt) and [credits](themes/ribbon/CREDITS.txt). Commercial use requires separate permission. Private correspondence is retained privately.

## Optional weather

Weather data: [Open-Meteo](https://open-meteo.com/), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Home selects four days,
rounds and converts values, and translates condition codes; it does not redistribute
Open-Meteo server code. City names and coordinates come from
[GeoNames](https://www.geonames.org/), via Open-Meteo geocoding, under CC BY 4.0.
Weather settings provide an accessible Data sources dialog with provider/license
links. The maintainer explicitly permits an information popup in
[attribution guidance](https://github.com/open-meteo/open-meteo/discussions/2245). The free endpoint is for non-commercial usage, subject to
[Open-Meteo's service terms](https://open-meteo.com/en/terms).

Approximate automatic city lookup uses [GeoJS](https://www.geojs.io/).
Home retains only the city, region, country, coordinates and lookup time, not the
returned IP, ASN or other connection metadata. Manual search does not call GeoJS.

Bundled fill and monochrome weather icons: [Meteocons by Bas Milius](https://github.com/basmilius/meteocons), MIT.
A static subset is bundled, monochrome colors inherit the theme, and SVG IDs are
prefixed for inline use. The full notice is retained in
`launcher/weather-icons/LICENSE-METEOCONS.txt`; no icon CDN is contacted.
