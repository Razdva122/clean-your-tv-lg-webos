# B9 recovery, requested removal and settings

The [new public report in #160](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160#issuecomment-7016298433)
uses CYTV 0.21.3 from v1.24.1 on Linux x64. The established TV is OLED65B9PLA,
firmware 05.50.00, SDK 4.10.0, previously reported webOS 4.10.2-31. Remote
model is unknown. The retained Root release is 0.20.0 from v1.21.0.
The reporter says Home, autostart and style changes fail. No precise UI
message or action sequence is supplied. The prior report confirmed
`installed-recovery-only` after the final-status fix.

## Why recover entered removal

The new report has a saved `uninstall` request at `requested` and its trace
enters `continue_clean_removal` from the recovery branch for
`clean-removal-v1`. In v1.24.1 that branch asks `Continue removing Clean Your TV?`
before dispatch. `Store.request_clean_removal` records this host goal only
from removal entry points. A completed Beta repair with no pending host
request does not create it. The report cannot establish which earlier
screen or command created the request, nor reconstruct the confirmation
conversation. Do not infer an automatic conversion from successful repair.

Regression coverage replays the completed-Beta observation with no pending
request and verifies no mutation prompt, removal or activation. With a saved
removal request, declining continuation preserves host records and invokes
no cleanup. A failed removal reservation must not be deleted or rolled back
merely from the projected diagnostic; it can hold authority on the TV.
No request cancellation or device cleanup was performed in this task.

## Errno 7 boundary

The report's product record has `OSError / errno=7` at `requested`.
The early subprocess boundaries are the short boot-identity Python command
and the private inventory Node program. The latter passes 103647 bytes of
published JS as one `node -e` argument, before fencing original writers or
removing packages. The report has no child boundary, stack limit or
process environment, so it cannot prove which exec failed.

Reused the verified exact W19H B9 05.50.00 image from the
[original firmware investigation](2026-11-16-issue160-beta-recovery.md).
In QEMU with factory ARM Node 0.12.2, the published inventory succeeds under
the ordinary lab process budget. With an explicitly modeled 512 KiB stack
limit and 32 KiB environment padding, its exec fails with E2BIG (errno 7).
Those limits are a reproducer, not measurements from the reporter's TV.

The fix streams verified source bytes to the existing legacy-compatible
stdin loader with a small fixed entry argument. Hash admission and
NODE_OPTIONS/NODE_PATH filtering remain before execution. The actual
candidate `LocalDevice.shared_cleanup('inventory', {})`, with the same
published source and modeled budget, succeeds on factory ARM Node under
QEMU. All 148 files of the retained installed package have matching hashes after inventory.
Only inventory ran; no recover, clean_remove or activation was invoked
in the firmware replay. Container networking was disabled and capabilities
dropped. The container Python substituted for the private TV interpreter.

New bounded diagnostic steps distinguish `boot-identity` and
`private-inventory`. Injected errno 7 at each early boundary retains the
requested stage and installed fixture packages, with the exact step in the
sanitized result. A large-source regression fails before the fix and
passes afterward; a source digest mismatch still prevents execution.

## Home and settings findings

Inspected the exact retained package and executed its real handlers with
modeled Python replies. Its Python CLI explicitly rejects startup status
and configuration for the native experimental backend, which includes B9.
Its compositor boot operation restores stock routing instead of rearming
Home. Repairing the private service runner does not upgrade those runtime
or UI bytes. Current firmware-specific rearm admission cannot establish
support for this B9 package.

Home status uses the correct nested service envelope. Native status carries
the backend identity needed for matching 100-second UI / 90-second service
activation deadlines. A startup-status failure followed by general status
works through the retained handler, so that rejection does not itself
explain the Home switch failure. Actual activation rejection is unknown.

Style changes use local ThemeManager, ThemeStore/ThemeRuntime and browser
storage, independently of Home service activation. The submitted recovery
report has no browser exception or exact UI outcome. No style defect was
reproduced; no style or Home-activation fix is claimed. Native render/input,
standby, cold boot, audio, OTA and rollback remain untested on this B9.

## Verification and remaining work

Focused host checks cover the shared cleanup adapter, recovery consent and
sanitized diagnostic steps. The firmware replay verifies the exact candidate
adapter against the published JS on stock Node. User guides need no control
changes for this transport-only fix. The release candidate was already
frozen when this branch started; the focused PR does not modify its scope,
selected build or acceptance and does not dispatch a release.

The cause of the saved removal goal and the actual Home/style error still
require the reporter's precise action and displayed message. The existing
issue request already asks for an enabling error. The fix eliminates the
reproduced large-source exec boundary, while the original B9 Home/settings
report remains unresolved. Do not repeat recovery or removal to collect
that UI evidence. No reporter TV was contacted or changed.

Host verification used the repository virtualenv. The final simple-removal
suite ran 27 cases with one root-only skip on macOS. Recovery action,
automatic recovery and diagnostic suites cover 81 cases in total, including
the newly added consent and diagnostic regressions. The larger coordinator,
clean-removal and recovery-diagnostic run exercised 173 cases. Its first
pass had 22 prerequisite errors from missing build font cache and runtime
import path. Those 22 cases were selected for retry with the existing
`CYTV_FONT_CACHE` and runtime PYTHONPATH. Independent code review found no
actionable issue. `git diff --check` passed.
The selected 22 prerequisite retries passed. Across the selected suites,
280 cases passed and one was skipped; this is focused development evidence,
not final release or B9 hardware acceptance.
