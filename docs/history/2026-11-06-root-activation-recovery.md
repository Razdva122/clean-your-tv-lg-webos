# Root activation recovery and health-context diagnostics

Related issue: [#334](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/334).
This record contains source analysis and host simulations, not a new installation
report or physical-device acceptance.

## Behavior

The installer previously refused continuation of a retained `activate-root/enable`
receipt even when its own inactive-state check accepted restored LG Home. Updated
profile-backend recovery accepts only known activation stages with verified files,
Root Updater/baseline, disabled intent and a restored routing journal. A linked
product installation must be complete and current with the same rollback baseline.
Existing legacy receipts must still carry complete matching file/baseline evidence.
Incomplete or unknown receipts remain blocked.

A host-supplied inspection script uses the existing product/update, persistent
operation and routing locks. It proves the restored binding belongs to the disabled
intent, reads back the recorded stock baseline, and rejects failsafe, update blocks
and remaining candidate/staging files. It does not repair or delete state. Recovery
checks run again after the separate default-No confirmation. Before that explicit
activation, the original host receipt is archived locally; packages are never
resubmitted. C1 Beta recovery and No-root behavior are unchanged.

The runtime now assigns fixed health-context reasons and appends the observed
reason before supervisor recovery, using PID and monotonic time for correlation.
The new record excludes transaction, boot identity and token values. It identifies
the failing predicate at observation time, not necessarily the first failure in
another process. Diagnostic imports and log writes cannot bypass recovery. A host
test additionally reproduced full shared-log writes preventing bound recovery;
the affected runtime diagnostic writes are now best effort without changing
shutdown classification, transaction ownership or restoration decisions.

## Verification

- `PATH=<prepared-venv>/bin:$PATH PYTHONDONTWRITEBYTECODE=1 bash scripts/test.sh
  tv-runtime installer setup android` exited 0: Root 1,023 cases, System Updater
  132, setup 239, shared installer 767 (72 reported skips), Android 35, plus the
  selected native/JS/Homebrew checks. This broad run started before the final
  best-effort logging refinements; final affected groups are recorded below.
  Skipped cases were not executed. The macOS multi-UID case requires Linux root;
  exact legacy Node 0.12.2 was not configured, so this is not new legacy-Node evidence.
- `npm ci` passed (281 packages; audit reported zero vulnerabilities).
- The new real-orchestration regression fails against the unchanged base installer
  with recovery refused, and passes against the modified installer. It simulates
  successful package setup followed by failed enable, restored LG Home, declined
  recovery and confirmed recovery. It verifies one explicit additional enable,
  no package install/remove submission and retention of the original receipt.
- All 84 operation tests passed in the prepared Python environment; five focused
  activation-recovery cases passed initially, including stale/missing evidence and confirmation
  revalidation. Three real-runtime proof cases passed against journals and locks.
- All seven health-context reason cases failed with the old generic error and
  passed after the change (63 health tests including inherited integration cases).
- Diagnostic import and full-log regressions failed before their corrections.
  Ten emergency-recovery tests and 73 persistent-recovery tests passed afterward.
  The complete final emergency group passed 36 cases. Six final installer recovery
  cases passed, including a new check that a busy proof after confirmation leaves
  the original receipt intact and submits no enable.
- Independent read-only review identified a diagnostic import that could bypass
  recovery. A red/green regression verifies the correction; final review of that
  and the shared-log changes found no remaining actionable issues.
- All 455 relative links in the recovery and localized guides resolve;
  `git diff --check` passed.
- Changed Python modules also parse with Python 3.9 grammar. Host execution is
  separate from exact TV Python/runtime or physical-device acceptance.

Initial operation tests in the sandbox could not download uncached pinned font
inputs; the dependency-equipped run prepared the verified cache and passed. The
first dependency-equipped attempt also lacked the pinned fontTools version;
installing `scripts/build-requirements.txt` resolved that test prerequisite.

## Delivery and limits

Installer/shared Android inputs and Root infrastructure need rebuilding through
the release coordinator. Existing retained runtime files require supported verified
delivery; an app-only update cannot add runtime diagnostics. No component versions,
release inventory, selected candidate build or acceptance records were changed.
The frozen candidate must not absorb this change without the coordinator's scope
decision, rebuild and affected acceptance.

`docs/RECOVERY.md`, `root-edition/TESTING.md` and all thirteen localized guides were
updated. Existing confirmation text and controls are reused. No dependency,
permission, endpoint or TV persistent-state format was added; the extra host
recovery archive uses the existing private receipt mechanism.

No TV was contacted. Test model, firmware/webOS, remote and installer-device
acceptance: not tested. Original activation cause and reporter recovery remain
unconfirmed. Physical Home routing, emergency gestures, key-up delivery, sound,
standby, cold boot, OTA and rollback on the reported TV remain untested. Host
checks do not establish device compatibility or justify closing the issue.
