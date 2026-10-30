# Home installation gates

Related issues: #140, #133. The controller-state and firmware gates shipped in
v1.5.0; immutable Helper 0.6.19 does not contain them. The Node 0.10.25 target
below is an unpublished follow-up for #152.

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
