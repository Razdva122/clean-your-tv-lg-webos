# Installer failure recovery and removal completion — 2026-11-07

Source/model verification for the next, unfrozen candidate after v1.10.0.
No TV was contacted, changed or used for acceptance. No reporter installation
result is published by this record.

## Resulting behavior

- Failed Root setup offers recovery using the original saved connection. Desktop
  and Android expose that action directly; Android does not reopen connection
  editing for an already bound recovery action.
- No-root cleanup retains an actual Root-access blocker and offers **Connect
  using Root**. Normal Root authentication and host-key trust remain required.
  Fresh, fully verified Root removal also completes unchanged, blocked No-root
  removal goals for the same host; their original intent IDs/history remain.
- Failed or uninspectable original No-root setup offers separately confirmed
  full cleanup, independently of its old package outcome. Declining preserves
  the original receipt. No uncertain original install request is repeated.
- Failed normal Root/C1 activation attempts ownership-checked LG Home restoration
  and verifies the inactive/stock proof. A failed compensation remains pending,
  including across status checks, until recovery verifies LG Home. The original
  error and stage remain separate from the compensation outcome.
- Cancellation with pending work exports a redacted report and offers recovery
  or the existing cleanup continuation. It does not claim that accepted TV work
  was cancelled. Cancellation before setup changes creates no recovery goal.

Cleanup retries transient connection loss or a busy CYTV worker at most three
times, re-reading current presence under the same approved intent. Reconnects
retain the saved SSH pin; credential/host-key failures are not automatically
retried. Full restart remains a physical user action with actual boot proof.
Known absent packages are skipped and unknown installation requests are never
replayed. A lost cleanup-carrier install response with no current registration
requires Root access rather than a second uncertain carrier install.

The existing private receipt gains fixed `activation_restore_pending` and
`activation_restore` fields, per-app `cleanup_carriers` submission dispositions,
and a `root_removal_operation` link when Root proves a blocked No-root goal clean.
Diagnostics expose only the fixed LG Home compensation result and retry flag,
alongside the separately preserved original failure. There is no new permission,
endpoint, TV lifecycle coordinator or emergency-stop reset. Host and Android
installers need rebuilding; no Helper behavior or package baseline changes here.

## Verification

- New regression cases reproduced the five original stops before implementation.
  Further regressions reproduced uncertain carrier replay and premature status
  reconciliation before their corrections. A final cancellation regression
  prevents a closed credential prompt from being retried as transport loss.
  The final 21 new cases pass.
- Complete host installer discovery ran 1,015 tests with two platform skips;
  its 15 errors were sandbox denials of loopback socket binding, with no product
  assertion failures. All 33 tests in those SSH/TLS/HTTP modules subsequently
  passed outside that sandbox restriction.
- Final affected operations, original-stream recovery, removal, normal/C1
  activation and real Qt journeys: 268 tests passed. Final diagnostics,
  localization and Android bridge checks: 101 tests passed. These overlap the
  complete run and must not be added as independent coverage counts.
- Real CLI/Store/Android events passed headless Chrome journeys for failure,
  cancellation/report availability, direct recovery and Root-removal handoff.
  The browser regression is included in the browser-core CI unit.
- Independent review reproduced both additional edge cases, reviewed the fixes
  and reported no remaining Critical/Important findings. Formatting and PR CI
  results are recorded in the implementation PR.

[PR #377](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/377) merged
into `release/next` as `186eb42586ba9c992b5e38a993226f644219aa87` after
[combined-head CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42358921172)
and both frozen desktop runtime checks passed. A further 55 recovery/native
checks passed on the resulting candidate including the neighboring #379/#380
changes. This is implementation integration, not frozen release acceptance.

TV model, firmware/webOS and remote are untested for this change. Physical Home,
key-up/emergency behavior, audio, standby, cold boot, OTA and rollback must not be
inferred from these source checks. Candidate build selection, version bumps,
package/feed verification and affected device acceptance remain the release
coordinator's work under `docs/RELEASE-FLOW.md`.
