# Root activation evidence investigation — 2026-11-04

## Scope and evidence limit

Related issue: [#282](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/282).
The existing public report identifies a Root installation on Windows AMD64 with
cytv 0.8.1, OLED65C44LA, firmware 33.31.68 / SDK 10.3.1; remote model is unknown.
It records verified packages and a retained `activate-root / enable` stage, no
submitted Home launch, unverified startup and an untested Home button. These are
reporter-supplied facts, not new maintainer device observations.

The generic exception in that report does not retain the failing command's exit
status or the TV's underlying reason. Readable Home interfaces and completed
package installation do not prove writable routing, input/guardian health or
successful activation. No firmware incompatibility or specific device cause has
been established. `recovery.category: other-edition` is the existing generic
non-No-root pending classification; it is not proof of conflicting editions.

## Reproduced source defect and correction

`Installer.activate_root()` caught `RuntimeError`, which includes `UserError`
and its typed `TVCommandError` / `TVRejected` subclasses, then replaced the
initiating error with a generic activation message. This discarded numeric SSH
or Luna metadata before both the immediate report and first-failure history.

Preserve existing typed installer errors after marking startup unverified.
Annotate failed deploy SSH calls with the fixed action and driver boundary;
use one action allowlist for immediate and retained diagnostic projections.
The existing generic activation advice remains for untyped failures. Raw output,
exception text, addresses, credentials and unrelated applications stay excluded.

The correction leaves activation, launch, pending checkpoints, terminal receipts,
explicit recovery and emergency behavior intact. It does not retry any operation,
clear a pending record or make an unsupported device pass a gate.

## Verification

- Installed locked JavaScript dependencies with `npm ci` and prepared a private
  host venv using the pinned font/runtime requirements. An initial system-Python
  baseline lacked `fontTools`; after preparing the venv, all 78 existing operation
  tests passed.
- Before the production change, the new regression failed separately for an
  enable SSH failure and a definite Home launch rejection because the original
  typed exception was replaced. After the change, both cases passed.
- The regression exercises real install/activation orchestration with only the
  external TV transport simulated. It checks retained stages, immediate and
  first-failure metadata, private-text exclusion and exactly one submission.
- Independent read-only review found no actionable issues; seven focused
  activation tests and `git diff --check` passed.
- `PATH="$PWD/.venv/bin:$PATH" bash scripts/test.sh installer setup android`
  passed: 224 setup tests, 671 installer tests (40 optional/environment-dependent
  skips), 27 Android tests and 17 Homebrew Python tests, plus the selected
  Homebrew JavaScript checks. The local venv does not contain PySide6; native
  frozen Windows/macOS/Android acceptance and cross-platform CI are separate.
  Expected negative-fixture warnings/argument refusals did not fail the run.

## Delivery and remaining work

This is a partial diagnostic correction. Original C4 activation remains unresolved
and requires reporter evidence; old reports cannot recover discarded details.
Do not ask the reporter to reinstall or repeat enable just to produce an error.
A supported status read through the original saved connection can distinguish
current active, inactive or recovering state without resubmitting activation.

The change requires rebuilt shared CLI/desktop/Android installers at a future
candidate freeze. It changes no TV package, release version, dependency, endpoint,
permission or device state. No signed build, publication or TV access occurred.
Actual C4 recovery, Home routing, controls/audio, standby, cold boot, OTA and
rollback remain untested. Full frozen-candidate checks belong to the coordinator.

Reviewed documentation: this record and the installer diagnostic contract. Setup,
recovery and control actions are unchanged; no new user-facing string is added,
so the twelve localized user guides need no action or translation changes.

## Integration into the next candidate

[PR #287](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/287)
merged into `release/next` as `6139c3c4a8361147b7b55a7030eba92f552b6249`.
The exact reviewed implementation head is `0f6b6aba5869bba7fc0f335e2673ff8661fd371d`.
[CI 41784534156](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41784534156)
passed Linux/macOS runtime/test summaries and ARM optional-Python checks; release
PR policy and Integration policy also passed. Browser and full-release jobs were
correctly unselected for this affected host-only change. No full candidate build
or physical-device acceptance is claimed.

The unfrozen [candidate #281](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/281)
records this partial change and #282 without selecting a version or build.
The original failure remains open for reporter evidence. Integration is not
publication, a completed recovery or confirmation of C4 Home routing.

## Related report #288 — 2026-11-04

[Issue #288](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/288)
supplies three public installer reports after a reported No-root-to-Root change.
They retain the same first failure on cytv 0.8.1: packages verified, pending
`activate-root / enable`, no submitted Home launch. Subsequent recovery reads
record disabled Home intent, inactive guardian and verified recovery integrity;
full removal refuses the unresolved activation. This evidence does not establish
an edition conflict, successful Home activation or recovery. It is not the
`install / coordinator-submitted` worker failure from #240.

The generic original error follows the same reproduced diagnostic-loss path
corrected by #287. Its original command detail cannot be recovered from these
reports. The reported TV-side Change Home crash has no captured TV-side failure
in the attachments; do not infer its cause from the host recovery refusal.
Current source still requires appropriate verified recovery and does not retry
an unresolved activation merely because installed packages are complete.

No new product patch is justified by these reports alone. Reused #287 rather
than duplicating its change or weakening pending/emergency/removal guards.
Installed locked JS dependencies and ran
`PATH="$PWD/.venv/bin:$PATH" python3 -m unittest discover -s tests/cytv -p test_operations.py -k activation`:
all seven existing real-orchestration activation regressions passed on
`8c2a6b9c96e78062e563abdedbf03f748b8a8fcd` (no product changes).
Requested only an existing on-screen error and already-known current Home
behavior, without repeating status, activation, recovery, install or removal.
Device acceptance and the original cause remain unresolved. No TV contacted;
no new owner installation result or raw/private evidence is published here.
