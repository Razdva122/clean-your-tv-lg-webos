# No-root observer runtime diagnostics — 2026-11-07

## Scope and implementation

Source-only follow-up for [#378](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/378),
after the diagnostic/portable-launch work in [#380](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/380).
No TV was contacted or changed. This is not a new reporter installation report,
a confirmed cause of the original failure, or device compatibility evidence.

The prior improvement distinguishes SSH/transport/JSON failures but a synchronous
observer guard or Node filesystem error still reduces to a numeric command
failure. Wrap only the current invocation with a bounded JSON error envelope.
Allowlist standard exception names, fixed module/filesystem codes and the
observer's fixed guard reasons on the TV, then revalidate them at host intake,
current export and retained-history export. Do not emit exception prose, stack,
paths, operation identifiers or raw command output in reports.

The host checks the original operation binding and rejects every error envelope;
malformed detail and foreign bindings remain failures. Handled runtime errors
use a JSON envelope on stdout, not an invented SSH exit status. `ENOSPC`/`EDQUOT`
retain existing storage guidance. The shared report reason allowlist now also
preserves `tv-storage-full` instead of replacing it with `unknown`.

No retry, additional TV probe, permission repair, package request, pending-receipt
cleanup or relaxation of recovery checks is introduced. Synchronous errors in
the current `prepare`/`status` invocation are covered; shell/runtime startup,
parse-before-execution and asynchronous/detached-worker failures retain their
existing command/transport/terminal paths. This diagnostic does not establish
that no package was submitted before a later failure.

The protocol, capsule contents and bound TV PROGRAM remain unchanged. AST byte
comparison with the starting source confirms PROGRAM SHA-256
`216527f79b3c2e3348c8b9351ffd76a915cf1698fb69688424d4af0ceca4102f`.
Old pending operations remain subject to their existing source/ownership checks.
No old diagnostic can recover discarded remote evidence retrospectively.

## Validation

- Baseline observer diagnostic suite: 7 passed.
- Three new regressions failed before implementation: runtime detail was lost,
  a matching error envelope was accepted as a plain response, and retained
  runtime fields were discarded. New ENOSPC/EDQUOT checks also reproduced loss
  of the shared report reason before correcting its allowlist.
- Expanded diagnostic suite: 11 passed, exercising real shell/Node execution,
  real prepare/status filesystem state, unsafe-permission refusal without file
  changes or retries, unknown-code redaction, hostile current/retained metadata,
  operation binding, storage guidance and later failure history.
- The 11 diagnostics passed on exact Node 0.10.15, 0.10.25 and 0.12.2 as well as
  current Node. No legacy-TV compatibility is inferred.
- Independent review found no actionable defects; its 11 diagnostics and 19
  real observer tests passed, and the generated launcher parsed as ES5.
- Python 3.9 AST syntax, `npm run format:check` and `git diff --check` passed.
- Combined `LC_ALL=en_US.UTF-8 PYTHON=<maintained-venv>/bin/python bash scripts/test.sh installer android setup`
  is running at implementation handoff; its final result is not yet claimed.
  Per maintainer instruction, implementation CI is not awaited before merging;
  complete combined candidate validation remains required before release.

## Documentation, delivery and limits

Updated the developer diagnostic contract, including the difference between
operation-scoped first failure and TV-wide history. Reviewed setup/recovery and
localized user guidance: no command, control, confirmation or displayed message
changes, so no translated user-guide edits are needed. Existing recovery advice
continues to retain evidence and forbid blind reinstallation.

Host desktop/console and Android installers must be rebuilt for delivery. No
component version, selected build, acceptance pin or release version is chosen.
The original #378 installation/recovery outcome remains unresolved; keep it open
at the status of that remaining investigation, not awaiting-release/released for
the diagnostic-only change. Physical installation, controls/emergency release,
sound, standby, cold boot, OTA and rollback remain untested.
