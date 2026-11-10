# Developer Mode removal restart proof (#472)

Date: 2026-11-11. Focused implementation evidence; not physical TV acceptance.

## Cause and approved boundary

The new standard diagnostic in [#472](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/472#issuecomment-6777602667)
confirms that removal refuses a root-owned real directory with mode 0111 during
`boot-create` / `boot-root`. SSH succeeds. The
[official LG SDK 11.2 jail configuration](https://developer.lge.com/common/file/DownloadFile.dev?sdkVersion=11.2.0&fileType=conf)
explicitly creates this execute-only `/tmp` for the Developer Mode OpenSSH jail,
while other app jails receive writable sticky `/tmp`. This is not the private
key-file permission problem on Windows, nor the Helper key ownership handoff
addressed by #488 and the shared contracts in #493.

The maintainer approved a conservative fallback: ordinary removal can complete
when its existing control, startup, process and absence checks pass; unfinished
prior operations and other existing restart gates still require restart proof.
No TV permissions are changed and no marker is moved into persistent storage.

`native/contracts/boot-proof.js` centralizes No-root UUID parsing and both proof
formats using the existing trusted-source loader/stager. It is embedded in the
standalone cleanup program, including Root updater embedding. It is not an
unused Helper runtime dependency. Android Gradle tracks the canonical source as
an input. The active identity is stored once in `cleanup_boot_proof`; capturing
it clears the redundant No-root `cleanup_boot_id`. Root's own boot identity and
recovery policy are unchanged.

Schema 1 preserves the original private, inode-bound marker on root-owned
01777 `/tmp`. Schema 2 is selected only for real root-owned 0111 `/tmp` over
Developer Mode SSH; it stores the goal and actual kernel UUID without touching
that directory. Only a changed kernel UUID grants restart credit. A repeated
UUID (including snapshot firmware), missing marker, successful release or
elapsed time cannot do so. Captured schema-1 evidence cannot downgrade on retry.
Unverified restarts remain pending with translated diagnostic guidance, rather
than an endless request to power-cycle again.

## Verification ledger

The changed input is boot-proof extraction plus the exact DevMode layout
fallback, so prior diagnostics-only results do not cover the new behavior.
Matching focused results are recorded here for reuse by candidate integration.
No candidate build, signing, installation, TV connection or power operation ran.

- Red: two actual-Node restricted-directory removal cases failed on the old
  root-path guard before implementation.
- Green: 79 No-root removal tests passed on current Node, plus one subsequent
  focused lost-capture/saved-proof/process-reappearance regression. Existing
  marker tampering, full-restart and removal gates remain covered.
- Exact Node 0.10.15: 11 existing boot cases passed. Both new restricted-layout
  cases and both proof-kind/absence cases passed on each exact Node 0.10.15,
  0.10.25 and 0.12.2 (12 new-case executions).
- Trusted resources/events: 14 tests passed, including byte-identical CLI and
  Android staging and Gradle tracking of every canonical source. Contract report
  propagation: 13 tests passed. Diagnostic report/history: 55 tests passed.
- Root simple removal: 22 tests with one existing skip; Root/No-root handoff:
  23 tests with one existing skip. No failures; injected refusal tracebacks in
  the Root suite are expected.
- Standalone source-injection/build regressions: three tests passed.
  Installer localization: 23 tests passed. Formatting and whitespace checks passed.
- Independent static review found the missing Android Gradle input; it was fixed
  and a focused source-input regression passed. No restart-authority or schema-1
  compatibility blocker was found; the reviewer did not repeat tests.

## Documentation and remaining acceptance

Reviewed and updated recovery/maintenance instructions and all 13 localized
practical guides with guidance for an unverifiable requested restart. Shared
contract reference documents the API and explicit same-ID limit. No component
version, release inventory or selected build is changed by this branch.

The original device still needs a published installer containing this change
and confirmation of completed removal. An issue diagnostic establishes the
failing guard, not physical success of the fix. Same-ID snapshot restart support
remains limited without a separately verified safe volatile proof mechanism.
Keep #472 open; do not clear an unknown original operation manually or infer
success from absent packages alone.
