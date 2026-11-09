# v1.14.0 candidate preparation — 2026-11-09

**Subsequent QA:** [the current dated QA record](2026-11-09-release-1.14.0-qa.md)
adds reviewed signing correction #456 and selects replacement full build42566531298:1
with completed scoped C3/Android acceptance. The eight-PR preparation/build below
is historical; its pin and pending-device statements describe that earlier stage.

Candidate [#442](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/442)
contains eight implementation/maintenance PRs: #441, #444, #445, #447, #449, #450,
#451 and release-blocking fixture correction #452.
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
payload validation and final frozen CI results are recorded below.

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
| Latest installer choice | #449 could bypass explicit choice or block recovery | GUI/CLI metadata/error/consent regressions; packaged desktop smoke | Source and packaged host checks passed |
| No-root continuation | #444 repairs only an exact owned key | Original operation/inode/emergency-stop tests; supported affected-device continuation | Host passed; reporter device untested |
| Root catalogs | #450 bypasses Node child process | Actual reader with subprocess forbidden, stream/deadline/mandatory-app checks; packaged setup | Host passed; reporter device untested |
| Shared Root/Beta KeyFilters | #451 changes admission and loaded broker/filter | Exact legacy runtimes and refusal fixtures; versioned fresh alternative setup, Home/emergency/key-up/restore and fault cleanup | Host/final build passed; physical cases pending |
| Ordinary Root | Shared broker loads in the normal service too | Exact package/service load and normal profile selection; short usable-state/control check after selected delivery | Final artifact/host checks passed; physical checks pending |
| Shared fonts | New corpus adds one Chinese glyph | Font coverage, generated package/resource comparison and Chinese browser rendering | Font delta, exact CI payload and frozen browser coverage passed |
| Android update | New APK and embedded shared operations | Exact original-signer code28→29 emulator upgrade, retained Store/native operation checks | Final signed APK verified in CI; exact upgrade/native acceptance pending |

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
Final metadata/notes/inventory agree; completed full-candidate validation is below.

## Consolidated first-run inventory and replacement

Full candidate42516955873:1 at7f0a98df completed all21 jobs:20 successful and
one failed Windows desktop job. Linux, macOS ARM64/Intel, Android, all8 runtime
shards, full browser/themes, ARM Python and aggregate validation completed.
Windows stopped during its host suite:1,057 cases,237 skips, one failed existing
`RootInventoryRuntimeTests.test_direct_reply_keeps_original_icon_and_metadata`.
No Windows installer artifact was produced. This failed run is not selected.

The fixture ran the real TV reader with the Windows host `path.resolve`, so the
POSIX TV icon path became a drive/backslash path and failed the reader allowlist.
Forcing `path.win32` on macOS reproduced the exact fallback-icon failure before
the fix. #452 selects the real Node `path.posix` in the fixture's existing module
guard, retaining its forbidden-child-process check, filesystem fixture and real
icon/metadata assertions. All9 runtime cases pass under the same forced-Windows
injection after the fix; all21 clean-reinstall tests pass normally. Independent
review and the complete PR CI pass. Only this fixture changed; no product code,
package/version, state format or device action changed.

The isolated fixture correction was prepared while the independent first-run
cases finished, then merged only after the complete failure inventory above.
No product fix or feature was interleaved with that case pass. There are no other
observed failures in this pass. Source-equivalence checking explicitly reports
`Candidate build inputs changed; rebuild required: tests/cytv/test_clean_reinstall.py`.
That guarded validation input requires one replacement full candidate; it cannot
be represented as a retry of unchanged source or a successful pin of the failed
run. Existing package preflight and scoped physical limitations remain applicable;
no old device result is relabeled as acceptance of new artifacts. Normal trusted
unit receipts may reuse matching successful checks without weakening coverage.

## Selected complete candidate and exact artifact verification

[Full build42519326218:1](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42519326218)
completed successfully at `4f9bcec196441eb23a5b4ff29fbe9a76dd5b8619`: all21 jobs
passed. This includes four desktop builds/package-runtime checks, signed Android,
all8 Linux/macOS runtime shards, browser/full-theme coverage, ARM Python, Homebrew
and the full-release marker. The Windows host suite that exposed the fixture
failure now passes on an actual Windows runner. Coverage uses fresh checks and
normal authenticated matching unit receipts; no required area is dropped or
new receipt fabricated. The failed first candidate is retained as history only.

The committed build pin selects this run/attempt/source; acceptance stays empty
and no acceptance_build token is asserted before actual device observations.
GitHub lists all9 expected console/desktop/Android artifacts, nonexpired and with
SHA-256 digests. Downloaded `cytv-macos-arm64` matches API artifact digest
`sha256:6414d30124d91a32c447b153fc57797a1f482315b0d2f6572d00df6a5875a24f`.
Its console SHA-256 is
`484d4fd9cc8d5ad38fddc94d03eff6d4b37c6e49621cb5d402448b25725d92fd`.
Without executing the binary, the release verifier checked all596 embedded
payload file hashes and component versions. Its complete payload hash map equals
the preliminary payload, including all package hashes recorded above; Helper
and System retain the authenticated published bytes. This is exact CI artifact
verification, not a new physical/Home/OTA/rollback observation.

The release remains draft for the selected TV and Android exact-upgrade/native
acceptance cases, final signing/public-feed verification and publication. #410
is still unresolved/planned; #389/#437 await delivery and reporter-device results.
Only metadata/evidence changes follow the selected build, with input equivalence
verified before pushing the pin. Do not rebuild for these records alone.
