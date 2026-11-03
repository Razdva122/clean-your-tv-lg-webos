<a id="theme-development-status-unreleased"></a>

# Theme development status

Themes, Columns and categorized settings are already available in published
packages. The 1.7.0 candidate changes the built-in lineup to Classic, Liquid Glass
and Ribbon; published 1.6.0 contains Classic, Alpine and Ribbon. Candidate
integration does not establish physical-TV acceptance.
The complete design remains in the [theme ecosystem specification](../superpowers/specs/2026-10-28-theme-ecosystem-design.md).

<a id="implemented-in-this-preparation-branch"></a>

## Current implementation

- Public Home, library and Inputs styling parts, separated Classic appearance,
  and trusted Settings/language/confirmation/update suspension in both editions.
- A shared Theme API 1 validator/serializer and host CSS compiler. Author data
  cannot supply executable scripts, plugins, arbitrary selectors or raw CSS values.
- Shared on-TV Columns settings: 1–8, or By theme. Explicit user choice takes
  priority over the author's `layout.columns`; Classic falls back to 5. Changes
  immediately use the existing layout/focus engine and retain app order/hidden IDs.
- A small separately stored column preference and effective count in the existing
  profile format. Authoritative restore clears a newer local preference once,
  then subsequent starts retain post-restore choices. Old supervisor schemas are
  unchanged. Legacy backups preserve the effective number, not the By theme mode;
  preserving that mode with installed theme state belongs to the storage gate below.
- A data-only reviewed showcase registry, pinned per-theme detail pages, static
  catalog, moderation states and read-only PR checks. Classic, Liquid Glass and Ribbon are bundled in the 1.7.0 candidate. Alpine 1.4.4 and Channel are external Showcase themes; the old toolkit Alpine listing remains archived.
- A separate candidate author toolkit with templates, multi-theme repositories,
  actual-renderer browser preview, validation/build, screenshots and PR drafts.
  The main project exports its renderer/compiler with file hashes and provenance.

See [CSS reference](THEME-CSS.md) and [showcase contribution guide](../../showcase/README.md).
The toolkit is [clean-your-tv-lg-theme](https://github.com/Razdva122/clean-your-tv-lg-theme); its quick start explains the exact
working directory, launch command, browser address, live reload and shutdown.
No official downloadable author-runtime release is published yet. Local work
uses an explicitly exported candidate, with dirty snapshots labelled as such.

## Release gates and remaining work

- Implemented: built-in Classic/Liquid Glass/Ribbon selection, external URL/collection install, app-origin IndexedDB, offline restore and durable 20-second trials. See [lifecycle/storage details](TV-THEMES.md).
- Runtime accepts five trusted composition presets (`dock-grid`, `icon-grid`,
  `side-grid`, `channel-list`, `scenic-grid`) with a configurable column count. Spacing/text/focus
  scales still require the Classic values; other combinations are explicitly
  rejected rather than silently disagreeing with navigation geometry.
- Implemented: file hashes, image headers/dimensions and bounded native decode before activation.
- Validate app-owned theme storage and service permissions on actual Root and
  No-root TVs, including quota, interruption, update and rollback preservation.
  IndexedDB is implemented and browser-tested; its TV-origin availability/quota remains a hardware gate.
- Published Home packages include transport/storage/trials. The built-in lineup follows the installed Home version. A saved `builtin:alpine` selection in 1.7.0 recovers to Classic with the visible recovery notice; it neither downloads Alpine automatically nor selects Liquid Glass.
- Generate complete real-renderer review scenarios and obtain separate device
  evidence before accepting the full community-theme release. Browser screenshots
  are not remote, standby, cold-boot, OTA or rollback acceptance.
- Voting is a later stage. No synthetic counts, voting controls or automatic
  popularity-based package changes are included.

## Source checks

Run `npm ci --ignore-scripts --no-audit --no-fund`, then:

```sh
npm run test:themes
npm run test:themes:browser
npm run test:geometry
npm run test:legacy-ui
scripts/test.sh
```

Browser checks use installed Chrome by default. CI sets `BROWSER_CHANNEL=chromium`
after installing Playwright Chromium. Showcase browser checks also support an
explicit `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` for an existing system Chrome.

The Pages workflow publishes the primary launcher preview with inline theme cards:

```sh
python3 scripts/preview.py --build build/theme-pages
```

Use fresh staging. An export containing the retired `/themes/` subtree is refused
before files are written, so old catalogue pages cannot survive a new deployment.
The main preview retains both editions, theme switching and the TV catalogue JSON.

The optional candidate `modern-icon-css-v1` capability supports bounded CSS-only
icon effects on browsers with filter/screen support. It never replaces original
app images; older browsers reject it safely. See [the contract](THEME-CSS.md#optional-css-icon-effects)
and [the local Itachi package source](../../themes/itachi/README.md).
