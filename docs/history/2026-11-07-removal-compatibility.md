# Removal compatibility corrections — 2026-11-07

This records source and host verification for the unpublished 1.10.0 candidate.
It is not a device installation/removal report. Final changed-removal acceptance
is deferred; unrelated manual feature checks are not repeated in this task.

## Corrected boundaries

- Strict stdin execution on Node 20+ exposes a getter-only global WebCrypto
  property. `cleanup_tail.js` used top-level `var crypto`, so it could fail before
  its guards. A local Node 23 stdin run reproduced the exception, while `-e` and
  the VM fixture did not. Two binding references now use `nodeCrypto`; a real
  stdin regression reaches the exact selector guard on both current Node and
  Node 8 with the getter-only binding.
- The shared cleaner recognizes UID0 and exact `0777` only on fixed SDK
  containers and known project app/service roots. Existing UID501/1001 shared
  services/packages handling remains. Unknown writable ancestry, UUID staging,
  foreign owners, symlinks and inode replacement are still refused.
- A failed or unconfirmed disable response from the two optional legacy
  Helper/Renewal services moves the existing full-boot checkpoint before package
  removal. The marker and boot baseline survive interruptions. After the boot
  changes, cleanup does not relaunch the recorded broken service. Root routing
  restoration, exact owned-activity cancellation and final absence proofs remain
  mandatory. Unexpected bus failures still stop cleanup.
- Known Root completed-profile and rollback-anchor data, plus finite System
  current-descriptor/installer-acceptance records, are classified by their exact
  component and bounded filename formats. Live roots and already authenticated
  archives use the same classification. Genuine inverse backups remain separate;
  unknown names, unsafe ownership/mode, hardlinks and changed inodes still block.
- Five existing removal reason codes survive diagnostic projection. The existing
  removal plan supplies Retry advice without a contradictory generic unfinished
  installation warning. Specific trust/authentication/storage advice keeps its
  priority. No private error text is exported and no new user copy is introduced.

## Verification

Independent scoped reviews approved the changes. The relevant regressions failed
before the fixes and passed afterward:

- Root cleanup/tail: 74/74 passed on Linux, exact Node 8.12.0 and strict GCC 12.2,
  with real UID1001/shared-directory, directory-replacement and original-lock
  handoff checks. Read-only source hashes matched before and after the run.
- Shared cleaner: 32/32 passed on current Node; six focused cases passed on each
  exact Node 0.10.15, 0.10.25, 0.12.2 and 8.12.0. These model the reported SDK
  ownership explicitly; modeled UID metadata is not a device acceptance claim.
- Diagnostic and retry guidance: 48 passed, including private-message exclusion,
  first-failure retention and specific authentication/trust guidance priority.
- Known private receipts: five new cases passed; affected host groups ran 51
  cases with 50 passed and one Linux-only skip. Near-prefix/wrong-component,
  foreign-owner and hardlink refusal cases remain covered.

The normal focused payload builder passed. Compared with build 42276916934's
actual Android payload, only `root-updater/install_device.py`,
`root-updater/cleanup_tail.js`, `root-updater/cleanup_no_root_private.js` and their
bundle manifest changed. All TV IPKs, published Helper 0.7.4 and the native
installer-support utility are byte-identical. This does not establish that the
changed installer execution has completed successfully on a TV.

## Candidate and acceptance boundary

Build 42276916934 remains successful evidence for its original source. Its pin
is removed from the corrected branch because installer inputs changed. A new
complete candidate must pass and be selected before final acceptance; the release
PR remains draft. No Helper lifecycle, supervisor migration or new cleanup
framework is introduced. Versions remain the unpublished 1.10.0 component set.

The intended remaining device sequence is the same removal intent, interrupted
connection/retry, a verified full kernel boot, final absence readback and repeated
Remove. An AC power-disconnect result is not available. Fresh interrupted setup,
pristine unrooted Developer Mode and other hardware remain untested unless
separately recorded. No public release or shipping notice is announced.

## Integrated source and replacement preflight

PR #367 head `c13f33c29e5faed797b6a8068844f0fe1641f50d` passed all eight
Linux/macOS runtime groups, browser, ARM/Python and integration policy
([42285970466](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42285970466)).
Merge `d158b3738` has the identical tested tree. The actual inventory is collected
without changing the unpublished version set. Helper remains byte-identical to
published 0.7.4; Android retains its existing signer and no Homebrew promotion
approval is selected. No new signing input is introduced.

