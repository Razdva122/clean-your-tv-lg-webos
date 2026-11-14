# Update, removal and launcher recovery implementation plan

> **For agentic workers:** Use `executing-plans` to implement the approved scope task by task. This document records analysis and proposed work; it does not authorize publication or device operations.

**Goal:** Let users complete updates and removal, or reach a specific recoverable stop, without repeated reinstall/restart loops; keep optional Home features from failing launcher readiness.

**Architecture:** Extend the existing operation journals and edition-specific recovery adapters. Preserve operation identity, authenticated package results, writer exclusion, emergency Stop and final readback. Introduce a common recovery decision contract and separate core Home readiness from optional modules; do not replace the entire transaction system.

**Tech stack:** Python desktop/CLI and Root coordinators, legacy-compatible Node contracts, JavaScript Home, Android bridge, existing unittest and browser suites.

**Spec:** The evidence, constraints and acceptance criteria in this document implement the user's request to investigate users blocked from uninstall/update and launcher errors.

## Scope and evidence provenance

### Current candidate reconciliation — supersedes the initial prioritization

The first audit used the published baseline and did **not** reconcile the active release candidate. On the user's follow-up, [RC #606, v1.20.4](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/606) was inspected at `58ceffd04ba3596f65f309b5ddb04e5ad68e5c4e`, including its actual diff, release inventory and added regression cases. The same head was verified again after inspection.

| Already included in this candidate | Effect on this plan |
| --- | --- |
| #607: recheck current package-manager state, wait up to 20 seconds for busy installation work, use authenticated original terminal/readback evidence when package status is denied, and permit eligible inherited removal without a changed boot UUID | The main implementation proposed by Task 1 is substantially present. Validate the candidate's existing path; do not build a competing restart/recovery implementation. A truly unresolved writer still requires a supported stop/restart path. |
| #607/#613: temporary installation archives can remain with an explicit warning after required removal checks succeed | Do not treat every retained temporary IPK as a removal failure or demand deletion as a prerequisite for reinstall. This exception does not mean arbitrary private state is disposable or irrelevant. |
| #613: exact known LS2 registration checks without listing foreign registry entries; bounded access diagnostics; EF950V removal and C1 clean-reinstall handoff changes | Part of Task 2 diagnostics and Task 5 firmware/history coverage is already implemented. Validate and retain these cases rather than duplicating them. |
| #614: check package staging before offering unfinished-install continuation; preserve configuration-only continuation without IPKs | Another #529 continuation trap is addressed. Added tests distinguish missing staging with remaining package work from completed package work. |
| #611/#613: restore a verified removable stock-Home file mount or active GlassHouse routing before eligible Root/C1 installation | Additional setup/reinstall compatibility work absent from the initial baseline audit is already in RC. It needs selected artifact/device acceptance. |
| #612: distinguish Debloat pairing, write and readback errors and explain firmware policy refusals | Debloat diagnostics are included; standalone Debloat maintenance without reinstall remains proposed work. |
| #609 and #605: independent clock format and PlxNative previews | Included feature scope is already frozen; this audit does not request removing it or changing the current candidate. |

At this reconciliation the PR reports 493 focused Python tests plus clock/formatting/metadata checks passed. These are reported results, not tests rerun by this audit. Replacement full build [43454675248](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/43454675248) was **queued** when queried; no successful build was pinned and physical TV/rollback acceptance remained pending. Source inclusion is not verified delivery or affected-device recovery.

Final recheck after implementation: RC #606 remains open at `ad594431509df0763bad5300da95922260763aa5`. Its only change after the audited source is `release-plan.json`, pinning build `43454675248` to source `58ceffd04ba3596f65f309b5ddb04e5ad68e5c4e`. The GitHub Actions API now reports that run completed successfully. Published latest remains v1.20.3. The reliability branch therefore uses the same application source as the latest RC; this successful RC build does not validate the new reliability changes or replace physical TV acceptance.

**Still outside the candidate:** isolation of optional Home startup exceptions; a shared semantic retry policy across recovery screens; normal desktop access to existing rollback recovery tools; maintenance-only entry points avoiding reinstall; any missing end-to-end history cases after accounting for RC's new tests. `launcher/app.js` changes in RC only add the clock-format event listener; its HomeUIReady optional-module coupling remains unchanged.

