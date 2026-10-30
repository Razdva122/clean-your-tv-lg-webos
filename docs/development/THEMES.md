# Theme development status (unreleased)

The maintainer has authorized integrating this current implementation, including
Themes, Columns and categorized settings, into the unfrozen `release/next`
candidate. Published packages do not yet contain this work, and integration does
not establish physical-TV acceptance.
The complete design remains in the [theme ecosystem specification](../superpowers/specs/2026-10-28-theme-ecosystem-design.md).

## Implemented in this preparation branch

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
  catalog, moderation states and read-only PR checks. Classic and Alpine are bundled; Channel is the first pinned external theme. The historical external Alpine listing is archived.
- A separate candidate author toolkit with templates, multi-theme repositories,
  actual-renderer browser preview, validation/build, screenshots and PR drafts.
  The main project exports its renderer/compiler with file hashes and provenance.

See [CSS reference](THEME-CSS.md) and [showcase contribution guide](../../showcase/README.md).
The toolkit is [clean-your-tv-lg-theme](https://github.com/Razdva122/clean-your-tv-lg-theme); its quick start explains the exact
working directory, launch command, browser address, live reload and shutdown.
No official downloadable author-runtime release is published yet. Local work
uses an explicitly exported candidate, with dirty snapshots labelled as such.

## Release gates and remaining work

- Implemented: built-in Classic/Alpine selection, external URL/collection install, app-origin IndexedDB, offline restore and durable 20-second trials. See [lifecycle/storage details](TV-THEMES.md).
- Runtime accepts five trusted composition presets (`dock-grid`, `icon-grid`,
  `side-grid`, `channel-list`, `scenic-grid`) with a configurable column count. Spacing/text/focus
  scales still require the Classic values; other combinations are explicitly
  rejected rather than silently disagreeing with navigation geometry.
- Implemented: file hashes, image headers/dimensions and bounded native decode before activation.
- Validate app-owned theme storage and service permissions on actual Root and
  No-root TVs, including quota, interruption, update and rollback preservation.
  IndexedDB is implemented and browser-tested; its TV-origin availability/quota remains a hardware gate.
- The theme-enabled candidate implements transport/storage/trials; published Home packages may not include it yet. Confirm the Themes control is present before following the candidate guide.
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
