# Post-RC recovery reliability implementation plan

> **For agentic workers:** Use `subagent-driven-development` with the user's explicitly requested parallel work. Every implementation and review agent uses **gpt-6.1-sol / medium**; do not escalate model or reasoning without new user permission.

**Goal:** Implement the remaining reliability improvements after reconciling v1.20.4 RC, without changing or merging into its frozen branch.

**Architecture:** Keep existing journals, guards and recovery commands. Isolate optional Home startup failures; add an advisory recovery-action policy consumed by the current frontends; expose existing maintenance operations without package reinstall. All mutation remains in current authenticated backend flows.

**Tech stack:** Python/PySide desktop and CLI, JavaScript Home and Android UI, existing unittest/Node/browser runners.

**Spec:** `2026-11-13-update-removal-reliability.md` in this directory, especially its current-candidate reconciliation. The user explicitly authorized implementation and parallel development after the RC check.

## Global constraints and base

- Base: RC #606 commit `58ceffd04ba3596f65f309b5ddb04e5ad68e5c4e`. Work on separate `codex/` branches; do not alter release/next, release versions, feeds, signing or publication.
- #607/#611/#613/#614 already implement No-root continuation, staging checks and native Home/reinstall fixes. Do not duplicate these changes.
- Preserve identity/pinning, package terminal proof, writer fencing, final readback, explicit Stop, watchdog and triple Home. Advice never authorizes mutation.
- Retained classified temporary IPKs are permitted by RC; do not convert their warning into an uninstall failure.
- No live TV actions, external notifications or GitHub comments. This phase is local development, review and validation. Preserve other chats' worktrees.
- Use TDD for changed behavior: reproduce the failure first, run the focused red test, implement, run covering tests and review. Record exact commands/results and environmental blockers.
- Read AGENTS.md and CONTRIBUTING.md in each checkout. npm ci precedes JS checks. Reuse a prepared Python virtualenv; use sys.executable for host children.
- Localize new user-facing strings across existing supported languages. Technical docs remain English; no release news in practical guides.
- No large architecture rewrite, new dependencies or telemetry. No automatic operation retries added by UI. No package removal merely to access settings.
- User approval for parallel agents overrides the skill's default sequential implementer rule; isolated worktrees and file ownership prevent conflicts. All agents use gpt-6.1-sol / medium, including review.

## Workspace and execution ownership

Integration: managed worktree `recovery-reliability`, branch `codex/recovery-reliability`.

Parallel workers:

1. `reliability-home-startup`: Task 1, Home JS and readiness tests only.
2. `reliability-retry`: Task 2, Python recovery decision/bridge contract and its tests only. No GUI/CLI/Android JS edits.
3. `reliability-rollback`: Task 3, desktop/CLI maintenance entry points and their tests. No recovery_ui.py/recovery.py or Android JS edits.

Task 4 frontend integration consumes Tasks 2 and 3 sequentially. Task 5 validates their composition and records any missing historical cases. Independent task reviewers run as slots become available, followed by one final combined review.

## Task 1: Isolate optional Home startup failure

**Files:** `launcher/app.js`, `launcher/weather.js` only if necessary; `launcher/profile-bootstrap.js` and `root-edition/ui/root-profile.js` only if required by the established readiness contract; relevant existing `tests/themes/noroot-startup-readiness*.cjs`, `tests/themes/bootstrap-ready.cjs`, `tests/weather/ui.cjs`, `root-edition/ui/test-profile.cjs`; add a narrowly named test under `tests/themes/` if the existing harness cannot express the case.

**Contract:** HomeUIReady resolves only after required profile/render readiness. A synchronous exception or rejected promise from optional Weather/settings-listener startup does not reject it. Required render/profile failures still reject. Optional failures may emit a bounded module/category diagnostic without raw exception text, and must not generate fake health receipts.

- [x] Inspect existing readiness harnesses and prove the current Weather.start throw rejects readiness; show the exact red test result.
- [x] Add cases for synchronous throw, returned rejected promise, successful optional startup, and failed required render/profile. Verify both edition consumers.
- [x] Move optional initialization behind a small local failure boundary. Keep render completion, theme/profile barriers and tile verification intact; do not use blanket catch on the entire startup promise.
- [x] Catch asynchronous initialization failure without an unhandled rejection. Check later weather callbacks only where a reproduced error escapes the optional boundary; avoid speculative refactoring.
- [x] Run affected Node tests plus `npm run test:compat`, relevant weather/theme checks and formatting for modified JS. Do not run a full release build.
- [x] Commit and report source change, red/green commands, exact test coverage, remaining device limits. Do not claim actual legacy TV acceptance from a simulated missing DOM API.

