# System Updater self-update implementation — 2026-11-16

This is focused implementation evidence, not release or TV acceptance.

## Authorized scope

Implement the [approved design](../superpowers/specs/2026-11-16-updater-self-update-design.md) and
[plan](../superpowers/plans/2026-11-16-updater-self-update.md) for Root and No-root when root is
available. Genuine unrooted/Developer Mode execution and a legacy release bridge are excluded.
The frozen release is not changed or published by this work. Product release numbering remains
with the release coordinator. The provisioned System Updater component baseline is 1.2.11;
engine and package versions are independent fields.

## Implemented path

The normal **Update all** request is handled by the pinned bootstrap before product parsing.
It verifies a bounded signed bootstrap catalog, retains its exact target/profile/variant and
shared ownership lease, stages the engine in the inactive slot, and requests readiness from
that engine. Only that engine interprets current product state and validates profile contents.
This prevents the original product parser becoming a gate on future product protocols.

The stable interface is `engine-state` (bounded edition/release/graphics/component summary),
`engine-profile`, `engine-health`, and `engine-reserve`. The last two require the exact original
engine operation and shared lease. Original bootstrap code and Python binding remain pinned.
A dedicated immutable public root authorizes release-key chains; each catalog binds all four
edition/graphics product manifests and the complete engine archive. Package downloads remain
bound to the retained catalog, rather than mutable latest metadata.

Slot activation uses a persisted trial and previous pointer. Recycled slots have a separate
retirement/staging journal, so interruption while deleting old files or writing new ones does
not require a computer to remove a stale receipt. Readiness failure does not select partial
code. Retry preserves the signed target and immutable profile. Cancellation restores the
previous pointer only before a child product reservation; an unknown package-manager outcome
cannot be cancelled or replayed.

Own-package replacement is part of the same operation. The signed engine includes the System
Updater IPK and a bounded LS2 permission plan. Both original and candidate packages are checked
before installation. The independent installer observer records intent, acceptance and exact
terminal evidence; matching installed bytes alone never establish completion. A coherent
`engine-state/supervisor-generation.json` selects the package inventory and service generation.
The original bootstrap package receipts remain intact. A permanent Python-bound service entry
verifies the selected slot before starting its service. Registration is journaled before writes;
activation restarts the identified Node service and checks an actual LS2 status response.

After self-update, the single shared owner transfers to the existing product transaction with
the same operation ID and profile. A crash between profile persistence, child reservation and
owner transfer resumes that exact reservation. Engine-only updates finish without a product
installer. Explicit **Reinstall System Updater** reinstalls the same signed own package without
resubmitting product components. Product rollback stays on the verified new engine, which must
continue to read the retained predecessor snapshot.

Root infrastructure evolution uses the union of authenticated original, current and target
inventories. New files can be added, removed files are retired only when their bytes match the
other authenticated leg, and rollback restores the old inventory and receipts. No-root Home
packages carry the same screensaver companion recipe; the rooted executor applies and verifies
it using the existing observer journal. No-root never gains a Root Home route merely because
its executor has root access.

Own-package recovery blobs live under `engine-state/cache`, outside ordinary product-cache
pruning. They are retained conservatively. Removal and boot admission authenticate the current
generation through a fixed private helper; uncertain own-package replacement can wake only the
original recovery worker. Pending migration and foreign ownership block removal and peers.

## Focused verification

Python command prefix used:

```sh
.venv-cytv/bin/python -m unittest discover -s tests/system_updates
```

