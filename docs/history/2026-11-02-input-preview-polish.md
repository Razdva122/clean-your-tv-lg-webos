# Inputs presentation and C3 browser probe — 2026-11-02

Unreleased follow-up in held PR #254. No merge into `release/next`, candidate
freeze, complete build, signing or public release is implied.

## Product changes and host verification

The theme-owned shelf now replaces the header Inputs shortcut when source tiles
exist. Menu mode and an empty shelf retain the shortcut; closest-target and
Left/Right navigation skip hidden controls. Changing theme with the menu open
closes it before restoring a visible target. A connected input without a firmware-reported device name now shows translated
Connected; reported names are preserved rather than guessed. Live preview defaults
off, requires the existing switch and appears only for shelf themes. Per maintainer
choice there is one switch without explanatory UI text; this record and the user
guides retain the observed audio/HDR limits.

The original CI viewport failure
was a stale test assumption that every default Home had shelf tiles. Updated
coverage preserves geometry tolerances and exercises menu/shelf explicitly at
720p/1080p in both editions.

The simulated picture previously appeared at mount, 300 ms before its `playing`
event changed icon/text state. It now remains hidden until that event and is
revealed afterward in the same task. Remove shelf text color fades, preserving
transform/background/opacity transitions and the 120 ms press animation. The
frame inherits theme rounding; safe release still does not depend on clipping.
A regression first reproduced premature picture visibility, then passed with
virtual-clock first-frame color/icon checks, corner hit testing and retained
240 ms focus/120 ms press transitions. Controller unit and compatibility checks
pass. Independent review found an overly broad transition override; it was
removed and re-reviewed. Header geometry, input shelf, overlay cleanup, packaged
Liquid Glass, motion and rendering-cost suites are covered by focused checks.

## Maintainer-owned device scope

| Field | Observed scope |
| --- | --- |
| TV | OLED55C3RLA |
| Firmware / SDK | 43.21.71 / 11.2.0; marketing webOS version not independently read |
| Remote | Not identified for this run |
| Edition | First a standalone browser video probe; then an isolated compiled Root UI preview |
| Release/components | Unreleased PR #254 source plus this polish; published-version declarations are not new packages; installed component versions not re-read |
| Installer/platform | macOS host, existing pinned Root SSH profile; no package installation |
| Input | Only connected HDMI 3; element mute requested before attachment, but audible sound was later reported |
| Unchanged scope | No Home route, Root intent, service permissions, firmware configuration, trust pin or production package writes |

The first direct-network page was unavailable. The same bounded probe was served
through a loopback-only reverse forward on the existing pinned SSH connection;
no discovery, replacement trust, firewall or SDK installation was used. The
owner started one native `service/webos-external` video at a time and compared
plain versus rounded wrappers. Native playing and timed stop events were
observed; the owner confirmed the real HDMI picture's corners rounded. Playback
was bounded to 25 seconds with explicit Stop and blur/hidden/pagehide release.
This confirms that browser/firmware scenario, not every Home renderer or model;
earlier webOS 6 observations of ignored clipping remain relevant.

At the owner's request, ordinary `tv-dev.py ui --stage-only` output was copied
into a private preview and launched in the existing TV browser. It retains the
separate development identity, namespaced storage and frozen service mocks.
Actual bundled Liquid Glass is selected; app icons/inventory are public test
fixtures. Only private native video creation for literal HDMI 3 is admitted;
other app/Home/system actions remain simulated. The host received `theme-ready`.
The owner focused HDMI 3; each media instance had a nonrenewing 45-second
playing deadline plus normal release. Repeated `playing` cannot extend it,
and an old detached media deadline cannot stop a future preview. The owner reported that the interface looked normal, but native HDMI produced
**audible sound despite `video.muted=true` and an HDR-on notification**. These are
observed failures of the requested quiet preview, not a muted-playback pass.
The host navigated the browser to a blank page to release native playback,
without changing TV volume/mute or HDR configuration. A refreshed compiled UI
was then launched with native-video creation removed and development preview
preference off; its `theme-ready` event was received. It uses simulated media
if that development-only preference is later enabled.

The product switch now defaults off and requires deliberate opt-in; native
mute/HDR behavior itself is **not fixed**. An exact packaged Home test remains
necessary before any claim about app-level quiet playback. No full-UI physical
acceptance is inferred from startup, owner appearance feedback or the standalone
rounding test.

No private address, URL token, pin, profile, app inventory, owner screenshot or
raw device reply is included. Physical Home/other controls, post-stop sound restoration, standby/cold boot,
OTA/rollback and other model/edition compatibility were not accepted here. UI preview is not signed-candidate or release evidence.

## Product source fingerprints used for this preview

| Source | SHA-256 |
| --- | --- |
| `launcher/app.js` | `6b6ef794e040c210a48b2d352ed02bddfaf7cc7cf388d10d016469dd390b947d` |
| `launcher/style.css` | `fe6868c546c406e26b435e0949d4b29504b2b46fec09e016215b0940c99858a4` |
| `preview/bridge.js` | `57589d524e15809417cdfe95e766650ee9586b3c965bc1e5599d7f3a1929bcff` |
| `launcher/input-sources.js` | `871425693eabaa57f98df4e1df5fbd6c28a5be8747cf119b184876cd2e399eee` |
| `launcher/catalogs.js` | `49ac005d6c45b449eabaf4cad044a66ebf6ffb7e0f3f9da56137d48c0b186adf` |
| `launcher/themes/liquid-glass/cytv-theme.json` | `f71d277b503010df3e2850b0f57a0bc91bc37c13d97c02d644b23a724e40523f` |
