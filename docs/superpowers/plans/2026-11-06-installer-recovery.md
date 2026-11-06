# Installer Recovery Implementation Plan

> **For agentic workers:** Use subagent-driven-development for implementation and independent review. Execute tasks sequentially in this worktree; do not dispatch concurrent implementation agents. Expanded order: 1–4, then 7 (Root clean removal), 8 (No-root clean removal), 5 (all UI/localization), 6 (integration/RC).

**Goal:** Recover supported interrupted installations through the installer, with understandable outcomes and sufficient operation-bound diagnostics.

**Architecture:** Reuse existing Store, Root coordinator, continuation and cancellation checks. Add common recovery assessment, typed authentication and durable per-package No-root observations. Preserve unsupported historical evidence explicitly.

**Tech Stack:** Existing Python, JavaScript, SSH, Luna and browser UI; no new dependencies.

**Spec:** ../specs/2026-11-06-installer-recovery-design.md

## Global Constraints

- Host Python 3.9+, No-root TV Node 0.10.15+, Root Node 8+; existing interpreter validation remains authoritative.
- Preserve trust, original operation/candidate binding, first failure, emergency stop, watchdog, rollback and foreign state.
- No TV connections or public installation reports. The maintainer subsequently authorized merge into release/next and preparation of a new versioned release candidate after implementation and verification; release version/build changes belong only to the final coordinated candidate stage.
- No unknown install/remove replay, file-only terminal inference or automatic legacy journal clearing.
- Update existing locales and guides for every changed user flow; describe unverified hardware honestly.

### Task 1: Typed credentials through normal and passive Android authentication

**Files:** cytv/transport.py, cytv/cli.py, android/app/src/main/python/android_bridge.py; android/tests/test_bridge.py, android/tests/test_root_recovery.py and affected transport tests.

**Interfaces:** Transport supplies a semantic credential type with the existing string prompt. CLI preserves that metadata when localizing; Android emits secretType without guessing from prose. Existing getpass-style callbacks remain callable with a string.

- [ ] Add a regression that feeds the actual passive Root secret callback in every locale; reproduce root/key incorrectly becoming developer before the fix.
- [ ] Implement the smallest compatible typed prompt path and reject unsupported credential kinds. Preserve the original SSH identity, pin and cancellation behavior.
- [ ] Run Android bridge/recovery and affected transport/CLI tests, including raw and localized prompts, cancellation and no secret persistence.
- [ ] Commit the change, record exact checks, and obtain independent task review.

### Task 2: Common recovery assessment and explicit actions

**Files:** cytv/recovery_state.py, cytv/recovery.py, cytv/operations.py, cytv/diagnostic_context.py, cytv/diagnostics.py; tests/cytv/test_recovery_state.py, test_activation_recovery.py, test_operations.py and test_desktop_recovery.py.

**Interfaces:** A pure assessment maps complete host receipt plus verified observation to fixed state/reason/action codes; exports are advice only. Existing backend proof functions remain authority. Actions distinguish checking, continuing setup, completing with LG Home, reconciling verified completion and retaining evidence.

- [ ] Add table-driven and orchestration regressions for pre-submission, live/unknown request, verified packages, disabled/restored activation, terminal removal, inherited/corrupt/foreign state and stale confirmation.
- [ ] Implement assessment and export validation without granting authority from filtered reports. Make Home-off completion directly selectable; default-No confirmation is per action.
- [ ] Persist useful fixed blockers and first-failure/observation distinction, without secrets, identifiers, paths or raw logs in exports.
- [ ] Run focused recovery/diagnostic/desktop tests and commit; obtain independent review.

### Task 3: Verified Root continuation and supported legacy cancellation

**Files:** cytv/operations.py, cytv/recovery.py, cytv/root_passive.py, existing root-edition/install_driver.py, install_device.py, cancel_install.py and cancel_provision.py as necessary; scripts/root-install-recovery.py, related Root and host tests.

**Interfaces:** New protocol receipts may request current trusted coordinator inspection; original UUID, candidate, snapshot, worker and lease remain bound. Existing continuation_status and Recovery.inspect/remove are reused, not approximated. Legacy passive inspection alone is never admission.