Observed focused runs (before the coordinator's final aggregate gate):

- `-p test_bootstrap_flow.py`: 7 pass. Both editions' normal handoff, engine-only release,
  same-version repair, interruption after child reservation, and uncertain own-installer retry.
  These execute real Bootstrap, Slots, Migration, SupervisorIO package/cache/generation and
  registration writes, engine request handlers and Manager reservation. Network, TV installer
  effects, LS2/process observation and child transport are fixture boundaries.
- `-p test_bootstrap.py`: 8 pass. Exact retry/cancel, refusal after child reservation, future
  current-state schema interpreted by the active engine, terminal-owner crash recovery and
  preserved product rollback after repair (including the immediate Recovery reply).
- `-p test_activation.py`: 5 pass. Signed slot inventory, confirmation binding, interrupted trial,
  wrong archive hash, interrupted recycled-slot write.
- `-p test_supervisor_io.py`: 3 pass. Own-package identity/hash bounds, LS2 permission boundaries,
  and rejection of an unrelated successful installer terminal.
- `-p test_core.py`: 20 pass, including exact immutable profile recovery at engine handoff.
- `-p test_device.py`: 52 pass, including infrastructure inventory evolution and exact-byte
  retirement protection.
- `node tests/system_updates/policy.cjs`: pass after changing the authorized No-root protocol-2
  expectation; malformed/unsupported manifests remain rejected.

The integration auditor supplies separate migration, package-identity, startup, removal and
real own-package registration/rollback tests. The coordinator owns the final aggregate Python,
Node, package/build/signing and repository checks, avoiding duplicate full runs. A provisional
204-test run encountered only five then-in-progress removal test failures; it is not final
acceptance and is superseded by the final gate recorded below.

## Remaining acceptance

No television was accessed, modified, installed, rebooted or tested in this implementation task.
The TV model, firmware/webOS, remote and installer platform for final device acceptance are
therefore untested. Hardware acceptance must cover normal Update all for both rooted editions,
service reactivation and root permissions, foreground/profile restoration, screensaver companion
behavior, software restart and physical cold boot, interruption at owned mutation boundaries,
and rollback/repair from the delivered signed artifact. A package readback or offline fixture
is not evidence of Home routing, sound, standby or physical remote behavior.

The permanent recovery ABI remains intentionally small: bootstrap catalog v1, generation and
migration receipt schema v1, the bounded engine entry interfaces, and the managed Python/Node
runtime constraints. Future engines may change product parsers, normal service implementation,
permissions and installed own package while preserving those recovery contracts. Replacing the
TV's runtime itself or changing the immutable recovery ABI is outside this baseline; unsupported
runtime requirements fail before installation.

## Final coordinator gate

The final independent review identified two recovery defects: terminal engine journal publication
could precede lease completion, and terminal engine-only status hid retained product rollback.
Both were corrected with regression tests and closed by independent code inspection.

Observed coordinator checks:

- System Updater Python suite: 184 passed before the final review fixes. After those fixes,
  the complete affected bootstrap and end-to-end flow modules passed all 15 tests. Unchanged
  modules were not rerun merely to recreate their evidence.
- Shared Root package identity, startup guard/hook, ownership and new engine identity: 65 passed.
- Computer System Updater preparation/replacement: 69 passed, including the bounded stdin
  cleanup transport and explicit one-time baseline replacement from System 1.2.10 to 1.2.11.
  The broken legacy transition remains excluded.
- Release/setup policy and signing preparation: 69 passed.
- Final Home/Helper/screensaver package compilation: 3 passed. Source-package assembly checks
  also passed all 5 tests after adding No-root Companion resources.
- All `tests/system_updates/*.cjs`, automatic release-signing tests and translation completeness
  passed. Catalog coverage includes 392 UI strings across thirteen TV languages.
- `git diff --check` passed. Changed JavaScript was formatted with the repository's pinned
  formatter; pre-commit formatting remains enabled.

These checks are focused development evidence, not full frozen-candidate CI or device
acceptance. No release was published, merged or dispatched, and no TV operation was performed.
The implementation selects one newest engine compatible with the retained recovery ABI;
it does not implement a multistep bridge graph or catalog expiry/revocation protocol.
Maintainers must preserve backward compatibility with the selected first baseline, retain
the stable catalog/trust path, and run final artifact/device acceptance before shipping.

## PR integration checks

[Draft PR #675](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/675) targets
`release/next` without changing the frozen candidate. Its first
[CI pass](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/43911840775)
exposed two integration defects on both Linux and macOS:

- Full clean removal captured a fixed component-journal list without the new engine
  journal. Its exact absence check consequently rejected profileless No-root cleanup.
  The snapshot now follows the canonical journal inventory. The affected lifecycle
  review also covers live engine/service entries and retained own-package staging.
- Generic package inspection temporarily changes the parser's application prefix.
  Companion admission incorrectly used that mutable value as parent authority while
  its default argument retained the original Home prefix. Admission now uses the
  two fixed Home application identities and still rejects foreign parents.

The original direct-candidate setup failure was reproduced before the Companion fix;
all 12 direct-candidate tests and all 10 package/screensaver-delivery tests passed
afterward. The original clean-removal failure was also reproduced before its fix.
All 111 tests in the affected `test_clean_removal.py` module then passed, including
new engine-journal/process, retained staging and foreign-package regressions.
The standalone test command needs `root-edition/runtime:root-edition/tests` in
`PYTHONPATH`; an initial run without the runtime path produced an import error,
not a product failure.

Review found that an old public installer stage can survive a successful installation
when unlink fails. After several self-updates its package may no longer appear in
the latest generation/migration receipt. Cleanup now checks the dedicated historical
engine cache with bounded file reads, exact hashes and own-package namespace checks,
then persists classified hashes before retiring cache bytes. This preserves retry
evidence without authorizing removal of a foreign package. The new regression was
observed failing before this correction and passing afterward.

Independent follow-up review closed the historical-stage finding and found no further
P1/P2 defects in the fix batch. The first CI pass completed its independent jobs:
runtime shards 1/4 on Linux and macOS, browser coverage, phone HEIC, optional Python,
frozen Windows/macOS Intel installer runtime and website build succeeded. Only the
two described causes failed runtime shards 2/3 and their aggregate gates. Unaffected
jobs and full release publication were skipped by normal routing.

The corrected product commit `8dd86a1c6b7a6d99a00ed9c3a516210e92595a86` passed
[Tests run 43915406758, attempt 2](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/43915406758):
all eight Linux/macOS runtime shards, both aggregate gates, browser coverage,
phone HEIC and optional Python checks succeeded. The frozen Windows/macOS Intel
installer runtime and website build also passed. Normal routing skipped unaffected
theme/weather jobs and full release publication.

The first attempt of that run could not obtain a hosted macOS ARM runner for shard 1.
GitHub cancelled it before any test step. After all other independent jobs finished
successfully, only that job and its dependent aggregate gates were retried. They passed;
successful test groups, release builds and TV operations were not manually repeated.
This final record changes documentation only and retains the matching code evidence.
These are host checks; hardware acceptance remains outstanding.
