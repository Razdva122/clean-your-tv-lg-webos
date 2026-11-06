# Installer recovery UI source verification — 2026-11-06

Scope: next unpublished candidate UI on base `1a5fffcb`, before integrating the
final Root and No-root full-removal adapters. No TV operation, signed installer,
release selection, publication or device acceptance is part of this record.

Desktop and Android now distinguish unresolved review/waiting from completed
recovery, independently of process exit code. Completed LG Home/Home-control-off
setup names that achieved goal; physical checklist observations remain separate.
Clean removal requires the backend's completed disposition and explicit
`verified_clean: true`; a missing/incomplete result is review. Android includes
an explicit removal tool with separate backend confirmation. Typed credential
metadata survives localized desktop prompts; frontend identity is semantic and
separate from the Python OS through the provider's diagnostic integration.

All 13 user guides were updated with candidate/stable separation, retained-data
and legacy limits, removal blockers, emergency controls and reporting consent.
Canonical recovery choices, plan/error sentences and cleanup phases have all 12
non-English translations, including Czech. Native-speaking review is unverified.
Current Root handoffs now distinguish published 1.8.2 Android passive inspection
and macOS CA correction from this candidate; historical code/bundle pins remain.
The issue form includes Android and requests the existing diagnostic instead of
another install/doctor run or private profiles.

## Verification model

The Qt journey tests execute actual CLI, Store, shared recovery assessment,
desktop adapter and widgets with simulated TV IO. Android browser journeys use
actual CLI/Store/Android adapters for Home-off, retain, legacy package rejection,
running worker and cancelled authentication. The continuation case executes the
production detached No-root observer and simulated vendor processes locally,
loses the host after Helper's durable terminal, then uses shared recovery to
finish original Home/configuration without resubmitting Helper. Browser rendering
uses those actual events; additional result-contract cases cover waiting and
missing/false/true clean-removal proof. See the
[maintained failure-injection matrix](../development/INSTALLER-RECOVERY-MATRIX.md).

Environment: pinned project Python 3.12 virtualenv, PySide6 offscreen,
`LANG=en_US.UTF-8`, `PYTHONDONTWRITEBYTECODE=1`, a task-specific font cache and the
existing npm lockfile/dependencies. Browser: installed Google Chrome via
Playwright. No dependency or version changes.

Focused pre-integration checks:

- `python -m unittest tests.cytv.test_desktop_recovery tests.cytv.test_gui tests.cytv.test_i18n android.tests.test_bridge android.tests.test_root_recovery` — **95 tests passed**.
- `python -m unittest discover -s android/tests` — **41 tests passed**.
- Android `localization.cjs`, `ui.cjs`, `checks.cjs` — passed: 13 catalogs, responsive layouts, keyboard/default-No behavior, typed prompts, retained checks and connection validation.
- Android `connection-first.cjs`, `maintenance.cjs`, `recovery-journey.cjs` — passed, including all 13 removal/maintenance locales, proof-only removal completion and the six actual recovery event journeys above. Cancellation was additionally rendered with a waiting removal plan to cover pre-auth intent presentation.
- Python 3.9 grammar for changed production/fixture Python files, `node --check` for both Android UI scripts and `git diff --check` — passed.

Qt offscreen reports its usual platform/font warnings; these runs do not verify
native window-system typography. Complete installer/setup/Android, affected TV
runtime, final browser checks and the new full-removal adapters must be verified
on the combined candidate before freeze. No Linux session/cgroup or retail
filesystem/vendor persistence, physical Home/sound/standby/cold boot, OTA,
rollback or universal legacy cleanup result is claimed. Old Helper writer
drainage and temporary carrier replacement require their own final implementation
tests and matching-device acceptance; UI proof handling does not establish them.

## UI review correction: explicit removal proof

Review of `9f361b00` found that an explicit Uninstall result with a completed plan
could bypass cleanup proof if its disposition was missing or set to another goal.
The Qt worker/widget regression reproduced six incorrect combinations; the
Android browser regression reproduced the missing-disposition case. Explicit
Uninstall now requires both `disposition: clean-removal` and Boolean
`verified_clean: true` before either UI presents completion. Other recovery goals
retain their existing rules. Tests exercise nine disposition/proof combinations in
Qt and eighteen edition/disposition/proof combinations in Chrome.

The same review found two duplicate canonical catalog rows. Their effective
translations were moved to the original rows and the duplicate definitions were
removed. Exact equality of all effective catalog mappings against `9f361b00` was
verified; a uniqueness regression prevents silent replacement by future rows.

Focused verification: `python -m unittest tests.cytv.test_desktop_recovery
tests.cytv.test_i18n` — **45 tests passed, 2.352 s**. Python 3.9 grammar,
Android UI/regression JavaScript syntax and `git diff --check` passed.
Chrome `removal-result.cjs`, `maintenance.cjs` and `recovery-journey.cjs` all
passed: the explicit proof regression, valid cleanup completion, retained results,
LG Home goal and actual original-operation continuation remain covered.
These are UI/source checks; full provider integration and physical acceptance
remain pending as above.
