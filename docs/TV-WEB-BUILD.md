# TV web compatibility build

The web frontend targets **Chromium 38**, the engine documented for webOS 3.x.
The same compiled assets run on later Chromium-based webOS engines. This is a
frontend build target, not a claim that Home Helper, input devices or firmware
services work on every TV. An unreleased #152 correction also emits the prefixed
layout/transform/animation forms required by webOS 2.x WebKit 538.2. Autoprefixer
uses Safari 8 as its prefix profile; that is not a complete WebKit compatibility
target or physical EF950V acceptance. The unsupported-feature gate remains intact.

Source builds require Node.js **20.19+** (Node 22 is used in CI) and npm:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run lint:compat
npm run test:compat
```

All production TV web packages pass through `scripts/tv_web_build.py`:
No-root Home, Root Home, Home Updater and Root Updater. Desktop and Android
installers embed these compiled packages. Native executables, TV Node services
and Python code retain their own runtimes. Helper JavaScript has a separate
Node-targeted build described below; other TV Node services are not transformed in ordinary builds. The opt-in
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
wrappers keep their behavior. Compatible ES5 sources keep their original bytes.
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
No setup steps or controls change. The fix is unreleased; visual acceptance on
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

## Helper Node compatibility

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

Run `node tests/helper-compat.cjs` with current Node; set `NODE010` to Node
0.10.25 and `NODE012` to Node 0.12.2 to test all three runtimes. The regression
compiles the actual Helper sources, exercises real pairing-key replacement
using bounded descriptor reads (Node 0.10 cannot use `readFileSync(fd)`),
exercises controller startup/error handling with TV hardware/Luna substitutes,
and service status/listApps, and performs a real local WSS register/subscribe,
fragmented text, ping/pong and close exchange. Invalid UTF-8 and oversized
payloads must be rejected. CI downloads a SHA-256-pinned official Linux x64
Node 0.10.25 and 0.12.2 archives. Packaged service tests also use those runtimes
when available. The legacy WebSocket imports the named EventEmitter constructor
and skips optional TLS write batching when unavailable on Node 0.10.
This verifies Node compatibility, not access to a TV's evdev devices.

Node 0.10.25 support is an unpublished source/test-build change for issue #152.
The EF950V reporter confirmed the computer-to-TV connection in v1.5.0, but the
published installer stopped before installation on that runtime. Launcher,
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
pinned at commit `e7db6ca603fd4862010383ff17ffd6cc4ffac1c0`. To regenerate,
download each original `NotoSansSC[wght].ttf` / `NotoSansTC[wght].ttf` into a
temporary directory as `NotoSansSC-variable.ttf` / `NotoSansTC-variable.ttf`,
then run:

```sh
/path/to/fonttools-4.60.1/bin/python scripts/subset-chinese-fonts.py /path/to/original-fonts
```

This developer-only tool bakes weight 400 and retains the catalog character set
plus Chinese date text. Regenerate after adding Chinese strings; package tests
reject missing catalog glyphs or variable fonts. User app names outside this
subset continue to use the TV's system fallback. These fonts do not establish
physical-TV rendering acceptance; verify both scripts on the candidate packages.