**Acceptance:** injected Weather failure leaves app grid/navigation usable, Home readiness succeeds, and no global update-recovery screen opens; required profile/render failure still enters the supported error path. No emergency/input regression.

## Task 2: Define an advisory recovery-action policy

**Files:** `cytv/recovery_ui.py`, `cytv/recovery.py`, existing Python bridge projection for Android if needed, `tests/cytv/test_recovery_ui.py`, `tests/cytv/test_recovery_actions.py`, `tests/cytv/test_recovery_state.py`, related bridge tests. Do not edit `cytv/gui.py`, `cytv/cli.py`, translation catalogs or Android JS; parent integrates consumers and copy in Task 4.

**Exact API:** `removal_action(plan, failure=None) -> dict` in recovery_ui.py. Its advisory result contains only fixed values:

```python
{'action': 'retry-removal', 'condition': 'transient', 'requires_change': False}
{'action': 'check', 'condition': 'unverified', 'requires_change': True}
{'action': 'connect-root', 'condition': 'access', 'requires_change': True}
{'action': 'retry-removal', 'condition': 'restart', 'requires_change': True}
{'action': 'none', 'condition': 'complete', 'requires_change': False}
```

No operation ID, path, exception text or credential belongs in the projection. Missing/unknown cleanup reason maps to `check/unverified`, never implicit mutation authority. Reuse current reason precedence and connection-failure helpers.

Policy table:

| Current evidence | Action |
| --- | --- |
| Verified terminal removal | none/complete |
| Explicit connect-root action or root-access-required | connect-root/access |
| Restart-required, absent a more specific connection failure | retry-removal/restart, user must act first |
| Network interruption, root-worker-busy, original-writer-active | retry-removal/transient; only on user click |
| Authentication/trust refusal | check/unverified; existing connection details UI remains available |
| cleanup-check-failed, private-cleanup-incomplete, ownership-conflict, controls-unverified, removal-terminal-unknown, removal-failed, unknown | check/unverified |
| Explicit newly requested removal without a failure | retry-removal/transient; it continues the already authorized goal |

- [x] Write table-driven pure tests for the table, malformed plan/failure inputs, precedence, and false terminal claims (removed true without verified_clean is not complete).
- [x] Implement the pure function and project it through the existing recovery plan result where frontend consumers can receive it. Keep assessment and backend proof methods unchanged.
- [x] Ensure a check path can inspect current evidence without performing cleanup; if current recover command mutates or always asks to continue, document its exact contract for the integrator instead of weakening backend authority.
- [x] Preserve original failure and current blocker separately. Add only the diagnostic fields needed to carry the fixed policy; do not widen raw-report exposure.
- [x] Run covering Python and bridge tests. Commit; report the exact projection key and affected frontend field names for Task 4.

**Acceptance:** no unknown or deterministic refusal is labeled an immediate unconditional retry; policy cannot make a denied backend operation succeed. Root/No-root and desktop/Android projections agree. The user retains a supported explicit continuation path after the relevant condition is resolved.

## Task 3: Expose safe maintenance without reinstall

**Files:** `cytv/cli.py`, `cytv/gui.py`, `cytv/debloat.py`, `cytv/operations.py` only if needed for connection-only preparation, `cytv/translations.py`, `tests/cytv/test_debloat.py`, `tests/cytv/test_gui.py`, focused CLI/desktop tests. Do not edit recovery_ui.py/recovery.py or Android assets. Do not change the recovery algorithm unless a test demonstrates a new defect; existing explicit readiness re-arm is already implemented.

**User-facing behavior:** Maintenance offers the existing `recover-root-rollback` and `recover-system-rollback` operations with clear distinct labels and ordinary confirmation. Add a `debloat` CLI action and desktop maintenance entry using the same selection/result UI as setup. It connects using the saved edition/SSH profile and performs selected settings operations only.

