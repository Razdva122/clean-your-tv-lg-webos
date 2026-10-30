# Root standby investigation (#171)

This is preparation for the unresolved [Root 0.6.1 standby report](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171),
not a standby fix or a hardware acceptance record. No TV operation was performed
for this change. Published v1.5.0 remains subject to its documented standby limitation.

## Established evidence and blocker

The maintainer-owned OLED55C3RLA, firmware 43.21.71 / webOS SDK 11.2.0,
Root 0.6.1 / shared UI 1.6.0, Root Updater 0.3.3 and System Updater 1.1.2,
left LG Channels visible after ordinary remote-off/wake with Home replacement
previously enabled. The installer host was macOS ARM64; remote model unknown.
The separate AC-off cold-start observation showed LG Channels first and then
Clean Your TV, and passed in that scoped observation window. Neither cold boot
nor a package install establishes standby acceptance.

The recorded Root IPK SHA-256 is
`419de466e43095b426d9652c102fabd2c3ebd5a58c4dbb0f4928056b6d4b9f64`;
source `1f41a9cf3d66a6858de71e91dcebcef417e81bd4`, build 41036602865/1,
QA signing 41037318681/1. The current failure has no captured matching power
stream, wake decision or post-wake intent/guardian/input-health state. Earlier
Root 0.6.0 readbacks established retained routing in their own cycles, and the
historical closed #90 concerned a different input-readiness failure. Neither
proves the cause of this 0.6.1 observation. See the
[original findings](../history/2026-10-30-supervised-candidate-findings.md).

Source and host fixtures establish that the current implementation already
handles a continuous acknowledged Active → Active Standby/Power Off → Active
edge and uses the exact metadata-verified native Channels policy for boot and
wake. It preserves unknown applications, explicit off, emergency/failsafe,
uncertain input/health and native last-input preference. There is no evidence
justifying a broader app predicate, retry, reactivation or safety bypass.

Two source-level diagnostic gaps are reproducible: early `present_wake` refusals
return before the old audit call, and the power reader previously retained no
record distinguishing an unobserved edge from EOF, an initial timeout or an
invalid stream. The draft corrects these diagnostic gaps while leaving launch,
input, watchdog and recovery policy intact. The original standby cause remains
unknown until matching observations are available.

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

A later, separately authorized maintainer QA run needs the same-cycle private
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
