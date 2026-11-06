# Simple removal UI checkpoint — 2026-11-06

Scope: user-approved practical removal flow on shared baseline `6416c005` plus
documentation plan `b41d23be`, branch `codex/installer-removal-ui-simple`. Earlier
UI work remains on its old branch. No advanced Helper/lifecycle implementation,
TV operation, version, build selection or publication was added here.

Desktop and Android now show **Try again** for an unfinished removal and repeat
`uninstall` for the same saved TV/edition/port. They do not enter another recovery
wizard or supply a blanket `--yes`; the provider must recognize the existing
approved goal. A lost connection has a direct connection-check message. Restart
instructions explicitly say to disconnect/reconnect TV power, wait for the
network and try again. Standby and Quick Start are insufficient, and CYTV never
reboots the TV itself. Actual busy/access/package errors keep bounded actionable
instructions. Saved keys and typed root/key/Developer Mode prompts are preserved.

An explicit removal completes only for a clean-removal disposition with both
`removed: true` and `verified_clean: true`, and no active restart-required flag.
Missing/false flags or contradictory stale completion stay neutral. Other setup
goals, including eligible LG Home/Home-control-off completion, keep their own
meaning and separate physical observations. The success wording does not infer a
historical LG/Home+ route when only project removal is proved.

All 13 guides now describe present-known-item removal, absent-item skipping,
partial setup, full restart, direct retry, actual access/busy instructions and
published/candidate separation. Twenty additional canonical messages have all
12 non-English translations, plus six Android UI labels in all 13 catalogs.
Emergency controls, original reports/keys and publication consent remain in
place. Native-speaking review is not claimed.

## Focused verification

Pinned Python/PySide6, existing npm/Playwright dependencies and Chrome; offscreen
Qt with the existing task font cache. No dependency changes.

- UI/Qt/i18n/Android adapter suite: **107 passed, 4.522 s**, excluding exactly the two provider integration cases below. A subsequently added restart-required/stale-true-flags Qt case passed separately (**1 passed, 0.237 s**), making 108 verified distinct methods for this checkpoint.
- Full Android Python discovery: **42 passed, 0.346 s**; 32 overlap the UI suite.
- Chrome `simple-removal.cjs`: all 13 localized AndroidConsole events, both editions, full-restart/connection/busy/access cases, direct same-goal retry, strict final flags and contradictory restart flag.
- Chrome `removal-result.cjs`, `recovery-journey.cjs` and `maintenance.cjs` passed, retaining strict proof, actual ordinary recovery/observer continuation, Home-off and all 13 maintenance locales.
- Python 3.9 grammar, JavaScript syntax and `git diff --check` passed.

Two intentionally RED cases on the old provider baseline are not counted as
passing: `test_actual_cli_retry_reuses_approved_goal_without_second_confirmation`
in `tests.cytv.test_simple_removal_ui.SimpleRemovalUITests` reproduces its second
confirmation; `test_root_clean_removal_cli_completes_only_after_device_proof`
in `tests.cytv.test_desktop_recovery.DesktopRecoveryTests` receives the old plan
without `removed: true`, which the UI now correctly rejects. Their new provider
implementations and actual two-step Root/No-root orchestration must be merged and
verified next. The Root SSH fixture already supports read-only `clean-target`;
its simulated reply is not deletion or boot evidence.

This checkpoint does not complete Task 5 or the user's removal goal. Combined
provider review, real boot-ID/final-sweep tests, complete candidate checks/builds
and physical Home/normal keys/sound/standby/cold boot/OTA/rollback remain pending.
No reporter device result or universal cleanup compatibility is claimed. See the
[current matrix](../development/INSTALLER-RECOVERY-MATRIX.md).
