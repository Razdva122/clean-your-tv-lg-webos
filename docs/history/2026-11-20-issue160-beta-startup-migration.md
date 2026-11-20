# Retained Root Beta startup migration

This focused change follows [issue #160](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160)
and the [B9 startup investigation](2026-11-19-issue160-beta-startup-contract.md).
The public installation is OLED65B9PLA, firmware 05.50.00, previously reported
webOS 4.10.2-31 and SDK 4.10.0, retained Root 0.20.0 from v1.21.0, installer
Linux x64. Remote model is unknown. The latest report includes a requested
removal; its full private ownership evidence is unknown. No reporter TV was
contacted. This record describes offline development acceptance only.

## Delivered behavior

`cytv migrate-root-beta --edition root --root-variant node012-beta` uses the
saved SSH connection and a separate interactive confirmation. It stages the
verified runtime payload without submitting its IPK to the package manager.
The installed application, service package and user preferences remain in
place. The private runtime/support closure and ARM guard are migrated with
matching backend, release, bundle and recovery inventories. Original package
file hashes and application version remain the retained package identity.

A root-owned journal and exact byte backups support old/new validation,
interrupted-write continuation and inverse publication. Readiness is revoked
before runtime replacement and published last. The global writer reservation,
provisioning lock and native operation lock fence the migration. Each mutating
retry checks disabled intent, stock guard status and a stock configd chain.
Final LS2 status must confirm the root process and verified recovery integrity.
The same candidate can be retried, rolled back using `--rollback-beta-startup`,
and explicitly reapplied after rollback. A different candidate cannot silently
replace an interrupted migration's payload.

A saved requested removal can be superseded only when the selected device
operation and intent match, its packages/done lists have no cleanup effects,
its predecessor is a completed deploy reservation, and every original component
journal is unchanged. The package and recovery inventories must still verify.
The exact old removal evidence is retained. Migration allocates a different
reservation ID, so an old cleanup continuation cannot regain authority. Host
removal records are archived and cleared only after the device confirms
application/preferences preservation. Later-stage or changed removal evidence
is refused.

The effective LG Home destination must be verified. If the defaultApps object
has no Home override, migration may materialize an explicit LG Home selection
while preserving all other defaults. A durable receipt precedes the single
submission and readback resolves a lost acknowledgement. A crash between receipt
and submission is deliberately ambiguous: it blocks automatic resubmission.
The private-runtime rollback remains available with Change Home off. Recovery
records must be retained until the destination can be verified. The response's
`home_changed=false` describes the effective destination; it does not assert
that no defaultApps record was written.

## Capability-based native continuation

The separate capability task is [PR #751](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/751),
source f16f4e92090697716f953f3aa36bc62f263aa591, included here for integrated
verification. Schema-3 boot continuation no longer compares a model/firmware
name tuple. It identifies the running init manager, verifies its executable and
shutdown observer, verifies the selected guard digest and requires its static
capability protocol. Old guards are refused before an unsupported command can
take their state lock. Legacy schema-1/2 ABI selectors and genuine stock-handler
byte identities remain distinct compatibility contracts; they were audited by
that task.

The guard supports systemd's stopping response and Upstart's exact running
shutdown/reboot job states. Normal running, stopped jobs, malformed, oversized,
unknown or timed-out observations fail closed. Explicit Off, triple-Home/emergency
and fault latches keep priority over normal-shutdown retirement. Static capability
reporting does not read or modify live guard state.

Native startup sources use the existing v1/v2 startup-policy parser and preserve
saved choices. Their CLI service entry no longer calls the profile coordinator.
After an authenticated new-session continuation, the native policy rechecks
intent, token, session, health, recovery integrity, normal startup and foreground.
It records an attempt before native launch so uncertain acknowledgement cannot
become a repeated launch. Live TV and verified LG Channels follow the TV choice;
YouTube requires its opt-in. HDMI, unknown sources and ambiguous foregrounds are
preserved. Same-session recovery and faults do not trigger a new startup launch.
Migration itself leaves Change Home off; the user explicitly enables it afterward.

## Firmware and process verification

Reused the official W19H 05.50.00 image and verified retained v1.21.0 package
from the earlier record. Archive SHA-256 is
`59ef18516657a7a058d4a8cf86dab14020eb25d40f794e328506bbc999a1b976`.
Additional factory files confirmed Upstart and the runlevel-triggered shutdown
and reboot jobs. Factory init.upstart and initctl ran in an isolated D-Bus
session under QEMU with harmless sleep jobs using the same runlevel triggers.
Both idle and active shutdown/reboot states were observed. Global RUNLEVEL was
not available, which is why the implementation queries the fixed jobs instead.
No destructive vendor shutdown scripts were run.

The new static ARM guard was built with the existing Zig ARM musleabi toolchain,
passed selfcheck/capabilities under QEMU and has SHA-256
`b7cdde421c9419bd5ade76253bebe1c6f4f4873eb9f08b57c931a1d6e47b732b`.
The native suite passed 51 tests, including normal shutdown, unavailable/invalid
observers, explicit Off and emergency retirement refusal.

Built an offline Root Beta runtime bundle with the new guard and the standard
builder's preliminary 0.0.1 version; this IPK was not installed. After later
private-engine-only changes, refreshed that source and its bundle digest without
rebuilding the unchanged UI/IPK. The candidate uses the integrated capability
and startup-policy source. Its final bundle-manifest SHA-256 is
`356ea5fd1a88702da6525d0b2ec6a052c4b70c03187a73a210a54ef2ef262285`. It is not a published or signed release artifact.

The full migration ran against the retained package in an isolated container
with factory ARM Node 0.12.2, vendor bootstrap, webos-service, LS2 hub/luna-send,
actual old/new ARM guards and the factory native Home executable. The original
148 installed files and saved startup-policy bytes matched after migration,
completed retry and inverse rollback. The actual retained JS service invoked the
migrated Python runtime and answered status with root=true and nested
integrity_verified=true. A second case started with an exact unstarted-removal
fixture and verified the new reservation and retained removal evidence.

The installed Python boot/source policy was replayed after migration with a new
startup session. The actual ARM guard performed boot retirement; the rearm and
foreground effects were modeled. Startup launched once, the repeated callback
never launched again, and a fault returned to restoration without rearming.
The Python ABI/binding, stock configd/settings replies, current init identity,
normal-start gate and board arming/foreground were modeled. Container Python
substituted for private ARM Python. These boundaries are not physical startup
acceptance. Containers disabled networking and dropped capabilities.

## Host, regression and review evidence

Focused migration/startup/CLI/i18n/diagnostic checks passed 137 cases. The
capability/provisioning suite passed 73 cases, including the 62 capability-runtime
cases from the separate task. The changed provisioning fixture now tests the
capability decision instead of a model tuple. The dependency suites for Root
provisioning, cancellation, clean removal, automatic recovery, CLI and passive
inspection passed 252 cases with one host-only skip. These groups overlap and
must not be summed as unique cases.

Regression coverage includes interruption after each publication boundary,
metadata reconstruction between release/bundle writes, authenticated temporary
prefixes during direct rollback, changed live/backup data, stale removal selectors,
source tampering, ordinary CLI dispatch, declined consent and host receipt retention.
A resumed migration repeats quiescent admission. Independent review found the
metadata, quiescence and temporary-file retry gaps; each was corrected and tested.
The uncertain Home-selection window is retained as an explicit limitation with
an available inverse. All 15 new installer messages and all practical guide
instructions were localized. `git diff --check` passed.

## Acceptance gaps

No physical B9 installation, physical Home/input/emergency sequence, sound,
standby wake, AC cold boot, Quick Start/snapshot, OTA or device rollback was run.
Actual device shutdown ordering and foreground policy need acceptance on the
selected final artifact. The original reporter's exact Home/style errors remain
unresolved by the available UI evidence. This task neither repeats recovery nor
removes or reinstalls the reporter's app. The implementation targets the next
candidate and does not alter the current frozen candidate scope or selected build.
