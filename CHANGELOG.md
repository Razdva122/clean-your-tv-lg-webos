# Changelog

## v1.6.0 — frozen candidate, not published

- Complete the five-stage installer diagnostics/recovery/outcome/admission/guidance work.
- Add adaptive HD/FHD delivery, Czech TV localization, compact Chinese fonts and themes.
- Refresh Root Settings and retain conservative rollback/recovery authority; known device failures remain open.
- See [selected versions, inventory, migration limits and release gates](docs/RELEASE-1.6.0.md).

## Earlier unreleased preparation

- Prepare Root OTA compatibility with the original 1.3.0 System Updater (#115):
  preserve managed paths and LS2 grants, validate candidate infrastructure before
  offering installation, and authenticate current runtime separately from its
  original bootstrap. Hardware update/rollback acceptance is still pending.


## v1.4.0

- Integrate #80, #81, #87, #89, #97 and #99: safe settings diagnostics, guided
  setup, verified missing-Home initialization, experimental opt-in eARC recovery,
  frozen Intel macOS dependency loading and actionable private-Python preflight.
- Include #102 pinned C2 package-data verification and interrupted No-root recovery;
  original report/device outcomes remain unresolved.
- Add #103 Root observer diagnostics and #105 clock-independent cold-start identity
  with one optional startup Home request. The corrected-runtime cold-boot, first-screen,
  early app-focus and emergency/off matrix must pass before publication.
- See [candidate scope and versions](docs/RELEASE-1.4.0.md) and
  [testing matrix](docs/RC-1.4.0-TESTING.md). C3 acceptance and manual rollback passed; see [scope and limits](docs/RELEASE-1.4.0-ACCEPTANCE.md).

## v1.3.0 — recovery, installer portability and localized Home

- See [release notes](docs/RELEASE-1.3.0.md) and the scoped
  [acceptance record](docs/RELEASE-1.3.0-ACCEPTANCE.md).

## v1.2.0 — Helper recovery and Root firmware settings

- Offer confirmed Helper start when firmware denies status (#59, #60).
- Validate Root migration before installation and recover verified cleanup before
  provisioning (#55, #61); the reported recovery-service startup failure remains unresolved.
- Preserve sanitized Luna rejection codes in installer diagnostics (#51, #62);
  the original installation refusal remains unresolved.
- Add Root control for Homebrew-owned LG firmware update blocking (#63).
- See [release notes](docs/RELEASE-1.2.0.md) and the
  [acceptance record](docs/RELEASE-1.2.0-ACCEPTANCE.md).

## v1.1.0 — System updates and automatic Root Python

- Fix Home Helper startup on TV Node 0.12.2 with a separate Babel/polyfill build,
  compatible WebSocket client and guarded error logging (#47, #54). Original-TV input,
  standby and cold-boot acceptance remains pending.

- Add a fixed System Updater supervisor and signed whole-edition updates with
  independent recovery, preserved profiles and component-set rollback.
- Supply a verified private ARMv7 Python on demand for eligible Root TVs; keep
  runtime bytes out of ordinary installers and retain bindings for recovery.
- Improve per-requirement Root diagnostics, Android operation receipts, TV
  package metadata, protected staging and bundled HTTPS trust.
- Prepare cytv 0.3.0, Home 1.4.0, Helper 0.6.19, Root and both Updaters 0.2.0,
  Android 0.2.0-preview / code 9 and supervisor 1.0.0 / protocol 1.
- See [release notes](docs/RELEASE-1.1.0.md) and the dated
  [acceptance record](docs/RELEASE-1.1.0-ACCEPTANCE.md) for tested and untested paths.

## v1.0.3 — Home recovery and installer diagnostics

- Carry the complete unpublished v1.0.2 scope, with Root 0.1.12 for shared app.js/style.css changes.
- Keep cytv 0.2.16, Home 1.3.8, Helper 0.6.18, Android 0.1.7-preview (code 8) and Updater 0.1.6.
- v1.0.2 signing correctly rejected changed Root bytes at the old version; that draft was never shipped.

## v1.0.2 — Unpublished candidate (superseded by v1.0.3)

- Fix Home return animation, focus, AirPlay opening and startup app refresh (#25/#26).
- Recover Helper monitoring/startup and late LG Home takeover; add guided one-report diagnostics (#29/#31, issue #12).
- Improve Key Server diagnostics, unfinished removal recovery, Helper process preflight and visible installer errors (#32/#33, issues #21–24).
- Candidate components: cytv 0.2.16, Home 1.3.8, Helper 0.6.18, Android 0.1.7-preview (code 8); Root and updater unchanged.
- Operator accepted the candidate; pin the exact new Helper archive and Home rollback before signing. See docs/RELEASE-1.0.2.md.

## v1.0.0 — Stable distribution

- Ship the existing No-root and Root features as a stable, model-scoped distribution; retain documented firmware and recovery limitations.
- Include cytv 0.2.14 with bounded waiting for old Root processes before uninstall completes, preventing a false removal failure.
- Keep Home 1.3.6, Helper 0.6.17, Root 0.1.10 and Updater 0.1.5 unchanged from v0.10.10.
- Refresh Android to 0.1.5-preview (code 6) with the current installer; Android and Developer Mode renewal retain preview/Beta status.
- Record the bounded release checks in docs/RELEASE-1.0.0.md.

## v0.10.10 — C4 state recovery and maintenance screens

- Include the Home/Root compact settings and desktop/Android maintenance improvements merged since v0.10.9.
- Bump cytv to 0.2.13, Home to 1.3.6, Helper to 0.6.17, Root to 0.1.10 and Android to 0.1.4-preview (code 5); keep Updater 0.1.5.
- Pin the exact Home 1.3.5 rollback and verify unchanged Helper protocols/executables before signing the new Helper baseline.

- Keep No-root SSAP available with a protected key in a trusted installer-owned state directory even when directory chmod is denied.
- Recover boot-expanded foreign-owned pairing keys through private staging and atomic replacement, preserving the shared group used by app inventory; keep SSAP blocked if protection fails.
- Treat app-list permission failures separately from pairing-key security and add modeled multi-UID regressions plus real Linux ownership checks in CI. C4/C3 hardware validation remains pending.

## v0.10.8 — Current No-root updates and stable update controls

- Read the installed Home manifest version for No-root startup health instead of reporting 1.2.2.
- Publish signed Home 1.3.4 / Helper 0.6.16 metadata with the exact Home 1.3.3 rollback package.
- Require both edition feeds, Helper compatibility and rollback package hashes to match release metadata before publication.
- Confirm Root startup automatically after profile/render readiness; keep the pre-install confirmation and recovery safeguards.
- Keep Root polling in the background without disabling controls or moving remote focus, and reserve status space to avoid shifting buttons.
- Components: cytv 0.2.11, Home 1.3.4, Helper 0.6.16, Root 0.1.8 and No-root Updater 0.1.5.

## v0.10.8 — No-root ARM32 runtime detection

- Verify the TV shell ELF ABI instead of rejecting aarch64 kernels that run ARM32 userspace.
- Reject unconfirmed, non-ARM and ARM64-only shell environments before package installation.
- Add allowlisted TV kernel architecture, userland ABI and ARM32 verification results to diagnostic reports.
- Add architecture and diagnostic privacy regressions; translate the clearer failure message in ten languages.
- Components: cytv 0.2.11; Home 1.3.3, Helper 0.6.16, Root 0.1.7 and No-root Updater 0.1.5 are unchanged. Reporter hardware confirmation for issue #15 remains pending.

## v0.10.7 — Root update readiness repair

- Exclude the Add app action tile from restored-application readiness checks.
- Derive expected visible tiles from the same saved-layout model as Home, including hidden applications.
- Keep genuine missing, incorrect or unrendered application tiles blocked.
- Include the Root feed publication guard and post-publication CI verification.
- Components: cytv 0.2.10, Home 1.3.3, Helper 0.6.16, Root 0.1.7 and No-root Updater 0.1.5.

## v0.10.6 — No-root SSH authentication compatibility

- Fix No-root RSA public-key authentication for Developer Mode SSH servers that accept ssh-rsa but omit server-sig-algs.
- Add real loopback SSH regression coverage for first connection and cached keys; verify Root still supports RSA SHA-2 authentication.
- Components: cytv 0.2.9; Home 1.3.3, Helper 0.6.16, Root 0.1.6 and No-root Updater 0.1.5 are unchanged.
- Addresses the likely authentication cause in issue #15; confirmation on the reporter’s TV is pending.

## v0.10.5 — Clearer updates, recovery and installer versions

- Hide older release versions and notes in Root Software updates.
- Open a separate Recovery screen showing the saved rollback version or why rollback is unavailable; Back returns to updates with remote focus restored.
- Name the exact rollback version in the confirmation dialog and translate the new messages in all ten languages.
- Show installed → bundled component versions in cytv before installation, with explicit first-install, reinstall and downgrade labels.
- Components: cytv 0.2.8, Home 1.3.3, Helper 0.6.16, Root 0.1.6 and No-root Updater 0.1.5.

## v0.10.4 — Root Home at startup and clearer settings

- Preserve the confirmed Root Home profile during normal shutdown so webOS opens it as the first app on the next startup. Keep independent boot recovery and explicit emergency restoration.
- Treat a retained shutdown profile as a successful observer exit.
- Clarify that Open LG Home is a one-time visit, and add explicit install/recovery confirmation dialogs with complete translations.
- Refresh the shared installation, edition, maintenance and recovery guides.
- Components: cytv 0.2.7, Home 1.3.3, Helper 0.6.16, Root 0.1.5 and No-root Updater 0.1.5.

## v0.10.3 — Redesigned desktop setup and source installation fixes

- Release cytv 0.2.6 with visible setup stages, Root/No-root cards, keyboard focus and collapsible maintenance actions.
- Include the localized setup, Root recovery/removal and Home startup fixes from the v0.10.2 source tag.
- Repair permissions in the current Helper package instead of a hardcoded old IPK.
- Honor Zig from ZIG/PATH in Termux without requesting the unavailable Android Python distribution.
- Components: cytv 0.2.6, Home 1.3.2, Helper 0.6.16, Root 0.1.4 and No-root Updater 0.1.4. C5/webOS 26 remains under investigation.

## v0.10.2 — Localized setup and complete project removal

- Complete cytv translations for interrupted setup, reinstallation, removal and recovery messages across all supported languages.
- Reconcile interrupted Root setup in the installer and verify the updater connection before activation.
- Remove Root Updater, its service, startup hook and retained app permissions through cytv; preserve inactive recovery records.
- Include the Home startup and bounded standby recovery fixes described in issue #10, plus ten-language TV and installer localization. QNED80T feedback is still pending.
- Versions: cytv 0.2.5, Home 1.3.2, Helper 0.6.16, Root 0.1.4 and No-root Updater 0.1.4.

## Unreleased — C4 helper follow-up

- Restore and verify known state permissions at runtime; avoid SSAP use if permission repair fails.
- Wait up to five seconds for held startup keys without grabbing the remote or losing heartbeat/stop handling.
- Preserve intentional LG Home after long Back while retaining short Home and normal app-exit returns.
- Distinguish EIM rejection, command failure, empty reply and confirmed registration.
- Add permission, startup relay, Back/controller and setup regressions. C3/C4 hardware verification remains pending.

## v0.8.2 — Root Edition 0.1.1 updates and recovery

- Add Root Settings → Software updates with an independent Root Updater and signed, edition-specific metadata.
- Preserve applications, embedded icons, inputs, configuration and tile order across compatible application updates.
- Add a durable one-attempt rollback after verified installation and failed launch confirmation; unknown installer outcomes remain blocked.
- Keep recovery/updater infrastructure pinned and require one-time computer setup; legacy Root Stable 0.1.0 needs supervised infrastructure migration.
- Validate a real Settings update and automatic timeout rollback on OLED55C3RLA / 43.21.71 using isolated lab identities; retain the exact-artifact and power-loss limitations.
- Retain No-root v0.8.1 packages and signed update metadata unchanged in the shared latest release.

## Root Stable 0.1.0 — OLED55C3RLA / 43.21.71

- Add a separate Root launcher, installer and recovery service without changing the stable No-root launcher, helper or updater implementation.
- Route short Home and confirmed Back exits through system Home; no LG flash observed on the tested OLED55C3RLA / 43.21.71.
- Add protected 60-second trials, explicit Keep Root mode, persistent intent and normal software-reboot reactivation.
- Add Settings exit and independent triple-short-Home emergency restoration, with reciprocal health checks, bounded recovery and owned startup registration.
- Import existing validated profile data into the candidate without changing the production profile.
- Fix atomic heartbeat read races and serialize boot callbacks; retain strict freshness and file-safety checks.
- Document both editions, installation, recovery, removal and hardware evidence. The fixed bundle passed quick standby, failsafe, clean removal/reinstall and fault recovery checks. Cold-power testing is deferred; an isolated first-attempt emergency-gesture miss remains unexplained. See the scoped Root Stable release notes.

## v0.8.1 — signed Home updates and recovery

- Add a separate signed-update and recovery package, portable Home profiles, and Software updates in Settings.
- Pause renewal Beta automatically and restore its prior preference after verified installation or rollback; Home Helper remains unchanged.
- Recheck signed offers after service restarts, subscribe to terminal installer responses, and keep ambiguous bus failures in recovery without starting another install.
- Add scoped permission setup/removal and fix remote navigation across disabled controls.
- Verify published signed Home update and rollback on OLED55C3RLA / 43.21.71, preserving apps, remote controls and disabled renewal.
- Grant the renewal service only canonical Activity Manager create/cancel methods; recover safely from a denied pause before installation.
- Refresh Recovery when reopened and reset restore confirmation.

## Unreleased — one-script installation

- Add `./install.sh <TV IP>` for macOS/Linux: local tool setup, Developer Mode SSH pairing, app sync, package build/install, verified helper configuration and helper launch.
- Install Zig 0.14.1 and webOS CLI 3.2.6 locally without sudo or global tool installation.
- Stop on setup errors, reject empty app inventories and protect existing CLI profiles from accidental retargeting. TV pairing approvals and hardware checks remain manual.

## v0.7.1 — macOS build and verified setup transfers

- Build on macOS: `fix-package-data.py` rewrites the ipk in Python; BSD `ar r` reduced the helper package to a 96-byte symbol-table archive.
- `configure-tv.sh` works with `@webos-tools/cli` 3.x, which offers `ares-push` only for the ose/apollo profiles: files are staged over `ares-novacom`, checked by SHA-256 and actual permissions, and atomically replaced; CLI errors are reported without echoing the key.
- `configure-tv.sh` checks the EIM response and warns when early input restoration is not registered.
- Compatibility: community test on LG OLED55C46LA (C4), webOS 24.

## v0.7.0 — Home 1.1.0, Home Helper 0.6.13

- Add opt-in Developer Mode session auto-renewal **Beta**, disabled by default.
- Add Home settings with session status, confirmed-renewal timestamp, disable control and sanitized diagnostics. LG TV settings remain accessible.
- Include a separate on-TV renewal service with direct LG HTTPS, bounded retries, persisted cooldown and a persistent hourly task.
- Home Helper, native key interception, emergency exit and watchdog are unchanged.
- Real renewal on stock unrooted TVs is awaiting feedback. Monitor the official timer; see [Beta guide](docs/DEVELOPER-MODE-BETA.md).


## v0.6.12 — first public release

Launcher 1.0.11; native helper 0.6.12.

- Skip the standby recovery launch when webOS already reports the launcher in front.
  Two quick power cycles passed with arrows, OK and short Home working.
- Include the tested network shortcut, system splash image and removal of the
  redundant internal loader.
- Preserve the native Home relay, watchdog and persistent long-Home emergency stop.
- Supply English setup, recovery and build instructions.
- Load watched application IDs from locally generated configuration instead of a
  developer-specific list.

Known issues: early cold-boot black interval; LG Home flash after Back exit;
unverified compatibility outside the listed C3 setup. The draft recovery-dialog
UI is not included in this release.
