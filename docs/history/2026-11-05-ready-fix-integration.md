# Ready-fix integration — 2026-11-05

The maintainer explicitly requested merging ready fixes into `release/next`.
Candidate integration is reopened. This is not a `main` merge, publication,
new build selection or hardware acceptance. Committed component versions remain
unchanged pending the next freeze. Unrelated showcase work remains deferred.

## Integrated changes

- PR305, source4432245921c18b5e8f62de63e68c6c0f24e0f3ac, merged as
  d74291baa93a38b02e68fcc0e2deee229ccbb97f: close the restored Root overlay
  after verified off/emergency recovery and fence stale UI close replies.
  Focused Tests41857292101 attempt3 passed, including Linux/macOS and browser.
- PR302, source90128a4a7ccb86968a5dfb6b77a6528126f7caab, merged as
  9f532ef327fe43ff4d7e46e314a1f35c1d68479a: bounded catalog convergence after
  successful No-root package installation. Focused Tests41852377414 passed.
  This is preventive; original issue295 evidence/recovery remains unresolved.
- PR309, sourceca3e36fc1a9849aefe09f06aecebe523838f864f, merged as
  e8f4f4de524d748e0a57088460188c0aac2e15df: retain allowlisted package failure
  categories/reasons in diagnostics. Focused Tests41872613335 passed. It does
  not recover the original issue201/307 pending operations.
- PR313, sourceea2b6b1c3861453d10c0cf6c43928d844c09dbc5, merged as
  cbe593898bd3e4cb4ec2d8f2586a977ce8787e4f: clarify that the selected wallpaper,
  rather than its theme, has no video version. English and all twelve translations
  changed; media logic did not. Focused Tests41882613032 attempt2 passed,
  including both platforms and browser, before integration.
- PR312, source0d0d97a87bc945982fb3ca0d40f087c69e25c142 after the reviewed
  history-index conflict resolution, merged as
  c087bc8d14349add216365a4b2647065cc313e04: explicitly retain SDK parent entries
  in No-root IPKs. Tests41893026455 and desktop runtime41893026570 passed,
  including Linux, macOS ARM/Intel, Windows and browser. Retail coexistence,
  service registration, Helper rollback and original recovery remain unverified.
- PR306, source461d20709e7cfbbb3f244acdd6480518fa35bd4a, merged as
  a01ab0403ed47f5ef8adb502199a589053790e23: enable the passive remote
  diagnostic's guarded stdin entrypoint over an existing trusted SSH connection.
  Tests41858806265 attempt3 passed Linux, macOS, browser, ARM Python and both
  required summaries. The macOS retry obtained a hosted runner and executed the
  tests; earlier capacity cancellations were not treated as passing evidence.
  This is diagnostic preparation, not an IR mapping or a fix for issues304/207.
- PR303, source6e8aebcf9352101c09405eb8edbb47f569b153a7, merged as
  8903eb3e3d31003f678f5e0921b254ce981297c5: prepare personal appearance,
  activate native Root, then await presentation frames and readiness. Async
  presentation is awaited before retiring the boot marker or acknowledging
  updater health. Tests41855169514 attempt5 passed Linux, macOS, browser,
  ARM Python and both required summaries. Physical timing on these final
  combined bytes remains unmeasured; the change is not accepted as a measured
  speedup merely because CI passed.
- PR316, source71896190837eaca88f41c1eb019f6190e0f9bfda, merged as
  3c356a2fe88b37b9be726559652fa561507b9f7a: gate Root wallpaper video and input
  previews on a current-generation literal content:false, including opaque
  themes and startup. Refresh/hide revoke permission; stale replies cannot grant
  it. Unknown or active content keeps the static poster. This is an opening/
  refresh snapshot, not a continuous ownership lease. Tests41938181353 attempt1
  passed Linux, macOS, browser, ARM Python and both required summaries. The
  compiled browser regression uses real cache/HTTP MSE playback beyond the
  12-second loop and native playback, with fixture LS2/activity/input responses.
  Earlier settings-fixture dispatch and detached native-fixture cleanup failures
  were reproduced and corrected without changing product gate code or relaxing
  assertions/timeouts. Independent reviews and all 33 native-gate host tests
  passed. The earlier C3 static-video and receiver-exit causes remain unknown;
  exact signed-package media/lifecycle acceptance remains required.

