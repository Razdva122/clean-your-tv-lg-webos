# Root HDMI audio recovery

Implements the approved [eARC research proposal](../research/2026-10-26-earc.md),
separately from PR #27's Bluetooth/microphone controls. Controls shipped in 1.4.0.
The next-candidate OTA compatibility correction (#115) changes their packaging
and internal RPC route, with no new user controls or hardware acceptance.

## Controls

Home settings → HDMI sound offers Reconnect eARC only with Active power, confirmed
pure configured/current external_arc and eArcSupport on. It writes off, waits
about two seconds, restores on and checks readback. ARC-only/off, combined/WOW
Orchestra, optical, Bluetooth, missing and contradictory states are skipped.
Restore HDMI output replaces the action for a confirmed fallback to tv_speaker.
No permanent route pinning, volume control or AV-sync adjustment is added.

Recover after power-on is experimental and initially off. Enabling it does not
reset sound. It requires eligible eARC and a supported power subscription, and
may interrupt healthy audio. The UI separates saved policy from a live observer.
Back closes the panel during an operation while the private runtime finishes.
After an RPC timeout check status. Interrupted/uncertain transactions require
Restore saved eARC setting: use it only if eARC on is your desired setting.

## Runtime and authority

The runtime places the audio transaction engine and detached worker in
`runtime/cli.py`, independent of the UI/JS RPC lifetime and Home-button controller.
`service/handlers.js` permits only fixed operations, exact keys/booleans and uid0.
Audio state uses `status` with `{audio:"status"}`; explicit configuration/recovery
uses `enable` with `{audio:"configure",enabled:boolean}` or
`{audio:"recover",operation:...}`. The read-only route cannot write settings.
This preserves the published 1.3.0 LS2 plan and executable destination inventory.
The runner selects the verified Python binding without shell interpolation.
No additional LS2 grant, network endpoint, global permission, privileged
third-party app or startup hook is introduced. Method support and audible results
still need physical acceptance.

Published 1.4.0 instead has separate `audio_recovery.py` / `audio-recovery.js`
files and three dedicated audio methods/grants. Those historical installed
contracts are not silently edited by the candidate. See
[Root OTA compatibility](ROOT-OTA-13-COMPATIBILITY.md).

All new state is in /var/lib/clean-your-tv-root/audio-recovery/, mode 0700.
Files are root-owned, mode 0600, atomic fsync/replace writes. Separate flock locks
serialize policy, operations, launching and worker ownership. Policy generations
cancel queued work. pending.json is persisted before the first off write.
last.json keeps only the latest result/monotonic time, no private diagnostics.

stop.json inhibits automation independently of the policy mutex. Explicit/fault
Home restoration publishes a stop token without taking the policy mutex. Audio failures never
block emergency Home recovery. Only explicit audio enable acknowledges the stop token observed before eligibility
checks; a newer emergency always wins. It does not clear Home emergency/off.
Manual audio recovery does not enable Home.

The worker holds a bounded luna-send -i tvpower subscription and requires its
acknowledgment. A genuine Standby → Active transition schedules one attempt after
ten seconds, expiring after thirty seconds. Duplicate Active pushes do not rearm.
Initial/reconnected Active snapshots, unknown states and clock gaps are not wake
events. Lost subscriptions clear readiness; three reconnect attempts are allowed.
The existing owned boot recovery callback starts saved enabled policy only after
the normal boot/failsafe gate. A consumed kernel boot identity and 120-second
monotonic startup bound prevent later callbacks/worker restarts masquerading as
cold boot. Manual enable consumes that boot too.

Settings effects use the existing product/update mutex. Pending update, package
disappearance or failsafe stops automation. Existing complete removal restores
Home, inhibits the worker and removes owned boot/service registrations. Private
audio receipts remain with retained recovery evidence. Old installed private
runtimes require checked fresh setup; updating only the web app is insufficient.

## Failures

Success means settings restored, never sound fixed. Interrupted processes or
uncertain writes retain a receipt and block further resets. No automatic replay
occurs. Disable before the first effect cancels it; after off, owned cleanup still
attempts restoration. Policy changes serialize with the first write; a contended
disable is a failed request, never reported as successful cancellation.

No platform compare-and-swap is established. Observable route changes are preserved.
An indistinguishable user write of the same off value during the interval cannot
be attributed reliably; avoid editing LG sound settings during a reset. Ambiguous
interrupted receipts always require explicit user choice.

## Physical acceptance: pending

Reporter target: LG 55NANO956NA, webOS 5.6.2, firmware 04.64.00, Samsung HW-Q950A.
No TV was connected or changed during implementation. Run at least five
identical-content comparisons with automation off/on, separating cold boot,
standby, Quick Start+ states and warm/cold receiver. Measure audible start time,
spread and needless interruptions. A ten-second intervention may be slower than
the symptom; do not claim improved acquisition without measurements.

Check working audio, ARC-only/off, WOW Orchestra, late/disconnected receiver,
manual route changes, duplicate/reconnected power events, disable during waiting
and off, RPC timeout, process kill between writes, explicit setting restore,
update/removal/rollback and triple-Home emergency release. Software/package checks
do not establish physical compatibility.
