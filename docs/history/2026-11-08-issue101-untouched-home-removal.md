# Never-activated Root removal without Home APIs — 2026-11-08

This is source verification for an implementation PR targeting `release/next`.
It is not a public release or an individual device recovery report.

## Change

A never-activated installation can now be removed without Settings Service or
System Profile readback. Previously, both the Python coordinator and final Node
cleanup required a readable `general.defaultApps` setting even when the original
operation had not applied routing.

The existing removal record must establish a lock-held pre-activation deploy
stage and no routing effects. Its retained inverse backup must exist and contain
no routing journal/backend. Current routing journals, native backends and the
CYTV profile override must also be absent. This proof is checked before every
destructive continuation, during Python final readback and in the final Node
process. A new journal after the restart checkpoint is preserved and blocks the
untouched path before cleanup. Unknown or previously activated routing retains
its existing restoration/readback requirements.

The existing `never-applied` routing record now supports a shape without `home`:
`{"mode":"never-applied"}`. This records absence of CYTV routing effects, not a
firmware routing value. Older readbacks may upgrade only with fresh no-effect
proof. Original failure evidence, ownership locks, package terminal/absence
proofs, full restart and private-runtime cleanup remain required. No new
permission, network endpoint or executable retained worker is introduced.

## Verification

The new coordinator and real Node-tail regressions failed before the correction.
Independent review reproduced a retry case that erased a newly appeared routing
journal before final proof; its integration regression also failed before the
pre-cleanup guard and passed afterward. Follow-up review found no remaining
important issue.

Using the configured host virtualenv:

- `PYTHONPATH=root-edition:root-edition/tests python -m unittest test_clean_removal test_simple_removal test_cleanup_tail_handoff test_update_luna -q`: 93 tests, two platform skips, no failures.
- `NODE8=/path/to/node8 PYTHONPATH=root-edition:root-edition/tests python -m unittest test_cleanup_tail -q`: 40 tests on actual Node 8.12.0, one Linux-only skip, no failures.
- `python -m unittest tests.cytv.test_simple_root_removal tests.cytv.test_clean_removal tests.cytv.test_root_clean_tail -q`: 12 host orchestration tests, no failures.

Tests use real temporary files, production removal logic and modeled vendor RPCs;
the macOS fd-path adapter does not prove Linux rename-race confinement. No TV was
contacted or changed. TV model, firmware/webOS, remote and physical Home, sound,
standby, cold boot, OTA/rollback and individual reporter recovery are untested.
This does not establish universal firmware compatibility or resolve the original
installation failure in issue #101. Final release-candidate validation remains
with the release coordinator; this PR does not change the selected candidate.
