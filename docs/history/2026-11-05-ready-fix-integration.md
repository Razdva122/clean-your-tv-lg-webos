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
