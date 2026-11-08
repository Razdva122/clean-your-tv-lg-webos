# TV web compatibility build

The web frontend targets **Chromium 38**, the engine documented for webOS 3.x.
The same compiled assets run on later Chromium-based webOS engines. This is a
frontend build target, not a claim that Home Helper, input devices or firmware
services work on every TV. The published #152 correction also emits the prefixed
layout/transform/animation forms required by webOS 2.x WebKit 538.2. Autoprefixer
uses Safari 8 as its prefix profile; that is not a complete WebKit compatibility
target or physical EF950V acceptance. The unsupported-feature gate remains intact.

Source builds require Node.js **20.19+** (Node 22 is used in CI) and npm:

```sh
npm ci --ignore-scripts --no-audit --no-fund
python3 -m pip install -r scripts/build-requirements.txt
npm run lint:compat
npm run test:compat
```

All production TV web packages pass through `scripts/tv_web_build.py`:
No-root Home, Root Home, Home Updater and Root Updater. Desktop and Android
installers embed these compiled packages. Native executables, TV Node services
and Python code retain their own runtimes. Helper JavaScript and the No-root Home/independent Updater services use the
separate Node-targeted build described below. Root services retain their
existing runtime requirements. The opt-in
[Root Node prototype](development/ROOT-NODE-PROTOTYPE.md) separately compiles the
Root runtime closure for host tests; Root admission remains Node 8+.
The installed cytv apps do not require Node/npm on the user's computer.

## Processing and validation

- Babel preset-env transforms modern JavaScript syntax into ES5. Acorn checks
  every emitted script against ES5, including scripts embedded in HTML.
- A bundled core-js runtime loads before application scripts and supplies missing
  ECMAScript built-ins. It is packaged locally, with licenses, without a CDN.
  It does not supply platform-specific Luna APIs or every modern browser API.
- PostCSS preset-env/Autoprefixer use the Browserslist entry in `package.json`
  plus the Safari 8 prefix profile. For example, `inset` becomes physical offsets
  and alpha hex colors become compatible color notation. CSS files, `<style>` elements and
  `style` attributes all pass through this step.
- doiuse checks the **transformed** CSS. Unsupported features left after PostCSS,
  including CSS Grid and flexbox gap, fail the build. Use compatible layouts and
  margins for those cases; do not globally disable the checks. An extra value
  check rejects `overflow-wrap: anywhere`, which doiuse misses.

There are two narrow, documented allowances: original `overflow` values
(`visible`, `hidden`, `auto`, `scroll`) are accepted despite doiuse's broad
partial-support warning; an optional `prefers-reduced-motion` override has a
scoped source comment because older engines safely ignore that media query.
Newer overflow values are still rejected. The linter uses compatibility data;
it is not an exhaustive proof of browser behavior.

Scripts remain separate classic scripts so the existing globals and UMD
wrappers keep their behavior. Compatible ES5 sources keep their original bytes, except block function
declarations: Acorn accepts these as ES5, but strict Chrome 38 code rejects
them, so the compiler also transforms that syntax.
No webpack or application-module migration is needed. Build products are staged
separately; the compiler never overwrites a developer's app configuration,
inventory or icons in the source tree.

## Static TV fonts