Audit date: 2026-11-13, Asia/Yekaterinburg. Read GitHub releases and issue discussions live. Latest published release at inspection: **v1.20.3**, tag commit `f7fb3fe015dfa8e2e5c68ee9a2406dc153715b8d`. Release history reviewed primarily covers v1.17.0–v1.20.3, with earlier cases where necessary.

Source inspection used `issue-610-debloat` at `47525ea`. GitHub comparison of its parent `538a6fc` to v1.20.3 showed preview/docs/release-plan changes, not the recovery files cited below. The local child changes Debloat diagnostics and its CLI/report plumbing; those changes are not treated as published recovery behavior. Other task branches remain untouched.

The eight detailed recovery discussions inspected were #588, #529, #472, #216, #542, #534, #579 and #438. #499 and #599 were also read to distinguish launcher startup errors from Helper/status failures. These are selected cases, not a statistical sample of installations. No failure rate or causal relationship between release frequency and defects is established.

No TV was contacted or changed. No new runtime tests or firmware emulation were run: this is an evidence/source audit, not a claim of physical reproduction or a completed fix. Existing verification records were read. Exact G5 firmware/offline reproduction remains part of Task 1; existing records already identify the schema-2 limitation, but do not prove why that device reused the observed identity.

## Findings and current delivery state

