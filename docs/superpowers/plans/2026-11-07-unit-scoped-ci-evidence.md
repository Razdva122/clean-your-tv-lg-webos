# Unit-scoped CI Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reuse authenticated successes for unchanged test units and finish the
replacement RC with final TV packages when green.

**Architecture:** Conservative per-unit Git projections, v2 receipts discoverable
by stable execution context, existing provenance/release gates unchanged.

**Tech Stack:** Python standard library, GitHub Actions, existing unittest/Node suites.

**Spec:** `docs/superpowers/specs/2026-11-07-unit-scoped-ci-evidence.md`.

## Global Constraints

- No package/build-input exemption or weakened required check.
- Unknown/shared/nonregular inputs invalidate all; setup retains full-tree binding.
- Preserve producer/artifact/run/job/merge/environment trust checks; full
  producers add exact origin/ref/source/full-marker and latest-job checks.
- No retrospective v1/full-run receipt promotion; first new-policy full run is fresh.
- One merged batch and one full candidate; no separate per-change PR CI wait.
- Finish the original case pass/failure inventory before correction implementation.
- Same model/reasoning for review agents; no external notifications or TV changes.

## Tasks

1. Close original run and failure inventory; inspect actual package hashes without
   selecting a failed build. Files: dated release record and current PR summary.
2. Write failing projection/discovery regressions in
   `tests/setup/test_ci_test_evidence.py`; implement the minimal audited projection
   in `scripts/ci-test-evidence.py` (or its one focused helper). Test owning,
   unrelated, shared, additions/deletions/modes, shards and all trust failures.
   Add authenticated full-candidate producers/consumers, latest-job failure
   suppression, cross-platform bounded API reads and distinct installer-host proof.
3. Correct `tests/cytv/test_long_ssh_commands.py` shell adapter and include it in
   `.github/workflows/cytv-runtime.yml` paths/commands. Retain assertions; prove
   Windows execution in the single full replacement; retain future PR coverage.
4. Update `docs/development/CI-CHECKS.md` and the dated RC record; independent
   review, focused checks and one reviewed correction PR to release/next.
5. Collect inventory, commit all final inputs and recheck Helper approval/source
   equivalence. Dispatch one replacement full candidate; diagnose any failure
   without claiming acceptance or redoing unchanged checks merely for records.
6. If green: pin exact run/attempt, verify final package hashes/equivalence, dispatch
   normal Root QA signing with publish=false (not preliminary), verify/download
   signed artifact and prepare the final supported host/TV QA package set. Update
   PR evidence and leave actual TV acceptance pending for the owner session.
