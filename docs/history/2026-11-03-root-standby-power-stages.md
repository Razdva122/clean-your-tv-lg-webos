# Root standby power-stage reproduction — 2026-11-03

## Scope and environment

Owner-supervised investigation of #171 on the maintainer C3. The owner requested
checking the TV and resolving the issue, then operated two remote-power cycles.
The session crossed local midnight; preparation started on November 2.

- Live readback: OLED55C3RLA, firmware 43.21.71, webOS SDK 11.2.0.
- Root app 0.7.0 and Root Updater 0.4.0, read from installed app metadata.
  Full installed release/IPK provenance and System version were not requalified.
  The old infrastructure `release.json` retains historical metadata; it is not
  used to infer the current package release.
- Installed `shutdown_state.py` and `intent_runtime.py` hashes match the source
  handlers examined for this failure. This is code identity, not full package
  acceptance. Installer/diagnostic host: macOS ARM64; remote model unknown.
- Existing pinned SSH profile; no pending host installer operation. All device
  operations in this investigation were reads/subscriptions. No package, Home
  preference, recovery receipt or firmware setting was changed.

## Expected and actual

Precondition: Home replacement was active/enabled; native input phase active;
fresh input and guardian records were present. The owner opened LG Channels,
switched off using the remote for the requested 30 seconds, switched on and
observed for the requested minute without Home/Back or another app launch.
Those intervals were instructed, not independently timed.

Expected: the existing guarded standby policy automatically presents Clean.
Actual: the owner reported LG Channels and no automatic Clean in both attempts.
In the captured readbacks the intent stayed active, generation/binding and startup
identity were unchanged, input/guardian health remained fresh, and no new bound
exit appeared. A separate normal-start marker was present and failsafe absent.
This is a same-session presentation failure, not a new reproduction of the old
ENODEV/disabled-intent exit. Neither historical failure is erased.

The second attempt had an independent continuous firmware subscription. Its
fixed, redacted power sequence was:

1. `Active`, acknowledged subscription.
2. `Active`, `onOff=off`, successive string `processing` values:
   `Request Power Off`, `Request Active Standby`, `Prepare Active Standby`.
3. `Active Standby`.
4. `Active Standby`, `onOff=on`, successive preparation values:
   `Prepare Power On`, `LastInput Ready`, `Screen On`.
5. `Active`.

The production power snapshot ended at `active-observed`, with zero Off/wake
counts. The existing boot decision was unchanged; no wake presenter invocation
was recorded. Private raw replies, identities, timestamps and snapshots remain
outside Git. A separate live foreground read confirmed the native Channels app.

## Cause and source correction

`PowerState.event` called `close('onoff-off')` at step 2, erasing the already
observed ON baseline. Step 3 consequently could not record a proven shutdown
edge; step 5 could not request wake presentation. Replaying the recorded sequence
against the original source fails at the expected missing proof assertion.

The focused change clears previous proof, cancels pending wake revisions and
resets pending sleep during preparation while retaining only an ON already
observed in this same stream. Only the later explicit standby/power-off state
creates proof. Preparation followed directly by Active never requests a wake.
Initial Off, unknown state and closed streams cannot invent a prior ON. Existing
session, input/guardian, foreground, failsafe, explicit Off and emergency checks
remain authoritative; no automatic re-enable or launch retry is added.

Host validation: the new replay failed before the runtime edit and passed after
it. All 54 shutdown-state, 91 presentation, 21 lifecycle and 209 persistent tests
passed. Independent source review found no actionable defects and separately
passed the initial 53 shutdown tests. The broader Root run initially lacked host
fontTools; its prepared-environment result is recorded in the implementation PR.

## Remaining acceptance

The corrected source has not been installed or physically accepted. No passing
standby result, first-screen guarantee, cold boot, audible sound, manual Home,
key-up, watchdog, triple-Home, Off persistence, OTA or rollback result is claimed
for the fix. No new physical controls/audio result was requested merely to fill
this record. Current TV preference remains active; no recovery state was cleared.

A signed versioned candidate must repeat affected standby and safety acceptance.
The current release candidate is unfrozen with unselected versions; its coordinator
owns inventory, versioning and build selection. Source integration alone cannot
close #171. The earlier no-proof observer-exit path remains a separate acceptance
boundary even though the newly captured preparation sequence explains this
same-session failure and can also suppress shutdown proof.
