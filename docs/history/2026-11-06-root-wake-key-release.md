# Root wake input readiness, 2026-11-06

## Observed installed baseline

Owner-supervised maintainer QA on OLED55C3RLA, firmware 43.21.71 / webOS SDK
11.2.0, Root edition of published 1.8.2. Installed Root/infrastructure 0.9.3,
Root Updater 0.4.4 and retained System Updater 1.1.2; No-root Home 1.9.4 and
Helper 0.7.4 are retained, with Helper stopped. Host: macOS ARM64, exact OS version
unknown. Remote supports pointer/wheel; exact model unknown. No package was
installed during this test. This is not candidate 1.9.0 acceptance.

The owner confirmed normal Home routing, arrows/OK, application launch and
return, audible video, volume, repeated Home, pointer/wheel, Back closing
settings, held-OK editing with Back cancellation, explicit Home Off persistence,
triple-Home emergency Off persistence, and long-Back LG Home visit followed by
short-Home return. Active Root/guardian and stopped Helper were read back during
the initial enabled test. Explicit/emergency Off had disabled intent, stopped
guardian and verified recovery.

For standby, the owner used remote Off, the requested approximately 20-second
wait, then On. The wait was instructed, not measured; the source was not named.
Clean appeared first, and the owner initially confirmed controls/audio. A later
readback found disabled intent and no guardian. On clarification, the owner
reported `Recovery busy` in Home settings, followed by Home closing itself.
Therefore standby/Home-control persistence **failed**; first-screen appearance
and working playback do not establish healthy routing persistence.

The current transaction's private emergency log reports `input_lost` during
`starting`. The adjacent observer record identifies `startup / keys_held`, but
has no transaction field; its association with this attempt is inferred from
log adjacency, not independently transaction-tagged.
Bound recovery completed with restored routing/binding, disabled input/intent
and verified integrity. System's existing 1.8.2 transaction stayed complete.
The owner confirmed LG Home, remote, video and sound remained usable. No retry,
manual repair, code/receipt edit, state cleanup, installation or reboot followed
this failure. Cold boot was not performed.

These observations match the external failure tracked by historical
[#90](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/90), whose earlier
closure and successful tests retain their original version scope. They do not
prove the original 0.4.0 failure had this exact cause. The current startup held
flag is distinct from the historical ENODEV/shutdown-proof and native startup
presentation investigations in #104/#171, and from the wallpaper fix #337.
The adjacent startup record supports the held-key hypothesis for this attempt.
The physical key, flag duration and underlying input-driver cause are unknown.
`Recovery busy` is consistent with a concurrent recovery operation;
its timing is not independently traced.

## Candidate source change and host verification

The existing read-only input observer now allows up to 750 ms for all keys to be
released. It drains historical events on every check and constructs triple-Home
and long-Back state only after release. It sends no READY/PING while waiting and
does not extend the existing two-second supervisor deadline. Permanently held
flags, EOF, input errors, invalid ABI/channel, malformed active events and queue
limits retain fail-closed behavior. There is no input grab, reinjection, new
permission, persistent state or automatic retry/re-enable.

The actual reader subprocess/private-pipe/watchdog delayed-release regression
failed on the old code (`input_lost` instead of the fresh emergency gesture).
A separate queued-gesture regression also failed before the patch. All ten
reader cases pass after the change, including permanently held keys under the
real startup watchdog. The related 459 executed startup, intent, guardian,
shutdown, emergency and persistent recovery cases passed. Independent read-only
code review found no actionable defects; its startup-deadline test limitation
was corrected and re-reviewed.

The actual focused Root 0.10.0 package builds successfully. Its staged reader,
bundle inventory and generated signed-update infrastructure all contain the exact
source bytes (reader SHA-256
`c605d0e1d230b7e707381dbef1702d247a639c78039c8c2c0f10938e4b58bf8d`).
This local package proof is not a selected full build or a signed TV artifact.

This is a bounded mitigation for transient startup flags, not proof that a
persistent/stale bitmap or every standby failure is fixed. Source installation
and physical acceptance remain pending. No normal setup/control instructions
change; localized guides retain their existing safety/recovery instructions.

## Remaining acceptance and release boundary

Root runtime and infrastructure must be rebuilt coherently, with the media fix
#341 and this blocker fix included before selecting the replacement full build.
The preceding full build 42112684336 does not contain either change. No final
acceptance or stable publication is established by host regressions.

Use the supported signed System worker with a fresh real UI profile. Record
actual package/source hashes, complete installer terminals and profile retention;
then verify enabled standby/Home routing with service readback, controls/audio,
triple-Home and explicit Off. Record cold boot separately. Retained rollback,
Root personal image/video and other-model/Android checks remain separate.
Stop on unresolved recovery or unknown package outcomes. Preserve private
diagnostics and original journals; publish only this redacted interpretation.