| Evidence | What it establishes | Current limitation |
| --- | --- | --- |
| [#588](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/588) | Root reinstall entered full removal, packages were gone but private cleanup blocked reinstall. Reporter reproduced the failure on v1.20.2 and identified retained state names absent from cleanup allowlists. | v1.20.3 includes ownership-based cleanup and original-operation resume. At initial inspection, no confirmation was present. The reporter subsequently confirmed verified removal on v1.20.3; #588 is closed. A subsequent Root installation remains untested. Do not implement the shipped cleanup fixes again. |
| [#529](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/529) | Latest attached report is cytv 0.20.3, action recover, pending uninstall, trigger `resident-installer-evidence`, failure `kernel-boot-unchanged`. Reporter says unplugging did not help. The original recorded failure predates the version in the initial prose: first_failure is cytv 0.14.0 with packages verified. | The temporary-IPK continuation improvement did not clear this user's already inherited removal. It is a different remaining stage, not proof that the IPK change itself failed. |
| [#472](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/472) | Removal advanced from inaccessible `/tmp`, to restart verification, to confusion about where Try again exists. A later participant reported completion on the update; the original reporter had not confirmed final completion at inspection. | Do not equate another participant's success with every affected device being recovered. |
| [#542](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/542) | Package rollback succeeded but launcher readiness timed out; the unresolved transaction blocked further updates and Home enable. A published CLI recovery eventually completed, after several attempts described by the reporter. | Recovery exists; the remaining product work is discoverability, coherent retry behavior and prevention of optional startup failures. |
| [#534](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/534), [#579](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/579) | Legacy foreground fallback and Stop-record permission repair have explicit affected-TV success reports. Re-running setup merely to access Debloat exposed a second installation failure on a working TV. | Keep these confirmed regressions in the matrix. Avoid routing maintenance-only goals through reinstall. |
| [#438](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/438) | Removing apps through LG's UI left installer recovery blocked on restoring a stock surface; direct LG Home launch is not portable across firmware. | A shipped legacy adapter does not establish this reporter's final recovery. |
| [#499](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/499) | An unsupported DOM call in Weather caused Home startup to display Software updates recovery. Back returned to working Home. | The specific DOM call was fixed in v1.17.1. The startup dependency still allows a synchronous optional-module exception to reject Home readiness. This evidence describes a recovery-screen failure, not necessarily an OS process crash. |

### Structural causes in the published v1.20.3 baseline

Read these with the candidate reconciliation above: item 1 is substantially addressed by #607's alternative admission path, and items 3 and 5 have partial improvements in the candidate.

1. **The restricted restart contract has no suitable proof on some devices.** `native/contracts/boot-proof.js:110–137` selects schema 2 for inaccessible marker storage and credits only a changed kernel boot UUID. `cytv/no_root_cleanup.py:537–553` refuses an inherited operation when that proof does not change. `docs/history/2026-11-11-issue472-devmode-boot-proof.md` explicitly records same-ID snapshot restart as unsupported without another verified proof. The #529 report reaches this exact refusal. A reboot prompt cannot fix a proof method the firmware does not satisfy.
2. **A setup/reinstall request may become a full removal prerequisite.** `cytv/operations.py:865–867` and `1707–1720` call full removal for the Root reinstall route. An incomplete cleanup therefore blocks installing a replacement even after working packages were removed. This does not describe ordinary OTA, which has its own update/rollback transaction.
3. **Error handling exposes too little distinction for the next action.** `root-edition/install_driver.py:37–75` preserves bounded exception context but maps most cleanup failures to `cleanup-check-failed`; `cytv/recovery_ui.py` tells users to retry for these categories. `cytv/gui.py:749–757` offers Try again for incomplete cleanup without a semantic retryability decision. Repeated attempts can be offered even when no input or state changed.
4. **Core startup and optional features share failure propagation.** `launcher/app.js:2724–2734` calls Weather and settings listeners inside `HomeUIReady`. `root-edition/ui/root-profile.js:198` sends rejection of that promise to update recovery. The unsupported Weather call was fixed, but this propagation mechanism remains.
5. **QA is stronger on artifact provenance and the project C3 than on retained user histories.** The v1.20.3 acceptance record includes real install, update, rollback and removal checks. Its No-root run uses Root SSH, while #529 uses Developer Mode. It explicitly leaves original G5/C1 states unverified. The gap is the state/connection matrix, not an absence of tests.

## Global constraints

- No unconditional deletion/reset of pending journals, keys or ownership leases.
- File/package absence alone is not evidence that an old writer cannot resume.
- Preserve explicit Stop, triple Home, Home Off, watchdog protection and foreign Home filters.
- Never mark verified-clean while required private cleanup or necessary final proof is incomplete. RC #607/#613 explicitly permit classified temporary installation archives to remain with a warning; retain that distinction.
- Do not turn firmware access denials into success; use a supported alternative or a specific blocked outcome.
- Reuse shipped fixes and existing test evidence. Create focused changes before one frozen candidate.
- Keep existing Python/legacy Node/browser compatibility and Android package/signing identity.
- Technical repository documentation is English; practical guides and user-facing copy remain localized.
- Use existing redacted reports and consented evidence; no hidden telemetry or publication of raw reports.

## Implementation sequence

### Task 1 — P0: accept the candidate's inherited No-root recovery fix

**Files:** `native/contracts/boot-proof.js`, `cytv/no_root_cleanup.py`, `cytv/no_root_observer.py`, `cytv/recovery_state.py`, `tests/cytv/test_no_root_simple_removal.py`, `tests/cytv/test_no_root_fence_removal.py`.

- [ ] Reuse #607's existing restricted-tmp, resident-installer, busy-package-manager and original-terminal/readback tests, plus #614 staging tests. Compare the #529 historical report to their preconditions; add only a demonstrably missing case.
- [ ] On the selected candidate artifacts, validate Developer Mode removal with inherited original-stream state and unchanged boot UUID: eligible current idle/evidence checks permit completion; a genuinely unresolved writer remains blocked. Preserve the original install and removal identities.
- [ ] Verify configuration-only continuation after installed packages and missing IPKs separately from unfinished package submission with unavailable staging. Do not offer the latter as a ready continuation.
- [ ] Verify classified temporary archives do not prevent reinstall, while active writers, required registration failures, changed paths and explicit Stop retain their guards.
- [ ] Finish the affected user's journey: original pending operation → verified removal or supported setup completion → usable installation. Confirm the original G5 case before calling that device recovered.
- [ ] Only if candidate evidence still fails, follow the offline firmware workflow for the exact image (or document the blocker/comparable-image limits), isolate the remaining condition, and prepare a focused follow-up. Do not introduce a new boot-proof scheme solely because v1.20.3 lacked this continuation.

**Dependency/output:** supplies a typed restart/proof decision consumed by Task 2; does not authorize generic same-boot cleanup of inherited operations.

### Task 2 — P0: actionable recovery decisions and bounded retry

**Files:** `cytv/recovery_state.py`, `cytv/recovery_ui.py`, `cytv/gui.py`, `cytv/cli.py`, `cytv/diagnostic_context.py`, `root-edition/install_driver.py`; existing desktop, recovery UI, clean-removal and diagnostic tests; Android maintenance presentation using the same contract.

**Proposed decision projection** (advice only; every backend action revalidates authority):

```json
{
  "goal": "remove",
  "phase": "private-cleanup",
  "condition": "proof-unavailable",
  "retry_policy": "after-evidence-change",
  "next_action": "save-report",
  "home_control": "stock-verified"
}
```

The contract should distinguish `transient`, `needs-user-action`, `unsupported`, `conflict` and `internal-error`, retaining first failure separately from the current blocker. Do not expose paths or credentials through these categories.

**Candidate overlap:** reuse #607's busy-operation waiting, #613's blocked-area diagnostics, #614's staging-specific refusal and #612's Debloat categories. A universal retry-policy contract and corresponding GUI gating are not in the inspected diff.

- [ ] Add failing cases for deterministic cleanup refusal, transient SSH loss, writer busy, unsupported restart proof and original package failure followed by cleanup failure.
- [ ] Add typed, allowlisted causes at the point of failure; preserve them through coordinator, CLI/Android bridge, diagnostics and UI. Do not infer cause from translated error strings.
- [ ] Offer retry for transient failures or a verified changed precondition. Keep a read-only recheck available for other cases; do not automatically repeat mutation. Show the missing condition and completed phases.
- [ ] Distinguish “LG Home restored; cleanup unfinished” from full removal success. Keep the original goal visible so an update request does not silently become an unexplained uninstall screen.
- [ ] Expose a pending operation from the saved TV maintenance screen, regardless of whether the user last selected Check connection, status or recover.
- [ ] Acceptance: each modeled failure has one applicable next step, no false success, no exception-only wording, and no automatic repeat with unchanged evidence. Desktop, CLI and Android agree on the decision.

### Task 3 — P0: isolate optional launcher startup failures

**Files:** `launcher/app.js`, `launcher/weather.js`, `launcher/profile-bootstrap.js`, `root-edition/ui/root-profile.js`; `tests/themes/noroot-startup-readiness.cjs`, `tests/themes/noroot-startup-readiness-ui.cjs`, `tests/themes/bootstrap-ready.cjs`, `tests/weather/ui.cjs`, `root-edition/ui/test-profile.cjs`.

- [ ] Inject a synchronous exception from Weather startup and settings listeners on both editions. Assert whether it currently rejects HomeUIReady or opens update recovery; retain the observed result as the regression.
- [ ] Define core readiness as a restored/validated required profile, rendered navigable app grid and available basic launch controls. Keep these checks authoritative for update acceptance.
- [ ] Start optional modules behind local failure boundaries; report their degraded status without opening transaction recovery. Handle asynchronous failures as well as synchronous exceptions. Do not suppress a required profile/integrity failure.
- [ ] Add legacy-DOM coverage for browser APIs used by startup modules; Babel/Node checks alone do not establish browser DOM support.
- [ ] Acceptance: Weather failure leaves Home navigation and app launch usable; actual profile/hash/readiness failures still enter supported recovery. Neither edition fabricates a ready receipt before core readiness.

### Task 4 — P1: recovery should not require reinstalling working software

**Files:** `cytv/operations.py`, `cytv/recovery.py`, `cytv/root_rollback_recovery.py`, `cytv/system_rollback_recovery.py`, `cytv/gui.py`, `cytv/cli.py`, `root-edition/updater/core.py`, `root-edition/ui/root-updates.js`; `tests/cytv/test_root_updater_recovery.py`, `tests/cytv/test_system_rollback_recovery.py`, `root-edition/tests/test_root_rollback_readiness.py`, `root-edition/tests/test_update_core.py`.

- [ ] Route the existing standalone Root and System rollback recovery commands into normal desktop recovery choices after inspecting the correct transaction owner. Do not invent a second recovery engine.
- [ ] Verify one explicit retry handles an expired readiness attempt coherently: reconcile the expired attempt, archive it, revalidate restored bytes/profile, and arm a fresh bounded window when eligible. A live window or another owner must not be superseded.
- [ ] For a healthy installed Root, prefer the existing verified updater path where compatible. Present full reinstall/removal as a distinct selected operation with its consequences visible. Validate replacement artifacts and the recovery path before removal.
- [ ] Make Debloat and other settings-only maintenance reachable without re-entering package installation. Its failures must not create an install/uninstall pending journal.
- [ ] Acceptance: a verified restored installation can leave recovery without uninstall; settings-only maintenance never calls prepare_root_reinstall or package submission. Unsupported migrations retain their explicit full-reinstall path.

### Task 5 — P1: historical-state regression matrix and release acceptance

**Candidate overlap:** #607/#613/#614 already add several proposed transition and firmware cases. Inventory their tests and reuse the 493 reported focused results where inputs match; this task is the remaining coverage/acceptance work, not a mandate to rewrite those tests.

**Files:** existing `tests/cytv/clean_removal_fixture.py`, removal/recovery suites, `root-edition/tests/test_clean_removal.py`, `root-edition/tests/test_simple_removal.py`, `root-edition/tests/test_cleanup_tail.py`, `docs/RELEASE-FLOW.md`, candidate verification ledger.

- [ ] Retain #588 as an upgrade-history regression: Root update failure, rollback receipts, old private files, partial removal, host restart, final removal, fresh install. Confirm v1.20.3's existing ownership cleanup passes before adding further cleanup changes.
- [ ] Retain #534/#579 as confirmed legacy regressions: denied foreground method, alternate paired read, firmware-expanded Stop mode, uninstall, reinstall, physical Home.
- [ ] Add missing transition cuts: request sent/reply lost, package terminal/readback lost, desktop exit before local journal completion, restart after partial cleanup, manual app deletion, expired readiness and repeated explicit retry.
- [ ] For each cut assert no duplicate package submission; same operation identity; preserved Stop and foreign state; either correct terminal completion or a concrete blocker. An ambiguous vendor outcome may remain blocked, but must not be represented as a transient retry.
- [ ] Separate Root SSH and Developer Mode acceptance. Minimum affected scenarios: modern Developer Mode inherited removal, Root System-profile reinstall/rollback history, legacy webOS 4.x Home/permission behavior. Native C1 cases are required when changed shared cleanup affects that backend.
- [ ] Use the existing test runner and exact runtime setup from CONTRIBUTING.md. During implementation run affected unittest files and browser suites; on the frozen candidate run required aggregate checks with authenticated matching evidence reuse. Do not repeat the current audit's unchanged tests just to generate a new count.
- [ ] Release acceptance is the user's completed journey: update → usable Home, or remove → verified cleanup → successful subsequent install. Passing the formerly failing line alone is insufficient.

### Task 6 — P1: release scope and measurement

**Files:** `release-plan.json`, candidate history record, `docs/RELEASE-FLOW.md`, `docs/RECOVERY.md`, affected practical guides.

- [ ] Finish the already frozen v1.20.4 candidate's required checks and affected acceptance. Keep new reliability work in follow-up branches unless the release coordinator identifies a candidate blocker; propose a subsequent focused reliability candidate for the remaining scope.
- [ ] Distinguish source fix, published delivery, and affected-device recovery in release notes and issue summaries. A diagnostics-only improvement must not be presented as resolution of the original issue.
- [ ] Review existing report cohorts by original installed version, target installer, edition, SSH type, firmware and last failing phase. Deduplicate repeated reports from one operation.
- [ ] Measure: completed removals among observed removal attempts; verified updates with usable Home; operations requiring more than one recovery attempt; unresolved operations with unchanged blocker; repeated power-cycle requests; optional startup failures entering global recovery. Use consented reports/test runs and label the denominator. Current data does not establish population rates.
- [ ] Initial release criteria: every selected fixture has an expected terminal/actionable outcome; no duplicate mutation on replay; no optional-module exception rejects core readiness; all selected hardware cases are passed, concretely blocked or explicitly deferred under repository rules. Do not claim universal compatibility from one C3.

## Recommended ordering and completion boundary

First complete Task 1 and the affected Tasks 5–6 acceptance for the existing v1.20.4 RC without duplicating its implementation. Then prioritize Task 3 optional-startup isolation and the remaining Task 2 retry UX, followed by Task 4 recovery discoverability and maintenance separation. Keep these follow-ups outside the frozen RC unless they fix a confirmed release blocker.

Avoid a broad coordinator rewrite or simply removing protective checks. The existing journals, final readback, ownership-based cleanup and published recovery commands are useful foundations. The missing work is a valid exit for supported retained states, bounded retry, optional-feature isolation, and verification of complete user journeys.

This plan is complete as an investigation deliverable. Product changes, device validation and release publication remain unperformed.


## Issue reconciliation for PR preparation

Latest public discussions were re-read before preparing the implementation PR.
#588 is closed after the reporter confirmed verified G5 cleanup on v1.20.3;
subsequent Root installation was not tested. #534 and #542 remain closed with
confirmed recovery, and #499 remains closed for its earlier shipped DOM fix.
These are related history for the new maintenance and isolation work, not new
claims of fixing their original failures. #529 remains open: its latest report
still fails restart verification. This PR improves next-action guidance but
does not establish recovery on that G5 or solve the firmware-specific boot proof.
