# Root health initialization and startup readiness race

Related issue: [#334](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/334).
This record contains source investigation and host reproductions, not another
user's installation report or physical-device acceptance.

## Evidence and causal chain

The published traceback names a generic health-context rejection. Root 0.8.4
uses one ValueError for seven predicates, so that traceback alone cannot identify
the first failing predicate or prove which process initiated recovery.

The source contains a reproducible initialization race:

1. The supervisor published `escape-ready` on reader READY, before publishing
   its first input health record. Bounded profile activation could then return.
2. `Coordinator.enable()` allowed twenty polls with 0.1-second sleeps for the
   first health record. A new supervisor process had not yet populated the
   private expected-package inventory cache. Its first `publish()` called
   `context()` and could perform cold package reads/decompression/validation
   before checking intent and writing the heartbeat.
3. If that validation took longer than the parent's wait, the parent failed to
   read health and used its existing fault recovery to disable intent and
   restore the binding/routing.
4. The delayed publisher then read the restored binding and raised the health
   context error. In this sequence the rejection is a consequence of the earlier
   startup timeout, not evidence that the matching binding was initially invalid.

A throwaway probe used actual Coordinator/Store/journal/context/watch orchestration,
with only external/provisioning/input boundaries simulated. Injecting three seconds
into the supervisor's first package-presence check produced a parent
FileNotFoundError, then `HealthContextError: binding-restored`, with final intent
disabled. Loading the original v1.7.1 `persistent_health.py` produced the exact
`ValueError: Inactive or stale health context` text under the same schedule.
This is an injected cold-validation schedule, not an ARM benchmark or a measurement
on the reporting TV. It establishes the source defect and a matching failure chain;
it does not establish that this was that TV's precise first cause.

## Correction

The bound supervisor validates the same context before starting the input loop,
then waits for a fresh guardian pulse. The guardian checks its context before its
first pulse so a cold validation cannot already consume the pulse's freshness.
The supervisor publishes `escape-ready` only after the first successfully validated
heartbeat. Each subsequent publication still checks all existing context predicates;
prewarming caches expected package inventories, never installed presence/authority.

Parent readiness and pre-input guardian waits use the existing trial journal's
deadline minus the existing twenty-second publication reserve. The independent
sixty-second trial is not renewed. Invalid, mismatched, excessive or exhausted
budgets fail closed. No Home publication is permitted by this waiting alone.
The two-second input watchdog remains unchanged, and an explicit elapsed check
prevents a slow callback from publishing readiness after that same bound.
The journal-derived preparation budget is an upper bound. Existing shorter caller
timeouts still apply (the service may terminate enable at thirty seconds). Such
termination can bypass Python exception cleanup: immediate rollback is not
guaranteed, and the detached guardian retains its original deadline/recovery duty.
A caller timeout is an uncertain outcome requiring status inspection, not a retry
signal. The reproduced three-second schedule fits every existing caller bound.

Legacy unbound READY behavior, PID/start-tick checks, key-up handling, triple-Home,
failsafe, restore-first boot handling and genuine fault recovery remain in force.

No dependency, permission, network endpoint, persistent record format or recovery
exception is introduced. The existing context-refusal diagnostics remain intact.
The affected Root runtime/infrastructure must be rebuilt and delivered through a
verified compatible complete update. A host-installer or launcher-only update
cannot retrofit this into installed runtime files. Versions/build selection remain
with the release coordinator.

## Verification

Ten focused startup cases pass: delayed first validation through actual persistent
activation and boot restart, health-before-readiness, initial validation-before-guardian-pulse,
readiness after the former three-second limit but within the trial budget,
failsafe, input loss before first heartbeat, missing guardian, invalid/exhausted
budgets, and a slow first heartbeat callback. The four primary regression cases
were run against unchanged base runtime files and failed before the correction.
Existing emergency fixtures now supply valid journal deadlines and model successful
preparation before injecting a later health-refusal failure.

Independent read-only source review found no actionable findings. The affected
`scripts/test.sh tv-runtime installer` run exited 0: Root 1,148 cases, System Updater
132, installer 805 (75 reported skips), plus selected private-filesystem, native/JS,
Homebrew, input/gesture/watchdog and generated-runtime checks. Skips were not run.
The boot-restart case was added after discovery in that broad run; the final focused
run includes all ten startup cases. Exact Node 0.12.2 was not configured, so this is
not new evidence for that runtime. `npm ci` passed (281 packages, zero reported
audit vulnerabilities); changed runtime modules parse with Python 3.9 grammar.
Changed guide targets resolve and `git diff --check` passes.

The initial sandbox run stopped on a loopback WebSocket fixture (`listen EPERM`)
before product checks; the authorized run permits local loopback. No TV was contacted.

## Limits

Edition: Root. Host verification platform: macOS ARM64. Device model, firmware/webOS,
remote, physical install/activation, Home/key controls, audio, standby, cold boot,
OTA and retained rollback: untested. Source tests are not acceptance of the QNED
model or any other device. Retain #334 open until its original outcome is established;
do not publish the injected schedule as an observed user-device cause or success.
