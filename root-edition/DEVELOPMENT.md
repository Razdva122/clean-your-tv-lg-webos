# Root developer references

For normal use, start with the [Root guide](README.md).

## Recovery startup diagnostics (1.3.0, issue #55)

Version 1.3.0 preloads `service/startup-diagnostics.js` before the firmware's
Node bootstrap. The runner still execs Node with the same PID and bootstrap
arguments; registration formats and recovery behavior do not change. A private,
root-owned mode-0600 `recovery-service.json` under `/var/lib/clean-your-tv-root`
records the current startup and terminal exit code. On Node 12.17+/13.7+,
`uncaughtExceptionMonitor` also records a bounded exception name/code/stack
without handling the exception or preventing its normal fatal exit. Node 8 still
records exit codes but cannot capture the exception through that monitor.

The file is replaced on each start and remains below 32 KiB; the exception stack
is limited to 4096 characters. Unsafe paths, symlinks/hard links and diagnostic
I/O failures cannot redirect writes or stop the service. This is exception/exit
instrumentation, not an unbounded stderr log. SIGKILL, default signal termination,
native aborts and failures before the preload runs may leave only an incomplete
startup record or no record. No exit code is invented in those cases.

If `finalize` fails, `recovery-failure.json` retains the failed phase, bounded
numeric Luna/client codes, recognized service/method/permission categories and
safe startup observations. A previous unchanged startup record is marked stale.

The optional `startup_milestone` records startup progress.
`status-registered` means the local handler registration returned,
`status-requested` means the callback was entered, and
`status-response-returned` means the local response call returned. The field
is exported only for a fresh process record or a milestone that advanced during
finalization. It may be absent on older builds, a previously active service or
failed diagnostic I/O. A local response call does not prove delivery to Luna's
client or authorise recovery. No request payloads or response contents are saved.

Luna stdout and stderr are drained with a combined 64-KiB limit; raw RPC text is
not exported. No readiness proof, Home activation or automatic retry is added.

The cytv installer reads this data after a definite failed Root install and adds
allowlisted `root_recovery` fields to that failed attempt's saved diagnostic
report. A per-install `CYTV_ROOT_INSTALL_ATTEMPT` token must match the retained
report; earlier failures cannot be attached to a later attempt. The token is not
exported. Failed/malformed diagnostic reads preserve the original install error.
The manual SSH bundle retains the two private files on the TV; its nonzero exit
alone is not a diagnosis. Review private exception text locally before sharing;
never publish the full file without redaction. Preserve deployment journals,
LS2 snapshots and retained drivers; do not overwrite an older installed driver
to retrofit these diagnostics or rerun provisioning merely to collect a log.

The OLED Flex 42LX3Q9LA / webOS 11.2.0 startup failure is still unresolved. The
firmware bootstrap argument contract and effective LS2 registrations need device
evidence; this change does not implement the report's unconfirmed manifests.d
hypothesis. No hardware, standby or cold-boot acceptance is claimed.

Packaging at freeze: bump/rebuild Root and cytv, synchronize metadata and rebuild
all desktop/console/Android payloads. The new private service file also changes
the generated Root infrastructure and System Updater inventory. Version/rebuild
the supervisor/bootstrap and validate its migration or explicit computer
rebootstrap before shipping; an old pinned inventory cannot accept the new path.
Existing failed installations and rollback baselines must remain recoverable.
Component versions and the release candidate inventory are unchanged here.


## Current source delivery

The paragraph above retains its original 1.3.0 implementation/freeze context.
Current component versions are in [1.4.0 release notes](../docs/RELEASE-1.4.0.md);
use the [release flow](../docs/RELEASE-FLOW.md) for packaging.
See [current runtime contract](runtime/README.md), [source bundles](package/README.md),
[original-supervisor OTA compatibility](../docs/development/ROOT-OTA-13-COMPATIBILITY.md)
and [Homebrew private DATA authority](../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#cold-boot-data-authority-correction).
