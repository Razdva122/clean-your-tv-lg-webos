# v1.7.1 — Installer and browser demo corrections

This maintenance release contains only #274, #276 and #277.

## Changes

- macOS installers accept PyInstaller's normal alias to the bundled package folder.
  Previously setup could report “Embedded graphics packages are missing or invalid”
  before installation even when the packages and hashes were correct. Individual
  package/member links, hashes, application identity, version and graphics-resolution
  checks remain enforced. Related reports: #270, #271, #273.
- Source setup installs the existing pinned font build requirements before TV access,
  avoiding the missing `fontTools` failure on a clean computer (#272).
- The browser demo downloads reviewed theme packages on preview selection. Its initial
  catalogue excludes theme assets; validated packages are reused across edition changes.

## Versions and packaging

| Component | v1.7.0 | v1.7.1 |
| --- | --- | --- |
| cytv | 0.8.0 | 0.8.1 |
| Android / versionCode | 0.7.0 / 18 | 0.7.1 / 19 |
| Home | 1.8.1 | 1.8.1 |
| Home Helper | 0.6.22 | 0.6.22 |
| Root | 0.8.4 | 0.8.4 |
| Independent updater | 0.4.2 | 0.4.2 |

Desktop/console and Android installers must be rebuilt because Android embeds the
shared installer implementation. No TV runtime source is changed. Existing users do
not need a TV component update to receive these host/demo corrections. Published
archives are immutable; this release does not replace bytes at older URLs.

## Validation and limits

The [macOS reproduction](history/2026-11-03-macos-graphics-payload-alias.md),
[source dependency checks](history/2026-11-03-source-install-build-dependencies.md)
and [final installer acceptance](history/2026-11-03-release-1.7.1-host-checks.md)
record the actual checks and hashes. Full build
[41672562712:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41672562712)
passed every required platform/runtime/browser gate. All seven TV IPKs in all
nine installer payloads, Root infrastructure and every Android embedded payload
entry match published 1.7.0 bytes. Both macOS payload aliases passed selection;
the exact ARM64 app passed offline runtime, payload and GUI smoke checks.
The exact original-signer Android APK passed code18-to-code19 emulator upgrade,
four-file synthetic retention and real native Store/operation checks.

No reporter installation success or new physical-TV result is claimed. Prior
[1.7.0 observations](history/2026-11-03-release-1.7.0-final-packages.md) retain their
original artifact, firmware and scenario limits. Physical installation, controls,
audio, standby/cold boot, phone-to-TV, OTA and rollback were not repeated for this
host patch. Original recovery/compatibility reports remain open where unresolved.
Keep existing signed recovery and rollback data. The frozen inventory and build
pin are maintained in [release PR #275](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/275).
