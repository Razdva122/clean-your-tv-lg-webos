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

### RC2 C3 observations

Protected signing [44706118549](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44706118549)
ran 13:53:22–13:54:35 UTC+05:00. The checked QA archive SHA-256 was
`772aeedd92e8fa7387e59c826b7021cbeeb49cf78d05b4041f3818f858312248`;
engine 1.2.15 was `43f72788d4412a0a2137a5108e17feb4c27cc3865cc6c3b51a1406eb8fa93d79`.
Host installer SHA-256 was `d6280e4a89c8e080332c850bae7ad4ca68a9d2f7149eca10947fa4b9d2328619`.
The project LG OLED55C3RLA (firmware 43.21.71, SDK 11.2.0, FHD) started
with published Root 0.22.0 and no System Updater. The verified macOS ARM64
v1.26.0 installer provisioned the starting System 1.2.14 engine. A paired
network Home press from Media Player opened the original Root Home before the
signed update.

| Case | Observation |
| --- | --- |
| RC1-01 Root | Romanian rendered after selection and after same-version Repair. The full rendered profile matched. Thirty-one installed package and companion files matched signed RC2. |
| RC1-01 No-root | Exact signed FHD and HD package inspection verified the Romanian picker and profile allowlist. Live update/profile retention remain unverified. |
| RC1-02 Root | Authenticated signed offer, forward update to engine 1.2.15 and own-IPK Repair completed using ordinary LS2. Repair moved the engine from slot A to B and preserved the product journal. |
| RC1-03 Root | **Release blocker.** After the signed forward update, a single paired network HOME from Media Player opened LG Home instead of Root Home. The original intent was active, the suspension captured disabled state, and the resume ticket recorded desired=true, attempted=false, outcome=skipped. Root stayed disabled and the guardian was stopped. Explicit Change Home through the installed RC2 UI subsequently armed the route and paired network HOME reached Root Home. The owner verified triple Home on the physical remote. Network and SSH readback confirmed LG Home, disabled intent and a stopped guardian. Physical audio was not reported. |
| RC1-04 | Exact firmware replay passed. Physical B9 check was explicitly deferred. |
| RC1-06 | Exact original-signer Android update passed on the isolated API 35 emulator. |

The owner set a fifteen-minute C3 access limit during the Root rollback.
Verified restoration of the original state takes precedence over starting
another edition transition with no assured time to undo it.

Root rollback returned the signed product to v1.25.0 Root 0.22.0 and Root
Updater 0.6.3. Thirty-one installed package and companion files matched the
published baseline. The rendered profile matched before/after and the active
engine stayed at 1.2.15, slot B, with ordinary LS2 returning rolled back.
Because the owner had explicitly used triple Home, network HOME correctly
continued to open LG Home after rollback.

The RC2 installer removed temporary Root/System state following a verified
software restart. The original v1.25.0 Root install was restored at 14:18
UTC+05:00. Root package hashes and the private origin snapshot matched and
paired HOME opened Root again. The
independent System Updater was absent as at the start. The owner subsequently
allowed leaving a usable No-root or stock configuration within the remaining
C3 access window.

### RC2 QA exit at 14:23:47 UTC+05:00

After the maintainer removed the requirement to return to the original
edition, the verified source installer completed a second Root cleanup and
software restart, then installed No-root RC2 using the existing Root SSH
connection. The installer returned verified completion. From Media Player,
paired network HOME briefly showed LG Home and then settled on Clean Your TV
No-root. Seven Home 1.20.6 and Helper 0.9.3 files matched the signed candidate.
The Romanian picker rendered Romanian on the installed launcher. The
all-components hash helper expected a complete System publication layout;
the ordinary install was verified separately against its two main IPKs.
C3 was left usable with No-root RC2 at the maintainer's request.

| Original case | Exit disposition |
| --- | --- |
| RC1-01 | Root signed Repair retained Romanian and the rendered profile. No-root direct install and Romanian rendered. No-root signed-profile persistence and rollback were blocked by the 15-minute C3 window. |
| RC1-02 | Root signed forward, same-IPK Repair and rollback passed as package, engine and ordinary LS2 operations. No-root signed transition, own-package Repair and rollback were blocked by the C3 access window. |
| RC1-03 | **Failed.** Signed Root forward did not resume the previously active Home route. Explicit activation and the physical triple-Home escape passed. Physical sound, standby and cold boot under RC2 were not verified before the C3 access window ended. The W20H repair-specific case requires its original interrupted setup receipt and was unavailable on C3. |
| RC1-04 | Exact artifact offline pass and explicit maintainer deferral of physical B9 acceptance. |
| RC1-05 | Ordinary RC2 Root cleanup after verified software restart passed. That verifies the C3 transition, not the affected retained legacy Python-cache or package-stub cases. Known legacy replay and full CI apply within their model limits. The C3 time limit prevented an additional No-root removal cycle. |
| RC1-06 | Exact signed Android upgrade passed on the owned emulator. |

Reconciliation: six original cases, one complete observed pass, one observed
failure, three partial cases with concrete live-scope blockers, and one
explicit physical deferral with offline verification. There is no available
independent planned TV check after the access cutoff. Do not mark RC2 accepted
or submit the release PR for publication. The observed Root resume failure
requires diagnosis and verification with a replacement candidate. Its ticket
records a conservative skip before activation, so an explicit activation
pass does not establish automatic continuation after update. The existing
reports remain the destination for owner tests on other hardware after a
verified release.

