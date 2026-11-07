# No-root observer error evidence — 2026-11-07

## Scope and diagnosis

Source-only follow-up for [#376](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/376).
No TV was contacted or changed; no new reporter installation result is published.
The original device installation and recovery cause remains unconfirmed.

The published v1.10.0 host `no_root_observer.invoke` catches `RuntimeError` around
both SSH execution and JSON validation. `TVCommandError` and other installer
`UserError` types inherit it. The replacement `pending-operation` discards the
numeric SSH status, storage guidance and known connection category. It also
makes malformed JSON and mismatched responses indistinguishable. The supplied
old diagnostic cannot reconstruct the discarded evidence or prove which of
these conditions occurred. Its later failed observation cannot establish the
cause or outcome of the initial package operation.

## Change and investigation limits

Preserve typed installer errors and annotate the exact host observer command
with a fixed failure category. Generic transport exceptions retain the existing
safe user message. Revalidate both current and retained categories at export;
raw exception text, output, identifiers and environment are excluded. The real
SSH receive deadline gets a fixed `operation-timeout` reason without changing
its message or deadline. Invalid status shapes remain refusals.

Use shell `unset` instead of `env -u` for the observer invocation. A controlled
POSIX-shell/Node test demonstrates successful environment isolation with an env
utility that rejects all options; it does not identify the reporting TV's env
implementation. No alternate package request, automatic retry, permissions
change or recovery bypass is introduced. The bound TV `PROGRAM` bytes are
unchanged, so existing capsule/source hashes remain valid.

The diagnostic reference includes category meanings and bounded follow-up
investigations. It does not prescribe speculative package or firmware changes.
The fixed categories cannot supply the private remote exception or a missing
vendor terminal result. Original #376 remains open and is not a confirmed fix
of installation, Home routing or physical recovery.

## Verification

The new regressions failed before the corresponding changes: typed errors were
replaced, storage guidance was lost, observer categories were absent, and the
option-limited env fixture prevented launch. A separate regression reproduced
the real SSH receive deadline losing its timeout identity.

Verified on macOS using the maintained `.venv-cytv` interpreter after `npm ci`:

- New observer evidence regressions: 7 passed.
- Focused observer/integration/transport/diagnostic/history/guidance suite:
  128 passed (includes those seven cases).
- `PYTHON=<maintained-venv>/bin/python bash scripts/test.sh installer android`:
  1,003 cytv cases passed with two platform skips; 43 Android cases passed;
  Homebrew payload/installer/continuation and real runtime/bridge/UI checks passed.
- Python 3.9 AST compatibility, `npm run format:check`, local Markdown targets
  and `git diff --check` passed.
- Independent review found no actionable defects.
- AST extraction and byte comparison confirmed unchanged TV `PROGRAM`, SHA-256
  `216527f79b3c2e3348c8b9351ffd76a915cf1698fb69688424d4af0ceca4102f`.

This is focused implementation verification, not a complete frozen-candidate
build or published installer acceptance.

Documentation review: setup steps, confirmations and controls are unchanged;
all displayed error messages already exist in localization. The developer
reference and this dated source record explain the additive evidence contract.
No localized user-guide step changes are required. Host desktop/console and
Android installers need rebuilding for delivery; no Helper/TV package version,
release version, selected build or candidate scope is changed here.

Physical installation, Home/Back/emergency behavior, sound, standby, cold boot,
OTA and rollback are untested. Source/model tests do not certify those paths.

## Integration into the next candidate

[PR #380](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/380) merged into
`release/next` as `6cb529ed92bbb39027c815fb567410efbcace79a`. Its final head
`e50860090b5a98a61656126c1bb559a82bec0cb0` includes concurrent #379; all 72
affected observer/report/history/guidance checks passed on that combined source.
The earlier full local installer/Android results above precede #379.
[Final-head CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42359837874)
is pending at integration; release-routing policy passed. No publication or new
physical acceptance is claimed. The release inventory keeps #376 linked while
explicitly retaining its unknown original installation/recovery cause.
