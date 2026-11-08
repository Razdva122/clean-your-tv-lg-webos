# v1.14.0 candidate preparation — 2026-11-09

Candidate [#442](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/442)
contains seven implementation PRs: #441, #444, #445, #447, #449, #450 and #451.
All use merge commits into `release/next`; none is excluded. Root/Beta #451 was
held for its existing task's completed revision, then reviewed and merged only
after a80392fb passed its final required CI. No new features are admitted after
this scope/version freeze. The PR stays draft for exact-build acceptance.

## Versions and actual packaging dependencies

| Component | Published v1.13.0 | Frozen target | Reason |
| --- | --- | --- | --- |
| Release | 1.13.0 | 1.14.0 | Advisory and shared capability-based Root backend |
| Home FHD/HD | 1.13.2 | 1.13.3 | Shared Chinese subset changes |
| Helper | 0.8.0 | 0.8.0 | Exact published bytes retained |
| cytv | 0.14.0 | 0.15.0 | Advisory, catalog transport, continuation and selector |
| Android / versionCode | 0.13.0 / 28 | 0.14.0 / 29 | Shared operations and embedded packages |
| Root / infrastructure | 0.13.2 | 0.14.0 | Service broker, admission and normal/Beta closure |
| Both edition Updaters | 0.5.4 | 0.5.5 | Shared Chinese subset changes; runtime unchanged |
| Fresh System / protocol | 1.2.7 / 1 | 1.2.7 / 1 | All 29 own bundle files match published bytes |

Initial source review suggested retaining Home/Updater versions because their
runtime sources were unchanged. Actual package preflight disproved that proposal:
`scripts/chinese_fonts.py` also reads the installer's literal translation corpus.
#449's first literal adds U+4E92 (互) to both SC/TC subsets, with no removed glyphs.
The first preliminary package comparison differed only in those two font files;
both Home graphics packages and both Updaters therefore require version bumps.
No font algorithm or runtime fix was added. A subsequent package-version check
caught the still-old renewal-service manifest; it was synchronized to Home1.13.3
before the full dispatch. These preliminary failures are not recorded as passes.

Helper0.8.0 is byte-for-byte identical to the signed published package, so no new
Helper transition or compatibility approval is selected. System's 29 own files
also retain exact published bytes. Root and its infrastructure archive change;
Updater version metadata changes in the dependent Root recovery closure too.
Regenerate release-set data for the new artifacts. Existing supervisors remain
pinned, with no new migration permission. Homebrew promotion remains disabled.
Android keeps its application ID, original signer and private storage layout.

## Authenticated baseline and host verification

Published v1.13.0 is neither draft nor prerelease. Downloaded BUILD-INFO,
SHA256SUMS, four signed System feeds, both Home IPKs, Helper, both Updaters and
the Root release archive. Downloaded asset checksums match SHA256SUMS. The four
feed signatures verify with the pinned public key; downloaded Home/Helper hashes
and sizes match signed bindings. BUILD-INFO source
`7edc6cecd492c31ebf82940ba0a6a983875c989d` matches the release target and versions.
Published Root archive manifests authenticate the extracted bundle files before
comparison; no device or private data is involved.

| Retained baseline | SHA-256 |
| --- | --- |
| Home1.13.2 FHD | `a1cef43e5317dc309cb7c424304ce943a1a8c9bb7f2926866d6eb9f3f043f0ec` |
| Home1.13.2 HD | `77cad4a33d8b4fa8e37af6fdb54e32611afde90c7d6f8f2848b40994b4ced1a0` |
| Helper0.8.0 | `6116d99281d2f5c21ff192ddb07ce6cbdae4223573999ac0d310d86ace87e0c2` |
| System1.2.7 IPK | `4debad924655388c5d3450a81a83496cbc40e48e66ce150ec858fdf8f99ef96c` |

Host: macOS ARM64, Python3.14.2 project virtualenv, Node23.11.0, locked npm
installation. `scripts/test.sh installer android setup` on the four-PR integrated
product inputs c601f0e8 passed 1,179 installer cases (six skips), 44 Android and
285 setup cases, plus selected Homebrew checks. Final #451 a80392fb passed 1,185
installer cases (three skips), 286 setup cases, 81 C1 runtime cases, exact
Node0.12.2/8.12.0/current generated-closure checks and real ARM32 builds in its
own task. Its final Linux/macOS, browser, ARM Python and Windows/macOS desktop
runtime CI passed. [Detailed development evidence](2026-11-09-root-beta-keyfilters.md).
These precede the versioned complete candidate; none is new TV acceptance.

Independent integration reviews found no runtime/security issue. Review found
stale SDK6–9/C1-only installation wording; it is corrected to distinguish the
unpublished shared Root/Beta path, capability requirements and physical limits.
Schema2 identity/state/recovery formats are preserved, but fresh probes and
explicit re-enable now require the shared read-only environment checks too.
That is conservative admission hardening, not unchanged admission; restore does
not call the admission probe. Developer guidance and release notes record it.
README metadata tests (3), formatting and whitespace checks pass. Versioned
payload validation and final frozen CI results are recorded below when complete.

## Documentation

Reviewed README, documentation index, edition selection, installation,
maintenance/removal, updates, recovery, controls, CLI/desktop, compatibility and
prerequisites, Root entry/recovery/update guides, Android guide/readiness, and the
affected developer authority/diagnostic/CI references. The merged #445/#447/#449
and #451 documentation covers current behavior and all 13 localized guides.
Localized additions are practical selection/advisory steps, with no project
release versions, publication banners or QA status. Existing anchors remain.
Unchanged controls/removal/feedback instructions require no new command or
permission. Fixed stale published-v1.13.0 candidate/download wording in README,
Root README and recovery. New candidate-specific guide notices remain honest
until publication; historical evidence and actual unpromoted Homebrew/Beta limits
retain their original scope. [Candidate release notes](../RELEASE-1.14.0.md).

## Scoped acceptance and issue disposition

No TV was accessed or changed. New physical model/firmware/remote and installer
platform for device acceptance are unselected/unknown. Historical C3 and Android
emulator results retain their original hashes and state preconditions.

| Case | Changed path / plausible failure | Minimum useful check | State |
| --- | --- | --- | --- |
| Latest installer choice | #449 could bypass explicit choice or block recovery | GUI/CLI metadata/error/consent regressions; packaged desktop smoke | Source tests passed; final installers pending |
| No-root continuation | #444 repairs only an exact owned key | Original operation/inode/emergency-stop tests; supported affected-device continuation | Host passed; reporter device untested |
| Root catalogs | #450 bypasses Node child process | Actual reader with subprocess forbidden, stream/deadline/mandatory-app checks; packaged setup | Host passed; reporter device untested |
| Shared Root/Beta KeyFilters | #451 changes admission and loaded broker/filter | Exact legacy runtimes and refusal fixtures; versioned fresh alternative setup, Home/emergency/key-up/restore and fault cleanup | Host passed; physical cases pending |
| Ordinary Root | Shared broker loads in the normal service too | Exact package/service load and normal profile selection; short usable-state/control check after selected delivery | Pending final artifacts |
| Shared fonts | New corpus adds one Chinese glyph | Font coverage, generated package/resource comparison and Chinese browser rendering | Preliminary font delta verified; frozen browser pending |
| Android update | New APK and embedded shared operations | Exact original-signer code28→29 emulator upgrade, retained Store/native operation checks | Pending final APK |

The original #410 remains open/planned: native ARM32 LG Home is still required;
in-compositor LG panels are refused and a KeyFilters field alone is insufficient.
#389 and #437 remain open/awaiting-release for their integrated source fixes, with
reporter-device confirmation outstanding. No reporter installation result or raw
diagnostic is republished. Experimental compositor/Beta ordinary OTA must remain
refused. Unchanged No-root input/watchdog code and routine package-version changes
do not select a whole new controls/AC-boot matrix by themselves. Changed Root
native paths still need their selected emergency/recovery and power-state cases;
no existing unresolved blocker is waived. Audible playback/HDMI, standby, AC cold
boot, OTA/rollback and physical phone-to-TV are not new passes. Final acceptance
must name build/attempt, artifact hashes, device/state preconditions and observed
results. No approval or acceptance is inferred from host tests.

## Completed pre-dispatch payload check

The final `build-cytv.py --payload-only` exits successfully and verifies 596 public
payload files, graphics, component/service metadata and normal/Beta backend
closures. The preliminary same-version/font and renewal-manifest failures above
are resolved before any full candidate dispatch. Eighteen Chinese font/preparation
tests pass. Home/Updater public file sets match the prior packages: only selected
version fields and the two SC/TC fonts differ. Helper matches exact prior bytes;
all 29 System own files match its authenticated published bundle. No Helper
transition probe is needed for those identical Helper bytes.

| Preliminary versioned package | SHA-256 |
| --- | --- |
| Home1.13.3 FHD | `74a683cc91556beb530d8ba0fa9160f6e84ab5c17990f01681b436ff53e67489` |
| Home1.13.3 HD | `d14675151a8feaad6157e44ed2a17e5d07ebcb33a0703e149b3cfc61c11ac6a7` |
| No-root Updater0.5.5 | `1878a84a223058d3fe3c622cdb29f181fa3ec93d3e89ec0dea0aed3355de0ed9` |
| Root Updater0.5.5 | `141aecaba4c5e700d5cd1bda2b8f691c28aca49a679277402115207df0b7827f` |
| Root0.14.0 FHD | `114d3ad1a8a390741c7140dc8b424c415a6661865b3eced6d4562e101c893ecb` |
| Root0.14.0 HD | `ed98a51864f2ad04d8ed22257ca77eebfc4f2f6aeef6117058bb4c985a23741c` |

These are local preliminary packages, not pinned CI artifacts or device acceptance.
Final metadata/notes/inventory agree; full candidate validation remains to run.
