# Practical clean removal source checkpoint — 2026-11-06

This is unpublished source verification, not final release-candidate or device
acceptance. The maintainer chose a bounded remover: stop owned controls/startup,
remove registered packages and known present files, require a real full restart,
then sweep and verify absence. Missing items are skipped, including after partial
installation. A connection loss offers **Try again** on the same approved goal.
Actual busy work, access denial and unsafe foreign paths remain visible blockers.

If an old controller or resident installer can still act, the restart checkpoint
comes before final package/file removal. Standby and Quick Start do not satisfy
the kernel boot-ID check. CYTV never reboots the TV automatically. Final UI success
requires `clean-removal` disposition, exact `removed:true` and
`verified_clean:true`, and no semantic restart signal. Old unknown installation
outcomes remain unknown; current absence does not invent their cause.

The published Helper remains **0.7.4**. No new Helper/service lifecycle protocol,
shared UID/generation machinery or separate removal-observer framework is included.
Root retains its existing locks and narrow support needed to retire managed
Python safely. Minimal non-executable removal records or genuine ownership backups
may remain; product credentials, configuration and owned runtime/staging data are
cleanup targets. Original computer reports and saved connection keys are retained.

## Checked source and results

These are separate executions, not one aggregate run. Independent scoped reviews
accepted the Root, No-root and UI fixes below. Later combined changes still need
their own validation.

| Checked source | Actual verification | Scope and limitations |
| --- | --- | --- |
| Root `9f51910c` | 61 removal tests: 58 passed, 3 Linux-only skips; separately 12 binding tests passed | First production handoff without a preseeded cleanup inventory removes a damaged unused managed runtime through actual Node 8. The interpreter actually executing from a managed slot still receives full integrity authentication, including symlinked executables. Temporary filesystems and modeled process/RPC state are not physical TV acceptance. |
| No-root `e79dfae5` | 29 practical-removal and 5 carrier tests passed; 8 affected tests passed separately on Node 0.10.15, 0.10.25, 0.12.2 and 8.12.0 | Permission cases exercise production emitted JS and real temporary POSIX permissions. Normal package removal, or one inert same-ID carrier when SAM is missing, retires exact owned No-root data; Root-edition markers still require Root access. Privileged package-manager replies and filesystem retirement are modeled. Legacy Helper state mode 0777 is handled with no-follow inode checks. |
| UI `28530a18` | 31 targeted Python tests and 12 Chrome result presentations passed after reproducing the failures | Semantic restart signals override stale completion flags; malformed removal data stays neutral; Home-off completion remains separate. This does not prove backend deletion or Android APK acceptance. |
| Combined host `c419a3a8` | 72 tests passed in 2.709 seconds | Real CLI/Store/Qt orchestration and Android bridge with modeled SSH/device replies. Includes the previously failing same-goal retry/second-confirmation regression. |
| Recovery result producer `a827d1df` | 49 focused tests passed in 2.413 seconds | Proven removal completion now carries both required success flags through recovery continuation. Independent scoped review approved the producer contract and its negative cases. |

Root's initial combined test invocation exposed a test-order limitation:
`test_python_binding` leaves a runtime import path in-process, causing later
removal fixtures to import the wrong `provision` module. The two affected groups
passed in separate processes; the limitation was not hidden or fixed by changing
runtime security checks.

Reproduce the focused source checks from the repository root with the declared
development dependencies and configured exact Node runtimes:

```sh
PYTHONPATH=root-edition:root-edition/tests NODE8=/path/to/node8 python3 -m unittest test_cleanup_tail test_cleanup_tail_handoff test_clean_removal test_simple_removal
PYTHONPATH=root-edition:root-edition/tests python3 -m unittest test_python_binding
python3 -m unittest discover -s tests/cytv -p test_no_root_simple_removal.py -v
python3 -m unittest discover -s tests/cytv -p test_no_root_carrier.py -v
NODE_EXEC=/path/to/exact-node python3 -m unittest discover -s tests/cytv -p test_no_root_simple_removal.py -k protected_no_root -k legacy_writable_helper -k legacy_state_symlink -k known_root -k disconnect_after_carrier -k rejected_carrier -k shared_container_exception -k directory_replacement -v
LANG=en_US.UTF-8 QT_QPA_PLATFORM=offscreen QT_LOGGING_RULES=qt.qpa.fonts=false NODE8=/path/to/node8 python3 -m unittest tests.cytv.test_simple_root_removal tests.cytv.test_clean_removal tests.cytv.test_clean_removal_cli tests.cytv.test_root_clean_tail tests.cytv.test_simple_removal_ui tests.cytv.test_desktop_recovery tests.cytv.test_recovery_ui android.tests.test_bridge
node android/tests/restart-result.cjs
```

