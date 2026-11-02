# Early Root admission and connection guidance — 2026-11-01

Stages four and five of the maintainer-requested installer improvements move the
existing Root Home-interface read contract ahead of private Python/package
preparation and add phase-bound, typed connection guidance across console,
desktop and Android. The [behavior contract](../development/INSTALLER-PREFLIGHT-HELP.md)
records schema parity, timeouts, pending/trust boundaries and filtered exports.
No Root TV runtime, permission, package format or recovery authority changes.
Two existing read endpoints are now called earlier by the host.

Current CLI/diagnostic references and all twelve installer guides are updated;
Czech remains TV-only. No version, freeze, build or physical acceptance selected.
Original #133/#216 recovery and firmware support remain unresolved; #217 still
needs the previously requested reporter information. These are partial workflow
improvements, not confirmed fixes for the original device reports.

## Verification

- `npm ci` completed before implementation.
- Red/green tests cover exact provisioning-request/schema parity, missing or
  malformed interfaces stopping before runtime preparation/package submission,
  Root reinstall admission before removal, unchanged maintenance/pending Doctor,
  bounded numeric failure codes and hostile diagnostic projections.
- Typed guidance tests distinguish Root/No-root credentials and phase-specific
  transport failures, preserve unknown causes, prioritize pending state, retain
  trust/journal bytes and verify real CLI semantic events and report output.
- `scripts/test.sh installer android setup` passes: 640 installer cases (two
  expected platform skips), 26 Android and 220 setup cases, plus Homebrew
  payload/runtime/bridge/continuation checks. Actual Qt is exercised locally.
- Real Chrome tests pass across twelve locales: advice, manual connection review,
  preserved custom port, no automatic operation or generic Status/Restore action,
  narrow/landscape layouts, per-run reset and failed-prerequisite ordering.
  Locale selection, persistence and native-message checks also pass.
- Complete translated guidance and new check labels are covered in all eleven
  non-English installer languages. Qt tests preserve report-failure warnings and
  show failed Root interfaces ahead of passed prerequisites.

Host/transport/UI fixtures only. No TV was contacted or changed; TV model,
firmware/webOS and remote are not applicable. Device Home, sound, standby,
cold boot, OTA and rollback remain untested. No owner result or private diagnostic
content is published. Independent final read-only review found no actionable safety, correctness or
documentation findings; its 23 capability/guidance cases passed. Changed Markdown
relative links and `git diff --check` pass. Final CI and integration are recorded
after verification.


## Integration

[PR #235](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/235) merged into
`release/next` as `654d5b856715caa7b79e597dfa5a541544f0b461` after exact source
`2b7060af3448800334695f9a1dc0f9e855992f46` passed selected
[Linux/macOS/ARM checks](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41337969918),
[frozen Windows/macOS Intel entrypoints](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41337970006)
and [integration policy](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41337986717).
Linux CI ran 640 installer cases (38 optional/platform skips), 26 Android and
220 setup cases. Actual Qt and twelve-locale Chrome were tested locally. The
Russian Qt failure fixture was visually inspected: failed Root check first,
readable guidance and preserved missing-report warning. Product/test merge files
match the verified source. Focused CI correctly skipped frozen full-candidate,
publication and browser jobs; local browser evidence does not replace final
candidate checks.

Candidate #210 records partial delivery without selecting a version or build.
Original #133/#216 stay open/planned for recovery/firmware work; #217 stays
open/needs-info under the existing reporter request. Source-integration comments,
current labels and generated inventory are verified during integration. No device
operation, public delivery or original-report resolution is claimed.
