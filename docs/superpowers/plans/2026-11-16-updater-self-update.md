# Cross-edition System Updater self-update implementation plan

> Execute sequentially with the executing-plans skill. This plan does not authorize
> parallel agents, release publication, changes to the frozen candidate, or device
> operations. Use existing maintainer authorization where it is established.

**Goal:** Establish a first baseline that can update its own engine and all selected
edition components through Update all, with an evidence-based Developer Mode path.

**Architecture:** A stable recovery launcher selects verified engine slots. The
root executor serves both Root and No-root editions. A Developer Mode executor is
admitted only after its independent authority and recovery probe succeeds.

**Tech stack:** Existing Python/Node, LS2, SSH, signed GitHub release packages,
filesystem journals and current desktop/Android clients. Select additional runtime
or SSH dependencies only after the unrooted probe establishes actual requirements.

**Spec:** [Design and behavioral contract](../specs/2026-11-16-updater-self-update-design.md).

## Constraints and implementation baseline

The maintainer subsequently selected implementation of Root and No-root on rooted
TVs only. Tasks 2 and 7 and acceptance cases SU-11/SU-12 remain outside that
selected scope. The architecture proposal below retains the broader future work;
it is not a claim that a Developer Mode executor was implemented. See the
[implemented delivery contract](../../development/SYSTEM-SELF-UPDATE.md).

- `1.23.0` is provisional. Allocate actual versions with the release coordinator.
- Repair of 1.21.0-to-1.22.0 OTA is excluded by the maintainer.
- Preserve edition independently of root capability, user profile/media, emergency
  stop, terminal installer evidence and previous-release rollback.
- Use signed immutable bytes and existing operation ownership. Never infer success
  from version readback or resubmit an uncertain package operation.
- Implement against current integration code in an isolated checkout if concurrent
  work requires it. The maintained checkout had unrelated edits during planning.
- Keep feature work outside the frozen candidate until the coordinator admits it.
- Read CONTRIBUTING.md and follow worktree cleanup and verification reuse rules.
- All new filenames/functions below are proposed interfaces, not existing code.

## 1. Capture the baseline and capability contract

Files: `system-updater/cli.py`, `system-updater/service.js`,
`system-updater/policy.js`, `launcher/system-updates.js`, `cytv/operations.py`.
Add `tests/system_updates/test_capabilities.py` and fixtures from the first selected
signed baseline. Reuse `tests/system_updates/service.cjs` and `ui.cjs`.

Proposed status fields:

```json
{"edition":"no-root","executor":"root","authority":"ready",
 "engineVersion":"2.0.0","bootstrapProtocol":1,"selfUpdate":true,
 "operation":null}
```

`executor` is `root`, `developer-mode` or `external`; `authority` is `ready`,
`unavailable` or `unknown`. Example version is illustrative, not allocated.

- [ ] Refresh source inventory after current release integration. Trace both UI
  entry points, standalone recovery apps, setup and removal against actual head.
- [ ] Add contract fixtures for No-root/root, No-root/prisoner, missing supervisor,
  denied status, root loss, old Node, pending installation and an edition mismatch.
- [ ] Implement authenticated capability reporting without changing installed
  edition on root discovery. Preserve last-known state on communication errors.
- [ ] Verify existing service/UI callers and commit this bounded interface change.

## 2. Prove the unrooted executor before committing to its product promise

Files: new `scripts/probe-devmode-update.py`, reuse `cytv/transport.py`,
`cytv/no_root_observer.py`, `cytv/storage.py`, `android/DEVELOPMENT.md`.
Record redacted results under `docs/history/` only with applicable device consent.

- [ ] Prepare two disposable test package versions and a dedicated probe service.
  Include signed package identity/hash verification and an original-response receipt.
- [ ] On a genuinely unrooted authorized TV, verify service-to-SSH networking,
  prisoner identity, host-key verification and dev/install access from that context.
- [ ] Verify private durable credential/journal/cache locations across application
  closure and reboot. Test the actual vendor Node/runtime and permissions.
