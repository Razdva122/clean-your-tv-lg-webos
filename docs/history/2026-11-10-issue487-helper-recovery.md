# No-root Helper power transitions and retained-key ownership — 2026-11-10

Related issue: [#487](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/487).
This is source/host verification, not a TV installation report or release
acceptance. The implementation stays on its own branch targeting `release/next`;
it does not change the frozen 1.16.0 inventory, version selection or artifacts.

## Changes and boundaries

- Authenticate an existing foreign-owned pairing key against the original
  capsule before restoring caller ownership through an atomic 0640 replacement.
  Both immutable observer sources, plans, capsules and package receipts stay
  unchanged. Ordinary read-only status and Root SSH do not repair files.
- Recognize only recently armed, confirmed evdev disappearance as exit 32;
  retain every cleanup step and preserve blocking for real I/O/close/output
  failures, Stop/triple Home and termination. Keep the controller alive for
  same-boot wake; require fresh settled Active, the existing settling delay and
  stop/latch guards before one new relay start. Preserve Home Off.
- Do not reinterpret the separate service `blocked`/`running` status discrepancy
  as repaired. No diagnostic availability or original device recovery is proven.

## Verification ledger

Host: macOS ARM64. Device model/firmware/webOS/remote: not tested by this task.
All files, identities, input events and service responses in regressions are
synthetic. No saved TV profile, private diagnostics or device connection is used.

| Changed input / missing evidence | Check and observed outcome |
| --- | --- |
| Foreign key owner with 0640/0775 | New regression first failed with unsafe-config-file, then passed; exact bytes retained, caller ownership restored and blocked untouched |
| Original pending continuation | Real detached observer/vendor-process regression passes: same capsule and operation, no repeated package submissions, configuration progresses while explicit stop still blocks launch |
| Wrong bytes, links, modes, unsafe companion and substitutions | Refused; no redirected private writes or replaced untrusted target; staging cleaned |
| Observer/continuation/operations dependencies | 131 tests passed with exact Node 0.10.15, 0.10.25 and 0.12.2 configured alongside current Node; later-added key/directory substitution test passed separately |
| Immutable observer compatibility | Both PROGRAM and ROOT_PROGRAM strings equal the branch-base bytes |
| Normal shutdown and same-boot wake | New C/controller tests first failed; affected controller matrix passes after fix, including fresh Active, duplicate events, Home wake and Home Off |
| Emergency and input cleanup boundaries | Actual relay harness covers EIO/close failures, no/expired/cancelled hints, Q+HUP and SIGTERM during cleanup; all existing cleanup attempts retained |
| Watcher lifetime | Independent review found premature controller exit; same-boot wake regression now verifies retained controller and a single new relay |
| Pre-READY power hint | Review found a missing startup hint; C startup-pump and controller regression now pass with the hint retained before READY |

Final affected checks passed: 80 source-controller cases and the same matrix
against compiled Helper output; 21 resume/Home cases; entry/service-status,
Home-control/bridge/jail, resume, controller Home/IR checks; all five native
filter/startup/relay/IR harnesses and four additional IR scenarios; 41 stop
filesystem cases. Compiled Helper runtime/WSS checks passed on current Node,
0.10.15, 0.10.25 and 0.12.2. After the last key-repair directory-stat refinement,
five affected permission/continuation tests passed again (the unrelated parts
of the 131-test run were not repeated). Python 3.9 grammar, Prettier and
whitespace checks pass. Final independent review has no blocking findings.

Checks are repeated only after
a changed affected input or a newly added regression; no full candidate build,
package signing, TV installation or rollback is selected by this work.

## Complete first CI inventory and one fixture correction batch

[PR CI 42800066196](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42800066196)
completed on 46fc5297 before another push. Browser, both phone HEIC jobs,
optional Python and six of eight runtime shards passed. The only underlying
failures were Linux shard 3's new continuation fixture and macOS shard 4's
unchanged Root guardian fixture; both aggregate summaries consequently failed.
No full release build ran.

- The Root fixture sent SIGSTOP immediately after ARMED, which is published
  while the real guardian still holds its state lock. A stopped lock owner
  prevents Restore from writing the stop latch within the test's 1.5-second
  wait. A temporary-source 2-second delay at that exact scheduling point
  deterministically reproduced the failure. The fixture now acquires the same
  flock before stopping, confirms the child is stopped with waitpid, then
  releases the lock. Acquisition/stop waits are bounded and failure cleanup
  resumes the child. Both freeze cases use this synchronization; production C,
  retirement deadlines and assertions remain unchanged. All 41 guardian cases
  pass, including the forced schedule.
- The Linux continuation fixture modeled foreign ownership by inode number.
  After atomic replacement that number could be recycled for unrelated private
  observer evidence, extending the synthetic UID to an unrelated file. The
  fixture now keeps its original key descriptor open until cleanup, preventing
  reuse. The affected continuation test passes locally; replacement Linux CI
  remains the required platform confirmation. Product ownership guards are
  unchanged.

Independent review found no actionable issue in this fixture-only correction.
Push this one batch after the complete first inventory; reuse unaffected source
and host results above. Updated-head CI must validate the changed fixtures. Do
not rebuild packages, sign artifacts, change a TV or weaken any acceptance gate
for these host failures.

## Remaining acceptance

A future release must select a new Helper version and build the native relay
and controller together. The published Helper 0.8.0 baseline remains immutable;
source edits alone do not deliver these changes. Rebuild embedding desktop/CLI
and Android payloads through normal release gates.

Final-artifact recovery and actual firmware errno/power event behavior remain
unverified. Physical Home/Back/other keys, audible sound, standby/wake, AC cold
boot, OTA and rollback are untested here. Startup validation failures still fail
closed; this is not a general retry mechanism for unavailable devices. The
separate service-status discrepancy remains unresolved. No universal model or
firmware compatibility is claimed. Existing saved connection/pending operation
and explicit emergency stop remain the recovery authority.

Developer references are updated. The practical controls and installation steps
in docs/i18n do not change, so no release notices or developer details are added
to those user guides. Issue #487 remains open for integration, publication and
exact-device acceptance; no shipping or closure is implied.
