# Next candidate preparation — 2026-11-20

Preparation started at 11:07:18 UTC+05:00 from v1.26.0 RC6
(`a9bf96f16c02a7c9fbcecfb65a5f953a0868a09b`, [release PR #729](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/729)).
This work became v1.27.0 RC1 in [release PR #761](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/761).

| PR | Integrated head | Merge | Scope |
| --- | --- | --- | --- |
| #738 | `5f23ea81` | `831d50b0` | Resume Root removal with an authenticated private Python cache |
| #742 | `2064dd87` | `4653c39e` | Linux system certificate fallback |
| #744 | `f9a4e590` | `f85a6946` | Romanian TV UI and both profile validators |
| #745 | `813dc432` | `e978b6af` | Local request activity for new Root recovery |
| #746 | `cf2f826b` | `d600edeb` | Verify and repair retained Root recovery in place |
| #749 | `d0cbaa09` | `7574309a` | Stream verified private cleanup and classify early failures |
| #750 | `d4ebc049` | `5cf3e617` | Record B9 startup evidence |
| #751 | `f16f4e92` | `4db18038` | Admit reboot resume by native guard and shutdown capabilities |
| #753 | `b0f97a58` | `e3439f91` | Distinguish input startup and heartbeat timeouts |
| #754 | `742cccf3` | `0797409f` | In-place Root Beta migration and native startup |
| #757 | `4f5a4b55` | `bbb60bb2` | No-root cleanup and verified LG Home fallback |
| #758 | `2c17c067` | `19c39cfc` | Legacy cleanup transport and packageinfo-only regression |

#754 contains the same #751 patch. #749 and #758 share one cleanup transport
implementation and retain both regressions. Conflict resolutions preserve both
CLI commands, diagnostic actions, and guarded activation and cleanup coverage.

## Verification

| Time (UTC+05:00) | Work and result |
| --- | --- |
| 11:07–11:09 | Read the open PR inventory and CI logs. [#746](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44569304378) reports an abandoned runtime shard. [Standalone #751](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44593333440) fails the runner fixture before dependent #754. |
| 11:09–11:11 | Merged twelve pinned PR heads in the isolated worktree. |
| 11:11–11:14 | Reproduced and repaired [#754](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44599003736) failures involving the installed runtime's provisioning module during host test discovery and changed ordinary OTA inventory. Integrated the recovery writer from #746 and confined the migration script to the Beta compositor installer bundle. |
| 11:11–11:15 | Focused macOS ARM64 checks passed: 131 Root tests (one skip), 10 published-supervisor OTA/rollback tests, 6 migration CLI tests, 26 installer recovery tests, 38 Python runtime tests (two skips), 138 No-root cleanup tests, 10 diagnostic tests, Romanian catalogs and Prettier. The OTA fixture used the existing pinned font cache. |
| 11:15–11:16 | All 52 native guard tests passed with host process visibility. The published-supervisor package probe also passed against the final packaging layout. |
| 11:19 onward | [Combined GitHub CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44687808650), frozen desktop runtime, website/preview and integration policy passed on #759 head `0cd636e0`. |

The first combined run also found a stale fixture assertion for the verified
Restore fallback. The focused rerun covers the explicit Restore argument.
The initial sandboxed native guard run could not exercise the macOS PID checks.
Two isolated checks confirmed the dependency before the full host-visible run.

Review package bytes before assigning version changes. #744 affects Home/Root
locale resources and both updater profile validators. Root service, installer
and infrastructure changes affect signed packages and embedded installers.
Review recovery and localized migration instructions in the release documentation
pass. The current v1.26.0 evidence and plan apply to RC6. No TV or private
reporter data was used for this integration. The original device behavior
described in open reports needs the corresponding physical acceptance.

## v1.27.0 RC1 freeze

| Time (UTC+05:00) | Work and result |
| --- | --- |
| 12:47:54 | Build handoff. Confirmed v1.26.0 publication and successful CI on #759. |
| 12:48–12:49 | Rehearsed and merged #759 at `528da6e0`; GitHub also marked all twelve original PRs merged. Collected the release inventory and added #160 links where the original PR descriptions used noncanonical wording. |
| 12:50–12:52 | Matched 15 v1.26.0 assets to SHA256SUMS. Verified four signed System feeds, 12 package bindings and the bootstrapped engine catalog against the pinned keys. BUILD-INFO points to published `fddc12d5` and accepted source `a9bf96f1`. |
| 12:50–12:52 | Built and verified the local versioned TV payload, including normal and Beta, HD and FHD bundles. Generated four System manifests and the engine archive. Three README metadata tests passed. |
| Pending | Full candidate dispatch, signed artifacts and selected physical acceptance. |

Helpers remain at 0.9.3. The local candidate matches the published signed
baseline byte for byte (SHA-256 `89a8d0eec0da5b0795ad239ca620408d3d93d5cb8995480a7f389108598c6f0f`).
System Updater IPK 1.2.11 also matches byte for byte. The local engine 1.2.15
(SHA-256 `43f72788d4412a0a2137a5108e17feb4c27cc3865cc6c3b51a1406eb8fa93d79`)
includes the Romanian profile validator. Local hashes are preflight evidence.

Reviewed README's download and component records, the desktop and translated
migration instructions, the retained repair flow, optional Python and language
guides. Existing No-root setup, prerequisites and device compatibility guidance
remain applicable. The release notes describe changes and link the acceptance
record. There is no newly verified TV model or firmware here.

### Device cases to bind after the full build

| ID | Changed path and scenario | Evidence required |
| --- | --- | --- |
| RC1-01 | Root and No-root Home locale and updater profile | Set Romanian, update through the signed profile path, retain the selection and verify UI, Home and rollback. |
| RC1-02 | System engine 1.2.15 and installed clients | Verify the existing bootstrap client can update in both editions, then check own-package recovery and rollback through the published baseline. |
| RC1-03 | Root recovery/activation and changed native guard | On a supported Root fixture or authorized device, verify normal activation, stock fallback, physical emergency Home input, sound and affected cold boot/standby separately. Use the original retained receipt for the repair-specific case. |
| RC1-04 | Retained legacy Root Beta migration | On an eligible authorized retained configuration, verify migration, source choices, boot resume, explicit Off and rollback without replacing the installed app or losing preferences. |
| RC1-05 | Root and No-root cleanup | Verify affected removal/recovery transitions, cached Python handling, package metadata cleanup and restored LG Home. |
| RC1-06 | Android installer with new embedded packages | Verify the signed upgrade from the published app and the affected install/recovery path and controls. |

All cases remain untested on the selected RC1 artifact. Assign artifact hashes
and available authorized TV preconditions before device operations. Do not
assume project-device coverage for the reported W19P, B9 or W20H configurations.

### RC1 build failure and replacement

[RC1 run 44698305176](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44698305176)
started at 12:53:37 UTC+05:00. Its Windows job failed five assertions in two
fixtures. The Linux CA fixture compared host-native path text to POSIX paths.
The cache-removal fixture ran TV code requiring POSIX paths and file metadata
on Windows. The replacement compares POSIX path text and runs the latter
fixture on POSIX CI. Installer and TV runtime sources and package versions are
unchanged. The focused macOS suite ran 38 cases (36 passed, two Linux-only
skips). The same-source failed-job retry cannot pick up these fixture changes.
RC1 was cancelled at 13:11:10 UTC+05:00 at the maintainer’s request to free the
queue. The failed attempt supplied no device acceptance.

### RC2 artifact preflight and acceptance scope

Release coordination handoff was at 13:17:14 UTC+05:00. The maintainer made
only the project OLED55C3RLA available. Its paired read-only check and SSH
release metadata succeeded. The starting Root version was 0.22.0; the
v1.25.0 rollback installer and original Root/Updater packages were verified
against the published checksums before device mutations.

- **RC1-06 (emulator).** Exact APK from RC2 run 44700115224:1, SHA-256
  `507ae5be20f9580792062b9c7bb28d7fccc55c9480288c356bfb0e781c00734e`.
  Original signing identity verified. ARM64 Android 15 / API 35 userdebug
  emulator upgraded the signed published v1.26.0 Android 0.22.0 / 52 APK to
  0.23.0 / 53 via install-r. All four synthetic retained files matched.
  The real Store and native OperationChecks passed. No pending action replayed
  on launch. No phone or TV commands were used in this emulator case.
- **RC1-04 (offline pass, physical deferred).** Verified the candidate macOS
  archive and 622 embedded payload files, including the Root Beta compositor
  bundle (manifest SHA-256
  `2b18ef364a16f62531b3e1615cf4c99268c633704d2a8f3981f5d88a6223a4be`).
  Replayed that exact bundle in the existing isolated W19H 05.50.00 laboratory.
  Factory ARM Node, LS2 and native guard verified ready status, an unstarted
  removal handoff with preserved evidence, migration, retry, rollback and
  explicit reapply. All 148 installed files and the saved preferences matched.
  The modeled boot used actual ARM retirement and launched once per verified
  new session. Physical boot and remote behavior are unverified and were
  explicitly deferred by the maintainer. Follow-up on other hardware belongs
  in the existing public reports after verified publication.

[RC2 run 44700115224, attempt 1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44700115224)
ran 13:11:12–13:52:06 UTC+05:00. All mandatory platform, runtime and browser
gates passed. Full build validation used source `3b49294bda1d2da49e4859f3ca72750ebac08475`.