- [ ] Install version A then B, capture terminal results, verify bytes and launch,
  then roll back. Close the initiating app during installation and reconcile once.
- [ ] Test replacement of the probe updater itself with an independent worker.
  After reboot, verify how recovery is reached and that state can be read safely.
- [ ] Exercise expired session/auth failure without resetting a user's installation.
  Record exact blockers and select on-TV or assisted backend using the spec table.
- [ ] Keep this result independent of Root acceptance. Commit harness and permitted
  evidence; do not claim an untested backend works.

## 3. Define and sign the bootstrap catalog

Files: new `system-updater/bootstrap-policy.js`,
`scripts/sign-system-bootstrap.cjs`, `tests/system_updates/bootstrap-policy.cjs`;
modify `system-updater/build.py`, `scripts/sign-release-feeds.cjs`,
`scripts/publish-release.cjs` and their existing signing tests.

Proposed interface `selectTransition(catalog, installedCapabilities)` returns one
verified next-engine descriptor or a typed reason. Descriptors bind edition scope,
source versions, runtime, hashes, launcher capability and state-schema range.

- [ ] Define bootstrap-v1 schema, immutable asset naming, stable endpoint, size
  limits, bounded transition graph and supported baseline retention rules.
- [ ] Add signature tests for skipped releases, wrong edition/CPU/runtime, unknown
  required features, cycles, rollback attacks and incomplete published assets.
- [ ] Specify trusted-key rotation, metadata sequence/expiry and clock failures.
  Test old-key-authorized transition and rejection of an untrusted replacement key.
- [ ] Implement deterministic selection and signed engine-bundle generation. Freeze
  selected descriptors in transaction state before any mutation.
- [ ] Publish catalog only after verifying all referenced assets. Keep product and
  bootstrap channels distinct, and test that a new product protocol leaves old
  bootstrap readers able to select their bridge.
- [ ] Run targeted policy/signing checks and commit.

## 4. Implement independent recovery and engine activation

Files: new `system-updater/bootstrap.py`, `system-updater/activation.py`,
`tests/system_updates/test_activation.py`; modify `system-updater/setup.py`,
`system-updater/build.py`, `system-updater/service.js`, `system-updater/cli.py`,
`root-edition/startup_hook.py`, `cytv/system_updater_remove.py`.

Proposed interfaces `stage_engine(descriptor, archive)`,
`activate_engine(operation_id)` and `reconcile_activation(operation_id)` return
durable state. The launcher derives all destinations from its private slot root.

- [ ] Test staged hashes and archive bounds, path traversal, symlinks, ownership,
  short writes, disk-full, worker lifetime and concurrent activation requests.
- [ ] Implement inactive-slot extraction with fsync and a durable activation record.
  Snapshot compatible state before migrations and preserve the previous slot.
- [ ] Implement service switch plus readiness carrying operation, engine hash and
  generation. Reject stale acknowledgments and avoid two active workers.
- [ ] Inject crashes at every persisted transition. Boot recovery must choose a
  provably complete slot or preserve a concrete recovery-required state.
- [ ] Integrate setup, removal and installer readback with both slots and the new
  launcher. Removal respects pending work and ownership before deleting state.
- [ ] Prove signed launcher/IPK/registration replacement by a surviving worker, or
  retain it as an explicit unsatisfied full-self-replacement acceptance requirement.
- [ ] Run activation, startup, removal and permission checks, then commit.

## 5. Join engine and product updates into one operation

Files: `system-updater/core.py`, `system-updater/device.py`,
`system-updater/cli.py`, `root-edition/installation.py` (`device_operation`),
`launcher/system-updates.js`, `tests/system_updates/test_core.py`,
`tests/system_updates/test_device.py`, new `tests/system_updates/test_self_update.py`.

- [ ] Locate the canonical operation owner and register the outer engine/product
  operation there. Avoid adding a second competing device lock protocol.