- [ ] Reproduce the host-to-coordinator continuation gap after a durable package terminal and before final readback.
- [ ] Add explicit same-operation continuation only where current proof authorizes it; do not turn lost submission into a new request. Revalidate after confirmation and retain the original receipt.
- [ ] Integrate recognized legacy cancellation through the existing proof-bound flow where deploy/runtime compatibility is established; preserve every refusal category and uncertain-removal stop.
- [ ] Cover complete-but-activation-pending setup, baseline propagation, Home-off/update preparation, changed proof, busy child, missing trust and old snapshot layouts. Keep PR #357 separate.
- [ ] Run affected Root/installer checks, commit and obtain independent review.

### Task 4: Durable new No-root package observations

**Files:** cytv/state.py, cytv/operations.py, cytv/transport.py and a focused bundled observer module if required; tests/cytv/test_operations.py, test_recovery_state.py, test_state_receipts.py and dedicated observer tests; builder payload inclusion when needed.

**Interfaces:** New versioned receipts bind operation, edition, package hash, action, observer source and per-package submission/terminal/readback. The observer uses the original public-bus subscribed request and private, atomically persisted receipts, independent of the SSH connection. It never replays unknown submission.

- [ ] Add real-process/filesystem regressions for host disconnect before/after terminal persistence and for duplicate starts, wrong operation/package, malformed/oversized replies and partial writes.
- [ ] Implement detached original-request observation using existing TV facilities and Node 0.10.15-compatible APIs. Preserve public IPK access separately from private credentials/observer journals.
- [ ] Resume only remaining configuration or provably unsubmitted packages. Preserve terminal failure/unknown state, and keep legacy #201/#307 historical-lookup limitations explicit.
- [ ] Cover install Helper then Home and removal, worker loss/reboot ambiguity, owner/path/link safety, existing public API access limits and bounded timeouts.
- [ ] Run observer/installer/runtime compatibility checks, commit and obtain independent review.

### Task 5: User flow, localization, diagnostics and acceptance matrix

**Files:** shared desktop and Android UI, cytv translations/prompts/failure help, all existing docs/i18n guides, docs/RECOVERY.md, relevant developer references and browser tests.

**Interfaces:** The same common assessment drives every frontend. Show what happened, confirmed current state, the recommended available action and exact reason other actions are blocked; retain detailed diagnostics behind an export action.

- [ ] Add browser scenarios for ordinary continuation, LG Home completion, running worker, unknown result, unsupported legacy recovery and cancelled authentication.
- [ ] Implement concise action choices and stable error codes across CLI/desktop/Android, translate every new string and update all affected guides.
- [ ] Add a maintained failure-injection matrix linked to real tests and identify untested physical/device/vendor contracts. Do not request repeated owner probes merely to fill it.
- [ ] Run installer/setup/Android, affected TV runtime and browser checks with pinned dependencies; fix failures and independently review the whole branch.
- [ ] Commit, prepare a compact PR to release/next with linked issues and honest remaining acceptance, reconcile actual issue labels, and preserve the branch before removing the temporary worktree.

### Task 6: Integrate and build the next release candidate

**Authorization:** The maintainer requested in the current Codex chat on 2026-11-06: after finishing everything, merge into the release candidate and build a new candidate version. This authorizes release/next integration and candidate preparation/build, not main publication or a TV operation.

- [ ] Complete all implementation tasks, independent review, affected tests and actual PR CI. Reconcile new PR/issue comments and preserve any concurrently selected release scope.
- [ ] Follow docs/RELEASE-FLOW.md as the single candidate coordinator: merge reviewed implementation into release/next with a merge commit, collect inventory and keep one current candidate record.
- [ ] Select consistent next release/component versions from actual inventory and packaging impact, finish notes and affected localized documentation, and verify baseline/signing prerequisites before full dispatch. Reuse unchanged authenticated evidence where allowed.
- [ ] Explicitly dispatch one full candidate from the complete frozen source, fix deterministic failures, and rerun only failed jobs at unchanged source when appropriate. Pin only its final successful run/attempt.
- [ ] Report exact candidate version/run, package verification and remaining physical acceptance honestly. Leave main unpublished and do not claim installed-device recovery from source/build success.


