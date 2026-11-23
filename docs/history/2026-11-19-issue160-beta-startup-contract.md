# Root Beta startup contract on the B9

This investigation follows [issue #160](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160).
The retained installation is Root 0.20.0 from v1.21.0 on OLED65B9PLA,
firmware 05.50.00, previously reported webOS 4.10.2-31 and SDK 4.10.0.
The installer platform is Linux x64. Remote model is unknown. The private
service runner was repaired in place; the runtime and application were
not upgraded by that repair. The latest report also has an unresolved
requested removal. No device operation is authorized by that diagnostic
projection alone.

## Two different startup paths

The retained `runtime/cli.py` explicitly rejects startup status and
configuration when `gate_backend()` selects the native backend. The existing
source-selection policy in `intent_runtime.py` uses the profile-based
coordinator's binding, transaction and guardian health records. The native
keyfilter has its own intent, leases and lifecycle. Removing the CLI guard
would not connect those state machines.

Separately, the retained `c1_keyfilter.execute('boot')` restores the stock
route. Its source explicitly excludes automatic rearming until an explicit
Enable. This is the reason that repairing the service alone cannot make
Home resume automatically.

The current native implementation has session-bound resumption, but
`reboot_resume_supported()` at source a26bc2f27 selects only the tuple
`65NANO913NA / 04.64.00 / 5.6.2`. This is a hardcoded scope of a validated
scenario, rather than a general capability test. The resumption machinery
also requires newer native commands, normal-shutdown evidence, current
startup session evidence, verified stock routing and preserved stop latches.
It must not be enabled on another device solely by changing that tuple.

## Exact firmware inspection

Reused the signature-verified official W19H image and retained v1.21.0
package from the [original B9 firmware work](2026-11-16-issue160-beta-recovery.md).
The archive SHA-256 remains
`59ef18516657a7a058d4a8cf86dab14020eb25d40f794e328506bbc999a1b976`.
Read additional files directly from `rootfs.pak` with Linux unsquashfs,
without extracting or committing vendor source into the repository.

The factory `/sbin/init` links to `init.upstart`. The image contains
`/sbin/initctl`, Upstart jobs for shutdown on runlevels 0/1 and reboot on
runlevel 6, and the LS2 watchdog uses those runlevels to distinguish normal
shutdown. `/bin/systemctl` is absent. In contrast, the current native
guard's `normal_shutdown()` invokes `/bin/systemctl is-system-running`
and expects the systemd stopping result. That observation cannot succeed
on the stock B9 image as written. The factory jobs suggest a possible
Upstart lifecycle adapter, but do not prove the running TV's event timing,
Quick Start/snapshot or standby semantics.

Factory ARM `initctl --help` ran under QEMU with the image's loader and
libraries. A read-only `get-env RUNLEVEL` request reached the expected
Upstart endpoint but failed because the isolated process lab has no live
init daemon at `/com/ubuntu/upstart`. No global Upstart environment was
changed. Live runlevel delivery cannot be established by that client-only
experiment.

The retained ARM guard SHA-256 is
`b8c4e10105c8eaa4cb164eee8b7cf57fa9eb20a474bc27e1759327700f379cf7`,
matching its retained release descriptor. Its `--selfcheck` ran successfully
under QEMU. The corresponding v1.21.0 source and binary lack the newer
`--guard-resumable` and `--retire-boot` interfaces. Adding a Python allowlist
entry alone cannot add those native interfaces.

## Runtime replay

Ran the original private JS service with the exact factory ARM Node 0.12.2,
vendor bootstrap, webos-service, LS2 hub and luna-send. The fixture represented
the repaired runner, original B9 compositor selection and published proofs.
The Python child used container Python to execute the actual retained CLI's
startup-status entry point. It selected the native backend and returned a
failure. The real service returned `returnValue=false` with startup choices
unavailable. All 148 installed package file hashes matched afterward.

The actual retained native Python boot branch was also executed with its
operation-lock context and board effects intercepted. It called restoration
and did not call Enable. This verifies branch selection, not hardware routing.
The actual retained integrity verifier accepted the unmodified local fixture,
then rejected an isolated runtime edit with a digest mismatch. The local
runtime file was restored and application hashes still matched. The binding
check was modeled for the substitute Python interpreter.

Containers used `--network none --cap-drop all`. No recover, removal,
installation, startup configuration or activation ran on the reporter's TV.
Physical remote input, Home routing, sound, standby, AC cold boot, snapshot
resume, OTA and rollback remain untested on that B9. No universal compatibility
claim follows from these process-level results.

## Can it be updated in place?

The code that needs changing lives in the private runtime and guard; deletion
of the application is not an architectural requirement. However, the current
Beta repair only changes the launcher and its proofs. It does not migrate
runtime/native bytes. The ordinary Root Updater explicitly rejects this
experimental backend too. A working in-place startup migration is therefore
not supplied by either existing path.

A supported implementation needs a verified startup/shutdown capability
contract, including Upstart where present, and a native startup policy instead
of invoking the profile coordinator. It must migrate the matching runtime,
ARM guard, backend native digest, recovery inventories and applicable hook
records together, with retained application/preferences, interruption recovery
and an inverse. It must preserve explicit Off, emergency stops and failed-attempt
latches across callbacks. The unresolved requested removal must be reconciled
through its actual ownership evidence before any migration is offered.

This investigation does not enable B9 by a model-name exception or ship a
startup migration. The exact outstanding contracts are Upstart shutdown and
snapshot/session observations, native source policy and a verified in-place
migration path. Hardware acceptance would still need the affected physical
power/input cases after those dependencies are implemented. The existing
Home/style UI error request remains separate and unresolved.
