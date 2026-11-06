# Installer recovery implementation plan

Use subagent-driven-development with isolated parallel worktrees and one release
coordinator. This is the current practical-removal scope agreed with the maintainer;
the earlier expanded Helper/service lifecycle architecture is deferred. Spec:
`../specs/2026-11-06-installer-recovery-design.md`.

## Constraints

- Host Python3.9+, No-root TV Node0.10.15+, Root Node8+.
- Preserve original private profile/pin, first failure and foreign data; observation
  does not manufacture completion. Keep current errors separate from old causes.
- Helper0.7.4 stays byte-identical. No new Helper/service lifecycle protocol,
  shared UID/GID namespace or separate removal-disconnect recovery framework.
- User-facing removal is one desired-absence operation, retryable from current
  presence; stale pending/install success does not gate known-owned cleanup.
- Use one full boot checkpoint and fresh final cleanup/readback. An actually active
  external updater or package-manager busy/denied result stays an explicit blocker.
- No TV, public installation report or main publication. Release/next merge and
  versioned RC are authorized after review/verification. Follow release rules.
- Developer docs English; all13 user guides and active installer locales equivalent.

## Completed reviewed foundations

- [x] Task1: semantic authentication prompts across locales and Android.
- [x] Task2: bounded common assessment, original/current failure distinction and
  explicit supported recovery actions.
- [x] Task3: original Root continuation/cancellation and original connection binding.
- [x] Task4: original No-root installation-stream evidence and guarded continuation.
  Retain reviewed behavior; do not expand it into a new full-removal framework.

## Task7 — practical Root removal

Own Root/backend/state/CLI, separate from No-root and frontend files.

- [ ] Reuse the existing clean-removal intent and original Root/component locks;
  distinguish a genuinely active worker from a stale pending record.
- [ ] Restore owned controls and disable startup/jobs without requiring successful
  activation/setup. Preserve foreign Home and genuine inverse records.
- [ ] Remove registered project packages using the existing ordinary package API;
  skip absent objects, report actual busy/denied errors with retry/access guidance.
- [ ] Replace mandatory Helper/global lifecycle proofs with a saved full-boot
  checkpoint. Keep only the Root-private lock/Node utility genuinely needed to
  retire managed Python. Do not ship the deferred c205 removal-observer framework.
- [ ] Sweep known Root and No-root residues after the boot boundary. Reuse the
  No-root owner's small inventory/sweep export rather than duplicate its logic.
  Old source/terminal/success is not an eligibility gate for known owned files.
- [ ] Verify current absence before final success/Store.finish. Keep exact
  operation binding and truthful diagnostics, including unknown original causes.
- [ ] Add focused real filesystem/CLI orchestration tests for partial setup,
  missing files, retry, reboot, repeat removal and foreign preservation; commit,
  report and obtain independent review.

## Task8 — practical No-root removal

Own new `cytv/no_root_cleanup.py`, shared inventory/sweep runtime and dedicated tests.
Use the common `continue_removal(installer, expected_pending)` entry point.

- [ ] Bypass the old require_removal_idle/global status path for explicit removal.
  Read current registered project packages and known file paths.
- [ ] Stop owned control/startup through existing supported interfaces. Route all
  explicit Remove UI/CLI requests through this one full-clean path.
- [ ] Use ordinary package removal and direct owned-residue cleanup; absent is skip.
  Expose real busy/denied/connection errors. Request Root access for protected Root
  residue. Add a single inert registration carrier only where actually necessary.
- [ ] Persist actual boot ID/restart-required; after a full boot, re-inspect, sweep
  and verify. Finish only with removed and verified_clean both true. Current
  presence is rechecked even when an old completed receipt exists.
- [ ] Retry reconnects and continues this same goal from actual presence. Preserve
  original history without reconstructing or requiring original install success.
- [ ] Provide a small concrete inventory/sweep JS export for the Root owner. Leave
  Helper, renewal/updater lifecycle source and new global native architecture out.
- [ ] Test missing/partial package and data,359's denied-global-status shape,
  disconnect/retry, boot gate, Root permission handoff, repeat cleanup, foreign
  preservation and current-source old Node compatibility. Commit/report/review.

## Task5 — simple frontend integration and guides

Own Qt/GUI, Android bridge/UI, recovery wording, locales, guides and related tests.
Start from reviewed6416; backend providers work in their own branches.

- [ ] Connection interruption has clear wording and Try again. For already
  confirmed clean removal, retry the same target/goal without an extra recovery
  wizard; backend rechecks and skips completed work.
- [ ] Show restart-required instructions for a full power restart, then Try again.
  Pass exact removed/verified_clean/restart_required fields safely.
- [ ] Green uninstall requires clean-removal disposition and both success Booleans.
  Keep safe bounded reasons, original/current failures and semantic credentials.
- [ ] Update all13 locales/guides for the practical flow, preserve historical
  evidence and remove active instructions describing deferred lifecycle work.
- [ ] Test actual CLI/Store/Qt and Android bridge/browser partial/retry/restart/final
  journeys. Integrate both providers and obtain independent review.

## Task6 — integration and versioned release candidate

- [ ] Integrate reviewed Root/No-root/UI changes into one branch, reconcile latest
  issue/release evidence and preserve concurrent release/next scope.
- [ ] Complete combined verification and whole-branch review, fix findings, open a
  compact feature PR to release/next with accurate partial issue summaries and
  run actual PR CI. Merge with a merge commit under existing authorization.
- [ ] Reconcile issue statuses, collect/commit release inventory and update the
  candidate PR. Do not close unconfirmed reports or announce delivery from a merge.
- [ ] Select consistent versions/manifests/README/notes and finish documentation.
  Verify published baselines and exact unchanged Helper0.7.4 bytes. Complete all
  selected signing/prerequisites before one full candidate dispatch.
- [ ] Build/pin the final successful candidate attempt and verify artifacts. Report
  version/run/results and pending physical acceptance truthfully. Main stays
  unpublished. Preserve required reports and archive only this task's worktrees.
