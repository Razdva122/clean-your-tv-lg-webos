# No-root setup activation and lost-profile recovery (#495)

Date: 2026-11-11. Focused development ledger, draft PR #503.
Base: `3e04e8a583098c2728088b3d7c66a61786529068` (`release/next`).
Hold for the next release alongside separate [#498](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/498).
No frozen inventory, version, selected build or device operation is changed.

## Diagnosis and selected behavior

Local differential checks reproduce the reported repeated-setup UserError/pending
before launch when a blocked/watchdog latch is retained. This supports a likely
cause; the exact historical marker/error on the reporter's TV remains unproven.
No reporter diagnostics or installation report is republished here.

The owner selected automatic Home On after successful setup, with any new Stop
during setup taking priority, and explicitly requested a simple implementation
without legacy migration. Earlier kept-stopped behavior and the proposed private
Stop journal are superseded.

One checked `state/stop-generation` file carries I/S plus 32 random hex digits.
The installer binds the starting generation before package work. Helper and relay
compare it while activating Home and acquiring/forwarding input. Every permanent
Stop changes it, including consecutive Stops with identical latch text. Transient
watchdog recovery fences retain the generation; retry exhaustion publishes Stop.
Failed publication invalidates the generation while physical Stop cleanup still
runs. No history, broker, migration, new permission or endpoint is introduced.

Interrupted operations retain the same bound intent and never replay uncertain
package/launch requests. Packages, launch ACK, observed startup and physical Home
remain separate outcomes. A new Stop reports cancelled activation and skips the
Home test prompt. Lost-profile advice uses the original profile or separately
confirmed full verified removal, never blind deletion of the TV reservation.
Execute-only tmp removal is handled separately by #498.

## Verification and reuse

Host: macOS, project Python virtualenv, real temporary filesystem/Node/C fixtures;
vendor calls and all device data are synthetic. No TV was contacted. TV model,
firmware/webOS, remote, edition/component versions and physical Home, sound,
standby, cold boot, OTA, rollback and actual removal: untested.

- New cancellation, interrupted/closed recovery, invalid preflight, late release
  Stop and failed-first-publication regressions failed before their respective
  fixes. Native tests cover actual files, repeated Stop, latch-removal/grab races,
  failed publication and emergency key release/cleanup.
- Focused host checks before the final publication fallback: integration,
  operations, outcomes and observer diagnostics 136 passed; frontend/localization,
  desktop recovery/diagnostics and CLI 162 passed; source injection, settings and
  build contracts 24 passed. Root removal: 22 tests, one existing skip.
- An earlier removal/build/support/handoff run had 110 tests, one existing skip
  and one synthetic SDK GID mismatch. The fixture now models the temporary FD's
  group consistently; the failing case and changed Stop case passed. The initial
  failure is retained here rather than describing that run as wholly green.
- Independent static review found three defects: transient watchdog Stop tokens
  prevented recovery; invalid preflight left a capless pending record; a final
  sample before release missed a late Stop. All were fixed with affected
  regressions; follow-up review found no remaining actionable findings.
- Exact observer PROGRAM/ROOT_PROGRAM bytes remain unchanged. Existing matching
  observer evidence is reused. Python 3.9 grammar, all 13 guide anchor aliases and
  whitespace checks passed. User guides describe setup Home On, new Stop priority
  and safe lost-profile recovery without release/developer news.

Final publication-fallback checks and selected PR CI are recorded below when
observed. Host verification is not physical acceptance or reporter confirmation.
Keep #495 open and in progress while this draft remains unmerged. Do not announce
public delivery. Final release/device acceptance belongs to the next coordinator.

## Final focused batch

- Changed integration/operations/outcomes/removal suite: 200 passed. The final
  pre-package initialization-mode correction and invalid final-sample handling
  then passed four affected integration cases; the latter first failed by
  returning ordinary completion. A failed final sample now reports the existing
  startup-unverified error without claiming a proven Stop or offering Home QA.
- Real filesystem generation/setup checks and real C generation replacement pass.
  Native controller: 88 passed. C watchdog/generation races, IR and startup pass.
  Helper compatibility passes on Node 0.10.15, 0.10.25, 0.12.2 and current 23.11.0;
  these are supported TV runtimes, not legacy Stop migration support.
- Publication-failure cases cover existing/missing tokens, denied write admission,
  repeated Stops and entropy/temp allocation failures. Emergency release still
  delivers key-up, ungrab and close. Standalone removal attempts Stop and control
  publication even when token publication fails; both tested baseline forms pass.
- Final Python grammar/guide anchors and whitespace checks pass.
- Initial CI on be46b9fd had matching Linux/macOS shard3 Mock-truthiness failures;
  that branch now requires explicit Boolean true and the affected CLI test passed.
  Other initial units completed successfully. That older behavior is superseded;
  selected CI on the final source is required before declaring this batch ready.
- A new #495 comment reports Back/Exit routing improved after manual Helper Start;
  it supports activation work but is not acceptance of this unpublished fix.
  Linked #505 concerns inventory/icons and is outside this setup fix.

## Selected CI and compiler follow-up

Final-source run [42975065260](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42975065260)
on 92f6712f completed: seven runtime shards passed, Linux shard2 failed only
GCC `-Wmisleading-indentation` in the new C header. The two statements are now
on separate lines; the actual C generation test passes locally. No runtime logic
changed. Browser, both phone-HEIC jobs, optional Python, desktop frozen runtimes
on Windows/macOS, website build and release policy passed. Independent follow-up
review found no remaining actionable defects. The subsequent selected run must
verify the GCC correction; successful authenticated units remain reusable.

Final product-source run [42976707149](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42976707149)
on 2ad3ada6 passed all eight runtime shards, browser, optional Python and both
phone-HEIC jobs. Matching desktop frozen-runtime, website build and integration
policy checks also passed. No full release build/deploy was requested. The final
issue reread confirms #495 open with `bug` and exactly `status:in-progress`;
there are no new PR comments/reviews. Merge and physical acceptance remain with
the next release, alongside #498. This final evidence/plan edit changes no
product input; do not repeat device/build acceptance for the documentation alone.
