# Root installer runtime delivery and reinstallation

Related issue: [#355](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/355).
This records source investigation and host verification. No TV was contacted and
no reporter installation report or private diagnostic data is reproduced here.

## Failure and correction

The installer admitted a self-consistent installed Root as maintainable. The
product coordinator then skipped deployment, verified the installed package using
its own retained descriptors, and returned success. Subsequent activation could
therefore execute older support/runtime instead of the selected installer code.
An updated host alone did not establish delivery of the health/readiness fix
recorded in [the startup race investigation](2026-11-06-root-health-startup-race.md).

Root setup now asks for explicit reinstallation when Root already exists,
including a pending profile activation. The replacement bundle, graphics,
inventory and rollback format are checked before removal. The normal full-project
remover restores controls and removes Root, updaters and any No-root Home/Helper.
Only verified clean removal with no pending receipt admits fresh deployment and
activation in the same invocation. It does not depend on resuming the old binding.
Preferences are removed; unrelated applications and the existing root access are
outside the removal goal. Previous recovery evidence stays on the computer.

A required restart or incomplete cleanup stops the replacement. Continue removal
through the installer, then choose setup again. No restart-spanning automatic
installation goal is introduced, and standalone removal never starts setup.
Noninteractive `--yes` still does not authorize replacement. Other pending goals
on the same TV and the C1 fresh-install-only admission remain guarded.

Two exact-code checks prevent false delivery claims. The worker permits an
installed no-submission handoff only when actual static support/runtime matches
the selected verified bundle. Before profile activation, a host-owned isolated
Python reader compares the selected code with installed bytes as data. It does
not use the retained manifest as expected authority or patch live runtime files.
Personalized package/release data is excluded from the static-code comparison.
Mismatch is explained as `installer-runtime-mismatch`, without enabling Home.
The existing verified private Python is reused. Successful cleanup invalidates
retired coordinator, recovery-support and interpreter paths before fresh preflight.

Activation command failures can carry seven fixed health-context explanations
only when the bounded diagnostic cursor establishes new records since enable.
Historical, rotated, unsafe, unknown and unavailable logs remain unclassified.
Connection/storage errors retain their original classification. No raw stderr,
paths, tokens or binding values are exposed. These explanations are observations,
not authority to bypass recovery predicates or clear an emergency stop.

## Verification and limits

The focused implementation checks reproduce old-runtime admission, blocked
reinstallation with an updater/pending activation, loss of specific worker reasons,
private-Python rejection and reuse of retired support before their corrections.
They cover replacement ordering, incomplete-removal refusal, declined/noninteractive
replacement, other saved operations, actual isolated byte reads, symlinks, local
payload changes and fresh-only failure guidance. Independent review found and
verified correction of the private-Python and retired-support regressions.

Completed local checks:

- `scripts/test.sh installer`: 1,205 tests, 7 skips, no failures; the Homebrew
  runtime/bridge/browser and supporting Python checks also completed.
- `scripts/test.sh setup`: 289 cases; 287 passed in the sandbox. The terminal
  PTY/process-substitution and standalone wallpaper local-HTTP cases were blocked
  by sandbox permissions and both passed in an authorized isolated rerun. These
  were environment failures; no product correction was made for them.
- `scripts/test.sh tv-runtime` completed the native/JS/generated-runtime checks
  (including exact Node 0.12.2) and 1,182 Root Python cases. Its sole failure was
  a staging-test fake missing the new selected-runtime admission method: 1,178
  passed and 3 skipped. After updating only that fake, the complete 27-case
  storage suite passed. Unchanged Root cases were not repeated. The remaining
  updater/System JS checks and all 136 System Python cases passed separately.
- Focused continuation/reinstallation/runtime/compensation checks: 34 passed.
- Existing health/startup regressions: 10 passed, including delayed cold validation.
- Independent review: no remaining blockers after the two corrections above.
- All 13 installer locales/guides updated; 23 i18n checks passed. Python 3.9 grammar,
  Prettier format check and `git diff --check` passed.

No release/component versions were selected or changed for this fix. Candidate
selection and package delivery remain with the release coordinator.

Host: macOS ARM64, maintained Python virtualenv. Edition: Root; selected graphics
and private-Python paths are simulated where stated. Device model, firmware/webOS,
remote, physical installation/removal/reinstallation, Home routing/button, audio,
standby, cold boot, OTA and rollback acceptance: untested. Source startup tests
exercise the existing corrected health-before-readiness path; they do not prove
activation on the C2 in #355. Keep the original issue open for release/device
acceptance. The removal fixes in [PR #457](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/457)
are separate and must be included when validating the combined affected flows.
