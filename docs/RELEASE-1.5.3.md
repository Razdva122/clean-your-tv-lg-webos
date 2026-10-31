# v1.5.3 — Themes, Root startup and recovery

Status: unpublished preparation superseded by [1.5.4](RELEASE-1.5.4.md). Publication stopped before signing/upload because the exact Helper approval record was stale. No stable 1.5.3 was delivered. All 17 implementation PRs are inherited by 1.5.4. Full candidate
[41185537404:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41185537404)
builds product source `f4bab0ea60c825994445b0b63625f5fd734bff4e`.
See the [signed Root QA and release decision](history/2026-10-31-release-1.5.3-signed-root-qa.md)
for exact package hashes, startup/controls observations and accepted limitations.
Historical builds 41118810865:1 and earlier retain their original scope.

## Changes

- #199 (#198): hold the receiver service activity until its session ends, so the
  standalone service idle timer cannot close the HTTP listener while a PIN waits.
  Integrated in `release/next`; normal delivery and original webOS 5/No-root
  confirmation remain pending.
- #205: #204 owned native EIM first-screen startup and cleanup;
  #202 automatic recovery preserving update Home resumption; #203 bounded
  compressed maintainer SSH admission; refreshed Classic README main screenshot
  and three built-in theme previews. [Batch verification](history/2026-10-31-release-1.5.3-native-startup-batch.md) records final PR CI and limits.
  The EIM enabled-mode C3 experiment is not final package acceptance or a fix for
  #171. Additional shutdown-decision diagnostics preserve existing safety policy.
  Actual signed QA still found Home preference loss on forward update and active
  rollback; #202 remains deferred, with normal explicit enable as the workaround.

- #193: refresh the Ribbon README screenshot and link theme browsing to the main
  interactive preview. Remove the standalone public theme catalogue page and its
  navigation link; on-TV Showcase and offline author review remain available.
- #192 (#152): avoid false active-Helper detection when legacy grep ignores exact
  matching, preserving real-process and uncertain-state guards. Add bounded LS2
  diagnostic categories. Original EF950V installation/control failures remain
  unresolved; reporter history and target-device confirmation are still needed.
- #189: use smaller complete GitHub job pages for signed Root QA admission while
  retaining exact-attempt, source, package and signature verification.

- #191: separate Appearance layout/app controls from Themes, add ID-first theme installation, show the effective Columns count and place language choices directly in their category. Remote navigation, delayed-status focus and twelve-language browser checks passed; physical TV acceptance remains pending.

- #188: bundle Ribbon for offline selection in both editions, with theme-driven
  scenic ribbon geometry, slanted cards and shortcut placement. Navigation enters
  Settings at the visible left edge, including after the application window moves.
  The existing Classic default remains. Theme authoring uses the optional
  `ribbon-layout-v1` capability; older Home versions reject unsupported imports
  before replacing the selected theme. Physical remote acceptance is pending.

- #175 and #183 (#160, #164): visible prerequisite results in console, desktop
  and Android, retained failure rows and diagnostic-report guidance. Root still
  requires TV Node.js 8+ and supported Python/Home interfaces. This improves
  diagnosis, not the original reporters' unsupported runtime or connection.
- #176 (#170): fixed-layout themes preserve hidden Columns geometry during
  Appearance Apply; hidden controls remain unavailable to pointer, keyboard and
  accessibility navigation. Installed-package acceptance is still required.
- #181 (#152): compile Helper for Node 0.10.25+, use descriptor-safe pairing-key
  reads and compatible vendored WebSocket calls. Published baseline pairing and
  emergency/watchdog guards remain authoritative. EF950V installation, input,
  power behavior and rollback remain unverified until actual target-TV results.
- #177 (#133): isolate maintainer read-only admission from retained Python code
  and obtain the original candidate from its authenticated operation. This does
  not perform individual recovery or add a Settings-only firmware adapter.
- #180 (#171): record guarded wake refusal stages and bounded private power-stream
  outcomes. This is diagnostic coverage, not a fix for automatic Home after wake.
- #117 (#116): explain exact Homebrew exec denial in twelve languages, preserve
  original request IDs and inspect before retry. Supported upstream prerequisite,
  exact-artifact acceptance and public Homebrew promotion remain pending.

## Component versions

| Component | Published 1.5.2 | Candidate 1.5.3 | Reason |
| --- | --- | --- | --- |
| cytv | 0.6.0 | 0.6.1 | Changed preflight, visible checks and recovery tooling |
| Home | 1.6.0 | 1.6.1 | Ribbon, shared layout module and Appearance CSS |
| Home Helper | 0.6.20 | 0.6.21 | Node 0.10.25/runtime and pairing-key handling |
| Root | 0.6.1 | 0.6.2 | Shared UI, Home resume, native startup and infrastructure diagnostics |
| Both edition Updaters | 0.3.3 | 0.3.4 | Both embed changed Appearance CSS |
| Android / versionCode | 0.5.0 / 15 | 0.5.1 / 16 | Changed UI/native replay/bridge and embedded payload |
| System supervisor | 1.1.2 | 1.1.2 | Executable supervisor/IPK closure unchanged |

Home, Helper, Root/infrastructure, both Updaters and all computer/Android installers
must rebuild together after the batch is integrated. The changed Helper runtime requires a new
version; published 0.6.20 must not be replaced with different bytes. Existing supervisors remain pinned;
normal admission, signatures and minimum-supervisor checks remain unchanged.

## Delivery and acceptance limits

The maintainer explicitly accepted release without the physical No-root Helper
0.6.20 to 0.6.21 transition test. This exact path remains untested; package,
signature, control and rollback regression checks remain required. The older
0.6.19 to 0.6.20 record is not reused as a new passing test.

The signed C3 record shows first-screen Clean on one same-session standby and
one true cold boot, controls/audio, profile retention, native Off/emergency and
rollback cleanup. #171's earlier different-session retained-intent failure remains
unresolved follow-up; no ENODEV exemption or automatic fault re-enable was added.
The maintainer requested proceeding with the tested source and recorded known
limitations; this is not universal firmware/TV compatibility.

Final Android APK checks and original-signer v1.5.2/code15 to code16 update passed
on an isolated Android 15/API35 ARM64 emulator without uninstall or loss of four
synthetic private files. Physical phone/TV operation and native instrumentation
were not rerun. The independent Homebrew Installer remains unreleased and its
promotion disabled. Other users' runtime/recovery reports remain unresolved where
only diagnostics or partial improvements ship.

Mandatory complete CI, final artifact/signature and verified publication checks
remain in force; a merge alone does not establish shipping.

## Accepted remaining limitations

The maintainer deferred further fixes/retests for [Home preference loss during
update/rollback (#202)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/202)
and [stale Home settings after emergency/resume (#206)](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/206).
After a transition, explicitly enable Change Home in normal settings if needed;
close and reopen Settings if its toggle is stale, then wait for the Clean status.
These are known failures, not successful automatic Home resumption.
The [signed C3 QA record](history/2026-10-31-release-1.5.3-signed-root-qa.md)
separates startup/controls passes from failures and untested paths.