- [ ] Reserve one target, cache candidate/baseline packages, save profile and user
  intent, activate required engine, then invoke the existing product transaction.
- [ ] Keep baseline state readable across migration and define whole-operation
  rollback. Reverting engine alone must not leave unsupported product/state behind.
- [ ] Preserve current installer observation rules through disconnect and reboot.
  A transaction with unknown submission stays blocked until terminal reconciliation.
- [ ] Add explicit same-version repair through Recovery with signed exact bytes.
- [ ] Test one-click transitions and failures from the unchanged first baseline,
  including future manifest format, newly introduced companion and new permissions.
- [ ] Run focused manager/device/UI cases and commit.

Concrete regression shape for the proposed engine interface:

```python
def test_recovery_ignores_unready_candidate(harness):
    original = harness.active_engine()
    operation = harness.stage_signed_future_engine()
    harness.crash_after(operation, "activation-intent")
    harness.restart_bootstrap()
    assert harness.active_engine() == original
    assert harness.product_installs() == []
    assert harness.profile() == harness.original_profile

def test_unknown_install_is_not_replayed(harness):
    harness.start_update_all()
    harness.disconnect_after_installer_acceptance()
    harness.restart_bootstrap()
    harness.reconcile()
    assert harness.install_submission_count() == 1
    assert harness.status() == "recovery-required"
```

Build this harness using the existing fake device/store fixtures and real manager,
activation and verifier implementations. Do not replace those implementations with
mocks returning the expected status.

## 6. Complete No-root/root lifecycle support

Files: `system-updater/device.py`, `system-updater/setup.py`,
`native/helper-rollback-compatibility.json`, `native/app/home-control.js`,
`renewal-service/home-control.js`, `cytv/operations.py`,
`tests/system_updates/test_device.py` and existing Helper integration tests.

- [ ] Build the No-root signed set including any candidate companion and permissions.
  Capture actual Helper/Home rollback compatibility using existing approval flow.
- [ ] Use existing suspend/restore paths for Helper and renewal. Preserve explicit
  stop and emergency stop across success, rollback and same-version repair.
- [ ] Extend initial provisioning to No-root/root through normal installer UI and
  CLI. Root detection alone cannot initiate provisioning or switch edition.
- [ ] Verify full profile and personal-media retention, Home status, Companion,
  Helper foreground readiness and existing recovery app entry points.
- [ ] Test root loss and engine outage without silently choosing another backend.
- [ ] Run focused checks and commit.

## 7. Implement the selected Developer Mode delivery path

Common files: `launcher/system-updates.js`, `cytv/operations.py`,
`cytv/no_root_observer.py`, `cytv/transport.py`, `cytv/installer_update.py`,
`android/stage.py`, existing desktop/Android integration tests.
If Task 2 passes, add `devmode-updater/service.js`, `devmode-updater/worker.js`,
`devmode-updater/build.py` and `tests/devmode_updates/` with equivalent signed-contract
fixtures. Bundle a compatible SSH implementation only if required by the probe.

- [ ] Share signed release data and test vectors across root and Developer Mode
  implementations. Avoid requiring the unrooted TV to run the root Python engine.
- [ ] Generalize the observer's fixed two-package plan to a bounded signed edition
  inventory, keeping request hashes and original terminal evidence per component.
- [ ] For on-TV mode, provision private authentication, durable state, detached
  worker and an independently launchable recovery surface. Test its own replacement.
- [ ] For assisted mode, display the update and client-required state, then let the
  opened paired client select the same signed target and execute it. Update outdated
  client support before starting package work. Keep all credentials in that client.
- [ ] Preserve profile/media outside replacement targets. Revalidate Developer Mode
  session and install permission before mutation. Session loss retains uncertainty.
- [ ] Test helper replacement, companion installation, updater replacement, boot
  recovery, skipped releases and reinstall-after-session-loss as separate cases.
- [ ] Commit only claims supported by the selected backend's actual results.

## 8. User flow and documentation

