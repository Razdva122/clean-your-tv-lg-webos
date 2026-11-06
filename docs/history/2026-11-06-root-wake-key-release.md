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
released. It discards the initial historical queue once. A fresh Home press or repeat
during settling cancels pending activation without sending READY; key-up can
complete settling, and fresh malformed input fails closed. Triple-Home and
long-Back state for normal operation are constructed only after release. It sends no READY/PING while waiting and
does not extend the existing two-second supervisor deadline. Permanently held
flags, EOF, input errors, invalid ABI/channel, malformed active events and queue
limits retain fail-closed behavior. There is no input grab, reinjection, new
permission, persistent state or automatic retry/re-enable.

The actual reader subprocess/private-pipe/watchdog delayed-release regression
failed on the old code (`input_lost` instead of the fresh emergency gesture).
Review identified that fresh Home during the added wait must cancel activation;
its regression failed until that safety gap was corrected. All thirteen
reader cases pass after the change, including permanently held keys under the
real startup watchdog. The related 462 executed startup, intent, guardian,
shutdown, emergency and persistent recovery cases passed. Independent read-only
code review found no actionable defects; its startup-deadline test limitation
was corrected and re-reviewed.

The actual focused Root 0.10.0 package builds successfully. Its staged reader,
bundle inventory and generated signed-update infrastructure all contain the exact
source bytes (reader SHA-256
`d032b473c2eca741ae1f2d80a740e72673e8a402e498ed8c81e6c91d9904862e`).
This local package proof is not a selected full build or a signed TV artifact.

This is a bounded mitigation for transient startup flags, not proof that a
persistent/stale bitmap or every standby failure is fixed. At source review, installation and physical acceptance were pending; see the
subsequent scoped candidate observations below. No normal setup/control instructions
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

## Combined candidate freeze

PR #344 merged at `eb16bd39cda5310012b4ac8b3aed098aa0e4e10a` after successful [final source checks](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42171984176). The frozen inventory contains 16 implementation PRs and nine related issues, including #341 and the owner-admitted demo-only #345. No CI-reuse implementation is part of this candidate.

Actual local TV packages were revalidated at that combined source: payload integrity, component versions, manifests against authenticated retained 1.8.2, and all four System edition/resolution sets passed. The staged reader matches the final reviewed source; Helper bytes and canonical archive remain unchanged. Changes since the focused package build are confined to the browser demo, its tests and release metadata. Existing Helper approval and deferred Homebrew promotion are retained. This is pre-dispatch package evidence, not CI signing or physical acceptance.

The previous full build and signed Root artifact predate these fixes and cannot be installed for this acceptance. The next complete candidate must be signed in ordinary Root QA mode before owner-supervised C3 update and affected Home/standby checks. The prior standby failure remains unresolved until that test; cold boot and rollback are separate scenarios. No stable publication or main merge is authorized.

## Signed candidate C3 observations

These observations belong to selected build
[42176689817:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42176689817),
source `6659cd9ed1dd16d19f452d1d2a958c51c092b0a4`, acceptance token
`42176689817:1`. All mandatory platform, runtime, ARM Python and full browser
jobs passed. Ordinary Root QA signing
[42178746923:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42178746923)
completed with publish=false at metadata-equivalent source
`5e8bf096b4f1d36967d2b08af3171f9704cde9b7`.
The artifact digest, source/run/attempt provenance, production signature and every
component size/hash/version were verified before device admission.

| Signed component | Version | SHA-256 |
| --- | --- | --- |
| Root | 0.10.0 | `f85b23e662ce0c6e6ba9cd4b14e0ffe89ce0bead7ca511baa53e041cd42f8115` |
| Root Updater | 0.4.5 | `ef6cd860b415d400b80054addbf47d27eb99b1d07f59ad7531683bb16659a77e` |
| Infrastructure | 0.10.0 | `3532e0ea3c13a50a6854af66413a66cf4a2c715ede07eb97a7d3c42d835f1bd1` |

Signed envelope SHA-256:
`f8cdab66746cc0f65f1794738d7f9a0cd0a7f82c6addaf2fcbc3abddab89688f`.
Signed artifact 13484192078 SHA-256:
`e94d7b03e52e5a43c770f282d39402ab7a52a65c6fd42b5cfe9cd6ec0c235c67`.

The same maintainer-owned C3/firmware/SDK/remote and macOS ARM64 host described
above were used. Upgrade source was published 1.8.2, with Root/infrastructure
0.9.3, Root Updater 0.4.4 and stopped Helper. System Updater 1.1.2 remained pinned.

The first host attempt stopped at live UI profile capture before install
admission; a subsequent capture from the loaded UI succeeded. Three status
observations confirmed the original transaction and component identities had not
changed. The first admitted update then aborted before any component installer
intent: available /var space was about 156.1 MiB versus required 157.1 MiB.
All three installer intents were false, with no submission/terminal, and Home
resume for the abort completed. Real installed versions remained 0.9.3/0.4.4.

The owner explicitly authorized stale-package cleanup, then chose to execute the
provided command personally. Two content-verified, unreferenced historical cache
copies freed approximately 54 MiB; available space read back as 215156 KiB
(about 210.1 MiB). No agent deleted TV files. Recovery journals, current/prior
packages, WAM data, private Python and historical replacement evidence were not
modified. Storage retention is a separate next-release follow-up.

Fresh supported admission from the exact finished, pre-intent abort used the same
signed candidate and a fresh actual UI profile. All three actual component
installer terminals succeeded. The ordinary launcher health signal and transaction/
Home resume completed. The captured profile's canonical digest matches the new
transaction; no whole-profile identity after subsequent user setting changes is
claimed. Actual installed appinfo versions and reader SHA-256 were read back:
Root 0.10.0, Root Updater 0.4.5, System 1.1.2, final reader `d032b473...` above.

