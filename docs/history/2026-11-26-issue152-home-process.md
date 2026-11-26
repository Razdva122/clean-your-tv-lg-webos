# Issue 152: Home startup and runtime removal — 2026-11-26

Base: `7d701785` (`release/next`). Evidence: [owner's seven reports](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152#issuecomment-7171438624).
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

## Local reproduction and change

The real cleanup program marks a persistent
`node /usr/bin/run-js-service com.local.nativehome.service` or
`com.gathin.tvhome.renewal` as project-running even after successful service
`disable`. A Home WebProcess can also remain resident after stock Home is shown.
These residents prevented reaching the vendor endpoint responsible for their
shutdown. The regression was RED at the same pre-package gate. A stalled installed
native controller without relay READY likewise prevented its vendor removal.

Allow those fixed installed-package runtimes to reach normal `dev/remove` only
after the existing Stop/control stages; service hosts require a positive disable
ACK. Helper native runtime allowance requires Helper in the current catalog and
no invalid Stop record. No force-kill, UID change or arbitrary process path is
introduced. Unknown references, installer and updater activity remain blocking.

After an actual delegated runtime observation, persist
`cleanup_package_runtime_delegated` until a positive postvendor process check.
The readback occurs before any private sweep. A vendor terminal with a surviving
runtime or lost `/proc` does not permit unlinking its service files, including on
an immediate retry. A confirmed kernel-change/terminal opaque retry uses the
previous scoped rule. Review found the missing-enumeration and forgotten-retry
cases; both were fixed and tested. This journal boolean is the only new removal
admission state and is distinct from advisory process telemetry.

Add fixed report booleans distinguishing controller, relay, Helper/Home service
hosts, Home web app, unknown path reference, active blocker and runtime delegated
to the package manager. Standard exports contain no PID, arguments or process path.
This will distinguish the previously hidden device branches on a later standard
report, without another custom owner-run command.

## Startup result correction and remaining Home limit

A transient native process was enough to pass the old startup observation. The
local failed/stalled-relay model reproduces that false positive. Native startup
now records its generation/schema and emits `worker-ready` only after READY,
Stop checks and the Home enable/disable command. The host reads bounded current
and rotated logs, checks current PID/proc identity and expected setup generation,
and waits at most five seconds while starting. It neither relaunches nor clears
Stop/watchdog state. The final generation check runs after observation, so a Stop
during the new wait still reports cancelled setup and wins over readiness.

`helper_startup` exports only a fixed state, controller/Home booleans and bounded
numeric exit code. The probe retains failure history after the PID file is gone,
but never calls an absent controller ready. Old/missing telemetry is unverified.
Home diagnostics that fail to start can attach the same best-effort observation
while retaining their original error.

This corrects misleading startup success and makes failed/slow relay startup
visible. It does **not** establish why the physical EF950V relay failed or promise
that its Home button is repaired. No log/exit code was present in the owner's
reports. Local fixture exit codes and stalled runtimes are explicit models,
not values newly discovered on the TV. Further device acceptance remains open.

## Verification model

The existing backend install fixture performs fresh installer calls and preserves
Stop arriving during the readiness probe without a second launch. Source cleanup
fixtures exercise resident LS2/web/native processes, failed disable, postterminal
survivors, lost visibility on first attempt and immediate retry, and unrelated
argument/path references. The startup fixture runs the production read-only Node
program against real files with modeled `/proc` and controller events. Privacy
checks reject PID, generation, command and path fields from exported summaries.

Five network-disabled Linux root-owned filesystem cases passed using SDK UID5755,
GID5000/groups44,505,509,777; root-owned 0775 containers, state5999:5000/0775 and
service slots0:0/0775 then5999:5000/0775 after fresh install. They include failed
and stalled controller observations, persistent LS2 hosts, two install/remove
cycles and vendor shutdown. Vendor mutations, PID entries, relay events and
intermediate install receipts are simulated; actual cleanup/readback/boot-proof
programs execute. Native Linux Node22 is used, not a complete booted LG image.
The earlier stock ARM/QEMU descriptor guard limit remains; no fresh stock Node
0.10.25 result is claimed.

The compiled Helper runtime test passed on host Node23, covering controller,
service, polyfills, websocket, watchdog recovery and Stop. Its initial sandbox
run could not bind localhost (EPERM); the same local-only test passed with the
sandbox restriction lifted. No device endpoint was contacted. A broader Python selection passed 268 cases before the final review corrections;
the final affected cleanup/diagnostic/recovery/startup selection passed 199 cases.
The later narrow path-reference regression and startup-observation updates passed
separately, as did 16 helper/Home diagnostics cases and both actual-controller
Home/IR suites. The final startup argv-identity review finding was fixed and
covered with the unrelated-script regression. Matching unaffected suites were
not repeated after documentation-only edits. Exact commands and CI status are
recorded in the PR. Physical Home, postboot Home,
sound, standby, OTA and rollback are unverified by this work.
