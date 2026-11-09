# Installer recovery and simple removal matrix

The published v1.13.0 removal flow follows stop/delete → full restart →
final sweep. It removes known project items that exist and skips absent items,
including after partial installation. Earlier install success is not a removal
prerequisite. A lost connection offers Try again on the same approved goal and
saved target. Actual OS access denial and busy work get their own instructions.
No automatic TV reboot or hidden retry runs. [User instructions](../RECOVERY.md).

The released continuation improvements add a narrow exception for an initially empty No-root
TV: two current absence/process checks, no inherited operation and confirmed
input-shortcut cleanup permit immediate completion. Unreadable/anonymous/live
processes retain the restart path. Current connection help preserves the saved
endpoint and host pin while allowing an explicitly selected Root sign-in key.
Helper is checked before No-root pairing; its stop gesture and recheck stay in
the same setup. Legacy Root Updater remnants offer separately confirmed full
removal before a new inventory. EIM list rejection falls back to the fixed own
shortcut delete; failed shortcut cleanup is deferred until safe package cleanup
finishes, and still blocks verified-clean. These published changes do not establish reporter-device acceptance; see [current maintenance guidance](../MAINTENANCE.md#unreleased-removal-and-reinstallation-continuation).

This matrix describes source/UI coverage. Simulated SSH replies, local processes
and browser events are not physical TV or vendor acceptance. Final success needs
`removed: true` and `verified_clean: true` from the backend; a restart-required
or missing/false proof result must stay neutral.

| Boundary or observation | Expected user behavior | Runnable evidence / current limit |
| --- | --- | --- |
| Connection lost during removal | Clear connection error and Try again, same uninstall/TV/port | `tests.cytv.test_simple_removal_ui.SimpleRemovalUITests.test_connection_loss_try_again_runs_same_uninstall_target`; `android/tests/simple-removal.cjs` |
| Retry after the original approval | Same durable goal, no recovery wizard, no second initial confirmation | `test_actual_cli_retry_reuses_approved_goal_without_second_confirmation` in the same Qt class; passes in the 72-case combined host run at `c419a3a8` |
| Partial setup or missing app/files | Delete present known items, skip absent items; old pending does not force installation | `test_simple_removal` / `test_cleanup_tail` in Root tests and `tests.cytv.test_no_root_simple_removal`: real temporary filesystems with modeled package/device replies; [source results and limits](../history/2026-11-06-practical-clean-removal.md) |
| Older No-root stock screen without launchable Home (next installer) | Only exact app-not-found launch refusal admits fixed LG stock foreground readback; otherwise launch fixed Live TV and verify. Package absence/restart remain required | `test_no_root_simple_removal` covers installed packages, manually removed packages, delayed foreground, wrong codes, malformed readback and connection loss |
| Retained C1 schema-1 removal (next installer) | Current compositor installer carries an authenticated mount recovery executor, used only for old restore; fresh setup still selects compositor | `test_root_c1_payload` validates generated bundles, actual recovery selection, tampering and fresh installed-file exclusion |
| BX final cleanup and completed external result (next installer) | Async bounded Node children keep stdin open; complete Activity inventory required. Revalidate matching completed operation under original locks without another destructive sweep | `test_cleanup_tail`, `test_cleanup_tail_children`, `test_clean_removal` and `test_update_luna`; [source evidence and device limits](../history/2026-11-09-installer-removal-four-issues.md) |
| Full restart requested | Explain power disconnect/reconnect and wait for the network, then Try again | `test_restart_required_is_neutral_and_explains_full_power_restart`; Android simple-removal cases in all 13 languages and both editions |
| Standby or unchanged boot lifetime | Still pending; a verified full restart is required | Root reuses the existing snapshot-aware kernel/session identity; No-root accepts a changed kernel UUID or disappearance of its previously captured per-goal volatile marker. Legacy baselines require fresh capture and another restart. `test_simple_removal`, `test_cleanup_tail` and `test_no_root_simple_removal` cover unchanged sessions, reused UUIDs, tampering and interrupted continuation. A modeled boot change is not physical cold-boot acceptance |
| Verified Root removal → normal setup | Revalidate current absence under the original mutex; preserve old fences and resume the same successor request after an interrupted move | `tests.cytv.test_clean_reinstall` and `test_clean_removal.CoordinatorCleanRemoval`; [source record and limitations](../history/2026-11-07-clean-reinstall.md) |
| Explicit Root reinstall / failed profile activation (unreleased, #355) | Validate the selected replacement before full cleanup; require verified clean removal before a fresh install. Compare actual support/runtime with selected bundle before maintenance or enable; explain only fresh allowlisted health refusals | `test_root_reinstallation`, `test_root_runtime_contract`, `test_root_action_failure`, Root `test_install_driver`; physical C2 acceptance remains pending |
| Verified full removal → Root or No-root (published) | Retire the completed destructive lease, keep old retries read-only, and bind a Root-SSH No-root successor under the original locks; recover incomplete goals before new setup | `test_root_no_root_handoff`, `test_clean_removal` and `test_cleanup_tail`; [contract and host/device limits](CLEAN-REMOVAL-REINSTALLATION.md) |
| Root removal catalog denied or timed out | Read the ordinary application catalog once; malformed replies and two unavailable catalogs remain blocked. Keep fixed-path sweeping/absence, registration and routing verification | `test_clean_removal` catalog cases and `test_cleanup_tail` fallback/residue checks; [source record](../history/2026-11-07-issue240-removal-catalog.md) |
| Root removal without `systemprofile` (published) | Admit only the exact missing-service reply, stock LG Home in Settings Service, and lock-held pre-restore proof that no current or backed-up routing inverse/backend exists. Preserve old fences, restoration, package absence and restart checks; ACL/timeouts, malformed replies, foreign Home and routing evidence still block | `test_clean_removal` webOS 5 cases, `test_cleanup_tail` stock-settings cases and `test_update_luna` exact-reply cases; [source scope and limits](../history/2026-11-07-issue240-profileless-removal.md) |
| Never-activated Root removal without Home APIs (published) | Use the lock-held original pre-activation stage, preserved routing inverse and current routing-path absence to prove CYTV never changed Home. Recheck before each destructive continuation and in the final Node process; retain full restart/package/private-data verification. New routing evidence blocks cleanup before deletion | `test_clean_removal` never-activated/never-applied cases and `test_cleanup_tail` untouched-Home cases; [source verification and limits](../history/2026-11-08-issue101-untouched-home-removal.md) |
| Retried Root cleanup fails differently | Keep the first failure and export the latest fixed call/reason/code and stage separately | `test_retry_keeps_first_and_latest_failure_separate`; `test_diagnostic_context` exported-report privacy regression |
| Root catalog access | Read both fixed catalogs directly over SSH without Node subprocesses; reuse the current local icon/normalization reader. A failed optional input query warns and keeps valid apps, while failed/empty app reads and connection loss still block. Partial inventory stays unverified; no SSAP pairing or new permission | Actual Node program/reader with `child_process` loading forbidden, bounded SSH replies and CLI/checklist regressions in `tests.cytv.test_clean_reinstall`; No-root keeps the existing SSAP path |
| Root inventory read fails (unreleased, #397) | Retain separate fixed application/input failure reasons and bounded Luna codes; no raw replies or app list in diagnostics. Required apps still block, optional inputs still warn | Real Node stdin reader/host and exported-report privacy cases in `tests.cytv.test_clean_reinstall` / `test_diagnostic_context`; real child-process classifications in `tests/apps/root-inventory-diagnostics.cjs` |
| Final result flags | Only both true flags with clean-removal disposition can show completion | `test_explicit_remove_needs_removed_and_verified_clean`; `test_explicit_uninstall_requires_clean_disposition_and_true_proof` in `tests.cytv.test_desktop_recovery`; `android/tests/removal-result.cjs` and `simple-removal.cjs` |
| Actual busy/access-denied/package failure | Wait and retry, restore required Root access, or inspect error and retry | Bounded shared copy in `cytv/recovery_ui.py`; Android bridge/browser cases in all 13 locales. Actual denial classification belongs the providers |
| Unknown or structured service code | Fixed human text, raw/private values excluded from main UI | `tests.cytv.test_recovery_ui`; `android.tests.test_bridge.BridgeTests.test_cleanup_details_are_localized_and_never_forward_unknown_codes` |
| Typed password/key/Developer Mode prompt | Existing sign-in and saved keys preserved in every language | `tests.cytv.test_i18n.LanguageTests.test_desktop_typed_credentials_survive_all_localized_labels`; `android.tests.test_root_recovery.AndroidRootRecoveryTests.test_passive_authentication_keeps_key_and_root_types_in_every_locale` |
| Original failure and later connection/removal error | Original unknown cause stays unknown; current blocker is separate | `tests.cytv.test_desktop_recovery.DesktopRecoveryTests.test_no_root_uninstall_connection_loss_keeps_intent_before_device_work`; existing diagnostic-lineage tests |
| Root Home-off setup and other recovery goals | Preserve achieved LG Home/off goal and separate physical observations | `test_root_home_off_confirmation_archives_original_and_completes`; `android/tests/recovery-journey.cjs` and `maintenance.cjs` |

The prior dated [UI source record](../history/2026-11-06-installer-recovery-ui-source-verification.md)
retains the earlier design/review evidence. Advanced lifecycle helpers/global
coordination from later experimental branches are outside this simple candidate.
Ordinary install-observer tests remain useful for their own installation flow;
they do not establish removal prerequisites or retroactively recover a reporter's
original cause. No removal result on #201/#307/#359 or any other reporter's TV is
claimed, and another installation is not required to populate this matrix.

Focused provider/UI integration and independent scoped reviews are recorded in the
[practical removal source checkpoint](../history/2026-11-06-practical-clean-removal.md).
The initial broader run exposed old fixtures and missing translations; all five
failed cytv modules passed their 74-case affected rerun at `aad6b110`. The producer
fix passed 49 focused cases at `a827d1df`; Homebrew continuation passed six cases
with real authenticated snapshots. Independent integration and correction reviews
approved these changes. The full Android Python suite passed 43 cases. Complete
Root/PR checks remain pending at this source checkpoint.
Still pending: current boot/readback contracts on supported
firmware, complete candidate suites/builds, and physical
Home, normal keys, sound, standby, cold boot, OTA and rollback acceptance. Keep
stable downloads distinct from candidate source instructions. Do not publish
another user's results or diagnostics without the required approval.