- [x] Inspect existing argument/confirmation/profile routing and reuse existing recovery commands; add tests that desktop choices dispatch those commands and retain confirmation/pending guards.
- [x] Add `debloat` to the existing parser/action routing. Use existing connection/preflight requirements necessary for settings access, without package preparation, install Root Home admission, personalization, journal begin, package submission or uninstall.
- [x] Pending install/remove/recovery must stop settings mutations with actionable existing recovery guidance. A Root/Home capability refusal unrelated to settings must not force reinstall; verify actual connection settings capability instead.
- [x] Test Root and No-root, saved Root-SSH No-root profile, cancelled selection, selected write/readback success, policy refusal, pairing failure, and existing pending operation. Spy on install/uninstall/package methods and assert zero calls for every Debloat case.
- [x] Keep Debloat selection consent and v1.20.4 diagnostics; standalone report exports must retain its bounded result categories. If this requires diagnostics.py edits, tell the parent first so it can reserve the file.
- [x] Localize new labels and guidance; update practical maintenance/recovery docs as appropriate without release metadata. Run covering Python/PySide tests and translation checks.
- [x] Commit and report red/green evidence. Explicitly report any CLI-only or frontend gap rather than implying a complete desktop feature.

**Acceptance:** user can reach Debloat or supported rollback recovery from desktop maintenance without reinstall, forced deletion or bypassed recovery guards. Existing setup Debloat flow still works.

## Task 4: Integrate policy into desktop and Android

**Dependencies:** Task 2 policy and Task 3 GUI changes are committed and reviewed first.

**Files:** `cytv/gui.py`, `cytv/cli.py`, Android bridge projection and `android/app/src/main/assets/ui/app.js`, existing translation catalogs, desktop/recovery/Android browser tests.

- [x] Consume removal_action in desktop and Android instead of unconditional Try again for every incomplete cleanup. Keep connection edit controls for authentication/network problems.
- [x] For check/unverified, primary action is an inspection/recovery review, not re-running uninstall. Present the unmet condition and offer explicit continuation only through existing confirmed recovery review with fresh backend checks. Do not strand users by hiding all continuation paths.
- [x] Preserve restart instructions and explicit post-restart continuation; do not automatically restart the TV. Busy/network retries are user initiated and preserve the operation identity.
- [x] Keep terminal verification strict and classified temporary-file warnings visible. Do not mark an operation complete merely because the launcher returned to LG Home.
- [x] Add browser/PySide tests asserting actual command dispatch and button behavior, not only text snapshots. Exercise unknown reason, current connection failure, deterministic cleanup failure, restart, connect-root and verified success.
- [x] Run affected Python/Android/JS formatting checks, commit and submit task review.

## Task 5: Combined review, regression verification and delivery

**Files:** focused existing test fixtures and developer/history evidence; this plan and audit. No release scope/version mutations.

- [x] Integrate reviewed task commits on `codex/recovery-reliability`; resolve only task conflicts and preserve RC content.
- [x] Inventory RC's already added #529/#152/#389 cases. Add only missing transitions exposed by these changes: optional-module failure during readiness; settings-only operation after working installation; deterministic cleanup refusal followed by inspection; explicit rollback recovery dispatch.
- [x] Run changed/dependent suites using repository scripts. Reuse unchanged RC results with their exact scope; do not claim a complete new release validation. Broaden tests only for shared changed boundaries or observed failures.
- [x] Independent whole-branch reviewer checks final diff, safety invariants and user journeys on gpt-6.1-sol/medium. Resolve substantive findings and rerun affected tests.
- [x] Preserve commits and plan/report artifacts; clean up temporary worker worktrees after saving results. Keep the integration checkout for user review.
- [x] Report implemented behavior, test evidence and specific remaining hardware acceptance. No publish, merge into release/next or external issue messages in this task.

## Execution and review ledger

Per-task briefs, reports and review packages live in the integration checkout's `.superpowers/sdd/2026-11-13-post-rc-reliability-execution/`. The durable user-facing plan is this file. Record base/commits, agent IDs, test evidence and decisions there so execution can resume after context compaction.

Conflict scan: Task 1 has no shared implementation files with Tasks 2/3. Task 2 provides one pure policy API; Task 4 consumes it after review. Task 3 owns GUI/CLI first; Task 4 edits those files only after Task 3 integration. Translations are owned by Task 3, then Task 4 sequentially. Task 5 integrates all and owns final evidence. No parallel writer shares an implementation file.


