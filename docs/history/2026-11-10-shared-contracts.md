# Shared contracts: development verification, 2026-11-10

Scope: shared No-root storage, Helper lifecycle/power decisions, host recovery
advice and bounded standard-report context. Baseline `850c952b` is the separately
reviewed #488 work. This batch adds no version selection, permission, endpoint,
TV operation or release acceptance. The [current contract reference](../development/SHARED-CONTRACTS.md)
describes implemented APIs and boundaries; the [design](../superpowers/specs/2026-11-10-shared-contracts-design.md)
and [implementation plan](../superpowers/plans/2026-11-10-shared-contracts.md)
retain scope and integration work.

## Verification ledger and dependency closure

Results below are successful recorded development executions, reused where their
inputs still match. Counts describe commands and overlap; do not sum them into a
unique test total. Review corrections were followed by affected checks. A new
branch, review or documentation record does not justify repeating successful
execution. The prepared project Python environment and dependencies were reused.

| Source/dependency closure | Matching evidence and result | Limits |
| --- | --- | --- |
| Typed JS/Python events, hostile values/getters, repeats/floods, failed emitters | `tests.cytv.test_contract_events`: 12 initial parity/resource tests; final Task 5 adapter/event/Stop command: 34 passed. | Literal vectors and raw sources on configured runtimes; no TV. |
| `tv_sources`, CLI/desktop freezer declarations, Android staging/Gradle inputs, Helper app/service copies | Build-assets 10, desktop-package 4, setup-package 5 passed; final event tests assert source/frozen-selection/Android staged canonical bytes and missing-resource refusal. | Fixture packaging and staging, not signed release binaries. |
| Shared storage, observer external adapter, Stop and operation fallback | Role-cycle/storage regressions on four runtimes; observer 21 plus 2 corrected cases, integration 22 plus 4 corrected cases passed. Task 5 storage/report follow-up: 20 passed; final adapter/Stop coverage included in 34 above. | Real host inode/rename/staging with substituted UID/GID; outer proof readers unchanged. |
| Home/preference/channel consumers, renewal/service state, screen watcher | `home-control`, bridge, jail, renewal-diagnostics, updates/service and controller Home/IR/resume scenarios passed. Final Task 5 Home/IR/resume/screen-watch scenarios passed. | Consumer boundary doubles plus separate real-inode storage tests. |
| `native.js`, runtime/power policies and logger | Final `node --test tests/controller-watchdog.cjs tests/controller-resume-home.cjs`: 105 passed, no failures/skips. | Includes Stop, cleanup/restart races, limits, exit 25/32, firmware processing and emitter failure. |
| Compiled Helper/runtime dependency closure | Final `node tests/helper-compat.cjs`: current Node 23.11.0 and exact 0.10.15 / 0.10.25 / 0.12.2 passed, including compiled watchdog/Stop cases. | Babel/ES5 and real module/controller execution on host; no retail TV compatibility claim. |
| Native T/R command change, input release | C filter/startup/relay-startup/relay-watchdog/IR harnesses compiled with `cc -std=c99 -Wall -Wextra -Werror` and passed, including expected IR emergency exit 27. | Synthetic evdev/ioctl/pipe conditions, not physical remote/power behavior. |
| Recovery assessment/projection, CLI/Qt/Android choices, proof consumers | 265 affected state/journey/UI/diagnostic checks passed; final contradiction/uninstall correction: 52 passed. | Real local Store/frontends with simulated backend/TV evidence; Qt enabled. |
| Transport, operation context, history, first failure, standard report | Task 5 broad affected command: 122 passed; final retained event count/timestamp regression plus context: 48 passed. | Fixed-envelope validation, original Root driver errors, privacy/bounds and cross-operation retention; no new backend admission. |
| Desktop Save / Android report-ready | Task 5 report/desktop-recovery/Android bridge: 61 passed with real Qt enabled. | Local generated report handoff; no signed APK or desktop release execution. |

Exact Python commands used `python -m unittest` with the module names above;
full module lists for the larger command groups follow:

- 122: `tests.cytv.test_contract_report`, `test_contract_events`,
  `test_storage_contract`, `test_diagnostic_context`, `test_diagnostics`,
  `test_transport`, `test_root_driver_failure`, `test_helper_stop` (all under
  `tests.cytv`).
