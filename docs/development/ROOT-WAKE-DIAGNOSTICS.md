# Root standby investigation (#171)

This tracks the unresolved [Root standby report #171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171).
Published v1.6.0 includes wake and shutdown-decision diagnostics, not a verified
fix of the original failure. No TV operation was performed in the post-release
source investigation below.

## Established evidence and blocker

The public issue and dated records contain the device, firmware, component,
installer and exact-artifact scope. Keep these distinct observations:

- The original remote-power cycle left LG Channels visible. The separate AC-off
  cold start eventually reached Clean; it does not accept standby.
- The [October 31 QA](../history/2026-10-31-release-1.5.3-signed-root-qa.md)
  includes both an earlier different-session ENODEV/disabled-intent failure and
  a later same-session standby pass. The later pass does not fix the earlier one.
- The [November 2 QA](../history/2026-11-02-release-1.6.0-hardware-qa.md)
  retains the first On-standby attempt as failed/unaccepted: a matching
  `observer_exit` decision had active/enabled intent, the same startup session,
  Home present, no failsafe, and no shutdown proof. Adjacent errno 19 was not
  transaction-tagged; it does not prove ordering or why that observer exited.
  Reported interference from another application remains an unproved explanation.
- The separately authorized repeat reached Clean after an unmeasured initial
  Channels screen through a new-session guarded startup fallback. Native Home
  autolaunch, the owned EIM entry and remembered Root selection were present.
  Immediate first-screen standby behavior remains unaccepted. The separate true
  AC-off check from running Clean showed Clean first within its recorded scope.

### Post-v1.6.0 source trace (2026-11-02)

`emergency_reader` reports input read errors and exits; pipe EOF becomes
`observer_exit` in `emergency_watchdog`. `bound_exit` preserves active intent only
with its existing shutdown/session/package/failsafe checks. In the observed
same-session, no-proof branch it disables intent, restores routing and cleans
owned native input. A later normal startup must keep that Off authoritative.
Neither ENODEV nor a subsequent successful power cycle supplies missing proof
for the failed cycle.

A continuous acknowledged Active → Active Standby/Power Off → Active edge in one
session uses `present_wake` without rearming. A changed startup identity uses
restore-first boot dispatch, the positive normal-start marker plus cleared
failsafe, fresh input and guardian checks, then one optional foreground fallback.
This is a later path than firmware's first-app selection; its success cannot
promise Clean as the first screen. Native EIM is retained across enabled boot
recovery, and an already active registration intentionally does not overwrite a
subsequently selected input. Re-registering on wake, adding retries or extending
the app predicate has no demonstrated causal basis here.

`test_wake_lifecycle.py` exercises real intent, binding, profile restoration,
volatile session identities, normal-start markers, input/guardian records and
native EIM receipts together. Firmware RPCs and physical input/process startup
are simulated. Separate cases cover same-session wake, new session with reused
kernel ID, changed-kernel cold boot, no normal marker, failsafe, explicit Off,
emergency, package loss and no-proof observer exit. Negative cases verify owned
native cleanup and that a later normal session does not auto-enable Home.
Existing power/parser, presentation and native-input suites cover malformed or
lost streams, metadata/foreground rejection, lease expiry and bounded operations.
These are host safety regressions, not a reproduction of firmware timing or a
product fix for #171.

The missing contract is the matching **pre-exit** cause and power-stream lifetime:
whether a genuine shutdown edge/request was observed before the failed observer
ended, and why no proof survived until that decision. For delayed presentation,
matching native first-app selection and startup/gate timestamps are needed to
separate firmware selection from the later fallback. Current post-wake EIM state
and missing volatile files cannot establish those earlier events. Do not change
input-loss, shutdown, emergency or normal-start gates to turn this gap into a pass.

## Private diagnostic records

The existing root-owned `boot-decision.json` now records **every invoked** wake
presenter, even an early refusal. `event=wake-presentation`, `outcome`, `boot`,
monotonic `uptime` and `context.stage` distinguish cancellation, session,
intent, combined health/routing, startup setting, foreground/metadata, final
input/guardian/intent checks and launch. A stage names the last check reached;
it does not claim the check passed or identify an exception's exact cause.
Foreground context retains only fixed classes and the existing boolean/unknown
first-app match. An acknowledged launch is not proof of sustained foreground.
This existing single decision file can be overwritten by a later boot/wake;
inspect its event, session and timestamp before attributing it to a cycle.

The power reader writes one atomic mode-0600 snapshot at
`/tmp/clean-your-tv-root-health/<transaction-sha256>.wake`, in the existing
trusted volatile health directory. Its schema-1 fields are:

| Field | Interpretation |
| --- | --- |
| `transaction`, `boot` | Private binding to the observer's transaction/session; compare locally with current state. |
| `uptime` | Last recorded monotonic time; a stale snapshot does not prove a live observer. |
| `event` | Fixed event such as observing, initial-state, active-observed, off-observed, wake-observed, processing, unknown-state, incomplete-frame, EOF, stopped, initial-timeout, child-exited, session-changed or invalid-or-unavailable-stream. |
| `primed`, `on`, `asleep`, `revision` | Local power parser state, not input/guardian health or active Home routing. |
| `off_count` | Distinct observed OFF transitions after ON; repeated OFF pushes do not add an edge. |
| `wake_count` | Eligible complete power edges; does not establish that a worker launched or that Home appeared. |

Duplicate Active snapshots do not write this diagnostic. Stream teardown keeps
the final reason and counters while revoking authority exactly as before. The
snapshot has no read path in authorization, recovery or launch. Writes use the
volatile directory without fsync; symlink/unsafe targets and I/O failures are
ignored. No new durable state, network endpoint or permission is added.
A missing file can mean older runtime, no observer or diagnostic I/O failure;
it must not be interpreted as proof that no power event occurred. A process or
snapshot termination may leave only the previous snapshot, without a final reason.

## Remaining evidence and acceptance

The existing issue evidence request remains applicable; do not repeat it as a new
request or start a TV session from this document. A later, separately authorized
maintainer QA run needs the same-cycle private
power snapshot and wake decision together with intent phase/enabled status,
matching session/binding, effective Home routing, input freshness, guardian
freshness/process identity, failsafe/package availability and native Home
preference. Read the records before a manual Home/app action or new boot can
replace the evidence. Preserve unknown/untested fields; do not clear emergency,
failsafe, bindings or recovery state to obtain a passing result.

Share only a concise redacted interpretation after inspecting the evidence.
Keep session/transaction values, raw device logs, addresses, credentials, private
paths and app inventories private. Existing diagnostics/report-consent rules
still apply. This document requests no immediate TV action or background monitor.

Future artifact-bound acceptance must separately observe standby automatic
presentation without Home input, manual Home routing and controls/audio,
triple-Home emergency release, key-up/watchdog behavior, explicit-off persistence
and cold boot where affected. CI/host fixtures cannot certify any of these
physical results. Keep #171 open until its actual cause and affected acceptance
are resolved; diagnostics alone do not deliver its reported fix.