### RC3 Root Home correction and remaining acceptance

The maintainer reported that access to the project C3 would end within five
minutes and remain unavailable for two days. The last observed state is a
usable No-root RC2 install. No further TV change was started in that window.
The previous physical B9 deferral remains in effect.

An on-disk lifecycle regression reproduced RC2's conservative `skipped`
outcome after an automatic boot callback under the update reservation changed
the saved disabled intent generation. Review identified a second path through
repeated suspension after the snapshot was saved. The same regression exposed
that generation change. This explains how the observed outcome can occur;
the C3 evidence does not identify which callback actually ran.

Automatic boot recovery and a repeat suspension with a verified disabled
snapshot now preserve its generation. Explicit Off and emergency escape
retain cancellation. A suspension interrupted before verified snapshot capture
still cannot infer permission to enable Home on retry.

| Original case | Remaining evidence on the final candidate |
| --- | --- |
| RC1-01 | Verify Romanian through signed No-root Repair and final Root Repair. Use RC2 Direct Install and rendering evidence for unchanged files and matching preconditions. |
| RC1-02 | Run signed No-root forward, same-IPK Repair and rollback. Repeat the signed Root sequence because the separately signed Root infrastructure changed. |
| RC1-03 | Start signed Root forward from active Home on the published baseline. Require automatic resume and verify paired HOME from Media Player, actual Magic Remote escape, sound, standby and cold boot. The W20H interrupted-setup receipt is unavailable on C3. |
| RC1-04 | Replay the changed final Root Beta package against the retained B9 fixture. Physical B9 remains explicitly deferred. |
| RC1-05 | Reuse the ordinary C3 Root removal evidence within its demonstrated scope. Verify the remaining No-root removal and the affected legacy cleanup using its matching fixture. |
| RC1-06 | Verify the final Android installer upgrade and retained data on the owned emulator if its embedded payload changed. |

Physical acceptance is blocked by C3 availability. The release PR stays draft
until required evidence is recorded against the selected candidate.

### RC3 offline preflight and development publication decision

The project C3 is no longer available. The maintainer authorized a separate,
opt-in `v1.27.0-dev.3` GitHub prerelease after offline verification, with
targeted notes in the six affected issues. v1.26.0 remains the stable release.
A dev publication leaves the v1.27.0 candidate draft and does not record
physical acceptance or ship stable OTA feeds.

Local preflight verified all four System variants. The Root and Home FHD/HD
IPKs and Helper are byte-identical to signed RC2. The Helper also matches
published v1.26.0. The System engine matches RC2 at SHA-256
`43f72788d4412a0a2137a5108e17feb4c27cc3865cc6c3b51a1406eb8fa93d79`.
Root infrastructure SHA-256 is
`99aef72b0c09b1487f9fb0ad0a9fc6d75c56299bee6855971f2c8eae4a19d3d8`.
Exactly four infrastructure files changed from RC2, all in the Root
runtime. Protected signing must verify the final delivered bytes.

The focused local pass covered 164 Root tests, three legacy OTA scenarios
and seven retained rollback anchor scenarios. The first focused CI on #762
found an older rollback fixture that rejected the new keyword. The verified
fixture correction was committed separately, then the superseded CI run was
cancelled by GitHub as the replacement started. The C3 failure remains
historical and cannot be attributed to a particular callback from the
available device evidence.

### Exact RC3 offline verification

[Full candidate run 44745629207, attempt 2](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44745629207)
completed at 19:31:28 UTC+05:00 from source `e5977792077ffb9dc3dc323cdad2442a998ab948`. Attempt 1 ran
from 18:35:22 UTC+05:00 and failed the Windows GUI test for an interrupted
No-root uninstall. The transition did not finish within its five-second
test wait. The same test passed on RC2 and passed locally in 3.260 seconds.
The failed-jobs retry kept the exact source and all successful platform
packages, including the Android and macOS ARM64 files tested offline below.

- **RC1-04.** Replayed the exact embedded Root Beta bundle
  `55190b885f08eb053ed7bdc01e8b0ccbb8a86e25250cd35d1466b6fb3d85013f` on the W19H 05.50.00 offline fixture. Factory ARM Node,
  LS2 and the native guardian verified readiness, unstarted removal handoff,
  modeled boot/session behavior, migration, retry, rollback and explicit
  reapply. All 148 installed files and settings matched. The lab needed an
  absolute QEMU path because the runtime sanitizes its child process PATH.
  The test package was unchanged. Physical B9 remains deferred.
- **RC1-06.** Android 0.23.0 / 53 APK
  `9d0e92f03fdbbfdad7638e2106ba5ac5abc90c90cfb56b07c1dc2930b543ee32` upgraded over published Android 0.22.0 / 52 on
  the owned ARM64 Android 15 API 35 emulator with the original signer.
  The app's store verified the retained profile and four seeded files.
  Native operation checks passed and idle launch caused no recovery replay.
  The successful Android job was reused by the Windows-only retry.
- **RC1-01, RC1-02, RC1-03, RC1-05.** The required final device evidence
  remains blocked by unavailable project hardware. The development release
  can collect voluntary reports. The stable candidate remains draft with
  physical acceptance unset.

### Protected QA and development publication

[Protected signing 44754494371](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44754494371)
completed at 19:34:42 UTC+05:00. Verified archive SHA-256
`93bbb19a0ddcca6fccef9f237291568fe5d33420556b3f390aee3183dc31e4c4` and the
Root/No-root FHD and HD manifests against the pinned CLI and published
System baseline. Engine 1.2.15 and corrected Root infrastructure matched
their preflight hashes. The QA catalog is retained for closed device testing.

