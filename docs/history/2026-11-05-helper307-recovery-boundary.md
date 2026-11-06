# Helper installation recovery boundary (#307) — 2026-11-05

## Outcome

No supported automatic recovery of the legacy #307 installation has been
established. The prepared correction improves the blocked recovery error and
adds exact-sequence host coverage; it does not recover the TV, clear the journal,
prove installer idle, or authorize a package request. The unresolved work stays
with the maintainer, not another reporter inventory request.

[Issue #307](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/307)
retains a failed Helper installation and a refused package-status query. Packaging
PR #312 and diagnostic PR #309 do not repair its original pending transaction.
The existing [original-transaction handoff](../development/NO-ROOT-TERMINAL-HANDOFF.md)
continues to govern recovery. No TV was contacted or changed here; no additional
owner installation result or private diagnostics were published.

## Why error 24 is insufficient

The reviewed source remains LG OSE appinstalld2 revision
`938ffd716c0c250bdb860100e9a41d3bd5b0b452`. It is not an identified retail binary.

- [InstallHistory.h](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/installer/InstallHistory.h)
  identifies 24 as `ErrorInstall`, distinct from complete installation (30) and
  complete removal (31).
- [Task.cpp](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/installer/Task.cpp#L294-L390)
  serializes that error as `install failed` with a nested error code. A negative
  reply does not describe current idle state or completed registration/cleanup.
- [AppInstaller.cpp](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/installer/AppInstaller.cpp#L156-L191)
  emits the finished signal, schedules task release asynchronously, and, for an
  errored unpacked install, schedules an internal `remove()` operation as cleanup.
  This is a concrete reason not to interpret the earlier error as a quiescent
  installer or to race it with a new removal. The source does not establish the
  retail TV's exact sequence.

The original diagnostic preserves a redacted error summary, not a vendor
transaction identifier. Its host diagnostic ID and phase do not create a
historical lookup contract. Neither an app directory with matching bytes nor a
missing service subtree proves that the original task and cleanup terminated.
Calling `dev/remove` is a new mutation; it cannot substitute for the denied monitor.
No available source establishes a safe historical terminal query for this receipt.
The existing vendor-contract draft in the handoff has not been sent.

## Narrow correction

`require_removal_idle()` now rethrows a No-root package-status refusal with the
existing localized capability-specific guidance instead of the generic advice
`Run cytv doctor`. It retains the exact typed exception and numeric Luna evidence.
There is no fallback bus/identity, repeated request, new endpoint, schema or state
write. Unknown/busy/denied outcomes remain blocked, and the existing exception for
provably unsubmitted removal remains unchanged.

The regression runs real installation and recovery orchestration against a
synthetic SSH boundary: Helper install fails with status 24, an app-list entry
remains, package-status is refused, and recovery stops. Both the original pending
install and a removal journal inheriting it retain their bytes and first-failure
record. There is no new install/remove, upload, restore or launch request after
the refusal. The message change was observed failing before the correction and
passing afterward. This is host simulation, not retail extractor/API acceptance.

## Verification

- `npm ci`: passed, 281 dependencies and no reported vulnerabilities.
- New sequence regression: passed for both journal shapes after observed failures.
- Recovery-state suite: 5 passed; installer translation suite: 16 passed. Existing
  translated guidance is reused; no user setup/control step changed. The existing
  recovery guides remain applicable without new commands or locale changes.
- `scripts/test.sh installer setup android` passed with the documented build/runtime
  dependencies in an isolated host venv: 235 setup tests (208.380 s), Homebrew
  checks, 761 installer tests (50.991 s; 72 existing optional/platform skips), and
  35 Android tests. Full candidate/device acceptance remains separate.
- Independent read-only review found no blockers; the new regression also passed
  independently for both journal shapes. Local documentation links and
  `git diff --check` passed.

Actual device recovery, service registration, Home controls, audio, standby, cold
boot, OTA and rollback are untested. Component versions, the release inventory,
selected candidate build and publication are unchanged. Resolving the original
case still requires an authoritative vendor terminal/cleanup contract and a
reviewed operation-bound recovery design; no owner retry is requested.
