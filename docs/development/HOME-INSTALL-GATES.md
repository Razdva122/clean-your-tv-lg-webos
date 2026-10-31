# Home installation gates

Related issues: #140, #133. The controller-state and firmware gates shipped in
v1.5.0; immutable Helper 0.6.19 does not contain them. The Node 0.10.25 target
below shipped in v1.5.4. The SSH stop fallback described below is unreleased.

## No-root recovery after Helper service refusal (#152)

Only a definite `helper-disable` rejection with code `-1` in No-root enables
the trusted installer-side ES5 stop program. It is streamed to `/usr/bin/node`
over the existing SSH session (no `-` option, unsupported by Node 0.10/0.12),
without executing installed Helper JS. Checked real shared state paths receive
an exclusive persistent `blocked` latch and atomic `control.json` stop request.
A new latch keeps the state directory group and group write access so a live
controller with another UID can execute its normal stop/cleanup path. Existing
latches, watchdog state and Home preference are preserved. Symlink/hardlinked
stop files, unsafe directories and uncertain process state are refused.

The existing read-only process probe must confirm no controller or relay before
Restore may launch LG Home or removal may proceed. A stale PID alone is not an
active process. Other failures and Root keep their existing behavior. No new
permission, endpoint or state filename is introduced. File/operation fixtures
and actual Node 0.10.25/0.12.2 host checks are not EF950V hardware acceptance.

## No-root controller state

Only controller startup initializes `control.json`. It creates a private,
exclusive file in the checked state directory, writes the empty command, sets
controller ownership and shared directory group with mode 0660, then atomically
replaces the control pathname. It does not write or chmod the previous inode.
Ordinary inventory/screen-watcher permission checks do not reset commands.
Automatic startup checks the emergency latch before initializing control.
The existing pairing-key repair remains separate and retains valid key bytes;
do not remove the key to work around a control-file permission error.

Existing state path validation, trusted directory ownership, shared-group checks,
no world writes, exclusive staging and cleanup on failure remain required.
No new persistent preference, permission, or network endpoint is introduced.

### Legacy process matching (unpublished follow-up for #152)

The installer scans NUL-separated `/proc/*/cmdline` arguments for the controller
identity, exact `native.js` path or exact relay path. An installed app or the
separate `com.local.nativehome.service` worker alone is not an active input
controller. The original `grep -Fx` assumption is incompatible with older
BusyBox: [1.20.2 grep.c](https://github.com/mirror/busybox/blob/1_20_2/findutils/grep.c)
uses substring matching for `-F` without checking `-x`. It can therefore match
the SSH probe's own command text on an otherwise idle TV. Anchored basic regular
expressions with literal dots avoid that behavior while retaining real controller
and orphan-relay refusal. Stale PID handling, unreadable/ambiguous-state refusal,
ownership checks and emergency latches are unchanged.

`tests/cytv/test_helper_preflight.py` executes the real shell probe against a
local proc fixture, including its own SSH command. A wrapper models the old
fixed-string behavior; this is not a run of the TV's BusyBox binary. The legacy
false positive fails before the change and passes afterward, while real processes
remain blocked. This proves a host-reproduced portability defect, not the actual
EF950V cause: its grep implementation/version and device behavior remain unknown.

Restore rejection diagnostics now distinguish fixed `helper-disable`,
`eim-delete-device` and `application-launch` categories. Unknown calls remain
`luna-call`; no arbitrary URI, application ID or remote error text is exported.
An LS2 `-101` alone is not proof that the controller is active or that a particular
service is absent. A failed `control.json` upload also does not establish which
shell utility, state directory or permission failed. Upload and stop behavior are
unchanged; no fallback, automatic directory creation or guard bypass is added.
These failures need a future scoped observation if they recur. Do not repeat
Restore/Uninstall, clear state or change pairing merely to diagnose them.

## Root firmware interfaces

Product preflight and explicit low-level component installation read Settings
Service `general.defaultApps` and System Profile `defaultApps` / `idleApp` before
creating Root state or submitting a package. Failed, incomplete and malformed
readbacks refuse installation. A missing settings `home` override remains valid
when the profile readback is complete; setup still requires its existing durable
stock-Home initialization and independent readback before recovery readiness.
This gate does not prove all write, rescan, input or boot-recovery capabilities.
Removal payload validation does not acquire install-only prerequisites.

Missing System Profile is an unsupported routing/recovery interface, regardless
of webOS marketing version. This change does not add a Settings-only adapter or
make an already retained installation recoverable by itself. The separate,
reviewed-source [cancellation tool](../ROOT-INSTALL-CANCELLATION.md) now admits
only exact never-activated finalize failures before recovery registration,
subject to original snapshot/runtime/package proofs and safe LS2 rollback.
It refuses stock-Home initialization, active processes, recovery readiness,
activity or activation state and unknown edits. Preserve the original operation
and provisioning evidence; no broad restore/remove recommendation follows from
a successful app launch or working LG Home controls. This tool is not public
Root compatibility support and has no target-TV acceptance yet.

## Packaging and acceptance

At candidate freeze select a new Helper version, synchronize manifests and
release metadata, and build it from source: builders deliberately reuse the
published baseline when the Helper version remains unchanged. Rebuild the affected
Root/Root Updater code bundles and installers as well. The signed Helper
transition also needs a new Home candidate and an explicitly tested rollback
compatibility archive pin: changing `native.js` is outside the narrow
state-permissions-only exception in `prepare-release.py`. No release versions are
changed during this preparation.

Run `scripts/test.sh`, including ownership fixtures, controller/emergency tests
and Root preflight tests. The multi-UID kernel test requires Linux root and runs
in CI; macOS reports it skipped. Current Helper source targets Node 0.10.25+;
set `NODE010` and `NODE012` to validate the exact Node 0.10.25 and 0.12.2 runtimes. Automated checks are not device
acceptance. Fresh-install Home, Back, triple-Home, pairing-backed monitoring,
standby, cold boot and recovery/removal need separate target-TV validation.