`release-inputs.py` identifies ten guarded changes relative to the prior selected
build, so a replacement full candidate is required: `cytv/diagnostic_context.py`,
`cytv/failure_help.py`, `cytv/no_root_cleanup.py`, `root-edition/cleanup_tail.js`,
`root-edition/install_device.py`, `root-edition/tests/test_clean_removal.py`,
`root-edition/tests/test_cleanup_tail.py`, `tests/cytv/test_diagnostic_context.py`,
`tests/cytv/test_failure_help.py` and `tests/cytv/test_no_root_simple_removal.py`.
The following freeze commit changes only exempt release metadata and documents.
Physical acceptance remains deferred; the source/build gate does not complete it.

## Selected corrected candidate

[Full build 42287736073:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42287736073)
completed successfully from `a8015ac2cd42d070cd4e12c6d8349e60eda21dcf`. All four
desktop platforms, Android and all 21 workflow jobs passed. This is the
selected build in `release-plan.json`; physical acceptance remains empty.

The actual Windows job ran 832 installer tests in 184.038 seconds: no errors or
failures, 163 expected platform skips. Frozen console cp1252, payload/runtime and
all three extracted desktop checks passed. The fresh browser-theme profile
executed all 43 commands successfully. Browser-core used authenticated matching
PR evidence; its receipt ZIP digest and run/job binding were independently checked.

Independent Android artifact verification matched GitHub archive digest
`66cd3ac9f8fdbc7d86318eb3a11486bc985c20059f0ad316032ea180459fb619`.
APK SHA256 is `f81eda4df2be10e23e02e7043647aeb33ff3f6229778f1acb36b2cda1ac51e7d`.
Embedded source/version provenance and all 316 payload hashes matched the
checked focused build, including all four corrected support files/manifests.
All TV IPKs, Helper and native utility remain byte-identical to the preceding
candidate. The exact new payload is retained privately for subsequent acceptance.
No phone/TV operation is implied by this artifact inspection.

Reviewed all 13 localized removal instructions: they request a restart when
needed without prescribing its position relative to package removal. The same
translated Retry/maintenance flow remains correct; no new text or action was added.
The installer does not restart a TV automatically. No further device change or
reboot was performed after the maintainer deferred physical testing until morning.

### Artifact inventory

These are retained Actions ZIP digests, not published feed hashes or device
acceptance. All expected platform/test artifacts were present and unexpired.

| Artifact | ID | SHA256 |
| --- | --- | --- |
| cytv-android-arm64 | 13538466837 | `66cd3ac9f8fdbc7d86318eb3a11486bc985c20059f0ad316032ea180459fb619` |
| cytv-android-native-tests | 13538401922 | `0100290168ea33c13529c6e216902d102ebfaa09536a5d18a39e2d37459b3c97` |
| cytv-linux-x64 | 13538717542 | `cb82bbdc01025e53a4ce64d56dc232b94689d3f05537a525b7888587dc75980c` |
| cytv-linux-x64-desktop | 13538348213 | `3eb3c0a0d11c7891930b30610d70746b3f52cc205a29b99d8b086faff298f11a` |
| cytv-macos-arm64 | 13539380186 | `dd82d51a8011f03ec0084f4b3702487e0ae25ff62a29c7266adf379ceec83fa3` |
| cytv-macos-arm64-desktop | 13538472722 | `d0efc32cfffc4ce619f66bc47e950a172f5485deb28e8f498a40aeb0f8bba4bd` |
| cytv-macos-x64 | 13539271058 | `5cb16d2b04988df5ac876327df666958ec5d7af6e538d5b5215d1981a007523d` |
| cytv-macos-x64-desktop | 13539321111 | `b73554a2eb8592539f76705b7c9fd1d3d43ca5f39f85fdac3ee70023fcc17715` |
| cytv-windows-x64 | 13539530205 | `5c4853c1be580fd042443aeab87c965443928e136d11f4f2c976063b08fdc622` |
| cytv-windows-x64-desktop | 13539515154 | `6863838460cd3132244fd899269512de0ef2cec4bc861b332ea359f7a424a2a6` |
| homebrew-candidate | 13538177434 | `cc26c101103cd13866c31f8a9b02c18a0a7702355bd1a64d6a99032c23222dd7` |

## Interrupted registration restoration follow-up

