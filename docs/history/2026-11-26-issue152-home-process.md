# Issue 152: Home startup and runtime removal — 2026-11-26

Original base `7d701785`. Shared removal reviewed with `d9f59f6c` on
`release/next`. Source evidence comes from the [owner's seven reports](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152#issuecomment-7171438624).
No TV connection or operation, reporter probe, release selection or physical
acceptance is part of this work.

## What the reports establish

cytv 0.24.2 on Windows AMD64 first completed the old removal with a confirmed
changed kernel and terminal Helper/Home packages. After reinstallation on
55EF950V-ZA/04.26.35/SDK 2.2.0/Node 0.10.25, package verification and launch ACK
passed and a Helper process was observed, but the owner selected LG Home as the
physical Home result. Home diagnostics subsequently had `start-unacknowledged`.

All four later removal attempts stopped at `controls-restored`, before package
requests: `phase=before-packages`, `project_running=true`, `installer_running=false`,
`decision=process-blocked`. The report does not name the process or identify the
match source. These facts are consistent with an actual controller, a package's
LS2 host or web process, or a path reference. None is claimed as the confirmed
identity on the reporting TV. Icons and overall compatibility remain unresolved.

## Shared removal review

[#841](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/841) reached
the same pre-package decision on a 43UM7600. The shared gate now includes
[#845](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/845), integrated
at `1e448367`. Its stock k5lp Node 0.12.2 QEMU replay used modeled process
listings and activity completion. A literal print passed, a delayed launch
blocked, and an acknowledged service could exit within the extended wait.
Neither report identifies which process matched on the TV.

An early #846 fixture modeled a package manager that stopped persistent LS2 hosts.
The reviewed implementation keeps #845's requirement for those services to exit
before a package request. The specific service acknowledged by disable has up
to 20 seconds. Other blocking processes have eight. A separate fixture covers
a catalogued Helper controller or Home web process that exits only when the
vendor removes the package. Only fixed application-runtime invocations can use
this path after Stop and control restoration. An unrelated path reference blocks.

The installer journals delegation before the package request. A surviving relay
or unavailable process listing after the vendor terminal preserves service files,
including on immediate retry. Review reproduced a further case after a verified
kernel change: the listing returned but a process command line was unreadable.
The corrected pre-sweep check keeps the functional service file and the terminal
receipt until the process readback succeeds. The fixture then completes cleanup
with one vendor removal request across all attempts.

## Startup observation

On the original draft a current PID and an earlier READY could still yield a
startup pass after input loss. The probe now follows `INPUT_WAIT`, the next
accepted READY, the relay exit announcement and the actual worker exit. A logged
nonzero exit remains visible when the controller subsequently sets its Stop latch.
The probe distinguishes unavailable process visibility from observed absence.
Old install plans without a bound generation cannot certify readiness from a PID.
A Stop arriving during the probe cancels activation without another launch.

Both CI shard-4 failures on the original draft reproduced locally: optional
readiness telemetry erased a confirmed negative process scan. The corrected
setup keeps `not-observed` when the readiness probe is unavailable. An unknown
scan stays `unverified`. Neither result certifies the physical Home button.
A new attempt clears old startup evidence.

## Verification and limits

The focused combined host run covered 206 cleanup, report, recovery, startup
and Home diagnostics cases. Nine shared Root removal tests passed. The two
changed Linux ownership scenarios each completed two install/remove cycles as
SDK UID 5755/GID 5000 with synthetic vendor replies, process files and relay
events. The tests used a read-only checkout with networking disabled. The startup
probe fixtures also passed on host Node 0.10.25 and on the comparable k5lp
stock ARM Node 0.12.2 under network-disabled QEMU. Both runs used modeled
controller records and process files. See the PR for the final
post-review cases and CI links.

Earlier exact EF950V firmware work ran stock ARM Node 0.10.25. The later
[descriptor-identity limit](2026-11-18-issue152-profile-reconciliation.md) bounds
that replay. No factory image or host fixture records the transient process or
relay state on the reporting TV. A future standard report from an installer
containing these changes can distinguish the category at removal and the relay
state at startup. Physical Home, postboot Home, sound, standby, OTA and rollback
remain unverified for this run.
