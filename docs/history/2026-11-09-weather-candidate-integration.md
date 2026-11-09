# Weather integration into the next candidate — 2026-11-09

The candidate remains an unfrozen draft in [PR #458](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/458).
No release/component version was selected or bumped, no build was pinned and no
application release or TV installation was performed by this integration task.

## Merges and source evidence

- [Home PR #463](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/463)
  merged into main-project `release/next` as
  `b997b80e2b5b8bd2ee6a28c3335e6b6be4992eb5` after every executed PR check
  passed on head `b715c35dfaa887070e094effb0076e3bd00313ca`. The Pages deploy
  check was intentionally skipped for the PR; no failed or pending checks
  remained at merge. [Runtime/browser CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42604456764),
  [desktop runtime CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42604456726),
  [catalog validation](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42604456809).
- [Author toolkit PR #9](https://github.com/Razdva122/clean-your-tv-lg-theme/pull/9)
  merged into its own `release/next` as
  `c815f1415447e5f0bda578d9471b628d75d65c57` after all PR checks passed.
  Its merged source tree equals checked head
  `cb9175ef6876e118c754f11c1cd7536420f23b53`.
  [Candidate CI](https://github.com/Razdva122/clean-your-tv-lg-theme/actions/runs/42604441579)
  rebuilt the exact locked Home runtime and ran the paired tests. The runtime pin
  remains `afc8586955802270167daed6cd3a445fc31ff364`, with candidate status.

The main release inventory was regenerated with `scripts/release-flow.py collect`,
retaining #457/#459/#460/#461/#462 and adding #463 with issue #353. Toolkit #9
belongs to a separate repository; it is linked evidence, not main-project PR #9.
No exclusions or previous issue links were removed.

## Result and documentation

Home now includes opt-in real weather, four theme-aware formats, manual/approximate
automatic city choice, metric/imperial units, localized previews and an accessible
Data sources dialog. Ribbon suppresses weather; Liquid Glass supports Compact.
Theme package updates and credited temporary community forks are included;
Channel/Itachi leave the active catalog while historical packages stay intact.
Shared theme/API references, notices and thirteen practical localized guides
were updated. [Development evidence](../development/2026-11-09-weather-integration.md)
records focused source, browser, live public-city and remote-byte checks.

## Remaining release gates

Home now needs a version decision and rebuilt Root/No-root packages, synchronized
manifests and updated installer payloads. Previously planned installer/Root/updater
rebuilds remain necessary. Home Helper source is unchanged. Final versions,
release notes, full trusted build, package/signature/feed checks and rollback
acceptance remain with the candidate freeze.

No TV was contacted: model, firmware/webOS and remote are untested/unknown in this
integration. Browser evidence is not physical acceptance. Weather-specific TV
cases include provider TLS/CORS, city lookup/failure, units/formats, physical
remote/focus, scrolling, readability, offline expiry, wake/cold boot and update
preference retention/rollback. Preserve the earlier batch's unresolved recovery
and installation reports. Issue #353 stays open awaiting public release; this
merge does not announce delivery.
