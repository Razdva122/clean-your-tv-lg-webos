# Installer recovery journey — 2026-11-01

## Source behavior and limits

Second stage of the maintainer-requested installer improvements. Console,
desktop and Android share **Review recovery options** / `cytv recover`. A pending
setup delegates to this path and returns before new installation. Inspection and
changes have separate default-No confirmation; `--yes` and noninteractive mode
cannot approve recovery. Saved TV/edition/port matching remains canonical.

Root inspection may run verified support code. Only existing verified resume
proof permits Home activation, rechecked at mutation. Missing host receipts do
not hide active/incomplete Root operations. Existing current, terminal Root
removal proof remains sufficient for its existing reconciliation. No orphan
adoption, cancellation or private-runtime repair is introduced.

No-root offers guarded removal only after the existing bounded package-status
check and rejects conflicting/unsupported removal records before restoration.
The backend repeats a positive idle check before changes. A false returnValue
with an empty status list is rejected. Successful cleanup stops before new setup;
Home preferences may be lost. Denied, unknown, busy or malformed state preserves
evidence and exposes the current attempt's report. Reports retain filtered known
status through the first-stage diagnostic contract. A presentation event never
authorizes backend work or persists a recovery capability.

The blanket Root failure advice to choose Remove again is removed. Android
focuses Cancel for default-No prompts and suppresses installation-success guidance
when setup only reviewed/recovered a previous attempt. Blocked recovery results
offer report export without Restore/retry buttons. All twelve localized installer
guides and current CLI/recovery references describe the unpublished behavior;
Czech remains a TV-only locale. No endpoint, permission, dependency or persistent
TV state is added. Embedding installers must be rebuilt at candidate freeze.

This is a partial workflow/safety improvement for #201/#216, **not a recovery fix
for their original devices**. The denied No-root terminal-authority contract and
Root original failure/passive handoff admission remain unresolved maintainer work.
Keep both issues open and planned. No new owner evidence, repeated probe, reset,
Remove retry or TV change is requested. No TV was contacted, staged or changed.
Model/firmware/remote: not applicable to simulated host tests. Physical controls,
Home routing, sound, standby, cold boot, OTA and rollback: untested in this task.

[Recovery contract](../development/INSTALLER-RECOVERY.md) ·
[No-root authority limits](../development/NO-ROOT-PACKAGE-AUTHORITY.md)

## Verification

- `npm ci` prepared dependencies before implementation.
- Red/green recovery tests cover default-No decisions, noninteractive rejection,
  no implicit reinstall, denied/busy/malformed/false-idle responses, timeout,
  removal conflicts, strict stages/entries, Root resume, orphan/incomplete Root
  state and verified Root removal. Twelve recovery cases pass.
- Actual Qt desktop/real CLI/state with simulated TV IO cover the saved target
  and custom port, both pending actions, inspection/removal confirmations,
  report export, no upload/reinstall on blocked/declined recovery, retained
  journal bytes and absence of stale report reuse. Focused journey/CLI checks
  pass; the new Tools command is covered by the GUI dispatch test.
- Independent read-only review found and then verified fixes for orphan Root
  state and Android installation-success instructions after recovery-only work.
  Final review found no remaining actionable correctness/safety issue.
- Android real Chrome maintenance checks pass in twelve locales and at narrow,
  portrait/landscape widths, preserving custom ports and operation recreation.
  Semantic plan states suppress unrelated Restore/retry and installed-Helper
  guidance, expose report save, and focus Cancel for default-No prompts.
- Setup: 220 cases pass. An earlier sandbox-only terminal failure was rerun with
  normal local process/terminal access; no product workaround was applied.

Final affected-suite and CI evidence is recorded with integration below. This is
source validation, not final candidate package or physical-device acceptance.

Final local affected verification: `scripts/test.sh installer android` passes
599 installer cases (two expected platform skips), 24 Android cases and the
Homebrew payload/runtime/bridge/continuation checks. Setup's 220-case pass above
covers unchanged setup dependencies. Final source journey tests and GUI dispatch
are included in that successful run. `git diff --check` passes.