Home and Root Home use static Outfit Light (300), Regular (400), Medium (500)
and Bold (700) files. Each CSS face declares one weight, including 700 for browser
bold defaults. This preserves the intended typography without variable-axis
support. The retained variable source defaults to Thin (100); old engines can
render that default for every weight (issue #68). Do not reference it in TV CSS.
The CSS gate rejects weight ranges; binary regressions check fixed weights,
distinct baked outlines, original character mappings and Root package staging.
Both preview inventories include the same static assets and OFL license.

To regenerate from the retained `launcher/fonts/outfit.ttf`, use a temporary
Python environment with `fonttools==4.60.1` (not a TV/build runtime dependency):

```sh
for weight in 300 400 500 700; do
  fonttools varLib.instancer launcher/fonts/outfit.ttf wght=$weight --static \
    --update-name-table --no-recalc-timestamp -o launcher/fonts/outfit-$weight.ttf
done
```

See [fontTools instancing](https://fonttools.readthedocs.io/en/latest/varLib/instancer.html).
No setup steps or controls change. The fix is packaged; visual acceptance on
the reporter's LG LM6370PSB / webOS 4.5 / Chromium 53 remains required. Host tests
verify assets and rendering in a current browser, not physical TV readability.
The separately reported Helper-unavailable state remains unresolved.

## Regression checks

`npm run test:compat` verifies syntax conversion, missing built-ins, polyfill
ordering, inline assets, rejected unsupported CSS and repeatable HTML injection.
`scripts/test.sh` runs it and the compatibility linter. CI also runs the browser
regression on the compiled Home frontend:

```sh
python3 scripts/tv_web_build.py --input launcher --output build/legacy-ui
npx playwright install chromium
BROWSER_CHANNEL=chromium TV_WEB_DIR=build/legacy-ui npm run test:legacy-ui
BROWSER_CHANNEL=chromium TV_WEB_DIR=build/legacy-ui npm run test:geometry
```

The browser test verifies the actual rendered Outfit face for each weight, then
disables `inset` and selected JS APIs to reproduce issue #20.
It checks actual card hit-testing, dimensions, icon fallback, scrolling,
launch/navigation and full-screen dialogs. This models the reported engine
limitations in a current browser; it is not an emulator of an entire old TV.
Hardware confirmation is still required on the original webOS 3.5 device.

The `prefixed-webkit` profile additionally ignores unprefixed flex, transforms,
transitions and animations, including runtime-injected theme styles and CSSOM
writes. It checks horizontal shortcuts, focus-frame alignment, scrolling,
dialogs and runtime Ribbon skew/bottom alignment. `launcher/app.js` writes both
CSSOM transform/transition forms. Theme runtime prefixes its validated output
only when the CSSOM exposes the legacy WebKit form, enforcing the emitted CSS
budget before changing layout or styles. Browser API, firmware input and actual
EF950V controls/recovery remain separate unverified device paths.

The geometry regression renders one through eight columns and checks spacing
between the focus frame and neighbouring cards, frame alignment, remote
navigation, scrolling back to the dock and the separately constructed Add app
tile. Card dimensions are calculated in `launcher/app.js`; CSS inherits the
item width rather than maintaining a second fixed card size. Sparse layouts
retain the original maximum size, while denser layouts reserve room for the
enlarged focus frame. These browser checks do not establish physical TV
performance or Home-button compatibility.

## Helper and No-root service Node compatibility

`scripts/helper_build.py` and `scripts/compile-helper.cjs` target **Node 0.10**
independently of Browserslist. Both `build-cytv.py` and `build.sh` compile the
Helper app and its status/inventory service, including vendored JS. Every
emitted `.js` file passes an ES5 parse check. Babel always runs, including on
sources that parse as ES5: strict block function declarations still fail in
Node 0.12 without transformation. Each top-level module loads local
core-js and safe-buffer before importing application dependencies. The original
Buffer constructor is preserved; only missing safe Buffer methods are added.
A Node 0.x shim also forwards callback arguments through `process.nextTick`.

`websocket.js` selects ws 6.2.4 below Node 10 and ws 8.21.0 on newer TV Node.
The legacy tree includes async-limiter and the pure JS UTF-8 validator from
ws 7.5.11; see its retained source notes. SSAP clients disable compression and
keep their handshake/payload limits. TV-provided webos-service remains external.
Published historical Helper baselines retain their original bytes.

The published build also compiles the No-root Home renewal service and
independent Updater service through this compiler in both source-package and
embedded-payload builds, including Home's injected theme receiver. The Updater
uses Node's legacy `url.parse`/`url.resolve` APIs, with HTTPS, credential, host,
port and path restrictions reapplied on every redirect; `require('url').URL` is
unavailable on Node 0.12. No endpoint or persisted state is added. The two Helper
SSAP clients request the same full permission set so registering inventory does
not replace the screen watcher's permissions on webOS 3.x.

`node tests/tv-service-compat.cjs` loads both compiled services and exercises
Updater URL validation and bounded relative/CDN redirects on current Node and
any configured `NODE010`, `NODE01025` and `NODE012` runtimes. The LS2 and HTTPS
substitutes establish host behavior, not actual TV bus permissions, TLS access,
Developer Mode boot, package installation or update/rollback acceptance.


Run `node tests/helper-compat.cjs` with current Node; set `NODE010` to Node
0.10.15, `NODE01025` to Node 0.10.25 and `NODE012` to Node 0.12.2 to test
all four runtimes. The regression
compiles the actual Helper sources, exercises real pairing-key replacement
using bounded descriptor reads (Node 0.10 cannot use `readFileSync(fd)`),
exercises controller startup/error handling with TV hardware/Luna substitutes,
and service status/listApps, and performs a real local WSS register/subscribe,
fragmented text, ping/pong and close exchange. Invalid UTF-8 and oversized
payloads must be rejected. CI downloads a SHA-256-pinned official Linux x64
Node 0.10.15, 0.10.25 and 0.12.2 archives. Packaged service tests also use those runtimes
when available. The legacy WebSocket imports the named EventEmitter constructor
and skips optional TLS write batching when unavailable on Node 0.10.
This verifies Node compatibility, not access to a TV's evdev devices.

Node 0.10.25 support shipped in v1.5.4 for #152; later published installers lower only
No-root installer admission to 0.10.15 for #283/#284 after exact runtime checks,
including unchanged published Helper 0.6.22 JavaScript. The older 1.7.1 installer still requires 0.10.25. No Helper product byte or Root requirement is
changed by this admission correction. The dated [webOS 1.x investigation](history/2026-11-04-webos1-node-floor.md)
records runtime/archive hashes and untested hardware scope. Launcher WebKit,
Home/Back, emergency release, standby, cold boot and recovery still require
separate physical-device acceptance; do not bypass the published version gate.

References: [LG engine versions](https://webostv.developer.lge.com/develop/specifications/web-api-and-web-engine),
[Babel preset-env](https://babeljs.io/docs/babel-preset-env),
[PostCSS preset-env](https://preset-env.cssdb.org/),
[doiuse](https://github.com/anandthakker/doiuse).


## Chinese UI fonts

The UI supports `zh-Hans` (Simplified Chinese) and `zh-Hant`
(Traditional Chinese). Explicit script tags take precedence over a region;
`zh`, CN and SG default to Hans, while TW, HK and MO default to Hant.
The preference is selectable and persisted using the existing language setting.
Home, Root Home, both independent updaters and Homebrew Installer carry static
Regular Noto Sans SC/TC subsets and their SIL OFL licenses. Desktop payloads
also include them; Android uses its platform font fallback.

The sources are [Google Fonts Noto Sans SC](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/notosanssc)
and [Noto Sans TC](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/notosanstc),
pinned at commit `e7db6ca603fd4862010383ff17ffd6cc4ffac1c0`. The build-only
`fonttools==4.60.1` dependency is installed from `scripts/build-requirements.txt`;
it is never loaded by a TV or installed/frozen runtime.

Packages, standalone installer fonts and live/static previews use the same
`scripts/chinese_fonts.py` preparation path. It decodes Chinese locale literals
(including Unicode escapes and static template text) from runtime catalogs,
including themes, Root audio, installers and updater screens, plus calendar and
language labels. Compiler inputs also contribute unscoped JavaScript/template
text, JSON strings, HTML text/entities/inline code and CSS content/escapes, so a
new locale module or static label needs no central source-list edit. Foreign
locale branches stay separate; initial HTML language does not hide shared code. Retained static faces are reused only when they cover all required
characters. Otherwise the build automatically generates small static weight-400
subsets; adding translations never requires editing tracked font binaries.

On the first regeneration, verified TLS downloads retrieve only those two pinned
sources. SHA-256 pins are SC
`a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`
and TC `864727d210d54f2537bbe23b3a839436c3992af72de9322af5270897246bd44f`.
Verified originals and deterministic subsets live in `build/chinese-font-cache`
(or `CYTV_FONT_CACHE`). Reuse that directory for offline builds; CI can cache it.
Corrupted cache entries fail with an integrity error rather than being trusted.
Each UI locale prefers its own regional Chinese face, then the other packaged
face. Shared theme names and quoted mixed-script brands use that cascade; each
subset retains the required glyphs supported by its full pinned original. A
glyph absent from both pinned originals fails explicitly. Nonregular cache
entries are refused before reading.
`scripts/subset-chinese-fonts.py` optionally primes this same cache; it does not
modify source assets. User app names outside the UI subset use system fallback.
These fonts do not establish
physical-TV rendering acceptance; verify both scripts on the candidate packages.
