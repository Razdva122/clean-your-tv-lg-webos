# Task 1 report: typed credentials

Date: 2026-11-06. Worktree: `codex/installer-recovery`.

## Result

Transport emits a validated `CredentialPrompt`, a `str` subclass carrying
`credential_type` (`key`, `root`, `developer`). Existing one-argument string and
getpass-style callbacks continue to receive a string with the same prompt text.
CLI localization reconstructs that metadata on the translated/formatted string.
Android uses explicit metadata without interpreting the display text, and refuses
unsupported explicit types before requesting input.

For legacy untyped callers only, Android preserves exact canonical/localized
label matching. This additionally recognizes canonical key/root labels while a
non-English locale is active. Arbitrary untyped text retains the prior developer
default; no substring/keyword heuristics were introduced. Explicit metadata wins
even when the display text names a different credential kind.

Authentication order, original profile/key selection, SSH pinning, passive
`persist=False`, and cancellation propagation were not changed. No dependencies,
release versions, TV connections, issue changes, or public reports were added.
No user-visible prose or control flow changed, so existing translations and user
guides need no wording changes for this task. Hardware acceptance remains untested.

## Regression evidence

The first change was the passive Root regression in
`android/tests/test_root_recovery.py`. It invokes the actual bridge recovery flow
through `root_passive.inspect_saved` and its actual secret callback. Only network
connection, encrypted-key loading, and the remote read are replaced; real
`load_identity` and `root_auth` produce the prompts. The original profile, pin,
operation, and imported key bytes must remain unchanged.

Before production edits, running:

```sh
/private/tmp/cytv-recovery-venv/bin/python -m unittest android.tests.test_root_recovery.AndroidRootRecoveryTests.test_passive_authentication_keeps_key_and_root_types_in_every_locale
```

failed in all 11 non-English locale subtests with observed
`['developer', 'developer']` instead of `['key', 'root']`. English passed. After
the typed path was implemented, that same test passed across all 12 locales.

Expanding the existing legacy raw/localized bridge regression initially failed
with `developer != key`, then passed after the exact compatibility fallback was
restored. The original localized semantic assertions were retained.

## Verification

All commands ran from the designated worktree. The coordinator completed
`npm ci` before task dispatch. Python environment: Python 3.11 with pinned
Paramiko 3.5.1, websockets 15.0.1 and psutil 7.2.2.

```sh
/private/tmp/cytv-recovery-venv/bin/python -m unittest android.tests.test_bridge android.tests.test_root_recovery tests.cytv.test_transport tests.cytv.test_cli tests.cytv.test_root_install_recovery tests.cytv.test_i18n tests.cytv.test_failure_help
```

Passed: 141 tests, no skips.

```sh
/private/tmp/cytv-recovery-venv/bin/python -m unittest discover -s android/tests
```

Passed: all 38 Android tests.

Expanded affected run:

```sh
/private/tmp/cytv-recovery-venv/bin/python -m unittest android.tests.test_bridge android.tests.test_root_recovery tests.cytv.test_transport tests.cytv.test_cli tests.cytv.test_root_install_recovery tests.cytv.test_i18n tests.cytv.test_failure_help tests.cytv.test_desktop tests.cytv.test_gui
git diff --check
```

Passed: 169 tests, 21 existing GUI tests skipped because Qt is unavailable.
The three argparse usage/error messages are expected outputs from negative
interactive-auth argument tests, not test failures. `git diff --check` passed.

The coordinator subsequently installed the existing pinned Qt build dependency.
The previously skipped suite was then executed explicitly:

```sh
/private/tmp/cytv-recovery-venv/bin/python -m unittest tests.cytv.test_gui
```

Passed: all 21 GUI tests with `QT_QPA_PLATFORM=offscreen`, no skips. Qt emitted
non-failing font/offscreen platform warnings (font aliases, CJK OpenType support,
size hints, raise and keyboard grabbing). No tests connected to a TV.

Coverage includes actual passive raw authentication in every locale; typed
metadata surviving the actual CLI localization boundary in every locale; legacy
raw/localized calls; authoritative/malformed explicit types; string callback
compatibility; genuine encrypted RSA unlock; Developer Mode typed requests;
Root secret cancellation without retry; unchanged original recovery records;
and returned secret absence from events, logs, saved diagnostics and other test
files. Existing pin/identity/transport regression tests passed.

## Handoff

The product/test change is committed together with this report. Obtain its SHA
with `git log -1 --format=%H -- cytv/transport.py`. Independent task review by the
coordinator/reviewer remains required. No implementation concerns are known;
physical TV behavior was not verified by this focused task.
