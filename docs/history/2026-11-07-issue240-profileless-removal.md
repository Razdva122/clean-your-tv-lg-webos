# Stock-only Root removal without systemprofile

Source fix for #240, targeting `release/next`. Related compatibility background:
#107. This implements removal of a partial installation, not general webOS 5
installation/routing support. Original installation causes and reporter-device
recovery remain unverified. No TV or phone was contacted or modified, and no
new reporter action is requested. Private diagnostic contents are not included.

## Contract and retained evidence

The old remover can reach `original-writers-fenced` without a trusted
pre-activation stage. Requiring `systemprofile/getProfiles` there blocks cleanup
on firmware without that service, even when there is no retained routing
transaction and Settings Service selects stock LG Home.

The new stock-settings path requires all of these conditions:

- The current bounded Luna reader receives the exact `returnValue: false`, integer
  `errorCode: -1`, and fixed systemprofile missing-service text for that exact
  method. Broad diagnostic categories never grant recovery authority.
- Settings Service independently returns `com.webos.app.home`. A foreign,
  project-owned, empty or malformed Home value is not accepted or rewritten.
- Under the original ownership/component locks, before current-runtime restoration,
  neither current state nor its saved routing backup contains a profile trial,
  persistent intent/binding, staged profile or experimental native Home backend.
  The fixed project profile override must also be absent. A prior successful
  three-profile readback cannot be downgraded to settings-only verification.

`profileless_cleanup_eligible` is a persisted boolean in the existing removal
record, captured before restoration can consume evidence. A recorded refusal is
not upgraded on retry. Existing failed removals without that field re-evaluate
current state and their already retained backup; old failure outcomes remain
separate. The inverse backup now also retains persistent intent/binding and the
staged profile as data. It remains private and is never executed or exported.

The selected `routes` proof records `mode: stock-settings` and the fixed stock
Home. Python restart/readback and the current Node finalizer preserve that
contract: another Home, an available profile service, malformed replies, transport
failure or access denial cannot satisfy it. Existing `never-applied` handling
retains its separate pre-activation proof. No service is provisioned or emulated;
no routing setter, dependency, permission or network endpoint is added.

Current-runtime restore, registration restoration, original-worker fencing,
precise file ownership, package receipts/absence, restart proof and final sweeping
remain mandatory. Emergency/off state is not automatically cleared.

## Verification

Before the production changes, the modeled Python retry remained at
`original-writers-fenced` and the real Node finalizer refused cleanup. Both
regressions pass after correction. An independent review identified malformed
successful profile replies in the finalizer; an added test reproduced that gap
before it was closed. Preserved-backup, sticky refusal, prior-profile readback,
current routing markers, non-stock Home and post-restart drift checks cover the
new fallback boundaries. The real child-process Luna tests cover exact error
classification, numeric types and client reaping.

Final local checks used macOS 15.6.1 ARM64, the maintained project Python 3.14.2
virtualenv, current Node 23.11.0 and the retained exact Node 8.12.0 executable:

- `PYTHON=<project-venv>/bin/python PYTHONDONTWRITEBYTECODE=1 scripts/test.sh tv installer setup android`
  passed: 1,311 Root cases (three expected skips), 132 System/update cases,
  280 setup cases, 1,069 installer cases (five expected optional/platform skips),
  44 Android Python cases, plus the selected UI/JS/native checks and generated
  normal/experimental Root/Updater/System package checks.
- `PYTHONPATH="$PWD/root-edition" NODE8=<node-8.12.0> PYTHONDONTWRITEBYTECODE=1 <project-venv>/bin/python -m unittest discover -s root-edition/tests -p test_cleanup_tail.py`
  passed all 38 finalizer cases, with one expected Linux-fd-only skip on macOS.
  The first standalone invocation omitted `PYTHONPATH` and had five import errors;
  the corrected command above passed, including the Python-to-Node handoff cases.
- The real subprocess `test_update_luna.py` suite passed all seven cases.
- `npm run format:check` and `git diff --check` passed.
- Final independent code/safety review found no remaining blockers after the
  malformed-success correction. It did not perform hardware tests.

The implementation PR records the source revision and subsequent CI state.

## Packaging, documentation and acceptance limits

Rebuild Root Updater support/infrastructure and all embedding desktop/Android
installers through the normal candidate process. `build_updater.py` copies the
shared Luna source into updater and system support; generated duplicates are not
edited manually. This task does not select component versions, freeze a release,
change the release inventory/build pin, merge or publish.

The developer recovery matrix is updated. The existing desktop/Android Remove,
Try again and requested full-restart actions and strings are unchanged. English
recovery/Root/Android guides and the maintained localized installation/removal
flows were reviewed for this boundary: no new user command, prompt or translation
is introduced. Candidate source behavior is separate from published downloads.

Local fixtures model stock-only older firmware and existing newer profile-based
routing. These are source/packaging checks, not physical acceptance. TV model,
firmware/webOS and remote for a new test run are unknown/untested; installer host
is macOS ARM64. Physical phone/TV removal, Home routing, keys, audio, standby,
AC cold boot, OTA, rollback and a subsequent fresh installation remain untested.
Original #240 and broader #107 must remain open; modeled removal is not proof
that their original installation failures are fixed.
