# TV Installer 0.1.0 on the v1.30.0 base

Selected for physical acceptance on 2026-11-28. This is a local macOS build of
`io.github.razdva122.cytvinstaller`. The build comparison ran offline after checking the GitHub tag and artifact
identity. The subsequent [C3 session](#c3-device-session-2026-11-28) confirmed
the package update and exposed a blocker before fresh Root setup.

## Package identity and comparison

| Input or result | Identity |
| --- | --- |
| Product source | [v1.30.0](https://github.com/Razdva122/clean-your-tv-lg-webos/tree/v1.30.0), `e9def6f2b3fa8a8469bfe2129c77f79d3cc37d84` |
| Official reference | [RC3 Homebrew job](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/46070775288/job/140747036211), run `46070775288:1`, source `dc9196fd1258cd38900db023f4b9cbd3ce76c68a` |
| CI input ZIP | [Artifact 15232822503](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/46070775288/artifacts/15232822503), SHA-256 `a1fe8940c4e48c76e6a4fb4715e5dc90f5f57d17f24970ce57181e7ac5f9ee77` |
| Reference Installer 0.0.0 | 205,958,534 bytes, SHA-256 `924fc522dba1b3af85b109eb4e180b01e549afa46ffb0dad16f178a77101b26d` |
| Selected Installer 0.1.0 | `io.github.razdva122.cytvinstaller_0.1.0_all.ipk`, 205,958,522 bytes, SHA-256 `91545d5ee923957bb298845c5b78c5c45c02ff957fe932f5f968b64243dba778` |
| Shared embedded inventory | `payload/manifest.json`, SHA-256 `258f9bc9f5d7740ece15926597488839d50029653318216011a8d60bdeeafef7` |

The tagged source differs from the RC3 source only in the release plan and
final acceptance document. The tagged packager built the tile with
`homebrew/build.py --installer-payload <verified-RC3-payload> --output <new-directory> --version 0.1.0`.
All 277 payload files, including the inventory, came from the authenticated
RC3 IPK. The packager and the manifest tool's offline verifier checked the
component inventories and runtime. A control repack of the 0.0.0 files with
the same packager reproduced the official RC3 IPK SHA-256 exactly.

Of 326 installed regular files, 323 match byte for byte. Each of the three
differences is exactly the substitution `0.0.0` → `0.1.0` in `appinfo.json`,
`report-version.js` and the outer package's `packageinfo.json`. The packaging
control record has the same substitution in `Version`. Both archives declare
214,430,140 installed bytes. Archive entry names, types, modes, ownership,
timestamps and uncompressed sizes match. Root 0.26.0, Root Updater 0.6.9,
System Updater 1.2.11, the No-root packages, offline Python, rollback cache,
bootstrap and routing code all match their RC3 counterparts.

## What carries forward on C3

The reference device was a project LG OLED55C3RLA, firmware 43.21.71,
webOS SDK 11.2.0, with stock Homebrew Channel 0.8.0. The physical remote
model is unknown. HB08-01 already records the Homebrew update and root-access
check. The development sessions established clean Root setup with system
Python, complete removal from TV and desktop, verified restart and return
to LG Home. The forced No-root fixture established refusal before writes,
resumption after consent, then focused daily tile launch and network HOME
after the routing correction. Keep each observation attached to its original
package and input path. [Homebrew C3 observations at the release tag](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.30.0/docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#c3-clean-install-and-removal-with-setup-checks)

The last C3 routing fixture (`cfefdf06…`) shared 304 of 326 regular files
with RC3, including its corrected `app.js`. The edition decision, embedded
Home/Helper packages and recovery baseline changed between that fixture and
RC3. The published release exercised the standard host installation, while
this IPK embeds the single-tile generation. Its Root Home, No-root Home and
Helper IPK hashes differ from the public counterparts. Reuse the component and
input observations within those boundaries. [Routing fixture results](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.30.0/docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#resume-after-native-pairing-approval) · [Standard release acceptance](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.30.0/docs/history/2026-11-28-release-1.30.0-final-acceptance.md)

## Remaining physical checks

Only the first row adds a version-specific check. Combine it with the existing
Homebrew installation pass on the selected IPK. The other rows map outstanding
work from the [original Task 8 matrix](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.30.0/docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#task-8-physical-matrix) and [HB08 plan](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.30.0/docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#homebrew-080-verification-2026-11-25).

| Existing cases | Observation still needed |
| --- | --- |
| HB08-02, HB-FALLBACK-01 | Install the selected IPK through the Homebrew UI. Verify installed files, package-manager version 0.1.0, foreground launch, actual app inspection and Installer version 0.1.0 in its diagnostic report. Record staging space and representative setup/maintenance screenshots. If an older Installer is already present, record whether its existing state survives the update. |
| HB08-03, HB08-05, HB-E2E | On the naturally Root-capable C3, verify fresh setup, activation, one daily tile, opening Root Home, and stable network HOME from Media Player. Verify the System Updater registrations and baseline, preserved settings when an eligible profile exists, and defaults on clean setup. Record runtime choice and peak space. |
| HB08-03/04 | Continue the same operation across matching host and TV clients in both directions. Check simultaneous requests, lost UI/network, restart and the recovery rows for interrupted stages. Verify the original receipt, one owner, and preserved state. |
| HB08-04 | Exercise signed single-tile upgrade and retained rollback on the TV, with profile restoration, a healthy Home and independent recovery. This needs a compatible signed generation-two offer and rollback baseline. The public v1.30.0 generation-one feed and offline signature tests do not supply that device observation. |
| HB08-05/07 | Verify physical triple-Home emergency release, including with the UI frozen, standby/wake, then a separate AC cold boot. Check routing and ordinary remote controls after each. While Root is present, verify the Homebrew firmware-block setting in Root Home, persistence after software restart and restoration of its original value. |
| HB08-06, HB-TVREMOVE, HB-FALLBACK-05 | After checks that require an installed product, cover separate Installer removal with the product preserved, direct deletion of each Root component with safe recovery, and full removal from the applicable clients. Verify owned state, the retained receipt, and stable LG Home. Reuse the earlier cancellation, restart/continue and UI observations where inputs match. |
| HB08-03, HB-FALLBACK-02–05, HB-ROUTE | Two starting states need separate coverage. A supported device without suitable system Python is needed for offline runtime preparation and its storage peak. Natural No-root fallback needs a rooted TV where the stock detector rules out Root and admits No-root. The C3's ordinary system-Python/Root path and the forced fixture establish different parts. Verify the selected generation's pairing, components, tile, HOME and cleanup on the applicable path. |

Home Chooser coexistence is a separate compatibility claim. If advertised,
verify switching Root Home → LG Home, persistence of the owner's selection
and recovery on removal. It adds no general catalog submission requirement.
[Home Chooser launcher contract](https://github.com/webosbrew/home-chooser/blob/main/docs/launcher-api.md#1-declare-the-app)

## Publication handoff

This record selects the local IPK for testing. For publication, record named
human review and close the physical matrix, select the originating project
release and its immutable URLs, then bind the exact IPK and serialized catalog
manifest in the protected approval. Verify trusted CI reproduces the accepted
hash, the public checksum and URLs resolve, the screenshots are available, and
the upstream package checks pass against those public bytes. The older
`v1.30.0` assets stay the source reference. [Promotion procedure](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.30.0/homebrew/DEVELOPMENT.md#acceptance-and-existing-release-gate)

## C3 device session, 2026-11-28

Handoff recorded at the first session check, 06:38:49 UTC. The source IPK
matched the selected SHA-256. The project OLED55C3RLA reported firmware
43.21.71, SDK 11.2.0, and stock Homebrew Channel 0.8.0 with root and firmware
blocking enabled. SSH used the saved host identity. Before installation,
the package manager listed Installer 0.0.0 and none of the selected Root or
No-root product packages. Free space was 3,783,592 KiB on the application
volume and 446,572 KiB on the volume containing /var/lib.

The existing tile opened No-root recovery with a saved operation, a No-root
daily tile binding and no Resume button. The retained on-TV No-root setup
record was at stage complete. Desktop removal records reported verified-clean.
A missing product and a retained operation are distinct starting conditions.
The Homebrew Channel UI offered Update in the private catalog for the
selected 0.1.0 IPK.

### Exact package result and clean-setup blocker

Homebrew's ordinary Update and Launch controls installed and opened 0.1.0.
The TV package manager reported 0.1.0. All 326 installed regular files matched
the selected IPK by SHA-256, with zero missing or extra files. The tile kept
the previous No-root edition and operation. Its **Save diagnostic report**
action persisted Installer version 0.1.0 and reported No-root,
`recovery_required`, stage `complete`, code `current-state-unverified`.

The actual Russian UI marked “Запуск Home Helper” as failed before and after
a status refresh. The No-root package, Helper and updater were absent. The
current product removal fence matched the final verified-clean receipt, with
private cleanup and service/startup removal confirmed. Independent readback
confirmed absence of product paths, hooks, registrations and active private
runtime. The separate Homebrew No-root coordinator still held its completed
setup record. An app-originated read-only inspection returned No-root recovery
even without specifying the browser's saved operation. It reported no active
operation and passed Homebrew access, root, payload, Python and staging checks.

The No-root status reader checks whether the original installed updater is still
present and bound to that setup. Its absence after removal makes current-state
verification fail. The UI maps stage complete to the final No-root progress row
and labels a recovery-required result as a failure on that row. This status read
does not attempt to start Helper. [Status reader](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.30.0/homebrew/no_root.py#L823) · [Progress mapping](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/v1.30.0/homebrew/app/setup-progress.js#L89)

The normal host Root handoff from matching single-tile source also recognized
the full tile and opened it. It reached the same recovery screen with Refresh,
Save/Open report and Close. Neither entry offered Install or Resume. No Root
setup was submitted. The previous No-root installation and current desktop
removal need reconciliation before this C3 can enter fresh setup through the
selected Homebrew artifact. Preserve the original receipts for this finding.

### Case reconciliation for this session

| Original group | Result and unresolved dependency |
| --- | --- |
| HB08-01 | Reused the earlier successful Homebrew 0.8.0 update. Current version, root configuration and access were confirmed again. |
| HB08-02 / HB-FALLBACK-01 | Package identity, bytes, launch, saved-report version and preservation across the update passed. Fresh Root review failed on this starting state. Its setup and maintenance screenshots remain unavailable. Only baseline free space was recorded. |
| HB08-03 / HB-E2E | Host-to-TV entry reached the installed tile. Root setup, clean defaults/import, both clients continuing the same Root transaction and its peak storage require an admitted Root request. Offline Python preparation also requires a compatible TV without suitable system Python. |
| HB08-04 | No Root transaction exists to interrupt, resume or challenge with a concurrent client. Signed single-tile upgrade and rollback additionally require a compatible generation-two offer and an installed baseline. |
| HB08-05 / HB-ROUTE | Stock safety route passed: Media Player → one paired network HOME → LG Home at 0.35 s, stable for at least one second. Root activation, physical emergency/frozen UI, standby and AC cold boot require active Root routing. |
| HB08-06 / HB-TVREMOVE | The existing clean receipt and current product absence were verified. Direct component deletion, removal with the product preserved, and full removal from each client require the corresponding installed product. Reinstalling the tile alone would leave the same independent coordinator readback. |
| HB08-07 | Root Home was absent. Its firmware-blocking switch and restart/restore sequence cannot be exercised from the Installer. The original Homebrew firmware-blocking setting was enabled. |

All seven original groups are accounted for: one reused pass, one failed
expected screen with passing package checks, two partial groups (03/05) and
three blocked groups (04/06/07). No deferrals were approved. No independent
case remains runnable on this starting state within the selected path. Natural
No-root fallback still needs hardware that actually rules out Root; HB-FALLBACK
and HB-ROUTE development-fixture observations retain their earlier scope.
Physical acceptance remains open. The temporary catalog was removed through
the Homebrew UI and its loopback server was closed. The TV was returned to
LG Home with Installer 0.1.0 retained for diagnosis.

## Read-only check of the proposed fix on the same C3

With the installed 0.1.0 runtime, payload and original records intact, the
updated bootstrap ran its normal setup inspection over the existing QA SSH
connection. The Root driver reported a verified clean removal and the No-root
reader returned the same completed operation with unverified current state.
The stock detector selected Root. The combined result was fresh, installable,
and included a candidate digest and the superseded operation. No install
request was submitted. The corrected packaged tile, Root activation and the
physical cases above still require candidate acceptance.