## Implementation result

Implementation and independent review completed on `codex/recovery-reliability`.
The final reviewed implementation commit is `8b9a146`. The integration checkout
is attached to this chat; all three temporary worker checkouts are archived with
recoverable snapshots. Every implementation and review subagent used the user's
requested GPT-6.1 Sol with medium reasoning.

- Home readiness now isolates optional Weather/settings startup failures,
  including the first forecast's scheduled render. Required profile, initial
  render and transaction health checks still gate startup.
- Desktop and Android consume the same bounded removal advice. Unknown or
  deterministic outcomes open recovery review with a separate continuation
  confirmation; known transient interruptions retain the same removal goal.
  Correcting authentication or an unverified connection also stays in review.
  Already Root targets retain their custom SSH port and runtime variant.
- Standalone `cytv debloat` and desktop Maintenance expose selected LG settings
  without installation or package removal. Both rollback recovery commands are
  available on desktop, including the explicit System Updater attempt option.
  Existing confirmation, pending-operation, host-key and completion guards remain.
- Interface copy, technical guides and all 13 localized usage guides match the
  actions. New user-visible strings are localized. No release version, feed,
  signing or publication changes were made.

### Verification

Final integration command (using the prepared virtualenv and offscreen Qt):

```sh
QT_QPA_PLATFORM=offscreen .venv-cytv/bin/python -m unittest   tests.cytv.test_recovery_ui tests.cytv.test_recovery_actions   tests.cytv.test_removal_action_ui tests.cytv.test_simple_removal_ui   tests.cytv.test_clean_removal_cli tests.cytv.test_simple_root_removal   tests.cytv.test_failure_help tests.cytv.test_cli tests.cytv.test_gui   tests.cytv.test_debloat tests.cytv.test_diagnostics tests.cytv.test_i18n   tests.cytv.test_maintenance_flow tests.cytv.test_no_root_simple_removal   android.tests.test_bridge
```

All **341 tests passed** in the final run. Five Android browser runners passed:
`recovery-action.cjs`, `simple-removal.cjs`, `removal-result.cjs`,
`restart-result.cjs`, and `auto-recovery-journey.cjs`. They cover both editions,
13 locales, contradictory completion flags, actual native command dispatch,
Root handoff and preservation of custom Root connection details.

The unchanged Home implementation had already passed **32 startup-readiness
browser cases**, Weather flows and the **832-case Weather matrix**, bootstrap,
legacy compatibility and related safety checks. The policy worker additionally
passed 88 operations tests. These are recorded task results, not a claim that a
new complete release build or physical acceptance was run. Formatting and diff
checks passed. Independent task and combined reviews are approved with no open
findings; their regression cases are included in the final suite.

### Release scope and remaining acceptance

Final remote recheck found RC #606 open at
`ad594431509df0763bad5300da95922260763aa5`. Its only change from our source base
`58ceffd04ba3596f65f309b5ddb04e5ad68e5c4e` pins successful build
[43454675248](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/43454675248).
Application source is identical. Published latest remains v1.20.3. This branch
is separate from the candidate and has not been published or merged.

Before release, verify the inherited G5 Developer Mode removal/restart case,
Root/No-root update and removal on affected firmware, optional Weather failure
on legacy webOS, and rollback recovery after a readiness deadline on physical
TVs. Host/browser tests do not establish those device outcomes.

Two scope limits remain explicit: older receipts recorded only
`connection-interrupted`, so their historical transport subtype cannot be
reconstructed; newly ambiguous failures are saved as `connection-unverified`.
Standalone Debloat blocks unresolved local receipts for the selected host, but
cannot infer an operation initiated by another computer with no local receipt.
No live TV changes or external messages were made.


### Pull request preparation

The maintainer subsequently requested these changes for the current candidate.
Branch `codex/recovery-reliability-rc` applies the reviewed changes on top of
`ad594431509df0763bad5300da95922260763aa5` for an implementation PR to
`release/next`. The original local implementation branch is retained. Product
and test files match the tested implementation; only the documentation and
inherited candidate build pin differ. Inclusion requires the release coordinator
to update the inventory, build and affected acceptance after merge.
