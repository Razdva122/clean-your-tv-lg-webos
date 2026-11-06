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
| Recovery result producer `a827d1df` | 49 focused tests passed in 2.413 seconds | Proven removal completion now carries both required success flags through recovery continuation. Independent review was still running at this documentation checkpoint. |

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
suite. The initial broader installer/Android execution failed a Homebrew continuation
fixture and final cleanup-result propagation. The producer fix has the focused
result above; the corrected continuation fixture has a separate focused check.
The broader installer run still has failures under diagnosis. Do not
describe the full suite, the final candidate or all user flows as
passing from these focused results. [Maintained matrix](../development/INSTALLER-RECOVERY-MATRIX.md).

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