The selected build above is superseded for changed removal support. A host
regression reproduces an interrupted restoration chain: System lockdown restores
the Root updater's installed API, Root registration restoration restores the
original SDK API, and a later interruption occurs before `controls-restored`.
Retry previously rejected that final SDK state as unknown lockdown drift.

The clean-removal path now recognizes that state only for the fixed Root updater
API. It checks the exact live registration receipt against the System snapshot,
the four fixed registration paths, the linked installed/original API bytes and
the exact disabled-snapshot transformation. Both legacy byte-only and newer
metadata snapshots remain supported. It leaves an already restored SDK API
untouched; all lockdown entries are validated before any restoration write.
Unknown bytes, broken snapshot links and unsafe metadata still stop removal.
Standalone supervisor removal keeps its default strict behavior.

Focused host verification passed: 35 Root clean-removal tests, 19 supervisor
removal tests and 39 rollback/recovery tests. The new interruption regression
failed before the fix and passed afterward, including legacy byte-only receipts;
six damaged-byte/receipt/metadata cases refuse before restoration writes. The
standalone compressed SSH command remains below its unchanged 8,000-byte limit
(7,994 bytes). The normal public payload builder passed; TV IPKs are unchanged.

No new user action, translation, service or state journal is introduced. The
existing Retry and requested full-restart instructions remain applicable.
The old build pin is cleared; a replacement complete candidate and affected
acceptance are required. This source record does not claim device completion.

### Bounded activity inventory

The existing detailed activity listing can exceed the generic updater RPC
64-KiB response limit. Dropping subscriber data is insufficient and must not
replace the activity name/callback/ID ownership proof. The RPC helper now allows
2 MiB only for the exact `luna://com.palm.activitymanager/list` URI, matching the
existing recovery-activity and final-cleanup helpers. Every other URI, including
near matches, keeps its 64-KiB bound; queries and cancellation selection are
unchanged. Three real child-pipe tests cover successful larger inventory,
oversized refusal, other/near-match URI refusal and client process reaping.
They failed on the old activity bound and passed after the two-line correction.
The fixed caller-identity regression also passed. The normal payload build copies
the change into both updater support bundles; all TV IPKs remain byte-identical.
The replacement candidate must include and verify the changed support bytes.

### Snapshot-aware restart continuation

Removal's raw kernel UUID comparison missed a known firmware property already
documented in [Root cold-start identity](../development/ROOT-COLD-BOOT.md): a
snapshot boot can reuse that UUID. Clock/uptime heuristics are not substituted.
Root removal now calls the existing `intent_runtime.boot_identity` from the
current verified payload in isolated Python. A legacy raw baseline without a
valid prior verified pair is replaced with a session baseline and requires a
further restart. Every rebaseline clears the prior verified fact. No new Root
boot service, observer, journal or marker format is introduced.

No-root records a single non-executable, private volatile marker for its already
approved removal goal. Creation binds the goal and actual kernel UUID; the host
captures its inode and device before effects. Probe never recreates it. A changed
kernel UUID or absence of the captured marker supplies the boot fact; altered
contents, ownership, mode, links or inode refuse continuation. Inventory remains
read-only. Marker retirement independently checks restart evidence. Before rearm
creates a replacement marker, the existing host journal clears the old proof,
so a lost response can recover the exact goal and establish a fresh baseline.

The Root tail uses a strict, distinct, same-format durable baseline/verified pair
only as the previously observed boot fact. Original ownership, package receipts,
current package/private-file absence, routing, process, activity and registration
checks remain mandatory. This permits retry after Python retirement and a later
volatile reset. Only the three known existing Root boot-session files are retired
through the pinned scanner after that durable proof; final readback checks the
directory is absent. Unknown members and unsafe metadata still block removal.

Focused host verification passed: 84 Root cleanup/tail/simple/handoff tests
(three platform skips), 25 tail tests on exact Node 8 (one platform skip), and
41 No-root cleanup tests. Eight affected cases passed on each exact Node
0.10.15, 0.10.25, 0.12.2 and 8.12.0. The emitted legacy-compatible JavaScript
is bound to SHA256 `3726e7990da5fe2232302d5a84620b38fae3f121ad93e47b7716588bc6429cab`.
Regressions reproduced UUID-only refusal, mixed-format false progress and a lost
rearm response before their fixes. These are source/model results; they do not
establish universal volatile-store lifetime or pristine No-root TV acceptance.
