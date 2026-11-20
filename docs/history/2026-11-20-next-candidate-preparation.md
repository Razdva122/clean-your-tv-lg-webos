# Next candidate preparation — 2026-11-20

Preparation started at 11:07:18 UTC+05:00 from v1.26.0 RC6
(`a9bf96f16c02a7c9fbcecfb65a5f953a0868a09b`, [release PR #729](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/729)).
This branch stages the following cycle. Its version, release inventory and
signed artifact selection are pending.

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
| Pending | Combined GitHub CI, signed candidate packages and selected device acceptance. |

The first combined run also found a stale fixture assertion for the verified
Restore fallback. The focused rerun covers the explicit Restore argument.
Two macOS native guard checks passed with host process visibility after an
initial sandboxed run could not exercise the PID checks.

Review package bytes before assigning version changes. #744 affects Home/Root
locale resources and both updater profile validators. Root service, installer
and infrastructure changes affect signed packages and embedded installers.
Review recovery and localized migration instructions in the release documentation
pass. The current v1.26.0 evidence and plan apply to RC6. No TV or private
reporter data was used for this integration. The original device behavior
described in open reports needs the corresponding physical acceptance.