- 52: `tests.cytv.test_recovery_actions`, `test_recovery_state`, `test_recovery`,
  `test_product_recovery`, `test_activation_recovery` (all under `tests.cytv`).
- 48: `tests.cytv.test_contract_report tests.cytv.test_diagnostic_context`.
- 61: `tests.cytv.test_contract_report tests.cytv.test_desktop_recovery android.tests.test_bridge`.
- 34: `tests.cytv.test_contract_report tests.cytv.test_contract_events tests.cytv.test_helper_stop`.

Final source inspection mapped every changed production dependency to these
checks. Storage-only diagnostic changes did not alter independent Home/renewal
consumer admission; the final compiled Helper and storage/report runs cover the
changed boundary. Later report-allocation changes affect only local export and
are covered by the final 48 checks. No uncovered product consumer or observed
product failure remains in this ledger. Independent whole-branch review and
selected PR CI are still integration work.

## Final integrity checks

Missing evidence was identified before each additional check: immutable observer
identity at combined inputs, and direct raw-source ES5 compatibility after final
logger changes. Both checks completed with exit 0 on 2026-11-10.

AST evaluation of only `PROGRAM` / `ROOT_PROGRAM` assignments compared exact
strings in `cytv/no_root_observer.py` against baseline `850c952b`:

| Immutable observer | SHA256, unchanged |
| --- | --- |
| `PROGRAM` | `e40dd1efa2a125b97223f03cb543603249b00defa005cca003448e784981359a` |
| `ROOT_PROGRAM` | `d2aaf53952b0b0be2c3aec324a8c7e1e3d36c11960355afe8d02afe19934e080` |

Acorn `ecmaVersion: 5` parsed final raw `contract-events`, `state-permissions`,
`runtime-policy` and `power-policy` successfully. Matching staged-byte/resource
checks above were reused; no full build, signing run, full RC suite or TV install
was repeated. Final documentation links/privacy and `git diff --check` are checked
before committing this record.

## Corrections and known limits

Independent task reviews found and corrected changing-getter projection,
accepted legacy directory follow-up writes, contradictory product setup advice,
and retained diagnostic counts crossing operation boundaries. Each has a focused
regression. Harness-only corrections included fixture dispatch/import paths and
storage boundary doubles; no safety assertion was relaxed. Qt's existing missing
Sans Serif alias warning remains an environment limitation, not a recovery result.

Edition coverage: No-root Helper and shared installer advice/reporting; Root
historical programs and protocol proof readers remain unchanged. Installer host:
macOS with real Qt and Android adapter fixtures. TV model, firmware/webOS, remote,
installed component versions and device outcomes: untested for this batch.
Home routing, sound, standby, cold boot, OTA and rollback: untested. Old Helper
telemetry and unwritable/unsafe logs cannot reconstruct discarded failures.

No user setup/control steps changed, so practical guides and `docs/i18n` were
left unchanged. Release integration, selected CI, exact rebuilt artifact checks,
issue status reconciliation and scoped physical acceptance remain with the
coordinator. This ledger does not announce delivery or claim the retrospective's
issues are fixed.

## Consolidated selected-CI corrections

After the complete selected PR #493 pass finished on baseline `9beea1ee`, its
failure inventory identified five owned causes: missing removal-recheck text in
all twelve non-English runtime catalogs, an outdated real-file ownership fixture,
optional telemetry running before locally inadmissible observer proof, and stale
status/Stop expectations. These corrections were applied as one batch. The
independent Root stock UID fixture collision is handled by upstream PR #494;
that integration and selected-CI verification remain with the release coordinator.

The ownership fixture now resolves the host temporary-directory alias and models
pinned-session cwd, relative paths and descriptor metadata consistently. Canonical
event validation runs in the storage module's VM realm, and screen-watch uses the
real checked configuration reader. All existing privacy, owner/group/mode,
read/write/rename failure, concurrent update, control, Back and power assertions
remain active. The legacy warning assertion checks the current typed metadata,
retained decision, directory field, UID/GID and unchanged directory mode. The
existing legacy-directory warning lacked its real field and metadata; a narrow
diagnostic correction now uses the existing directory vocabulary and stat context
without changing admission or Stop behavior.

