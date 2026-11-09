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
- LG C3 — No-root — webOS 26
- LG C5 77″ — No-root
<!-- compatibility-reports:end -->

These are reports for the listed configurations, not a guarantee for every firmware or test case. Unreported versions are omitted. Earlier failures and untested paths remain in the evidence below.

## What has been tested

| Configuration | Evidence and limits |
| --- | --- |
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
- Developer Mode expiry can remove sideloaded apps. Automatic renewal is optional Beta; real renewal on unrooted TVs remains unverified. Monitor the official timer.
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