[v1.27.0-dev.3](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.27.0-dev.3) was published as a GitHub prerelease at 19:58:16 UTC+05:00.
Verified the tag's frozen source, all 12 asset digests and anonymous access
to the checksum file. GitHub Latest and all 37 stable asset digests matched
v1.26.0 before and after publication. The
[stable feed verifier](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44758575652)
rejects dev tags at argument validation before reading any update feeds.
The dev assets are installers and
verification metadata. The stable v1.27.0 candidate remains pending device
acceptance.

Confirmed development release notices in issues [160](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160#issuecomment-7046298349), [389](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/389#issuecomment-7046266816), [615](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/615#issuecomment-7046269019), [692](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/692#issuecomment-7046270755), [712](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/712#issuecomment-7046272421), [739](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/739#issuecomment-7046274006).

## RC3 retired from stable consideration on 2026-11-21

The maintainer authorized reopening integration for a replacement candidate.
The integration pass began at 17:27 UTC+05:00. RC3 remains available as
[v1.27.0-dev.3](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.27.0-dev.3).
Run 44745629207:2 is retained above as historical evidence. The replacement
has no selected build or acceptance record. The six original acceptance case
IDs remain in scope. Device cases requiring the C3 remain blocked by access.

The development APK installed and upgraded on the emulator. A later
[operation-level check](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/776)
found that the packaged installer could not import its desktop bridge.
RC1-06 is open for the replacement. Verify clean install, upgrade from
published codes 52 and 53, retained state, and an installer operation on the
production-signed APK. The Android candidate needs an upgradeable versionCode.

The integration combines the reviewed fixes and audit branches, including the
stacked Android payload update. It resolves overlapping C1 Settings and lease
broker changes while retaining explicit LG Home recovery and embedded-adapter
subscriber cleanup. The embedded LG Home adapter requires target-device
acceptance before stable delivery. Existing offline evidence does not cover
installation, rendered Home, physical input, HDMI/audio, standby, boot or rollback.

Focused integration checks passed for 70 compositor runtime cases on Python
3.11, 20 embedded runtime cases, eight bootstrap flow cases, the native stale
input case, lease-broker behavior, and the Home CARD browser check in both
editions. GitHub will validate the combined patch before merge.

### Replacement integration results

- At 17:50:48 UTC+05:00, [#789](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/789)
  merged as `9f6fb58b`. [Combined CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44904514619)
  passed on `fd482ad5`. All 23 selected checks passed. The six unselected
  checks were skipped. The review kept the embedded adapter's original
  input-loss behavior while ordinary C1 retains input reconnection.
- [#772](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/772) advanced
  during combined CI. Its updated head `27af65d7` passed its
  [own CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/44905177061).
  The combined tree also passed the affected installer diagnostics, desktop
  recovery, Root activation, compositor runtime, clean removal and transport
  tests locally. It merged at 18:04:26 UTC+05:00 as `024a4f9d`, with the same
  tree as the local verification.
- All 22 implementation PRs are integrated. GitHub still lists v1.26.0 as
  Latest, and `v1.27.0-dev.3` resolves to the original RC3 source. No new
  candidate build, device operation or acceptance result was recorded.

## RC4 preparation on 2026-11-22

| Stage (UTC+05:00) | Result |
| --- | --- |
| 13:07:00 | Release coordination handoff. Confirmed v1.26.0 as Latest and v1.27.0-dev.3 as the previous development prerelease. |
| 13:08:48–13:09:06 | Merged [#793](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/793) as `4d6bd0c3` and [#794](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/794) as `163d1707` after their focused CI. [#790](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/790) remains draft pending the outcome of the requested retained-activation test. |
| 13:09–13:10 | The saved C3 remote connection timed out and SSDP returned no devices. The maintainer confirmed the TV was unavailable. No device change or fresh pairing was attempted. |
| 13:10–13:12 | Downloaded v1.26.0 assets, matched their published checksums and verified four signed System feeds, 12 package bindings and the signed engine catalog against the production public keys. |
| 13:11–13:13 | Built and verified the 634-file local TV payload on macOS ARM64. The first attempt could not resolve the pinned font download host. The retry used the existing hash-checked source font cache and verified the normal, C1 and legacy Beta packages. |
| 13:12–13:14 | Three README tests, six screen-watch cases, 39 controller cases and 177 Python diagnostics tests passed locally. [Combined Tests](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/45001456000), [frozen installer runtime](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/45001455643) and [website scope](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/45001455817) passed on `163d1707`. |
| 13:14 | Validated the four local System sets, engine transition and the separate Helper probe payload. The prior Helper approval rejected the new package pair as expected. |
| 13:16 | Ten release-input boundary checks and eight System bootstrap flow checks passed locally. |
| Pending | Published Home/new Helper on project C3, then one full CI dispatch, build pin and artifact-bound acceptance. |

The [release notes](../RELEASE-1.27.0.md) show the prepared version set. Home,
Root, cytv and both Updaters advance beyond RC3 because their packaged paths
changed. The System Updater engine advances for the changed shared storage
support and infrastructure inventory. The System Updater IPK stays 1.2.11.
Android advances to 0.23.1 / 54 for upgrade from codes 52 and 53. #794 adds
runtime code and requires Helper 0.9.4. No Homebrew Installer promotion is
selected. The release plan remains unfrozen while the mandatory compatibility
probe is blocked. #793 and #794 improve reports for #792 and #686. Those two
issues and #739 still await reporter evidence for their original behavior.

### RC4-P00 Helper compatibility before full dispatch

| Input | SHA-256 |
| --- | --- |
| Published Home 1.20.5 FHD | `93dae5cd5f0be37efbe81981bef2283c9fe5c349b769a45f62d1db713095529e` |
| Published Home 1.20.5 HD | `836b75bacf6f5d9a030e6fec5236e6acb6082a8b5a5f53d9fab720ea41cb1477` |
| Published Helper 0.9.3 | `89a8d0eec0da5b0795ad239ca620408d3d93d5cb8995480a7f389108598c6f0f` |
| Local Helper 0.9.4 IPK | `56e76e9d52d9196916f725c6499291f0417f666aa801b9e13a25c571fa3c2b55` |
| Local Helper 0.9.4 canonical archive | `53432274e26e4621c5a64c32376c097e1f12379acaec843e864ce6dae1927859` |
| Local System engine 1.2.16 | `7200e8ac7c133b24ff0228d3411a84cfe94954d8722a7f9cb4ad72c6efd79fb2` |

Use the authorized project OLED55C3RLA. Recheck the firmware and prior edition,
versions, pending operation and rollback readiness by readback. The last
observed firmware was 43.21.71 with SDK 11.2.0 and an LG Magic Remote of unknown
exact model. The macOS ARM64 source installer probe pairs authenticated
published Home 1.20.5 with the exact Helper 0.9.4 used in the local TV payload.
Read back the installed application and service files, check Start and enabled
status from the published Home, and verify network HOME from Media Player
reaches and remains on Clean Your TV. Observe that the diagnostics session
opens, captures and closes the additional foreground subscription on firmware
that supports it. Physical Magic Remote and standby observations belong to
the affected cases below. Record the actual runtime result before updating
the approval. Run `verify_helper_transition` with the real packages and
approval before dispatching the full candidate. The previous approval remains
in place until first-hand evidence exists for the new pair.

### RC4 selected acceptance cases

The original IDs remain in scope. This pass uses the complete candidate once
pinned and signed. Attach each artifact hash, starting state, observed result
and evidence before issuing a failure inventory or changing the device state.

| Case | Affected behavior and minimum evidence | Disposition |
| --- | --- | --- |
| RC1-01 | Signed Repair and forward update in each edition retain the Romanian profile and render Home. Home, Root and updater package hashes changed. | Awaits final signed packages and C3. |
| RC1-02 | Exercise signed forward, same-IPK Repair and supported rollback in both editions from the authenticated baseline, including engine 1.2.16 and the changed infrastructure. Verify usable Home after rollback. | Awaits final signed packages and C3. |
| RC1-03 | Start from active published Root Home. Verify automatic resume after signed update, paired HOME from Media Player, physical triple-Home emergency exit, audio, standby and AC cold boot. Verify retained recovery separately on a matching fixture or authorized device. | Awaits final signed packages and C3. The reporter's W20H receipt is unavailable on C3. |
| RC1-04 | Re-run the exact final Beta artifact on the W19H retained B9 fixture for in-place migration, boot resume, Off and rollback. | Awaits final bundle. Existing maintainer deferral of physical B9 testing remains recorded. |
| RC1-05 | Cover affected ordinary No-root removal and Root recovery/cleanup. Verify restored LG Home and surviving state on C3; use the matching simulated legacy Python and metadata fixtures for those paths. | Awaits final package. |
| RC1-06 | Run the production-signed code 54 APK on the owned emulator: clean install, upgrades from codes 52 and 53, retained profile/state and a native installer operation that reaches the desktop bridge. | Awaits final signed APK. RC3 operation failure keeps this case open. |
| RC4-07 | On an admitted embedded LG Home device, verify native Home overlay, physical controls and safety stop, HDMI/audio, standby, restart and rollback for the changed embedded controller and lease broker. | Awaits final package and access to an admitted device. |
| RC4-08 | On the final No-root package, verify report export with the added window fields and ordinary Home routing during capture. Fixtures cover sanitization, opt-in, reconnect and Stop; the original webOS 4.5 YouTube scenario needs a matching TV. | Awaits final package and C3; matching webOS 4.5 device unavailable. |

Reviewed README, desktop and source installation, recovery, updates, Helper
diagnostics, Android and Root guides, compatibility, themes and all 13
localized guides against the changed paths. The integrated guidance covers
refused connections, Root Home handoff and unavailable themes. Existing
localized anchors were preserved. Records and release versions are kept
outside the translations. Hardware claims still depend on the selected
acceptance cases.

## RC4 input recovery integration

The maintainer requested the extra integration at 14:15:31 UTC+05:00 on
2026-11-22. [#790](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/790)
merged as `10e366a6` at 14:17:33 after its focused CI and explicit approval
to take the PR out of draft. [#796](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/796)
merged as `d805389a` at 17:07:58 on 2026-11-23 after
[its selected CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/45006539797)
passed. The merged tree matches the locally rehearsed integration tree.

The combined macOS ARM64 build on 2026-11-22 verified 634 TV payload files and
all four System sets. Home and Root app IPKs, both Updaters, and the System
engine match the first RC4 preparation. Helper 0.9.4 and Root infrastructure
0.24.1 changed. The unpublished RC4 component versions are retained. The
macOS CLI and GUI verified payload and runtime. The GUI also passed the
offscreen smoke test. The sandbox blocked the CLI bootloader's semaphore;
the same binary passed the checks outside the sandbox. Android staging
verified all 634 entries. Three focused suites on the combined source passed
109 Root activation and recovery tests. The 13 updated localized guides
retain their previous anchors and cover input reconnection; developer
guides describe the changes to the relay and Root wake behavior.

### Current RC4-P00 probe inputs

These replace the earlier RC4 probe bytes for the same case ID. Published
Home and the previous Helper remain the authenticated v1.26.0 inputs above.

| Input | SHA-256 |
| --- | --- |
| Helper 0.9.4 IPK | `b0020d1ae15b71737297c7dfdfa592a67da5d348beaf5d5356920ed71e53ff59` |
| Helper 0.9.4 canonical archive | `4f5f70daa3d2b0a6c78ab91692478149c5fd3685eccfc81d76aa03d2972b50a7` |
| Root infrastructure 0.24.1 | `1186cee5471a9d245fa4543bb1a69318e8dfb55caa3bfc1b98213546590fae38` |

TV QA handoff was 17:06:14 UTC+05:00 on 2026-11-23. Paired SSAP and saved
Root SSH succeeded. The project OLED55C3RLA reports firmware 43.21.71,
SDK 11.2.0 and Node 20.12.2. It starts in No-root on Home 1.20.6 and
Helper 0.9.3, with no pending installer operation. This case requires
the new exact Helper archive with published Home 1.20.5 because neither
the current installation nor the older RC4 probe covers the changed
Helper/controller/relay. Reuse the signed published baseline and recover
through the ordinary installer if needed.

### Additional RC4 acceptance coverage

Keep the original cases and the W20H retained-state scope of RC1-03.
RC4-09 covers the changed input-loss path from #796. On the pinned
artifacts, verify both editions retain the confirmed Home choice and
reconnect physical input across a standby/wake or actual device recreation,
with explicit Off, emergency Stop and unrelated controls still working.
Run the project-device routing and physical checks on the admitted C3 path.
The G3 report also needs its original inactivity-driven cycle on matching
hardware because the terminal transition was absent from the reporter's
trace. Existing host fixtures cover device loss without a power frame,
reconnect, Off, held keys and watchdog expiry within their modeled scope.

### RC4-P00 result on 2026-11-23

The published macOS ARM64 rollback installer matched v1.26.0 SHA256SUMS and
verified its complete payload. The ordinary macOS ARM64 source installer
0.24.1 used saved No-root Root SSH on the project OLED55C3RLA with firmware
43.21.71 and SDK 11.2.0. The installed pair changed from Home 1.20.6 /
Helper 0.9.3 to Home 1.20.5 / Helper 0.9.4. The installer verified both
packages and reported that explicit Start Helper was required. All 14
selected installed files matched the published Home and exact local Helper
inputs. No installer operation remained pending. The maintainer confirmed
Start Helper from the published Home UI with the physical remote.

With Media Player foreground, one paired network HOME briefly entered LG
Home and settled on Clean Your TV, still foreground after one second. The
diagnostic recorder opened and expired normally with five populated
foreground-window records. This completes the exact-pair compatibility
probe. The committed approval and `verify_helper_transition` agree with
the inputs above. Physical Home routing, standby, cold boot, audio, OTA,
rollback and matching legacy device evidence remain distinct cases.

The author's [latest #739 report](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/739#issuecomment-7079362528)
did not confirm resolution, and the issue is closed. RC4 carries the verified
bench recovery improvement. The reported post-reboot and removal outcomes
remain unverified.

### First full RC4 run and CI corrections

[Run 45174994655](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/45174994655)
started at 17:30:40 UTC+05:00 on 2026-11-23 from `aeef4ca7`. Windows
host testing found a generated inventory fixture parser that left a semicolon
before CRLF. The signed Android APK matched its expected hash; its emulator
failed to discover the AVD before installation. Forced CRLF reproduced the
Windows error. The fixture fix passed forced CRLF and all 37 related tests.
The shared runner-local AVD path passed local discovery, YAML and shell
validation, and nine CI profile tests. Independent review found no blockers.
[#801](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/801) merged
at 17:56:47 with the maintainer's instruction to start the replacement without
waiting for the outstanding jobs. The guarded test/workflow changes require a
replacement run. The verified Helper archive and the pre-dispatch approval
remain applicable. No final build pin or hardware acceptance has been recorded.

The project C3 was returned to published v1.26.0 No-root for the selected
signed forward/Repair/rollback tests. The ordinary macOS ARM64 installer
verified Home 1.20.5 and Helper 0.9.3. The first System preparation stopped
at setup while Home Updater was absent; read-only status confirmed no
supervisor, and ordinary status reconciled the receipt. Installed the
authenticated Home Updater 0.6.4 with a matching backend terminal. The
ordinary setup retry completed System Updater 1.2.11, with no pending
operation. Paired network HOME from Media Player settled on Clean Your TV.
The existing Romanian setting from RC2 was unsupported by the older Home's
profile export. English was selected through the published language picker,
and the actual rendered profile was captured privately for the forward test.

The nine selected acceptance IDs remain open pending the verified replacement.
The B9 lab's retained factory executables were absent, so the exact official
W19H 05.50.00 archive is being restored. The Android test setup matched the
published code 52 and development code 53 hashes and signer and started an
isolated ARM64 API 35 emulator. These checks establish preconditions for the
remaining artifact-bound cases.

### Replacement RC4 verification in progress

The maintainer resumed end-to-end release coordination at 18:01:12 UTC+05:00
on 2026-11-23. The [replacement run 45179501341](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/45179501341)
was dispatched at 17:59:33 from `63a96a2b`. It waited for the superseded
run's two macOS packaging jobs. The original full validation suite passed,
while Windows host testing and Android emulator setup had already failed.
The old run was cancelled to free the concurrency queue. Neither build
was selected at this point.

The original signed APK from run 45174994655, SHA-256
`20a2cfa4e8a88185054ecb33116e54e1706bc809fb9fa3b9d572ae8154a72c45`,
passed a clean install and its real bridge/native fixtures on an isolated
ARM64 Google APIs API 35 userdebug emulator. In-place upgrades from codes
52 and 53 to code 54 retained all four seeded files and passed real Store
verification. Both baseline APKs matched their published digests and the
candidate matched the pinned signer. This observation can cover RC1-06
on the replacement only if the checked APK and relevant runner bytes match.

The maintainer confirmed that only the project C3 is available and approved
post-release user testing for other TV models. Read-only LS2 on the C3
confirmed that System Profile is present, so it cannot run the embedded
Home compositor path. RC4-07 physical W17M-class acceptance is explicitly
deferred. The original G3 inactivity cycle, legacy webOS 4.5 YouTube
reproduction and W20H retained recovery remain model-specific follow-up.
All applicable C3 scenarios and the selected offline and Android checks
remain in scope. The release must describe those limits without claiming
hardware coverage from a different model.

#### Android candidate result

At 18:21–18:22 UTC+05:00, the exact RC4 APK passed RC1-06 on the owned
ARM64 API 35 userdebug emulator. Its SHA-256
`2d7f6af8e7d162a8c63e75dd70117ddbd658ebdd06e818a759eb984bcb7624a6`
matches the APK build report from the post-smoke artifact of build
45179501341, attempt 1. The APK source and original production signer
verified, and the installed app was non-debuggable with version 0.23.1,
code 54. A clean install passed both edition fixtures and a real packaged
Python bridge operation with loopback inspection and a synthetic TV status
response. In-place upgrades from code 52 and 53 to 54 preserved the
original signer, all four seeded files and the app's Store readback.
The isolated emulator was stopped after verification. These Android
checks did not use a physical TV.

#### Offline fixture and device readiness

The B9 05.50.00 LG image ZIP was verified and extracted. Its SHA-256 is
`59ef18516657a7a058d4a8cf86dab14020eb25d40f794e328506bbc999a1b976`.
The restored W19H sysroot runs factory ARM Node 0.12.2, the LS2 hub and
`luna-send` under QEMU in a network-isolated lab. The original v1.21.0
Mac installer matched its published checksum. Its verified Root Beta
0.20.0 bundle `716468795d7ca68592403b5d3258a51cc674cc68656f1b789580c2ca6c78b446`
restored the 148-file installation fixture. The lab rehearsed migration,
modeled startup and rollback using preliminary bytes. RC1-04 still
requires the exact selected installer bundle.

At 18:24–18:25 UTC+05:00, the project C3 answered a read-only package query
with published No-root Home 1.20.5, Helper 0.9.3, Home Updater 0.6.4 and
System Updater 1.2.11 installed. Root Home was absent, as expected for the
initial No-root case. The query made no device changes.

At 18:31–18:33 UTC+05:00, RC1-04 passed both the ordinary and pending-removal
scenarios on that W19H fixture with the exact Root Beta bundle from RC4's
macOS ARM64 installer. All 53 embedded files matched their payload manifest.
Bundle SHA-256 was `ce0f165bdfc0a5ca1dbca2a09a6ec3e81327f0a5554da6d7bd6ff0c29c441e78`;
the GitHub artifact ZIP was `111eb3b91fa89b2cd8087291427a6e8ed282ffac5be0776caa140922d75f6791`.
The factory ARM Node and LS2 service reported verified integrity. The
ordinary and pending-removal variants preserved all 148 installed files
and settings. The latter recorded the previous pending removal before
starting a new lease. Both verified startup-session admission, single
resume, inverse rollback from a modeled Off state, and explicit reapply.
Power and controller signals were modeled for the boot replay. Physical
B9 acceptance remains deferred.

For RC1-05, the successful Linux CI installer shards recorded the
legacy Python recovery-before-removal check, validation before cache
retirement, and No-root terminal cleanup limited to empty owned
package metadata. The result covers those fixtures. The selected C3
removal and recovery checks remain open.

The exact macOS ARM64 payload carries Helper 0.9.4 with SHA-256
`b0020d1ae15b71737297c7dfdfa592a67da5d348beaf5d5356920ed71e53ff59`,
matching RC4-P00 and the committed published-Home rollback contract.
The final C3 cases still use the new Home IPK and signed System catalog.

#### Selected build

At 18:43:01 UTC+05:00 the full RC4 run 45179501341, attempt 1,
completed successfully. The trusted candidate verifier pinned source
`63a96a2bb19b4236ec15437868ff160b2d73d8f4`. The Android and offline B9
observations above use the exact selected artifact bytes. Stable hardware
acceptance remains unset pending the signed C3 cases.

At 18:43:44 UTC+05:00 the pinned commit dispatched the
[private System signing run](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/45186783420).
The successful run's artifact ZIP matched
`daea3e036e49f1132343f5a089966e574460b57abaab2a0e108f356637558923`.
Local verification with the production public key checked the exact
build provenance, all four variants, catalog signature and package
hashes. Catalog SHA-256 is
`3a41af18d11522de989d8426f83587177bb50f74180325d279a893a89fbcb94f`.
Engine 1.2.16 SHA-256 is
`7200e8ac7c133b24ff0228d3411a84cfe94954d8722a7f9cb4ad72c6efd79fb2`.
The bundled System IPK 1.2.11 is byte-identical to the published baseline.

#### C3 No-root observations

At 18:47–18:49 UTC+05:00, the signed v1.26.0 to v1.27.0 No-root
forward operation completed on OLED55C3RLA (43.21.71 / SDK 11.2.0,
Magic Remote model unknown, macOS ARM64 installer). The active engine
1.2.16 and original System IPK 1.2.11 verified through the ordinary LS2
status method. Home 1.20.7 is
`cc2b2aa5f6924ee9523d635cab6fcd166d73670859807a30444af59d5d36b500`;
Home Updater 0.6.6 is
`791b0a63527bf1334ff79e54d83a06a40a333a31532cdddd139a32a6a2b68d11`.
Network HOME from Media Player briefly entered LG Home and settled on
Clean Your TV. Both exported settings and configuration matched the
real English baseline.

At 18:49–18:50, the same-IPK signed Repair produced a new real
app-install terminal on the other verified engine slot and preserved
the original product journal. The Romanian selection made through
the running Home language picker rendered after Repair. The Romanian
preference and captured settings and configuration matched the
pre-Repair export.

At 18:51, the normal Home setting confirmed explicit Off, persisted
the false preference, and paired network HOME from Media Player
settled on LG Home. On a fresh Home open, the normal status and
switch did not become available for re-enable. The Helper status
service reported not running and no Stop latch. Process readback
still found the recorded controller PID, and the scoped journal
showed a later relay-exit event. The cause is under investigation.
No-root diagnostics, physical standby/escape and rollback are listed
as outstanding until exercised against this artifact.

At 18:56–18:57 the verified software restart reset uptime and removed a
unique temporary marker. The normal settings panel read the retained Off
choice and accepted explicit On. Paired network HOME again settled on
Clean Your TV from Media Player. The first fresh-panel re-enable failure
remains recorded. A single control repeat from this recovered state is
justified to separate a repeatable Off-to-On transition failure from the
observed unavailable control broker after the first Off. The repeat
uses the same installed bytes and requires no reinstall or receipt edits.

RC4-08 completed on the final Home 1.20.7 and Helper 0.9.4. The
three-minute export completed with four populated foreground-window
records, each with the bounded app ID and window type fields. During
capture, paired network HOME from Media Player reached and stayed
on Clean Your TV. The reporter's original webOS 4.5 YouTube scenario
remains deferred to matching hardware.

The controlled Off-to-On repeat reproduced the unavailable switch
after explicit Off. LG Home routing and the saved Off choice were
verified. A second software restart restored the ordinary On action
for the independent physical tests. This repeat confirms a usable
re-enable failure on the selected C3 package before restart. The
mechanism and extent across other preconditions are open. At 19:00:13
the final No-root package was active with Media Player in front, ready
for the Magic Remote standby, Home and emergency escape checks.

The No-root physical request was issued with the final package and a
confirmed Media Player starting state. The owner was not observed
performing the sequence before the 19:07 handoff to required rollback
and the independent Root cases. Passive records showed a screen-saver
cycle while the TV stayed Active, with Media Player still foreground.
There is no physical evidence for No-root standby or triple-Home in
this window. The case stays selected and requires physical input on
the final artifact. The owner was asked to wait before further input.

The signed No-root rollback completed at 19:07–19:08, retained the
verified engine slot and restored working Home from Media Player.
The rendered English settings and configuration exactly matched the
published baseline export. Before removing that restored edition,
one matching control comparison on the rolled-back Home and Helper
isolates whether the new No-root package bytes are required for the
Off-to-On failure. This uses the already available package state.

The comparison after rollback reproduced the same unavailable
Off-to-On switch with published Home 1.20.5 and Helper 0.9.3. The
signed rollback kept engine 1.2.16. This comparison therefore shows
the symptom with both package sets under that test state, and leaves
the behavior with the original 1.2.14 bootstrap and fresh standalone
install undetermined.

The ordinary RC4 installer began full No-root removal. It required
the previously saved Root connection for this installation. The Root
handoff re-used the removal flow and reached its expected
restart-required state. A verified software restart reset uptime and
removed the unique temporary marker before retrying the same removal.

At 19:13 the retained removal continuation reached
`verified-completion`, with `removed` and `verified_clean` both true.
Media Player remained available and paired network HOME settled on
stock LG Home. This covers the selected ordinary No-root removal and
Root connection handoff. The Root-installed cleanup case remains
separate. The published v1.26.0 Root installer passed its published
checksum and was started after this clean-state readback.

#### C3 Root observations

The published v1.26.0 Root installer completed on the cleaned C3.
Root Home 0.23.0 had a positive persistent active readback and paired
network HOME from Media Player opened Root Home before the transition.
The existing System IPK 1.2.11 reported its original engine 1.2.14.
The recorded live Root profile was used for signed forward at 19:17.
The candidate Root 0.24.1 IPK SHA-256 is
`cc4dc070e7ff9400d051b733bc9f8b8afbf649a71e99296d295bd174dd14b9bd`;
Root Updater 0.6.6 is
`955eda9c015672b520554d12bdba68640d829048e958222e254186057ba25fda`;
Root infrastructure is
`1186cee5471a9d245fa4543bb1a69318e8dfb55caa3bfc1b98213546590fae38`.

**Root forward failed.** The System engine migrated successfully and
the device installed and foregrounded Root 0.24.1. The launcher failed
to deliver its profile readiness receipt before the updater's 120-second
health deadline. At about 19:23 the durable transaction automatically
entered rollback with `Launcher profile readiness timed out`. The
earlier harness timeout left the operation in place. No second install
or manual health acknowledgement was submitted.

The automatic rollback restored Root 0.23.0 and completed its normal
Home restoration. Readback reported `phase=rolled-back`,
`homeResumePhase=rolled-back`, `status=restored` and active persistent
Root intent. The restored app had rendered. This is automatic recovery
from a failed forward update. The separate supported Root rollback
after a successful forward and the signed Romanian Root Repair remain
blocked on a successful forward transaction. The `v1.27.0` OTA failed
before successful active Home resume could be tested.

After automatic rollback, paired network HOME from Media Player settled
on Root Home, and the captured settings and configuration matched the
pre-update export. The exact RC4 macOS installer then completed
ordinary Root cleanup after a verified software restart. It returned
`verified-completion`. Media Player remained available and network HOME
settled on LG Home. This completes the selected C3 removal and recovery
subcase of RC1-05 with its stated transition.

The Root 0.24.1 application extracted from the verified signed IPK was
exercised in local Chromium with the same privately captured Root
profile and a modeled LS2 broker. An existing verifying transaction
and a visible installing-to-verifying transition both submitted the
correct health receipt. When the broker reported service unavailable
at startup, the launcher loaded the saved profile. A later normal
`webOSRelaunch` after broker restoration did not submit health. This
demonstrates a failure mode under modeled replies. The actual C3
broker reply at the failed startup was not captured, so causality is
unconfirmed.

A separate clean installation from the pinned RC4 macOS CLI was
started only after the verified cleanup. It can exercise the
independent Root runtime cases. It cannot supply signed OTA evidence.

The clean RC4 direct Root installation reached verified completion.
Root 0.24.1 persistent intent was active and paired HOME from Media
Player opened Root Home. The rendered Change Home switch produced a
verified disabled state and LG Home routing. An ordinary re-open
and On returned the intent to active and restored Root Home routing.
At 19:33:37, Media Player was foregrounded for the physical Root
check. A pre-test uptime and unique temporary marker were recorded
for the AC power verification.

#### RC4 case reconciliation before physical Root evidence

| Case | Disposition at this checkpoint |
| --- | --- |
| RC1-01 | No-root signed forward and Romanian Repair passed. Signed Romanian Root Repair is blocked by Root forward. |
| RC1-02 | No-root signed forward, same-IPK Repair and supported rollback passed. Root forward failed its readiness deadline. Automatic Root rollback restored the previous package, profile and routing. A separate Root Repair and requested rollback require successful forward. |
| RC1-03 | The source Root route was active. Candidate automatic resume after signed forward is blocked by Root OTA. Direct final Root network routing passed. Physical sound, standby, cold start and emergency escape await the owner on the direct build. W20H retained-receipt hardware remains deferred. |
| RC1-04 | Exact Root Beta passed both modeled B9 offline scenarios. Physical B9 is explicitly deferred. |
| RC1-05 | Both C3 editions reached verified full removal with stock LG Home and a surviving Media Player. Existing pinned CI evidence covers the scoped legacy cache and metadata fixtures. |
| RC1-06 | Exact production-signed Android APK passed all owned-emulator cases. |
| RC4-07 | Explicitly deferred to an eligible physical embedded LG Home device. |
| RC4-08 | Final C3 No-root export and routing passed. The original webOS 4.5 YouTube case is deferred. |
| RC4-09 | No-root retains Off and routes to LG Home. Its ordinary Off-to-On flow failed twice and needed software restart. Direct Root Off-to-On and both routing destinations passed. No-root physical evidence was unavailable during its handoff window. Root physical evidence is outstanding. The original G3 inactivity scenario is deferred. |

Nine cases stay selected. Four passed within their non-deferred scope
(RC1-04, RC1-05, RC1-06, RC4-08). Two have directly observed failures
(RC1-02, RC4-09). Two are partially demonstrated with blocked signed
Root scenarios (RC1-01, RC1-03). One case is explicitly deferred
(RC4-07). P00 and CI support individual subchecks; no entire case
uses prior-candidate evidence in place of the selected artifact.
The required physical observations stay open. This is a checkpoint
with release blockers, and stable acceptance remains unset.

At 19:40:35 UTC+05:00, C3 still had Media Player in front with the
direct Root 0.24.1 route active. Uptime had continued and the unique
cold-start marker remained. No physical result had arrived for sound,
standby, Magic Remote Home/escape or AC boot. The C3 hardware subcases
are blocked on the owner's physical availability in this window and
retain their case IDs. The earlier No-root hardware subcases also
retain their requirement on the exact No-root artifact.

Exit reconciliation for the current QA window retains nine selected
cases: four scoped passes, two cases with observed failures, two
partially verified cases with concrete blockers, and one explicit
other-model deferral. Earlier evidence supports individual subchecks;
zero complete cases use previous-candidate evidence. There are zero
remaining independent automated cases in the original plan. Owner
input and successful signed Root forward are the remaining specific
dependencies. The Root OTA failure and the reproduced No-root
re-enable failure are recorded separately. Stable release acceptance
remains unset and v1.26.0 remains the current public release.
