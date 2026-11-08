# v1.13.0 — passive IR Home and safer continuation

Unpublished preparation for [release PR #425](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/425), after published v1.12.1.
No complete candidate build or physical acceptance is selected. The published
download buttons still serve v1.12.1. Do not install these preliminary packages
as a verified release or infer that an integrated fix resolved a reporter's TV.

## Changes

- Allow a new Root or No-root setup after verified full removal (#436). Retire
  the completed removal's destructive authority, preserve only inactive recovery
  fences, and keep old retries from deleting a later installation. Root-SSH
  No-root setup binds its original plan under the same locks. Physical full
  uninstall/reinstall and P00 compatibility acceptance remain pending.
- Select owned Developer Mode jail storage when its temporary directory cannot
  host private observer evidence (#435, #409). Recovery stays bound to the original
  location; unsafe or ambiguous roots refuse setup. Existing temporary-space and
  full-restart requirements remain. Physical reporter confirmation is pending.
- Add passive standard IR short-Home handling in No-root Helper, based on
  ferrets6's contribution and the reviewed safety batch (#419/#428, #207).
  Home opens after approximately 700 ms, possibly after LG Home flashes. Held
  Home stays with webOS. Stop, Home-control Off, relay recovery and overflow
  discard stale gestures; fresh triple-Home escape remains. Actual ordinary
  Developer Mode input access and physical remote compatibility are unverified.
- Prevent a closing heartbeat socket from crashing Helper (#415, #414).
  An already stopped Helper still needs explicit Start Helper and confirmation;
  installing an update does not clear emergency-stop state.
- Preserve an exactly owned Root Home route while arming fresh startup protection
  (#427, #422). Actual physical Home, emergency and power acceptance is pending;
  the published v1.12.1 failures remain recorded separately.
- Retry exact transient Root OTA profile permission refusals within the existing
  startup budget (#421, #351). Health still requires legitimate profile, tile and
  presented-frame evidence. Final signed early-start, public-feed and rollback
  acceptance remain pending; original permission-race causality is unconfirmed.
- Give visible Root apps priority within the existing icon budget; refresh a
  newly pinned missing icon (#423, #416). Catalog order and size limits remain.
  Keep legacy clocks compact with an HH:MM fallback (#429, #311).
- Remove proven never-activated Root installations without Home APIs (#424,
  #101). Continue the same approved removal after recoverable connection errors,
  recheck a running Helper before pairing, and offer separate full removal for
  legacy Root Updater remnants (#431). Unknown cleanup remains pending; explicit
  Root removal, required restart and a later new setup remain separate actions.
- Retain fixed catalog/input failure categories and bounded Luna codes (#426,
  #397), activation-recovery refusal stages (#430, #355), control-restoration
  boundaries (#432, #418), socket causes (#433, #420) and aggregate No-root icon
  counts (#429, #311). No new retry, probe, permission or diagnostic recovery
  authority is added. These diagnostic improvements do not resolve the original
  installation, connection or recovery reports.

## Versions and packaging

| Component | Published v1.12.1 | Selected candidate v1.13.0 | Reason |
| --- | --- | --- | --- |
| Home FHD/HD | 1.13.1 | 1.13.2 | Clock fix and shared catalog refresh |
| Home Helper | 0.7.5 | 0.8.0 | New passive IR controls and heartbeat fix |
| cytv | 0.13.1 | 0.14.0 | Removal/reinstallation continuation and diagnostics |
| Android / versionCode | 0.12.1 / 27 | 0.13.0 / 28 | Shared operations, UI and embedded packages |
| Root / infrastructure | 0.13.1 | 0.13.2 | Startup routing, OTA readiness, icon allocation and removal |
| Both edition Updaters | 0.5.3 | 0.5.4 | Shared locales and embedded Root coordinator closure |
| Fresh System / protocol | 1.2.6 / 1 | 1.2.7 / 1 | Changed shared runtime/infrastructure closure |

All desktop/Android installers and normal/Beta Root payloads need rebuilding.
The actual builder's historical Helper byte pins cover 0.6.16/0.6.17/0.6.19,
not 0.7.5. A new source-built Helper version is required regardless: release
assembly refuses changed bytes under an unchanged published version. New 0.8.0
requires genuine published Home 1.13.1/new Helper compatibility and rollback
evidence matching its canonical archive hash before full candidate dispatch.
The old 0.7.4→0.7.5 approval does not cover this transition.

Existing System supervisors remain pinned; component OTA does not replace them.
Explicit replacement still admits only installed 1.1.0/1.1.1, not 1.1.2/1.2.x.
Root Beta remains a separate exact-Node-0.12.2 payload with ordinary OTA disabled.
C1 compositor admission and Homebrew Installer promotion retain their independent
unverified gates; no Homebrew release approval is selected. Android retains its
application ID and persistent signer; exact code27→code28 APK upgrade acceptance
is pending. No new general firmware or phone compatibility is claimed.

## Validation and remaining gates

The [preparation record](history/2026-11-08-release-1.13.0-preparation.md)
records actual package hashes, host checks, documentation review and blockers.
[Integration evidence](history/2026-11-08-next-candidate-integration.md) retains
reviewed PR checks; it is distinct from full frozen-candidate validation.
The [bounded physical checklist](history/2026-11-08-next-candidate-physical-checklist.md)
separates the mandatory pre-dispatch Helper probe from later exact-build
acceptance. Public-feed verification cannot pass against an unpublished QA offer.
No TV was contacted or changed in this preparation task.
