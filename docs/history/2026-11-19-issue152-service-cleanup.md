# Issue 152: service residue after fresh installation — 2026-11-19

Source base: `4a38424dbac02a2dae2991a80b749aaa23037eb2` (`release/next`).
Report: [issue 152 follow-up](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152#issuecomment-7002816259).
No TV connection or mutation, candidate selection or physical acceptance occurred.

## Evidence and scope

The posted cytv 0.22.0 reports show verified removal followed by completed fresh
No-root installation on EF950V 04.26.35/SDK 2.2.0/Node 0.10.25, Windows AMD64.
Startup was observed and the owner confirmed the Home button destination. A
later uninstall had terminal Helper and Home removals, then failed at
`private-cleanup`, `cleanup-check-failed`, `blocked_areas: [service]`.
The posted listing establishes only the retained Helper app/state ownership:
Helper and its parent 0:0/0775, empty state 5999:5000/0775. It does not identify
which service failed, its owner or its remaining contents. Post-reboot Home,
icons and full hardware compatibility remain outside this correction.

The existing exception accepted a directory-only Helper application tree after
its terminal removal, but tried to delete service directories unconditionally.
An empty service slot under a root-owned 0775 services container reproduces the
same failure class. We model that plausible residue; we do not claim the export
proves the owner's service slot is empty.

## Correction

Reuse the same bounded, two-pass directory-only walk for each fixed Helper,
Home renewal and updater service slot after that slot's own package terminal.
Sweep still attempts deletion first. The retained service flag survives final
readbacks, interrupted completion, the retry path, result and redacted diagnostic
projections. The completion screen reports empty service directories separately;
all installer languages have the new message. No control, privilege, network
endpoint or external dependency is added. No automatic install follows removal.

The existing catalog, SAM, process, registration and inode/ownership rules remain.
Helper-specific reboot/opaque-process evidence is not extended to services.
Unrelated paths and nonempty inaccessible service slots remain blocking. New
regressions cover a surviving same-pass SAM registration, late appearance of a
second empty-directory type, missing own terminal, files/symlinks and a file
returning before resumed completion. Independent review found and corrected the
stale-terminal snapshot in SAM readback and missing late result flag. The exact
fixture also closes its pipe and bounds child teardown after failures.

## Local verification model

- Original cleanup program fails on the protected-empty-service fixture; the
  candidate completes it. The program is the production bundled JS, executed by
  Node, not a fabricated cleanup reply.
- `tests/cytv/test_no_root_service_cleanup.py` runs in a network-disabled Linux
  container. The SDK child uses UID 5755/GID 5000, groups 44/505/509/777. Helper,
  parent and service containers are root-owned 0775; Helper state is
  5999:5000/0775. The first service trees are 0:0/0775, the fresh-install trees
  5999:5000/0775. These service owners are fixture variants, not new device facts.
  A separate privileged parent performs simulated vendor install/remove changes
  using actual fixture IPK extraction. Both removals leave only directories and
  finish with no pending operation. The intervening install receipt is simulated
  here; the full installer/observer install cycle is covered separately below.
- The existing backend/observer integration performs actual installer calls:
  install, full remove, fresh install over retained service directories, full
  remove again. The fake vendor transports only model package endpoints and
  privileged filesystem access; actual install receipts, observer and cleanup
  programs execute. Both fixture IPKs contain service files so reinstallation
  really writes into the retained service slots.
- The root ownership replay uses native Linux Node 22; the full integration uses
  the host Node runtime. This is a filesystem/installer regression, not an
  emulated complete EF950V firmware. The earlier stock ARM Node 0.10.25/QEMU
  attempt stopped at a directory-descriptor identity guard before reconciliation
  (see the prior profile-reconciliation record); it is not reused as a passing
  firmware acceptance result. The prior extracted executable is no longer
  present in the retained local sysroot, so this task does not claim a new stock
  ARM runtime run. No extra reporter/device operations were requested.

Verification ledger: the broader removal/integration/recovery/profile selection
passed 237 tests (two expected root-only skips) in 369 seconds. After review
corrections, the affected simple-removal/recovery-state/new full-cycle selection
passed 148 tests in 115 seconds; diagnostics/i18n passed 51. The root-only
ownership replay passed separately in the network-disabled Linux container.
`npm ci --offline`, `npm run format:check`, Python compilation and diff checks
passed. Matching tests were not repeated after documentation-only changes.
Detailed commands are recorded in the PR. No physical Home,
post-reboot startup, sound, standby, cold boot, OTA or rollback result is inferred.
The actual owner's remaining service files are still unknown; if they are
nonempty or a registration/process survives, this patch intentionally keeps the
operation pending rather than fabricating success.
