# Simple Stop-aware activation implementation

Owner approved automatic Home On after setup and priority for new Stops;
subsequently explicitly removed legacy support and requested the simple design.
Spec: ../specs/2026-11-11-issue495-stop-aware-activation-design.md.

- [x] Native implementation: fixed stop-generation token in existing checked
  state contract; all C/JS Stop writers publish a fresh token. Helper setup start
  compares bound token across old-latch removal and startup; relay fences input
  against token change. Home On uses existing preference storage. No new broker.
- [x] Installer implementation: capture/bind baseline in new plan/capsule, launch
  with setup intent, retain unknown-request guards and truthful cancellation/
  startup/Home outcomes. Preserve lost-profile guidance and #498 separation.
- [x] Meaningful regression checks: real filesystem/Node/C races and interruption,
  source staging and all affected frontend/report/localization boundaries.
- [x] Rewrite stale kept-stopped docs/ledger/PR, independent final review, selected
  CI and issue status verification. Final product-source CI on 2ad3ada6 passed.

After saving and pushing this evidence, archive this managed temporary worktree.

Do not merge into frozen release inventory or change versions/build selection.
Do not contact a TV, publish another user's report or comment to the reporter.