The 72-case command above is its recorded combined subset, not the full installer
suite. The initial 966-case cytv run completed with 102 failed subcases, four
errors and two skips. Ninety-six subcases were missing translations for three
No-root messages. The remaining failures were old removal fixtures and macOS
path-alias comparison. The corrected five modules passed all 74 tests at
`aad6b110`; production guards were retained. The Homebrew continuation fixture
separately passed six tests with authenticated original snapshots. Independent
reviews approved those corrections. No unchanged successful tests were relabeled
as fresh executions.

The complete Android Python suite passed 43 tests; Chrome simple removal covered
all 13 locales and both editions, and 12 restart/malformed-result presentations
passed. Three new first-handoff regressions also passed on actual Linux ARM64/
Node 8 in a disposable read-only, network-disabled container, with input hashes
unchanged. The complete Root run and actual PR checks were still pending at this
checkpoint; these focused results do not establish their success.
[Maintained matrix](../development/INSTALLER-RECOVERY-MATRIX.md).

## Documentation and remaining acceptance

The desktop, CLI, Android and Root removal references distinguish the candidate
flow from published retention/recovery rules. All 13 localized installation
guides describe present-item cleanup, full power restart and same-goal Retry;
published download buttons remain separate from candidate source instructions.
There is no native-speaker acceptance claim.

No TV operation was performed for this source checkpoint. TV model, firmware,
webOS and remote are unknown/untested here. Package-manager admission, physical
Home/navigation, sound, standby, cold boot, OTA and rollback were not tested.
No outcome on another user's device or original issue cause is asserted.

Remaining work: resolve the broader-run failures, complete final combined review,
merge the reviewed implementation into `release/next`, collect scope and finalize
versions/documentation, then build and pin the complete versioned candidate.
Affected exact-artifact and physical acceptance remain separate. A successful
package build or source test cannot establish a clean TV or universal compatibility.

## Combined Root and OTA delivery correction

The full Root run completed 1,219 tests with 24 failures, one setup error and three
skips before the final corrections. Sixteen failures came from the test loader
binding the runtime `provision` module where a coordinator fixture needed its own
module. After collecting all 1,222 tests, the isolated fixture rerun passed 61
cases with one Linux-only skip; the prior module identity was restored. The lab
setup error used an undeclared child Python without fontTools; with the declared
build environment, all three lab cases passed. Neither correction weakened a
runtime check.

The other failures exposed a real packaging regression: five new cleanup/cancel
files extended the fixed infrastructure paths accepted by installed supervisors.
At `849ac605`, these files remain hash-authenticated in the current installer
bundle/staging, while persistent Root Updater code, receipts and the System OTA
archive retain the exact published path set. Apply/resume share that precise
projection and preserve the complete original staged bundle proof. Ordinary TV
OTA/rollback does not require the five helpers. No supervisor migration, new
loader or change to the immutable published-supervisor fixture was introduced.

Fresh checks passed: the unchanged legacy archive contract (2), actual bootstrap
and metadata resume (3), immutable rollback anchors (7), legacy update/rollback
lifecycle (3), packaging (5), and actual packaged Node compatibility on 0.12.2,
8.12.0 and current Node. Independent scoped review approved the delivery correction.
The original CI failure and its correction belong to
[implementation PR #363](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/363);
only its final successful revision can authorize integration. These are host/source
checks, not physical OTA or removal acceptance.

## Linux support utility portability

The next PR CI revision found strict GCC sign-comparison/indentation diagnostics
and a macOS-only temporary test path. At `fee4d5eb`, filesystem mode parameters
use `mode_t`, unconditional statements are separated, and the fixture uses a
resolved platform temporary directory. No flags, permissions or gate semantics
were relaxed. Actual native gate/Root fence checks passed 12 cases on Linux and
12 on macOS. Strict Zig 0.14.1 ARM compilation produced a static ELF32 EABI5
without interpreter/dynamic headers: 39,740 bytes, SHA256
`c943cd280ffb6a1972d7235520aa237c9bd4efcc96ed88fa397b6601247cd275`.
This changes installer support inputs; the final candidate must use this corrected
source. Published Helper bytes remain unchanged; prior binary evidence retains
its original scope. Independent scoped review approved the portability correction.
