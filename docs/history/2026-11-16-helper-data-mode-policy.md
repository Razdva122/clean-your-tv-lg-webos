# Helper ordinary-data mode policy — development verification

## Scope and baseline

Prepared from `release/next` at `f442dd14774472b2f885a4b916625f9a38ae1d5e`.
This is a focused source PR, not a release candidate or a device installation.
Related historical reports: [#653](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/653)
and [#505](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/505).
The latest #653 report confirms its delivered upgrade/restart fix; this change
addresses the recurring storage policy rather than reopening that resolved report.

Developer Mode can expand retained rwx bits. Ordinary registered app/service
records and the catalog now remain readable without a per-file bootstrap repair
list. Home/startup consumers use bounded no-follow reads. Home checks preference
types; the startup claim still requires boolean true and a different boot identity.
Catalog verification retains expected hashes without requiring mode 0644.
Bounded logs survive mode-only changes. Credential privacy, installer key proof,
command channels, explicit Stop/watchdog, root authorization and native locks
retain their existing policy. Fresh writes still verify their intended modes.

Implementation details and extension rules are in
[Shared contracts](../development/SHARED-CONTRACTS.md#storage-and-ownership-handoff).
The unpublished screensaver implementation is outside this PR; ordinary new
records inherit the shared policy when registered, without a boot-repair entry.

## Selected verification ledger

The missing evidence was generalized ordinary-data admission after rwx expansion,
not another install of the existing release. Tests use real local inodes where
possible; UID/group fixtures project webOS identities without requiring host chown.

| ID | Selected case | Result |
| --- | --- | --- |
| MODE-01 | Storage contract, ordinary rwx variants including 0777, catalog hash mismatch, bounded data reads, symlink/hardlink and concurrent replacement refusal, credential/Stop exclusions | PASS: 24 tests on each of Node 23.11.0, 0.10.15, 0.10.25 and 0.12.2. Original source failed three new cases before the change. |
| MODE-02 | Home preference and actual service reader with real 0777 storage; off, invalid types, one launch per boot, Stop/watchdog | PASS: `tests/home-control.cjs`, `tests/helper-service-status.cjs`, `native/prototype/test-startup-storage.cjs`. Home invalid-type regression failed before validation was added. |
| MODE-03 | Packaged/runtime/Root SSH owner transitions and original key proof | PASS: `native/prototype/test-state-permissions-owners.cjs`. |
| MODE-04 | Installer observer, operation/recovery flows, Stop, data-directory selection and diagnostics | PASS: observer 24, operations 88, Helper Stop 10, storage selection 6, observer diagnostics 14. No-root integration: 53 of 55 cases passed initially; the two expanded-state upgrade/resume cases passed after restoring explicit-upload compatibility. The two affected observer cases were rerun and passed after that correction. |
| MODE-05 | Shared runtime dependencies, controller, command channels and input/emergency regressions | PASS: `scripts/test.sh --shard 2/4 tv-runtime`, with the same four Node runtimes; includes controller/channel/native safety checks and 319 Root Python cases. Its real Linux UID case is tracked separately as MODE-08. |
| MODE-06 | Compiled Helper/service compatibility and compiled watchdog/Stop tests | PASS: `tests/helper-compat.cjs` on the same four Node runtimes, rerun after the final Home validation change. |
| MODE-07 | Independent static review, formatting and whitespace checks | PASS: independent static review (including final upload boundary), targeted Prettier check and `git diff --check`. |
| MODE-08 | Real multi-UID Linux storage fixture | BLOCKED locally: requires Linux UID 0; development host is macOS and has no Docker runtime. The fixture remains in the Linux CI path; owner projection is not a substitute. |

No TV was changed for this PR. TV model, firmware/webOS, remote, installed
component versions and installer platform: not exercised/not applicable to this
source-only run. No Home-routing, power-cycle, update/rollback or screensaver
acceptance is claimed for a device or a final artifact.

## Reproduction and delivery

Use the project Python environment. Set `NODE010`, `NODE01025` and `NODE012` to
the exact runtimes above when repeating compatibility cases. The storage suite
runs with `python -m unittest discover -s tests/cytv -p test_storage_contract.py`;
the other named Python suites use the same discovery pattern.

Local initial failures in older tests expected catalog chmod or refusal for
ordinary writable data. Those assertions now retain the catalog inode/mode and
verify content; refusal coverage remains for special bits, links, foreign
ownership, hash mismatch and changed identities. No safety check was weakened to
turn an unrelated failure into a pass.

At release freeze, synchronize and rebuild Helper app/service and the desktop,
CLI and Android bundled storage resource. An unchanged Helper version can reuse
published bytes and does not deliver this fix. The release coordinator must bind
changed-package device acceptance to the selected final artifact. This PR does
not choose versions, publish packages or alter Root's privileged runtime policy.

The initial full integration run exposed two failures at the retained observer's
configuration upload. Restoring the existing catalog normalization only inside
explicit `prepareConfiguration(..., repair=true)` fixed both. This is intentional
write compatibility for immutable recovery sources; ordinary reads, read-only
verification and bootstrap do not repair catalog modes. Original observer and
capsule bytes are unchanged. Only the two affected integration/observer cases
were repeated; the other passing scenarios retain matching behavior evidence.

Exit reconciliation: 8 selected cases; 7 observed passes (including matching
unaffected results and the focused reruns), 1 concrete local platform blocker
(MODE-08), 0 approved deferrals and 0 independent untested local cases. Linux CI
and final artifact/device acceptance remain separate delivery gates. No device
acceptance follows from this completed local inventory.