Observer status validates its original local proof before optional telemetry.
The invalid legacy capsule regression confirms no SSH command, unchanged receipt
and capsule, explicit removal consent and a purely local diagnostic export.
Partial/corrupt receipt coverage permits only the exact trusted read-only log
projection with no stdin and its ten-second timeout; receipts remain unchanged
and completion is not inferred. Root ordering coverage requires the exact trusted
Stop program bytes and bounded quiescence command before enable.

Focused verification on macOS with the prepared project Python environment:

- 83 passed: i18n; the legacy-capsule regression; partial/stale/corrupt status;
  Stop-before-enable; contract report; Helper Stop; diagnostic context.
- 3 passed: pending original install despite matching versions/hashes;
  source-shaped terminal not replacing original proof; uncertain receipt admission.
- 27 real-file ownership fixture cases passed unprivileged.
- After the diagnostic correction: 31 storage/report/Stop tests passed, with
  storage checked on current Node and exact 0.10.15, 0.10.25 and 0.12.2 runtimes;
  all 27 owner cases and the three exact status/Stop/legacy-capsule cases passed
  again. Raw storage ES5 parse, focused Prettier and `git diff --check` passed.

Prior selected CI supplies the matching failing evidence; giant assertion dumps
were not repeated. Only storage diagnostic metadata changes in production JavaScript. Immutable
observer programs, capsules, Root backend, control decisions and emergency latches
are unchanged; focused storage/direct legacy evidence covers the changed source. No full suite, compiled Helper, C, release build,
signing or TV operation was repeated. Linux execution and the new selected-CI
pass remain integration evidence, not claimed here. Device fields and acceptance
limits remain as stated above; this is development evidence, not delivery.

## Remaining ordered fixture closure

The next selected CI pass reached the basic ownership fixture and the separate
Linux root multi-UID gate. Their failures were fixture assumptions: a macOS
temporary-path alias, an obsolete expectation that runtime chmods `apps.json`,
and staging the storage module without its canonical event dependency.

The basic fixture now uses the resolved directory and checks that `apps.json`
retains its original mode/content. Its final permission-denial case resets the
previous directory-shaped key to a valid file, loads actual builtins and
same-realm canonical events, and verifies real directory/key/staging chmod
attempts, typed retained/refused outcomes, unchanged key inode/owner/content/mode
and removal of staging files. Existing missing-file, unsafe path/type and privacy
checks remain. The Linux fixture stages both canonical files and retains all
real multi-UID, group, SGID, reconfiguration and Stop latch assertions.

Focused macOS results: basic fixture passed; all 27 modeled owner cases passed;
Prettier and whitespace checks passed. The real Linux root gate remains required
CI evidence; no macOS skip is counted as a pass. The remaining ordered prototype
suffix is `test-stop-io.cjs`, then `test-stop-journal.cjs`; their independent source,
compiler and fixture inputs are unchanged, so matching prior Stop/C evidence is
reused. No product source, dependency, version or TV state changed in this followup.


## Root SSH group access and Linux fixture cwd

Before merge, a real-inode role regression showed that UID0/GID0/groups[0]
was refused by canonical Stop for packaged UID5999/GID5000/mode0770 storage.
The normal successful-disable path previously wrote Stop with a privileged
shell; consolidation introduced runtime group-membership admission there.
A disable reply can precede controller exit, so this is a reachable Root path.

Canonical sessions now use one captured UID0-or-group-membership predicate for
group access. Trusted owners, same configuration/directory group, exact original
foreign-key hash, safe modes/types/single links, no-follow descriptors, inode
checks and verified staging syscalls remain required. No caller-supplied Root
role was added. Unprivileged callers cannot forge group access. Host regression
coverage preserves emergency latch/watchdog bytes, refuses unsafe link/type/path
destinations and wrong-group/wrong-hash foreign configuration, accepts exact-hash
reclamation and verifies failed Root staging chown preserves the destination and
removes staging. Actual Root permissions are tested separately on Linux.

The complete selected CI pass on the preceding head reached the Linux root
fixture's first dropped-UID call and returned an opaque failure. The fixture
inherited the checkout cwd despite its intended independence from checkout
permissions. A bounded host probe confirmed that canonical preparation returns
false if restoration to the inherited cwd gets EACCES, while a traversable temp
cwd succeeds. The runner's actual permission cause remains unproven pending CI.
Child processes now start in the already traversable fixture root before UID
drop; prepare calls emit bounded canonical contract events on failure. Production
cwd handling is unchanged. The Linux fixture retains all previous UID/group,
SGID, ownership, reconfiguration, denied-write and controller Stop assertions,
and adds actual UID0/GID0/groups[0] Stop with both an existing and missing latch,
verified output group/mode/ownership and a controller write under another UID.

