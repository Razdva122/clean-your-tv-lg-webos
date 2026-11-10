# No-root removal boot-check diagnostics (#472)

Date: 2026-11-10. Diagnostic improvement only; original device failure remains
unconfirmed. This branch does not change the frozen v1.16.0 inventory or build.

## Evidence and scope

The reporter supplied two standard diagnostic exports. Both show cytv 0.15.0
failing in `capture_boot` → `boot-create`, SSH exit 1, before control restoration
or package deletion. The later issue comment says CYTV still launches after TV
power-on and one Home press returns to LG Home. That is unfinished removal, not
successful recovery. The existing reports discarded the remote exception, so
neither a directory-layout problem nor a filesystem/Node failure is established.
No private attachment contents are reproduced here.

The approved change reports fixed boot action, check step, exception name/code,
filesystem operation, fixed guard reason and volatile-directory mode/owner/type.
It does not export paths, exception prose, stack, credentials, marker identity,
boot UUID, app inventory or raw stdout/stderr. The host revalidates categories
again when saving reports and failure history. Bootstrap/transport failures keep
their typed error and numeric SSH status with the host-known boot action.

A caught synchronous boot-check error returns a semantic failure envelope, as
in the existing No-root observer protocol. SSH completion is not removal success:
the host raises before consuming a boot proof or allowing cleanup to continue.
Non-boot provider actions retain their existing execution/error behavior. No
new permission, endpoint, state field, retry, automatic restart or relaxed path
check is introduced. Existing marker, restart and package/file/process proofs
remain required. The shared raw provider remains independently executable for
Root cleanup embedding.

## Verification ledger

Existing #481 source/CI results were consulted. They cannot establish error
metadata propagation: the specific missing evidence is the new boot-check error
wrapper plus report/history allowlisting. Focused checks cover those changed
inputs, small SSH stdin requests, marker tampering and interrupted continuation.
No full candidate build, signing, installation or device operation was run.

- Red: actual Node execution with a non-admitted volatile directory failed the
  regression because no safe diagnostic envelope reached the host.
- Green: complete No-root removal suite passed 73 tests on current Node.
  Two subsequent narrow checks passed for storage-full guidance and rejection
  of malformed/mixed error-success envelopes; unrelated cases were not repeated.
- Exact Node 0.10.15, 0.10.25 and 0.12.2: eight affected boot cases passed on
  each runtime (24 executions). The later storage-guidance check also passed on
  current Node and exact Node 0.12.2.
- Diagnostic report/history suites: 55 tests passed, including revalidation of
  every new field against structured/private values.
- Root simple-removal/shared raw-provider checks: 22 tests, one existing
  platform-specific skip, no failures. Deliberately injected cleanup failures
  print expected tracebacks; the suite passes.
- Source-injection/format build regressions: three tests passed. Formatting and
  Git whitespace checks passed. No full local candidate suite was repeated.
- Independent static review found no actionable correctness/privacy issue.
  The review did not repeat tests or contact a television.

## Remaining work

No television was contacted or changed. The original C5 cleanup error still
requires a standard diagnostic report produced by an installer containing this
change. Do not infer its cause from the injected host cases or announce a fix
for the reported removal. The release coordinator decides whether to admit this
change after freeze; no selected artifact or acceptance record is changed here.
