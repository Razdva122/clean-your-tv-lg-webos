# Clean Your TV comparison baseline

Snapshot: 25 October 2026. The comparison uses public **v1.2.0**, commit
`d5804f6a7ce5d4eb35c0093ca19ae011e5a6df7f`, published at 13:48:20 UTC.
The local research started at `39dd72c5d317f98a9ddeac330bc003e22f3cd057`.
Its later desktop recovery work and concurrently edited Android release work are
excluded from published-feature claims.

## Published components

| Component | Version | Qualification |
| --- | --- | --- |
| Distribution | 1.2.0 | Public GitHub release; Android retains preview status |
| cytv installer | 0.3.1 | Desktop and console distributions |
| Home | 1.4.1 | Shared launcher interface |
| Home Helper | 0.6.19 | No-root input and lifecycle controller |
| Root Edition | 0.3.0 | Existing root required |
| Edition Updaters | 0.2.1 | On-device installation requires root |
| System Updater | 1.0.0, protocol 1 | Separate computer bootstrap required |
| Android | 0.2.1-preview, versionCode 10 | ARM64, debug-signed preview |

Sources: [release](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.2.0),
[version manifest](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/release-versions.json),
[release scope](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/RELEASE-1.2.0.md).

## Features and evidence

| Area | Published behavior | Source |
| --- | --- | --- |
| Access | No-root through Developer Mode; separate edition for existing root | [Editions](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/EDITIONS.md) |
| Installation | One wizard for both editions; bundled computer runtime and TV packages | [CLI](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/CLI.md) |
| Desktop | Windows x64 graphical ZIP, macOS Intel/ARM, Linux x64 DEB; console builds too | [Desktop](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/DESKTOP_INSTALL.md) |
| Phone | Android install, status, restore and Helper diagnostics; no uninstall, discovery or System Updater bootstrap in this preview | [Android](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/android/README.md) |
| Discovery | Desktop/CLI SSDP discovery across active local IPv4 interfaces; manual address fallback | [CLI](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/CLI.md) |
| Connection | Saved TV profiles, SSH fingerprint confirmation, password/private-key access | [Transport](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/cytv/transport.py) |
| Version review | Shows installed and bundled versions before installation; distinguishes reinstall and downgrade | [CLI](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/cytv/cli.py) |
| Runtime | Eligible Root setup can provide a verified private ARMv7 Python; it does not obtain root | [Optional Python](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/OPTIONAL-PYTHON.md) |
| Layout | Personal grid, configurable dock, local icons, focused-app ambient colour | [Launcher](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/app.js) |
| Organisation | Hold OK to reorder; Back cancels; hide and undo; restore via Add app | [App management](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/APP-MANAGEMENT.md) |
| Inventory | Add app requests fresh installed-app inventory; unavailable service falls back to saved inventory | [App library](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/app-library.js) |
| Persistence | Tile order, hidden IDs and known catalog survive restart and supported profile recovery | [User data](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/user-data.js) |
| Clock | Localised clock, date and time-dependent greeting | [Launcher](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/app.js) |
| Inputs | Input chooser and HDMI launching; labels included in setup/profile data | [Launcher markup](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/index.html) |
| Settings | Wi-Fi shortcut and LG settings access | [Launcher](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/app.js) |
| Languages | Ten TV/installer languages, automatic system selection and saved override | [Catalogs](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/catalogs.js) |
| No-root Home | On-TV Helper intercepts short Home; no everyday external watcher | [Controller](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/native/app/native.js) |
| Root Home | Native system routing with independent recovery; must not run alongside old Helper interception | [Root lifecycle](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/root-edition/README.md) |
| Back | No-root watches app exit while preserving navigation; LG can flash. Root has scoped C3 evidence without that flash | [Compatibility](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/COMPATIBILITY.md) |
| Escape | Triple Home within two seconds stops Home control; deliberate resume required | [Recovery](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/RECOVERY.md) |
| Watchdog | Releases interception after stalled controller; duplicate-controller lock | [Native implementation](https://github.com/Razdva122/clean-your-tv-lg-webos/tree/v1.2.0/native/prototype) |
| Input | Arrows/held arrows, OK and pointer; other buttons and wheel events pass through | [Input filter](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/native/prototype/filter.c) |
| Home choice | Settings switch controls ordinary routing; visiting LG Home once retains the saved choice | [Home control](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/helper-control.js) |
| Developer Mode | Optional on-TV renewal Beta, session check and diagnostics | [Renewal](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/launcher/renewal-panel.js) |
| Maintenance | Status, diagnostics, restore and uninstall via desktop/CLI | [Desktop](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/DESKTOP_INSTALL.md) |
| Helper diagnosis | Guided Home-press capture and bounded report export | [Diagnostics](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/HELPER-DIAGNOSTICS.md) |
| Privacy of reports | Bounded, allowlisted diagnostics; special Home capture can contain observed app IDs/timing and needs review before sharing | [Diagnostic implementation](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/cytv/diagnostics.py) |
| Updates | Signed edition release sets, independent worker, profile backup, previous component cache and rollback | [Updates](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/UPDATES.md) |
| Uncertain operations | Durable receipts block automatic replay of an unknown install/removal outcome | [Recovery operations](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/cytv/operations.py) |
| Firmware policy | Root UI controls Homebrew's saved blockUpdates preference; readback and a real restart are required | [Firmware control](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/LG-FIRMWARE-UPDATES.md) |
| Old runtimes | TV web compatibility targets Chrome 38; Helper targets Node 0.12.2+; Root needs Node 8+ and Python 3.9+ | [Build](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/TV-WEB-BUILD.md) |
| HTTPS | Bundled Mozilla CA store for outbound downloads | [TLS trust](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/TLS-TRUST.md) |
| Preview | Browser simulation with demo inventory and both editions | [Preview](https://github.com/Razdva122/clean-your-tv-lg-webos/tree/v1.2.0/preview) |

## Product gaps in the published baseline

No public implementation was found in the reviewed v1.2.0 launcher/settings
surfaces for app folders/search, recent-app switcher, individual background-app
closing, weather, user wallpaper gallery/video wallpapers, photo screensaver,
Immich, full Control Center, remote shortcut remapping, OLED wear dashboard,
device-wide ad/telemetry blocking, app uninstall from the TV launcher or MQTT/Home
Assistant integration. Hiding a CYTV tile leaves the installed app and system ads
intact. Passing wheel events through is not wheel-to-tile navigation.

The input chooser is not an EPG or tuner channel guide. A clean launcher screen
is not device-wide debloating. An update signature and local tests are not proof
that the entire physical update/rollback path has passed device acceptance.

## Remaining acceptance boundaries

- The documented Root evidence is concentrated on OLED55C3RLA / firmware
  43.21.71. It is not a model-wide or all-webOS compatibility claim.
- No-root Helper 0.6.19 still needs original-device acceptance. C4 key ownership,
  long Back and resume fixes retain their stated hardware limits; C5 Helper
  startup remains under investigation in the published compatibility record.
- True Root cold-power startup and a complete signed System Updater upgrade and
  rollback remain untested in the cited public record.
- No-root auto-renewal remains opt-in Beta; Android remains a preview. Neither is
  promoted to confirmed physical compatibility for this comparison.
- v1.2.0 contains a partial Root migration improvement and extra installation
  diagnostics. Its release notes explicitly preserve the original OLED Flex and
  UN70006LA failures. Extra diagnostics are not treated as failure resolution.

Sources: [compatibility](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/COMPATIBILITY.md),
[acceptance](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/RELEASE-1.2.0-ACCEPTANCE.md),
[release scope](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.2.0/docs/RELEASE-1.2.0.md).

No GitHub issue statuses are inferred from these historical documentation entries.
This research does not implement a fix or handle a candidate merge.
