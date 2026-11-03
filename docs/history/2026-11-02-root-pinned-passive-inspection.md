# Root pinned inspection and passive status — 2026-11-02

Source development only. No TV was contacted, staged, installed, recovered or
changed, and no owner installation result is published. Related: #101, #240,
#216 and the Windows Root follow-up in #200. #133's existing pinned handoff,
#161's foreign-Home refusal and installed System Updater 1.1.2 remain unchanged.

## Exact source

Implementation: `a75ca76a61ab065fcbd8d178561ba67d94f976f7`, based on
`da748e26b015564d98aa2deba8b3cfb9c8b19f4d` (`origin/release/next`).
These hashes identify trusted HOST files, not retained TV code or consent:

| File | SHA-256 |
| --- | --- |
| `cytv/transport.py` | `43f6940ef1d7c0732dbf037e18651bafc59c03a189bf5b9146f3e072fb613011` |
| `cytv/operations.py` | `2dc13c54fe1bec354867933b22b0f4bf6b171dd785a92e76b3590f33c15872c2` |
| `cytv/diagnostic_context.py` | `5b642a9ce0871af8fe71bb25be19853bca72098c8da0281a87be9706cb55a87a` |
| `cytv/root_passive.py` | `038f0ae1d49f05aeac8ccd85492db90a9ed8ef680bc00e86d35f41c9785d287a` |
| `scripts/root-install-recovery.py` | `5cb3509c0f79c3ad5d025239368d23539af64d9fca042a38e7484260c2a0ee0a` |
| `scripts/root-passive-inspection.py` | `9b66546220f89a0f7db4244f724a89ed419adfb013df43b78e5a13f093dbd50d` |

Cancellation bundle/modules are unchanged and not rebuilt here. For #101's new
option review these host identities in addition to the exact approved bundle.
#133 still names its original complete source: do not silently substitute this
script into an older handoff. No new bundle pin is invented.

## Cause and resulting boundaries

Internal admission refused every secret prompt after resolved SSH rejection.
Explicit `inspect --interactive-auth` now permits hidden local entry while
requiring the original local cytv host pin. Echo fallback, missing/changed pin,
EOF/cancel, timeout, partial auth and interrupted agent login stop. No identity,
secret, profile or trust change persists. Inspect stages only after successful
authentication. Remove/reconcile reject this flag and retain noninteractive
proof/control checks.

Historical `coordinator-submitted` status staged a coordinator and could execute
retained Python binding code while diagnosing exit 127. Root INSTALL status at
that boundary now reads only exact-operation data using system Node. Pending
is preserved, recovery-required remains and diagnostic data never enables resume
or finishes the record. This deliberately also refuses to infer completion from
a complete/other-stage record at this boundary; separately reviewed recovery is
needed. Foreground successful setup and other maintenance states keep existing
paths. No request, receipt, guard or journal is rewritten and no worker replays.

The internal passive script selects exactly one original saved Root profile and
UUID, requires its existing pin, and reads request/submission, raw manifest
candidate and worker-driver hashes, bounded log categories and ordered Python
binding/launcher/inventory/executable DATA. Only exact archive paths from that
original host receipt are allowed; no latest /tmp selection. This is internal
consistency, not full snapshot/package admission, process quiescence, execution
proof or original deployment diagnosis. Blocked/missing/unsafe/inconsistent data
stop. Report fields are fixed categories, revalidated at export without UUIDs,
addresses, paths, commands, credentials, raw exception text or full logs.

Shared files for coordination with No-root work: `cytv/transport.py`,
`cytv/operations.py`, `cytv/diagnostic_context.py` and associated installer tests.
The operations change is Root-install-only. Ordinary transport defaults and
No-root behavior remain unchanged. No dependency, endpoint, permission or new
persistent TV state. Embedding installers need normal candidate rebuild; no
version, release scope, build, signing or publication is selected here.

## Verification and independent review

- `npm ci`; unchanged cytv/build requirements installed in a temporary venv,
  Python 3.14/macOS ARM64.
- Red/green regression for inspect flag, original-identity password fallback,
  safe report fields and status. Baseline release/next fails the explicit
  no-coordinator-staging assertion; current source passes.
- `scripts/test.sh installer setup`: 656 installer tests (38 expected optional
  skips), 222 setup tests and Homebrew JS/Python checks pass. Initial runs failed
  on absent local fonttools and an untranslated new message. Installed the
  normal build requirement and reused existing translated host-key refusal;
  no product guard was relaxed.
- `scripts/test.sh android`: 26 tests pass; no Android device/emulator used.
- 63 focused passive/auth/recovery/diagnostic tests pass, including real local
  SSH handshakes, rejection then password success, missing/changed pin before
  secret, agent-refusal no retry, cancellation/EOF/timeout/partial auth,
  unchanged pending/profile/trust bytes/modes and privacy canaries.
- Exact Node 8.12.0 Darwin x64 executes filesystem fixtures. Official archive
  SHA-256 `ca131b84dfcf2b6f653a6521d31f7a108ad7d83f4d7e781945b2eca8172064aa`
  verified against nodejs.org SHASUMS256; ES5 parsing succeeds. Fixtures cover
  UUID/candidate/submission/snapshot mismatch, blocked/missing state,
  links/owners/modes/oversize/truncated JSON and unchanged original bytes/modes.
- Independent review found official inventory mode 0644 rejection and loss of a
  short log's first complete line. Both reproduced red, fixed with tests and
  re-reviewed with no further actionable findings.
- Documentation and diff checks pass. Twelve localized user-guide boundaries
  plus English reviewed: existing setup/controls, default-No recovery and
  translated errors remain applicable. Internal source-only flags add no public
  setup step; maintainer handoffs/passive contract updated.

## Remaining work

Original #101/#240/#216/#200 recovery and historical causes remain unresolved.
No TV model, firmware/webOS, remote or component acceptance is established by
these host tests; device values are unknown here. Physical Home/controls, sound,
standby, cold boot, OTA, rollback/removal and root preservation are untested.
Actual Windows/frozen CLI/GUI hidden prompting and exact packaged artifacts are
untested and required before an applicable owner handoff. No full frozen
candidate or signed acceptance ran. Owner agreement remains required for any
bounded device read and separately for later recovery mutation.