Focused macOS development evidence after the change:

- 32 storage/report/Stop tests passed; storage cases ran on current Node and exact
  Node 0.10.15, 0.10.25 and 0.12.2. The new role regression failed at the intended
  shared-group gate on all four runtimes before the source change.
- Basic permissions fixture and all 27 modeled owner cases passed.
- Three focused Root ordering, partial-receipt and removal-admission tests passed.
- Raw ES5 parsing, Linux fixture syntax, focused Prettier and whitespace checks passed.

The actual Linux root gate remains required CI evidence and was not executed on
macOS. No Linux skip, host test or installed package is physical TV acceptance.
No TV, firmware, remote or installer-platform device run was performed. Immutable
Root observer programs/capsules, backend receipts and stopped-Helper proof remain
unchanged. No full suite, C/compiled Helper run, RC build or TV operation was
repeated for this focused fix.

## Packaged key reader trust and repair authority

The follow-up role matrix found that a packaged-owner key expanded to 0775 was
trusted for reading but refused even when the installer supplied its exact
original hash. Trusted read ownership did not make that noncaller inode safe to
chmod in place. Installer configuration now routes a noncaller key with other
permission bits through the existing authenticated replacement branch. Its exact
SHA256, allowed modes and same-directory group checks remain unchanged; a caller's
own 0775 key still repairs in place. Private packaged keys retain their original
inode, owner and mode, including the existing accepted 0600/0640/0660 cases.

For both Root UID0/groups[0] and an ordinary caller sharing group5000, the new
host inode matrix failed the intended valid-hash replacement on current Node
and exact 0.10.15, 0.10.25 and 0.12.2 before the fix (eight failures). After the
minimal branch change, all 33 storage/report/Stop tests passed. Final explicit
0600/0660 preservation and caller-owned in-place assertions passed in the same
matrix on all four runtimes. Read-only expanded-key inspection, missing/wrong
hash, mismatched group and foreign apps ownership refuse before mutation; exact
hash replacement produces a new caller-owned 0640/group5000 inode and retains
key bytes, apps inode and emergency/watchdog state. No new ownership literal,
mode allowance or proof exemption was added. Actual Linux root CI and physical
TV acceptance remain outside this macOS development evidence.


## Integration into the next candidate

Both implementation PRs are merged into `release/next` and collected in the
unfrozen [next candidate #491](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/491):

- [#488](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/488), selected head
  `013745ecaa6d963571c9c672b1d3bf5c031b7483`, merge `dcc73292`;
  [selected CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42834780004)
  passed.
- [#493](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/493), selected head
  `81afb4e47963c9530b93ae70138de3b69b4544f6`, merge `612d981d`;
  [selected CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42849562325)
  passed all eight Linux/macOS runtime shards, ARM Python, browser and HEIC
  checks. The required Linux real UID/GID ownership step executed successfully,
  including UID0 without shared-group membership; it was not skipped.
  All 24 attached PR gates passed or had their intended skip disposition,
  including frozen Windows/Intel macOS installer runtime and preview checks.

Independent whole-branch and subsequent integration/role reviews found no
remaining blocking findings. The final package-owner correction had eight
expected RED role/runtime cases, followed by 33 affected storage/report/Stop
checks passing; the last mode-preservation matrix then passed eight executions
on current Node and exact 0.10.15, 0.10.25 and 0.12.2. Unchanged dependency checks
above were reused rather than repeated.

The committed inventory preserves #492 and #494. No version was selected,
no candidate build was pinned and no physical acceptance was claimed. These
changes require rebuilding the common computer/Android installer resources and
matching Helper/support sources when the release coordinator freezes the next
candidate. Practical localized setup/control steps are unchanged; developer
contracts, diagnostics and this evidence record contain the implementation
changes. The existing Qt font-alias warning remains a host-environment follow-up.

Issue #487 remains open at `status:awaiting-release`: ordinary public delivery
is pending, and the reporter's continuation, standby and wake scenarios remain
unverified. No TV was contacted during this development task; source CI is not
final artifact acceptance or universal device compatibility evidence.
