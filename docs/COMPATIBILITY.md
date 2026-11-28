# Requirements and known limits

> **Release 1.9.0:** see [versions, tested scope and recovery limits](RELEASE-1.9.0.md). C1 Beta is fresh-install only, selected automatically in the common installer; normal OTA is unavailable and physical C1 acceptance is pending. Historical results below retain their original artifact scope.

> See [1.6.0 versions, installer changes and limits](RELEASE-1.6.0.md) and the [dated acceptance scope](history/2026-11-02-release-1.6.0-final-acceptance.md). Obtain available packages from [GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases).

[Documentation](README.md) · [Choose an edition](EDITIONS.md) · [Install](INSTALL.md)

Check the access method and runtime first. Meeting these requirements or installing
an IPK does not prove that Home, recovery or startup works on a particular TV.

## TV requirements

<a id="next-installer-shared-experimental-home-backend"></a>

### Shared experimental Home backend

The installer also packages the existing guarded KeyFilters Home
alternative for Node 0.12.2 Root Beta. Ordinary Root and Beta share the same
selector and capability checks: vendor Qt JavaScript filters, ARM32 native Home
and compatible input/recovery are required when System Profile is explicitly absent.
SDK numbers are recorded, not used as an allowlist. A KeyFilters setting alone
is insufficient: firmware with an in-compositor Home ribbon or another stock
Home implementation is refused. Compatibility on the #410 TV is unconfirmed. Both
experimental Home variants retain fresh-install restrictions and disabled OTA.
See [backend and verification limits](development/C1-NATIVE-GATE.md#shared-root-runtime-variants-unpublished-beta-packaging).

### Release 1.12.0: legacy Root choices

The 1.12.0 installer includes a separate, explicitly selected **Root Beta
for exactly Node.js 0.12.2**. It also offers **No-root using existing root SSH**
when ordinary Root rejects an identified older Node version. The fallback keeps
Home/Helper's own runtime and ARM32 checks; it does not install Developer Mode
over root. Unknown or unreadable Node output does not authorize either path.

Beta leaves system Node unchanged, retains Python/vendor module/Home checks and
blocks ordinary OTA. Host checks do not establish native LS2 registration, Home,
emergency, audio, power or rollback compatibility on any TV, including #383.
For release1.12.0 the maintainer explicitly deferred physical Beta testing;
this is an unverified Beta limitation, not compatibility evidence or a passing
#383 outcome. [Selected checks and limits](history/2026-11-07-release-1.12.0-scoped-qa.md). See [implementation and testing](development/ROOT-NODE-PROTOTYPE.md#unreleased-installer-beta).

Release 1.5.4 includes Home Helper 0.6.21 with TV Node.js 0.10.25+ support for
[#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152).
Root still requires Node.js 8+. Host runtime tests do not establish EF950V
launcher, input, Home routing, standby, cold-boot or recovery compatibility.
The physical No-root Helper 0.6.20→0.6.21 transition remains untested under the
maintainer's explicit release decision; see [scoped QA](history/2026-10-31-release-1.5.3-signed-root-qa.md).
Do not bypass a failed runtime gate.

| | No-root | Root |
| --- | --- | --- |
| Access | Active LG Developer Mode, Key Server and local networking | Existing root, trusted root SSH and compatible Homebrew services |
| TV runtime | Node.js 0.10.15+ for the compiled Helper (published 0.8.0) | Node.js 8+ and Python 3.9+ with the required modules |
| Input | Compatible remote devices and native input access | Supported ARM32 userspace and compatible Magic Remote input |
| Ongoing requirement | Keep Developer Mode active and Helper pairing/networking available | Keep independent recovery services and their referenced runtime intact |

Root does not obtain root or flash firmware. Do not install Developer Mode over
existing root. On eligible ARMv7 TVs, the installer can prepare [private Python](OPTIONAL-PYTHON.md);
it does not replace system libraries or make unsupported firmware compatible.
Do not bypass failed input, ownership or runtime checks.

Computer/phone requirements: [desktop](DESKTOP_INSTALL.md), [Android](../android/README.md),
or [source/manual tools](MANUAL_INSTALL.md). Desktop packages and Android have
separate OS/device acceptance; a successful computer build is not a TV test.

<a id="webos-1x-runtime-floor-unreleased"></a>

## webOS 1.x runtime floor (1.8.2)

LG documents [Node.js 0.10.15 for webOS TV 1.x](https://webostv.developer.lge.com/develop/guides/js-service-basics#supported-nodejs-version).
Published 1.8.2 admits No-root Helper 0.7.4 on Node.js 0.10.15+. Earlier v1.7.1
installers required 0.10.25+. Exact 0.10.15 host checks cover the compiled Helper;
see the dated evidence for the original baseline and actual tested cases. Older/unknown runtimes still stop
before installation. Root continues to require Node.js 8+.

This does not establish compatibility on the reported 32LB650V-ZN or 49UB8500-UA.
Their actual Node versions have not yet been measured in the reports. LG lists
[WebKit 537.41 for packaged apps on webOS 1.x](https://webostv.developer.lge.com/develop/specifications/web-api-and-web-engine#web-engine),
so UI/native-input/remote acceptance is separate from Node compatibility.
Do not install a replacement system Node or bypass the existing runtime/input
checks. A standalone Home IPK or historical Home-only update cannot provide
Helper's Home-button interception; the current complete installer has no
Helper-free first-install mode promising that behavior.

[Exact hashes, runtime cases, packaging and limits](history/2026-11-04-webos1-node-floor.md).

## User-reported working TVs

The catalog includes specific Home button checks, general reports of operation
and partial results. A partial result covers a launcher observed running with a
documented limitation or workaround. The [device catalog](compatibility-reports.json)
records the tested steps, unresolved faults and configurations for each entry.
When a reported platform name conflicts with the installed SDK version, the
catalog groups the result by the SDK and records the other name in the report.

<!-- compatibility-reports:start -->
- OLED65G19LA — No-root — firmware 03.53.45 — webOS SDK 6.5.3 — v1.5.4
- OLED55B19LA — No-root — firmware 03.53.45 — webOS 6; SDK 6.5.3 — v1.11.0
- OLED55G36LA — No-root — firmware 23.25.40 — webOS SDK 9.2.2
- OLED55B36LA — No-root — firmware 33.31.75 — webOS SDK 10.3.2
- OLED83G36LA — No-root — firmware 43.21.71 — webOS SDK 11.2.0 — v1.13.0
- 55SK8100PLA — No-root — firmware 05.50.70 — webOS 4; SDK 4.4.0
- 50NANO80ASA — No-root — firmware 33.31.80 — webOS 25; SDK10.3.2
- UN70006LA — No-root — firmware 04.64.00 — v1.2.0
- OLED65C3PUA — No-root — firmware 43.21.96
- OLED55C3RLA — Root — firmware 43.21.71 — webOS SDK11.2.0 — v1.13.0
- 55UR91006LA — No-root — firmware 33.31.75 — webOS SDK10.3.2 — v1.11.0
- OLED55C2PUA — No-root — firmware 33.31.68 — webOS 10.3.1 / build 3006
- OLED42C24LA — No-root — firmware 33.31.68 — webOS 10.3.1 — v1.17.0 — owner confirmed removal through Recover, fresh setup, short Home and automatic Helper restart after remote off/on.
- OLED42C24LA — No-root — firmware 43.21.94 — webOS SDK 11.2.0 — v1.21.0 — owner confirmed an in-place upgrade from Helper 0.8.4, short Home after explicit Start Helper, and automatic startup and short Home after a full remote restart.
- LG C3 — No-root — webOS 26
- LG C5 77″ — No-root
- 43UQ75003LF — No-root — firmware 04.60.92 — webOS 7.6.0 — owner reports successful installation on Windows 11; individual checks were not described. [Owner report #654](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/654)
- OLED55C37LA — Root — firmware 23.20.54 — webOS 24; SDK 9.2.1 — v1.25.0: owner confirmed verified removal after interrupted setup, working LG Home/remote and preserved Homebrew/root. Original installation support remains unresolved. [Recovery result #133](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/133#issuecomment-7035596176)
- OLED65C1PSA — Root — firmware 03.53.45 — webOS SDK 6.5.3 — v1.24.0 — owner confirmed removal through Review recovery options after an interrupted removal and TV restart, successful Root reinstallation, and physical short Home from another app opening CYTV Home. [Owner confirmation #418](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/418#issuecomment-6987290015)
- 32LB650V-ZN — No-root — firmware 05.05.90 — webOS 1.4.0 — [partial result (#283)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/283#issuecomment-6724042805)
- 43NANO766QA — No-root — firmware 04.60.91 — webOS 22 — v1.5.4 — [partial result (#227)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/227#issuecomment-6573089997)
- 43UM7600PLB — No-root — firmware 05.40.97 — webOS 4.5 — [partial result (#686)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/686)
- 43UP751C0ZF — No-root — firmware 03.53.45 — webOS SDK 6.5.3 — [partial result (#687)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/687)
- 49NANO80PNA — No-root — firmware 04.64.00 — webOS SDK 5.6.2 — v1.0.0 — [partial result (#20)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/20#issuecomment-6388040635)
- 49UJ651V-ZA — No-root — firmware 06.10.75 — webOS 3.5 — v1.12.1 — [partial result (#47)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/47#issuecomment-6722365004)
- 49UJ750V — No-root — firmware 06.10.65 — webOS 3.5 — v1.0.1 — [partial result (#20)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/20#issuecomment-6390518287)
- 50NANO756PA — No-root — firmware 03.53.45 — webOS 6; SDK 6.5.3 — [Home button verified (#106)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/106)
- 55LB652V-ZA — No-root — webOS 1.4.0-2536 — v1.12.0 — [partial result (#311)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/311#issuecomment-6711772795)
- 55NANO81ANA — No-root — firmware 04.64.00 — webOS 5.6.2-21 — v1.0.1 — [partial result (#21)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/21#issuecomment-6388756143)
- 55UK7500PSA — No-root — firmware 05.50.70 — webOS SDK 4.4.0 — v1.20.4 — [Home button verified (#534)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/534#issuecomment-6828871492)
- 55UM7450PLA — No-root — firmware 05.40.97 — webOS SDK 4.10.0 — v1.23.0 — [partial result (#692)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/692#issuecomment-6956439664)
- 55UP7000PUA — No-root — firmware 03.25.45 — webOS 6.2.1 — v1.14.0 — [partial result (#207)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/207#issuecomment-6749035244)
- 55UQ7400PSF — No-root — webOS 22 — v1.16.0 — [partial result (#500)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/500)
- 60UJ6050-UA — No-root — firmware 06.10.55 — webOS SDK 3.9.0 — [owner reported operation (#410)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/410#issuecomment-6882932369)
- 65QNED80SRA — No-root — webOS 25; 10.3.2-33 reported — v1.4.0 — [partial result (#140)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/140)
- 65QNED80TSA — No-root — firmware 33.31.75 — webOS SDK 10.3.2 — [partial result (#10)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/10)
- 65UM7470PSA — No-root — webOS 4.5 (build 4.10.2-29) — v1.16.0 — [partial result (#499)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/499)
- 75NANO80TSA — No-root — firmware 33.31.75 — webOS 25; SDK 10.3.2 — v1.4.1 — [partial result (#155)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/155)
- LM6370PSB — No-root — firmware 05.40.97 — webOS 4.5 — [partial result (#68)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/68)
- OLED42C2PSA — Root — firmware 33.31.68 — webOS 10.3.1-3006 (SDK 10.3.1) — v1.15.0 — [partial result (#355)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/355#issuecomment-6766778759)
- OLED48B46LA — Root — firmware 33.31.75 — webOS SDK 10.3.2 — [partial result (#282)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/282#issuecomment-6657735674)
- OLED48C24LA — No-root — firmware 43.21.74 — webOS SDK 11.2.0 — [partial result (#59)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/59)
- OLED48C55LA — No-root — firmware 43.21.77 — [owner reported operation (#472)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/472#issuecomment-6748054482)
- OLED55C11LB — No-root — firmware 03.53.45 — webOS 6.0 — [partial result (#54)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/54)
- OLED55C14LB — No-root — firmware 03.53.45 — webOS 6 — v1.21.0 — [owner reported operation (#608)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/608)
- OLED55C16LA — No-root — firmware 03.53.45 — [owner reported operation (#454)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/454#issuecomment-6900707375)
- OLED55C35LA — No-root — webOS 26 (build 11.2.0-3711) — [owner reported operation (#664)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/664)
- OLED55C46LA — Root — firmware 33.31.68 — webOS 10.3.1 — v1.13.0 — [owner reported operation (#416)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/416)
- OLED55C47LA — No-root — firmware 33.31.61 — webOS SDK 10.3.1 — v1.20.6 — [owner confirmed short Home opened Clean Your TV Home after fresh setup (#635)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/635#issuecomment-6877112869)
- OLED55C5ELB — No-root — firmware 43.21.77 — webOS 26 — v1.24.0 — [partial result (#715)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/715)
- OLED55C9PLA — No-root — firmware 05.30.25 — webOS 4.5 / SDK 4.9.0 — v1.20.7 — [partial result (#626)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/626#issuecomment-6881622004)
- OLED55G59LS — No-root — firmware 43.21.96 — v1.20.5 — [owner reported operation (#529)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/529)
- OLED65C11LB — Root — firmware 03.53.45 — webOS SDK 6.5.3 — v1.29.1 — [Home routing verified after one standby/wake cycle (#741)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/741#issuecomment-7225725297)
- OLED65C27LA — Root — firmware 23.20.74 — webOS 9.2.1-2617 — v1.29.1 — [Home routing verified after three standby/wake cycles (#741)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/741#issuecomment-7218117520)
- OLED65C2PUA — No-root — firmware 43.21.94 — [owner reported operation (#646)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/646)
- OLED65C3LA — No-root — [owner reported operation (#279)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/279)
- OLED65C57LA — No-root — firmware 43.21.77 — webOS SDK 11.2.0 — [partial result (#96)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/96)
- OLED65C5PUA — No-root — webOS 26; SDK 11.2.0-3706 — [partial result (#12)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/12#issuecomment-6401658552)
- OLED65G39LA — Root — firmware 43.21.71 — webOS 26 / SDK 11.2.0 — v1.21.0 — [partial result (#702)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/702)
- OLED77C12LA — No-root — firmware 03.53.45 — webOS SDK 6.5.3 — v1.24.0 — [Home button verified (#720)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/720)
- OLED77C34LA — No-root — firmware 43.21.96 — webOS SDK 11.2.0 — v1.21.0 — [Home button verified (#495)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/495)
- OLED77G5RLA — Root — firmware 43.21.77 — webOS SDK 11.2.0 — [owner reported operation (#588)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/588)
- QNED75URA — No-root — firmware 33.31.75 — webOS 25 / SDK 10.3.2 — v1.20.4 — [Home button verified (#627)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/627)
- UK6400PLF — No-root — firmware 05.50.7 — webOS 4.x — [Home button verified (#599)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/599)
- UM7450PLA — No-root — firmware 05.40.97 — webOS 4.5 — v1.14.0 — [Home button verified (#473)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/473)
<!-- compatibility-reports:end -->

These are reports for the listed configurations, not a guarantee for every firmware or test case. Unreported versions are omitted. Earlier failures and untested paths remain in the evidence below.

## What has been tested

| Configuration | Evidence and limits |
| --- | --- |
| OLED65C11LB (C1) / firmware 03.53.45 / SDK 6.5.3, Root | On v1.29.1, LG Home was visible on wake and the first physical Home press opened CYTV. The diagnostic confirmed Home control enabled and routing armed and healthy. On v1.24.0, Home still opened LG Home after fresh setup and the Home control switch reverted to Off. [v1.29.1 standby/wake (#741)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/741#issuecomment-7225725297), [earlier v1.24.0 result (#389)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/389#issuecomment-6971032548) |
| OLED65C27LA (C2) / firmware 23.20.74 / webOS 9.2.1-2617, Root | On v1.29.1, LG Home Auto Launch showed LG Home on wake. In each of three cycles, the first physical Home press from YouTube opened CYTV and Home control stayed On. Review recovery options and enabling Home control from the TV app resolved the initial activation failure. Cold boot was used for old-install removal. The owner did not test routing after cold boot or reboot. [Owner confirmation (#741)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/741#issuecomment-7218117520) |
| OLED65C1PSA (C1) / firmware 03.53.45 / SDK 6.5.3, Root | v1.24.0 Windows desktop installer using the same saved Root SSH connection. Restore returned LG Home and physical Home opened it. Removal subsequently lost its SSH result and the TV restarted; Review recovery options completed the existing removal, then Root setup completed. Physical short Home from another app opened CYTV Home. Exact remote and newly installed Root component version were not reported. Emergency Stop, audio, standby/wake, AC cold boot and OTA/rollback were not confirmed. [Owner confirmation #418](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/418#issuecomment-6987290015) |
| OLED42C24LA (C2) / firmware 43.21.94, No-root Developer Mode | v1.21.0 (cytv 0.20.9, Home 1.19.0, Helper 0.8.7). The in-place upgrade completed. Short Home worked after explicit Start Helper. A full restart from the remote restored the vendor's `0777` directory mode, and Helper started automatically and routed short Home. Installer platform, exact remote model, emergency Stop, audio, standby, AC cold boot and OTA/rollback were not reported. [Owner confirmation #653](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/653#issuecomment-6910629293) |
| OLED55C3RLA / firmware 43.21.71, Root | [v1.13.0 exact-artifact acceptance](history/2026-11-08-release-1.13.0-artifacts.md): signed update/rollback/forward through retained System 1.2.5, physical short/triple Home, remote off/on, AC cold boot and audible playback. [Exact Helper transition](history/2026-11-08-helper-0.8.0-compatibility.md) is separate No-root evidence. Earlier [1.6.0](history/2026-11-02-release-1.6.0-final-acceptance.md) and [1.4.0](RELEASE-1.4.0-ACCEPTANCE.md) observations retain their original scope. No guarantee of immediate first-screen startup or other models. |
| OLED55C46LA (C4), No-root | Earlier community Helper results have outstanding firmware/input and long-Back confirmation. [Original reports](history/COMPATIBILITY.md#historical-110-hardware-evidence). |
| Specific C5 / webOS 26, BX / webOS 5 and UK6540PTD reports | Unresolved or unverified paths remain on the reporting devices. Positive reports above belong to their own configurations; they do not resolve a different owner’s failure. |
| Other models, firmware and remotes | Unverified until their actual controls and recovery paths are checked. |
| Android | Scoped Android 15 ARM64 / WebView 124 emulator acceptance, including native recovery fixtures; physical phones, minimum-version devices and live phone-to-TV recovery remain unverified. [1.6.0 evidence and limits](history/2026-11-02-release-1.6.0-final-acceptance.md); [readiness details](../android/STABLE-READINESS.md). |

[Release/device evidence](history/README.md) keeps earlier versions and tests in
their original scope. It is not a list of universally supported TVs.

## Limits to understand before use

- **Root OTA from original 1.3.0 to published 1.4.0 is blocked by its pinned infrastructure.** Preserve the aborted journal; do not retry or edit private pins. Guarded compatibility/replacement preparation shipped in 1.5.0; it does not rewrite the incompatible 1.4.0 release or approve a retained operation. [Update guidance](UPDATES.md).
- An unrooted TV is updated through the computer installer. Whole-edition on-TV updates need compatible, separately prepared rooted infrastructure.
- Developer Mode expiry can remove sideloaded apps. Automatic renewal is optional. Check the official timer for confirmation that the session was extended.
- Startup is not instant. Check standby/wake and a true cold boot separately; either can initially show a black screen or LG Home.
- App-specific Back and exit dialogs remain the app's behavior. A return to the launcher can briefly show LG Home. Test emergency exit before daily use.
- No-root Helper needs its SSAP pairing and local network. Some firmware returns no reply to Developer Mode service calls; this does not by itself prove success or rejection.
- Hiding tiles does not uninstall apps or remove system advertisements. Wheel events pass through; wheel-to-tile navigation is not implemented.
- Experimental HDMI sound recovery is off by default. A restored setting does not prove audible sound. Firmware blocking requires its own restart/effective-blocking checks and can block security updates.

If a check fails, stop at [recovery](RECOVERY.md). Share only an approved,
redacted [installation result](FEEDBACK.md); no extra TV changes are needed just
to complete a report.

<a id="120-acceptance"></a>
<a id="historical-110-hardware-evidence"></a>
<a id="current-110-hardware-evidence"></a>
<a id="c4-follow-up-fixes-hardware-verification-pending"></a>

Earlier compatibility tables and C4 implementation details moved to the
[historical reference](history/COMPATIBILITY.md).

<!-- Anchors retained for links to earlier guide headings. -->
<a id="compatibility-and-known-limits"></a>
