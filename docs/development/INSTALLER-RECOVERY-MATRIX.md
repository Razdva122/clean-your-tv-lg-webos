# Installer recovery and simple removal matrix

The current unpublished removal candidate follows stop/delete → full restart →
final sweep. It removes known project items that exist and skips absent items,
including after partial installation. Earlier install success is not a removal
prerequisite. A lost connection offers Try again on the same approved goal and
saved target. Actual OS access denial and busy work get their own instructions.
No automatic TV reboot or hidden retry runs. [User instructions](../RECOVERY.md).

This matrix describes source/UI coverage. Simulated SSH replies, local processes
and browser events are not physical TV or vendor acceptance. Final success needs
`removed: true` and `verified_clean: true` from the backend; a restart-required
or missing/false proof result must stay neutral.

| Boundary or observation | Expected user behavior | Runnable evidence / current limit |
| --- | --- | --- |
| Connection lost during removal | Clear connection error and Try again, same uninstall/TV/port | `tests.cytv.test_simple_removal_ui.SimpleRemovalUITests.test_connection_loss_try_again_runs_same_uninstall_target`; `android/tests/simple-removal.cjs` |
| Retry after the original approval | Same durable goal, no recovery wizard, no second initial confirmation | `test_actual_cli_retry_reuses_approved_goal_without_second_confirmation` in the same Qt class; RED on baseline `6416c005` until the simple CLI provider lands |
| Partial setup or missing app/files | Delete present known items, skip absent items; old pending does not force installation | Root/No-root simple provider filesystem tests and combined UI orchestration are required before candidate freeze; UI mocks do not prove deletion |
| Full restart requested | Explain power disconnect/reconnect and wait for the network, then Try again | `test_restart_required_is_neutral_and_explains_full_power_restart`; Android simple-removal cases in all 13 languages and both editions |
| Standby, Quick Start or same boot | Still pending; only a real boot change permits final sweep | Backend boot-ID tests are required. UI only tests the neutral pending/result contract |
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

Still pending: combined Root/No-root provider integration, current boot/readback
contracts on supported firmware, complete candidate suites/builds, and physical
Home, normal keys, sound, standby, cold boot, OTA and rollback acceptance. Keep
stable downloads distinct from candidate source instructions. Do not publish
another user's results or diagnostics without the required approval.
