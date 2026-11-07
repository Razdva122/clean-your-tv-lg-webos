# No-root observer storage — 2026-11-07

## Change and limits

Source-only follow-up for [#201](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/201).
No TV was contacted or changed. This record describes implementation tests,
not a new publication of another user's installation results.

The private observer root moves from `/media/developer/.cytv-installer` to
`/tmp/.cytv-installer` with the existing 0700, owner and strict ancestry checks.
The former parent can be unwritable to Developer Mode, and its root-owned 0775
layout was also rejected before mkdir. Public IPKs remain in SDK staging:
newer appinstalld versions restrict installation from `/tmp`. Only public
traversal accepts the fixed root-owned SDK 0775/0777 developer and 0777 temp layouts.
No vendor chmod or broader private-ancestry exception is added. Public staging
retains its existing vendor shared-namespace trust limitation; the installer's
pathname read is not atomic with host verification.

One storage check before `Store.begin` exercises private write/hardlink/fsync
and staging mkdir/rmdir. Storage refusal leaves no new pending receipt/capsule.
Later disconnects and storage failures still retain pending evidence.

Changing PROGRAM intentionally prevents continuation of every older bound
observer source, including partial installations. Existing separately confirmed
project removal remains the supported fallback: archive the original local
journal, retain the capsule, fence old writers with the normal full restart,
skip absent packages and verify cleanup before a separate new setup. No old
capsule source is executed or silently rebound. Both private root locations are
included in cleanup. Loss of volatile `/tmp` evidence never grants permission
to resubmit an unknown package operation.

There is no new recovery protocol, confirmation, automatic reinstall or global
package-status call. The legacy UK6400 historical transaction and the C2's
original installation outcome remain unresolved; host checks do not establish
retail compatibility or recovery.

## Verification

The new regressions first failed on pending creation after staging refusal and
on unsupported storage-check. They pass with the implementation. Real Node and
filesystem cases cover the C2-shaped SDK metadata, storage refusal without a
journal, ordinary installation after that refusal, and missing volatile evidence
without resubmission. The existing recovery journey is exercised against a real
Store: declining cleanup keeps the legacy journal; confirmed cleanup archives
it, retains its capsule and submits no install/remove request for absent apps.
Cleanup also recognizes the new private root and waits for its restart fence.

The initial focused run also exposed stale exact-PROGRAM test adapters after
#382 and the new cleanup fixture's missing root-owned sticky-parent model.
The branch was refreshed to reuse upstream #384's adapter correction; only the
new storage-check reply is added to that adapter here. The cleanup fixture's
parent model was corrected and verified. Two inherited package tests expected
uncompiled service bytes after #381; their expectations now match compiled
service assets, without changing packaging behavior.

Local verification:

- `scripts/test.sh installer android` completed Homebrew runtime/bridge/browser,
  eight payload, six installer and six continuation tests, then 1,034 installer
  cases (two skips). Its only failures were the two stale package expectations
  described above; the runner consequently did not reach Android.
- After correcting those expectations, all 85 affected packaging, integration,
  diagnostics and cleanup cases passed. The unchanged full suite was not repeated.
- Android: 43 passed separately.
- Current storage/diagnostic/initial-setup checks: 13 passed; the SDK permission
  test executed actual Node 0.10.15, 0.10.25, 0.12.2 and 23.11.0.
- Source-injection and new cleanup checks: four passed.
- Independent review: no blocking findings. Python 3.9 syntax,
  `npm run format:check` and `git diff --check` passed.

The initial browser launch was sandbox-blocked; the local runner was rerun with
normal host browser access. Logs remain local. These are affected source checks,
not a full frozen-candidate build or physical acceptance. No standalone CI
or candidate build is requested by this task. Physical installation, service
registration, Home/remote behavior, audio, standby, cold boot, OTA and rollback
are untested. Host desktop/Android installers and the shared cleanup support
need rebuilding in the normal future candidate; no versions or pinned build
are selected here.

Documentation: the developer authority reference is updated. Existing setup,
recovery confirmations, restart guidance, messages and all translated controls
remain applicable; no localized user-facing step changes are introduced.

## Integration

[PR #385](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/385) merged into
`release/next` as `459f10718482d3096ff4cada4e2d320cf01c53c4`, for draft
[candidate #374](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/374).
Standalone CI was skipped by explicit maintainer instruction. No public release,
selected build or device acceptance is claimed. The original issue remains open.
