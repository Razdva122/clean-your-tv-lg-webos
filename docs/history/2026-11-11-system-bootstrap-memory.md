# System bootstrap read allocation correction — 2026-11-11

Focused implementation evidence for [issue507](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/507), targeting the coordinated fix batch for [candidate491](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/491).
The [canonical candidate ledger](2026-11-11-release-1.17.0-candidate.md) retains the original selected cases, failures and exit reconciliation. This record does not create another acceptance plan or change their disposition.

## Investigation and correction

The owner-present C3 setup failed in snapshot → verify_baseline → safe while reading a captured baseline cache, before System bootstrap/package submission. Source investigation reproduced a separate, concrete allocation defect: reading a real8192-byte file with safe reserved100797373 traced bytes on the macOS host because read received the96MiB policy ceiling plus one. This is a Python allocation peak, not a disk-full result. Other TV process/address-space constraints have not been established.

The reader now requests the descriptor-checked actual size plus one, still enforcing the existing96MiB admission ceiling, no-follow ancestors/descriptor, regular-file, single-link and optional owner/mode checks. Length must equal the observed size, so growth or truncation between stat and read refuses rather than returning a partial baseline. No new dependency, persistent state, permission, endpoint, lease, package-submission or health behavior is introduced.

The same8192-byte read now peaks at142269 traced bytes (about139KiB). This removes the needless maximum-sized allocation; it is not a claim that all archive buffering is eliminated or that the TV MemoryError has already been accepted fixed.

## Verification and packaging

Baseline before implementation:15 existing System build/bootstrap tests passed. The new memory regression first failed at100796477 bytes against a1MiB threshold; growth/truncation regressions also failed without the size check. An initial directory-exception expectation was corrected in the test before product changes. The three final regression methods then passed after the minimal reader correction.

Fresh checks on the corrected source:

- `python -m unittest discover -s tests/system_updates`:139 passed, including baseline integrity, packaging, bootstrap, supervisor update and rollback dependencies.
- `python -m unittest discover -s tests/cytv -p 'test_system*.py'`:98 passed, including installer setup/replacement/recovery interfaces.
- Ordinary and legacy-node Beta System bundles rebuilt and compared file-for-file with selected full build42969073353:1's authenticated CLI payload. Only `setup-system-updater.py` and its enclosing `bundle.json` differ. Both System IPKs retain SHA256 `2aad7f24a652b7bfd7d65c925a53f560f5f97986edf832a95bcae8b879a6d716`; installed supervisor code and version1.2.8 remain identical.
- `git diff --check` passed. User-facing setup steps, controls and localized guides are unchanged.

Host: existing project virtualenv on macOS arm64. All new fixtures are synthetic; no TV was contacted by this fix task and no device data was deleted. The original OLED55C3RLA/firmware43.21.71/SDK11.2.0 observations remain in the canonical ledger, with Magic Remote exact model unknown.

## RC integration and remaining acceptance

The coordinator owns release inventory, versions, selected build and the one replacement full dispatch after the complete fix batch. Changed embedded bootstrap bytes require replacement CLI/APK artifacts; the old build cannot certify their delivery. No full candidate, signing run or device reinstall was dispatched here. Existing unchanged evidence remains reusable under the release rules.

T17-04 must rerun the previously blocked fresh System bootstrap on the corrected artifact, then real signed Root update/profile/health/Home Off. T17-05 remains dependent on that successful signed transaction and must run retained rollback/forward. This focused host result neither clears those acceptance gaps nor establishes anonymous public-feed delivery or compatibility with another TV. No main merge or public release is authorized by this record.
