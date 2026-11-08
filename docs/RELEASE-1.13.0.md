# v1.13.0 — passive IR Home and safer continuation

Release [v1.13.0](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.13.0), after v1.12.1. Full build42491346675:1 and its exact signed Root artifacts passed the selected C3 acceptance; Android original-signer code27→28 emulator upgrade passed. See the [artifact-bound acceptance and limitations](history/2026-11-08-release-1.13.0-artifacts.md). Integrated partial improvements do not establish that every reporter's device is fixed.

## Changes

- Allow a new Root or No-root setup after verified full removal (#436). Retire
  the completed removal's destructive authority, preserve only inactive recovery
  fences, and keep old retries from deleting a later installation. Root-SSH
  No-root setup binds its original plan under the same locks. The C3 preliminary
  removal/reinstall and published-Home/new-Helper probe passed; final artifact-bound
  acceptance and its scope are linked above.
- Complete clean Root-to-No-root staging and subsequent No-root removal (#439).
  Inert temporary files can be retained with a warning without blocking a new
  setup. Fresh Root capture accepts inventories with an empty optional icon color;
  fresh System setup reopens the launcher to apply its new service permissions.
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
  (#427, #422). Final C3 remote wake, AC cold start, short Home and triple-Home
  escape passed; the earlier v1.12.1 failures remain recorded as history.
- Retry exact transient Root OTA profile permission refusals within the existing
  startup budget (#421, #351). Health still requires legitimate profile, tile and
  presented-frame evidence. Final signed update/rollback/forward and actual
  renderer/profile preservation passed on C3 with retained System1.2.5; ordinary
  reporter public-feed acceptance remains separate and original causality is
  unconfirmed.
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

All desktop/Android installers and normal/Beta Root payloads were rebuilt in the
selected complete candidate.
The actual builder's historical Helper byte pins cover 0.6.16/0.6.17/0.6.19,
not 0.7.5. A new source-built Helper version is required regardless: release
assembly refuses changed bytes under an unchanged published version. New 0.8.0
has a committed published Home 1.13.1/new Helper probe matching its exact canonical
archive hash. Short Home, triple-Home escape, later Home staying LG, arrows and
volume buttons passed on the C3; see the
[compatibility record](history/2026-11-08-helper-0.8.0-compatibility.md). This is not
an automatic OTA/rollback or final-build acceptance claim.

Existing System supervisors remain pinned; component OTA does not replace them.
Explicit replacement still admits only installed 1.1.0/1.1.1, not 1.1.2/1.2.x.
Root Beta remains a separate exact-Node-0.12.2 payload with ordinary OTA disabled.
C1 compositor admission and Homebrew Installer promotion retain their independent
unverified gates; no Homebrew release approval is selected. Android retains its
application ID and persistent signer; exact code27→code28 APK upgrade acceptance
passed on the isolated emulator. No new general firmware or phone compatibility
is claimed.

## Validation and remaining gates

The [preparation record](history/2026-11-08-release-1.13.0-preparation.md)
records actual package hashes, host checks, documentation review and blockers.
[Integration evidence](history/2026-11-08-next-candidate-integration.md) retains
reviewed PR checks; it is distinct from full frozen-candidate validation.
The [bounded physical checklist](history/2026-11-08-next-candidate-physical-checklist.md)
separates the mandatory pre-dispatch Helper probe from later exact-build
acceptance. Public-feed verification cannot pass against an unpublished QA offer.
The [consolidated C3 pass](history/2026-11-08-c3-preliminary-qa.md) records actual
device changes, fixes, outcomes and the remaining acceptance scope.
