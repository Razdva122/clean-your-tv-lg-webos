# Root Edition test plan

> **1.11.0:** [exact final C3 QA](../docs/history/2026-11-07-release-1.11.0-tv-qa.md) records final installer setup, controls/audio, standby, key-up, emergency return and verified full removal after an ordinary OS reboot. The maintainer requested publication with icon issue394 non-blocking and edition-transition guidance deferred. AC cold boot was waived; OTA/retained rollback and other untested paths are not passes.

> **1.10.0:** [exact final build and scoped installer acceptance](../docs/history/2026-11-07-release-1.10.0-final-acceptance.md). Maintainer-directed C3 removal/reinstallation, controls/audio, standby, ordinary reboot and escape are recorded separately from untested No-root, AC cold start, OTA/retained rollback and other-device paths. The maintainer accepted that bounded release scope; untested paths are not passes.


Historical result (2026-10-27): [corrected C3 acceptance and manual physical rollback](../docs/RELEASE-1.4.0-ACCEPTANCE.md) passed in the recorded scope. The maintainer accepted #90 and requested closure. Pending statements below describe earlier investigation checkpoints; other hardware remains unverified.

For current setup use [installation](../docs/INSTALL.md), [update preparation](UPDATES.md)
and [current release scope and acceptance](../docs/RELEASE-1.9.0.md). The
[1.4.0 acceptance](../docs/RELEASE-1.4.0-ACCEPTANCE.md) remains historical; the
Root 0.6.1 standby failure in [#171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171)
is unresolved. Root 0.7.0 has scoped signed-update, active retained-rollback,
physical controls/audio, startup and emergency/fault/failsafe evidence in the
[current artifact-bound acceptance record](../docs/history/2026-11-02-release-1.6.0-final-acceptance.md).
The owner accepted the documented standby presentation limitation for 1.6.0;
this does not establish a fix for #171. See
[Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases) for published downloads.
This is a developer test plan; bounded trials below are not a normal installer
Keep/confirmation step. Dated checkpoints retain their original builds and do
not override later issue evidence or accept new candidate artifacts.

Current1.9.0 C3 update, controls/audio, standby, cold-start and retained rollback results are in the [artifact-bound record](../docs/history/2026-11-06-root-wake-key-release.md#final-cold-start-retained-rollback-and-android-upgrade). Settings status #347 remains a deferred failure; other-model claims remain unverified.

## When to repeat this matrix

Select affected scenarios using the [scoped release acceptance rules](../docs/RELEASE-FLOW.md#scoped-physical-acceptance-and-retry-recovery).
Bind every result to build run/attempt, artifact SHA-256 and TV/firmware/state.
Evidence-only edits preserve the same selected bytes and do not require another
physical run. Carry a prior scenario only when all its artifacts and preconditions
match; source similarity alone is insufficient. The tool's broad categories are
review prompts. Select individual cases by changed behavior, package entrypoints and dependencies; a Settings/catalog/font change
does not automatically select cold boot, observer suspension or failsafe. Document
why other cases are not selected; do not call them passes on the new package.
Unisolated dependencies require investigation or a broader relevant case set.
Unresolved failures and untested paths retain their original status. The stage requirements below still apply to
any scenario selected for retest.

## Local checks (no TV required)

```sh
python3 -m unittest discover -s root-edition/tests -v
scripts/test.sh
```

The Python suite checks doctor parsing and privacy filtering, manifest validation,
exact-byte rollback decisions, preservation of unrelated fields, tampered plans,
conflicts and refusing to overwrite output files. Preview tests also verify
separate identity, exclusion of personal inventory and helper scripts, rejection
of indirect source files and reproducible content hashes. It does not emulate SAM,
registration-cache updates, power loss or Homebrew failsafe.

Existing launcher/helper tests remain part of the normal suite. Root tooling is
not included in the production IPKs by `scripts/build.sh`.

## Hardware gates (user present)

This table is a case library. Run the affected rows selected in the candidate
plan, preserving any existing release blocker. Independent recovery readiness
is required before changes; actual forced recovery/rollback is not repeated
for every unrelated UI update.

Before each stage, verify the baseline, off-device backup and independent recovery.
Use one bounded change at a time. Do not count a successful API reply as a visible
or cached-state result.

| Stage | Required evidence |
| --- | --- |
| Manifest registration | Only Home category changed; getAppInfo and actual category-based launch both agree |
| Metadata rollback | Exact original bytes restored; SAM registration matches original; settings untouched |
| Short Home | From an ordinary application screen, returns to real Home while the interception helper is stopped |
| Back Cancel | Back still navigates in-app; Cancel leaves the app running |
| Back exit | Confirmed exit returns to real Home; observe any LG flash |
| Other controls | Arrows, held arrows, OK, volume, pointer, wheel and app launches work |
| Emergency behavior | A documented escape returns to LG and restores routing, with no automatic re-enable |
| Timer/crash recovery | Forced activation/worker failure returns all routing and metadata state to baseline |
| Startup | Normal reboot, quick standby and cold start preserve controls and intended startup |
| Failsafe | Recovery runs with ordinary init.d unavailable; normal operation resumes after leaving failsafe |

Repeat application-exit tests across multiple apps. A dialog intercepting Home is
not the same case as Home pressed from an ordinary app screen. Record the screen,
transaction timing and whether the helper was actually stopped.

## Report results

Use the Root Edition issue template. Include model, firmware, component versions,
which exact stage ran, expected/actual behavior and whether rollback succeeded.
Review/redact doctor output. Do not attach root credentials, pairing tokens,
SSH keys, private backups, firmware images or complete device logs.

## Integrated candidate acceptance record

For each selected package, record its `bundle.json` SHA-256 before starting.
Use the linked current acceptance record for completed exact-artifact scenarios;
repeat only cases selected by changed bytes or preconditions. The items below
define evidence for selected cases, not mandatory repeated installations or a
blanket statement that every case is pending. Use a supported update when that
is the chosen transition; do not uninstall/reinstall just to populate the list:

1. Inspect existing recovery/updater state before replacing anything; check the
   candidate payload and record its exact source/build. Do not bypass retained
   updater or unresolved-operation checks.
2. Use the supported interactive setup; confirm candidate hashes, service root
   identity, independent recovery and automatic Home activation.
3. Confirm native Home, Back Cancel, confirmed Back exit and other controls with
   the No-root Helper stopped. There is no normal installer trial/Keep step.
4. Exercise Change Home off/on and triple-Home escape; verify LG destinations and
   user-visible control, with no automatic re-enable after emergency off.
5. Repeat the startup/recovery matrix with the user present, then separately
   prepare supervisor upgrade/rollback and Homebrew failsafe tests.
6. Exercise interrupted installation and uninstall only in a prepared test;
   preserve conflicting/unknown state for inspection.

Local tests cover independent installer completion, unknown outcomes, exact
payload hashes, recovery provisioning and the helper stop latch. They cannot
prove delivery of a boot activity on this firmware. Explicit permanent activation is now implemented and tested on one C3; repeat
the affected lifecycle and emergency scenarios on the selected final artifacts;
carry earlier evidence only under the identical-hash/precondition rule above.

## Triple-Home emergency regression matrix

`setup.py emergency-trial --ssh my-tv` is an explicit bounded test, not permanent
activation. Stop the No-root helper first. The command requires the ARM32 input
ABI and the previously observed `LGE M-RCU - Builtin [0]` channel. Input is opened
read-only: no grab, injection or system-library patch.

Three completed Home presses within two seconds request recovery. Each press must
last 40–500 ms; repeats, long holds, another key and invalid sequences reset it.
The observer runs outside the web interface. A separate supervisor monitors its
private heartbeat pipe; input loss, exit or a two-second stall requests verified
rollback. The original independent 60-second guardian remains armed. Failure to
acknowledge observer readiness prevents Home publication. Production helper state
is never changed.

Select the following supervised fault matrix when input/gesture recognition,
observer/supervisor lifecycle, emergency routing or their dependencies change.
It is not an automatic gate for unrelated icon, font or status text changes.
When selected, use the final package:

1. Ordinary Home and navigation still work; triple short Home restores LG Home
   before the deadline without magnification.
2. Suspend only the candidate renderer after verifying its process identity.
   Triple Home must still restore routing. Always resume that exact process in
   cleanup; never suspend WebAppMgr, system UI or the production launcher.
3. Suspend only the diagnostic observer. Its supervisor must restore routing
   before the independent deadline.
4. Confirm the production launcher and explicit helper resumption work afterward.

Local tests exercise the gesture, synthetic input pipe, real stopped/killed child
processes, malformed health messages, startup refusal and transaction-bound
recovery. These tests alone do not establish TV key delivery or frozen-renderer recovery;
see RELEASE-ACCEPTANCE.md for the earlier hardware evidence.
Permanent-mode supervision is a separate path; test it through `enable` or
turning **Change Home** on, using the same emergency and fault matrix. No Keep
confirmation is required by the current normal activation flow.

<a id="unreleased-cold-start-correction-104"></a>
## Historical cold-start investigation (#104)

Test initial foreground separately from short Home routing. See the
[cold-start investigation, source policy and remaining device matrix](../docs/development/ROOT-COLD-BOOT.md).
At this investigation checkpoint, the two existing-source AC-off results did
not validate the then-new nonce or optional foreground request. The #90
checkpoint below retains its original scope; it does not describe the later
Root 0.6.1 standby failure in #171. Preserve explicit off in every retest.

## Candidate wake-key release settling (2026-11-06)

The candidate reader waits up to 750 ms for an initially held key state to clear.
It discards the initial historical queue once. Fresh Home down/repeat while
waiting cancels pending activation (`startup / home_activity`); key-up permits
settling, and fresh malformed input fails closed. Normal gesture recognizers are
created only after all keys are released. No READY or PING is sent during this interval; the
existing independent two-second supervisor deadline is not extended. A persistent
held flag, input error, invalid channel or exhausted drain still fails closed.
Emergency/off state is never automatically re-enabled.

This mitigates a transient held-key startup condition. It does not identify the
physical key or repair a persistent/stale input bitmap. The renewed C3 failure
and remaining exact-package tests are recorded in the
[dated investigation](../docs/history/2026-11-06-root-wake-key-release.md).
Historical diagnostic-only behavior below retains its original scope.

<a id="issue-90-intermittent-wake-input-startup-diagnostic-source"></a>
## Historical issue 90: intermittent wake input startup

At this diagnostic checkpoint, the first failed standby on Root 0.4.0 remained unresolved. Its `input_lost`
recovery occurred in durable phase `starting`; subsequent successful standby and
AC-off tests do not identify that failure's cause. A held wake key is a hypothesis.

The diagnostic reader writes one `input-observer-fault` JSON record to stderr
(the existing private `emergency.log` under normal supervision) before its
unchanged `LOST` health message. Fixed `phase`/`reason` codes distinguish:

- `startup`: `eof`, `drain_limit`, `keys_held`.
- `active`: `eof`, `partial_event`, `invalid_timestamp`, `events_dropped`,
  `invalid_key_value`, `drain_limit`.
- Both phases: `read_error` with numeric `errno`, preserving the existing
  exception/observer-exit recovery path. Device inspection also found repeated
  active-read `ENODEV` (19) exits, including shutdown-classified exits and a later
  unclassified exit. These do not establish the original startup cause.

No key codes/history, addresses, app inventories or event payloads are recorded.
Discovery, ioctl exceptions, observer exit and heartbeat timeout still use
the existing supervisor path; absence of this new record is not proof of held
keys. This change adds no readiness wait, retry or automatic re-enable, and does
not change ABI/channel validation, triple-Home, Long Back or watchdog deadlines.

For a supervised retest:

1. Record exact installed source/bundle hashes and verify recovery, current
   intent and independent guardian. Do not replace retained runtime files or
   edit integrity receipts by hand. The diagnostic runtime needs the supported
   checked setup/update path; an app-only replacement does not install it.
2. With confirmed active Home control, turn off by remote, wait 30 seconds,
   wake, open Emby and press Home briefly. Record actual destinations and
   read-only intent/guardian/recovery results. Repeat standby separately from
   a genuine AC-off cold boot; keep every failure alongside successful runs.
3. On failure, retain the private emergency log, correlate the observer fault
   with its supervisor transaction and `bound-exit-decision`, and share only
   reviewed fixed codes. A pre-READY `keys_held` record establishes the failing
   condition on that attempt; it does not identify which key or prove why it
   remained down. Do not change policy based on the old generic log alone.
4. Verify explicit off and triple-Home still stay off after wake/fault. Any
   later enable must be explicit. Do not close issue 90 based on diagnostic
   delivery or successful local tests.

Local regression: `python3 -m unittest discover -s root-edition/tests -p 'test_emergency*.py'` covers all nine explicit-loss branches, startup/active read errors, full-log
fallback and unchanged wire signals, plus gesture/recovery/watchdog tests. No new user setup/control flow is
introduced; localized user guides retain the known standby limitation.

### Candidate: validate health before startup readiness (#334)

A cold supervisor can spend longer than the parent's initial heartbeat wait in
private expected-package validation. Publishing `escape-ready` on reader READY
alone let the parent time out, restore intent/binding, and make a late publisher
raise `Inactive or stale health context`. The host regression reproduces that
sequence with a three-second validation delay; it is not a measured TV latency.

Bound startup now validates its context before starting the input watchdog and
waits for a fresh guardian pulse. The guardian performs its initial context check
before claiming that pulse. `escape-ready` follows the first validated heartbeat.
Parent/guardian readiness waits use the existing journal deadline minus the
existing twenty-second publication reserve; the sixty-second trial is not extended.
Existing shorter caller timeouts still apply; a timeout requires status inspection,
with the detached guardian retaining its original recovery duty. The two-second
input watchdog and all context predicates remain in force. A slow
heartbeat callback cannot publish readiness after that same watchdog bound.
Expected-inventory prewarming never caches installed presence or lifecycle authority.
Legacy unbound READY handling and emergency gestures retain their original contract.

Run `python3 -m unittest discover -s root-edition/tests -p test_health_startup.py`
and the existing emergency, guardian, health, recovery and boot suites. Cover cold
validation, first-pulse/readiness ordering, exhausted/invalid startup budget,
missing guardian, failsafe and input loss before the first heartbeat. No user
command, control, permission or journal format is changed. Rebuild and deliver
verified Root infrastructure; updating the host installer alone cannot retrofit
this correction into an old retained runtime. [Source proof and limits](../docs/history/2026-11-06-root-health-startup-race.md).

### Health-context refusal diagnostics (unreleased, #334)

`HealthContextError` retains ValueError recovery semantics and distinguishes
`transaction-mismatch`, `binding-restored`, `generation-mismatch`, `token-mismatch`,
`boot-mismatch`, `phase-inactive` and `failsafe-present`. The publisher supervisor
appends `health-context-rejected` to its existing private emergency log before
calling `recover(..., 'supervisor_error')`. It contains only the fixed reason,
process ID and monotonic uptime. `emergency-recovery` includes the same process
and time fields for correlation. Diagnostic write failure cannot skip recovery.
The wire READY/PING protocol, two-second heartbeat bound and emergency controls
are unchanged; bound startup readiness is gated as described above.

The code names the first failing predicate in that observation, not necessarily
the first failure across processes. A `binding-restored`/`phase-inactive` record
may follow another process's recovery; correlate the original attempt's preceding
observer, guardian and `bound-exit-decision` events. No token or boot identity is
included in the new record. Raw logs still need private inspection and redaction.
Host tests do not establish the original device cause. Rebuilt, verified runtime
delivery is required; an app-only update does not change retained runtime files.

2026-10-27 investigation: on the saved C3 test target, read-only CLI inspection
verified recovery integrity and restored routing with intent disabled. After
explicit user activation, active intent/guardian and released keys were verified.
One supervised remote-off / 30-second standby / wake / Emby / short-Home cycle
returned to Clean Your TV; subsequent readback again verified active intent,
guardian and recovery integrity. The appended log classified observer exit as
normal shutdown and retained intent. The installed observer hash matched source
`1e6e92ce` from the original report; the diagnostic reader was **not installed**.
This is another successful repetition of existing code, not validation of a fix
or a new compatibility claim. Raw logs and connection details remain private.

## Root 0.4.0 retained-runtime transition (#111)

The new coordinator must verify the installed release SHA/app/package identity
before allowing the exact published 0.4.0 runtime set without `audio_recovery.py`.
It must still reject altered bytes, incomplete legacy/current inventories and
foreign version metadata, before disabling either updater. Repeat validation
immediately before the old driver invocation. Regression checks live in
`tests/test_root_driver_compatibility.py` and the removal effect-order fixture.

Source `3eef546b` failed supervised C3 preparation at this boundary; supported
restore returned LG Home and package versions were unchanged. The original immutable
request was subsequently continued using the complete separately verified fixed
coordinator; independent status confirmed complete/current removal. Original
Root state is retained and updater states archived. No new-runtime cold-boot
acceptance is established. See the [candidate transition record](../docs/RC-1.4.0-TESTING.md#root-040-transition-regression-111).


<a id="exact-9194-first-ac-failure-and-shutdown-regression-coverage"></a>
## Historical 9194 first AC failure and shutdown regression coverage

Exact CI40489987476/source9194c16a Root0.5 installed on the maintainer's C3.
Active intent/guardian/recovery and owner-confirmed Emby/Home/basic controls
passed before AC testing. The first new-runtime remote-off10s/AC-off30s cycle
failed: LiveTV remained after one minute without Home, ENODEV revoked intent,
and stock LG Home/controls were restored. Root was left disabled after that attempt.

A separate passive Root-disabled diagnostic cycle proved Active Standby before
input loss and systemd stopping afterward. It does not accept standby or establish
when the original failed-cycle input loss occurred. The diagnostic observer was
removed. [The technical record](../docs/development/ROOT-COLD-BOOT.md) separates
these facts and the session-race hypothesis from hardware acceptance.

Host regressions cover fresh ON→OFF subscription transitions, initial/stale OFF,
unknown/unsubscribed/malformed/lost streams, cache expiry, actual child cleanup,
old-session writers and observer exits before boot dispatch. For that shutdown
fix, the selected regression set also required escape, explicit off, package
loss, failsafe, same-session input faults, unconfirmed trials and restore-before-gate.
This is the historical scope of that mechanism change, not a full physical pass
for every later shared-file edit. Rebuild coherent artifacts after product changes
and select affected cases using the current dependency review above. Unisolated
impact requires investigation or an appropriate broader case set. Never re-enable
fault-disabled Root automatically or edit installed runtime/receipts.


<a id="candidate-original-130-system-ota-115"></a>
## Original 1.3.0 System OTA contract (#115)

[Compatibility contract and offline evidence](../docs/development/ROOT-OTA-13-COMPATIBILITY.md)
cover the original supervisor, exact paths/LS2 plan, signed current-runtime
validation, update and both rollback timings. The test fixture replaces TV RPC,
SDK installation and runtime suspension/finish boundaries; it does not accept
physical controls or audio. Coordinate a future C3 test of the actual frozen
signed upgrade, preserved apps/settings, Home/emergency state and retained rollback.
Do not borrow the earlier fresh-install/manual-rollback acceptance for this path.
