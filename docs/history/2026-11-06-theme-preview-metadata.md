# Theme preview metadata and Crăciun UHD — 2026-11-06

Implementation evidence for the next, unfrozen candidate. No release version,
final build or production-package acceptance is selected by this work.

## Changes

Both edition pickers and the primary browser preview show total declared package
bytes as decimal MB. Classic remains app-native and has no fabricated package
size. The 4K badge requires a 3840×2160 video variant; image dimensions alone
do not establish UHD output. A film icon advertises reviewed moving video bytes
from the hash-bound `showcase/moving-wallpapers.json`. Still MP4 loops such as
Alpine and Crăciun receive no film icon. Unknown motion is not advertised.
Badges introduce no focus stops; their sizes are 18px in the browser switcher
and 26px in the TV pane. Detail badges remain inside the 480px image frame.

Crăciun 1.2.0 source is committed at
`cbab0161859d57897f25652152b1b2cf57463fc2`; distribution commit is
`5ae94595` (the registry records its full immutable URL). The main-project
identity follows the existing maintained-Alpine model because the original
author repository is read-only to the maintainer. Original source CSS, preview
and fallback JPEG are preserved. Rares retains styling/composition credit;
MIT styling and CC BY 4.0 wallpaper/video notices are included. The old author
listing is retained as removed historical evidence; cached installations are
not automatically replaced or selected.

The new package is approximately 3.1 MB and includes silent two-second H.264
variants at 3840×2160 and 1920×1080. Its image was originally AI-generated at
1672×941 and upscaled by the author with Real-ESRGAN. UHD output is not native
source detail or animation.

## Automated verification

On macOS, current Node and Chrome with simulated TV services:

- Full `npm run test:themes` passed. The initial sandbox run could not bind its
  loopback receiver; the network-permitted run passed. A real suite regression
  exposed assumptions about minimal ThemeData test implementations; metadata is
  now supplied by verified data and the complete suite passes.
- Source/distribution byte hashes, local Showcase and hostile-submission checks,
  catalogue freshness, thirteen-language catalogues and TV web compatibility
  passed. Final remote bytes are verified after the branch is pushed.
- Root and No-root inline preview checks passed, including actual 3840×2160
  decoding of Crăciun, all preview images loading, no still-video film badge,
  original app order and selected-theme persistence across edition changes.
- Both-edition installed-preview lifecycle and deferred-catalogue focus checks
  passed at their existing viewport sizes.
- Independent review found one minor detail-frame alignment issue, corrected
  before integration; no security or data-integrity blocker was identified.

Showcase and source authoring instructions document the new metadata and
packaging. Localized installation flows and controls were reviewed: this change
adds informational badges without a new setup action or remote binding.

## Bounded development-TV observation

Maintainer-owned LG OLED55C3RLA, firmware 43.21.71, known candidate context
webOS SDK 11.2; remote is pointer/wheel, exact model unknown. Installer/host:
macOS, existing trusted SSH, already installed SDK hosted container 1.1.0.
Edition: isolated Root-style UI, app metadata 0.0.1, shared Home engine 1.10.0,
Crăciun package 1.2.0. Production component versions were not changed or retested.

Expected: the new theme appears in Themes with 4K, about 3.1 MB and no film icon.
Observed: the container launched, fetched the verified theme and media, and the
owner confirmed the theme/card looked correct. Badges were subsequently enlarged
and the development page reloaded. This is UI observation, not signed-package
installation or proof of native 4K video-plane output. HTTP media requests alone
are not decoder/display evidence; physical UHD playback remains unverified.

Direct host-interface HTTP failed in this development environment. A temporary
loopback-only SSH reverse tunnel and a local range-capable static server allowed
the existing SDK container to load the isolated stage. No production app, Home
routing, updater, saved profile or network policy was modified.

Home routing, sound, standby, cold boot, OTA, rollback, production-package
installation and other devices are untested. Final release/component bumps,
coherent packages and affected physical acceptance remain release-coordinator
work at freeze. No private profiles, raw diagnostics or device screenshots are
included in this record.