Files: `launcher/system-updates.js`, `launcher/i18n.js`, `cytv/translations.py`,
`docs/UPDATES.md`, `docs/RECOVERY.md`, `docs/i18n/`, `docs/RELEASE-FLOW.md`.

- [ ] Show edition and meaningful user state. Root-capable mode offers Update all,
  progress, completion and Recovery. Hide engine protocol choices from the UI.
- [ ] On unrooted supported devices, show Developer Mode renewal/reconnection only
  when it is the actual failed prerequisite. Assisted mode says to open the paired
  CYTV client and never claims installation has started before acceptance.
- [ ] Reconnect UI after engine/service restart using the saved operation ID.
  Closing Home must not cancel an accepted transaction.
- [ ] Explain rollback's settings snapshot and same-version repair in Recovery.
- [ ] Keep localized guides practical and version-free. Put baseline versions,
  runtime limitations and QA evidence in developer/release documentation.
- [ ] Verify remote focus, locale layout and accessible progress, then commit.

## 9. Release acceptance and future publication gate

Files: `scripts/release-flow.py`, `scripts/build-tv-candidate.py`,
`scripts/root-candidate-feeds.py`, `.github/workflows/release-candidate.yml`,
new `tests/system_updates/test_supported_upgrade_paths.py`, release verification ledger.

| Case | Required observation |
| --- | --- |
| SU-01 | Installed first-baseline reader accepts signed bootstrap catalog and rejects invalid trust/target metadata |
| SU-02 | Root Update all upgrades engine then a product requiring that engine, with exact final bytes |
| SU-03 | No-root/root Update all delivers Home, Helper, updater and companion, preserves settings and checks Home |
| SU-04 | Skip intermediate releases and complete all required engine transitions |
| SU-05 | Bad engine readiness restores executable recovery and coherent state |
| SU-06 | Crash at every journal transition resumes safely; unknown installer submission is never repeated |
| SU-07 | Runtime/ABI mismatch, full storage and unavailable packages stop before mutation |
| SU-08 | Whole-operation rollback, user-requested product rollback and same-version repair preserve defined snapshots |
| SU-09 | Launcher/IPK/LS2 migration preserves independent recovery through its own replacement |
| SU-10 | Root/authority loss, edition mismatch and concurrent desktop/TV commands retain one owner |
| SU-11 | No-root genuine unrooted execution and self-recovery pass, or concrete assisted-backend result is recorded |
| SU-12 | Developer Mode expiry/auth failure yields accurate recovery instructions and no false completion |
| SU-13 | Signing-key rotation and catalog retention let an unchanged old client still reach a valid future release |
| SU-14 | Exact final artifacts pass selected network Home, profile/media and affected physical-input/boot cases |

- [ ] Preserve first-baseline client bytes and authenticated provenance as permanent
  fixtures. Test actual old code against new signed artifacts at each publication.
- [ ] Group equivalent supported clients by actual parser/runtime behavior, not
  release labels. Keep bridge artifacts for each supported class.
- [ ] Run existing focused tests during development. At freeze follow full candidate
  checks, pin final signed artifacts, and run only missing affected device cases.
- [ ] Reconcile every selected case in the original ledger. Report observed pass,
  fail, reusable evidence or concrete dependency blocker. Do not omit independent
  checks after the first failure. Separate failure inventory from acceptance.
- [ ] Block publication if a supported client has no proven update route or if
  any required recovery transition is unresolved. Do not announce unrooted on-TV
  support based on a rooted TV test or successful package installation alone.

## Planning verification

The plan covers all three privilege/edition combinations, first-time setup,
self-update, launcher migration, repair, rollback, skipped releases, key rotation,
runtime compatibility and publication. The main unresolved feasibility question
is autonomous Developer Mode installation and durable self-recovery on a genuinely
unrooted device. Task 2 establishes this before that backend is promised.

No TV operation, product implementation, branch switch, release change or
publication was performed while preparing these documents. The current files
are an implementation proposal and have not passed device acceptance.