| Scenario | Expected / observed | Result |
| --- | --- | --- |
| Signed update from 1.8.2 | Supported worker completes all components and ordinary Home health; exact installed versions/reader confirmed | PASS after owner cleanup; initial space refusal retained above |
| Post-update Home/audio | Enable Change Home, video with sound/volume, short Home returns Clean without recovery busy/hang | Owner PASS; active intent/guardian read back |
| Standby routing/audio | Remote Off for requested approximately 20 seconds, On, short Home, settings wait and return to video | Routing/audio PASS; active intent/guardian confirmed by service and actual UI caller; UI status FAIL below |
| Settings status after standby | Open panel should show current active state | FAIL: message stays Changing Home control and switch disabled/unchecked despite active backend; Back/reopen restores correct state |
| Triple-Home emergency Off | Three Home presses in two seconds, then later short Home must stay LG; controls/audio usable | Owner PASS; disabled intent, stopped guardian, verified integrity and stopped Helper read back |

The maintainer explicitly deferred the Settings presentation failure to the next
release, tracked as [#347](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/347).
No UI fix is included in these bytes. The initially returned transient phase was
not captured; stale transitional status is supported by source inspection and
successful panel reopening, not a directly observed initial response. This is
separate from the earlier recovery-busy/Home-close failure with disabled routing.

Final state: candidate 1.9.0 installed, LG Home available, Root emergency Off,
guardian stopped, Helper stopped, recovery integrity verified. System transaction
is complete and retained rollback is available. Retained rollback was not
exercised. Cold boot, new-package long-Back/pointer/wheel/editing cases, personal
receiver/media (#337), C1/B4/C4 behavior, No-root and exact Android upgrade/data
retention remain untested here. Do not copy the earlier baseline's manual results
onto different candidate bytes. These scoped results are not complete release
acceptance, universal compatibility, public-feed/anonymous-download acceptance,
or authorization to merge main/publish stable.

## Final cold-start, retained rollback and Android upgrade

The maintainer subsequently requested cold boot, retained rollback and publication
of this version. On the same candidate, the owner enabled Change Home, confirmed
short Home, switched the TV off and disconnected AC for a requested 30 seconds.
After reconnecting, Home, video, audio and volume worked. Readback found active
intent/guardian and verified integrity. Uptime reset from 815.49 to 86.83 seconds;
the reported boot UUID did not change. Therefore the UUID is not used as the sole
restart proof. Physical power removal is owner-confirmed; its duration was not
independently measured. No cause is assigned to the retained UUID.

The ordinary installed Root restore service confirmed recovery/Off before the
ordinary System rollback call. The original worker restored all three retained
1.8.2 components with successful rollback submission/terminal evidence and normal
launcher health. System phase and Home resume were rolled-back. Actual Root0.9.3,
Root Updater0.4.4 and retained System1.1.2 were read back. Runtime reader SHA-256
`c395e0661ea2ab128ac99d91a1a107242d119eabd03082d66d6e4a79d96c34f4`
matched authenticated prior infrastructure
`8f6352b33599d17938f1fd70a255301f5c1b19eb913e84083db707dbafcba9be`.
The owner confirmed enabled Home, application/video/audio/volume, preserved
appearance/settings and explicit Off returning to LG after rollback. The saved
transaction profile remains bound to its original digest and normal restore/
health completed; no fresh post-rollback whole-profile identity is claimed because
the UI was already closed during the final read-only capture attempt. It was not
reopened merely to fill a report. Final TV state is restored1.8.2, LG Home,
Root/guardian off, stopped Helper and verified integrity. No unsupported forced
install, key/receipt replacement or journal deletion was used.

The final protected-CI Android APK was separately authenticated by Actions archive
size/digest/source/attempt, then checked against a clean exact build-source checkout
using android/verify_release.py. Embedded provenance/payload/versions, ARM64 ABI,
SDK declarations, non-debuggable release mode and the original public signer match.
APK SHA-256: `90922be5e6ca69e8c18ccbe65b8032d19969f971512d4be294014ce227ae19d1`.
Signer SHA-256: `5434c3eb169a59a1a5ae1f60c443b927601d0c508fd4f41919b0dd2947d14f94`.
CI native runner SHA-256:
`e534e6a4a13481ee404cd0982aabadeecdd2cad5393d86091b01962a5d09c388`.

On a newly created isolated API35 ARM64 userdebug emulator, the original signed
published1.8.2 Android0.8.2/code22 was installed and seeded by the real native
Store fixture. Its API asset digest/size and original certificate were verified.
Force-stop followed by install-r of the unchanged final Android0.9.0/code23 APK
succeeded without uninstalling. Four synthetic files (profile, dummy key,
preferences, pending operation) retained their hashes across upgrade, idle launch,
background/return, rotation, lock/wake and process death. No automatic installer
service replay or fatal exception was observed. Native Store verify confirmed the
retained pending operation blocks another begin; full native OperationChecks passed
both edition contexts, bounded replay, pending prompts and stale-answer rejection.
Only this owned userdebug emulator used supported adb-root for instrumentation;
the APK was not re-signed or made debuggable. No real TV profile/key or phone-to-TV
operation was involved. Physical phones, oldest supported Android/WebView and
interrupted live network operations remain untested.

The maintainer's release instruction follows these scoped results. Known #347
Settings presentation and #348 storage retention are deferred to the next release;
future PRs #346/#349 are excluded from these bytes. Personal receiver/media #337,
C1/B4/C4 target hardware and broader No-root/phone acceptance remain documented
limitations, not passed cases. These observations support shipping within this
scope; they do not establish universal compatibility or resolve partial reports.
