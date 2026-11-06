# Installer recovery failure-injection matrix

This is maintained source coverage for the next unpublished candidate. Simulated
TV replies and local processes establish only the stated software contract, not
device compatibility, vendor persistence or owner recovery. Keep historical
device acceptance with its exact release artifacts. The original failure and a
later inspection failure are separate evidence; neither should overwrite the
other. [User flow and limits](../RECOVERY.md).

| Injected boundary | Expected result | Runnable evidence |
| --- | --- | --- |
| Default retain / decline inspection | Original receipt preserved; review, no installation success | `tests.cytv.test_desktop_recovery.DesktopRecoveryTests.test_root_menu_defaults_to_retaining_receipt_without_activation`; `test_declining_recovery_retains_receipt_and_does_not_offer_automatic_retry`; `android/tests/recovery-journey.cjs` |
| Cancel root authentication | Original profile, host pin and receipt preserved; cancelled; no TV mutation | `tests.cytv.test_desktop_recovery.DesktopRecoveryTests.test_cancelled_recovery_auth_keeps_original_records_and_shows_cancelled`; Android journey `cancelled-auth` |
| Localized hidden credentials | Credential type survives presentation in all 13 languages; no password guessing from prose | `tests.cytv.test_i18n.LanguageTests.test_desktop_typed_credentials_survive_all_localized_labels`; `android.tests.test_root_recovery.AndroidRootRecoveryTests.test_passive_authentication_keeps_key_and_root_types_in_every_locale` |
| Eligible Root Home-off completion | Actual chosen LG Home goal wins generic Clean Home checklist; untested physical observations stay visible | `tests.cytv.test_desktop_recovery.DesktopRecoveryTests.test_root_home_off_confirmation_archives_original_and_completes`; Android journeys and `android/tests/maintenance.cjs` |
| Running Root worker / unsupported legacy package status | Retain evidence, precise blocker, no replay or green completion | Android journeys `running-worker` / `legacy-unknown`; `tests.cytv.test_desktop_recovery.DesktopRecoveryTests.test_failed_recovery_offers_original_failure_report_without_retry_or_install` |
| Host lost after original Helper terminal | Continue original Home/configuration bytes, never resubmit Helper or adopt new versions | `tests.cytv.test_no_root_integration.OriginalOperationIntegration.test_host_loss_resumes_only_original_home_and_configuration_after_upgrade`; actual detached-process continuation in Android journey |
| Lost config or restore acknowledgement | Unknown remains blocked, even if current inventory looks desired | `tests.cytv.test_no_root_integration.OriginalOperationIntegration.test_copied_capsule_cannot_duplicate_delayed_configuration`; `test_removal_transport_loss_cannot_be_sealed_by_empty_eim_inventory` |
| Changed capsule, source or configuration | No continuation; no private-byte disclosure | `tests.cytv.test_no_root_integration.OriginalOperationIntegration.test_changed_capsule_or_current_files_never_submit_home`; `test_changed_trusted_reader_refuses_original_source_without_remote_effects`; `tests.cytv.test_no_root_observer.ObserverProcesses.test_pinned_stream_uploads_on_every_configured_runtime` |
| Sender loss, durability failure, competing host | Permanent operation claims prevent replay; unknown remains explicit | `tests.cytv.test_no_root_observer.ObserverProcesses.test_killed_bootstrap_and_worker_loss_never_duplicate_original_request`; `test_claim_and_terminal_durability_failures_never_replay`; `test_distinct_operations_exclude_and_stale_releaser_cannot_delete_new_owner` |
| Emergency stop arrives during launch | New recovery launch cannot clear or bypass the stop | `tests.cytv.test_no_root_integration.OriginalOperationIntegration.test_native_entry_preserves_stop_arriving_after_host_guard`; `test_emergency_marker_prevents_recovery_launch` |
| Exit 0 with review/ready/waiting/blocked/removal incomplete | Neutral review; no green success or automatic force/retry; explicit uninstall requires both clean-removal disposition and true cleanup proof, including when the payload omits or changes disposition | `android/tests/maintenance.cjs`; `android/tests/removal-result.cjs`; `android.tests.test_bridge.BridgeTests.test_recovery_result_preserves_fixed_disposition_and_verified_cleanup`; `tests.cytv.test_desktop_recovery.DesktopRecoveryTests.test_explicit_uninstall_requires_clean_disposition_and_true_proof` |

Full clean-removal adapters and native writer fences have their own focused
integration tests in the candidate. Their final method names and acceptance
results must be added here after integration; the frontend result contract alone
does not validate those adapters. Original legacy reports #201/#307/#359 remain
outside the future observer's terminal evidence. In #359, the initial generic
install failure is unknown and the later package-status rejection is distinct.
Do not request another install to fill this matrix.

Still unverified by these source tests: Linux-specific session/cgroup behavior,
retail SSH persistence, real private-filesystem permission/rename semantics,
vendor terminal delivery after disconnect/reboot, old Helper writer drainage,
carrier replacement on historical firmware, and actual clean removal on each
edition/model. Physical Home, unrelated buttons, sound, standby/wake, cold boot,
OTA and rollback require matching frozen artifacts and separate observations.
Native-speaking translation review is also not claimed.
