# Local recovery storage diagnostics — 2026-11-07

Source-only work for [#201](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/201).
No TV was contacted or changed. This records host regressions and implementation
limits, not another user's installation result or original-device acceptance.

The v1.12.0 coordinator froze its five-PR inventory during this task. This work
stays in its own PR outside that inventory until publication; it selects no new
build and does not change candidate inputs. The feature branch merges the frozen
base only to preserve its published-recovery wording and history links.

## Behavior

The private capsule reader now distinguishes local directory ownership,
permissions, type/access, missing/unsafe/changed/invalid file data and incompatible
retained observer source. A directory refusal does not claim that capsule bytes
were lost: its checks can stop before the file is opened. Desktop/console/Android
human messages are translated in all twelve additional installer languages.

New schema-1 `local_recovery` metadata exports only a fixed reason/location,
optional four-digit octal mode and root/current-user/other owner category. Current
and retained first/observation failure records are filtered again on export.
Paths, user/group IDs, account names and original exception text are excluded.
The original installation failure remains separate from a later status refusal.

New No-root operations validate local capsule ancestry and exercise a temporary
private write/flush/fsync plus directory sync before recording pending or calling
the TV observer. Failure does not leave a new journal/capsule. Disk-full/quota
errors retain computer-storage guidance, including profile-directory creation.
The probe reserves no disk capacity; subsequent failures still retain pending.

No path/ownership/permission policy is relaxed. No automatic chmod, journal
deletion, old-source execution, package replay, cleanup-confirmation change,
endpoint, persistent TV state or version bump is introduced. The bound observer
PROGRAM bytes and root-SSH source selection are unchanged. Existing separately
confirmed cleanup remains the fallback for an incompatible old source.

## Verification and limits

The baseline three capsule tests passed. New tests failed before implementation
for the missing failure categories, a pending journal left after local refusal,
and the absent early local I/O check. Both disk-full guidance regressions were
observed failing before their corrections.

The final focused local/capsule/observer-diagnostic/recovery/localization run
passed 61 tests. Independent review identified the first-access disk-full
translation issue; the regression and correction were independently verified
with no remaining actionable findings. The local-recovery/capsule subset passed
14 tests independently. No new TV result was collected.

`scripts/test.sh installer android` completed successfully: Homebrew payload,
runtime/bridge/browser, installer/continuation checks, 1,079 installer tests
(five expected platform/runtime skips) and 44 Android Python tests. The final
61-test affected run covers the subsequently added first-access disk-full
correction and first-failure preservation assertion; the unchanged full suite
was not repeated solely to copy its result. Optional font/Qt platform messages
did not fail the run.

Python 3.9 syntax passed for all six changed Python implementation/catalog
modules; formatting and diff checks passed. All thirteen localized guide
recovery links were checked; setup, controls and confirmations are unchanged.
The common recovery explanation and developer diagnostic-field reference were
updated, without changing current published downloads or historical evidence.

This work does not identify a specific reporter's rejected ancestor, recover a
historical terminal result, prove compatibility with a host directory layout or
confirm original installation/recovery. Rebuilt installers and normal candidate
verification remain required for delivery. Physical installation, Home/remote,
audio, standby, cold boot, OTA and rollback are not tested by these host checks.
