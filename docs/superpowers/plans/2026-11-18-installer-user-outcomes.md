# Installer completion and fewer support requests

**Implementation plan · 18 November 2026 · Desktop, CLI and Android**

**Goal.** Help owners complete installation, recover from an interruption, or return to LG Home without a maintainer walking them through the installer. Reduce recurring support issues by removing their causes and by making the next safe action available at the point of failure.

**Architecture.** Keep decisions about whether the device can be changed in the existing Python installer and TV-side protocols. Use the current operation record, live observations and existing recovery actions. Desktop Qt, the CLI and the Android bridge present the same result. A screen, diagnostic export or historical success cannot grant permission to change a TV.

**Specification and baseline.** This plan implements the user journeys and acceptance cases below. The published reference for the investigation is [v1.24.0](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.24.0). The integration reference is [96a51b24](https://github.com/Razdva122/clean-your-tv-lg-webos/tree/96a51b24048246fae41cd4ac5073770fff6ff9a0). The existing [installer recovery design](../specs/2026-11-06-installer-recovery-design.md) describes the underlying recovery flow. Use the [contribution rules](../../../CONTRIBUTING.md) for implementation.

## Why these tasks come first

| Observation on 18 November | Consequence for the plan |
| --- | --- |
| Of 72 external issues with a readable diagnostic in the opening post, 17 pointed to installation inspection and 17 to the package step. Seven package cases returned `pending-operation`. In two of these the storage check failed before package submission. | Distinguish a safe pre-submission retry from an uncertain device operation. Review [#409](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/409), where an owner later confirmed success, and [#417](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/417). |
| Among 22 external threads with removal-related diagnostics, eight included `cleanup-check-failed`, five included a restart request and two included incomplete private cleanup. These sets overlap. | Show which part of removal has finished. Resume the same operation after reconnect. In [#440](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/440) the owner had to ask how to go from Restore to removal. In [#472](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/472) the owner ultimately confirmed package absence, LG Home and a responding remote. |
| Five opening diagnostics identified Root Home interfaces and two identified Root prerequisites. Nine stopped at SSH and four at TV pairing. Many earlier reports had no specific reason code. | Check alternatives the TV can actually run and give connection advice for the failed transport. [#519](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/519), [#410](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/410), [#217](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/217). |
| In [#389](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/389) removal and reinstallation succeeded, but physical Home still selected LG Home. | Installation, launch and Home routing each need their own observed result and next action. |
| In 153 external threads, 79 opening posts contained a recognizable diagnostic link or embedded report. In 18 the entire body consisted of JSON attachment links. These figures include successful reports and feature requests. | Ask the owner only for facts the installer cannot see. Preserve an easy path to report a new defect. |

The counts describe self-selected support threads across versions. They do not estimate failure rates among all installations. A thread can report several failures over time. The three historical `inventory-unavailable` opening reports concerned Root. The optional HDMI failure on No-root was reproduced separately against the integration code.

## Dispatch and verification

**One numbered card = one assignment for one agent.** Give the agent its card, this section and the linked evidence. For agent-driven work use the subagent-driven-development workflow. Agents inherit the parent model and reasoning level. This document is a backlog for assignment. It does not start agents, open issues or schedule monitoring.

**First dispatch.** Start T01 (actual support baseline), T02 (false pending state), T12 (actual removal failure) and T23 (optional HDMI failure). They have separate primary write areas. T02 and T12 have the strongest support evidence. T23 is a short reproducible fix. Next bring T04, T05, T13 and T14 through their listed dependencies. Later task IDs are stable assignment identifiers, not a promise to build every item before shipping useful changes.

**Coordination.** The prerequisites on each card are hard dependencies. Cards without a shared prerequisite can still touch the same file. Sequence edits to the same function, shared translation catalog or Android renderer. Reuse a merged change that already meets the card and record the matching evidence. Compare current integration and active PRs first, especially [#704](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/704), [#705](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/705) and [#708](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/708). Work from an up-to-date checkout based on `release/next`. Preserve unrelated local work.

**How to finish a card.** Reproduce its named case via the normal entry point, make the smallest change, and verify the positive and refusal cases. Include affected public strings and practical guides with the behavior change. Link the existing issue when applicable. Keep the regression, result and remaining device-specific limitation together in the implementation PR. A passing fixture is an offline result. Only apply issue labels or post updates under the repository's normal issue workflow. A card is not a request to create a GitHub issue for tracking.

**Verification commands.** For a named host suite such as `tests/cytv/test_tv.py`, use `.venv-cytv/bin/python -m unittest discover -s tests/cytv -p test_tv.py` from the checkout root. For example, T02 starts with `.venv-cytv/bin/python -m unittest discover -s tests/cytv -p test_no_root_observer_diagnostics.py`. Use `scripts/test.sh installer` for shared installer behavior and `scripts/test.sh android` when the bridge or Android rendering changes. Reuse matching evidence according to the release ledger. Full release acceptance belongs to the release coordinator. Use the offline firmware workflow before requesting another owner run.

**Common constraints.** Preserve the original TV identity, stock Home recovery, emergency stop, artifact integrity, operation ownership and explicit consent for destructive actions. When the prior submission is uncertain, observe it before considering another mutation. Keep legacy operation records usable. Application lists, addresses, credentials, SSH keys and raw diagnostics stay outside public examples. Use synthetic fixtures or already-approved redacted facts.

**Priorities.** P0 addresses observed loops, ambiguous device state or loss of control. P1 improves self-service for a documented cause. P2 addresses a narrower case or measures results after adoption. The Start recommendation above deliberately includes one short P1 change.

## A. Stop sending fresh installs into recovery

### T01 · Establish the baseline for repeat support · P0

- [x] **Agent assignment, ready now.** Use the published external issues and the criteria under “Measurement” below. Produce a dated, aggregate table in `docs/history/` with the query, dates, release exposure and counts. Start with #409, #417, #440 and #472 to calibrate the coding.
- **Accept when** another maintainer can distinguish an external report from an internal task, a request to revisit the TV from a shipping notice, and confirmed success from a silent closure. Count one thread once per cause. Record unknowns and the denominator.

### T02 · Distinguish a failed preflight from an uncertain package submission · P0

- [x] **Agent assignment, ready now.** In `cytv/no_root_observer.py`, trace `begin`, `invoke` and `observation_error`. Expose a bounded reason for a failed storage selection/check when the current attempt has not submitted a package and there is no conflicting reservation. Preserve the existing command and exception classification. Evidence: #409 and #417.
- **Accept when** an invalid storage response before submission yields a retryable preflight result with zero package requests; a foreign operation, existing reservation or lost reply after submission retains recovery protection. Exercise `tests/cytv/test_no_root_observer_diagnostics.py` and `tests/cytv/test_no_root_observer.py`.

### T03 · Give a storage failure one actionable explanation · P1

- [x] **Agent assignment, after T02.** In `cytv/failure_help.py` and `cytv/storage.py`, distinguish insufficient measured space, an unreadable location and a conflicting installer reservation. Use the existing space estimates and supported staging selections. Evidence: #434, #541 and #409.
- **Accept when** real disk exhaustion shows required and available space, an inaccessible location asks for the relevant access or presents an already-supported alternative, and a foreign reservation routes to review. A recognized ramfs result retains its edition-specific behavior. Verify `tests/cytv/test_storage.py` and `tests/cytv/test_no_root_storage_selection.py`.

### T04 · Retry only the check that failed before submission · P0

- [x] **Agent assignment, after T02.** Wire the new classification into `cytv/cli.py`, `cytv/desktop.py` and the result action in `cytv/gui.py`. Keep the chosen device and edition. Offer a read-only repeat of the failed check, followed by the normal setup confirmation once ready.
- **Accept when** a transient error followed by a healthy response needs no trip to Doctor or Uninstall. Cancel leaves the device untouched. A newly discovered pending operation redirects to recovery before any install command. Exercise `tests/cytv/test_desktop_recovery.py` with a command-count assertion.

### T05 · Observe an interrupted package request before resuming · P0

- [x] **Agent assignment, after T02.** Audit the existing terminal evidence in `cytv/no_root_observer.py`, `cytv/recovery_state.py` and `cytv/recovery.py`. Route a lost reply after submission to the existing observation path. Use the original receipt and package readback. Evidence: #378, #529 and #635.
- **Accept when** simulating a disconnect immediately after submission, reopening the installer and resuming produces one total package request. Verified completion advances to configuration. An unknown outcome preserves the record and offers a status check. Replay `tests/cytv/fixtures/no-root-terminal-authority.json` through `tests/cytv/test_no_root_integration.py`.

### T06 · Find the saved profile that owns the unfinished operation · P0

- [x] **Agent assignment, ready now.** Extend the interaction around `require_idle` in `cytv/root_runtime.py` and its caller in `cytv/cli.py`. If another saved edition has the pending action, offer review with that exact saved connection. Revalidate identity on connection. A shared host address alone cannot authorize continuation. Evidence: #643 and #664.
- **Accept when** a Root selection with a pending No-root uninstall can open the correct operation with one choice. A changed identity, multiple plausible profiles or an inaccessible original profile leaves records intact and explains the choice. Verify through `tests/cytv/test_recovery_actions.py`.

### T07 · Recover from a missing local operation file using existing evidence · P1

- [x] **Agent assignment, after T05.** Exercise the supported receipt fallback in `cytv/no_root_cleanup.py` and its presentation in `cytv/recovery.py`. The changed deliverable is a direct next action for eligible owners who lost their local recovery capsule. Reuse the existing matching rules. Evidence: #201 and #635.
- **Accept when** a matching original receipt and TV plan lead to the existing confirmed recovery path, a mismatched receipt refuses, and neither branch asks the owner to find or edit files. Verify `tests/cytv/test_no_root_capsule.py` and `tests/cytv/test_no_root_fence_removal.py`.

### T08 · Recover gracefully when the computer cannot save its local record · P1

- [x] **Agent assignment, ready now.** In `cytv/state.py`, `cytv/failure_help.py` and the installer result screen, distinguish a local disk/permission failure from failed TV storage. Exercise the existing capsule-storage precheck before a device write. Evidence: #201.
- **Accept when** a read-only or full local destination identifies the computer as the affected device, permits retry after correction, and produces zero TV package submissions. A healthy local destination preserves the normal path. Verify `tests/cytv/test_local_recovery_diagnostics.py`.

### T09 · Continue configuration after packages were already verified · P1

- [x] **Agent assignment, after T05.** Follow the configuration-only resume path in `cytv/no_root_observer.py` and `cytv/recovery.py`. Offer to finish configuration when the matching installed bytes and original operation authorize it. Evidence: #529 and #635.
- **Accept when** missing temporary installation archives do not force a verified configuration-only attempt to upload packages again. Changed installed bytes and an outstanding package operation both refuse this shortcut. Verify `tests/cytv/test_no_root_integration.py`.

### T10 · Preserve an intentional Helper stop across recovery · P0

- [x] **Agent assignment, after T05.** Use the recorded stop generation and `cytv/helper_stop.py` when presenting the remaining configuration action. Preserve an owner or emergency stop across a retry, restart and stale completion. Reuse stop-aware behavior already integrated for #495.
- **Accept when** retrying setup after an explicit stop leaves LG Home reachable. The installer describes how to start Helper intentionally. A newer stop wins over an earlier install request. Verify `tests/cytv/test_helper_preflight.py` and `tests/cytv/test_no_root_integration.py`.

### T11 · Make retries safe when two installer windows are open · P0

- [x] **Agent assignment, after T04 and T05.** Exercise two normal setup or recovery entry points for the same saved operation. Use existing device reservations and terminal state. Expose a clear “another operation is active” result to the second window in `cytv/recovery.py` and `cytv/failure_help.py`.
- **Accept when** two concurrent attempts submit once, the second can refresh the result without becoming the writer, and an unrelated TV remains independently usable. Verify the concurrency case in `tests/cytv/test_no_root_observer.py` or its integration fixture.

## B. Finish removal and return control to the owner

### T12 · Explain the exact removal step that failed · P0

- [x] **Agent assignment, ready now.** Map the bounded `cleanup_step`, saved stage and live result from `root-edition/install_driver.py` and `cytv/no_root_cleanup.py` through `cytv/recovery_ui.py`. Distinguish restoring controls, waiting for package removal and cleaning project-owned data. Evidence: #240, #389, #440 and #615.
- **Accept when** two failures that formerly both displayed “Removal is not finished yet” lead to different truthful messages and next actions. Preserve the original and latest failures. Unknown legacy records get neutral wording. Verify `tests/cytv/test_removal_action_ui.py` and `tests/cytv/test_root_recovery_diagnostics.py`.

### T13 · Keep removal as the selected goal through Restore · P0

- [x] **Agent assignment, after T12.** In `cytv/recovery.py` and `cytv/gui.py`, carry the already-confirmed removal goal through the intermediate restoration of LG Home. Continue the same supported uninstall flow from that screen. Evidence: #418, #440 and #469.
- **Accept when** a person who chose Uninstall can go from restored Home to remaining cleanup without the main menu. A person who chose Restore alone ends with LG Home and the applications retained. Cancel before consent sends no removal request. Verify `tests/cytv/test_simple_removal_ui.py`.

### T14 · Recheck the current boot before asking for another restart · P0

- [x] **Agent assignment, after T12.** Build on the stale-restart correction in #704. In `cytv/recovery.py` and `cytv/no_root_cleanup.py`, exercise launch after a saved restart request, a real new boot and a still-running old boot. Surface the current reason from the original operation.
- **Accept when** a verified new boot advances the eligible case; standby or an unreachable device remains unconfirmed. A refresh on the same boot gives an accurate current instruction without rearming the same proof. Verify `tests/cytv/test_clean_removal.py` and `tests/cytv/test_desktop_recovery.py`. Evidence: #472 and #529.

### T15 · Resume observation when the TV comes back online · P0

- [x] **Agent assignment, after T13 and T14.** In the desktop removal screen, use a bounded, cancellable read-only reconnect to the saved device while the owner is waiting after restart. Reuse transport timeouts and identity checks. Present the existing authorized continuation when ready.
- **Accept when** offline → online resumes the correct screen, timeout ends with a manual retry, Cancel stops polling, and rediscovery of a different TV sends no mutations. Verify with deterministic transport fixtures in `tests/cytv/test_desktop_recovery.py`. Evidence: #472.

### T16 · Show completed removal milestones separately · P1

- [x] **Agent assignment, after T12.** In `cytv/recovery_ui.py` and `cytv/gui.py`, display available live evidence for stock control, package absence and remaining cleanup. Include “unknown” for missing observations from older records. Evidence: #440 and #472.
- **Accept when** restored controls plus a still-installed Helper produces a partial result, confirmed removal uses the existing terminal proof, and an accepted launch request alone never says the physical remote works. Verify `tests/cytv/test_recovery_ui.py`.

### T17 · Recognize package removal completed through the TV menu · P1

- [x] **Agent assignment, ready now.** Replay #201 and #438 through `cytv/no_root_cleanup.py`. When the owner manually deleted the apps, use current catalog and startup readback to direct them to the remaining project-owned cleanup. Reuse integrated legacy catalog and stock-surface handling.
- **Accept when** already-absent packages are not submitted for removal again, a surviving project registration is still surfaced, and an unreadable catalog is never interpreted as package absence. Verify `tests/cytv/test_no_root_simple_removal.py`.

### T18 · Handle known harmless residue without unsafe cleanup · P1

- [x] **Agent assignment, ready now.** Audit the actual paths for #152 and #389 in `cytv/no_root_cleanup.py` and `root-edition/cleanup_tail.js`. Reuse shipped handling of protected empty Helper directories and recognized generated Python cache files. Surface which outcome was proven.
- **Accept when** each known harmless fixture ends with the right retained/removed result, an unexpected file or changed ownership blocks the affected cleanup, and an untouched sibling is preserved. Verify `tests/cytv/test_clean_removal.py` and `root-edition/tests/test_clean_removal.py`. Extend acceptance only for a separately evidenced case.

### T19 · Keep unconfirmed LG package removal attached to the original request · P0

- [x] **Agent assignment, after T12.** In `cytv/no_root_cleanup.py`, trace timeout, terminal rejection, already absent and accepted-but-unobserved replies. Reuse the existing package monitor to offer a status refresh. Evidence: #152 and #472.
- **Accept when** a delayed terminal reply completes the original request, a genuine rejection names the blocked package operation, and repeated refresh sends zero duplicate removals. Verify `tests/cytv/test_no_root_fence_removal.py`.

### T20 · Handle older stock Home layouts during removal · P1

- [x] **Agent assignment, ready now.** Trace `restore_stock_home` in `cytv/no_root_cleanup.py` against the existing older-TV case where LG Home is not a separately launchable app. Make the verified legacy destination understandable in the result. Evidence: #283 and #438.
- **Accept when** the supported app-not-found case with confirmed stock foreground can continue, an unrelated foreground or disconnected TV stays unverified, and users see the stock surface actually observed. Verify `tests/cytv/test_clean_removal.py`.

### T21 · Explain private cleanup when higher access is actually needed · P1

- [x] **Agent assignment, after T06 and T12.** Use `root_removal_profile` in `cytv/recovery_ui.py` and the existing connect action in `cytv/gui.py`. Offer the matching saved Root connection only for a verified access requirement. Evidence: #240 and #643.
- **Accept when** an eligible rooted TV can continue using its saved connection, a genuinely unrooted owner receives an accurate remaining limitation, and a retryable network interruption does not ask for root credentials. Verify `tests/cytv/test_removal_action_ui.py`.

### T22 · Make a verified clean state usable for reinstall · P1

- [x] **Agent assignment, after T13 and T16.** Build on #708 in `cytv/recovery.py`, `cytv/root_gate.py` and the desktop result action. Offer fresh setup on the same TV only after verified cleanup and only when the user has chosen reinstall or explicitly selects that next action. Evidence: #615 and #678.
- **Accept when** verified clean offers setup with the right edition and connection, a partial cleanup stays on recovery, and a plain uninstall can finish and exit. Confirm preference-loss consent where applicable. Verify `tests/cytv/test_root_reinstallation.py` and `tests/cytv/test_clean_reinstall.py`.

## C. Get a usable installation on the first attempt

### T23 · Let No-root continue when only the HDMI listing is unavailable · P1

- [x] **Agent assignment, ready now.** Change `SSAP.inventory` in `cytv/tv.py` for fresh setups that have authenticated pairing and a usable application list. Treat a definitive endpoint-specific refusal or an unusable optional input payload as partial inventory. Keep a transport interruption, lost pairing or a failed application query distinct. Preserve existing saved input choices on update, or limit the fallback to fresh setup until preservation is verified.
- **Accept when** a replay with one valid application passes for an empty input list, a denied optional endpoint and a missing devices field; the last two display that inputs were unavailable. Lost connection still blocks. Verify `tests/cytv/test_tv.py`. The published Root fallback in `cytv/operations.py` is a reference; #389 and #440 were Root cases.

### T24 · Recover from one malformed optional catalog entry · P2

- [x] **Agent assignment, after T23.** In `cytv/tv.py`, isolate one invalid optional display entry in an otherwise usable bounded catalog. Only adopt this change if the installed Helper can retain the correct app IDs and the remaining launcher choices are usable. Keep the inventory size limits. Never treat an uncertain package inventory as authority for removal.
- **Accept when** valid entries remain usable, skipped entries are counted without names in diagnostics, an entirely unusable list gives an actionable error, and update preserves existing user choices. Verify `tests/cytv/test_tv.py` and the app-ID handling in `cytv/operations.py`.

### T25 · Offer the verified No-root alternative on Root-only incompatibility · P1

- [x] **Agent assignment, ready now.** Trace the published alternative-edition chooser in `cytv/root_runtime.py`, `cytv/root_capabilities.py`, `cytv/cli.py` and `Installer.check_no_root_alternative`. Extend only an evidenced, deterministic Root-only refusal for which an independent No-root preflight succeeds. Start with #519, #587 and #410.
- **Accept when** a supported alternative is offered using the existing Root SSH connection, the owner explicitly chooses it, and no Developer Mode installation is required on that rooted TV. Unknown capability, active recovery or a failed No-root preflight gives no unsafe offer. Verify `tests/cytv/test_root_preflight.py`.

### T26 · Explain Python prerequisites as a single decision · P1

- [x] **Agent assignment, ready now.** In the Root preflight in `cytv/operations.py` and `cytv/python_runtime.py`, group dependent Python checks in the user-facing result. Distinguish an eligible private runtime, a host download/cache failure and a TV platform that cannot use this runtime. Keep individual results in the standard export. Evidence: #160, #200 and #410.
- **Accept when** a missing interpreter does not ask the owner to fix four modules individually, an invalid cache gives the relevant local action, and an unverified runtime stops before activation. Preserve existing provisioning and integrity checks. Verify `tests/cytv/test_python_preflight.py`.

### T27 · Make an unsupported experimental Home backend an understandable endpoint · P1

- [x] **Agent assignment, after T25.** In `cytv/root_capabilities.py`, `cytv/failure_help.py` and setup results, explain which Home capability failed, whether anything was installed, and which tested alternative is available. Reuse the offline legacy firmware evidence for #383 and the retained-state evidence for #615.
- **Accept when** unsupported hardware is clearly distinguished from unreadable runtime information; an unknown capability can be rechecked, while a known unsupported setup does not encourage repeating the same install. Verify `tests/cytv/test_root_preflight.py` on both paths.

### T28 · Catch an incomplete desktop installer before asking the owner to use the TV · P1

- [x] **Agent assignment, ready now.** Use package metadata and the existing graphics/payload validation in `cytv/graphics.py` and `cytv/package.py` to identify a missing required distribution resource at the earliest point where its absence is conclusive. Reuse existing startup validation if it already covers the case. Evidence: #270 and #271.
- **Accept when** a broken host distribution asks for the complete installer and sends no TV write; an edition-specific optional resource has no effect on other editions. Verify the affected packaged entry point and `tests/cytv/test_graphics.py`.

### T29 · Separate unreachable TV, rejected SSH credentials and failed TV pairing · P1

- [x] **Agent assignment, ready now.** Trace errors through `cytv/transport.py`, `cytv/tv.py` and `cytv/failure_help.py`. Route each to the appropriate existing action with the right TV, edition and saved connection. Keep an on-screen pairing request open long enough to answer and present a recoverable refusal distinctly. Evidence: #164, #217, #244 and #283.
- **Accept when** refusal before SSH, authentication failure after SSH and SSAP pairing refusal generate three different actions. None recommends removal. A connection interruption during an existing operation preserves it. Verify `tests/cytv/test_ssh_connection_diagnostics.py` and `tests/cytv/test_tv.py`.

### T30 · Reconnect after a factory reset without carrying a stale uninstall forward · P1

- [x] **Agent assignment, after T06 and T29.** Exercise the existing reset flow in `cytv/no_root_reconnect.py`, `cytv/ssh_identity_review.py` and the connection screen. Offer it only when the current access mode and prior state support the explicit reset workflow. Evidence: #368 and #664.
- **Accept when** the owner can explicitly establish the new identity, old records are retained, and the stale operation cannot mutate the newly paired device. A changed identity without confirmed reset stops. Verify `tests/cytv/test_no_root_reconnect.py` and `tests/cytv/test_state_check_identity.py`.

### T31 · Give a specific route when another Home replacement is present · P1

- [x] **Agent assignment, after T25.** Use `cytv/home_handoff.py` and `cytv/root_capabilities.py` to describe the existing supported handoff or the specific owner action needed for a recognized conflict. Preserve the original failure through retry. Evidence: #454 and #519.
- **Accept when** an eligible handoff is offered once, a declined handoff keeps the existing Home in place, and an unrecognized third-party integration is never removed. The installer rechecks stock routing before continuing. Verify through the Root preflight and clean-reinstall suites.

### T32 · Keep “installed” separate from “Home works” in the completion screen · P0

- [x] **Agent assignment, ready now.** Use the existing fields in `cytv/outcomes.py` rather than defining a second success model. In desktop results show packages, launcher startup and the observed Home-button outcome. Evidence: #389, #599 and #647.
- **Accept when** read-back packages plus untested physical Home shows both facts, an acknowledged app launch cannot claim working Home, and a verified package install with failed Home offers a routing check rather than reinstall. Verify `tests/cytv/test_gui.py` with all three outcomes.

### T33 · Guide the owner through one useful Home-button check · P1

- [x] **Agent assignment, after T32.** Use the existing Home diagnostic in `cytv/diagnostics.py` and the outcome fields in `cytv/outcomes.py`. Ask for one physical press only when that input is the missing evidence. Explain the starting screen, expected destination and what each observed destination means. Evidence: #207, #389 and #687.
- **Accept when** LG Home, CYTV Home and no visible response each lead to a different truthful next step. A network-remote result and a skipped check cannot become a physical-button success. Preserve existing emergency stop. Verify `tests/cytv/test_home_diagnostics.py`.

### T34 · Reuse a successful connection check for the next setup step · P1

- [x] **Agent assignment, ready now.** Audit #704 in `cytv/gui.py`, `cytv/desktop.py` and the integration checkout before making edits. Exercise a new install, a working setup and a pending recovery after Doctor. Change only a remaining real dead end or hand off the matching existing evidence.
- **Accept when** the journey reuses the selected TV, edition and connection; an existing pending operation takes priority; cancelling after Doctor leaves the TV unchanged. Verify `tests/cytv/test_desktop_recovery.py`. A successful connection check alone cannot mark installation complete.

## D. Keep self-service available on every installer surface

### T35 · Bring stage-aware recovery actions to the Android installer · P1

- [x] **Agent assignment, after T04, T05 and T12.** Carry the shared Python reason and permitted action through `android/app/src/main/python/android_bridge.py` into `android/app/src/main/assets/ui/app.js`. Reuse the existing recovery-plan callback and localized action labels.
- **Accept when** the same three synthetic plans produce preflight retry, observe submitted request and cleanup review on desktop and Android. An old bridge event with missing fields gets a safe status action. Verify `android/tests/recovery-action.cjs` and `android/tests/test_bridge.py`.

### T36 · Restore the correct Android removal screen after backgrounding · P1

- [x] **Agent assignment, after T14 and T35.** Exercise the activity/service lifecycle in `android/app/src/main/java/com/cleanyourtv/android/InstallerService.kt` and the UI restore path. Reattach to the existing operation or observe it again when Android recreates the screen.
- **Accept when** backgrounding during removal, rotation and reconnect after TV restart never submit a second uninstall. A stale restart event prompts a fresh read. Verify `android/tests/restart-result.cjs`, `android/tests/simple-removal.cjs` and the existing emulator operation case for any changed native behavior.

### T37 · Make noninteractive CLI outcomes usable by callers · P1

- [x] **Agent assignment, after T02, T05 and T12.** Preserve the CLI's existing output and exit conventions. Extend its structured result through `cytv/cli.py`, `cytv/terminal.py` and the shared recovery projection so callers can distinguish a retryable check, an operation waiting for evidence, verified completion and required owner input.
- **Accept when** a noninteractive run never waits for an invisible prompt, a status check performs no mutation, and legacy callers still consume established fields. Verify `tests/cytv/test_clean_removal_cli.py` and `tests/cytv/test_terminal.py`.

### T38 · Keep the primary recovery action visible in translated desktop screens · P1

- [x] **Agent assignment, after T04, T13 and T32.** In `cytv/gui.py`, check minimum-window layout and keyboard focus for the specific retry, resume, report and completed states. Reuse the Qt layout checks already used for #704. Each behavior owner supplies its translated strings when implementing its card.
- **Accept when** at the supported minimum window size the recommended action and diagnostic export are reachable by keyboard and readable in the longest supported translations; Enter does not trigger a destructive secondary action. Verify `tests/cytv/test_gui.py` and `tests/cytv/test_i18n.py`.

### T39 · Replace the manual troubleshooting detour with a short recovery guide · P2

- [x] **Agent assignment, after T13, T16 and T32.** Update `docs/RECOVERY.md`, `docs/DESKTOP_INSTALL.md` and the affected practical passages in `docs/i18n/`. Reconcile behavior owners' in-place edits. Use the actual button labels for unfinished install, restored Home with apps remaining, and completed removal. Keep existing anchors.
- **Accept when** following each example from its named screen reaches the expected result without a shell command, hunting for a saved record or opening GitHub. Record any edition-specific exception in the corresponding branch of the instructions.

## E. Make a genuine support case actionable on the first message

### T40 · Prepare an accurate issue draft from the first failure · P1

- [x] **Agent assignment, after T02 and T12.** In `cytv/diagnostics.py` and `cytv/diagnostic_context.py`, generate a short editable summary from the existing allowlisted export: goal, edition, installer version, observed phase, reason and last verified outcome. Generate a useful title. Prefer the original failure for the same operation and label a later observation separately. Evidence: #417 and #418.
- **Accept when** rerunning Doctor does not overwrite the original install failure, an old report with no cause says “unknown”, and the output includes no addresses, credentials, inventories, paths or raw exception. Verify `tests/cytv/test_diagnostics.py` and `tests/cytv/test_diagnostic_context.py`.

### T41 · Make reporting a single optional action after a failed desktop journey · P1

- [x] **Agent assignment, after T40.** Use the shared draft in `cytv/gui.py` and `cytv/terminal.py`. Let the owner inspect/copy it, open the correct installer issue form, and attach the existing saved diagnostic. Keep draft preparation local and leave submission to the owner.
- **Accept when** the form opens with the correct category and a usable title, cancelling sends nothing, the report remains available offline, and preparing it triggers zero TV checks. Test missing browser, missing report and non-ASCII titles in the desktop and console fixtures.

### T42 · Shorten the installer issue form when a report already exists · P1

- [x] **Agent assignment, after T40.** In `.github/ISSUE_TEMPLATE/cytv.yml` and `docs/FEEDBACK.md`, ask what the owner was trying to do, what is visible now and for the existing saved diagnostic. Ask for missing edition, version or platform only when unavailable from that report. Preserve a route for a TV that cannot connect and an installer that cannot export.
- **Accept when** a report-backed owner need not retype facts already captured; a person without an export can still submit a useful issue; neither path asks them to repeat installation. Validate the GitHub form structure and walk both examples through the form text.

### T43 · Make the same support draft available on Android · P2

- [x] **Agent assignment, after T35, T40 and T42.** Reuse the shared sanitized summary and the existing report-ready event in `android/app/src/main/python/android_bridge.py` and `android/app/src/main/assets/ui/app.js`. Offer the existing file using the supported Android export/share interaction.
- **Accept when** an Android owner can identify the failed step and deliberately share the existing report; cancel, offline use or lack of a share target never repeats the TV operation or sends the report. Verify the Android bridge and UI fixtures.

### T44 · Replace a repeated support question with a targeted local check · P1

- [x] **Agent assignment, after T12 and T40.** Use #389 as the bounded case: after successful removal/reinstall, users were asked to inspect a retained Python inventory to explain why Home could not be changed. Compare current `cytv/root_install_recovery.py`, `cytv/diagnostic_context.py` and the existing installed inventory reader. Surface the missing distinction in normal diagnostics using bounded categories and counts only.
- **Accept when** matching inventory, known generated entries, unexpected entries and unreadable inventory remain distinguishable. Use read-only synthetic states. The owner can save the standard report without running shell commands, and the report exposes neither filenames from the device nor raw paths. Confirm it does not relax cleanup or activation authority.

### T45 · Replay difficult user journeys from the installer's normal entry points · P0

- [x] **Agent assignment, after T04, T05, T13, T14 and T32.** Link the focused regression results first. Use the existing installer fixtures to cover only the gaps across steps: preflight failure → retry; lost reply → original package completion; Restore → remaining uninstall; successful install → physical Home still opens LG Home. Use #409, #529, #440 and #389 as scenario sources. Publish only synthetic fixtures.
- **Accept when** each journey reaches a named user-visible outcome with zero duplicate package submissions, zero accidental uninstalls and no requirement to consult a maintainer. Keep uncertainty visible for the physical Home case. Record the normal entry point and final state for each case in the integration PR.

### T46 · Evaluate whether the changes reduced repeat issues · P1

- [ ] **Agent assignment, after T01 and public availability of a named batch.** Perform the time-bounded comparison below using public evidence. Separate already-open long threads, new reports on older installers, new reports on the changed installer and unknown versions. Give a continue/adjust decision for each shipped behavior.
- **Accept when** the report includes counts, denominators, unresolved cases, missing exposure information and one next decision tied to an actual repeat cause. File further work only through normal maintainer prioritization. This is a one-time analysis when the observation window exists.

## Measurement and stopping decisions

Use the 14 complete days before publication and the first 14 complete days after publication for the first batch. Record dates in UTC and the installer versions delivered. For slower adoption, label the initial comparison inconclusive and show the actual sample size. Do not infer prevented issues from the number of closed tickets.

| Measure | Definition | How to use it |
| --- | --- | --- |
| New issues for targeted installer causes | Count unique new external installation/removal threads in each targeted family. Also show their share of all new external installation/removal threads in the same window; list unknown versions separately. | A falling count and share with comparable adoption supports continuing the intervention. Downloads, if shown, are only a rough exposure proxy. |
| Repeat visits to the TV | For each eligible thread count distinct maintainer requests that require the owner to perform another action on the TV or installer. Report median and number requiring two or more visits. | A repeated request for the same evidence is a candidate for the next self-service change. Group a single compatible set of actions as one visit. |
| Achieved original goal | Install, reinstall and uninstall have separate denominators. Count owner-confirmed, partially achieved, failed and unknown. Track verified physical Home only when the original goal included it. | Lower issue volume alongside worse or unknown outcomes requires inspecting the open cases. A successful Doctor run or a silent closure cannot count as success. |
| Report usefulness | Count how many first posts on the affected installer allow a maintainer to identify phase and next action without asking for a second diagnostic. Retain the number with no report. | Tune the draft and the failing screen if the same missing fact appears repeatedly. Preserve the ability to report unknown defects. |
| Harm from a relaxation | Track duplicate package mutations, wrong-device continuation, unintended changes after Restore/Cancel, loss of stock Home, emergency-stop regression or lost preferences. | Any confirmed occurrence warrants stopping the affected shortcut and restoring its previous guard while investigating. |

**First review decision.** Prefer the cards addressing the remaining high-volume cause after the first shipped batch. Defer narrower tasks if their existing implementation already passes the stated cases or the support burden disappears. Owners should be able to report a real problem as easily as before.

## Agent handoff · 18 November 2026

All 46 cards were assigned to separate GPT-6.2 Sol agents with high reasoning. The changes are saved locally on `codex/installer-outcomes`. The selected public release candidate and deployed installers have separate acceptance records.

Forty-three cards contributed commits, including documentation, tests and the issue baseline. T18 verified the existing protected-directory and Python-cache behavior. T45 replayed four owner journeys. T46 is open until a named release containing these changes has 14 complete UTC days of follow-up. The [support baseline](../../history/2026-11-18-installer-support-baseline.md) records 60 external threads, 142 requests to revisit the TV or installer and 24 threads with at least two such requests. Only 17 owners confirmed the original goal by the cutoff. The baseline predates this batch.

| Card | Local integration or observed disposition |
| --- | --- |
| T01 | `7adba42c` |
| T02 | `99546c6a` |
| T03 | `01e6dd9e` |
| T04 | `91ec9324` |
| T05 | `4a4a6000` |
| T06 | `36f2baa4` |
| T07 | `6d534a35` |
| T08 | `29ceab93` |
| T09 | `26b2fd75` |
| T10 | `baacc8e3` |
| T11 | `85e93df9` |
| T12 | `5b7c0380` |
| T13 | `58a4c40a` |
| T14 | `0b1d577f` |
| T15 | `242028c5` |
| T16 | `87e35b27` |
| T17 | `298b171f` |
| T18 | Existing behavior verified at `85e93df9` |
| T19 | `2cacffa6` |
| T20 | `ea5228d2` |
| T21 | `3a76f0d0` |
| T22 | `5e701ea7` |
| T23 | `3a279619` |
| T24 | `08d0b869` |
| T25 | `ee786cd7` |
| T26 | `14bcef54` |
| T27 | `0aaea2c4` |
| T28 | `73ef2813` |
| T29 | `8e6f9a03` |
| T30 | `7d9e0b78` |
| T31 | `98e77ae3` |
| T32 | `8ffdd2ab` |
| T33 | `1e8316d0` |
| T34 | `b0678962` |
| T35 | `9356e32d` |
| T36 | `110ca143` |
| T37 | `cf43ed64` |
| T38 | `445f8078` |
| T39 | `a605365a`, `986a8a5b` |
| T40 | `693d8761` |
| T41 | `aca3ca29` |
| T42 | `598e6251` |
| T43 | `26aac91c` |
| T44 | `8449d51f` |
| T45 | Journey replay at `8e6f9a03` and after T33/T38 |
| T46 | Waiting for publication of the changed batch and the observation window |

**Combined checks.** The host run covering CLI, terminal, preflight, storage, catalog, recovery and Home reported 206 passes. The separate report, passive status, outcome and package concurrency run reported 101 passes and one skip. The combined Qt, desktop recovery, simple removal, translations and recovery UI run reported 156 passes after removing an unnecessary Root inventory read while waiting for restart. These runs overlap. A Windows lock fixture and initialization error path were also corrected and verified together with the two-window scenario. Android action/replay checks used Python fixtures and browser tests. The guides site built successfully, and rendered recovery labels and anchors were checked across all 13 languages. No physical TV, newly signed desktop installer, or freshly built Android APK was verified in this batch.

**Owner journeys.** A storage retry and a Home-routing complaint each submitted one Helper and one Launcher install and zero removals in the simulated desktop journey. The final Home action reused the recorded owner answer and report. Reopening after a lost package reply did not duplicate the original request. Continuing Restore after explicit Uninstall reused one removal intent. Standalone Restore and cancellation retained the applications. Physical remote input was simulated.

**Remaining verification.** Some broader agent runs had intermittent No-root fixture failures that passed when isolated, and two Android browser checks also failed on the comparison base. Native platform behavior, the full frozen-candidate suite, and public delivery are outside this local acceptance. Compare the 14 complete UTC days before publication with the 14 complete days after it. Count new-version, older-version and unknown-version reports separately and keep already-open threads separate. Evaluate support volume together with repeat visits and confirmed outcomes.
