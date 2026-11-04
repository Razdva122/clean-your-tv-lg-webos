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

Independent final source reviews found no blocking defects. PR312 and PR309 had
one history-index conflict. The proposed PR312 update0d0d97a87bc945982fb3ca0d40f087c69e25c142
retains both investigation links; independent review verified all other blobs
and merged product changes were preserved. On that combined tree, setup234 and
installer760 tests passed (72 optional skips), as did both package-parent tests
and the two history links. This prospective result does not itself merge PR312
or replace its required CI.

## Still outside the inventory

At this checkpoint PR303 (Root activation), PR306 (passive IR diagnostics),
PR313 (wallpaper availability wording) and the updated PR312 are awaiting
successful required CI. Cancelled hosted-runner jobs were rerun once for each
of303/306/313 during this integration task. No failed check was bypassed.
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