### Task 7: Independent clean-removal intent and complete Root removal

**Authorization:** Explicit maintainer instruction on 2026-11-06 requires a clean TV after removal regardless of installation success. Read the expanded design and /private/tmp/cytv-clean-removal-design-review.md. This task precedes Task5/6 and is sequential after independently approved Task4.

**Files:** cytv/state.py, operations.py, recovery_state.py, recovery.py, diagnostic_context.py; Root install_driver/install_device/installation/cancellation/provision/updater/bootstrap and existing removal modules as required; focused full-uninstall/coordinator/component tests. Reuse existing primitives, not a second coordinator.

- [ ] Add durable clean-removal intent and safe assessment/diagnostic projections preserving original profile/pin, original/nested receipts and first failure. Remove setup-success as the admission prerequisite; old outcome and new removal outcome are separate. Observation never advances effects.
- [ ] Under original Ownership/component locks, fence every compatible original writer, including pre-reservation launch, and transition to full removal without fresh-UUID lock bypass. Retain exact original evidence and compatible terminal tombstones.
- [ ] Extend Root full-project removal to recognized partial deployment, provisioning, updater/bootstrap and activation states. Restore only owned controls/routes/registration from verified backups; no activation/finish-install prerequisite. Preserve emergency/key-up/guardian until normal controls are restored.
- [ ] Remove product packages with original new-removal terminal evidence and fresh readback; changed product-owned preferences are removable, foreign/shared bytes require exact ownership restoration. Preserve third-party Home baseline, no blanket all-LG assertion.
- [ ] Retire owned credentials/config, executable support, payloads and classified live/archive leftovers after writer/terminal barriers. Keep genuine owner backups/minimal audit separately; no arbitrary archive-prefix purge or falseclean if residues remain.
- [ ] Add real filesystem/orchestration interruption, partial-component, late-worker, repeated-uninstall, foreign-route/backup and cleanup-failure tests; test exact mutation counts. Run focused dependencies, commit/report and obtain independent review. No No-root gate/carrier implementation in this task; expose a narrow shared intent contract for Task8.

### Task 8: Fenced No-root clean removal and partial-package repair

**Files:** cytv/no_root_observer.py, transport/state/operations/recovery/diagnostics as needed; focused standalone native lifecycle gate and existing payload/Android builders; dedicated real-process/native/package-contract tests. Preserve Helper0.7.4 bytes and reuse existing pinned compiler, no third-party runtime library.

- [ ] Add a securely opened never-recreated kernel lifecycle gate and generation revocation, with sole TV-side execution for package/config/EIM/launch effects. Test inherited lock lifetime, paused child/bootstrap, crash, copied host and late effect; no PID/time reclamation or transferable host mutation tokens.
- [ ] Add removal-intent supersession from successful/failed/new/recognized legacy installs, seal/fence old opportunities, preserve original outcome audit, and use a new destructive removal's own admission/terminal rather than requiring old install success. Establish required platform contracts explicitly; no empty-inventory/no-SAM/drain inference.
- [ ] Build narrowly validated inert cleanup carriers for proven missing-SAM owned partial packages when direct remove cannot admit. Preserve exact known old/new service identity union; no functional handlers/controller/startup/keys or unrelated permissions. Validate request/control/app IDs, version/ABI, original binding and current readback. Persist carrier and final removal as distinct original streams; no replay/force/blind repair loops.
- [ ] Complete owned service/data/EIM/private/staging cleanup with minimal non-executable fences; preserve unrelated apps/routes/backups. Repeat removal as verified no-op and resume only provably remaining work. TV-unreachable/API-denied/unknown stages remain truthful removal-in-progress.
- [ ] Cover exact legacy #359 shape, #201/#307 boundaries, missing-SAM plus service residue, source-shaped deletion-only auto-cleanup before/during/after carrier, busy vs accepted-lost, power loss, storage errors and late old configuration. OSE model is development evidence, not retail compatibility proof.
- [ ] Run actual Node0.10.15/0.10.25/0.12.2/current process tests, native lifecycle and packaging/ARM checks, focused installer dependencies; report exact contracts/limitations, commit and obtain independent review. Then Task5 translates/polishes all new flow before final whole-branch review and Task6 RC.
