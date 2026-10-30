# Root Edition test plan

Historical result (2026-10-27): [corrected C3 acceptance and manual physical rollback](../docs/RELEASE-1.4.0-ACCEPTANCE.md) passed in the recorded scope. The maintainer accepted #90 and requested closure. Pending statements below describe earlier investigation checkpoints; other hardware remains unverified.

For current setup use [installation](../docs/INSTALL.md), [update preparation](UPDATES.md)
and [current release limits](../docs/RELEASE-1.5.3.md). The
[1.4.0 acceptance](../docs/RELEASE-1.4.0-ACCEPTANCE.md) remains historical; the
Root 0.6.1 standby failure in [#171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171)
is unresolved, and candidate Root 0.6.2 adds diagnostics rather than a proven fix.
This is a developer test plan; bounded trials below are not a normal installer
Keep/confirmation step. Dated checkpoints retain their original builds and do
not override later issue evidence or accept new candidate artifacts.

## When to repeat this matrix

Select affected scenarios using the [scoped release acceptance rules](../docs/RELEASE-FLOW.md#scoped-physical-acceptance-and-retry-recovery).
Bind every result to build run/attempt, artifact SHA-256 and TV/firmware/state.
Evidence-only edits preserve the same selected bytes and do not require another
physical run. Carry a prior scenario only when all its artifacts and preconditions
match; source similarity alone is insufficient. Behavioral JS and unknown/shared
changes conservatively select the full matrix. Unresolved failures and untested
paths retain their original status. The stage requirements below still apply to
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

For the new package, record its `bundle.json` SHA-256 before starting. Earlier
private tests do not count as acceptance of this build. Run these steps together:

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

Required supervised tests on the final package:

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
old-session writers and observer exits before boot dispatch. Escape, explicit
off, package loss, failsafe, same-session input faults, unconfirmed trials and
restore-before-gate remain mandatory. Rebuild coherent artifacts after product changes
and repeat the affected supervised matrix (unknown/shared impact requires the full matrix); do not re-enable
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