Independent final source reviews found no blocking defects. PR312 and PR309 had
one history-index conflict. The proposed PR312 update0d0d97a87bc945982fb3ca0d40f087c69e25c142
retains both investigation links; independent review verified all other blobs
and merged product changes were preserved. On that combined tree, setup234 and
installer760 tests passed (72 optional skips), as did both package-parent tests
and the two history links. These host results were followed by successful
new-head CI before PR312 merged; they do not constitute retail acceptance.

After all seven focused merges, the combined product tree at593629e7 passed
`node tests/home-presentation-ui.cjs` and
`CYTV_THEME_CASE=startup node tests/themes/startup-motion-ui.cjs` locally.
The actual compiled browser fixtures cover Root activation before foreground
frames, async personal appearance, modal focus, visibility/relaunch ordering,
launch failure/success/staleness, No-root fallback and first-frame/warm lifecycle
in both editions. Services are simulated; no TV was contacted by these tests.
This is additional combined-source evidence, not a full candidate build or
physical timing, input, standby, boot, media or rollback acceptance.

## Helper foundations

PR317, source53c8747d755d43e52e27889d9b7065144f0e5182, merged as
a2fd765f57b343f33c2729ae9379267a760dd866 after Tests41959824989 attempt1
passed Linux/macOS runtime, browser, ARM Python and both required summaries.
It adds reviewed, unwired C Stop/private-journal/controller-lease primitives,
an ES5 journal protocol and a read-only private credential guard. Defaults deny
without trusted I/O, identity and provisioning. Existing consumers and package
versions remain unchanged; this is not a ninth completed runtime bug fix.

Focused host evidence includes 41 Stop cases, 71 private lease/journal cases,
41 private-reader cases and 70 ES5 protocol cases. The JS cases and the compiled
Helper/WSS/TLS/watchdog regressions ran on current Node and exact 0.10.15,
0.10.25 and 0.12.2. Native suites also passed sanitizers. An undersized invalid-nonce
fixture was corrected for GCC without relaxing validation. A macOS concurrency
failure was reproduced as a legitimate fail-closed directory-change refusal;
the test now schedules overlapping prechecks deterministically and separately
tests rejection of an incomplete concurrent publication. Both schedules passed
1,000 host executions. Independent source/integration reviews found no blocking
defects. These results are host evidence, not target storage or input acceptance.

The C/Node Stop-journal pipe bridge and relay cleanup are integrated separately
below. They do not activate the protected Helper migration. Home-origin authentication, ordinary protected provisioning,
native/service identity and namespace lifetime, input-holder lifecycle, fresh
pairing where required, and update/rollback/cold-boot acceptance remain open.
No physical observation is carried to these new source bytes.

## Relay cleanup outcomes

PR318, source1391d170ea44319711ab3722b1e3fc07abf0a010, merged as
2b156210182546f0a019907e0cfc9fdb73e553f7 after Tests41961887838 attempt1
passed Linux/macOS runtime, browser, ARM Python and both required summaries.
The relay now attempts key-up, ungrab and both descriptor closes even if an
operation fails, reports the failure mask and original cause, and returns 31
rather than a reason eligible for watchdog retry. The existing controller
blocks 31 and retains its separate cleanup after actual child close. The
standalone cleanup command also fails when its output close fails. Healthy
watchdog, emergency and source-removal behavior is preserved.

The original native failure assertion reproduced before the change. All 38
synthetic evdev scenarios passed normally and with ASan/UBSan, all 31 controller
watchdog cases passed, and startup/filter/triple-Home/controller Home/runtime
policy regressions and strict static ARM EABI5 linking passed. Independent
narrow review found no blocking defects. These checks execute the actual relay
against simulated devices; no physical remote was touched. This is truthful
native I/O reporting, not proof that all physical keys or surviving input
holders are released. It does not fix the unresolved Helper storage guard,
Home authorization, provisioning or future broker/relay lease lifetime.
The [developer contract](../development/HELPER-RELAY-CLEANUP.md) records the
failure codes, existing best-effort latch behavior and remaining acceptance.

## Native Stop-journal pipe bridge

PR319, source d160eed45fa6a41910bc99c1e4a3ffb01f723c54, merged as
727ca918de8d12ce25cc0ccd98f47a14c3f57b97 after Tests41964254235 attempt1
passed Linux/macOS runtime, browser, ARM Python and both required summaries.
The actual GitHub merge tree matched the locally checked expected tree
0fec1c90e4032bf08a44d664119d774362876879, preserving the relay cleanup fix,
reviewed native bridge/lease files, existing entry points and versions.

The bridge connects compiled legacy-compatible Node to a real C child over
bounded pipes. The C process owns the actual controller lease; a separate Stop
publisher bypasses that lease. Receipts require verified readback bytes. Native
SCAN checks the lease before and after observation, and END acknowledges success
only after validation and cleanup. Cancellation closes admission and waits for
actual native completion and process close; a timer cannot prove lock release.
These endpoint checks do not establish atomic cross-directory state or Home
origin. Production bindings remain absent, no consumers or native package build
are wired, and no input authority is added.

The first macOS CI run exposed a backpressure test assumption. The failure was
reproduced on exact official Node22.23.4: a one-byte high-water mark did not force
a false write when the stream drained synchronously. The test now uses the
actual Writable cork/uncork API where available, preserving Node0.10 behavior,
and requires a false APPEND write, a real drain event and a C-verified receipt.
Production transport code did not change. All 68 actual-child cases passed on
Node22.23.4, current23.11.0, 0.10.15, 0.10.25 and0.12.2 (340 executions), with 85
native private cases normally/under sanitizers, 41 Stop cases and combined
compiled Helper/WSS/TLS/watchdog checks retained at their recorded sources.
Independent integration and fixture reviews found no blocking defects.

This is integrated infrastructure, not a working protected Helper. Ordinary
provisioning and native/service identity/namespace qualification, authenticated
Home commands, consumer/relay lifetime, fresh pairing where required and final
update/rollback/full-boot/media/controls acceptance remain unresolved. Existing
source/default-denial and host fixtures cannot replace those requirements.

## Relay output backpressure safety

PR #320, source d3806bbd322a9df95602d91d178f484deea2d515, merged as
86f93d2938306755567502c6a820d19dcd524384 after Tests 41981116020 attempt 1
passed Linux/macOS runtime, browser, ARM Python and both required summaries.
Release policy 41981112959 also passed. Independent source reviews found no
blocking defects. This is focused source verification, not final candidate or
TV input acceptance.

An actual C harness with synthetic evdev reproduced a full controller stdout
pipe stranding the original relay beyond a three-second host bound. The fix
makes pipe/socket output nonblocking and requires complete bounded records.
Output failure cleans up and exits 30 without automatic recovery; cleanup failure
still takes precedence as 31. Standalone cleanup remains independent of stdout
and returns 0 or 11 for its actual cleanup outcome. TTY/regular-file flags and
healthy protocol records are preserved.

Real-pipe backpressure, EPIPE/closed stdout, watchdog/emergency cleanup, startup,
controller policy and static ARM compilation passed. The first Linux CI caught
three GCC misleading-indentation errors in the test harness; braces/newlines
fixed those test-only statements, then the complete focused CI matrix passed.
No failed check was bypassed. No TV operation, pairing, version change or public
release was performed for this fix. Rebuilt packages, physical key release,
normal Start/Stop, independent emergency exit and full-boot acceptance remain
required; this does not repair the protected Helper provisioning blocker.

## Still outside the inventory

Cancelled hosted-runner
jobs were rerun once for each of303/306/313 during this integration task.
PR313 subsequently passed and merged;303/306 were cancelled again on macOS.
During the authorized overnight integration, only the cancelled macOS jobs were
retried. PR303 and PR306 then passed their complete required matrices and merged.
No failed check was bypassed.
PR310 remains incomplete: trusted Helper storage/authorization and the actual
No-root context broker are not implemented or admitted.

## Issue and acceptance boundaries

Applicable issue bodies, discussions, timeline links, related PR discussions and
release evidence were reviewed. The latest issue295 attachment is another
recovery failure, not the requested original-install diagnostic. Its existing
request remains applicable; status is `needs-info` without a duplicate request.
Issues201/307 remain `planned`, issue304 `needs-info`, and issue207 `planned`.
All remain open with their original failures unresolved; no shipping claim or
new reporter-device test is made.

Build41837911621:1 and its signed Root QA artifacts predate these product merges.
Their observations remain in the dated November4 record; the plan's old build
and acceptance binding are removed. A fresh full candidate, exact artifacts and
affected controls/media/update/recovery acceptance are required after the scope
stabilizes. No TV operation was performed for this integration task. In particular,
Helper repair must keep protection, avoid trusting the exposed legacy key, and
pass a genuine new kernel boot with preserved store protection and actual
Helper/Home behavior; standby is insufficient. C1 remains physically unverified.


## Helper startup follow-up — 2026-11-05

PR321, source89a118a8335f97cc16412feafe09573754f9e669, merged as
4c13b86b027501f6f8c374487900b5f78b74868d. Source and merge trees are equal.
Focused Tests42017755525 attempt1 passed Linux/macOS runtime and summaries,
browser and optional ARM Python; integration policy passed. Linux job127212535707
actually executed the root multi-UID ownership test successfully. Local affected
checks passed; the initial broader run lacked declared fonttools, and the two
affected build modules passed after installing scripts/build-requirements.txt.

This handles Helper startup after a TV restart. It is not a repaired protected-state
architecture or final-byte device acceptance. Associated maintainer device remains
C3 OLED55C3RLA, firmware43.21.71/SDK11.2.0, Magic Remote with pointer (exact remote
model and marketing webOS unknown); no new TV operation was performed for this
source integration. Host validation used macOS ARM. Candidate component manifests
remain provisional; fresh packages and actual Home/Start/Stop/emergency, sound,
full boot and update/rollback tests remain pending.

The maintainer requires No-root overlay PR310 in this candidate. Its production
context/dismissal connection now has HOST and compiled-browser coverage at
a4042ba8; current-head CI/review, integration and packaged-TV acceptance remain
pending. Earlier frontend-only status above describes the earlier head. PR322
separately removes three unwired research JS modules from production packaging;
it remains pending its complete checks. Neither pending PR is counted as merged.


## Shipping-scope cleanup — 2026-11-05

PR322, source369e04b04c115cf7b06370112f2c3d798186e1f3, merged as
8857c9bc7ee348eebb72a303b37172461b71e6ff after complete focused
Tests42019540901 attempt1 and policy checks passed. Source/merge product inputs
match; only release-plan.json and this dated record differ from the source head.
Three unused JS research modules now live under native/prototype, outside both
production Helper builders. Their bytes and standalone checks are preserved.
The C research files remain source-only; active relay/startup fixes do not depend
on these modules. No new permissions or runtime endpoint is activated.

The packaging regression failed before the move, then compiled Helper/WSS/watchdog
and prototype41/70/68 checks passed. Independent review found no production
consumer. This is source/build-scope evidence, not a newly built package hash or
a device result. No TV operation, selected build or component-version change
was performed here. PR310 remains mandatory and under current-head CI.
